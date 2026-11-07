#!/usr/bin/env python3
"""Inventory proven decoded ranges and entry-seeded static code, not packed data."""

import json
from pathlib import Path

from static_loader import decode


def reachable(memory, known, entries):
    pending, seen = list(entries), {}
    while pending:
        pc = pending.pop()
        while known[pc] and pc not in seen:
            item = decode(memory, pc)
            seen[pc] = item
            if item["mode"] == "r" or item["mnemonic"] == "JSR":
                pending.append(item["target"])
            if item["mnemonic"] == "JMP":
                if item["mode"] != "q":
                    pending.append(item["target"])
                break
            if item["mnemonic"] in ("RTS", "RTI", "BRK", "KIL"):
                break
            pc = item["next"]
    return [seen[pc] for pc in sorted(seen)]


def main():
    root = Path("build/research/tower-power/static")
    rows = json.loads((root / "unpacked-index.json").read_text())
    output = root / "parts"
    output.mkdir(exist_ok=True)
    report = []
    for row in rows:
        if not row["pass"]:
            continue
        prefix = Path(row["output_prefix"])
        memory = prefix.with_suffix(".memory.bin").read_bytes()
        known = prefix.with_suffix(".known.bin").read_bytes()
        item = {"source": row["source"], "prefix": str(prefix), "ranges": row["ranges"]}
        entries = []
        if all(known[0xc2f0:0xc2f4]):
            entry = int.from_bytes(memory[0xc2f0:0xc2f2], "little")
            irq = int.from_bytes(memory[0xc2f2:0xc2f4], "little")
            item.update(entry=entry, irq=irq, entry_in_this_payload=bool(known[entry]),
                        irq_in_this_payload=bool(known[irq]))
            entries = [entry, irq]
        code = reachable(memory, known, entries)
        listing = ["Static entry/IRQ reachability only; indirect/SMC targets unresolved."]
        listing += [f"{x['address']:04x}: {x['bytes']:<8} {x['mnemonic']} {x['text']}" for x in code]
        (output / (prefix.name + ".asm")).write_text("\n".join(listing) + "\n")
        (output / (prefix.name + ".json")).write_text(json.dumps(code, indent=2) + "\n")
        item.update(instruction_count=len(code),
                    direct_calls=sorted({x["target"] for x in code if x["mnemonic"] == "JSR"}),
                    indirect_jumps=[{"pc": x["address"], "pointer": x["operand"]} for x in code if x["mnemonic"] == "JMP" and x["mode"] == "q"],
                    vic_writes=[{"pc": x["address"], "target": x["operand"]} for x in code if x["mnemonic"] in ("STA", "STX", "STY") and x["mode"] in ("w", "wx", "wy") and 0xd000 <= x["operand"] < 0xd040])
        report.append(item)
        if entries:
            print(prefix.name, f"entry={entry:04x} irq={irq:04x}", len(code), "instructions", "calls=" + ",".join(f"{a:04x}" for a in item["direct_calls"]))
    (root / "parts-index.json").write_text(json.dumps(report, indent=2) + "\n")


if __name__ == "__main__":
    main()
