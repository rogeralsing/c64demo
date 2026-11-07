#!/usr/bin/env python3
"""Export the supplied Koala scene unchanged for foreground sprites."""

import hashlib
import json
from pathlib import Path

def prepare(output):
    source = (Path(__file__).resolve().parent / "assets" / "scene.koa").read_bytes()
    if len(source) != 10003:
        raise ValueError("Expected a 10003-byte Koala multicolor image")
    bitmap = bytearray(source[2:8002])
    screen = bytearray(source[8002:9002])
    colors = bytearray(value & 15 for value in source[9002:10002])
    background = source[10002] & 15
    if background != 0:
        raise ValueError("The supplied scene must have a black global background")
    # The current image has artwork inside the circle. Keep its measured
    # origin in the source manifest rather than requiring a solid white disk.
    calibration = json.loads((Path(__file__).resolve().parent / "assets" / "scene-circle-repair.json").read_text())
    if calibration["source_sha256"] != hashlib.sha256(source).hexdigest():
        raise ValueError("The circle origin manifest does not match the supplied scene")
    center_x, center_y = calibration["center"]
    output.mkdir(parents=True, exist_ok=True)
    (output / "ball-bitmap.bin").write_bytes(bitmap)
    (output / "ball-screen.bin").write_bytes(screen)
    (output / "ball-colors.bin").write_bytes(colors)
    metadata = {"source": "assets/scene.koa", "source_sha256": hashlib.sha256(source).hexdigest(),
                "center": [center_x, center_y], "background": background,
                "bitmap_passthrough": True, "generated_dithering": False}
    (output / "scene.json").write_text(json.dumps(metadata, indent=2)+"\n")
    constants = {"CENTER_X": center_x, "CENTER_Y": center_y,
                 "X_BIAS": (center_x-104) & 255, "Y_BIAS": (center_y-78) & 255,
                 "X_OFFSET": center_x-128, "Y_OFFSET": center_y-128}
    (output / "scene.asm").write_text("// Graphics origin measured from the supplied white circle.\n"+
                                    "".join(f".const SCENE_{key} = {value}\n" for key, value in constants.items()))
    print(json.dumps(metadata))


if __name__ == "__main__":
    prepare(Path(__file__).resolve().parent / "build")
