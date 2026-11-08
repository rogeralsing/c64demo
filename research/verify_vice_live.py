#!/usr/bin/env python3
"""Passively verify retained real VICE wire, cancellation and closure evidence.

No emulator, subprocess, CPU model or live connection is started. The raw wire
contract is checked independently of the observer implementation.
"""

import base64
import datetime
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "build/research/vice-live-verification"
OUTPUT = BASE / "verification"
LIVE_SHA = "4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c"
FROZEN_SHA = "173134636447e1c670074c49dc3007751390958ce39990036568c6cbe5826124"
REJECTED_SHA = "406599dd7fe9e7862e27bd7928ea39121dea6716c90af63b943be504dbcf83e1"
CASE_PINS = {
    "interrupt-01": "8ddc5cee0287bf83a96fbd69066d6059683d9e3903eabe7c5416faf117918c01",
    "interrupt-02": "30fc777b625bae18f6d022197c66885c48d88fa3c92e3200cb2bca232de143bc",
    "trace-01": "47e1625dfb734183cc2cc0d1f63a65fa01ba1708505135e8d13e972f10eb1680",
    "rejected-utc-collision": "b9d6aad23da74e2ed8bfd324a6100bf0bb566d7a01cf2a349716144633cb0100",
}
PROMPT = re.compile(rb"\((?:C|8|9|10|11):\$[0-9a-fA-F]{4}\) $")
REGISTERS = re.compile(
    r"(?m)^\.;([0-9a-fA-F]{4})\s+([0-9a-fA-F]{2})\s+([0-9a-fA-F]{2})\s+"
    r"([0-9a-fA-F]{2})\s+([0-9a-fA-F]{2})\s+([0-9a-fA-F]{2})\s+"
    r"([0-9a-fA-F]{2})\s+([01]{8})\s+(\d+)\s+(\d+)\s+(\d+)\s*$")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def pinned_case(name):
    directory = BASE / name
    items = [dict(name=path.name, bytes=path.stat().st_size, sha256=sha(path.read_bytes()))
             for path in sorted(directory.iterdir()) if path.is_file()]
    digest = sha(json.dumps(items, sort_keys=True, separators=(",", ":")).encode())
    assert digest == CASE_PINS[name], ("Changed retained evidence", name, digest)
    return [artifact(directory / item["name"]) for item in items]


def registers(text):
    matches = REGISTERS.findall(text)
    assert len(matches) == 1, ("Expected one explicit register row", len(matches))
    values = matches[0]
    keys = ("pc", "a", "x", "y", "sp", "port00", "port01", "flags", "line", "cycle", "clock")
    return {key: int(value, 16 if index < 7 else 2 if index == 7 else 10)
            for index, (key, value) in enumerate(zip(keys, values))}


