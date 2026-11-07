#!/usr/bin/env python3
"""Extract The Lab's note from a raw 64K RAM capture of its original reader.

The input is a runtime capture, not a decoder for the packed disk image. The
reader at $0880 distinguishes $FF page boundaries, $FE end, and $FC commands.
Only the four-byte $FC command form present in this note is supported. Display
color and inverse attributes are recorded separately from the readable text.
"""

import argparse
import hashlib
import json
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def extract(memory, start=0x6800):
    if len(memory) != 65536:
        raise ValueError("Expected a raw 65,536-byte RAM capture.")
    # This is the original reader's dispatch, not a guessed string delimiter.
    if memory[0x884:0x890] != bytes.fromhex("c9 ff f0 28 c9 fe f0 16 c9 fc f0 0c"):
        raise ValueError("The expected original note-reader dispatch is absent.")
    pages = []
    controls = []
    page_start = start
    line = []
    position = start
    while position < len(memory):
        address = position
        value = memory[position]
        position += 1
        if value == 0xFE:
            pages.append({"address": page_start, "text": "".join(line)})
            return pages, controls, position
        if value == 0xFF:
            pages.append({"address": page_start, "text": "".join(line)})
            page_start = position
            line = []
        elif value == 0xFC:
            parameters = memory[position:position + 3]
            if len(parameters) != 3 or parameters[0] >= 0x11:
                raise ValueError(f"Unsupported $FC command at ${address:04X}.")
            controls.append({"address": address, "parameters": list(parameters)})
            position += 3
        elif value == 0:
            line.append("\n")
        else:
            # The note uses the C64's mixed-case screen-code arrangement.
            # Bit 7 selects inverse styling; removing it preserves the letter.
            code = value & 0x7F
            if 1 <= code <= 26:
                line.append(chr(code + 96))
            elif 32 <= code <= 95:
                line.append(chr(code))
            else:
                # Do not silently invent a custom-font symbol.
                line.append(f"<{value:02X}>")
    raise ValueError("No $FE note terminator found before the end of RAM.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ram", type=Path)
    parser.add_argument("--compare", type=Path,
                        help="Optional second capture; require identical note bytes.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    memory = args.ram.read_bytes()
    pages, controls, end = extract(memory)
    start = 0x6800
    comparison = None
    if args.compare:
        other = args.compare.read_bytes()
        if len(other) != 65536 or other[start:end] != memory[start:end]:
            raise ValueError("The note region differs between the two captures.")
        comparison = {"file": str(args.compare), "sha256": digest(other),
                      "note_bytes_equal": True}
    args.output.mkdir(parents=True, exist_ok=True)
    text = "\n\n".join(
        f"PAGE {number}, CPU ${page['address']:04X}\n{page['text']}"
        for number, page in enumerate(pages, 1)) + "\n"
    (args.output / "note-pages.txt").write_text(text)
    (args.output / "note-raw.bin").write_bytes(memory[start:end])
    receipt = {
        "ram_file": str(args.ram), "ram_sha256": digest(memory),
        "start": start, "end_exclusive": end,
        "note_bytes": end - start, "note_sha256": digest(memory[start:end]),
        "pages": len(pages), "controls": controls,
        "comparison": comparison,
        "reader_dispatch": {"address": 0x884,
                            "bytes": memory[0x884:0x890].hex(" ")},
        "limitations": ["Runtime RAM extraction, not a standalone disk depacker",
                        "Custom-font symbols retain explicit hexadecimal markers",
                        "Styling and layout are not reproduced by the text export"]}
    (args.output / "note-extraction.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({key: receipt[key] for key in (
        "ram_sha256", "start", "end_exclusive", "note_bytes", "note_sha256", "pages")}))


if __name__ == "__main__":
    main()
