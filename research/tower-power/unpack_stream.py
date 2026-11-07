#!/usr/bin/env python3
"""Offline translation of Tower Power's $c023..$c177 packed-stream decoder.

This does not execute 6502 code or emulate disk I/O. The loader's raw-byte
reader is modeled as file bytes after the two-byte PRG prefix, with its eager
LSB-bit refill preserved. Outputs remain provisional until checked against
the original loader's RAM writes. Unknown back-reference sources are reported.
"""

import argparse
import hashlib
import json
from pathlib import Path


class Decoder:
    def __init__(self, blob):
        self.blob = blob
        self.pos = 2
        self.memory = bytearray(65536)
        self.known = bytearray(65536)
        self.written = bytearray(65536)
        self.commands = []
        self.destination = 0
        self.total = 0
        self.unknown_reads = []
        self.remaining = self.byte()
        self.bits = self.byte()
        if not 1 <= self.remaining <= 8:
            raise ValueError(f"Invalid initial bit count: {self.remaining}")

    def byte(self):
        if self.pos >= len(self.blob):
            raise EOFError(f"Raw byte at file offset {self.pos:#x}")
        value = self.blob[self.pos]
        self.pos += 1
        return value

    def word(self):
        low = self.byte()
        return low | self.byte() << 8

    def bit(self):
        # $c156 first shifts, THEN eagerly reads the following bit byte when
        # the count reaches zero, while retaining the old LSR carry result.
        value = self.bits & 1
        self.bits >>= 1
        self.remaining -= 1
        if self.remaining == 0:
            self.remaining = 8
            self.bits = self.byte()
        return value

    def bit_value(self, count):
        value = 0
        for _ in range(count):
            value = (value << 1) | self.bit()
        return value

    def length(self, base):
        # Literal base=5, match base=4; escape 11 returns a raw byte directly.
        if self.bit():
            if self.bit():
                return self.byte()
            return base + 5 + self.bit_value(3)
        if not self.bit():
            return base + self.bit()
        if not self.bit():
            return base + 2
        return base + 3 + self.bit()

    def offset(self, long_allowed):
        if long_allowed and self.bit():
            return self.word()
        low = self.byte()
        return low | self.bit_value(1) << 8

    def put(self, value, known=True):
        self.memory[self.destination] = value
        self.known[self.destination] = bool(known)
        self.written[self.destination] = 1
        self.destination = (self.destination + 1) & 0xffff
        self.total += 1
        if self.total > 1024 * 1024:
            raise ValueError("Output safety limit exceeded")

    def run(self):
        count_high = 0
        match_only = False
        for _ in range(200000):
            command_pos = self.pos
            # Finishing a literal run falls through $c06d, not back to $c02e:
            # its following match/control omits the leading two dispatch bits.
            first = 1 if match_only else self.bit()
            second = 1 if match_only else self.bit()
            if first and second:
                if not self.bit():
                    length = 2
                    offset = self.offset(False)
                elif not self.bit():
                    length = 3
                    offset = self.offset(True)
                else:
                    length = self.length(4)
                    if length == 1:
                        self.destination = self.word()
                        self.commands.append({"kind": "destination", "file_offset": command_pos,
                                              "destination": self.destination})
                        match_only = False
                        continue
                    if length == 2:
                        self.commands.append({"kind": "end", "file_offset": command_pos})
                        return
                    offset = self.offset(True)
                length = length or 65536
                source = (self.destination - offset - 1) & 0xffff
                self.commands.append({"kind": "match", "file_offset": command_pos,
                                      "destination": self.destination, "source": source,
                                      "distance": offset + 1, "length": length})
                for _ in range(length):
                    if not self.known[source] and len(self.unknown_reads) < 32:
                        self.unknown_reads.append({"source": source, "destination": self.destination})
                    self.put(self.memory[source], self.known[source])
                    source = (source + 1) & 0xffff
                match_only = False
            else:
                if first:
                    length = 1
                elif second:
                    length = 2 if not self.bit() else 3 + self.bit()
                else:
                    length = self.length(5)
                    if length == 3:
                        # Literal-count escape at $c041 writes $03/$04, then
                        # $c060 stores the returned HIGH byte into $03 again.
                        # Preserve that literal machine-code behavior, even
                        # though the streams tested may never use this escape.
                        word = self.word()
                        count_high = word >> 8
                        length = count_high
                length = (count_high << 8) | length
                length = length or 65536
                self.commands.append({"kind": "literal", "file_offset": command_pos,
                                      "destination": self.destination, "length": length})
                for _ in range(length):
                    self.put(self.byte())
                count_high = 0
                match_only = True
        raise ValueError("Command safety limit exceeded")


def ranges(bitmap):
    result = []
    start = None
    for address, value in enumerate([*bitmap, 0]):
        if value and start is None:
            start = address
        if not value and start is not None:
            result.append([start, address])
            start = None
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path("build/research/tower-power"))
    args = parser.parse_args()
    root = args.root
    output = root / "static/unpacked"
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for item in json.loads((root / "files.json").read_text()):
        if item["name"] in (">>tower power!<<", "tower note!     ", "win386.swp"):
            continue
        source = Path(item["file"])
        blob = source.read_bytes()
        name = f"side{item['side']}-" + (item["name"][:2] if item["side"] == 2 else source.name.strip().replace(" ", "_"))
        if item["name"] == ">>>>camelot!<<<<":
            name = f"side{item['side']}-disk-marker"
        row = {"source": str(source), "source_sha256": hashlib.sha256(blob).hexdigest()}
        try:
            decoder = Decoder(blob)
            decoder.run()
            segments = ranges(decoder.written)
            (output / (name + ".memory.bin")).write_bytes(decoder.memory)
            (output / (name + ".known.bin")).write_bytes(decoder.known)
            (output / (name + ".commands.json")).write_text(json.dumps(decoder.commands, indent=2) + "\n")
            for low, high in segments:
                (output / f"{name}-{low:04x}-{high-1:04x}.bin").write_bytes(decoder.memory[low:high])
            row.update({"pass": True, "consumed": decoder.pos, "bytes": len(blob),
                        "trailing_bytes": len(blob) - decoder.pos,
                        "output_bytes": decoder.total, "ranges": segments,
                        "unknown_output_bytes": sum(bool(decoder.written[i]) and not decoder.known[i] for i in range(65536)),
                        "unknown_read_examples": decoder.unknown_reads,
                        "memory_sha256": hashlib.sha256(decoder.memory).hexdigest(),
                        "output_prefix": str(output / name)})
        except Exception as exc:
            row.update({"pass": False, "error": str(exc)})
        rows.append(row)
        print(json.dumps({key: row[key] for key in ("source", "pass", "consumed", "bytes", "trailing_bytes", "output_bytes", "ranges", "unknown_output_bytes", "error") if key in row}))
    (root / "static/unpacked-index.json").write_text(json.dumps(rows, indent=2) + "\n")


if __name__ == "__main__":
    main()
