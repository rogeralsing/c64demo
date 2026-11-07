#!/usr/bin/env python3
"""Compare Mufflon's actual generator CPU output with a separate host builder.

Flat RAM only. VIC/CIA registers are ordinary output latches, with no IRQ,
DMA, raster, open-bus or peripheral timing model. Stop before enabling IRQs.
"""
import importlib.metadata
import json
from pathlib import Path
import sys

from py65.devices.mpu6502 import MPU

from extract import ROOT, OUT, sha


def load(blob):
    memory = bytearray(65536)
    address = int.from_bytes(blob[:2], 'little')
    memory[address:address+len(blob)-2] = blob[2:]
    return memory


def color(value, default_register):
    kind = value >> 4
    if kind == 0:
        return value, default_register
    if kind == 1:
        return 0xd4, value & 15
    return value, (0x20 if kind == 2 else 0x20 | kind)


def build(memory):
    template = bytearray(memory[0x3300:0x33d6])
    result, starts = bytearray(), []
    for row in range(100):
        mode = row % 4
        offset, source, first = ((2, 0x39, 6), (0, 0x28, 6),
                                 (0, 0x2f, 6), (2, 0x34, 3))[mode]
        # The original copies selected instruction bytes into the template.
        for i in range(offset, 7):
            template[i] = template[source+i]
        for lane, address in enumerate((0x2401, 0x2481, 0x2801, 0x2881, 0x2c01, 0x2c81)):
            value, register = color(memory[address+row], 0x28+lane)
            template[first if lane == 0 else 0x0b+5*(lane-1)] = value
            template[0x08 if lane == 0 else 0x0d+5*(lane-1)] = register
        template[0x24] = memory[0x334c+row]
        starts.append(0x1000+len(result))
        result.extend(template[offset:0x28])
    result.extend(memory[0x33d0:0x33d6])
    # The generator's three final code patches, before IRQ is enabled.
    result[0x9be:0x9c0] = b'\x00\xdd'
    result[0x26] = 0xa0
    return bytes(result), starts


class TraceMemory:
    def __init__(self, ram):
        self.ram, self.events = ram.copy(), []
        self.pc, self.cycle = None, 0

    def __getitem__(self, address):
        return self.ram[address]

    def __setitem__(self, address, value):
        self.ram[address] = value
        if 0xd000 <= address <= 0xd03f or address == 0xdd00:
            # Cycle is instruction entry, not the physical write bus phase.
            self.events.append(dict(pc=self.pc, cpu_cycle=self.cycle,
                                    address=address, value=value))


def trace_speedcode(ram, original, starts):
    memory = TraceMemory(ram)
    cpu = MPU(memory=memory, pc=0x1000)
    cpu.a, cpu.x, cpu.y = 0x38, 0x3e, 0x78
    cpu.sp, cpu.p = 0xfd, cpu.UNUSED | cpu.INTERRUPT
    memory.ram[0x1fe:0x200] = b'\xff\x01'
    expected = []
    for row in range(100):
        expected.append((0xd011, (0x38,0x3a,0x3c,0x3e)[row % 4]))
        for lane, address in enumerate((0x2401,0x2481,0x2801,0x2881,0x2c01,0x2c81)):
            value, register = color(original[address+row], 0x28+lane)
            expected.append((0xd000+register, value))
        expected.append((0xdd00,3) if row == 63 else (0xd018,original[0x334c+row]))
    expected.append((0xd011,0x10))
    steps, phase_cycles = 0, []
    while cpu.pc != 0x200:
        assert 0x1000 <= cpu.pc < 0x1f42 and steps < 2000
        if cpu.pc in starts:
            phase_cycles.append(cpu.processorCycles)
        memory.pc, memory.cycle = cpu.pc, cpu.processorCycles
        cpu.step(); steps += 1
    assert [(e['address'],e['value']) for e in memory.events] == expected
    assert len(memory.events) == 801 and len(phase_cycles) == 100
    assert memory.ram[0x1000:0x1f42] == ram[0x1000:0x1f42]
    return dict(instructions=steps, cpu_cycles_including_rts=cpu.processorCycles,
                io_store_instructions=len(memory.events), trace=memory.events,
                phase_cycles=[b-a for a,b in zip(phase_cycles,phase_cycles[1:])],
                scope='No hardware stalls/IRQs; cycle tags are instruction entry, not bus-write time')


