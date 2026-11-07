#!/usr/bin/env python3
"""Decode only statically reachable Tower Power boot/loader instructions.

No C64 instructions are executed. The verified boot copy maps $2100..$25ff to
$c000..$c4ff; traversal starts at actual boot calls $c010 and $c300. Indirect
jumps, self modification, drive code and packed streams require further proof.
"""

import argparse
import hashlib
import json
from pathlib import Path


# NMOS 6502/6510 opcode matrix. Unknown/unstable instructions are named rather
# than silently decoded as data. Addressing modes determine instruction length.
ROWS = [
    "BRK.i ORA.ix KIL.i SLO.ix NOP.z ORA.z ASL.z SLO.z PHP.i ORA.n ASL.a ANC.n NOP.w ORA.w ASL.w SLO.w",
    "BPL.r ORA.iy KIL.i SLO.iy NOP.zx ORA.zx ASL.zx SLO.zx CLC.i ORA.wy NOP.i SLO.wy NOP.wx ORA.wx ASL.wx SLO.wx",
    "JSR.w AND.ix KIL.i RLA.ix BIT.z AND.z ROL.z RLA.z PLP.i AND.n ROL.a ANC.n BIT.w AND.w ROL.w RLA.w",
    "BMI.r AND.iy KIL.i RLA.iy NOP.zx AND.zx ROL.zx RLA.zx SEC.i AND.wy NOP.i RLA.wy NOP.wx AND.wx ROL.wx RLA.wx",
    "RTI.i EOR.ix KIL.i SRE.ix NOP.z EOR.z LSR.z SRE.z PHA.i EOR.n LSR.a ALR.n JMP.w EOR.w LSR.w SRE.w",
    "BVC.r EOR.iy KIL.i SRE.iy NOP.zx EOR.zx LSR.zx SRE.zx CLI.i EOR.wy NOP.i SRE.wy NOP.wx EOR.wx LSR.wx SRE.wx",
    "RTS.i ADC.ix KIL.i RRA.ix NOP.z ADC.z ROR.z RRA.z PLA.i ADC.n ROR.a ARR.n JMP.q ADC.w ROR.w RRA.w",
    "BVS.r ADC.iy KIL.i RRA.iy NOP.zx ADC.zx ROR.zx RRA.zx SEI.i ADC.wy NOP.i RRA.wy NOP.wx ADC.wx ROR.wx RRA.wx",
    "NOP.n STA.ix NOP.n SAX.ix STY.z STA.z STX.z SAX.z DEY.i NOP.n TXA.i XAA.n STY.w STA.w STX.w SAX.w",
    "BCC.r STA.iy KIL.i AHX.iy STY.zx STA.zx STX.zy SAX.zy TYA.i STA.wy TXS.i TAS.wy SHY.wx STA.wx SHX.wy AHX.wy",
    "LDY.n LDA.ix LDX.n LAX.ix LDY.z LDA.z LDX.z LAX.z TAY.i LDA.n TAX.i LAX.n LDY.w LDA.w LDX.w LAX.w",
    "BCS.r LDA.iy KIL.i LAX.iy LDY.zx LDA.zx LDX.zy LAX.zy CLV.i LDA.wy TSX.i LAS.wy LDY.wx LDA.wx LDX.wy LAX.wy",
    "CPY.n CMP.ix NOP.n DCP.ix CPY.z CMP.z DEC.z DCP.z INY.i CMP.n DEX.i AXS.n CPY.w CMP.w DEC.w DCP.w",
    "BNE.r CMP.iy KIL.i DCP.iy NOP.zx CMP.zx DEC.zx DCP.zx CLD.i CMP.wy NOP.i DCP.wy NOP.wx CMP.wx DEC.wx DCP.wx",
    "CPX.n SBC.ix NOP.n ISC.ix CPX.z SBC.z INC.z ISC.z INX.i SBC.n NOP.i SBC.n CPX.w SBC.w INC.w ISC.w",
    "BEQ.r SBC.iy KIL.i ISC.iy NOP.zx SBC.zx INC.zx ISC.zx SED.i SBC.wy NOP.i ISC.wy NOP.wx SBC.wx INC.wx ISC.wx",
]
OPCODES = [token.split(".") for row in ROWS for token in row.split()]
SIZES = {"i": 1, "a": 1, "n": 2, "z": 2, "zx": 2, "zy": 2,
         "ix": 2, "iy": 2, "r": 2, "w": 3, "wx": 3, "wy": 3, "q": 3}


