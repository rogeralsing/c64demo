#!/usr/bin/env python3
"""Assemble unchanged teaching examples and exercise their original CPU code.

The synthetic D012 read sequence exercises polling/control flow only. It does
not model a VIC, time, interrupts, bus arbitration, border visibility or pixels.
The separate compositor calculation is an ideal model, not a release renderer.
"""

import hashlib
import importlib.metadata
import json
import os
import re
import subprocess
from collections import Counter
from itertools import product
from pathlib import Path

from py65.devices.mpu6502 import MPU


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/research/ghostbyte"
SOURCE_SHA256 = {
    "ghostbyte": "db28c561af70b1c83b42b9eabb5ecf8aef561dded5dbc418fe684ea6e57b1c62",
    "sprite": "64b26f7b2b9a284bda6d9b233817460cb39eb4b1a03476b042c06d4cfbf3d801",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


class SyntheticIO:
    """Flat RAM, recorded writes, and explicit low-byte samples on D012 reads."""

    def __init__(self, blob):
        self.data = bytearray(65536)
        load = int.from_bytes(blob[:2], "little")
        self.data[load:load + len(blob) - 2] = blob[2:]
        self.pc = None
        self.reads = []
        self.writes = []
        # The exact same low bytes could also be supplied by lines 2/258 etc.
        # Full-line annotations describe this test fixture, not sampled VIC data.
        self.samples = iter([247, 248, 257, 258] * 2)

    def __getitem__(self, address):
        if address == 0xD012:
            line = next(self.samples)
            value = line & 255
            self.reads.append({"pc": self.pc, "fixture_line": line, "value": value})
            return value
        return self.data[address]

    def __setitem__(self, address, value):
        self.data[address] = value
        self.writes.append({"pc": self.pc, "address": address, "value": value})


def assemble(name):
    source = OUTPUT / f"{name}.s"
    assert digest(source.read_bytes()) == SOURCE_SHA256[name]
    java = os.environ.get("JAVA", "/opt/homebrew/opt/openjdk/bin/java")
    jar = Path(os.environ.get("KICKASS_JAR", Path.home() / ".local/share/c64-tools/KickAssembler/KickAss.jar"))
    target = OUTPUT / f"{name}.prg"
    command = [java, "-jar", str(jar), str(source), "-o", str(target), "-symbolfile"]
    assembled = subprocess.run(command, cwd=OUTPUT, check=True, capture_output=True, text=True)
    (OUTPUT / f"{name}-assembly.log").write_text(assembled.stdout + assembled.stderr)
    symbols = {label: int(address, 16) for label, address in
               re.findall(r"\.label (\w+)=\$([0-9a-f]+)", source.with_suffix(".sym").read_text())}
    assert symbols["start"] == 0x080E
    return target.read_bytes(), symbols, {
        "source_sha256": digest(source.read_bytes()), "source_bytes": len(source.read_bytes()),
        "prg_sha256": digest(target.read_bytes()), "prg_bytes": target.stat().st_size,
        "command": command, "kickass_jar_sha256": digest(jar.read_bytes()), "symbols": symbols,
        "source_modified": False,
    }


def execute(name, blob, symbols):
    memory = SyntheticIO(blob)
    cpu = MPU(memory=memory, pc=symbols["start"])
    loops = steps = 0
    while steps < 1000:
        pc = cpu.pc
        assert symbols["start"] <= pc < symbols["openborder"] + 27, hex(pc)
        memory.pc = pc
        cpu.step()
        steps += 1
        if memory.data[pc] == 0x4C and cpu.pc == symbols["openborder"]:
            loops += 1
            if loops == 2:
                break
    assert loops == 2 and len(memory.reads) == 8
    d011 = [event["value"] for event in memory.writes if event["address"] == 0xD011]
    assert d011 == [0x13, 0x1B] * 2
    assert [(event["address"], event["value"]) for event in memory.writes[:2]] == [(0xDC0D, 0x7F), (0xDD0D, 0x7F)]
    assert memory.data[0x3FFF] == (1 if name == "ghostbyte" else 0)
    for absent in (0xD016, 0xD018, 0xD01B, 0xD01C, 0xD025, 0xD026, 0xDD00):
        assert not any(event["address"] == absent for event in memory.writes)
    result = {"pass": True, "entry": symbols["start"], "steps": steps,
              "completed_polling_loops": loops, "d012_reads": memory.reads,
              "write_events": memory.writes, "d011_values": d011,
              "ghostbyte_address": 0x3FFF, "ghostbyte_value": memory.data[0x3FFF],
              "fixture": "D012 returns F7,F8,01,02 twice, one sample per CPU read; no hardware clock drives it",
              "limitations": ["No VIC or CIA, no CPU-port banking, no DMA/BA, no interrupts or frame/pixel simulation",
                              "D012 alone exposes only eight raster bits; fixture line 258 is indistinguishable from line 2",
                              "Reset/BASIC hardware defaults are not validated by this flat-memory execution"]}
    if name == "sprite":
        assert memory.data[0xD015] == memory.data[0xD01D] == 255
        assert list(memory.data[0x7F8:0x800]) == [0x24] * 8
        assert memory.data[0xD010] == 0xC1
        assert list(memory.data[0xD001:0xD010:2]) == [255] * 8
        positions = [memory.data[0xD000 + 2 * i] + 256 * ((memory.data[0xD010] >> i) & 1) for i in range(8)]
        assert positions == [496, 40, 88, 136, 184, 232, 280, 328]
        result.update({"sprite_x_9bit": positions, "sprite_y": [255] * 8,
                       "sprite_pointers": [0x24] * 8,
                       "pointer_times_64": 0x900, "sprite_data_bytes": len(blob) - (0x900 - 0x801) - 2,
                       "enabled_and_xexpanded": 255,
                       "explicit_sprite_colour_change": {"sprite": 5, "colour": 8}})
        assert result["sprite_data_bytes"] == 64
    return result


def composite(ghost, codes):
    """Black=1/background=0; one expanded multicolor symbol spans four pixels.

    The diagnostic palette has transparent 00, black 01, background-colour 10
    and background-colour 11. This explicit palette models the three choices
    described by Trident, independently of hardware register assignments.
    """
    result = 0
    for cell, code in enumerate(codes):
        nibble = (ghost >> (4 * (1 - cell))) & 15
        value = nibble if code == 0 else 15 if code == 1 else 0
        result = (result << 4) | value
    return result


def compositor_proof():
    sizes = Counter()
    for ghost in range(256):
        outcomes = {composite(ghost, codes) for codes in product(range(4), repeat=2)}
        high, low = ghost >> 4, ghost & 15
        independently_expected = {(a << 4) | b for a in {0, 15, high} for b in {0, 15, low}}
        assert outcomes == independently_expected
        sizes[len(outcomes)] += 1
    examples = sorted({composite(0x81, codes) for codes in product(range(4), repeat=2)})
    assert sizes == {4: 4, 6: 56, 9: 196}
    assert len(examples) == 9 and 0x42 not in examples
    return {"pass": True, "ghostbytes_enumerated": 256, "sprite_code_pairs_per_ghostbyte": 16,
            "four_pixel_symbols": "transparent, black, background, background",
            "distinct_8pixel_outcomes_histogram": dict(sorted(sizes.items())),
            "ghost_81_outcomes_hex": [f"{value:02x}" for value in examples],
            "ghost_81_impossible_example_hex": "42",
            "scope": "Ideal foreground/idle composition at fixed alignment; no register timing, pixel pipeline, PNG interpretation or release matching"}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    examples = {}
    for name in SOURCE_SHA256:
        blob, symbols, assembly = assemble(name)
        examples[name] = {"assembly": assembly, "cpu_execution": execute(name, blob, symbols)}
    receipt = {"pass": True, "script_sha256": digest(Path(__file__).read_bytes()),
               "py65_version": importlib.metadata.version("py65"),
               "examples": examples, "ideal_compositor": compositor_proof(),
               "scope": "Exact teaching-source assembly plus bounded original-CPU polling and initialization; these examples do not contain the multicolor shine-through scroller"}
    (OUTPUT / "proof.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"pass": True, "examples": {name: {"prg_sha256": item["assembly"]["prg_sha256"],
                                                        "prg_bytes": item["assembly"]["prg_bytes"],
                                                        "cpu_steps": item["cpu_execution"]["steps"]}
                                               for name, item in examples.items()},
                      "ideal_compositor": receipt["ideal_compositor"]}, indent=2))


if __name__ == "__main__":
    main()
