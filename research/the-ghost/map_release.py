#!/usr/bin/env python3
"""Audit depacked payload bounds and map a small original first-scene path.

Static bytes and saved CPU receipts only; no extra CPU or hardware execution.
"""

import json
from pathlib import Path

from inspect_disk import OUTPUT, ROOT, digest


def main():
    depack_path = OUTPUT / "depack.json"
    depack = json.loads(depack_path.read_text())
    streams = json.loads((OUTPUT / "streams.json").read_text())["files"]
    assert depack["pass"] and len(depack["files"]) == len(streams) == 62
    files = []
    for execution, stream in zip(depack["files"], streams):
        assert (execution["side"], execution["file"]) == (stream["side"], stream["file"])
        assert execution["status"] == "returned" and not execution["uninitialized_reads"]
        packed = (ROOT / stream["path"]).read_bytes()[2:]
        low, high = int.from_bytes(packed[:2], "little"), int.from_bytes(packed[2:4], "little")
        assert high == execution["destination_pointer_end"]
        assert len(execution["outputs"]) == 1
        output = execution["outputs"][0]
        assert [output["low"], output["end_exclusive"]] == [low, high]
        raw = (ROOT / output["path"]).read_bytes()
        assert raw[:2] == low.to_bytes(2, "little")
        assert len(raw) == high - low + 2 and digest(raw[2:]) == output["sha256"]
        cursor = (execution["source_cursor_base_high"] << 8) + (stream["load"] & 255) + execution["source_cursor_x"]
        tail = stream["load"] + stream["packed_bytes"] - cursor
        assert 0 <= tail <= 9
        files.append({"side": stream["side"], "file": stream["file"], "low": low,
                      "end_exclusive": high, "bytes": high - low,
                      "sha256": output["sha256"], "unread_packed_tail_bytes": tail})

    first = files[1]
    assert first["side"] == "a" and first["file"] == 1
    assert first["sha256"] == "c8919472979de1c66abdd094aebaf8f73eec86c8c63072c1ad1c5ab8200a1828"
    ram = (OUTPUT / "depacked/a-001-ram.bin").read_bytes()
    anchors = [
        (0x203B, "20 5e 31 20 68 20 20 d6 02", "Entry path calls $315E, reset routine $2068, then resident load/depack"),
        (0x2063, "4c 00 80", "Next direct scene transfer is JMP $8000"),
        (0x2098, "a9 08 8d 16 d0 a9 03 8d 00 dd a9 14 8d 18 d0", "Reset path restores D016=$08, DD00=$03, D018=$14"),
        (0x2108, "a9 02 8d 00 dd a9 80 8d 18 d0", "IRQ path writes DD00=$02 and D018=$80"),
        (0x214B, "ad b2 20 8d ff 7f", "IRQ path loads $20B2 and writes idle byte $7FFF"),
        (0x2195, "a9 3b 8d 11 d0", "Later IRQ path selects D011=$3B, with ECM clear"),
        (0x21ED, "a9 13 8d 11 d0 a9 0e 8d 21 d0", "Lower-border path writes D011=$13 and D021=$0E"),
        (0x2235, "a9 00 8d ff 7f a9 1b 8d 11 d0", "Later IRQ clears $7FFF and restores D011=$1B"),
    ]
    mapped = []
    for address, hexadecimal, meaning in anchors:
        signature = bytes.fromhex(hexadecimal)
        assert ram[address:address + len(signature)] == signature
        mapped.append({"address": address, "bytes_hex": hexadecimal, "meaning": meaning})
    result = {"pass": True, "script_sha256": digest(Path(__file__).read_bytes()),
              "depack_receipt_sha256": digest(depack_path.read_bytes()),
              "depacked_files": files, "total_output_bytes": sum(row["bytes"] for row in files),
              "total_cpu_steps": sum(row["steps"] for row in depack["files"]),
              "first_scene": {"file": "side A raw file 1", "output_range": [0x2000, 0x8000],
                              "payload_sha256": first["sha256"], "anchors": mapped,
                              "derived_vic_bank": 0x4000, "idle_byte_in_bank": 0x7FFF,
                              "derived_screen": 0x6000,
                              "assumption": "CIA2 low port bits are outputs as configured by the installer ($DD02=$3F); derive bank from inverted DD00 low bits",
                              "limits": "Addresses are original static instruction locations. No IRQ/raster schedule is executed; no particular visual effect is assigned from these anchors alone"},
              "scope": "Independently audit every output against packed destination headers and hashes; bounded static first-scene byte map, no native reproduction"}
    (OUTPUT / "release-map.json").write_text(json.dumps(result, indent=2) + "\n")
    (OUTPUT / "output-inventory.tsv").write_text("side\tfile\tlow\tend_exclusive\tbytes\tsha256\n" +
        "".join(f"{row['side']}\t{row['file']}\t{row['low']:04x}\t{row['end_exclusive']:04x}\t{row['bytes']}\t{row['sha256']}\n" for row in files))
    print(json.dumps({key: result[key] for key in ("pass", "total_output_bytes", "total_cpu_steps", "first_scene")}, indent=2))


if __name__ == "__main__":
    main()
