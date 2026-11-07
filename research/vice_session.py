#!/usr/bin/env python3
"""Run an owned PAL VICE research session, accepting JSON monitor commands.

Example input: {"command": "disass 8:0401 8:04ff"}
All monitor commands and responses are preserved in the output directory.
Only the emulator created by this process is stopped during cleanup.

For a documented BASIC SYS entry, use --no-autostart, wait for BASIC READY,
then load the original PRG through the monitor. Keyboard input is unquoted
lowercase text, for example: keybuf sys12288\\x0d. VICE converts ASCII to
PETSCII; quotation marks become literal keystrokes.
"""

import argparse
import datetime
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from verify import connect_monitor, vice_command


class ResearchMonitor:
    prompt = re.compile(rb"\((?:C|8|9|10|11):\$[0-9a-fA-F]{4}\) $")

    def __init__(self, connection):
        self.connection = connection
        self.transcript = []
        connection.settimeout(0.1)
        try:
            while connection.recv(65536):
                pass
        except socket.timeout:
            pass
        connection.settimeout(30)

    def run(self, command):
        self.connection.sendall((command + "\n").encode())
        response = b""
        needs_registers = command.strip() in ("r", "registers")
        try:
            while (not self.prompt.search(response)
                   or needs_registers and not re.search(rb"^\.;", response, re.M)):
                part = self.connection.recv(65536)
                if not part:
                    raise RuntimeError("VICE closed the research monitor connection.")
                response += part
        except (OSError, RuntimeError) as error:
            self.transcript.append(command + "\n" + response.decode(errors="replace")
                                   + f"\n[Monitor observation failed: {error!r}]\n")
            raise
        result = response.decode(errors="replace")
        self.transcript.append(command + "\n" + result)
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("program", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--disk", type=Path)
    parser.add_argument("--vice", default=shutil.which("x64sc"))
    parser.add_argument("--no-autostart", action="store_true",
                        help="Start a reset machine; load the program later through the monitor.")
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    command = vice_command(args.vice, args.program, port, ROOT / "palettes/colodore.vpl")
    if args.no_autostart:
        autostart = command.index("-autostart")
        del command[autostart:autostart + 2]
    command += ["-drive8type", "1541", "-drive8truedrive", "+autostart-handle-tde"]
    if args.disk:
        command += ["-8", str(args.disk.resolve())]
    monitor = None
    with (output / "vice.log").open("w") as log:
        process = subprocess.Popen(command, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True)
        receipt = {"pid": process.pid, "port": port, "command": command,
                   "program": str(args.program.resolve()),
                   "startup_mode": "manual monitor load" if args.no_autostart else "autostart",
                   "started_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()}
        (output / "session.json").write_text(json.dumps(receipt, indent=2) + "\n")
        try:
            with connect_monitor(process, port) as connection:
                monitor = ResearchMonitor(connection)
                initial = monitor.run("r")
                monitor.run("sidefx off")
                (output / "monitor.log").write_text("\n".join(monitor.transcript))
                print(json.dumps({"ready": receipt, "initial_registers": initial}), flush=True)
                for line in sys.stdin:
                    try:
                        request = json.loads(line)
                        if request.get("close"):
                            print(json.dumps({"closed": True}), flush=True)
                            break
                        response = monitor.run(request["command"])
                        (output / "monitor.log").write_text("\n".join(monitor.transcript))
                        print(json.dumps({"response": response}), flush=True)
                    except Exception as error:
                        if monitor:
                            (output / "monitor.log").write_text("\n".join(monitor.transcript))
                        print(json.dumps({"error": repr(error)}), flush=True)
                        if process.poll() is not None:
                            break
        finally:
            if monitor:
                (output / "monitor.log").write_text("\n".join(monitor.transcript))
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)
            receipt["exit_code"] = process.returncode
            receipt["closed_utc"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            (output / "session.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
