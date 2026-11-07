#!/usr/bin/env python3
"""Compare lft's inline assembly with the pinned release; annotate all bytes.

Author work: https://www.linusakesson.net/scene/a-mind-is-born/index.php
The author licenses the work CC BY-NC-SA4.0. Raw author HTML/code/binary and
derived full listings remain ignored artifacts; this tracked analysis is ours.
No untrusted downloaded code is executed and no C64/emulator is launched.
"""

import ast
import hashlib
import importlib.util
import json
import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/research/a-mind-is-born"
PRG_SHA = "7da29c8eed5acc39c5a1d3f0d40f5057c516cb6d2a04a18b15d71e6f8903f1f5"
URL = "https://www.linusakesson.net/scene/a-mind-is-born/index.php"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class Blocks(HTMLParser):
    def __init__(self):
        super().__init__()
        self.inside = False
        self.buffer = []
        self.blocks = []

    def handle_starttag(self, tag, attributes):
        if tag == "pre":
            self.inside, self.buffer = True, []

    def handle_endtag(self, tag):
        if tag == "pre":
            self.blocks.append("".join(self.buffer))
            self.inside = False

    def handle_data(self, data):
        if self.inside:
            self.buffer.append(data)


def expression(text, symbols):
    tree = ast.parse(re.sub(r"\$([0-9a-f]+)", r"0x\1", text), mode="eval")

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return node.value
        if isinstance(node, ast.Name):
            return symbols[node.id]
        if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Add, ast.Sub, ast.Mult)):
            left, right = visit(node.left), visit(node.right)
            return left + right if isinstance(node.op, ast.Add) else left - right if isinstance(node.op, ast.Sub) else left * right
        raise ValueError(ast.dump(node))

    return visit(tree)


def assemble_fragment(source, origin, symbols, opcodes):
    """Small two-pass assembler only for the article's demonstrated syntax."""
    statements = []
    for line in source.splitlines():
        line = line.split(";", 1)[0].strip().lower()
        if not line:
            continue
        if " " not in line and line not in {name.lower() for name, _ in opcodes}:
            statements.append(("label", line))
        else:
            pieces = line.split(None, 1)
            statements.append((pieces[0], pieces[1] if len(pieces) == 2 else ""))
    labels = dict(symbols)

    def instruction(name, operand, pc):
        name = {"asr": "alr", "sbx": "axs"}.get(name, name).upper()
        operand = operand.replace(" ", "")
        if name in ("LSR", "ROR", "ASL", "ROL") and not operand:
            mode, value = "a", 0
        elif not operand:
            mode, value = "i", 0
        elif name in ("BCC", "BCS", "BEQ", "BNE", "BPL", "BMI"):
            mode, value = "r", expression(operand, labels)
        elif operand.startswith("#"):
            mode, value = "n", expression(operand[1:], labels)
        elif operand.startswith("(") and operand.endswith("),y"):
            mode, value = "iy", expression(operand[1:-3], labels)
        elif operand.startswith("(") and operand.endswith(")"):
            mode, value = "q", expression(operand[1:-1], labels)
        else:
            suffix = operand[-2:] if operand.endswith((",x", ",y")) else ""
            value = expression(operand[:-2] if suffix else operand, labels)
            mode = ("z" if value <= 255 and name not in ("JMP", "JSR") else "w") + suffix[-1:]
        options = [i for i, pair in enumerate(opcodes) if pair == [name, mode]]
        assert options, (name, mode, operand)
        opcode = 0xEA if name == "NOP" and mode == "i" else options[0]
        size = {"i": 1, "a": 1, "w": 3, "wx": 3, "wy": 3, "q": 3}.get(mode, 2)
        if mode == "r":
            displacement = value - pc - 2
            assert -128 <= displacement < 128
            value = displacement & 255
        return bytes((opcode,)) + (value.to_bytes(2 if size == 3 else 1, "little") if size > 1 else b"")

    # Author labels are forward references; their instruction widths are fixed
    # by supplied constants/modes. Supply the named boundary labels explicitly,
    # then independently assert every locally declared address in the first pass.
    pc = origin
    for name, operand in statements:
        if name == "label":
            if operand in labels:
                assert labels[operand] == pc, (operand, labels[operand], pc)
            labels[operand] = pc
        else:
            pc += 1 if name == ".byt" else len(instruction(name, operand, pc))
    output, pc = bytearray(), origin
    for name, operand in statements:
        if name == "label":
            continue
        data = bytes((expression(operand, labels),)) if name == ".byt" else instruction(name, operand, pc)
        output.extend(data)
        pc += len(data)
    return bytes(output)


