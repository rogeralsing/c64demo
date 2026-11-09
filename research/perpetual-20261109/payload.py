#!/usr/bin/env python3
"""Passive typed relocation/data analysis of the original Perpetual Fragility payload."""
from pathlib import Path
import argparse
import hashlib
import json

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "build/research/aloft-motion-20261109/primary-analysis/accepted-01"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def meta(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}

def dump(path, obj):
    path.write_text(json.dumps(obj, indent=2) + "\n")

def source_inputs():
    prg = (SOURCE / "perpetual-unpacked.prg").read_bytes()
    assert len(prg) == 17405 and sha(prg) == "4280209180aba0847703b7a1d6e0682df372a927cbcef25656ae04eee53a4863"
    memory = bytearray((SOURCE / "perpetual-predicted-memory.bin").read_bytes())
    known = bytearray((SOURCE / "perpetual-predicted-known.bin").read_bytes())
    assert sha(memory) == "48d9b5983ad654737f76c9ed6a2c4f650c12b3a1b80a31231340c6be43d66866"
    assert sha(known) == "df9ed6ed5d3185ddbe579e70f7e5362b4b732e129fbca9d009e28ac900f9d458"
    assert int.from_bytes(prg[:2], "little") == 0x0801
    assert memory[0x0801:0x4bfc] == prg[2:] and all(known[0x0801:0x4bfc])
    return memory, known

def guard(memory, address, expected, role):
    data = bytes.fromhex(expected)
    assert memory[address:address+len(data)] == data, (hex(address), role)
    return {"address": address, "end_exclusive": address+len(data), "hex": expected, "role": role}

def relocate(memory, known):
    """Recognized records [remainder,pages,destination_end_lo,hi], read backwards.

    Actual wrapper first copies 256 bytes to $0200 and disables I/O while
    copying records. This data transform predicts RAM bytes only; no CPU runs.
    """
    guards = [
        guard(memory, 0x080d, "a97f8d0ddc78a9358501a9008d00dda93c8d02dd204009", "entry and PAL timing setup call"),
        guard(memory, 0x0824, "a200bd3e089d0002e8d0f7ad3e098510ad3f098511c6014c2b02", "256-byte resident copy, end pointer, I/O off and copied entry"),
        guard(memory, 0x0869, "a51038e9048510a511e9008511c90a903f", "four-byte reverse header and source page termination"),
        guard(memory, 0x087a, "a003b1109912008810f8a412f024", "read remainder, page count and destination endpoint"),
        guard(memory, 0x0888, "a51038e5128510b002c611a51438e5128514b002c61588f007b110911488d0f9b1109114", "subtract remainder and backwards copy including byte zero"),
        guard(memory, 0x08ac, "a513f0b9c611c615c6134c6002", "one 256-byte backwards copy per page"),
        guard(memory, 0x08b9, "e601eeff0220ed0220f002adfc028dfeffadfd028dffff0dfefff0044e19d05820f302", "I/O restore, init API calls and conditional IRQ enable"),
    ]
    memory[0x0200:0x0300] = memory[0x083e:0x093e]
    known[0x0200:0x0300] = known[0x083e:0x093e]
    cursor = int.from_bytes(memory[0x093e:0x0940], "little")
    assert cursor == 0x4bfc
    records = []
    while True:
        cursor = (cursor-4) & 0xffff
        if cursor >> 8 < 0x0a:
            break
        assert all(known[cursor:cursor+4])
        remainder, pages, dlo, dhi = memory[cursor:cursor+4]
        destination_end = dlo | dhi << 8
        length = remainder + 256*pages
        start = cursor-length
        target = destination_end-length
        assert 0x0a00 <= start <= cursor and 0 <= target < destination_end <= 0x10000
        assert all(known[start:cursor])
        # A bytewise backward copy handles the overlapping $1800 record without
        # ever sourcing bytes previously overwritten by this record.
        copied = []
        for i in range(length-1, -1, -1):
            src = start+i
            dst = target+i
            assert known[src]
            memory[dst] = memory[src]
            known[dst] = 1
            copied.append(dst)
        records.append({"header": cursor, "remainder": remainder, "pages": pages,
                        "source": [start, cursor], "target": [target, destination_end],
                        "bytes": length, "sha256": sha(memory[target:destination_end]),
                        "copy_order": "decreasing address"})
        cursor = start
    assert len(records) == 8 and cursor == 0x09fc
    # The wrapper's INC $02FF is also source-defined and outside effect code.
    memory[0x02ff] = (memory[0x02ff]+1) & 255
    return records, guards

