#!/usr/bin/env python3
"""Recover Lunatico's original technical note with its own line decoder.

The release ZIP is reused from a verified local archive. Only the RAM-only
line decoder is executed; no VSP tool, music, hardware, startup or demo part.
"""

import hashlib
import importlib.metadata
import json
import struct
import zipfile
import zlib
from pathlib import Path

from py65.devices.mpu6502 import MPU


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/research/lunatico-rain"
ZIP = ROOT / "build/research/frontier-followup/lunatico.zip"
ZIP_SHA256 = "1e22a02eeef77d98a8c348b03cbb808b489b3cf842d14db25dbf72f79eb9e6c0"
NOTE_SHA256 = "66a74aa174c936c3c53366f9e620c0b6edddfd04c45472f18551affca0ce9f60"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def sector_count(track):
    assert 1 <= track <= 35
    return 21 if track <= 17 else 19 if track <= 24 else 18 if track <= 30 else 17


def sector(disk, track, number):
    assert 0 <= number < sector_count(track)
    offset = 256 * (sum(sector_count(t) for t in range(1, track)) + number)
    return disk[offset:offset + 256]


def acquire_note():
    assert digest(ZIP.read_bytes()) == ZIP_SHA256
    with zipfile.ZipFile(ZIP) as zipped:
        disk = zipped.read("lft-lunatico/lft-lunatico-side1.d64")
    (OUTPUT / "lft-lunatico-side1.d64").write_bytes(disk)
    track, number, seen = 18, 1, set()
    start = None
    while track:
        assert (track, number) not in seen
        seen.add((track, number))
        block = sector(disk, track, number)
        for index in range(8):
            row = block[index * 32:(index + 1) * 32]
            if row[2] & 7 == 2 and row[5:21].rstrip(b"\xa0 ") == b"NOTE & VSP TOOL":
                assert start is None
                start = tuple(row[3:5])
        track, number = block[:2]
    assert start is not None
    track, number = start
    links, raw = [], bytearray()
    while track:
        assert (track, number) not in links
        links.append((track, number))
        block = sector(disk, track, number)
        raw.extend(block[2:] if block[0] else block[2:block[1] + 1])
        track, number = block[:2]
    assert digest(raw) == NOTE_SHA256 and len(raw) == 23064
    (OUTPUT / "note-vsp.prg").write_bytes(raw)
    return bytes(raw), {"reused_zip": str(ZIP.relative_to(ROOT)), "zip_sha256": ZIP_SHA256,
                        "disk_sha256": digest(disk), "note_sha256": NOTE_SHA256,
                        "note_bytes": len(raw), "note_dos_chain": links}


class Cpu(MPU):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instruct = list(self.instruct)
        self.cycletime = list(self.cycletime)
        self.instruct[0x80] = self.nop_immediate
        self.cycletime[0x80] = 2

    @staticmethod
    def nop_immediate(cpu):
        cpu.ByteAt(cpu.pc)
        cpu.pc += 1


class Memory:
    def __init__(self, blob):
        self.data, self.known = bytearray(65536), bytearray(65536)
        load = int.from_bytes(blob[:2], "little")
        self.data[load:load + len(blob) - 2] = blob[2:]
        self.known[load:load + len(blob) - 2] = b"\1" * (len(blob) - 2)
        self.pc = None
        self.reads, self.writes = set(), set()

    def __getitem__(self, address):
        assert not 0xD000 <= address < 0xE000, "Hardware address forbidden"
        assert self.known[address], (hex(self.pc or 0), "unknown read", hex(address))
        self.reads.add(address)
        return self.data[address]

    def __setitem__(self, address, value):
        assert not 0xD000 <= address < 0xE000, "Hardware address forbidden"
        self.data[address], self.known[address] = value, 1
        self.writes.add(address)


def decode_line(blob, pointer):
    memory = Memory(blob)
    for address, value in ((0x20, (pointer + 2) & 255), (0x21, (pointer + 2) >> 8), (2, 0), (3, 0xF0)):
        memory[address] = value
    cpu = Cpu(memory=memory, pc=0x1928)
    cpu.p, cpu.sp = cpu.UNUSED, 255
    cpu.stPushWord(0x1FFE)
    for steps in range(100_000):
        if cpu.pc == 0x1FFF:
            break
        assert 0x1928 <= cpu.pc <= 0x19C4, hex(cpu.pc)
        opcode = memory.data[cpu.pc]
        assert cpu.instruct[opcode].__name__ != "inst_not_implemented", hex(opcode)
        memory.pc = cpu.pc
        cpu.step()
    else:
        raise AssertionError("Line decoder did not return within bound")
    assert all(address in memory.writes for address in range(0xF000, 0xF026))
    return bytes(memory.data[0xF000:0xF026]), steps


