#!/usr/bin/env python3
"""Verify all three converter-generated native PNGs at the fixed PAL origin.

Reads the existing native checker output; starts no emulator and performs no
offset search. The documented PAL NUFLI picture rectangle is 320x200 at (32,32).
"""

import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "build/research/nufli"
CONVERTER = ROOT.parent / "c64"


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", type=Path, default=BASE / "converter-native-01")
    parser.add_argument("--expected", type=Path, default=BASE / "converter-audit/expected-indices.bin")
    args = parser.parse_args()
    native = args.native.resolve()
    report_file = native / "verification.json"
    report = json.loads(report_file.read_text())
    expected_file = args.expected.resolve()
    expected = expected_file.read_bytes()
    assert len(expected) == 64000 and max(expected) <= 15
    assert sha(expected_file) == report["expected_sha256"]
    assert sha(Path(report["program"])) == report["sha256"]
    assert report["pass"] and report["pal"]
    assert report["speed_percent"] == 100 and not report["warp"]
    palette_file = CONVERTER / "palettes/colodore.vpl"
    palette = [tuple(int(value, 16) for value in line.split()[:3])
               for raw in palette_file.read_text().splitlines()
               if (line := raw.strip()) and not line.startswith("#")]
    assert len(palette) == len(set(palette)) == 16
    reference = [palette[index] for index in expected]
    samples = []
    for original in report["samples"]:
        path = native / original["file"]
        assert sha(path) == original["sha256"]
        picture = Image.open(path).convert("RGB")
        assert picture.size == (384, 272)
        pixels = list(picture.crop((32, 32, 352, 232)).get_flattened_data())
        mismatches = [index for index, (a, b) in enumerate(zip(pixels, reference)) if a != b]
        assert len(pixels) == 64000
        assert not mismatches, {"file": path.name, "mismatches": len(mismatches),
                                "first_indices": mismatches[:20]}
        assert original["origin"] == [32, 32] and original["mismatches"] == 0
        samples.append({"file": path.name, "sha256": sha(path),
                        "compared_pixels": len(pixels), "mismatches": len(mismatches)})
    assert len(samples) == 3
    result = {
        "pass": True, "program_sha256": report["sha256"],
        "expected_sha256": sha(expected_file), "palette_sha256": sha(palette_file),
        "native_report_sha256": sha(report_file), "script_sha256": sha(Path(__file__)),
        "native_checker_sha256_at_recheck": sha(CONVERTER / "nufli/verify-vice.py"),
        "comparison": "Fixed PAL NUFLI rectangle (32,32)..(352,232); all 320x200 RGB samples; no offset search or excluded pixels.",
        "samples": samples,
        "scope": "Three PAL captures of one current-converter fitted/exported reference picture. No NTSC or physical-hardware claim.",
    }
    (native / "fixed-origin-check.json").write_text(json.dumps(result, indent=2) + "\n")
    print("PASS: 3 current-converter PAL captures; 64,000 matching pixels each; fixed origin (32,32).")


if __name__ == "__main__":
    main()