def byte_roles(offset):
    roles = []
    for low, high, name in [(2, 14, "BASIC header/SYS/end marker"),
                            (11, 36, "SID shadow"), (0x22, 0x32, "script"),
                            (0x32, 0xB3, "IRQ code"), (0xB2, 0xCD, "initialization including shared NOP"),
                            (0xCD, 0xF4, "main visual code"), (0xF4, 0xF8, "bass table"),
                            (0xF8, 0x100, "melody table")]:
        if low <= offset < high:
            roles.append(name)
    if 0x12 <= offset <= 0x16:
        roles.append("VIC palette shadow")
    specific = {4: "D3FF indirect SID base low / BASIC line-number low",
                5: "D3FF indirect SID base high / BASIC line-number high",
                0x10: "D01C indirect VIC base low / voice1 attack-decay",
                0x11: "D01C indirect VIC base high / voice1 sustain-release",
                0x14: "clock low / voice2 pulsewidth low / palette entry",
                0x15: "melody LFSR / voice2 pulsewidth high / palette entry",
                0x16: "voice2 waveform / palette entry / script target",
                0x21: "clock high / SID filter cutoff high",
                0x22: "filter resonance/routes / script targetFF",
                0x23: "filter mode/volume / script first value",
                0x73: "LAX#0 alternate entry inside normal AND absolute operand",
                0x74: "LAX immediate zero / normal AND absolute high operand",
                0xAC: "constant03 for normal bass AND / SID-store operand",
                0xB2: "IRQ JMP-ROM high operandEA / startup NOP",
                0xCC: "init JMP operand00 / video pointer low",
                0xCD: "executed-once LDA opcodeA9 / video pointer high",
                0xD6: "script-modified LDY/BIT/AND opcode / matrix OR mask",
                0xD8: "script-modified ORA/ADC opcode / envelope operation"}
    if offset in specific:
        roles.append(specific[offset])
    assert roles, offset
    return roles


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    blob = (ROOT / "build/research/frontier/a_mind_is_born.prg").read_bytes()
    assert len(blob) == 256 and sha(blob) == PRG_SHA
    html = (OUTPUT / "author.html").read_bytes()
    parser = Blocks()
    parser.feed(html.decode())
    assert len(parser.blocks) == 18 and parser.blocks[0].strip() == "54271 SYS2225"
    utility = module(ROOT / "research/tower-power/static_loader.py", "nmos_opcodes")
    symbols = dict(sid=0x0A, const_d3ff=3, const_d01c=0x0F, clock=0x13,
                   mel_lfsr=0x14, clock_msb=0x20, script=0x21, vmptr=0xCB,
                   mod_op1=0xD5, mod_op2=0xD7, basstbl=0xF3, freqtbl=0xF7,
                   mainloop=0xD2, initloop=0x08BE, noc1=0x39, highpass=0x4B,
                   noend=0x51, noduck=0x5D, nointro=0x65, bassoff=0x72,
                   bassdone=0x87, noc2=0x97, nomel=0x9E, vicloop=0xA0, loop=0xA8)
    comparisons = []
    unique = set()
    for name, indices, origin, loaded in [("IRQ", range(6, 18), 0x31, 0x0831),
                                         ("startup", [1], 0x08B1, 0x08B1),
                                         ("main", range(2, 6), 0xCC, 0x08CC)]:
        source = "\n".join(parser.blocks[i] for i in indices)
        data = assemble_fragment(source, origin, symbols, utility.OPCODES)
        file_offset = loaded - 0x07FF
        assert blob[file_offset:file_offset + len(data)] == data, name
        unique.update(range(file_offset, file_offset + len(data)))
        comparisons.append({"name": name, "article_blocks": list(indices),
                            "assembled_origin": origin, "loaded_address": loaded,
                            "bytes": len(data), "sha256": sha(data), "pass": True})
    rows, listing = [], []
    for offset in range(2, 256):
        row = {"file_offset": offset, "byte": blob[offset],
               "loaded_address": offset + 0x07FF, "nominal_relocated_address": offset - 1,
               "copied_by_init": offset >= 4, "roles": byte_roles(offset)}
        rows.append(row)
        listing.append(f"file{offset:02x} load{row['loaded_address']:04x} zp{offset-1:02x}  {blob[offset]:02x}  " + "; ".join(row["roles"]))
    result = {"pass": True, "script_sha256": sha(Path(__file__).read_bytes()),
              "opcode_table_script_sha256": sha((ROOT / "research/tower-power/static_loader.py").read_bytes()),
              "author_url": URL, "author_html_sha256": sha(html),
              "author_code_blocks_sha256": sha(json.dumps(parser.blocks, ensure_ascii=False).encode()),
              "author_license": "https://creativecommons.org/licenses/by-nc-sa/4.0/",
              "prg_url": "https://hd0.linusakesson.net/files/a_mind_is_born.prg",
              "prg_sha256": sha(blob), "file_bytes": len(blob), "payload_bytes": len(blob) - 2,
              "load_address": int.from_bytes(blob[:2], "little"),
              "source_assembly_matches": comparisons, "unique_source_code_bytes_matched": len(unique),
              "literal_basic_next_pointer": int.from_bytes(blob[2:4], "little"),
              "author_prose_next_pointer": 0x080B,
              "basic_discrepancy_scope": "Literal080D in pinned release vs080B in author prose; no BASIC-ROM execution tested here",
              "relocation_scope": "Original copy coversZP03..FF, reading0803..08FF;08FF is one byte beyond loaded payload, ZP00..02 preserved",
              "payload_byte_map": rows}
    (OUTPUT / "payload-annotated.txt").write_text(
        "A Mind Is Born by Linus Akesson/lft. Derived byte-role annotation, not original assembly formatting.\n"
        + URL + "\nhttps://creativecommons.org/licenses/by-nc-sa/4.0/\n"
        + "\n".join(listing) + "\n")
    (OUTPUT / "source-byte-proof.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({k: v for k, v in result.items() if k != "payload_byte_map"}, indent=2))


if __name__ == "__main__":
    main()