def coordinate_deposits(memory, limit, incoming=None):
    """Exact $1A00 address/mask recurrence, not a geometric substitute."""
    assert 0 <= limit <= 1496
    bitmap = bytearray(8192) if incoming is None else bytearray(incoming)
    assert len(bitmap) == 8192
    events = []
    for index in range(limit):
        word = int.from_bytes(memory[0xc000+2*index:0xc002+2*index], "little")
        offset, mask_index = word & 8191, word >> 13
        mask = memory[0x24d8+mask_index]
        old = bitmap[offset]
        bitmap[offset] |= mask
        events.append({"entry": index, "source": 0xc000+2*index, "word": word,
                       "bitmap_address": 0x4000+offset, "mask": mask,
                       "before": old, "after": bitmap[offset]})
    return bitmap, events

def initialize(memory, known):
    guards = [
        guard(memory, 0x1800, "a200a0208a9d0040e8d0faee071888d0f4", "32-page bitmap zero clear, self-modifying page operand"),
        guard(memory, 0x1811, "9d00689d0069e8d0f7a91b9d00609d00619d00629d0063e8d0f1", "two sprite pages zero, four attribute pages $1B"),
        guard(memory, 0x182b, "a9008510a9c08511a9288512a9fa8513a9dd8526", "coordinate pointer C000 and signed count -1496; 221 groups"),
        guard(memory, 0x183f, "20001a20001a20001ac626d0f3", "three deposits per group, total 663"),
        guard(memory, 0x184c, "a900852085218516851785288527a9018529a9808526a9018522a9008518a9a08519a980852460", "initial WIZ, fade, selection and text state"),
        guard(memory, 0x1a00, "24131030e612d002e613a000b1108514c8b110aa291f094085158a4a4a4a4a4aaabdd8248811149114a51018690285109002e61160", "signed list exhaustion, address/mask extraction and persistent OR deposit"),
        guard(memory, 0x24d8, "8040201008040201", "MSB-first bit masks"),
    ]
    memory[0x4000:0x6000] = bytes(8192)
    memory[0x6800:0x6a00] = bytes(512)
    memory[0x6000:0x6400] = bytes([0x1b])*1024
    known[0x4000:0x6400] = bytes([1])*9216
    known[0x6800:0x6a00] = bytes([1])*512
    memory[0x1807] = 0x60  # high byte advanced after all 32 bitmap pages
    bitmap, events = coordinate_deposits(memory, 663)
    memory[0x4000:0x6000] = bitmap
    pointer = 0xc000+2*663
    counter = (-1496+663) & 65535
    values = {0x10:pointer & 255, 0x11:pointer >> 8, 0x12:counter & 255, 0x13:counter >> 8,
              0x14:events[-1]["bitmap_address"] & 255, 0x15:events[-1]["bitmap_address"] >> 8,
              0x16:0, 0x17:0, 0x18:0, 0x19:0xa0, 0x20:0, 0x21:0, 0x22:1,
              0x24:0x80, 0x26:0x80, 0x27:0, 0x28:0, 0x29:1}
    for address, value in values.items():
        memory[address] = value
        known[address] = 1
    return events, guards

def divide40(source, value):
    """The five compare/subtract/ROL stages at $22D1; exact binary carry."""
    assert 0 <= value < 1024
    residue, quotient = value, 0
    stages = []
    for y in range(4, -1, -1):
        divisor = source[0x24ce+y] | source[0x24d3+y] << 8
        subtract = residue >= divisor
        if subtract:
            residue -= divisor
        quotient = (quotient << 1) | int(subtract)
        stages.append({"Y": y, "divisor": divisor, "subtract": subtract,
                       "quotient": quotient, "residue": residue})
    assert (quotient, residue) == divmod(value, 40)
    return quotient, residue, stages