def audit_session(name):
    directory = BASE / name
    files = pinned_case(name)
    session = json.loads((directory / "session.json").read_text())
    events = [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]
    wire = {kind: (directory / filename).read_bytes()
            for kind, filename in (("input", "input.bin"), ("sent", "sent.bin"), ("received", "received.bin"))}
    cursors, queued, cancelled, ordinary, responses, partial = dict.fromkeys(wire, 0), {}, set(), {}, {}, {}
    active, sending, input_lines, request_rows = None, None, [], []
    previous_utc = None
    starts, closes, terminations, waits = [], [], [], []
    for index, event in enumerate(events):
        kind = event["kind"]
        timestamp = datetime.datetime.fromisoformat(event["utc"])
        assert previous_utc is None or timestamp >= previous_utc
        previous_utc = timestamp
        if kind in wire:
            first, end = event["first"], event["end"]
            assert first == cursors[kind] and first < end <= len(wire[kind]), (name, index, event)
            cursors[kind] = end
            if kind == "sent":
                assert sending is not None
                assert (event["sequence"], event["purpose"]) == (sending["sequence"], sending["purpose"])
                sending["bytes"].extend(wire[kind][first:end])
            elif kind == "received":
                assert event["active_sequence"] == (active["sequence"] if active else None)
        elif kind == "input_line":
            input_lines.append(base64.b64decode(event["raw_base64"], validate=True))
        elif kind == "queued":
            sequence = event["sequence"]
            assert sequence not in queued
            queued[sequence] = event
        elif kind == "send_requested":
            assert sending is None
            sequence = event["sequence"]
            assert sequence in queued and sequence not in cancelled
            if event["purpose"] == "ordinary":
                assert active is None and sequence not in ordinary, "Ordinary command retried or overlapped"
                assert event["command"] == queued[sequence]["command"]
                active = dict(sequence=sequence, first=cursors["received"], interrupt=None)
                ordinary[sequence] = event
            else:
                assert event["purpose"] == "interrupt" and event["command"] == "r"
                assert active and active["sequence"] == sequence and active["interrupt"] is None
                assert queued[sequence]["command"] in ("x", "exit")
                active["interrupt"] = cursors["received"]
            sending = dict(**event, bytes=bytearray())
            request_rows.append(event)
        elif kind == "send_complete":
            assert sending is not None
            assert (event["sequence"], event["purpose"]) == (sending["sequence"], sending["purpose"])
            assert bytes(sending["bytes"]) == (sending["command"] + "\n").encode()
            sending = None
        elif kind == "response":
            sequence = event["sequence"]
            assert active and sequence == active["sequence"] and sequence not in responses
            assert sending is None
            assert event["received_first"] == active["first"] and event["received_end"] == cursors["received"]
            raw = wire["received"][active["first"]:cursors["received"]]
            assert raw.decode(errors="replace") == event["response"] and PROMPT.search(raw)
            if event["status"] == "interrupted":
                interrupt = event["interrupt"]
                assert active["interrupt"] == interrupt["received_first"]
                assert interrupt["response_first"] == active["interrupt"] - active["first"]
                assert interrupt["command"] == "r" and interrupt["drained_registers_and_prompt"]
                register_raw = raw[interrupt["response_first"]:]
                assert register_raw.decode(errors="replace") == interrupt["register_response"]
                registers(interrupt["register_response"])
                assert PROMPT.search(register_raw)
            else:
                assert event["status"] == "completed" and active["interrupt"] is None
                if event["command"] in ("r", "registers"):
                    registers(event["response"])
            responses[sequence] = event
            active = None
        elif kind == "partial_response":
            sequence = event["sequence"]
            assert active and sequence == active["sequence"] and sequence not in partial
            assert event["status"] == "partial"
            assert event["response"] == wire["received"][active["first"]:cursors["received"]].decode(errors="replace")
            partial[sequence], active = event, None
        elif kind == "observation_timeout":
            assert active and event["sequence"] == active["sequence"]
            assert event["waiting"] and event["status"] == "partial"
            assert event["received_bytes"] == cursors["received"] - active["first"]
            assert event["sequence"] not in [row["sequence"] for row in waits]
            waits.append(event)
        elif kind == "cancelled_before_send":
            sequence = event["sequence"]
            assert sequence in queued and sequence not in ordinary and sequence not in cancelled
            cancelled.add(sequence)
        elif kind == "owned_process_started":
            starts.append(event)
        elif kind == "owned_terminate_requested":
            assert active is None and event["pid"] == session["pid"]
            terminations.append(event)
        elif kind == "closed":
            assert active is None and sending is None
            assert all(event[key] == value for key, value in session.items())
            closes.append(event)
        else:
            assert kind in ("interrupt_requested", "interrupt_already_pending", "close_requested", "input_rejected"), kind
    assert all(cursors[kind] == len(data) for kind, data in wire.items())
    assert input_lines == [line for line in wire["input"].splitlines() if line.strip()]
    assert set(queued) == set(ordinary) | cancelled
    assert set(ordinary) == set(responses) | set(partial)
    assert len(starts) == len(closes) == len(terminations) == 1
    assert starts[0]["pid"] == session["pid"] and starts[0]["port"] == session["port"]
    assert starts[0]["command"] == session["command"]
    assert session["exit_code"] == -15 and session["owned_process_reaped"] and session["closed_utc"]
    assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]
    address = f"ip4://127.0.0.1:{session['port']}"
    assert session["command"].count(address) == 1
    assert len({row["sequence"] for row in request_rows if row["purpose"] == "ordinary"}) == len(ordinary)
    public_commands = [json.loads(line) for line in input_lines if "command" in json.loads(line)]
    assert [(row["command"], row.get("id")) for row in public_commands] == [
        (row["command"], row["id"]) for row in queued.values() if not row["internal"]]
    return dict(name=name, files=files, session=session, events=events, wire=wire,
                queued=queued, requests=request_rows, responses=responses, partial=partial,
                cancelled=cancelled, waits=waits)


