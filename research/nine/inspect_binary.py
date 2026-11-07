#!/usr/bin/env python3
"""Bounded original Nine SFX unpack and static candidate-code inventory.

No VICE, disk, renderer, ROM or VIC emulation. Mapped I/O writes are recorded
separately from underlying RAM; reads requiring hardware/ROM stop the CPU run.
"""

import hashlib
import importlib.util
from importlib.metadata import version
import json
from collections import Counter, deque
from pathlib import Path

from py65.devices.mpu6502 import MPU


ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / "build/research/nine/lft-nine.prg"
OUT = ROOT / "build/research/nine/binary"
PRG_SHA = "a257fa0436bc0d97fbeaa906c55489786a26ee6a9213aa3fd0d8e21f9612d839"
OUTPUT_STORES = {0x0132, 0x0191}
TEMPLATE_ADDRESSES = (0xA22A, 0xA24A, 0xA26A)
TEMPLATES = tuple(bytes.fromhex(row) for row in (
    "b0 00 24 00 a5 65 8d 21 d0 a5 66 8d 11 d0 ea 9d b1 cf 8c 21 d0 8e 21 d0 8e 11 d0 a9 3c 8d ff 7f",
    "b0 00 ea ea a5 65 8d 21 d0 a5 66 8d 11 d0 ea 8d 21 d0 8c 21 d0 8e 21 d0 8e 11 d0 a9 3c 8d ff 7f",
    "b0 00 2c 00 00 a5 65 8d 21 d0 a5 66 9d a1 cf 9d b1 cf 8c 21 d0 8e 21 d0 8e 11 d0 a9 3c 8d ff 7f",
))


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def ranges(addresses):
    result = []
    for address in sorted(addresses):
        if result and result[-1][1] == address:
            result[-1][1] += 1
        else:
            result.append([address, address + 1])
    return result


class Dependency(Exception):
    pass


class Memory:
    def __init__(self, blob, fill):
        self.data = bytearray((fill,)) * 65536
        self.known = bytearray(65536)
        self.data[0x0801:0x4013] = blob[2:]
        self.known[0x0801:0x4013] = bytes((1,)) * (len(blob) - 2)
        self.data[0:2] = bytes((0x2F, 0x37))
        self.known[0:2] = bytes((1, 1))
        self.pc = 0
        self.writes = Counter()
        self.output = set()
        self.output_events = 0
        self.io = []
        self.dependencies = []
        self.unknown = Counter()
        self.cycles = 0
        self.write_trace = []
        self.trace_writes = False

    def pins(self):
        return (self.data[1] & self.data[0]) | (7 & ~self.data[0])

    def __getitem__(self, address):
        pins = self.pins()
        if 0xD000 <= address < 0xE000 and pins & 3:
            self.dependencies.append([self.pc, "I/O" if pins & 4 else "characterROM", address])
            raise Dependency()
        if address >= 0xE000 and pins & 2 or 0xA000 <= address < 0xC000 and pins & 3 == 3:
            self.dependencies.append([self.pc, "ROM", address])
            raise Dependency()
        if not self.known[address]:
            self.unknown[address] += 1
        return self.data[address]

    def __setitem__(self, address, value):
        if self.trace_writes:
            self.write_trace.append([self.pc, address, value, self.cycles])
        if 0xD000 <= address < 0xE000 and self.pins() & 3 and self.pins() & 4:
            self.io.append([self.pc, address, value])
            return
        self.data[address] = value
        self.known[address] = 1
        self.writes[address] += 1
        if self.pc in OUTPUT_STORES:
            self.output.add(address)
            self.output_events += 1


def unpack(blob, fill=0, stack=0xFD):
    memory = Memory(blob, fill)
    cpu = MPU(memory=memory, pc=0x080D)
    cpu.sp, cpu.p = stack, cpu.UNUSED | cpu.INTERRUPT
    trace = deque(maxlen=20)
    status, steps = "instruction_limit", 0
    for steps in range(10_000_000):
        pc = cpu.pc
        if pc == 0x080D and steps:
            status = "normal_entry"
            break
        if not (0x080D <= pc < 0x081C or 0x3EEA <= pc < 0x3F3B or 0x00FD <= pc < 0x01D5):
            status = "unexpected_transfer"
            break
        opcode = memory.data[pc]
        if cpu.instruct[opcode].__name__ == "inst_not_implemented":
            status = "unsupported_opcode"
            break
        trace.append([pc, opcode, cpu.a, cpu.x, cpu.y, cpu.p, cpu.sp])
        memory.pc = pc
        memory.cycles = cpu.processorCycles
        try:
            cpu.step()
        except Dependency:
            status = "hardware_or_ROM_dependency"
            break
    output_ranges = ranges(memory.output)
    output_bytes = b"".join(memory.data[a:b] for a, b in output_ranges)
    return memory, {"status": status, "instructions": steps, "stop_pc": cpu.pc,
                    "entry_first32": memory.data[cpu.pc:cpu.pc + 32].hex(" "),
                    "fill_byte": fill, "initial_stack": stack,
                    "output_store_pcs": sorted(OUTPUT_STORES),
                    "output_ranges_end_exclusive": output_ranges,
                    "distinct_output_bytes": len(memory.output),
                    "output_events": memory.output_events,
                    "output_sha256": sha(output_bytes), "RAM_sha256": sha(memory.data),
                    "mapped_IO_writes": memory.io, "dependencies": memory.dependencies,
                    "uninitialized_read_addresses": [[a, n] for a, n in sorted(memory.unknown.items())],
                    "last_instructions": list(trace),
                    "scope": "Original SFX official opcodes in binary mode, initial zero/fill RAM except PRG+port; no BASIC/ROM/hardware execution"}


