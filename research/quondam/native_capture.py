#!/usr/bin/env python3
"""Analyze existing original-Quondam native captures; never control a process."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

from PIL import Image

REPO = Path(__file__).resolve().parents[2]
BASE = REPO/"build/research/quondam"
PAL_CYCLES, LINE_CYCLES = 19656, 63
REGISTER = re.compile(
    r"^\.;([0-9a-f]{4})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+"
    r"([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([01]{8})\s+(\d+)\s+(\d+)\s+(\d+)", re.I)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def parse_monitor(text):
    bank, requested = "cpu", None
    context = {"registers": None, "io": {}}
    captures, screenshots, registers = {}, {}, []
    seen = set()
    for source_line in text.splitlines():
        line = source_line.strip()
        if line == "x":
            context = {"registers": None, "io": {}}
            requested = None
        if line.startswith("bank "):
            bank = line.split()[1]
            requested = None
        match = REGISTER.match(line)
        if match:
            fields = match.groups()
            record = dict(zip(("pc", "a", "x", "y", "sp", "port00", "port01"),
                              (int(value, 16) for value in fields[:7])))
            record.update(flags=int(fields[7], 2), raster_line=int(fields[8]),
                          raster_cycle=int(fields[9]), stopwatch=int(fields[10]))
            context["registers"] = record
            key = record["pc"], record["stopwatch"]
            if key not in seen:
                registers.append(record)
                seen.add(key)
        match = re.fullmatch(r"m ([0-9a-f]+) ([0-9a-f]+)", line, re.I)
        if match:
            requested = (int(match[1], 16), int(match[2], 16), bank)
        match = re.match(r">C:([0-9a-f]{4})\s+(.*)", line, re.I)
        if match and requested:
            address = int(match[1], 16)
            count = min(16, requested[1]-address+1)
            tokens = match[2].split()[:count]
            if requested[0] <= address <= requested[1] and requested[2] == "io":
                assert len(tokens) == count and all(re.fullmatch(r"[0-9a-f]{2}", t, re.I) for t in tokens)
                context["io"].update((address+i, int(t, 16)) for i, t in enumerate(tokens))
        for command, destination in (("bsave", captures), ("screenshot", screenshots)):
            match = re.match(command+r' "([^"]+)"', line)
            if match:
                destination[Path(match[1]).name] = deepcopy(context)
    return captures, screenshots, registers


def clock_position(registers):
    return registers["raster_line"]*LINE_CYCLES+registers["raster_cycle"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, default=BASE/"native-01")
    args = parser.parse_args()
    directory = args.capture
    log_path = directory/"monitor.log"
    text = log_path.read_text(errors="replace")
    contexts, screenshot_contexts, register_samples = parse_monitor(text)
    mapping = json.loads((BASE/"release-map.json").read_text())
    helper = json.loads((BASE/"quondam-window-proof.json").read_text())
    original = (BASE/"quondam-unpacked-ram.bin").read_bytes()
    assert sha(original) == mapping["unpacked_ram_sha256"]
    assert sha((BASE/"quondam-tunneling.prg").read_bytes()) == mapping["program_sha256"]
    session = json.loads((directory/"session.json").read_text())
    assert session.get("closed_utc"), "Analyze the final closed session, not a partial log."
    inputs = [log_path, directory/"session.json", BASE/"release-map.json", BASE/"quondam-window-proof.json",
              BASE/"quondam-unpacked-ram.bin", BASE/"quondam-tunneling.prg"]

    def ram(filename):
        path = directory/filename
        data = path.read_bytes()
        assert len(data) == 65536
        inputs.append(path)
        return data

    before = ram("ram-before-init.bin")
    preinit = []
    for region in mapping["preinitialization_regions"]:
        first, end = region["start"], region["end_exclusive"]
        actual, expected = before[first:end], original[first:end]
        assert actual == expected, (region["file"], "native original code mismatch")
        preinit.append({"file": region["file"], "start": first, "end_exclusive": end,
                        "bytes": len(actual), "sha256": sha(actual), "match": True})

    charset_checks = []
    for filename in ("ram-initialized.bin", "ram-display-032.bin", "ram-display-096.bin"):
        data = ram(filename)
        entries = []
        for entry in mapping["memory_selection_table"]:
            first = entry["charset"]
            actual = sha(data[first:first+2048])
            assert actual == entry["prepared_charset_sha256"], (filename, entry["index"], first)
            entries.append({"table_index": entry["index"], "charset": first,
                            "bytes": 2048, "sha256": actual, "match": True})
        charset_checks.append({"capture": filename, "entries": entries,
                               "bytes_compared": 18*2048, "all_match": True})

    windows = []
    for number in (1, 2, 3):
        filename = f"ram-window-{number:02d}.bin"
        data = ram(filename)
        context = contexts[filename]
        registers, io = context["registers"], context["io"]
        assert registers["pc"] == 0x932D and registers["port01"] == 0x35
        phase = data[0x11]
        expected = helper["cases"][phase]
        assert expected["phase"] == phase
        assert data[0x9325:0x932D] == bytes.fromhex(expected["patched_window"])
        assert (data[0x931F], data[0x9326]) == (expected["ldx"], expected["lda"])
        assert (registers["x"], registers["a"]) == (expected["ldx"], expected["lda"])
        memory_phase = phase if phase%2 == 0 else phase-1
        memory = mapping["memory_selection_table"][memory_phase//2]
        palette_phase = phase if phase%2 else phase-1
        palette = helper["cases"][palette_phase]
        assert io[0xD018]&0xFE == memory["d018"]
        assert io[0xDD02] == memory["dd02"]
        actual_bank = ((~io[0xDD00])&3)*0x4000
        assert actual_bank == memory["expected_vic_bank"]
        actual_globals = [io[address]&15 for address in (0xD021, 0xD022, 0xD023)]
        assert actual_globals == [14, palette["ldx"], palette["lda"]]
        assert io[0xD011]&0x7F == data[0x9321]
        assert io[0xD011]&0x60 == 0 and io[0xD016]&0x10 and not io[0xD016]&8
        assert io[0xD012] == registers["raster_line"]&255
        assert registers["stopwatch"]%PAL_CYCLES == clock_position(registers)
        windows.append({"capture": filename, "registers": registers, "band_phase": phase,
                        "motion_bytes_12_13_14": list(data[0x12:0x15]),
                        "mode": expected["mode"], "patched_window_hex": data[0x9325:0x932D].hex(" "),
                        "io_raw": {f"{a:04x}": io[a] for a in (0xD011,0xD012,0xD016,0xD018,0xD021,0xD022,0xD023,0xDD00,0xDD02)},
                        "io_d018_normalized": io[0xD018]&0xFE, "actual_vic_bank_from_pins": actual_bank,
                        "screen": memory["screen"], "charset": memory["charset"],
                        "global_palette_low_nibbles": actual_globals,
                        "color_ram_directly_sampled": False,
                        "selector3_black_basis": "Original initialization writes Color RAM08; source inference, not direct IO sample"})
    assert [w["band_phase"] for w in windows] == [7,8,9]
    assert len({tuple(w["motion_bytes_12_13_14"]) for w in windows}) == 1
    intervals = []
    for first, last in zip(windows, windows[1:]):
        a, b = first["registers"], last["registers"]
        delta = b["stopwatch"]-a["stopwatch"]
        assert delta == 8*LINE_CYCLES and a["raster_cycle"] == b["raster_cycle"]
        intervals.append({"cycles": delta, "pal_raster_lines": 8, "same_pc": 0x932D,
                          "same_raster_cycle": a["raster_cycle"]})

    alternate = contexts["ram-alternate-irq.bin"]
    ram("ram-alternate-irq.bin")
    assert alternate["registers"]["pc"] == 0x935C
    alternate = {"registers": alternate["registers"], "d011_before_handler_exec": alternate["io"][0xD011],
                 "cycles_since_prior_window": alternate["registers"]["stopwatch"]-windows[-1]["registers"]["stopwatch"],
                 "scope": "Different PCs: this 202-cycle gap is not a four-line handler period"}

    frame_irqs = [r for r in register_samples if r["pc"] == 0x9129]
    assert len(frame_irqs) >= 5 and all(r["raster_line"] == 251 for r in frame_irqs)
    reference = frame_irqs[0]
    cadence = []
    for first, last in zip(frame_irqs, frame_irqs[1:]):
        raw_delta = last["stopwatch"]-first["stopwatch"]
        phase_delta = clock_position(last)-clock_position(first)
        assert (raw_delta-phase_delta)%PAL_CYCLES == 0
        cadence.append({"raw_cycles": raw_delta, "observed_raster_position_delta_cycles": phase_delta,
                        "pal_frame_intervals": (raw_delta-phase_delta)//PAL_CYCLES})
    screenshots = []
    for filename, expected_elapsed in (("tunnel-native-032.png",32),("tunnel-native-096.png",96)):
        context = screenshot_contexts[filename]
        registers = context["registers"]
        delta = registers["stopwatch"]-reference["stopwatch"]
        phase = clock_position(registers)-clock_position(reference)
        assert delta-phase == expected_elapsed*PAL_CYCLES
        path = directory/filename
        inputs.append(path)
        with Image.open(path) as image:
            size = list(image.size)
        screenshots.append({"file":filename, "sha256":sha(path.read_bytes()), "pixels":size,
                            "registers":registers, "elapsed_pal_intervals_from_reference":expected_elapsed,
                            "irq_hit_number_from_reference_inclusive":expected_elapsed+1,
                            "scope":"Original native output observation; no same-time RAM pixel reconstruction"})

    result = {"pass":True, "program_sha256":mapping["program_sha256"],
        "scope":"Original native code/assets/register witnesses and sampled IRQ timing; no full display pixel oracle",
        "preinitialization":preinit, "prepared_charsets":charset_checks,
        "causal_windows":windows, "window_intervals":intervals, "alternate_irq_entry":alternate,
        "frame_irq_samples":frame_irqs, "frame_irq_intervals":cadence, "screenshots":screenshots,
        "session_reported_closed_utc":session["closed_utc"], "session_reported_exit_code":session["exit_code"],
        "monitor_side_effect_reads_disabled":"sidefx off" in text,
        "inputs":[{"file":str(p.relative_to(REPO)),"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())}
                  for p in dict.fromkeys(inputs)],
        "script_sha256":sha(Path(__file__).read_bytes())}
    (directory/"native-evidence.json").write_text(json.dumps(result,indent=2)+"\n")
    print(json.dumps({"pass":True,"charsets_per_capture":18,"charset_captures":len(charset_checks),
        "window_phases":[w["band_phase"] for w in windows],"window_intervals":intervals,
        "frame_irq_intervals":cadence,"screenshots":len(screenshots)},indent=2))


if __name__ == "__main__":
    main()
