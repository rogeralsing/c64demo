#!/usr/bin/env python3
"""Compare Next Round's published pattern definitions with original-run RAM.

This checks relocated tables and all reserved pattern glyphs in either the
standalone example or a separately identified original-production capture.
"""

import argparse
import hashlib
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ram", type=Path)
    parser.add_argument("patterns", type=Path)
    parser.add_argument("--capture-kind", choices=("standalone", "production"),
                        default="standalone")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    memory = args.ram.read_bytes()
    definition = json.loads(args.patterns.read_text())
    if len(memory) != 65536:
        raise ValueError("Expected a raw 65,536-byte RAM capture.")
    patterns = definition["patterns"]
    odd = bytes(int(p["odd_hex"], 16) for p in patterns)
    even = bytes(int(p["even_hex"], 16) for p in patterns)
    tables_match = memory[0x400:0x418] == odd + even
    checks = []
    for base in (0xD800, 0xE000, 0xE800):
        for pattern in patterns:
            expected = bytes((int(pattern["even_hex"], 16),
                              int(pattern["odd_hex"], 16))) * 4
            address = base + pattern["id"] * 8
            actual = memory[address:address + 8]
            checks.append({"charset": base, "pattern": pattern["id"],
                           "address": address, "bytes": actual.hex(" "),
                           "match": actual == expected})
    receipt = {
        "ram_file": str(args.ram),
        "ram_sha256": hashlib.sha256(memory).hexdigest(),
        "definition_file": str(args.patterns),
        "definition_sha256": hashlib.sha256(args.patterns.read_bytes()).hexdigest(),
        "source_sha256": definition["source_sha256"],
        "relocated_tables_match": tables_match,
        "glyph_checks": checks,
        "pass": tables_match and len(checks) == 36 and all(c["match"] for c in checks),
        "scope": f"Reserved patterns in {args.capture_kind} RAM; no frame-timing assertion"}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"pass": receipt["pass"], "tables": tables_match,
                      "matching_glyphs": sum(c["match"] for c in checks)}))
    if not receipt["pass"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