def wiz_cycle(source):
    guards = [
        guard(source, 0x22ad, "a526f004c626d00320001a", "fade countdown: zero or decrement-to-zero calls deposit"),
        guard(source, 0x22b8, "a51618695385168521a5176902290385178523a9008520a004", "offset += $253 modulo 1024; separate division scratch"),
        guard(source, 0x22d1, "a521d9ce24a523f9d324900fa521f9ce248521a523f9d32485233826208810e0", "five compare/subtract/ROL stages divide by 40"),
        guard(source, 0x22f1, "a5161869018514a5176900290309608515", "attribute start = $6000 + ((offset+1)&$3FF)"),
        guard(source, 0x2302, "a000a200bde0249114e8e614d00ba515186901290309608515e02890e7", "forty writes, wrapping pointer within four matrix pages"),
        guard(source, 0x24ce, "2850a040800000000102", "40,80,160,320,640 divisors in low/high tables"),
        guard(source, 0x24e0, "0000"+"1c"*36+"0000", "two black, 36 white-on-grey, two black bitmap attributes"),
    ]
    offset = 0
    rows = []
    seen = set()
    for frame in range(1024):
        offset = (offset+0x253) & 1023
        assert offset not in seen
        seen.add(offset)
        quotient, remainder, _ = divide40(source, offset)
        start = (offset+1) & 1023
        first_length = min(40, 1024-start)
        segments = [{"address": 0x6000+start, "length": first_length, "stencil_offset": 0}]
        if first_length < 40:
            segments.append({"address": 0x6000, "length": 40-first_length, "stencil_offset": first_length})
        rows.append({"invocation": frame, "offset": offset, "vertical_quotient_20": quotient,
                     "horizontal_remainder_21": remainder, "write_segments": segments})
    assert offset == 0 and len(seen) == 1024
    # A direct independent integer division cross-check covers every admitted
    # source value, rather than only an initial demonstration position.
    for value in range(1024):
        divide40(source, value)
    return rows, guards

def sprite_x_motion(source):
    guards = [
        guard(source, 0x231f, "a207a924186d002638ed00264a9530ad25231869058d2523ad29231869058d2923ca10de", "eight lookup-difference samples, stores $37 down to $30"),
        guard(source, 0x2343, "ad25231869db8d2523ad29231869d68d2923", "net source-low phase changes +3 and -2 per update"),
    ]
    # Both literal indexed absolute operands point into the SAME original
    # 256-byte asset; only the operand low bytes are self-modified.
    table = source[0x2600:0x2700]
    assert set(table) == {8, 9, 10}
    p, q = source[0x2325], source[0x2329]
    assert (p, q) == (0, 0)
    rows = []
    for invocation in range(256):
        output = [None]*8
        for sample in range(8):
            left, right = table[(p+5*sample)&255], table[(q+5*sample)&255]
            assert 0 <= 0x24+left <= 255 and 0 <= 0x24+left-right <= 255
            output[7-sample] = (0x24+left-right) >> 1
        rows.append({"invocation": invocation, "operand_low_before": [p,q], "ZP30_to_37": output})
        p, q = (p+3)&255, (q-2)&255
    assert (p,q) == (0,0)
    # Bind every consumer: each loads the computed byte then stores sprite 5 X.
    consumers = []
    for i, pc in enumerate((0x20af,0x20bf,0x20d0,0x20da,0x20eb,0x2109,0x212e,0x2138)):
        consumers.append(guard(source, pc, bytes((0xa5,0x30+i,0x8d,0x0a,0xd0)).hex(), "sprite 5 X sample consumer"))
    return rows, guards+consumers

