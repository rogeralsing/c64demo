#!/usr/bin/env python3
"""Render original implicit 3D surfaces and encode Oscar64-compatible LZ streams."""
import hashlib
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "build"
BAYER = ((0, 8, 2, 10), (12, 4, 14, 6), (3, 11, 1, 9), (15, 7, 13, 5))


def render(phase):
    angle = math.tau * phase / 25
    centers = [(17 * math.cos(angle + shift), 9 * math.sin(2 * angle + shift),
                9 * math.sin(angle + shift), radius)
               for shift, radius in ((0, 15), (2.1, 12), (4.2, 10))]
    bits = []
    for y in range(42):
        row = []
        for x in range(96):
            px, py = x - 47.5, (y - 20.5) * 1.5
            hit = None
            # Orthographic rays enter an implicit sum-of-potentials surface.
            for z in range(-34, 35):
                potential = sum(r*r / max(0.1, (px-cx)**2 + (py-cy)**2 + (z-cz)**2)
                                for cx, cy, cz, r in centers)
                if potential >= 1.7:
                    hit = z
                    break
            if hit is None:
                row.append(False)
                continue
            normal = [0., 0., 0.]
            for cx, cy, cz, r in centers:
                delta = (px-cx, py-cy, hit-cz)
                factor = r*r / max(0.1, sum(d*d for d in delta))**2
                for axis in range(3):
                    normal[axis] += delta[axis] * factor
            length = math.sqrt(sum(v*v for v in normal))
            diffuse = max(0., sum(a*b for a, b in zip(normal, (-.45, -.35, -.82))) / length)
            level = min(1., .12 + .70*diffuse + .55*diffuse**12)
            row.append(level * 16 > BAYER[y % 4][x % 4])
        bits.append(row)
    frame = bytearray(512)
    for y, row in enumerate(bits):
        for x, active in enumerate(row):
            if active:
                sprite = (y // 21) * 4 + x // 24
                offset = sprite*64 + (y % 21)*3 + (x % 24)//8
                frame[offset] |= 128 >> (x % 8)
    return bytes(frame)


def compress(raw):
    """Greedy LZ: literal count, or high-bit count and 8-bit backward distance."""
    encoded, pending = bytearray(), bytearray()
    cursor = 0
    def flush():
        if pending:
            encoded.append(len(pending))
            encoded.extend(pending)
            pending.clear()
    while cursor < len(raw):
        best_length, best_distance = 0, 0
        for distance in range(1, min(cursor, 255)+1):
            length = 0
            while length < min(127, len(raw)-cursor) and raw[cursor+length] == raw[cursor+length-distance]:
                length += 1
            if length > best_length:
                best_length, best_distance = length, distance
        if best_length >= 4:
            flush()
            encoded.extend((128 | best_length, best_distance))
            cursor += best_length
        else:
            pending.append(raw[cursor])
            cursor += 1
            if len(pending) == 127:
                flush()
    flush()
    encoded.append(0)
    return bytes(encoded)


def main():
    OUT.mkdir(exist_ok=True)
    raw_frames = [render(phase) for phase in range(25)]
    packed = [compress(raw) for raw in raw_frames]
    (OUT / "frames.raw").write_bytes(b"".join(raw_frames))
    source = ["// Generated original frames, not original-production assets.",
              "frameLo: .byte " + ",".join(f"<packed{i}" for i in range(25)),
              "frameHi: .byte " + ",".join(f">packed{i}" for i in range(25))]
    for i, data in enumerate(packed):
        source.append(f"packed{i}: .byte " + ",".join(f"${v:02x}" for v in data))
    (OUT / "frames.asm").write_text("\n".join(source) + "\n")
    (OUT / "artwork.json").write_text(json.dumps({"frames": 25, "raw_bytes": 12800,
        "packed_bytes": sum(map(len, packed)), "packed_sizes": list(map(len, packed)),
        "raw_sha256": hashlib.sha256(b"".join(raw_frames)).hexdigest(),
        "format": "Oscar64 #embed lzo byte-command stream, not standard LZO1X"}, indent=2)+"\n")
    print(f"Prepared 25 original frames: 12800 raw bytes, {sum(map(len, packed))} packed bytes")


if __name__ == "__main__":
    main()