def window(ram, start, stop, *, x=0, y=0, carry=0, limit=1_000_000):
    """Execute a separately identified RAM-only code interval, not its caller.

    The complete RAM image is an explicit input fixture. Neither raster values
    nor ROM routines are supplied to make the full initializer proceed.
    """
    memory = Memory(INPUT.read_bytes(), 0)
    memory.data[:] = ram
    memory.data[0:2] = bytes((0x2F, 0x35))
    memory.known[:] = bytes((1,)) * 65536
    memory.trace_writes = True
    cpu = MPU(memory=memory, pc=start)
    cpu.sp, cpu.p = 0xFD, cpu.UNUSED | cpu.INTERRUPT | carry
    cpu.x, cpu.y = x, y
    steps = 0
    while cpu.pc != stop:
        assert start <= cpu.pc < stop, ("Unexpected control transfer", hex(cpu.pc))
        assert steps < limit, "Bounded instruction limit"
        assert cpu.instruct[memory.data[cpu.pc]].__name__ != "inst_not_implemented"
        memory.pc, memory.cycles = cpu.pc, cpu.processorCycles
        cpu.step()
        steps += 1
    assert not memory.dependencies and not memory.unknown
    return memory, dict(start_pc=start, stop_pc=stop, instructions=steps,
                        nominal_CPU_cycles=cpu.processorCycles,
                        mapped_IO_writes=memory.io,
                        scope="Original official CPU opcodes; explicit RAM/register fixture; no IRQ, DMA, raster or bus-write timing")


def relocate(ram):
    """Decode the length/target records independently of the page-copy loops."""
    expected = bytearray(ram)
    expected[0:2] = bytes((0x2F, 0x35))
    cursor, blocks = 0x7CBB, []
    while True:
        size = int.from_bytes(expected[cursor:cursor + 2], "little")
        if size == 0:
            break
        previous = cursor - size - 4
        target = int.from_bytes(expected[previous + 2:previous + 4], "little")
        source = previous + 4
        payload = bytes(expected[source:cursor])
        assert len(payload) == size and target + size <= 65536
        expected[target:target + size] = payload
        blocks.append(dict(source=source, destination=target, size=size,
                           destination_end_exclusive=target + size, sha256=sha(payload)))
        cursor = previous
    actual, result = window(ram, 0x0888, 0x0909)
    assert not actual.io
    # Only the original loop's documented scratch $02..$09 is excluded from
    # all-address equivalence. All destination bytes are checked separately.
    differences = [a for a in range(65536) if actual.data[a] != expected[a] and not 2 <= a < 10]
    assert not differences, differences
    for block in blocks:
        a, b = block["destination"], block["destination_end_exclusive"]
        assert actual.data[a:b] == expected[a:b]
    result.update(blocks=blocks, zero_size_record=cursor, all_non_scratch_RAM_matches=True,
                  scratch_exclusion=[2, 10], total_block_bytes=sum(b["size"] for b in blocks),
                  RAM_sha256=sha(actual.data))
    return actual.data, result


def first_hardware_dependency(ram):
    memory = Memory(INPUT.read_bytes(), 0)
    memory.data[:] = ram
    memory.known[:] = bytes((1,)) * 65536
    cpu = MPU(memory=memory, pc=0x080D)
    cpu.sp, cpu.p = 0xFD, cpu.UNUSED | cpu.INTERRUPT
    for count in range(10000):
        assert 0x080D <= cpu.pc < 0x0888
        memory.pc, memory.cycles = cpu.pc, cpu.processorCycles
        try:
            cpu.step()
        except Dependency:
            assert memory.dependencies == [[0x082B, "I/O", 0xD011]]
            return dict(stop_pc=0x082B, completed_instructions=count,
                        first_read=memory.dependencies[0], preceding_mapped_IO_writes=memory.io,
                        scope="Original normal-entry wrapper stops on its first real hardware read; no fake raster values supplied")
    raise AssertionError("Expected first hardware boundary")