def source_contract(source):
    guards = [
        guard(source, 0x1b00, "c6008da524a91d38ed06dc8d0f1b1000a9a9a9a9a9a9ada5ea8ea7248ca924cefdff", "IRQ saves A/X/Y in restore immediates, timer-dependent delay"),
        guard(source, 0x1b22, "a9908d18d020cb24", "IRQ matrix select and NOP-tail delay helper"),
        guard(source, 0x1bb4, "8db81b10fe", "horizontal offset patches BPL operand into following delay strip"),
        guard(source, 0x1bcc, "8a4d22008d11d08e11d08c11d0eaeaa9808d18d0a9908d18d0", "timed D011 writes and D018 $80/$90 matrix switch"),
        guard(source, 0x1953, "a93d8d02dda9ff8d15d0a9008d17d0a9088d16d0a93b8d11d0a92e8d12d0", "selected effect CIA2 DDR, sprite enable, hires bitmap mode and raster IRQ line"),
        guard(source, 0x1976, "a529200010", "music init at $1000 with selected tune"),
        guard(source, 0x2355, "cefdff200310eefdff", "music tick $1003 inside IRQ"),
        guard(source, 0x24a1, "eefdffa900a200a0004e19d0eefdffe60040", "restore register immediates, raster acknowledge, DDR restore, RTI"),
        guard(source, 0x24b3, "ea"*26+"60", "NOP/RTS tail with multiple duration entry points"),
    ]
    return {"guards": guards, "routines": [
        {"entry":0x1800,"role":"init and initial coordinate deposition","end_exclusive":0x1873},
        {"entry":0x1873,"role":"interactive setup and keyboard selection","end_exclusive":0x19a7},
        {"entry":0x1a00,"role":"one persistent bitmap bit deposit","end_exclusive":0x1a35},
        {"entry":0x1b00,"role":"raster IRQ, display schedule, coordinate/attribute update, text and music","end_exclusive":0x24b3},
        {"entry":0x22ad,"role":"fade/deposit and WIZ offset/matrix update","end_exclusive":0x231f},
        {"entry":0x231f,"role":"eight source-LUT sprite-X samples","end_exclusive":0x2355},
        {"entry":0x24b3,"role":"NOP-tail delay helper","end_exclusive":0x24ce}],
        "memory_roles": [
        {"range":[0x1000,0x1135],"role":"music init/tick code and data"},
        {"range":[0x1800,0x273f],"role":"effect code, inline masks, stencil and motion tables"},
        {"range":[0x3000,0x37e8],"role":"menu screen/attribute source and menu sprite data"},
        {"range":[0x4000,0x6000],"role":"persistent bit-deposit bitmap, cleared at init"},
        {"range":[0x6000,0x6400],"role":"1 KB CPU-side matrix for circulating 40-byte stencil"},
        {"range":[0x6400,0x6800],"role":"alternate matrix/pointer address window, not wholly initialized by $1800"},
        {"range":[0x6800,0x6a00],"role":"cleared text sprite working storage"},
        {"range":[0x7000,0x7340],"role":"13 complete 64-byte sprite blocks from release"},
        {"range":[0x7400,0x7d80],"role":"38 complete 64-byte sprite blocks from release"},
        {"range":[0x9000,0x9800],"role":"16 planes x 128 character text font source"},
        {"range":[0xa000,0xa910],"role":"prepared scroll text"},
        {"range":[0xc000,0xcbb0],"role":"1496 packed address/bit coordinate records"}],
        "capture_plan": [
        {"PC":0x1800,"role":"installed code before any initializer self-modification"},
        {"PC":0x1873,"role":"initializer return, before interactive display setup"},
        {"PC":0x1944,"role":"SPACE exits keyboard menu into effect setup"},
        {"PC":0x1b00,"role":"IRQ entry; guard only stable prefix before first save/delay patches"},
        {"PC":0x22ad,"role":"pre snow/WIZ update: ZP10..29, bitmap and matrix are genuine inputs"},
        {"PC":0x231f,"role":"post attribute deposition, before sprite-X wave generation"},
        {"PC":0x24a1,"role":"pre register restore and IRQ exit"}],
        "unmodeled": ["exact raster schedule and sprite DMA/fetches", "CPU ports and CIA2 pin-derived bank state",
                      "text shifter and music", "native timing, frame cadence and complete display"]}

