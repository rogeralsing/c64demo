#!/usr/bin/env python3
"""Extract Next Round's original Bitfire raw files, not its DOS aliases.

Format from bboxy/bitfire d64write.c at 5a3964b533656332c12cc0904f2ce92f44499c6f.
The exact production payloads were also checked against native loaded RAM.
Other productions must independently establish their format/version first.
"""
import hashlib
import json
from pathlib import Path

ROOT = Path("build/research/next-round/boot-analysis")


def sector_count(track):
    return 21 if track <= 17 else 19 if track <= 24 else 18 if track <= 30 else 17


def read_sector(disk, track, sector):
    assert 1 <= track <= 35 and 0 <= sector < sector_count(track)
    address = 256*(sum(sector_count(t) for t in range(1, track))+sector)
    return disk[address:address+256]


def sector_order(track):
    interleave = 4 if track <= 17 else 3
    return [s for residue in range(interleave) for s in range(residue, sector_count(track), interleave)]


def extract(disk, side):
    assert len(disk) == 174848, "This decoder is restricted to 35-track D64s"
    files = []
    for dirsector in (18, 17):
        directory = read_sector(disk, 18, dirsector)
        if dirsector == 18:
            assert directory[3] == 0xF0+side-1
        track, slot, byte = directory[:3]
        count = 0
        for index in range(63):
            fields = [directory[4+index+63*k] for k in range(4)]
            if not any(fields):
                break
            lo, hi_minus_one, size_lo, size_hi = fields
            load = lo | ((hi_minus_one+1)&255) << 8
            size = (size_lo | size_hi << 8)+1
            data = bytearray()
            while len(data) < size:
                order = sector_order(track)
                if slot == len(order):
                    track += 1
                    if track == 18:
                        track += 1
                    slot = 0
                    order = sector_order(track)
                sector = read_sector(disk, track, order[slot])
                take = min(256-byte, size-len(data))
                data.extend(sector[byte:byte+take])
                byte += take
                if byte == 256:
                    slot += 1
                    byte = 0
            files.append((len(files), load, bytes(data)))
            count += 1
        if count < 63:
            break
    return files


def main():
    previous = {(e["side"], e["file"]): e for e in json.loads((ROOT/"bitfire-files.json").read_text())}
    result = []
    for side in (1, 2, 3):
        disk_path = Path(f"build/research/next-round/release/round{side}.d64")
        files = extract(disk_path.read_bytes(), side)
        for index, load, payload in files:
            digest = hashlib.sha256(payload).hexdigest()
            old = previous[side, index]
            assert old["load_address"] == load and old["bytes"] == len(payload) and old["payload_sha256"] == digest
            path = ROOT/f"bitfire-round{side}/{index:03d}-{load:04x}.prg"
            assert path.read_bytes() == load.to_bytes(2, "little")+payload
            result.append({"side": side, "file": index, "load": load, "bytes": len(payload), "sha256": digest})
        print(f"round{side}: {len(files)} raw files reproduce exactly")
    assert len(result) == len(previous)
    (ROOT/"extraction-check.json").write_text(json.dumps({
        "pass": True, "files": result,
        "source_commit": "5a3964b533656332c12cc0904f2ce92f44499c6f",
        "scope": "Reproduce existing raw file payloads from original disks; no CPU/native hardware execution",
        "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    }, indent=2)+"\n")


if __name__ == "__main__":
    main()