def main():
    index = json.loads((OUT / 'extraction.json').read_text())
    sys.path.insert(0, str(ROOT / 'research/tower-power'))
    from static_loader import decode
    rows = []
    for item in index['files']:
        if item['load_address'] != 0x2000:
            continue
        blob = (ROOT / item['path']).read_bytes()
        assert sha(blob) == item['sha256'] and all(item['embedded_code_matches'])
        original = load(blob)
        expected, starts = build(original)
        memory = original.copy()
        cpu = MPU(memory=memory, pc=0x3000)
        cpu.sp, cpu.p = 255, cpu.UNUSED | cpu.INTERRUPT
        steps = 0
        actual_starts = []
        while cpu.pc != 0x3109:
            assert steps < 100_000
            if cpu.pc == 0x3025:
                actual_starts.append(int.from_bytes(memory[0xfb:0xfd], 'little'))
            cpu.step()
            steps += 1
        assert actual_starts == starts and len(starts) == 100
        assert int.from_bytes(memory[0xfb:0xfd], 'little') == 0x1f3c
        assert bytes(memory[0x1000:0x1f42]) == expected
        assert memory[0x0280:0x02a8] == original[0x2280:0x22a8]
        assert memory[0x33d8:0x3400] == original[0x73d8:0x7400]
        assert memory[0x03f8:0x0400] == original[0x23f8:0x2400]
        assert memory[0x07f8:0x0800] == bytes([0xfe])*8
        assert memory[0x7ff8:0x8000] == bytes(8)
        stem = Path(item['path']).stem
        (OUT / f'{stem}-generated.ram').write_bytes(memory)
        (OUT / f'{stem}-speedcode.bin').write_bytes(expected)
        pc, listing = 0x1000, []
        while pc < 0x1f42:
            d = decode(memory, pc)
            listing.append(f"{pc:04x}: {d['bytes']:8s} {d['mnemonic']} {d['text']}")
            pc = d['next']
        assert pc == 0x1f42 and memory[0x1f41] == 0x60
        (OUT / f'{stem}-speedcode.txt').write_text('\n'.join(listing)+'\n')
        trace = trace_speedcode(memory, original, starts)
        (OUT / f'{stem}-register-trace.json').write_text(json.dumps(trace,indent=2)+'\n')
        rows.append(dict(name=item['name'], prg_sha256=sha(blob),
                         pass_=True, instructions=steps, flat_cpu_cycles=cpu.processorCycles,
                         generated_bytes=len(expected), generated_sha256=sha(expected),
                         speedcode_cpu_cycles_including_rts=trace['cpu_cycles_including_rts'],
                         speedcode_io_store_instructions=trace['io_store_instructions'],
                         row_starts=starts))
    # All 256 switch byte values against the original $33b0 CPU helper.
    tests = 0
    for value in range(256):
        for lane in range(6):
            memory = bytearray(65536)
            code = bytes(json.loads((OUT/'source-arrays.json').read_text())['nuifli_displayer_code2'])
            memory[0x3300:0x3300+len(code)] = code
            cpu = MPU(memory=memory, pc=0x33b0)
            cpu.a, cpu.y, cpu.sp, cpu.p = value, 0x28+lane, 0xfd, cpu.UNUSED | cpu.INTERRUPT
            memory[0x1fe:0x200] = b'\xff\x01'
            n = 0
            while cpu.pc != 0x200:
                cpu.step(); n += 1
                assert n < 30
            assert (cpu.a, cpu.y) == color(value, 0x28+lane)
            tests += 1
    receipt = dict(pass_=True, py65_version=importlib.metadata.version('py65'),
                   script_sha256=sha(Path(__file__).read_bytes()), files=rows,
                   switch_helper_cases=tests,
                   instructions=sum(r['instructions'] for r in rows),
                   scope='Original generator and switch decoder, flat RAM; no VIC/CIA/IRQ/raster/DMA proof')
    (OUT / 'generator-validation.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k!='files'}, indent=2))


if __name__ == '__main__':
    main()