def produce(output):
    assert not output.exists(), "Use a fresh output directory"
    output.mkdir(parents=True)
    memory, known = source_inputs()
    records, guards = relocate(memory, known)
    anchors = [
        guard(memory, 0x1800, "a200a0208a9d0040e8d0faee071888d0f4", "effect initializer: zero $4000..$5FFF"),
        guard(memory, 0x1873, "a90b8d11d0a9008d15d08d17d08d1bd08d1dd08d20d0", "interactive setup entry"),
        guard(memory, 0x1944, "a90b8d11d02c11d030fb2c11d010fba93d8d02dd", "keyboard exit to effect display setup"),
    ]
    init_memory, init_known = bytearray(memory), bytearray(known)
    initial_events, init_guards = initialize(init_memory, init_known)
    full_bitmap, all_events = coordinate_deposits(memory, 1496)
    rows, wiz_guards = wiz_cycle(memory)
    sprite_rows, sprite_guards = sprite_x_motion(memory)
    contract = source_contract(memory)
    # Pure progression of the source signed exhaustion counter. The 833
    # remaining list entries are first eligible at runtime invocation 128.
    countdown, remaining, deposited = 128, 1496-663, 663
    completion_invocation = None
    for invocation in range(1, 1101):
        if countdown:
            countdown -= 1
        if countdown == 0 and remaining:
            remaining -= 1
            deposited += 1
            if not remaining:
                completion_invocation = invocation
    assert deposited == 1496 and completion_invocation == 960
    (output / "initialized-memory.bin").write_bytes(init_memory)
    (output / "initialized-known.bin").write_bytes(init_known)
    (output / "initial-bitmap-4000.bin").write_bytes(init_memory[0x4000:0x6000])
    (output / "complete-coordinate-bitmap-4000.bin").write_bytes(full_bitmap)
    dump(output / "coordinate-deposits.json", {"source": [0xc000,0xcbb0], "entry_count": 1496,
         "initial_deposits": 663, "initial_pointer": 0xc52e,
         "initial_signed_counter": -833, "remaining": 833,
         "first_runtime_deposit_invocation_1based": 128,
         "last_runtime_deposit_invocation_1based": completion_invocation,
         "unique_address_and_bit_sites": len(set((x["bitmap_address"],x["mask"]) for x in all_events)),
         "bitmap_memory_bit_count": sum(x.bit_count() for x in full_bitmap), "events": all_events})
    dump(output / "sprite-X-motion-cycle.json", {"period":256, "table":list(memory[0x2600:0x2700]),
         "formula":"out[7-i] = (36 + table[(p+5*i)&255] - table[(q+5*i)&255]) >> 1", "rows":sprite_rows})
    dump(output / "source-contract.json", contract)
    dump(output / "wiz-offset-cycle.json", {"period": 1024, "step": 0x253,
         "stencil":list(memory[0x24e0:0x2508]),
         "integer_division_cases_checked": 1024, "rows": rows,
         "limits": ["Invocation progression is conditional on reaching the update once per IRQ",
                    "Matrix addresses are CPU-side RAM addresses, not a model of AGSP/VIC fetch timing"]})
    (output / "payload.checked.py").write_bytes(Path(__file__).read_bytes())
    (output / "installed-memory.bin").write_bytes(memory)
    (output / "installed-known.bin").write_bytes(known)
    dump(output / "relocation-records.json", records)
    dump(output / "source-anchors.json", {"wrapper": guards, "installed": anchors, "initialization": init_guards, "coordinates_and_WIZ": wiz_guards, "sprite_X_motion": sprite_guards,
         "copied_API": {"init_02ED": "JMP $1800", "setup_02F0": "JMP $1873", "tick_02F3": "JMP $022A (RTS)",
                         "exit_test_02F6": "JMP $022A (RTS)", "exit_02F9": "JMP $022A (RTS)"},
         "IRQ_vector_metadata": int.from_bytes(memory[0x02fc:0x02fe], "little")})
    outputs = [{"name": p.name, "bytes": p.stat().st_size, "sha256": sha(p.read_bytes())}
               for p in sorted(output.iterdir())]
    proof = {"schema": "perpetual-original-relocation-and-update-v1", "pass_": True,
        "producer": meta(Path(__file__).resolve()), "inputs": [meta(SOURCE / n) for n in
        ("primary-proof.json", "perpetual-unpacked.prg", "perpetual-predicted-memory.bin", "perpetual-predicted-known.bin")],
        "records": records, "copied_record_bytes": sum(x["bytes"] for x in records),
        "coordinate_count": 1496, "coordinate_sites": len(set((x["bitmap_address"],x["mask"]) for x in all_events)),
        "initial_deposits": 663, "remaining_deposits": 833, "WIZ_offset_period": 1024,
        "WIZ_division_cases": 1024, "attribute_writes_per_update": 40,
        "IRQ_vector_metadata": int.from_bytes(memory[0x02fc:0x02fe], "little"), "outputs": outputs,
        "limits": ["Pure format relocation from original recovered bytes; no CPU execution or native input",
                   "Installed memory contains declared original prior context outside copied ranges; known mask is authoritative",
                   "Source-bound initializer and coordinate/attribute math only; no CPU state/flags/timing or native verification",
                   "No complete IRQ register schedule, AGSP physical fetch, sprite compositor or displayed-pixel claim",
                   "Coordinates are released prepared data; no analytic reconstruction of author-side generator"]}
    dump(output / "payload-proof.json", proof)
    print(json.dumps({"pass_": True, "records": len(records), "proof": str(output / "payload-proof.json")}))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    produce(parser.parse_args().output.resolve())
