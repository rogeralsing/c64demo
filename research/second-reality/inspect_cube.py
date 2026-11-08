#!/usr/bin/env python3
"""Check the original BA/BB texture cube's generated packed-color sampler.

Original instructions run only on known RAM. Native snapshots are passive,
paired full-memory inputs; no VIC, IRQ, ROM, drive or unknown response is
supplied. Independent indexed span equations check every draw write, while
geometry-table provenance belongs to cube_geometry.py.
"""
import argparse
from collections import Counter
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path

from py65.devices.mpu6502 import MPU
from inspect_ca import BASE, ROOT, KnownRam, comparison, native, ranges, record, run, sha

FILES = {
    'BA': ('side2-entry05-BA.prg', 0x4000, 4080,
           'fdc325fc558f9fe9e40fd909b166b98f1acec19de20c7f6ceb7af1c790fcb846'),
    'BB': ('side2-entry06-BB.prg', 0x7000, 12288,
           '3b84919d607a072c1990f43be657017f1240be46a537a29b3046e05ecbe1d7ce'),
}


def word(memory, address):
    return memory[address] | memory[address + 1] << 8


def files():
    memory = bytearray(65536)
    known = bytearray(65536)
    records = {}
    for name, (filename, first, size, digest) in FILES.items():
        path = BASE / 'disk-map' / filename
        blob = path.read_bytes()
        assert len(blob) == size + 2 and word(blob, 0) == first and sha(blob) == digest
        memory[first:first + size] = blob[2:]
        known[first:first + size] = bytes([1]) * size
        records[name] = dict(**record(path), load_header=first, payload_bytes=size)
    return memory, known, records


def generated_oracle():
    """Literal chain layout, without executing the generator's pointer loops."""
    pair = bytes.fromhex('bd 00 60 1d 00 62 91 50 c8')
    first = pair * 32 + b'\x60\x60'
    second = bytes.fromhex('b1 50 29 f0 1d 00 62 91 50 c8') + first
    return {0x5000: first, 0x5200: second}


def span_oracle(memory, texture_index):
    """Direct indexed packing of [left,right), preserving uncovered nibbles.

    The original triangle setup's actual patched source operands are inputs.
    This independently checks sampling/indexing, pair packing, odd endpoints,
    guard-page crossings and ordered stores, not the setup's UV equations.
    """
    left, right = memory[0x20:0x22]
    assert 0 <= left < right <= 64, (left, right)
    pointer = word(memory, 0x50)
    destination = pointer + left // 2
    events = []
    temporary = {}

    def load(address):
        return temporary.get(address, memory[address])

    def store(pc, address, value, sources, kind):
        assert 0xc000 <= address < 0xd000, hex(address)
        temporary[address] = value
        events.append(dict(pc=pc, address=address, value=value,
                           sources=sources, kind=kind))

    odd = left & 1
    if odd:
        source = word(memory, 0x5205) + texture_index
        assert memory[source] & 0xf0 == 0
        store(0x5207, destination, (load(destination) & 0xf0) | memory[source],
              [source], 'leading_low_nibble')
        destination += 1
    count = right // 2 - (left + 1) // 2
    first = 0x520a if odd else 0x5000
    for index in range(count):
        instruction = first + 9 * index
        assert memory[instruction] == 0xbd
        assert memory[instruction + 3] == 0x1d
        high = word(memory, instruction + 1) + texture_index
        low = word(memory, instruction + 4) + texture_index
        assert memory[high] & 15 == 0 and memory[low] & 0xf0 == 0
        store(instruction + 6, destination, memory[high] | memory[low],
              [high, low], 'complete_pair')
        destination += 1
    if right & 1:
        last = first + 9 * count
        # The tail's explicit ADC wraps the low-byte index. Duplicate palette
        # pages make this agree with full absolute,X loads across page ends.
        tail = 0x4b86 if odd else 0x4b3e
        high_page = word(memory, tail + 1)
        assert high_page & 255 == 0
        source = high_page + ((texture_index + memory[last + 1]) & 255)
        assert memory[source] & 15 == 0
        store(0x4b89 if odd else 0x4b41, destination,
              (load(destination) & 15) | memory[source], [source], 'trailing_high_nibble')
    assert len(events) == (right + 1) // 2 - left // 2
    return dict(left=left, right=right, texture_index=texture_index,
                destination_pointer=pointer, source_program=first,
                stores=events, nibble_samples=right - left,
                endpoint_parity=[left & 1, right & 1])


