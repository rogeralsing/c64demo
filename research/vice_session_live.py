#!/usr/bin/env python3
"""Run one owned PAL VICE instance with a cancellable monitor observer.

JSON input accepts {"command": "..."}, {"interrupt": true}, and
{"close": true}. An interrupt sends read-only `r` on the existing socket.
It does not restore a snapshot, change PC, or restart a timed-out command.
"""

from collections import deque
import argparse
import base64
import datetime
import json
import os
from pathlib import Path
import re
import selectors
import shutil
import signal
import socket
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verify import connect_monitor, vice_command


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def emit(value):
    print(json.dumps(value), flush=True)


class Journal:
    """Flush input, actual wire bytes and lifecycle evidence independently."""

    def __init__(self, directory):
        self.directory = directory
        self.received = (directory / "received.bin").open("wb")
        self.sent = (directory / "sent.bin").open("wb")
        self.input = (directory / "input.bin").open("wb")
        self.events = (directory / "events.jsonl").open("w")
        self.monitor = (directory / "monitor.log").open("w")

    def event(self, kind, **fields):
        self.events.write(json.dumps(dict(utc=utc(), kind=kind, **fields)) + "\n")
        self.events.flush()

    def wire(self, direction, data, **fields):
        stream = getattr(self, direction)
        first = stream.tell()
        stream.write(data)
        stream.flush()
        self.event(direction, first=first, end=stream.tell(), **fields)
        return first

    def text(self, data):
        self.monitor.write(data.decode(errors="replace"))
        self.monitor.flush()

    def save_session(self, receipt):
        # Keep the previous complete JSON readable if this process is interrupted.
        temporary = self.directory / "session.json.tmp"
        temporary.write_text(json.dumps(receipt, indent=2) + "\n")
        temporary.replace(self.directory / "session.json")

    def close(self):
        for stream in (self.received, self.sent, self.input, self.events, self.monitor):
            stream.close()


