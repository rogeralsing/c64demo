#!/usr/bin/env python3
"""Compare every decoded, known output address with a raw 64 KB RAM capture."""

import argparse
import hashlib
import json
from pathlib import Path

from unpack_stream import ranges


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ram", type=Path)
    parser.add_argument("--before", type=Path)
    parser.add_argument("--root", type=Path, default=Path("build/research/tower-power"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    live = args.ram.read_bytes()
    if len(live) != 65536:
        parser.error("RAM input must be exactly 65,536 raw bytes, without a PRG header")
    before = args.before.read_bytes() if args.before else None
    if before is not None and len(before) != 65536:
        parser.error("Before RAM input must also be exactly 65,536 raw bytes")
    comparisons = []
    for item in json.loads((args.root / "static/unpacked-index.json").read_text()):
        if not item.get("pass"):
            continue
        prefix = item["output_prefix"]
        memory = Path(prefix + ".memory.bin").read_bytes()
        known = Path(prefix + ".known.bin").read_bytes()
        indices = [i for i, value in enumerate(known) if value]
        mismatch = [i for i in indices if memory[i] != live[i]]
        bitmap = bytearray(65536)
        for address in mismatch:
            bitmap[address] = 1
        row = {"source": item["source"], "known_bytes": len(indices),
               "matches": len(indices) - len(mismatch), "mismatches": len(mismatch),
               "mismatch_ranges": ranges(bitmap),
               "first_mismatch_addresses": mismatch[:64],
               "io_mismatches": sum(0xd000 <= i < 0xe000 for i in mismatch),
               "zero_page_stack_mismatches": sum(i < 0x200 for i in mismatch)}
        if before is not None:
            row["changed_known_bytes"] = sum(before[i] != live[i] for i in indices)
        comparisons.append(row)
    comparisons.sort(key=lambda row: (row["mismatches"] == 0, row["matches"]), reverse=True)
    report = {"ram_file": str(args.ram), "ram_sha256": hashlib.sha256(live).hexdigest(),
              "raw_comparison": "No IO, stack, or other addresses excluded",
              "vector_bytes_c2f0_c2f8": live[0xc2f0:0xc2f9].hex(" "),
              "comparisons": comparisons}
    if before is not None:
        report["before_file"] = str(args.before)
        report["before_sha256"] = hashlib.sha256(before).hexdigest()
        report["changed_bytes"] = [{"address": i, "before": a, "after": b}
                                   for i, (a, b) in enumerate(zip(before, live)) if a != b]
    output = args.output or args.root / "static/live-comparison.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"output": str(output),
                      "exact_known_range_matches": [row["source"] for row in comparisons if not row["mismatches"]],
                      "changed_bytes": len(report.get("changed_bytes", []))}, indent=2))


if __name__ == "__main__":
    main()