def by_id(case, identifier):
    rows = [row for row in case["responses"].values() if row["id"] == identifier]
    assert len(rows) == 1, ("Missing completed response", identifier)
    return rows[0]


def interruption(case, identifier, reason):
    candidates = [row for row in case["queued"].values() if row["id"] == identifier]
    assert len(candidates) == 1
    sequence = candidates[0]["sequence"]
    sends = [row for row in case["requests"] if row["sequence"] == sequence and row["purpose"] == "interrupt"]
    assert len(sends) == 1, "No interrupt r on original wire"
    response = by_id(case, identifier)
    assert response["status"] == "interrupted" and response["interrupt"]["reason"] == reason
    return registers(response["interrupt"]["register_response"])


def natural_stop(case):
    response = by_id(case, "natural-raster")
    assert response["status"] == "completed" and "interrupt" not in response
    beam = re.search(r"(?m)^#\d+ \(Stop on\s+exec ([0-9a-fA-F]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+", response["response"])
    cpu = re.search(r"(?m)^\.C:([0-9a-fA-F]{4})[^\n]*- A:([0-9a-fA-F]{2}) X:([0-9a-fA-F]{2}) Y:([0-9a-fA-F]{2}) SP:([0-9a-fA-F]{2}) ([NV\-BDIZC.]{8})\s+(\d+)\s*$", response["response"])
    assert beam and cpu
    assert int(beam[1], 16) == int(cpu[1], 16) and int(beam[2]) == 267
    flags = sum((128 >> i) for i, value in enumerate(cpu[6]) if value != ".")
    expected = dict(pc=int(cpu[1], 16), a=int(cpu[2], 16), x=int(cpu[3], 16), y=int(cpu[4], 16),
                    sp=int(cpu[5], 16), flags=flags, clock=int(cpu[7]), line=int(beam[2]), cycle=int(beam[3]))
    following = registers(by_id(case, "after-natural")["response"])
    assert all(following[key] == value for key, value in expected.items())
    setup = by_id(case, "any-raster")
    assert setup["command"] == "break exec 0000 ffff if RL == $10b"
    assert "BREAK:" in setup["response"]
    return dict(observed=expected, compared_fields=list(expected),
                subsequent_registers=following, any_original_instruction_condition=setup["command"])


def summary(case):
    return dict(name=case["name"], files=case["files"], session=case["session"],
                byte_streams={kind: dict(bytes=len(data), sha256=sha(data)) for kind, data in case["wire"].items()},
                event_count=len(case["events"]), ordinary_commands=len(case["queued"]) - len(case["cancelled"]),
                completed_responses=sum(row["status"] == "completed" for row in case["responses"].values()),
                interrupted_responses=sum(row["status"] == "interrupted" for row in case["responses"].values()),
                partial_responses=len(case["partial"]), waiting_notices=len(case["waits"]),
                cancelled_commands=[case["queued"][sequence] for sequence in sorted(case["cancelled"])],
                one_owned_process_and_endpoint=True, complete_byte_ranges=True,
                command_serialization_checked=True, ordinary_resends=0, restarts=0)


