#!/usr/bin/env python3
"""Colorize the already accepted independent prediction for human inspection."""
import hashlib
import json
from pathlib import Path

from PIL import Image, __version__ as pillow_version

ROOT = Path(__file__).resolve().parents[2]
PROOF = ROOT / 'build/research/aloft-pixels-20261109/display-analysis/accepted-01/display-contract-proof.json'
PROOF_SHA = '859f7ce6a03b64f6be7e056052c4f980e55da428cce658cbddc75b3602c239a5'
PALETTE = ROOT / 'palettes/colodore.vpl'
PALETTE_SHA = 'cfc740890e811b94a73bbbe9f38c400f6714d37c6b6167935adf4f892422b972'
OUT = ROOT / 'build/research/aloft-pixels-20261109/preview-01'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ref(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def main():
    assert not OUT.exists()
    assert sha(PROOF.read_bytes()) == PROOF_SHA
    assert sha(PALETTE.read_bytes()) == PALETTE_SHA
    proof = json.loads(PROOF.read_bytes())
    assert proof['pass_'] and proof['accepted_native_pixel_comparison']
    row = next(row for row in proof['predicted_outputs']
               if row['name'] == 'later-predicted-graphics-320x200.bin')
    path = PROOF.parent / row['name']
    pixels = path.read_bytes()
    assert len(pixels) == row['bytes'] == 64000 and sha(pixels) == row['sha256']
    colors = [[int(value, 16) for value in line.split()] for line in PALETTE.read_text().splitlines()
              if line.strip() and not line.lstrip().startswith('#')]
    assert len(colors) == 16 and all(len(color) == 3 for color in colors)
    assert set(pixels) <= set(range(16))
    image = Image.frombytes('P', (320, 200), pixels)
    image.putpalette([v for color in colors for v in color] + [0] * (768 - 48))
    OUT.mkdir(parents=True)
    normal, enlarged = OUT / 'aloft-later-320x200.png', OUT / 'aloft-later-640x400.png'
    image.save(normal)
    image.resize((640, 400), Image.Resampling.NEAREST).save(enlarged)
    metadata = dict(classification='Visualization of independently predicted physical pixel indices, not a native screenshot.',
        producer=ref(Path(__file__)), inputs=[ref(PROOF), ref(path), ref(PALETTE)],
        outputs=[ref(normal), ref(enlarged)], physical_pixel_geometry=[320, 200],
        multicolor_sample_geometry=[160, 200], enlarged_nearest_integer_scale=2,
        pillow_version=pillow_version, RGB_palette_is_visualization_not_analog_output=True)
    (OUT / 'preview.json').write_text(json.dumps(metadata, indent=2) + '\n')
    print(json.dumps(metadata['outputs']))


if __name__ == '__main__':
    main()