def code_generator(ram):
    expected = bytearray(ram)
    patterns = bytes(ram[0xAF01:0xAF16])
    for address, template in zip(TEMPLATE_ADDRESSES, TEMPLATES):
        assert ram[address:address + 32] == template
    families = []
    for base, address, template in zip((0x3000, 0x3400, 0x3800), TEMPLATE_ADDRESSES, TEMPLATES):
        body = bytearray()
        for pattern in patterns:
            cell = bytearray(template)
            cell[28] = pattern
            body.extend(cell)
        body.append(0x60)
        for offset, value in ((0x5C, 0x50), (0x23C, 0x60),
                              (0x5E, 0x18), (0x23E, 0x18), (0x5F, 0xD0), (0x23F, 0xD0)):
            body[offset] = value
        expected[base:base + len(body)] = body
        expected[address + 28] = patterns[-1]
        families.append(dict(template=address, first=base, end_exclusive=base + len(body),
                             cells=21, cell_bytes=32, trailing_RTS=base + 672,
                             sha256=sha(body)))
    actual, result = window(ram, 0x807B, 0x8146)
    assert not actual.io
    assert all(actual.data[f["first"]:f["end_exclusive"]] == expected[f["first"]:f["end_exclusive"]]
               for f in families)
    differences = [a for a in range(65536) if actual.data[a] != expected[a] and a not in (0x40, 0x41)]
    assert not differences, differences
    assert patterns[2] == patterns[1] and patterns[17] == patterns[16]
    result.update(families=families, total_generated_bytes=3 * 673,
                  row_patterns=list(patterns), pointer_switch_cell_indices=[2, 17],
                  switch_rows_repeat_previous_pattern=True,
                  all_non_scratch_RAM_matches=True, scratch_exclusion=[0x40, 0x42])
    return actual.data, result


def timed_cells(ram):
    results = []
    expected_starts = ((15, 21, 26, 30, 34), (16, 22, 26, 30, 34), (16, 21, 26, 30, 34))
    for variant, address in enumerate(TEMPLATE_ADDRESSES):
        for carry in (0, 1):
            fixture = bytearray(ram)
            fixture[0x65:0x67] = bytes((6, 0x70))
            actual, result = window(fixture, address, address + 32, x=0x70, y=0x17, carry=carry)
            writes = [dict(pc=pc, address=a, value=v, instruction_start_cycle=c)
                      for pc, a, v, c in actual.write_trace]
            relevant = [w for w in writes if w["address"] in (0xD011, 0xD021)]
            # The first background-colour store precedes the quoted split.
            starts = tuple(w["instruction_start_cycle"] for w in relevant[1:])
            assert starts == tuple(c + carry for c in expected_starts[variant])
            assert result["nominal_CPU_cycles"] == 44 + carry
            assert [w["address"] for w in relevant[1:]] == [0xD011, 0xD021, 0xD021, 0xD021, 0xD011]
            assert actual.data[0x7FFF] == 0x3C
            assert actual.data[0xD011] == fixture[0xD011] and actual.data[0xD021] == fixture[0xD021]
            result.update(variant=variant, initial_X=0x70, initial_Y=0x17, initial_carry=carry,
                          write_instruction_starts=writes,
                          mapped_IO_preserves_underlying_RAM=True)
            results.append(result)
    return results


def pointer_and_glyph_setup(ram):
    pointer_memory, pointer_result = window(ram, 0x81AB, 0x81FB)
    expected = {(0x53F8 + page * 0x400 + sprite): 0x90 + member * 4 + page
                for page in range(4) for member, sprite in enumerate((0, 2, 4, 5))}
    assert {a: pointer_memory.data[a] for a in pointer_memory.writes} == expected
    pointer_result.update(expected_pointer_writes=[[a, v] for a, v in sorted(expected.items())],
                          sprite_members=[0, 2, 4, 5], screen_pointer_tables=[0x53F8, 0x57F8, 0x5BF8, 0x5FF8])
    glyph_memory, glyph_result = window(ram, 0x8245, 0x8271)
    expected = bytearray(ram)
    copied = []
    for n in range(9):
        source, target = 0x7800 + 64 * n, 0xE883 + 192 * n
        expected[target:target + 63] = ram[source:source + 63]
        copied.append(dict(source=source, destination=target, bytes=63))
    # Original code also advances its two self-modified absolute operands.
    expected[0x824A:0x824C] = (0x7800 + 9 * 64).to_bytes(2, "little")
    expected[0x824D:0x824F] = (0xE883 + 9 * 192).to_bytes(2, "little")
    expected[0:2] = bytes((0x2F, 0x35))
    assert glyph_memory.data == expected
    glyph_result.update(copies=copied, destination_stride=192, all_RAM_matches=True,
                        interpretation="Nine63-byte image copies. This isolated loop alone does not establish which display stage consumes them.")
    return dict(pointer_setup=pointer_result, image_copy_setup=glyph_result)


