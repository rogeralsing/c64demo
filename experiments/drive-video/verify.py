#!/usr/bin/env python3
"""Check our real 1541 upload, VIA signal, timer coupling and live field cycle."""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import shutil
import socket
import subprocess
import time
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUTPUT = HERE / "build/verification"
TRACE = re.compile(r"#\d+ \(Trace\s+(load|store) ([0-9a-fA-F]{4})\).*?"
                   r"\.8:([0-9a-fA-F]{4})[^\n]*?- A:([0-9a-fA-F]{2}) "
                   r"X:([0-9a-fA-F]{2}) Y:([0-9a-fA-F]{2})[^\n]*?\s(\d+)\n", re.S)


def registers(monitor):
    text = monitor.run("registers")
    match = re.search(r"^\.;([0-9a-fA-F]{4})\s+(.*)$", text, re.M)
    if not match:
        raise AssertionError("Missing native drive registers")
    return int(match[1], 16), int(match[2].split()[-1])


def events(text):
    return [{"kind": kind, "address": int(address, 16), "pc": int(pc, 16),
             "value": int(a, 16), "x": int(x, 16), "y": int(y, 16), "clock": int(clock)}
            for kind, address, pc, a, x, y, clock in TRACE.findall(text)]


def reference(phase, y, column):
    if column == 0:
        return 0 if (y + phase) % 256 // 16 % 2 == 0 else 2
    if column == 1:
        return 0 if (((y + phase) % 256 + 8) // 16) % 2 == 0 else 2
    v = (y + phase) % 256
    return 0 if (((v + 16) // 16) + v // 64) % 2 == 0 else 2


def signal_check(records, phase, labels):
    start = labels["visibleLines"]
    end = labels["blankLines"]
    visible = [r for r in records if start <= r["pc"] < end]
    writes = [r for r in visible if r["kind"] == "store" and r["address"] == 0x1800]
    reads = [r for r in visible if r["kind"] == "load" and r["address"] == 0x1800]
    motors = [r for r in visible if r["kind"] == "store" and r["address"] == 0x1c00]
    assert len(writes) == 256 * 6, len(writes)
    assert len(reads) == len(motors) == 256
    image = Image.new("RGB", (512, 256), "black")
    decoded = []
    for y in range(256):
        row = writes[6*y:6*y+6]
        expected = [8, 2] + [reference(phase, y, c) for c in range(3)] + [2]
        assert [r["value"] for r in row] == expected, (phase, y, row, expected)
        assert [r["clock"] - row[0]["clock"] for r in row] == [0, 6, 20, 28, 36, 42]
        assert row[0]["y"] == (y + phase) % 256
        if y:
            assert row[0]["clock"] - writes[6*(y-1)]["clock"] == 64
        assert motors[y]["value"] == 0x64 + (reads[y]["value"] >> 7)
        assert motors[y]["clock"] - reads[y]["clock"] == 20
        for c in range(3):
            value = row[c+2]["value"]
            # VIA output latches are inverted at the IEC pins. DATA low/CLK
            # high gives black; both high gives white with DATA-resistor wiring.
            rgb = (255, 255, 255) if value == 0 else (0, 0, 0)
            for x in range((20+c*8)*8, (28+c*8)*8):
                image.putpixel((x, y), rgb)
            decoded.append(value)
    all_reads = [r for r in records if r["kind"] == "load" and r["address"] == 0x1800]
    all_motors = [r for r in records if r["kind"] == "store" and r["address"] == 0x1c00]
    assert len(all_reads) == len(all_motors)
    for read, motor in zip(all_reads, all_motors):
        assert motor["value"] == 0x64 + (read["value"] >> 7)
        assert 0 <= motor["clock"] - read["clock"] <= 20
    vsync = [r for r in records if labels["verticalSync"] <= r["pc"] < labels["noteLo"]
             and r["kind"] == "store" and r["address"] == 0x1800]
    # STY writes are recorded with A by the parser; here Y is the actual value.
    assert len(vsync) == 20
    for i in range(10):
        assert vsync[2*i]["value"] == 8 and vsync[2*i+1]["y"] == 2
        assert vsync[2*i+1]["clock"] - vsync[2*i]["clock"] == 28
        if i:
            assert vsync[2*i]["clock"] - vsync[2*i-2]["clock"] == 32
    assert {r["value"] for r in motors} == {0x64, 0x65}
    transitions = [reads[i]["clock"] for i in range(1, len(reads))
                   if (reads[i]["value"] ^ reads[i-1]["value"]) & 128]
    return image, {"phase": phase, "visible_rows": 256, "native_port_records": len(records),
                   "visible_sync_period": 64, "sync_width": 6, "column_width": 8,
                   "timer_sample_transitions": transitions,
                   "decoded_columns_sha256": hashlib.sha256(bytes(decoded)).hexdigest()}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "verification.json").unlink(missing_ok=True)
    spec = importlib.util.spec_from_file_location("native_common", ROOT / "verify.py")
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    common.PROMPT = re.compile(rb"\((?:C|8|9|10|11):\$[0-9a-fA-F]{4}\) $")
    host_labels = common.read_labels(HERE / "build/main.sym")
    drive_labels = common.read_labels(HERE / "drive/build/main.sym")
    program = HERE / "build/example.prg"
    payload = (HERE / "drive/build/example.prg").read_bytes()
    assert payload[:2] == b"\x00\x03" and len(payload[2:]) == 1280
    palette = ROOT / "palettes/colodore.vpl"
    assert palette.is_file()
    with socket.socket() as reserve:
        reserve.bind(("127.0.0.1", 0))
        port = reserve.getsockname()[1]
    command = common.vice_command(shutil.which("x64sc"), program, port, palette)
    command += ["-drive8type", "1541", "-drive8truedrive", "+trapdevice8", "-drive8idle", "0",
                "-limitcycles", "20000000"]
    samples, checked, pictures, monitor = [], [], [], None
    process = None
    try:
        with (OUTPUT / "vice.log").open("w") as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True)
            with common.connect_monitor(process, port) as connection:
                monitor = common.Monitor(connection)
                connection.settimeout(45)
                monitor.run("r")
                monitor.run(f"break {host_labels['driveRunning']:04x}")
                monitor.run(f"break {host_labels['faultIdle']:04x}")
                monitor.run("x")
                assert monitor.registers()[0] == host_labels["driveRunning"]
                monitor.run("disable 1")
                monitor.run("disable 2")
                cia = monitor.memory(OUTPUT / "host-cia2.bin", 0xdd00, 0xdd02)
                assert cia[0] & 0x38 == 0
                monitor.run("device 8:")
                monitor.run("sidefx off")
                assert monitor.memory(OUTPUT / "uploaded-payload.bin", 0x300, 0x7ff) == payload[2:]
                monitor.run(f"break {drive_labels['frameStart']:04x}")
                monitor.run("x")
                trace_ids = []
                for command in ["trace load 1800", "trace store 1800", "trace store 1c00"]:
                    trace_ids.append(int(re.search(r"TRACE:\s*(\d+)", monitor.run(command))[1]))
                for n in trace_ids:
                    monitor.run(f"disable {n}")
                selected = {0, 14, 15, 62, 63, 64, 126, 127, 128, 190, 191, 192, 254, 255, 256, 257}
                for index in range(258):
                    pc, clock = registers(monitor)
                    assert pc == drive_labels["frameStart"]
                    old_phase = monitor.memory(OUTPUT / "counter.bin", 0x2f0, 0x2f0)[0]
                    if index:
                        assert old_phase == (samples[-1]["old_phase"] + 1) % 256
                    if index in selected:
                        for n in trace_ids:
                            monitor.run(f"enable {n}")
                    response = monitor.run("x")
                    _, next_clock = registers(monitor)
                    phase = (old_phase + 1) % 256
                    via1 = monitor.memory(OUTPUT / "via1.bin", 0x1800, 0x180f)
                    via2 = monitor.memory(OUTPUT / "via2.bin", 0x1c00, 0x1c0f)
                    assert via1[2] == 0x1a and via1[11] == 0xc0
                    assert via2[2] == 0x6f and via2[11] == 0
                    note = [0x046e, 0x03f0, 0x0354, 0x02f0][phase // 64]
                    assert via1[6] + 256*via1[7] == note
                    samples.append({"index": index, "old_phase": old_phase, "phase": phase,
                                    "drive_clock": clock, "field_clocks": next_clock-clock,
                                    "timer_reload": note})
                    if index in selected:
                        (OUTPUT / f"field-{index:03d}-trace.txt").write_text(response)
                        records = events(response)
                        picture, proof = signal_check(records, phase, drive_labels)
                        picture.save(OUTPUT / f"field-{index:03d}.png")
                        pictures.append(picture)
                        checked.append(proof)
                        for n in trace_ids:
                            monitor.run(f"disable {n}")
                assert {r["old_phase"] for r in samples} == set(range(256))
                assert len({r["decoded_columns_sha256"] for r in checked}) >= 8
                assert max(r["field_clocks"] for r in samples) < 20100
                connection.sendall(b"quit\n")
                process.wait(timeout=5)
        common.save_animation(pictures, OUTPUT / "drive-signal.gif", 100)
    finally:
        if monitor:
            (OUTPUT / "monitor.txt").write_text("\n".join(monitor.transcript))
        if process and process.poll() is None:
            process.terminate()
        if process:
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    assert process.returncode == 0
    proof = {"passed": True, "program_sha256": hashlib.sha256(program.read_bytes()).hexdigest(),
             "payload_sha256": hashlib.sha256(payload).hexdigest(), "upload_bytes": 1280,
             "fields": samples, "signal_checks": checked,
             "limitations": ["Digital IEC/VIA output only; no analog resistor/monitor model",
                             "No physical drive sound or head mechanics measurement",
                             "Field handovers are explicit timing gaps; not full PAL compliance"],
             "vice_exit_code": process.returncode}
    (OUTPUT / "verification.json").write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"passed": True, "fields": len(samples), "signal_fields": len(checked),
                      "field_clocks": sorted({r["field_clocks"] for r in samples}),
                      "sha256": proof["program_sha256"]}))


if __name__ == "__main__":
    main()