class LiveObserver:
    prompt = re.compile(rb"\((?:C|8|9|10|11):\$[0-9a-fA-F]{4}\) $")
    registers = re.compile(rb"(?m)^\.;[0-9a-fA-F]{4}\b")

    def __init__(self, process, connection, journal, receipt, timeout, close_grace, signals):
        self.process, self.connection = process, connection
        self.journal, self.receipt = journal, receipt
        self.timeout, self.close_grace, self.signals = timeout, close_grace, signals
        self.queue, self.active = deque(), None
        self.sequence, self.stdin_buffer = 0, bytearray()
        self.closing, self.close_deadline = False, None
        self.reason = None
        self.initial_registers = None
        self.connection.settimeout(0.2)
        self.selector = selectors.DefaultSelector()
        self.selector.register(connection, selectors.EVENT_READ, "socket")
        self.selector.register(sys.stdin.fileno(), selectors.EVENT_READ, "stdin")
        self.enqueue("r", internal=True)
        self.enqueue("sidefx off", internal=True)

    def enqueue(self, command, request_id=None, internal=False):
        if not isinstance(command, str) or not command.strip():
            raise ValueError("command must be a nonempty string")
        if any(character in command for character in "\r\n\x00") or len(command.encode()) > 4096:
            raise ValueError("command must be one monitor line, at most4096 UTF-8 bytes")
        self.sequence += 1
        frame = dict(sequence=self.sequence, id=request_id, command=command, internal=internal,
                     response=bytearray(), sent_at=None, waiting_reported=False, interrupt=None)
        self.queue.append(frame)
        self.journal.event("queued", **self.frame_summary(frame))
        return frame

    @staticmethod
    def frame_summary(frame):
        return {key: frame[key] for key in ("sequence", "id", "command", "internal")}

    def send(self, command, sequence, purpose):
        data = (command + "\n").encode()
        self.journal.event("send_requested", sequence=sequence, purpose=purpose, command=command)
        self.journal.text(data)
        remaining = memoryview(data)
        while remaining:
            count = self.connection.send(remaining)
            if not count:
                raise RuntimeError("VICE closed while sending monitor input")
            self.journal.wire("sent", remaining[:count].tobytes(), sequence=sequence, purpose=purpose)
            remaining = remaining[count:]
        self.journal.event("send_complete", sequence=sequence, purpose=purpose)

    def start_next(self):
        if self.active is not None or not self.queue or self.closing:
            return
        self.active = self.queue.popleft()
        self.active["sent_at"] = time.monotonic()
        self.active["received_first"] = self.journal.received.tell()
        self.send(self.active["command"], self.active["sequence"], "ordinary")

    def interrupt(self, reason):
        frame = self.active
        if frame is None or frame["command"].strip().lower() not in ("x", "exit"):
            self.journal.event("interrupt_rejected", reason="No pending x/exit", requested_by=reason)
            return False
        if frame["interrupt"] is not None:
            self.journal.event("interrupt_already_pending", sequence=frame["sequence"], requested_by=reason)
            return True
        interruption = dict(reason=reason, response_first=len(frame["response"]),
                            received_first=self.journal.received.tell(), requested_utc=utc())
        self.journal.event("interrupt_requested", sequence=frame["sequence"], **interruption)
        try:
            self.send("r", frame["sequence"], "interrupt")
        except BaseException as error:
            self.journal.event("interrupt_send_failed", sequence=frame["sequence"],
                               interruption=interruption, error=repr(error))
            # A partial wire send cannot safely be retried. Leave no successful
            # interrupt marker, and fail into the owned-process cleanup path.
            raise RuntimeError("Interrupt input was not fully sent; closing owned session") from error
        frame["interrupt"] = interruption
        return True

    def request_close(self, reason):
        if self.closing:
            return
        self.closing, self.reason = True, reason
        self.close_deadline = time.monotonic() + self.close_grace
        self.journal.event("close_requested", reason=reason)
        while self.queue:
            frame = self.queue.popleft()
            self.journal.event("cancelled_before_send", **self.frame_summary(frame))
            if not frame["internal"]:
                emit(dict(status="cancelled", **self.frame_summary(frame)))
        if self.active is not None:
            self.interrupt("close")
        emit(dict(closing=True, reason=reason))

    def input_line(self, raw):
        self.journal.event("input_line", raw_base64=base64.b64encode(raw).decode())
        try:
            request = json.loads(raw)
            if not isinstance(request, dict):
                raise ValueError("input must be a JSON object")
            actions = sum(key in request for key in ("command", "interrupt", "close"))
            if actions != 1:
                raise ValueError("input must contain exactly one command, interrupt or close action")
            if "close" in request:
                if request["close"] is not True:
                    raise ValueError("close must be true")
                self.request_close("input")
            elif "interrupt" in request:
                if request["interrupt"] is not True:
                    raise ValueError("interrupt must be true")
                emit(dict(interrupt_requested=self.interrupt("input")))
            elif self.closing:
                raise ValueError("session is closing; no new commands accepted")
            else:
                frame = self.enqueue(request["command"], request.get("id"))
                emit(dict(accepted=True, **self.frame_summary(frame)))
        except ValueError as error:
            self.journal.event("input_rejected", error=str(error))
            emit(dict(error=str(error)))

    def read_input(self):
        data = os.read(sys.stdin.fileno(), 65536)
        if not data:
            self.selector.unregister(sys.stdin.fileno())
            if self.stdin_buffer:
                self.input_line(bytes(self.stdin_buffer))
                self.stdin_buffer.clear()
            self.request_close("stdin EOF")
            return
        self.journal.wire("input", data)
        self.stdin_buffer.extend(data)
        while b"\n" in self.stdin_buffer:
            line, _, rest = self.stdin_buffer.partition(b"\n")
            self.stdin_buffer = bytearray(rest)
            if line.strip():
                self.input_line(bytes(line))

    def read_socket(self):
        data = self.connection.recv(65536)
        if not data:
            self.journal.event("socket_closed")
            self.reason = self.reason or "monitor connection closed"
            return False
        self.journal.wire("received", data, active_sequence=self.active["sequence"] if self.active else None)
        self.journal.text(data)
        if self.active is None:
            # No command is sent until this batch is handled. Retain unsolicited
            # greeting/output without assigning it to a later command.
            self.journal.event("unsolicited_output", bytes=len(data))
            return True
        frame = self.active
        frame["response"].extend(data)
        response = bytes(frame["response"])
        needs_registers = frame["command"].strip().lower() in ("r", "registers")
        register_scope = response
        if frame["interrupt"] is not None:
            needs_registers = True
            register_scope = response[frame["interrupt"]["response_first"]:]
        if not self.prompt.search(response) or needs_registers and not self.registers.search(register_scope):
            return True
        status = "interrupted" if frame["interrupt"] else "completed"
        result = dict(status=status, **self.frame_summary(frame), response=response.decode(errors="replace"),
                      received_first=frame["received_first"], received_end=self.journal.received.tell())
        if frame["interrupt"]:
            result["interrupt"] = dict(**frame["interrupt"], command="r", drained_registers_and_prompt=True,
                                       register_response=register_scope.decode(errors="replace"))
        self.journal.event("response", **result)
        if frame["internal"]:
            if frame["command"] == "r":
                self.initial_registers = result["response"]
            elif frame["command"] == "sidefx off":
                emit(dict(ready=self.receipt, initial_registers=self.initial_registers))
        else:
            emit(result)
        self.active = None
        return True

    def run(self):
        try:
            while True:
                if self.signals:
                    self.request_close("signal " + self.signals.pop(0))
                if self.process.poll() is not None:
                    self.reason = self.reason or "owned VICE exited"
                    break
                if self.closing and (self.active is None or time.monotonic() >= self.close_deadline):
                    break
                self.start_next()
                ready = self.selector.select(0.1)
                # Deliver interrupt/close requests before interpreting a racing
                # natural-stop prompt. No queued command starts inside handlers.
                ready.sort(key=lambda pair: pair[0].data != "stdin")
                alive = True
                for key, _ in ready:
                    if key.data == "stdin":
                        self.read_input()
                    else:
                        alive = self.read_socket()
                        if not alive:
                            break
                if not alive:
                    break
                if self.active and not self.active["waiting_reported"]:
                    elapsed = time.monotonic() - self.active["sent_at"]
                    if elapsed >= self.timeout:
                        self.active["waiting_reported"] = True
                        value = dict(status="partial", waiting=True, elapsed_seconds=round(elapsed, 3),
                                     **self.frame_summary(self.active), received_bytes=len(self.active["response"]),
                                     action="Still pending; send interrupt or close. No retry or restart.")
                        self.journal.event("observation_timeout", **value)
                        emit(value)
        finally:
            # An EOF/socket error or unexpected exception must not leave queued
            # commands looking as though they were sent during cleanup.
            while self.queue:
                frame = self.queue.popleft()
                self.journal.event("cancelled_before_send", **self.frame_summary(frame))
            if self.active is not None:
                frame = self.active
                result = dict(status="partial", **self.frame_summary(frame),
                              response=bytes(frame["response"]).decode(errors="replace"),
                              interrupt=frame["interrupt"], reason=self.reason or "observer exception")
                self.journal.event("partial_response", **result)
            self.selector.close()
        return self.reason


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--disk", type=Path)
    parser.add_argument("--vice", default=shutil.which("x64sc"))
    parser.add_argument("--no-autostart", action="store_true")
    parser.add_argument("--observation-timeout", type=float, default=30,
                        help="Report partial/waiting after this many seconds; never restart (default30).")
    parser.add_argument("--close-grace", type=float, default=3,
                        help="Seconds to drain a pending interrupt before owned process cleanup (default3).")
    args = parser.parse_args()
    if not args.vice:
        parser.error("VICE x64sc was not found; supply --vice")
    if args.observation_timeout <= 0 or args.close_grace < 0:
        parser.error("observation-timeout must be positive; close-grace must be nonnegative")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    journal, process, connection = Journal(output), None, None
    signals, previous_handlers = [], {}
    receipt = dict(observer="vice_session_live.py", program=str(args.program.resolve()),
                   started_utc=utc(), output=str(output))
    for number in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[number] = signal.getsignal(number)
        signal.signal(number, lambda signum, _frame: signals.append(signal.Signals(signum).name))
    try:
        with socket.socket() as reserve:
            reserve.bind(("127.0.0.1", 0))
            port = reserve.getsockname()[1]
        command = vice_command(args.vice, args.program, port, ROOT / "palettes/colodore.vpl")
        if args.no_autostart:
            index = command.index("-autostart")
            del command[index:index + 2]
        command += ["-drive8type", "1541", "-drive8truedrive", "+autostart-handle-tde"]
        if args.disk:
            command += ["-8", str(args.disk.resolve())]
        with (output / "vice.log").open("w") as log:
            process = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
        receipt.update(pid=process.pid, port=port, command=command,
                       startup_mode="manual monitor load" if args.no_autostart else "autostart")
        journal.save_session(receipt)
        journal.event("owned_process_started", pid=process.pid, port=port, command=command)
        connection = connect_monitor(process, port)
        observer = LiveObserver(process, connection, journal, receipt, args.observation_timeout, args.close_grace, signals)
        receipt["close_reason"] = observer.run()
    except BaseException as error:
        receipt["observer_error"] = repr(error)
        journal.event("observer_error", error=repr(error))
    finally:
        if connection is not None:
            connection.close()
        if process is not None:
            if process.poll() is None:
                journal.event("owned_terminate_requested", pid=process.pid)
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    journal.event("owned_kill_requested", pid=process.pid)
                    process.kill()
                    process.wait(timeout=5)
            receipt["exit_code"] = process.returncode
            receipt["owned_process_reaped"] = process.returncode is not None
        receipt["closed_utc"] = utc()
        journal.save_session(receipt)
        journal.event("closed", **receipt)
        journal.close()
        for number, handler in previous_handlers.items():
            signal.signal(number, handler)
        try:
            emit(dict(closed=True, session=receipt))
        except BrokenPipeError:
            pass


if __name__ == "__main__":
    main()