def static_inventory(ram):
    helper = ROOT / "research/tower-power/static_loader.py"
    spec = importlib.util.spec_from_file_location("nine_static", helper)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    spans = ((0x080D, 0x0943), (0x8000, 0x8304), (0x8D7E, 0x8E15),
             (0x8D04, 0x8D7E), (0x9900, 0x99BF), (0x99BF, 0x9B00), (0x9B00, 0x9CBA),
             (0x9CBA, 0x9CFB), (0x9D00, 0x9DD0), (0x9E00, 0x9E80),
             (0xA22A, 0xA28A))
    listings = []
    for first, last in spans:
        lines, pc = [], first
        while pc < last:
            instruction = module.decode(ram, pc)
            lines.append(f'{pc:04x}  {instruction["bytes"]:<8} {instruction["mnemonic"]} {instruction["text"]}')
            pc = instruction["next"]
        name = f"code-{first:04x}-{last:04x}.txt"
        payload = "\n".join(lines) + "\n"
        (OUT / name).write_text(payload)
        listings.append(dict(file=name, sha256=sha(payload.encode()), first=first, last_exclusive=last))
    return dict(disassembler_file=str(helper.relative_to(ROOT)), disassembler_sha256=sha(helper.read_bytes()),
                listings=listings,
                caution="Selected linear disassemblies contain data/padding and self-modified operands; they are candidate maps, not execution traces.")


def main():
    assert version("py65") == "1.2.0"
    blob = INPUT.read_bytes()
    assert len(blob) == 14356 and sha(blob) == PRG_SHA
    OUT.mkdir(parents=True, exist_ok=True)
    memory, result = unpack(blob)
    assert result["status"] == "normal_entry" and result["output_events"] == 29884
    assert result["output_ranges_end_exclusive"] == [[0x0801, 0x7CBD]]
    assert result["output_sha256"] == "ef45ab609f139bb03befcf20ab3253e2bb30debbc4cbd789350607c1c9d54004"
    assert not result["mapped_IO_writes"] and not result["dependencies"]
    (OUT / "unpack-ram.bin").write_bytes(memory.data)
    (OUT / "unpack-known.bin").write_bytes(memory.known)
    result.update({"script_sha256": sha(Path(__file__).read_bytes()), "input_sha256": sha(blob)})
    (OUT / "unpack.json").write_text(json.dumps(result, indent=2) + "\n")
    robustness = [result]
    for fill, stack in ((0xA5, 0xFD), (0, 0xF6), (0xA5, 0xF6)):
        _, alternate = unpack(blob, fill, stack)
        assert alternate["status"] == "normal_entry" and alternate["output_sha256"] == result["output_sha256"]
        assert alternate["output_events"] == 29884 and not alternate["mapped_IO_writes"] and not alternate["dependencies"]
        robustness.append(alternate)
    relocated, relocation_result = relocate(memory.data)
    (OUT / "relocated-ram.bin").write_bytes(relocated)
    generated, generator_result = code_generator(relocated)
    (OUT / "generated-ram.bin").write_bytes(generated)
    report = dict(input_sha256=sha(blob), script_sha256=sha(Path(__file__).read_bytes()),
                  py65_version=version("py65"), unpack_robustness=robustness,
                  normal_entry_hardware_boundary=first_hardware_dependency(memory.data), relocation=relocation_result,
                  generator=generator_result, template_execution=timed_cells(relocated),
                  setup=pointer_and_glyph_setup(relocated), static_inventory=static_inventory(relocated),
                  scope="Original SFX+isolated RAM-only routines, no patched original instructions, no hardware-read mock, no VIC/CIA/ROM or whole-program execution")
    path = OUT / "binary-proof.json"
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(dict(receipt=str(path.relative_to(ROOT)), unpack_fixtures=len(robustness),
                          payload_bytes=result["distinct_output_bytes"],
                          relocation_instructions=relocation_result["instructions"],
                          generator_bytes=generator_result["total_generated_bytes"],
                          timed_cell_cases=len(report["template_execution"])), indent=2))


if __name__ == "__main__":
    main()
