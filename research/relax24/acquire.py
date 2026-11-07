#!/usr/bin/env python3
"""Pin Relax #24's original archive and extract its containers without execution.

This inventories original bytes. It does not decode the magazine's article
format or turn a contemporary review into an effect-author explanation.
"""

import argparse
import datetime
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "build/research/relax24"
URL = "https://c64.rulez.org/pub/c64/Magazines/Relax/Relax_24_Phuture.zip"
ZIP_SHA = "cd0573d52adacd50927facd065ab8a7d51a8b236bd80f2a5ba90ec7e80f9bb21"
MEMBERS = {
    "REL24_S2.D64": (174848, "5f9e3b02ce0ed6feb8e75e1b7b006ccc803c07f0448555d4f2609f94d5c3f76b"),
    "REL24_S1.LNX": (31465, "85bc680309d41538003c4ed49262b693bfedc4ebafa62edf96d64e3ac747fa46"),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true", help="Fetch the pinned original ZIP; otherwise replay local bytes.")
    args = parser.parse_args()
    BASE.mkdir(parents=True, exist_ok=True)
    archive = BASE / "Relax_24_Phuture.zip"
    if args.fetch:
        with urllib.request.urlopen(URL, timeout=20) as response:
            data = response.read(2_000_001)
            assert len(data) <= 2_000_000 and sha(data) == ZIP_SHA
            archive.write_bytes(data)
            (BASE / "fetch.json").write_text(json.dumps({
                "requested_url": URL, "final_url": response.url,
                "utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "archive": record(archive),
            }, indent=2) + "\n")
    raw = archive.read_bytes()
    assert sha(raw) == ZIP_SHA
    with zipfile.ZipFile(io.BytesIO(raw)) as container:
        assert set(container.namelist()) == set(MEMBERS)
        for name, (size, expected) in MEMBERS.items():
            data = container.read(name)
            assert len(data) == size and sha(data) == expected
            (BASE / name).write_bytes(data)

    # The single-entry STAR LYNX container has one 254-byte directory block.
    # LSU includes the DOS final-block count byte: data length is LSU - 1.
    lnx = (BASE / "REL24_S1.LNX").read_bytes()
    fields = lnx[lnx.index(b"\r") + 1:254].split(b"\r")
    assert fields[0].strip() == b"1  *STAR LYNX 0.80  JOE/STA"
    assert int(fields[1]) == 1 and fields[4] == b"P"
    assert fields[2] == b"RELAX\xa4#024/SPR98"
    blocks, lsu = int(fields[3]), int(fields[5])
    assert blocks == 123 and 1 <= lsu <= 255
    size = (blocks - 1) * 254 + lsu - 1
    main_path = BASE / "relax24-main.prg"
    main_path.write_bytes(lnx[254:254 + size])
    assert len(lnx) == 254 + size
    assert sha(main_path.read_bytes()) == "ea9040469d211c87cdfd1aaa2a5eca04685be741d679bc1537cb7cc280810180"

    reader = ROOT / "research/second-reality/disk_inventory.py"
    spec = importlib.util.spec_from_file_location("relax24_disk_reader", reader)
    disk_reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(disk_reader)
    disk = (BASE / "REL24_S2.D64").read_bytes()
    pages, entries = disk_reader.directory(disk)
    output = BASE / "side2-files"
    output.mkdir(exist_ok=True)
    files, owners = [], set()
    for entry in entries:
        if entry["type_low_bits"] != 2:
            continue
        data, sectors, segments, termination = disk_reader.follow_chain(
            disk, entry["start_track"], entry["start_sector"])
        assert termination["kind"] == "valid_eof"
        assert len(sectors) == entry["declared_blocks"]
        for sector in sectors:
            identity = (sector["track"], sector["sector"])
            assert identity not in owners
            owners.add(identity)
        prefix = bytes.fromhex(entry["name_hex"])[:2].decode("ascii")
        target = output / (prefix + ".prg")
        assert prefix.isalnum() and len(prefix) == 2
        target.write_bytes(data)
        files.append({"directory_entry": entry, "extracted": record(target),
                      "sectors": sectors, "file_segments": segments,
                      "termination": termination,
                      "first_24_bytes_hex": data[:24].hex()})
    assert len(files) == 21
    result = {
        "pass": True, "scope": "Original container identity and exact extraction only; no article, CPU, display or timing proof.",
        "original_url": URL, "archive": record(archive),
        "members": [record(BASE / name) for name in MEMBERS],
        "lynx": {"format_source": "https://ist.uwaterloo.ca/~schepers/formats/LNX.TXT",
                 "directory_blocks": 1, "entry_count": 1,
                 "filename_hex": fields[2].hex(), "blocks": blocks,
                 "lsu": lsu, "data_offset": 254, "extracted": record(main_path),
                 "unaccounted_bytes": len(lnx) - 254 - size},
        "disk_reader": record(reader), "script": record(Path(__file__).resolve()),
        "directory_pages": pages, "directory_entries": entries,
        "side2_files": files, "distinct_file_sectors": len(owners),
        "limits": ["PRG is the DOS directory type, not proof of a load header or entry address.",
                   "No original article is decoded by this script; filenames alone do not identify article subjects.",
                   "Contemporary reviewer analysis must remain distinct from author evidence and checked runtime behavior."],
    }
    target = BASE / "archive-proof.json"
    target.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pass": True, "side2_files": len(files),
                      "file_bytes": sum(row["extracted"]["bytes"] for row in files),
                      "lynx_file_bytes": size, "proof": record(target)}, indent=2))


if __name__ == "__main__":
    main()
