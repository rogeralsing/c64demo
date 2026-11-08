#!/usr/bin/env python3
"""Check No Bounds' repeated bob-screen data; no CPU, tools or network run.

Inputs are the archived primary article, immutable source tree and published
assets in build/research/frontier-reading-20261108/. Downloaded code is data.
"""

import hashlib
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/research/frontier-reading-20261108"
COMMIT = "965807c511e2025b5c5e1ffb2a6235a4efd6ae5b"
ACQUISITIONS_SHA256 = "8c4e5c0c77c3110bcecb1d442f1cd69195347d76d58028ae4201f8a09be58301"
PART = "NoBounds/Parts/TinyCircleScroll/"
LINK = "NoBounds/Link/TinyCircleScroll/"


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha256(data)}


def source_contracts():
    index_path = OUT / "acquisitions.json"
    assert sha256(index_path.read_bytes()) == ACQUISITIONS_SHA256
    index = json.loads(index_path.read_text())
    assert len(index) == 27
    for name, entry in index.items():
        assert entry["http_status"] == 200
        data = (OUT / name).read_bytes()
        assert len(data) == entry["bytes"] and sha256(data) == entry["sha256"]

    commit = json.loads((OUT / "commit.json").read_text())
    tree = json.loads((OUT / "tree.json").read_text())
    assert commit["sha"] == COMMIT
    assert tree["sha"] == commit["commit"]["tree"]["sha"] and not tree["truncated"]
    blobs = {x["path"]: x for x in tree["tree"] if x["type"] == "blob"}
    checked = []
    for name in index:
        if name.startswith("NoBounds/"):
            data = (OUT / name).read_bytes()
            blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            assert blob == blobs[name]["sha"]
            checked.append({**artifact(OUT / name), "git_blob": blob})

    cpp = (OUT / (PART + "TinyCircleScroll.cpp")).read_text()
    asm = (OUT / (PART + "TinyCircleScroll.asm")).read_text()
    sls = (OUT / (PART + "TinyCircleScroll.sls")).read_text()
    # Guard the visible source statements from which this bounded translation
    # was made. The immutable blobs above bind their full context as well.
    for fragment in ["static const int NUM_CHARS = 104;", "static const int NumFrames = 3;",
                     "(170.0 + sin(Angle * 5.0) * 30.0) / 2.0", "int NumCharsUsed = 1;",
                     "int NewX = XChar - 30 + (Repeat * 10) - Screen + 7;",
                     "int NewY = YChar - 30 + (Repeat * 10) - Screen;",
                     "SinTable[i] = ((unsigned char)iSinVal) % 80;"]:
        assert fragment in cpp
    for fragment in ["ldx #41", "cpx #9", "lda (ZP_ScreenSRC + (i * 2)), y",
                     "sta (ZP_ScreenDST + (i * 2)), y", ".var srcj = i * 40 + 29",
                     ".var dstj = (i + 10) * 40 + 39", ".var srcj = (14 * 40) + i",
                     ".var dstj = (24 * 40) + 10 + i"]:
        assert fragment in asm
    screen_line = next(line for line in sls.splitlines() if "Screen.bin" in line and line.startswith("File:"))
    assert screen_line.split()[-3:] == ["c000", "0000", "0400"]
    return {"acquisition_index": artifact(index_path), "acquired_bodies": len(index),
            "commit": COMMIT, "commit_utc": commit["commit"]["committer"]["date"],
            "tree": tree["sha"], "git_blob_checks": checked,
            "standalone_manifest_screen_line": screen_line.strip()}


