#!/usr/bin/env python3
"""Extract conventional DOS files and record original D64 identity; no CPU."""

import hashlib
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/research/the-ghost"
DISKS = {
    "a": "568373df6b4451fe1f591dea0e217aefff0c147cd8987a6382b4ced1c1c9ce0b",
    "b": "19545727ff108d80c2b6aa51912235e919651383239438add178a48d82ab6c93",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sectors(track):
    assert 1 <= track <= 35
    return 21 if track <= 17 else 19 if track <= 24 else 18 if track <= 30 else 17


def sector(disk, track, number):
    assert 0 <= number < sectors(track)
    offset = (sum(sectors(t) for t in range(1, track)) + number) * 256
    return disk[offset:offset + 256]


def petscii(data):
    return "".join(chr(value) if 32 <= value <= 126 else f"<{value:02X}>" for value in data.rstrip(b"\xa0"))


def chain(disk, track, number):
    seen, raw = [], bytearray()
    while track:
        assert (track, number) not in seen
        seen.append((track, number))
        block = sector(disk, track, number)
        raw.extend(block[2:] if block[0] else block[2:block[1] + 1])
        track, number = block[:2]
    return bytes(raw), seen


def inspect(side):
    disk = (OUTPUT / "extracted" / f"the-ghost-{side}.d64").read_bytes()
    assert len(disk) == 174848 and digest(disk) == DISKS[side]
    bam = sector(disk, 18, 0)
    entries, seen = [], set()
    track, number = 18, 1
    out = OUTPUT / "dos-files" / side
    out.mkdir(parents=True, exist_ok=True)
    while track:
        assert (track, number) not in seen
        seen.add((track, number))
        block = sector(disk, track, number)
        for index in range(8):
            row = block[index * 32:(index + 1) * 32]
            if not row[2]:
                continue
            name = petscii(row[5:21])
            item = {"index": len(entries), "name": name, "name_hex": row[5:21].hex(),
                    "type": row[2], "start": list(row[3:5]), "directory_blocks": int.from_bytes(row[30:32], "little")}
            if row[3]:
                raw, links = chain(disk, row[3], row[4])
                target = out / f"{len(entries):03d}.prg"
                target.write_bytes(raw)
                item.update({"path": str(target.relative_to(ROOT)), "bytes": len(raw), "sha256": digest(raw),
                             "sector_chain": links, "load": int.from_bytes(raw[:2], "little"),
                             "first_bytes_hex": raw[:48].hex(" ")})
                basic = re.search(rb"\x9e\s*([0-9]+)", raw[2:64])
                if basic:
                    item["basic_sys_decimal"] = int(basic.group(1))
            entries.append(item)
        track, number = block[:2]
    return {"side": side, "d64_sha256": digest(disk), "bam_title": petscii(bam[0x90:0xA0]),
            "bam_title_hex": bam[0x90:0xA0].hex(), "bam_id_hex": bam[0xA2:0xA7].hex(),
            "entries": entries, "directory_sector_count": len(seen),
            "scope": "Conventional CBM DOS directory chains only; custom fastloader streams are not identified"}


def main():
    result = {"pass": True, "script_sha256": digest(Path(__file__).read_bytes()),
              "disks": [inspect(side) for side in DISKS]}
    (OUTPUT / "disk-inventory.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"disks": [{"side": disk["side"], "directory_entries": len(disk["entries"]),
                                "distinct_payload_hashes": sorted({item["sha256"] for item in disk["entries"] if "sha256" in item}),
                                "bootstrap": {key: disk["entries"][0][key] for key in
                                              ("bytes", "load", "basic_sys_decimal", "sector_chain")}}
                               for disk in result["disks"]]}, indent=2))


if __name__ == "__main__":
    main()