def display(codes):
    alphabet = "0123456789abcdefghijklmnopqrstuvwxyz"
    punctuation = {36: "-", 37: "+", 38: "=", 39: "*", 40: "/", 41: "&", 42: ":", 43: ".",
                   44: ",", 45: "!", 55: "'", 56: "?", 58: "(", 59: ")", 61: " ", 63: " "}
    return "".join(alphabet[value & 63] if value & 63 < len(alphabet) else punctuation.get(value & 63, f"{{{value & 63}}}") for value in codes).rstrip()


def render_font(original):
    """Analysis glyph sheet from original font bytes; no screenshot/photo edits."""
    font = original[0x0F3C:0x113C]
    width, height = 656, 752
    pixels = bytearray([220] * (width * height * 3))

    def glyph(code, x, y, scale):
        for yy, value in enumerate(font[code * 8:code * 8 + 8]):
            for xx in range(8):
                colour = 255 if value & (128 >> xx) else 0
                for sy in range(scale):
                    for sx in range(scale):
                        offset = 3 * ((y + yy * scale + sy) * width + x + xx * scale + sx)
                        pixels[offset:offset + 3] = bytes([colour] * 3)

    for code in range(64):
        x, y = code % 8 * 82, code // 8 * 94
        glyph(code, x + 8, y + 2, 8)
        glyph(code // 10, x + 20, y + 72, 2)
        glyph(code % 10, x + 36, y + 72, 2)

    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    scan = b"".join(b"\0" + pixels[y * width * 3:(y + 1) * width * 3] for y in range(height))
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(scan)) + chunk(b"IEND", b"")
    (OUTPUT / "note-glyphs.png").write_bytes(png)
    return {"source_range": [0xF3C, 0x113C], "font_sha256": digest(font), "glyph_sheet_sha256": digest(png)}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    blob, acquisition = acquire_note()
    original = Memory(blob).data
    font = render_font(original)
    pointer, previous, lines = 0x1A80, 0, []
    while pointer < 0x44A8 and len(lines) < 1000:
        back, forward = original[pointer:pointer + 2]
        assert back == previous, (hex(pointer), back, previous)
        if not forward:
            break
        assert forward >= 3
        codes, steps = decode_line(blob, pointer)
        lines.append({"line": len(lines) + 1, "record_address": pointer,
                      "record_bytes": forward, "screen_codes_hex": codes.hex(" "),
                      "text": display(codes), "cpu_steps": steps})
        previous, pointer = forward, pointer + forward
    else:
        raise AssertionError("No bounded note terminator")
    assert lines
    text = "\n".join(row["text"] for row in lines) + "\n"
    (OUTPUT / "note-decoded.txt").write_text(text)
    result = {"pass": True, "script_sha256": digest(Path(__file__).read_bytes()),
              "py65_version": importlib.metadata.version("py65"), "acquisition": acquisition,
              "lines": lines, "decoded_text_sha256": digest(text.encode()),
              "terminator_record": pointer, "total_cpu_steps": sum(row["cpu_steps"] for row in lines),
              "scope": "Original $1928..$19C4 text-line decoder; CPU extension $80 immediate NOP; explicit source/output pointer inputs, no hardware/music/VSP/whole-note or rain effect execution",
              "font": font,
              "character_mapping": "Glyph sheet visually checked:0..9 digits,10..35 alphabet, punctuation mapped by glyph;63 space. Letter case normalized to lowercase; high colour bits retained in raw screen_codes_hex. Unmapped graphical symbols stay numerical."}
    (OUTPUT / "note-receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"lines": len(lines), "total_cpu_steps": result["total_cpu_steps"],
                      "terminator_record": hex(pointer), "decoded_text_sha256": result["decoded_text_sha256"]}, indent=2))
    print("\n".join(row["text"] for row in lines[:25]))


if __name__ == "__main__":
    main()
