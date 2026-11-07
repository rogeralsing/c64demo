#!/usr/bin/env python3
"""Check Quondam's captured VIC row reuse without running the demo or VICE.

The original native-02 monitor transcript and full snapshots are inputs.
Rejected observations remain in the transcript and are explicitly identified.
"""

import hashlib
import json
from pathlib import Path
import re
import tarfile

from snapshot_state import compare_modules, module_payload, read_snapshot

ROOT = Path(__file__).resolve().parents[2]
CAPTURES = ROOT / "build/research/quondam/native-02"
ORIGINAL_SHA256 = "e86e4bcf40e859f4ec3fcc83a86f8f0c172b6efa0a38d8dc199a85717fddc17c"
MEMORY_WRITER_SHA256 = "12058072799a1b0c8d46df7d978a8051bf4d6ef5e7fb26921ac82cd94ed2e149"
TRACE = re.compile(
    r"^#(?P<checkpoint>\d+) \(Trace store d011\)\s+"
    r"(?P<line>\d+)/\$[0-9a-f]+,\s+(?P<cycle>\d+)/\$[0-9a-f]+\n"
    r"\.C:(?P<pc>[0-9a-f]+)\s+[^\n]*?"
    r"- A:(?P<a>[0-9a-f]+) X:(?P<x>[0-9a-f]+) Y:(?P<y>[0-9a-f]+) "
    r"SP:(?P<sp>[0-9a-f]+) [^\n]*?\s+(?P<clock>\d+)\n",
    re.MULTILINE | re.IGNORECASE,
)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def traces(text, checkpoint):
    result = []
    for match in TRACE.finditer(text):
        fields = match.groupdict()
        if int(fields.pop("checkpoint")) != checkpoint:
            continue
        row = {key: int(value, 16 if key in ("pc", "a", "x", "y", "sp") else 10)
               for key, value in fields.items()}
        row["written_value"] = row["x"] if row["pc"] == 0x910F else row["a"]
        result.append(row)
    return result


def clock(path):
    assert read_snapshot(path)["modules"]["MAINCPU"]["version"] == [1, 4]
    return int.from_bytes(module_payload(path, "MAINCPU")[:8], "little")


def physical_ram(path):
    metadata = read_snapshot(path)["modules"]["C64MEM"]
    assert metadata["version"] == [0, 1] and metadata["payload_size"] == 65555
    # Exact 3.10 c64memsnapshot.c writes four port/cartridge bytes, all RAM,
    # then fifteen further port-state bytes. No bytes are silently excluded.
    return module_payload(path, "C64MEM")[4:65540]


def pin_memory_writer():
    directory = ROOT / "build/research/quondam/hardware-source"
    archive = directory / "vice-3.10.tar.gz"
    from snapshot_state import SOURCE_ARCHIVE_SHA256
    assert digest(archive) == SOURCE_ARCHIVE_SHA256
    member = "vice-3.10/src/c64/c64memsnapshot.c"
    with tarfile.open(archive, "r:gz") as source:
        data = source.extractfile(member).read()
    assert hashlib.sha256(data).hexdigest() == MEMORY_WRITER_SHA256
    destination = directory / member
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(data)
    return {"member": member, "sha256": MEMORY_WRITER_SHA256,
            "writer_lines": [180, 197], "reader_lines": [216, 230],
            "module_version": [0, 1], "ram_payload_slice": [4, 65540]}


def snapshot_row(path):
    state = read_snapshot(path)
    vic = state["vicii"]
    assert vic["model"] == 1
    assert len(vic["color_ram"]) == 1024 and set(vic["color_ram"]) == {8}
    return {
        "file": path.name, "sha256": state["file_sha256"], "clock": clock(path),
        "raster_line": vic["raster_line"], "raster_cycle": vic["raster_cycle"],
        "rc": vic["rc"], "vcbase": vic["vcbase"], "vc": vic["vc"],
        "vmli": vic["vmli"], "idle_state": vic["idle_state"],
        "bad_line": vic["bad_line"], "vbuf": vic["vbuf"], "cbuf": vic["cbuf"],
        "vic_model": vic["model"], "color_ram_values": sorted(set(vic["color_ram"])),
        "color_ram_sha256": hashlib.sha256(bytes(vic["color_ram"])).hexdigest(),
        "d011": vic["regs"][0x11], "d018": vic["regs"][0x18],
        "palette": [value & 15 for value in vic["regs"][0x21:0x24]],
        "cia2_port_latch": state["cia"]["CIA2"]["pra"],
        "cia2_direction": state["cia"]["CIA2"]["ddra"],
    }