def decode(memory, pc):
    mnemonic, mode = OPCODES[memory[pc]]
    size = SIZES[mode]
    raw = bytes(memory[pc:pc + size])
    operand = raw[1] if size == 2 else int.from_bytes(raw[1:], "little")
    target = None
    if mode == "r":
        target = (pc + 2 + (operand if operand < 128 else operand - 256)) & 0xffff
        text = f"${target:04x}"
    elif mode == "i":
        text = ""
    elif mode == "a":
        text = "A"
    elif mode == "n":
        text = f"#${operand:02x}"
    elif mode in ("z", "zx", "zy"):
        text = f"${operand:02x}" + {"z": "", "zx": ",X", "zy": ",Y"}[mode]
    elif mode in ("ix", "iy"):
        text = f"(${operand:02x},X)" if mode == "ix" else f"(${operand:02x}),Y"
    else:
        text = f"${operand:04x}" + {"w": "", "wx": ",X", "wy": ",Y", "q": ""}[mode]
        if mode == "q":
            text = f"({text})"
        elif mnemonic in ("JSR", "JMP"):
            target = operand
    return {"address": pc, "bytes": raw.hex(" "), "mnemonic": mnemonic,
            "mode": mode, "operand": operand, "text": text, "target": target,
            "next": (pc + size) & 0xffff}


def traverse(memory, entries, low, high):
    pending, instructions = list(entries), {}
    while pending:
        pc = pending.pop()
        while low <= pc < high and pc not in instructions:
            item = decode(memory, pc)
            instructions[pc] = item
            mnemonic = item["mnemonic"]
            if item["mode"] == "r" or mnemonic == "JSR":
                if item["target"] is not None:
                    pending.append(item["target"])
            if mnemonic == "JMP":
                if item["mode"] != "q":
                    pending.append(item["target"])
                break
            if mnemonic in ("RTS", "RTI", "BRK", "KIL"):
                break
            pc = item["next"]
    return [instructions[pc] for pc in sorted(instructions)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("build/research/tower-power"))
    args = parser.parse_args()
    root = args.root
    output = root / "static"
    output.mkdir(parents=True, exist_ok=True)
    boot = root / "side1/>>tower power!<<"
    blob = boot.read_bytes()
    memory = bytearray(65536)
    start = int.from_bytes(blob[:2], "little")
    memory[start:start + len(blob) - 2] = blob[2:]
    loader = bytes(memory[0x2100:0x2600])
    memory[0xc000:0xc500] = loader
    (output / "loader-c000.bin").write_bytes(loader)
    rows = traverse(memory, [0xc010, 0xc300], 0xc010, 0xc500)
    listing = ["Static reachability from boot-confirmed loader entries; not a runtime trace."]
    for item in rows:
        listing.append(f"{item['address']:04x}: {item['bytes']:<8} {item['mnemonic']} {item['text']}")
    (output / "loader-reachable.asm").write_text("\n".join(listing) + "\n")
    report = {"boot_file": str(boot), "boot_sha256": hashlib.sha256(blob).hexdigest(),
              "boot_load": start, "copy_source": [0x2100, 0x2600],
              "copy_destination": [0xc000, 0xc500],
              "loader_sha256": hashlib.sha256(loader).hexdigest(),
              "entry_points": [0xc010, 0xc300], "instructions": rows,
              "limitations": ["No execution", "Indirect targets unresolved",
                              "Self-modification may change instruction targets",
                              "No packed stream interpreted as code"]}
    (output / "loader-analysis.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key != "instructions"}, indent=2))
    print(f"Decoded {len(rows)} statically reachable instructions.")


if __name__ == "__main__":
    main()
