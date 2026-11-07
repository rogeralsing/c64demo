#!/usr/bin/env python3
"""Extract the older six-byte Bitfire directory with a pinned writer reference.

No fastloader/drive code is executed. Raw source and disk payloads stay ignored.
"""

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from inspect_disk import DISKS, OUTPUT, ROOT, digest, sector, sectors


COMMIT = "092ea04e865db6d6193ecae48b81615d9ad52dd4"
SOURCES = {
    "d64write.c": "e04cc500e58aa3dddcf8015941b84552b8d90586",
    "resident.asm": "b6be1fa2727aef3ca30a7fe00149c5a4a5926c46",
    "drivecode.asm": "887057e9613b58bcb88c68b239f9c9f6fc6636ab",
}


def order(track):
    return [index for residue in range(4) for index in range(residue, sectors(track), 4)]


def source_archive():
    out = OUTPUT / "loader-reference"
    out.mkdir(exist_ok=True)
    receipt = []
    for name, expected in SOURCES.items():
        url = f"https://raw.githubusercontent.com/bboxy/bitfire/{COMMIT}/bitfire/{name}"
        path = out / name
        if not path.exists():
            with urllib.request.urlopen(url, timeout=30) as response:
                path.write_bytes(response.read(200_001))
        raw = path.read_bytes()
        git_blob = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        assert git_blob == expected
        receipt.append({"url": url, "path": str(path.relative_to(ROOT)), "bytes": len(raw),
                        "git_blob_sha1": git_blob, "sha256": digest(raw)})
    return receipt


def extract(side):
    disk = (OUTPUT / "extracted" / f"the-ghost-{side}.d64").read_bytes()
    assert digest(disk) == DISKS[side]
    assert sector(disk, 18, 18)[255] == (0xF0 if side == "a" else 0xF1)
    flat = [(track, number) for track in range(1, 36) if track != 18 for number in order(track)]
    rows, allocated = [], set()
    out = OUTPUT / "packed" / side
    out.mkdir(parents=True, exist_ok=True)
    for directory_sector in (18, 17, 16):
        table = sector(disk, 18, directory_sector)
        for slot in range(42):
            fields = table[slot * 6:slot * 6 + 6]
            if not fields[0]:
                return rows
            track, number = fields[:2]
            load = int.from_bytes(fields[2:4], "little")
            size = int.from_bytes(fields[4:6], "little") + 1
            assert load + size <= 65536
            start = flat.index((track, number))
            links = flat[start:start + (size + 255) // 256]
            assert not allocated.intersection(links), "Raw files unexpectedly share sectors"
            if rows:
                assert start == rows[-1]["flat_sector_end_exclusive"], "Unexpected gap/order between raw files"
            allocated.update(links)
            data = b"".join(sector(disk, t, s) for t, s in links)[:size]
            assert len(data) == size
            path = out / f"{len(rows):03d}-{load:04x}.prg"
            path.write_bytes(load.to_bytes(2, "little") + data)
            rows.append({"side": side, "file": len(rows), "directory_sector": directory_sector,
                         "directory_slot": slot, "directory_fields_hex": fields.hex(" "),
                         "load": load, "packed_bytes": size, "packed_sha256": digest(data),
                         "file_sha256": digest(path.read_bytes()), "path": str(path.relative_to(ROOT)),
                         "sector_chain": links, "flat_sector_end_exclusive": start + len(links),
                         "first_bytes_hex": data[:24].hex(" ")})
    return rows


def main():
    sources = source_archive()
    files = [row for side in DISKS for row in extract(side)]
    assert sum(row["side"] == "a" for row in files) == 17
    assert sum(row["side"] == "b" for row in files) == 45
    receipt = {"pass": True, "script_sha256": digest(Path(__file__).read_bytes()),
               "writer_reference_commit": COMMIT, "source_files": sources, "files": files,
               "scope": "Six-byte old Bitfire directory layout and fixed four-sector interleave; disk rows/continuous allocation checked independently; no drive or serial transfer"}
    (OUTPUT / "streams.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"pass": True, "files": len(files), "side_a": 17, "side_b": 45,
                      "packed_payload_bytes": sum(row["packed_bytes"] for row in files), "source_files": sources}, indent=2))


if __name__ == "__main__":
    main()