def check_control(first, second, expected_alarm_values):
    a, b = CAPTURES / first, CAPTURES / second
    comparison = compare_modules(a, b)
    differences = comparison["different_modules"]
    assert len(differences) == 1 and differences[0]["module"] == "CIA1"
    assert differences[0]["differences"] == [{
        "payload_offset": 33,
        "first": expected_alarm_values[0] & 255,
        "second": expected_alarm_values[1] & 255,
    }]
    states = [read_snapshot(path) for path in (a, b)]
    alarms = [state["cia"]["CIA1"]["relative_tod_alarm_cycles"] for state in states]
    assert alarms == expected_alarm_values
    assert all(state["cia"]["CIA1"]["tod_stopped"] for state in states)
    assert module_payload(a, "MAINCPU") == module_payload(b, "MAINCPU")
    assert module_payload(a, "C64MEM") == module_payload(b, "C64MEM")
    assert module_payload(a, "VIC-II") == module_payload(b, "VIC-II")
    comparison.update(
        clocks=[clock(a), clock(b)], relative_tod_alarm_cycles=alarms,
        tod_stopped=True,
        interpretation="CPU, RAM and complete VIC module agree. The active TOD alarm phase differs; whole-machine equality is not claimed.",
    )
    return comparison


def main():
    original = ROOT / "build/research/quondam/quondam-tunneling.prg"
    assert digest(original) == ORIGINAL_SHA256
    memory_writer = pin_memory_writer()
    transcript = (CAPTURES / "monitor.log").read_text()
    # Trace 2 is the anomalous first trial. Trace 3 has no automatic command;
    # traces 8 and 9 are later constant-print and I/O-command control trials.
    plain = traces(transcript, 3)
    assert len(plain) == 51
    assert traces(transcript, 8) == plain
    assert traces(transcript, 9) == plain
    late = [row for row in plain if row["pc"] == 0x9322]
    alternate = [row for row in plain if row["pc"] == 0x936F]
    assert len(late) == len(alternate) == 24
    assert [row["line"] for row in late] == list(range(55, 240, 8))
    assert [row["line"] for row in alternate] == list(range(59, 244, 8))
    assert {row["cycle"] for row in late} == {54}
    assert {row["written_value"] for row in late} == {0x1F}
    assert {row["written_value"] for row in alternate} == {0x18}
    assert all(b["clock"] - a["clock"] == 504 for a, b in zip(late, late[1:]))

    initial = snapshot_row(CAPTURES / "initial-row-fetch.vsf")
    assert (initial["raster_line"], initial["raster_cycle"], initial["rc"], initial["vcbase"]) == (50, 10, 1, 0)
    expected_codes = list(range(0x4C, 0x74))
    assert initial["vbuf"] == expected_codes and initial["cbuf"] == [8] * 40
    raw_control = (CAPTURES / "ram-after-untraced.bin").read_bytes()
    assert len(raw_control) == 65536
    assert physical_ram(CAPTURES / "after-untraced.vsf") == raw_control
    initial_ram = physical_ram(CAPTURES / "initial-row-fetch.vsf")
    assert initial_ram[0x7000:0x7028] == bytes(expected_codes)
    assert initial_ram[0x7028:0x7050] == bytes(24) + bytes([0xAA]) * 16
    assert initial_ram[0x7000:0x7028] != initial_ram[0x7028:0x7050]
    before = snapshot_row(CAPTURES / "before-late-write.vsf")
    wrapped = snapshot_row(CAPTURES / "after-late-wrap.vsf")
    assert (before["raster_line"], before["raster_cycle"], before["rc"], before["vcbase"]) == (56, 50, 7, 0)
    assert (wrapped["raster_line"], wrapped["raster_cycle"], wrapped["rc"], wrapped["vcbase"]) == (56, 60, 0, 40)
    assert wrapped["bad_line"] == 1 and wrapped["idle_state"] == 0
    assert before["vbuf"] == wrapped["vbuf"] == expected_codes
    assert before["cbuf"] == wrapped["cbuf"] == [8] * 40

    windows = []
    for index in range(24):
        row = snapshot_row(CAPTURES / f"after-window-{index+1:02d}.vsf")
        assert row["raster_line"] == 57 + 8 * index
        assert row["raster_cycle"] == ([1] * 5 + [12] * 7 + [1] + [8] * 3 + [1] * 8)[index]
        assert row["clock"] == 15413896 + 504 * index + row["raster_cycle"] - 1
        assert row["rc"] == 0 and row["idle_state"] == 0
        assert row["vcbase"] == row["vc"] == 40 * (index + 1)
        assert row["vbuf"] == expected_codes and row["cbuf"] == [8] * 40
        bank = (row["cia2_direction"] & 3) * 0x4000
        assert row["cia2_port_latch"] & 3 == 0
        row["charset_address"] = bank + ((row["d018"] & 14) << 10)
        row["screen_address"] = bank + ((row["d018"] >> 4) << 10)
        windows.append(row)
    # Each charset is reused for two eight-row bands with different palette
    # interpretations. The cache retains its codes even when the bank changes.
    for index in range(0, 24, 2):
        a, b = windows[index:index+2]
        assert a["charset_address"] == b["charset_address"]
        assert a["palette"] == ([14, 0, 12] if (index // 2) % 2 == 0 else [14, 12, 0])
        assert b["palette"] == [a["palette"][0], a["palette"][2], a["palette"][1]]

    controls = [
        check_control("after-plain-trace.vsf", "after-untraced.vsf", [4235, 4233]),
        check_control("after-instrumented-frame.vsf", "after-control-frame.vsf", [4281, 4282]),
    ]
    assert controls[0]["clocks"] == [15406479, 15406479]
    assert controls[1]["clocks"] == [15426135, 15426135]
    session = json.loads((CAPTURES / "session.json").read_text())
    assert "closed_utc" in session
    receipt = {
        "original_sha256": ORIGINAL_SHA256,
        "script_sha256": digest(Path(__file__)),
        "snapshot_parser_sha256": digest(Path(__file__).with_name("snapshot_state.py")),
        "transcript_sha256": digest(CAPTURES / "monitor.log"),
        "method": "Original PAL program; full original snapshot restores; native breakpoints, stepping and passive I/O observations. No program/PC patches.",
        "cycle_numbering": "VICE zero-based raster-cycle counter; 54 corresponds to hardware cycle 55 in Bauer's one-based tables.",
        "plain_trace": plain, "late_store_count": len(late),
        "alternate_store_cycle_range": [min(row["cycle"] for row in alternate), max(row["cycle"] for row in alternate)],
        "constant_print_recheck_equal": True, "io_action_recheck_equal": True,
        "initial_fetch": initial, "before_late_write": before,
        "screen_matrix_discrimination": {
            "schema": memory_writer,
            "snapshot_ram_matches_all_65536_raw_control_bytes": True,
            "initial_fetch_ram_sha256": hashlib.sha256(initial_ram).hexdigest(),
            "initial_screen_address": 0x7000,
            "first_matrix_row": list(initial_ram[0x7000:0x7028]),
            "second_matrix_row": list(initial_ram[0x7028:0x7050]),
            "interpretation": "Cached codes match the first matrix row; the next row is different. Buffer equality is not explained by identical rows in matrix RAM.",
        },
        "after_row_wrap": wrapped, "windows": windows, "controls": controls,
        "rejected_observations": [
            {"trial": "first tracepoint-2 automatic I/O action", "observed": "Only one D011 store before an unexpected BRK-like main entry at raster255. Later identical I/O-action trial completed normally; cause remains unresolved.", "used_for_display_proof": False},
            {"trial": "raster49/cycle>=54 conditional wait", "observed": "No instruction checkpoint hit before observation timeout; r interrupted the same live process. Subsequent mislabeled snapshots preserved as attempt-timeout-initial-row-fetch.vsf and attempt-timeout-after-window-01.vsf.", "used_for_display_proof": False},
        ],
        "scope": "One complete sampled frame retains the same 40 cached screen codes through 24 late row wraps, while charset/palette selection changes. Complete VIC endpoint payload equals the uninstrumented control. No full independent pixel/3D-asset oracle or all-pose timing claim.",
        "session_closed_utc": session["closed_utc"],
    }
    destination = CAPTURES / "raster-evidence.json"
    destination.write_text(json.dumps(receipt, indent=2) + "\n")
    print(f"PASS: {len(plain)} D011 writes; 24 cached-row wraps; CPU/RAM/VIC controls agree; TOD phase differences retained.")
    print(destination.relative_to(ROOT))


if __name__ == "__main__":
    main()