def main():
    source, frozen = ROOT / "research/vice_session_live.py", ROOT / "research/vice_session.py"
    assert sha(source.read_bytes()) == LIVE_SHA and sha(frozen.read_bytes()) == FROZEN_SHA
    rejected_files = pinned_case("rejected-utc-collision")
    failure = json.loads((BASE / "rejected-utc-collision/failure.json").read_text())
    assert failure["source_sha256"] == REJECTED_SHA
    assert sha((BASE / "rejected-utc-collision/vice_session_live.py").read_bytes()) == REJECTED_SHA
    failed, live, traced = [audit_session(name) for name in ("interrupt-01", "interrupt-02", "trace-01")]
    try:
        interruption(failed, "unbounded", "input")
    except AssertionError as error:
        assert str(error) == "No interrupt r on original wire"
        rejected_contract_reason = str(error)
    else:
        raise AssertionError("Pre-fix actual interruption unexpectedly passed")
    assert failed["wire"]["sent"] == b"r\nsidefx off\nx\n"
    rejected = [row for row in failed["events"] if row["kind"] == "input_rejected"]
    assert len(rejected) == 1 and "dict() got multiple values for keyword argument 'utc'" in rejected[0]["error"]
    interrupted = interruption(live, "unbounded", "input")
    after_interrupt = registers(by_id(live, "after-interrupt")["response"])
    assert interrupted == after_interrupt
    natural = natural_stop(live)
    pending_close = interruption(live, "pending-close", "close")
    assert [live["queued"][sequence]["id"] for sequence in live["cancelled"]] == ["cancel-on-close"]
    assert not live["partial"]
    traced_state = interruption(traced, "partial-trace", "input")
    pending = json.loads((BASE / "trace-01/pending-wire-check.json").read_text())
    prefix = (BASE / "trace-01/pending-received-prefix.bin").read_bytes()
    assert pending["pass"] and pending["pending_id"] == "partial-trace"
    assert len(prefix) == pending["received_prefix_bytes"] == 4711018
    assert sha(prefix) == pending["received_prefix_sha256"]
    assert traced["wire"]["received"].startswith(prefix)
    response = by_id(traced, "partial-trace")
    assert response["interrupt"]["received_first"] == len(prefix)
    assert response["received_first"] == 178 and response["received_end"] > len(prefix)
    assert not PROMPT.search(prefix[178:]) and not REGISTERS.search(prefix[178:].decode())
    assert pending["completed_response_absent_at_observation"]
    assert pending["waiting_notice"] in traced["waits"]
    assert b"(Trace  exec fd75)" in prefix and not traced["partial"]
    assert len({case["session"]["pid"] for case in (failed, live, traced)}) == 3
    assert len({case["session"]["port"] for case in (failed, live, traced)}) == 3
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()), live_observer=artifact(source),
                  frozen_sequential_observer=artifact(frozen), documentation=artifact(ROOT / "docs/research/vice-live-observer.md"),
                  scope="Passive real JSON/wire/lifecycle contract verification; no emulator or process started.",
                  test_value=dict(contract="Pending command interruption, stream ownership, queue cancellation and owned closure at the real monitor boundary.",
                                  credible_regression="Retained pre-fix UTC collision prevents interrupt r from reaching the wire.",
                                  distinct_boundary="Sequential capture audits cannot exercise stdin during pending x or incremental output persistence.",
                                  production_test_seams=[]),
                  successful_cases=[summary(live), summary(traced)],
                  rejected_baseline=dict(files=rejected_files, case=summary(failed),
                                         contract_rejection=rejected_contract_reason, no_interrupt_r_sent=True),
                  interrupted_then_registers=dict(interrupted=interrupted, subsequent=after_interrupt, identical=True),
                  natural_any_PC_raster_stop=natural, pending_close_drained_registers=pending_close,
                  pending_trace=dict(preserved_prefix=artifact(BASE / "trace-01/pending-received-prefix.bin"),
                                     pending_owner_observation=artifact(BASE / "trace-01/pending-wire-check.json"),
                                     prefix_is_exact_final_received_prefix=True, interrupted_registers=traced_state,
                                     bytes_persisted_before_completed_response=len(prefix)),
                  limits=["The sessions prove these retained real interactions, not every possible transport race or command.",
                          "The natural-stop and interrupt cases are separate; no forced simultaneous natural-stop/interrupt race is claimed.",
                          "Trace FD75 produced a persisted pending prefix; tracing was not continuous at cancellation, so no such coverage is claimed.",
                          "Session metadata certifies recorded owned VICE exit/reaping; it does not store the helper process exit code.",
                          "Register equality is not complete RAM/device-state equality; no native snapshots belong to these helper tests.",
                          "These reset-machine monitor tests do not prove Dragonbond artwork or whole-demo timing.",
                          "No forced send failure, hard host kill, power-loss durability or unrelated-process cleanup behavior is claimed."])
    result["pass"] = result.pop("pass_")
    OUTPUT.mkdir(parents=True, exist_ok=True)
    target = OUTPUT / "verification.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pass": result["pass"], "successful_cases": 2, "retained_rejected_case": 1,
                      "preserved_pending_bytes": len(prefix), "receipt": artifact(target)}, indent=2))


if __name__ == "__main__":
    main()