class CubeRam(KnownRam):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.pending = []
        self.pending_offset = 0
        self.spans = []
        self.oracle = bytearray(self.data)
        self.sample_stores = []

    def begin_span(self, cpu):
        assert not self.pending, ('Unclosed span', self.pc)
        assert cpu.a == self.data[0x20]
        span = span_oracle(self.data, cpu.x)
        self.spans.append(span)
        self.pending = span['stores']
        self.pending_offset = 0
        for event in self.pending:
            self.oracle[event['address']] = event['value']

    def finish_span(self):
        assert self.pending_offset == len(self.pending)
        self.pending = []
        self.pending_offset = 0

    def __setitem__(self, address, value):
        super().__setitem__(address, value)
        if 0xc000 <= address < 0xd000:
            assert self.pending, ('Unexpected screen store', self.pc, address)
            event = dict(pc=self.pc, address=address, value=value)
            expected = self.pending[self.pending_offset]
            assert event == {key: expected[key] for key in event}, (event, expected)
            self.sample_stores.append(event)
            self.pending_offset += 1


def execute(memory, registers, port, ddr, stop, limit=2_000_000):
    ram = CubeRam(bytearray(memory), bytearray([1]) * 65536, port, ddr)
    cpu = MPU(memory=ram, pc=registers['pc'])
    for name in ('a', 'x', 'y', 'sp'):
        setattr(cpu, name, registers[name])
    cpu.p = registers['flags']
    assert cpu.p & 8 == 0
    counts = Counter()
    steps = 0
    while not (steps and cpu.pc == stop):
        assert steps < limit, ('Instruction budget', hex(cpu.pc), steps)
        ram.pc = cpu.pc
        if cpu.pc == 0x4b00:
            ram.begin_span(cpu)
        if cpu.pc in (0x4b43, 0x4b8b) and ram.pending:
            ram.finish_span()
        opcode = ram[cpu.pc]
        assert cpu.instruct[opcode].__name__ != 'inst_not_implemented'
        counts[cpu.pc] += 1
        cpu.step()
        steps += 1
    if ram.pending:
        ram.finish_span()
    report = dict(entry=registers['pc'], stop=stop, instructions=steps,
                  nominal_cpu_cycles=cpu.processorCycles,
                  final_cpu=dict(pc=cpu.pc, a=cpu.a, x=cpu.x, y=cpu.y, sp=cpu.sp, flags=cpu.p),
                  instruction_counts=dict(sorted(counts.items())),
                  read_ranges=ranges(ram.reads), written_ranges=ranges(ram.writes),
                  rejected_hardware_or_unknown_accesses=0,
                  scope='Captured prestate, literal original opcodes, known RAM only; no IRQ or hardware responses.')
    return ram, report


