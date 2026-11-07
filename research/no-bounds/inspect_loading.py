#!/usr/bin/env python3
"""Check No Bounds' published stream plan and bounded scheduling arithmetic.

This is a host integer/manifest model, not original CPU execution, a Sparkle
decoder, a source rebuild or a native timing/scheduling proof.
"""

import ast
import json
from pathlib import Path
import re

from loading_sources import BASE, ROOT, record


def arithmetic(expression):
    node = ast.parse(expression.replace("$", "0x"), mode="eval").body

    def visit(item):
        if isinstance(item, ast.Constant) and type(item.value) is int:
            return item.value
        if isinstance(item, ast.BinOp) and isinstance(item.op, (ast.Add, ast.Sub)):
            a, b = visit(item.left), visit(item.right)
            return a + b if isinstance(item.op, ast.Add) else a - b
        raise ValueError(expression)

    return visit(node)


def text(relative):
    return (BASE / "NoBounds" / relative).read_text()


def main():
    source_path = BASE / "loading-source-proof.json"
    source = json.loads(source_path.read_text())
    assert source["pass"]
    for item in source["sources"]:
        assert record(ROOT / item["artifact"]["path"]) == item["artifact"]
    cpp = text("Parts/NoBounds/NoBounds.cpp")
    values = {name: int(value) for name, value in re.findall(
        r"static const int (ImageWidth|ImageHeight|ImageChunkWidth) = (\d+);", cpp)}
    assert set(values) == {"ImageWidth", "ImageHeight", "ImageChunkWidth"}
    assert values == {"ImageWidth": 1600, "ImageHeight": 200, "ImageChunkWidth": 64}
    assert "unsigned char MAPData[25][8][8];" in cpp
    assert "unsigned char SCRData[25][8];" in cpp and "unsigned char COLData[25][8];" in cpp
    width, height, strip_width = (values[key] for key in ("ImageWidth", "ImageHeight", "ImageChunkWidth"))
    chunk_count = (width - 320) // strip_width
    bitmap_bytes = height * strip_width // 8
    attribute_bytes = (height // 8) * (strip_width // 8)
    chunk_bytes = bitmap_bytes + 2 * attribute_bytes
    buffers = (0x7c00, 0x7400, 0x9800, 0x9000)
    actual, group = [], None
    for line in text("Link/NoBounds/StreamData.sls").splitlines():
        if line.startswith("#Chunk "):
            group = int(line.split()[1])
        elif line.startswith(("File:", "Mem:")):
            fields = line.split()
            assert len(fields) == 5 and fields[1].endswith("StreamData.bin")
            actual.append((group, fields[0][:-1], *(int(v, 16) for v in fields[2:])))
    expected = []
    for chunk in range(chunk_count):
        group = max(0, chunk - 3)
        if chunk >= 4:
            for prior in range(chunk - 3, chunk):
                expected.append((group, "Mem", buffers[prior % 4], prior * chunk_bytes, chunk_bytes))
        expected.append((group, "File", buffers[chunk % 4], chunk * chunk_bytes, chunk_bytes))
    assert actual == expected
    occupancy, resident_checks = {}, []
    for group, kind, address, offset, size in actual:
        assert size == chunk_bytes and offset % chunk_bytes == 0
        chunk = offset // chunk_bytes
        if kind == "Mem":
            resident_checks.append({"group": group, "address": address, "chunk": chunk,
                                    "exact": occupancy[address] == chunk})
        else:
            occupancy[address] = chunk
    assert all(item["exact"] for item in resident_checks)

    macros = text("Main/Main-CommonMacros.asm")
    match = re.search(r"\.macro MusicSync\(SyncFrame\)\s*\{(.*?)\n\s*\}", macros, re.S)
    instructions = [line.split("//", 1)[0].strip().replace("\t", " ") for line in match[1].splitlines()]
    instructions = [" ".join(line.split()) for line in instructions if line]
    assert instructions == ["!: lda $d011", "bpl !-", "lda MUSIC_FrameLo", "cmp #<SyncFrame",
                            "lda MUSIC_FrameHi", "sbc #>SyncFrame", "bcc !-"]
    defines = text("Main/Main-CommonDefines.asm")
    targets = {name: arithmetic(expression.strip()) for name, expression in re.findall(
        r"\.var (SYNC_\w+)\s*=\s*([^\r\n/]+)", defines)}
    assert len(targets) == 17 and all(0 <= v <= 65535 for v in targets.values())
    comparisons = 0
    for target in targets.values():
        for counter in range(65536):
            low_carry = int((counter & 255) >= (target & 255))
            high_result = (counter >> 8) - (target >> 8) - (1 - low_carry)
            assert (high_result >= 0) == (counter >= target)
            comparisons += 1

    assert re.search(r"\.var MAIN_BASECODE\s*=\s*\$0800", defines)
    assert re.search(r"\.var DISK_BASE\s*=\s*MAIN_BASECODE\s*\+\s*\$8f", defines)
    disk = text("Parts/NoBounds/DISK-NoBounds.asm")
    assert re.search(r"PartDone:\s*\.byte\s*\$00\s*Entry:", disk)
    assert re.search(r"lda #>\(Entry-1\)\s*pha\s*lda #<\(Entry-1\)\s*pha\s*jmp \$c000", disk)
    entry = 0x0800 + 0x8f + 1
    for initial_sp in range(256):
        stack, sp = {}, initial_sp
        for value in (((entry - 1) >> 8) & 255, (entry - 1) & 255):
            stack[0x100 + sp] = value
            sp = (sp - 1) & 255
        sp = (sp + 1) & 255
        low = stack[0x100 + sp]
        sp = (sp + 1) & 255
        high = stack[0x100 + sp]
        assert ((high * 256 + low + 1) & 65535) == entry and sp == initial_sp

    proof = {
        "pass": True, "script": record(Path(__file__).resolve()), "source_proof": record(source_path),
        "stream": {"source_geometry": values, "initial_image_width": 320,
                   "streaming_chunks": chunk_count, "bitmap_bytes_per_chunk": bitmap_bytes,
                   "screen_bytes_per_chunk": attribute_bytes, "color_bytes_per_chunk": attribute_bytes,
                   "chunk_bytes": chunk_bytes, "total_stream_bytes": chunk_count * chunk_bytes,
                   "buffer_addresses": list(buffers), "payload_resident_bytes": len(buffers) * chunk_bytes,
                   "manifest_rows": actual, "resident_definition_checks": resident_checks,
                   "bundle_groups": sorted({row[0] for row in actual}),
                   "scope": "Exact File/Mem plan against independent geometry/ring indexing. Mem rows are manifest declarations, not observed runtime transfers."},
        "music_compare": {"targets": targets, "counter_cases": comparisons,
                          "source_instructions": instructions,
                          "scope": "CMP/SBC carry arithmetic for all 65536 values at each published target; assumes coherent low/high reads and no intervening flag changes. No IRQ atomicity or time measurement."},
        "handover": {"disk_base": entry - 1, "entry": entry, "stack_pointer_cases": 256,
                     "specific_exit_target": 0xc000,
                     "scope": "Host stack-byte/RTS arithmetic only. This DISK script first enters the fade at C000; the fade loads the next part and later returns."},
        "limits": ["No source rebuild, original-disk payload extraction or native frame/load timing.",
                   "No proof that IRQ/main-thread buffer consumption meets each refill deadline.",
                   "The 2000-byte chunks include bitmap and both attribute planes, not 2000 bitmap bytes alone."]}
    output = BASE / "loading-plan-proof.json"
    output.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"pass": True, "chunks": chunk_count, "chunk_bytes": chunk_bytes,
                      "manifest_rows": len(actual), "resident_checks": len(resident_checks),
                      "music_compare_cases": comparisons, "proof": record(output)}, indent=2))


if __name__ == "__main__":
    main()
