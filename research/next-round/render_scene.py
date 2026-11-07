#!/usr/bin/env python3
"""Host-only scene preview, deliberately not a C64 pixel/cycle emulator.

Uses exact rational even-odd interiors sampled at pixel centers and the literal
published pattern table. The native renderer has different integer edge rules.
"""
from fractions import Fraction
import hashlib
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw

from analyze_scene import intervals

ROOT = Path("build/research/next-round/boot-analysis")
PALETTE = [(53, 40, 121), (255, 255, 255), (154, 210, 132), (88, 141, 67)]


def render(frame, patterns):
    image = Image.new("RGB", (160, 240), PALETTE[0])
    pixels = image.load()
    for polygon in frame["polygons"]:
        points = polygon["outline_xy"]
        pattern = patterns[polygon["pattern"]]
        for y in range(max(0, min(p[1] for p in points)), min(240, max(p[1] for p in points))):
            for left, right in intervals(points, Fraction(2*y+1, 2)):
                for x in range(max(0, math.ceil(left-Fraction(1, 2))), min(160, math.ceil(right-Fraction(1, 2)))):
                    pixels[x, y] = PALETTE[pattern[y & 1][x & 3]]
    return image.resize((320, 240), Image.Resampling.NEAREST)


def main():
    scene = json.loads((ROOT / "original-scene.json").read_text())
    p = json.loads(Path("build/research/next-round/patterns.json").read_text())
    patterns = {e["id"]: [e["even_selectors"], e["odd_selectors"]] for e in p["patterns"]}
    samples = list(range(256, 536, 8))
    sheet = Image.new("RGB", (8*160, math.ceil(len(samples)/8)*136), "#202020")
    draw = ImageDraw.Draw(sheet)
    for n, index in enumerate(samples):
        im = render(scene["frames"][index], patterns)
        thumb = im.resize((160, 120), Image.Resampling.NEAREST)
        x, y = n % 8 * 160, n // 8 * 136
        sheet.paste(thumb, (x, y+16))
        draw.text((x+4, y+2), f"record {index}", fill="white")
    sheet.save(ROOT / "scene-contact-sheet.png")
    for index in [296, 304, 312, 320, 322, 328, 336, 344, 352, 360, 368, 376, 384, 392, 400]:
        render(scene["frames"][index], patterns).resize((640, 480), Image.Resampling.NEAREST).save(ROOT / f"host-scene-{index:03}.png")
    (ROOT / "host-preview.json").write_text(json.dumps({
        "scope": "Host geometry/pattern preview, NOT native C64 output or integer edge equivalence",
        "scene_sha256": scene["summary"]["stream_sha256"],
        "pattern_source_sha256": p["source_sha256"],
        "sampled_records": samples,
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }, indent=2)+"\n")
    print(ROOT / "scene-contact-sheet.png")


if __name__ == "__main__":
    main()