def check_transition(directory, before_name, after_name, output):
    before, _, before_cpu, before_meta = native(directory, before_name)
    after, _, after_cpu, after_meta = native(directory, after_name)
    ram, execution = execute(before, before_cpu, before_meta['port_latch'],
                             before_meta['port_ddr'], after_cpu['pc'])
    checks = [comparison(ram.data, ram.oracle, 0xc000, 0xd000,
                         'All4096 screen bytes versus independent ordered indexed span oracle'),
              comparison(after, ram.oracle, 0xc000, 0xd000,
                         'All4096 native screen bytes versus independent ordered indexed span oracle')]
    assert all(check['exact'] for check in checks)
    full = comparison(after, ram.data, 0, 65536,
                      'Complete native RAM versus IRQ-free CPU endpoint; every difference retained')
    cpu = [dict(register=key, actual=after_cpu[key], expected=value,
                exact=after_cpu[key] == value)
           for key, value in execution['final_cpu'].items()]
    assert all(item['exact'] for item in cpu), cpu
    stores_path = output / (before_name + '-indexed-stores.json')
    stores_path.write_text(json.dumps(ram.spans, indent=2) + '\n')
    return dict(before=before_meta, after=after_meta, execution=execution,
                exact_screen_checks=checks, cpu_comparison=cpu, full_ram_observation=full,
                native_elapsed_clocks=after_cpu['clock'] - before_cpu['clock'],
                phase_before=before[0x02c0], phase_after=after[0x02c0],
                zoom_pointer_before=word(before, 0x08),
                texture_scroll_phase_before=before[0x02c1],
                spans=len(ram.spans), covered_nibbles=sum(s['nibble_samples'] for s in ram.spans),
                ordered_screen_stores=len(ram.sample_stores),
                store_kinds=dict(Counter(e['kind'] for span in ram.spans for e in span['stores'])),
                endpoint_parities=sorted({tuple(s['endpoint_parity']) for s in ram.spans}),
                source_reads=sum(len(e['sources']) for s in ram.spans for e in s['stores']),
                indexed_store_receipt=record(stores_path))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, required=True)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    output = args.output or BASE / ('cube-analysis-' + datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    output.mkdir(parents=True, exist_ok=True)
    (output / 'cube-proof.json').unlink(missing_ok=True)
    memory, known, file_records = files()
    assert memory[0x4000:0x4003] == bytes.fromhex('20 00 41')
    # Stop before the first VIC write; the original JSR creates all used stack
    # bytes. No synthetic RTS destination or display hardware is supplied.
    prepared, preparation = run(memory, known, 0x4000, 0x41d6, port=0x35)
    generation_checks = []
    for first, data in generated_oracle().items():
        expected = bytearray(65536)
        expected[first:first + len(data)] = data
        check = comparison(memory, expected, first, first + len(data),
                           'File-only original sampler generation versus direct template construction')
        assert check['exact']
        generation_checks.append(check)
    (output / 'file-generated-samplers.bin').write_bytes(memory[0x5000:0x5330])
    transitions = []
    for first, last in [('ba-span-pre', 'ba-span-post'), ('ba-draw-pre', 'ba-draw-post')]:
        if all((args.capture / (name + '.vsf')).is_file() for name in (first, last)):
            transitions.append(check_transition(args.capture, first, last, output))
    assert transitions, 'Need an actual paired native draw or span capture.'
    geometry = BASE / 'cube-geometry/proof.json'
    report = dict(pass_=True, script=record(Path(__file__)),
                  py65_version=importlib.metadata.version('py65'), original_files=file_records,
                  preparation_execution=preparation, sampler_generation_checks=generation_checks,
                  native_capture_directory=str(args.capture),
                  geometry_proof=record(geometry) if geometry.exists() else None,
                  transitions=transitions,
                  limits=['Span UV source operands and triangle edge arrays are actual setup inputs, not independently derived geometry.',
                          'Screen-RAM equality does not alone prove complete VIC scanout, physical hardware or coherent-frame cadence.',
                          'RAM-only CPU cycles exclude VIC stalls, IRQ/music, drive and other hardware; all full-RAM differences remain visible.'])
    report['pass'] = report.pop('pass_')
    (output / 'cube-proof.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(passed=True, output=str(output),
                         transitions=[dict(first=t['before']['name'], last=t['after']['name'],
                                           spans=t['spans'], covered_nibbles=t['covered_nibbles'],
                                           stores=t['ordered_screen_stores'],
                                           nominal_cycles=t['execution']['nominal_cpu_cycles'],
                                           native_clocks=t['native_elapsed_clocks']) for t in transitions]), indent=2))


if __name__ == '__main__':
    main()