def occupied_characters():
    # Independent coverage oracle: enumerate all 25 pixels of every clipped
    # 5x5 glyph rectangle. The C++ instead records per-row byte contributions
    # and handles right-hand byte spill separately.
    occupied = set()
    for frame in range(3):
        for copy in range(3):
            for letter in range(104):
                angle = (letter * 3 + frame) * 2 * math.pi / 312
                radius = (170 + math.sin(5 * angle) * 30) / 2
                px = math.floor(96 + math.sin(angle) * radius - 80 + copy * 80 + 0.5)
                py = math.floor(96 - math.cos(angle) * radius - 80 + copy * 80 + 0.5)
                for y in range(max(0, py), min(200, py + 5)):
                    for x in range(max(0, px), min(200, px + 5)):
                        cell = (x // 8, y // 8)
                        if 15 <= sum(cell) < 35:
                            occupied.add(cell)
    return {cell: n + 1 for n, cell in enumerate(sorted(occupied, key=lambda p: (p[1], p[0])))}


def quotient_maps(ids, period=10):
    # Each destination resolves to one representative in the diagonal band
    # 15 <= X+Y < 35. Unlike the C++ producer, this visits destinations once
    # and never splats a shape through a loop of eight copies.
    result = bytearray(10 * 1024)
    for screen in range(10):
        for y in range(25):
            for x in range(40):
                repeat = (x + y + 38 + 2 * screen) // (2 * period)
                cx = x + 23 + screen - period * repeat
                cy = y + 30 + screen - period * repeat
                result[screen * 1024 + y * 40 + x] = ids.get((cx, cy), 0)
    return bytes(result)


def reconstruct_screens(base, expected, repair=True):
    # None means an input byte not established by the one loaded 1KB screen.
    # Reads across $CFFF into the sprite region deliberately remain unknown.
    memory = [None] * 16384
    addresses = [0, 0x400, 0x800, 0xC00, 0x2000, 0x2400, 0x2800, 0x2C00, 0x3000, 0x3400]
    memory[:1024] = base
    checks = []
    for screen in range(9):
        src, dst = addresses[screen:screen + 2]
        # Preserve source order and aliasing, including over-read into the
        # destination for contiguous screen blocks. No C64 CPU is emulated.
        for y in range(256):
            for page in range(4):
                memory[dst + 256 * page + y] = memory[src + 41 + 256 * page + y]
        before = memory[dst:dst + 1000].count(None)
        if repair:
            for i in range(10):
                memory[dst + 960 + i] = 0
                memory[dst + i * 40 + 39] = 0
            for i in range(15):
                memory[dst + (i + 10) * 40 + 39] = memory[src + 41 + i * 40 + 29]
            for i in range(30):
                memory[dst + 24 * 40 + 10 + i] = memory[src + 41 + 14 * 40 + i]
        visible = memory[dst:dst + 1000]
        target = expected[(screen + 1) * 1024:(screen + 1) * 1024 + 1000]
        checks.append({"screen": screen + 1,
                       "unknown_visible_before_repairs": before,
                       "unknown_visible_after_repairs": visible.count(None),
                       "visible_differences_or_unknown": sum(a != b for a, b in zip(visible, target))})
    return checks


def check_maps():
    screens = (OUT / (LINK + "Screen.bin")).read_bytes()
    assert len(screens) == 10240
    ids = occupied_characters()
    assert len(ids) == 143 and max(screens) == 143
    produced = quotient_maps(ids)
    assert produced == screens
    assert all(not any(screens[i * 1024 + 1000:(i + 1) * 1024]) for i in range(10))
    rebuilt = reconstruct_screens(screens[:1024], screens)
    assert all(x["visible_differences_or_unknown"] == 0 for x in rebuilt)
    wrong_period = sum(a != b for a, b in zip(quotient_maps(ids, period=8), screens))
    unpatched = reconstruct_screens(screens[:1024], screens, repair=False)
    assert wrong_period > 0 and any(x["visible_differences_or_unknown"] for x in unpatched)

    sin = (OUT / (LINK + "SinTable.bin")).read_bytes()
    generated_sin = bytes((math.floor(math.sin(i * 2 * math.pi / 256) * 76 + i * 160 / 256 + 0.5) & 255) % 80
                          for i in range(256))
    assert sin == generated_sin and min(sin) == 0 and max(sin) == 79
    d018 = bytes([14, 30, 46, 62, 142, 158, 174, 190, 206, 222])
    tables = d018 + bytes(range(23, 15, -1)) + bytes(range(7, -1, -1))
    tables += bytes([195, 199, 203, 207, 227, 231, 235, 239, 243, 247])
    prg = (OUT / (LINK + "TinyCircleScroll.prg")).read_bytes()
    assert prg.count(tables) == 1
    table_offset = prg.index(tables)
    load = int.from_bytes(prg[:2], "little")
    return {"occupied_nonblank_characters": len(ids), "characters_with_blank": len(ids) + 1,
            "screen_artifact": artifact(OUT / (LINK + "Screen.bin")),
            "quotient_comparisons": len(screens), "quotient_differences": 0,
            "reconstructed_visible_cells": 9000, "reconstruction": rebuilt,
            "negative_controls": {"eight_character_period_differences": wrong_period,
                                  "omitted_boundary_repairs": unpatched},
            "sin_table": {**artifact(OUT / (LINK + "SinTable.bin")), "compared": 256,
                          "differences": 0, "range": [min(sin), max(sin)]},
            "published_prg": {**artifact(OUT / (LINK + "TinyCircleScroll.prg")),
                              "load_address": load, "selection_table_file_offset": table_offset,
                              "selection_table_address": load + table_offset - 2,
                              "selection_table_hex": tables.hex(), "unique_occurrences": 1},
            "d018_by_coarse_phase": list(d018),
            "scope": "Asset geometry and source-derived RAM-copy algebra only; no assembled source/release proof, CPU execution, scanout or timing."}


def main():
    report = {"pass": True, "producer": artifact(Path(__file__).resolve()),
              "sources": source_contracts(), "repeated_bob_screens": check_maps()}
    destination = OUT / "reading-findings.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"pass": True, "receipt": artifact(destination),
                      "source_blobs": len(report["sources"]["git_blob_checks"]),
                      "map_bytes": 10240, "reconstructed_visible_cells": 9000,
                      "characters_including_blank": 144}, indent=2))


if __name__ == "__main__":
    main()
