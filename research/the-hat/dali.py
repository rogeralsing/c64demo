#!/usr/bin/env python3
"""Typed Bitfire/Dali stream semantics; no CPU interpreter or native tools.

The format is derived from Tobias Bindhammer's retained 2021 Dali source.
Its original BSD-style notice is retained separately in the source archive;
this independent model does not execute or copy that assembly implementation.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DISK = ROOT / 'build/research/the-hat/disk-analysis/accepted-02'
SOURCE = ROOT / 'build/research/next-round/boot-analysis/bitfire-source'
NATIVE = ROOT / 'build/research/the-hat/native-01'
PINS = {
    DISK / 'disk-proof.json': 'a23fa100137fe60f929af25b6596584089cd93cacd891fe02e7ebc85d47635a3',
    SOURCE / 'loader/resident.asm': '87d8f77d54f1c6dbee25a84cb3bc128e240f174cd1d25753cd7ad070a42708f1',
    SOURCE / 'packer/dali/dzx0_dali.asm': '35f1951faea2f5a1c86daeb89930273a69514199d02e84f411647a3aa865562c',
    SOURCE.parent / 'bitfire-source.json': 'ae970f06264ae255335516d20e3e04fff5670f1cfa11674e9f61965c6b01cff1',
    NATIVE / 'first-load-entry-ram.bin': '313b4a7c3460bd952959b8895049cd695e47402ab26ddbfe84b7241dbec93ab7',
    NATIVE / 'first-loaded-ram.bin': 'e76ca88565cffba8005be0d920d51b12c546144d45d9d4b1865366afd608bf6a',
}


def sha(b):
    return hashlib.sha256(b).hexdigest()


def meta(p):
    p = p.resolve()
    b = p.read_bytes()
    return {'path': str(p.relative_to(ROOT)), 'bytes': len(b), 'sha256': sha(b)}


def output_meta(p):
    b = p.read_bytes()
    return {'name': p.name, 'bytes': len(b), 'sha256': sha(b)}


class Stream:
    def __init__(self, payload, ordinary_word_control=False):
        self.payload = payload
        self.pos = 2
        self.mask = 0
        self.bits = 0
        self.bit_count = 0
        self.progress = {}
        self.extensions = []
        self.ordinary_word_control = ordinary_word_control

    def byte(self):
        if self.pos >= len(self.payload):
            raise ValueError('packed stream exhausted at byte %d; %s' %
                             (self.pos, json.dumps(self.progress, sort_keys=True)))
        value = self.payload[self.pos]
        self.pos += 1
        return value

    def bit(self):
        if self.mask == 0:
            self.bits = self.byte()
            self.mask = 128
        value = int(bool(self.bits & self.mask))
        self.mask >>= 1
        self.bit_count += 1
        return value

    def elias(self, first=None):
        value = 1
        control = self.bit() if first is None else first
        while control == 0:
            value = 2 * value + self.bit()
            if self.ordinary_word_control:
                if value > 65535:
                    raise ValueError('ordinary-word control exceeds 16-bit domain')
            elif value > 255:
                # Original .lz_length_16 saves the low eight payload bits,
                # then decodes the high byte as a separate continued number.
                # This differs from an ideal unbounded binary Elias integer.
                low = value & 255
                high = self.elias()
                if high > 255:
                    raise ValueError('Elias extension exceeds original 16-bit domain')
                value = (high << 8) | low
                self.extensions.append({'packed_cursor': self.pos,
                                        'low': low, 'high': high, 'value': value})
                return value
            control = self.bit()
        return value


def decode(prg, initial=None, allow_unknown=False, ordinary_word_control=False):
    assert initial is None or len(initial) == 65536
    load = int.from_bytes(prg[:2], 'little')
    payload = prg[2:]
    if not 0 <= load < load + len(payload) <= 65536:
        raise ValueError('packed file crosses C64 address boundary')
    dest = int.from_bytes(payload[:2], 'little')
    start = dest
    ram = bytearray(65536) if initial is None else bytearray(initial)
    provenance = bytearray([0 if initial is None else 1]) * 65536
    dependency = list(range(65536)) if initial is None else [None] * 65536
    ram[load:load + len(payload)] = payload
    provenance[load:load + len(payload)] = bytes([2]) * len(payload)
    dependency[load:load + len(payload)] = [None] * len(payload)
    reader = Stream(payload, ordinary_word_control)
    reader.progress['destination'] = dest
    offset = 1
    operations = []
    prior_reads = []
    raw_reads = []
    computed_reads = 0
    unknown_reads = []
    written = set()

    def put(value, origin=None):
        nonlocal dest
        if not start <= dest < 65536:
            raise ValueError('output crosses bounded nonwrapping destination')
        if load + reader.pos <= dest < load + len(payload):
            raise ValueError('output overwrites unread packed stream')
        ram[dest] = value
        provenance[dest] = 3 if origin is None else 4
        dependency[dest] = origin
        written.add(dest)
        dest += 1
        reader.progress['destination'] = dest

    state = 'literal'
    end = None
    while end is None:
        if len(operations) > 65536:
            raise ValueError('operation bound exceeded')
        before = dest
        reader.progress['state'] = state
        packed_before = reader.pos
        if state == 'literal':
            length = reader.elias()
            for _ in range(length):
                put(reader.byte())
            operations.append({'kind': 'literal', 'destination': before,
                               'length': length, 'packed_before': packed_before,
                               'packed_after': reader.pos})
            state = 'new' if reader.bit() else 'repeat'
            continue
        if state == 'new':
            high = reader.elias()
            if high == 256:
                end = 'offset-Elias-256'
                break
            if high > 256:
                raise ValueError('offset high Elias outside 1..256')
            raw = reader.byte()
            offset = (((high - 1) << 7) | (raw >> 1)) + 1
            length = reader.elias(first=raw & 1) + 1
        else:
            assert state == 'repeat'
            length = reader.elias()
        for _ in range(length):
            source = (dest - offset) & 65535
            value = ram[source]
            origin = dependency[source]
            if provenance[source] in (0, 4):
                if not allow_unknown:
                    raise ValueError('match reads unknown prior memory at $%04X; destination $%04X, packed byte %d' %
                                     (source, dest, reader.pos))
                assert origin is not None
                unknown_reads.append({'read_address': source, 'origin_address': origin,
                                      'destination': dest})
            elif provenance[source] == 1:
                prior_reads.append({'address': source, 'value': value})
            elif provenance[source] == 2:
                raw_reads.append({'address': source, 'value': value})
            else:
                computed_reads += 1
            put(value, origin)
        operations.append({'kind': state, 'destination': before,
                           'length': length, 'distance': offset,
                           'packed_before': packed_before,
                           'packed_after': reader.pos})
        if dest == load + reader.pos:
            end = 'in-place-destination-equals-source'
        else:
            state = 'new' if reader.bit() else 'literal'
    return ram, {'load': load, 'packed_bytes': len(payload), 'destination': start,
                 'computed_end_exclusive': dest, 'packed_consumed': reader.pos,
                 'packed_cursor_address': load + reader.pos,
                 'end_condition': end, 'bits_read': reader.bit_count,
                 'word_number_extensions': reader.extensions,
                 'last_distance': offset, 'operations': operations,
                 'computed_bytes': len(written),
                 'unknown_output': [{'address': i, 'origin_address': dependency[i]}
                                    for i in sorted(written) if provenance[i] == 4],
                 'match_reads': {'prior_context': prior_reads,
                                 'packed_file': raw_reads,
                                 'computed': computed_reads,
                                 'unknown_dependencies': unknown_reads}}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    (a.output / 'dali.checked.py').write_bytes(Path(__file__).read_bytes())
    for path, expected in PINS.items():
        assert sha(path.read_bytes()) == expected
    resident = (SOURCE / 'loader/resident.asm').read_text().splitlines()
    source_anchors = []
    for lo, hi, label in [(315, 335, 'MSB-first refill/control/payload'),
                          (336, 365, 'save low byte then decode high byte'),
                          (399, 419, 'destination little-endian stream header'),
                          (455, 492, 'new distance and backtracked length'),
                          (543, 592, 'literal and new/repeated selector'),
                          (597, 648, 'repeated match, forward copy, in-place check')]:
        body = '\n'.join(resident[lo - 1:hi])
        source_anchors.append({'member': 'loader/resident.asm', 'first_line': lo,
                               'last_line': hi, 'role': label, 'text': body})
    memory = (NATIVE / 'first-load-entry-ram.bin').read_bytes()
    guards = {
        0x0294: ('Elias refill', 'AAB1F02A85F2E6F0F0F18AB00B06F22AB00706F290F7F0E860'),
        0x02AD: ('word extension low save/high decode', '489820A30285F5'),
        0x02E4: ('destination header', 'A0008CBB038CC303A2FFB1F095F4E6F0D00320E103E8F0F28A38D07E'),
        0x0328: ('distance and raw-byte backtrack', 'E9014A8DC303B1F06A8DBB03E6F0F0DDA901A0FEB074'),
        0x0384: ('literal copy', 'B1F091F3E6F0F069E6F3F0BECAD0F1A901'),
        0x0399: ('repeated distance length', '06F2B00706F22A06F290F9D005209402F0AAE901'),
        0x03BA: ('forward match copy and in-place stop', 'E9008DC803A7F4E8E9008DC903B9EFBE91F3C8D0F886F4A901E4F1D096A6F3E4F0D090'),
    }
    runtime = []
    for address, (role, code) in guards.items():
        b = bytes.fromhex(code)
        assert memory[address:address + len(b)] == b
        runtime.append({'pc': address, 'role': role, 'hex': code})
    disk = json.loads((DISK / 'disk-proof.json').read_text())
    cases = []
    outputs = []
    decoded = {}
    for side, index in [('a', 0), ('a', 40), ('a', 41), ('a', 42),
                         ('b', 0), ('b', 16), ('b', 17), ('b', 18)]:
        row = next(r for d in disk['disks'] if d['side'] == side
                   for r in d['raw_streams'] if r['index'] == index)
        path = DISK / row['output']
        prg = path.read_bytes()
        assert int.from_bytes(prg[:2], 'little') == row['load']
        assert len(prg) - 2 == row['bytes']
        assert sha(prg[2:]) == row['payload_sha256']
        result, details = decode(prg)
        lo = details['destination']
        assert details['end_condition'] == 'in-place-destination-equals-source'
        hi = details['load'] + details['packed_bytes']
        assert not details['unknown_output']
        assert not details['match_reads']['prior_context']
        name = side + '%02d' % index
        decoded[name] = (lo, bytes(result[lo:hi]))
        target = a.output / (name + '-%04x.bin' % lo)
        target.write_bytes(result[lo:hi])
        outputs.append(output_meta(target))
        trace = a.output / (name + '-operations.json')
        trace.write_text(json.dumps(details, indent=2, sort_keys=True) + '\n')
        outputs.append(output_meta(trace))
        counts = {kind: sum(r['kind'] == kind for r in details['operations'])
                  for kind in ['literal', 'new', 'repeat']}
        tail = hi - details['computed_end_exclusive']
        if tail:
            assert result[details['computed_end_exclusive']:hi] == prg[-tail:]
        cases.append({'name': name, 'side': side, 'raw_index': index,
                      'raw': meta(path), 'destination': lo, 'end_exclusive': hi,
                      'bytes': hi - lo, 'computed_bytes': details['computed_bytes'],
                      'untouched_original_tail_bytes': tail,
                      'packed_consumed': details['packed_consumed'],
                      'end_condition': details['end_condition'],
                      'operation_counts': counts,
                      'word_extensions': details['word_number_extensions'],
                      'prior_memory_reads': 0, 'unknown_bytes': 0,
                      'output': output_meta(target), 'trace': output_meta(trace)})
    oracle = (NATIVE / 'first-loaded-ram.bin').read_bytes()
    lo, body = decoded['a00']
    assert oracle[lo:lo + len(body)] == body
    context_result, _ = decode((DISK / 'raw-a/000-1673.prg').read_bytes(), memory)
    assert context_result[lo:lo + len(body)] == body
    # A source-discriminating rejected model, not a second accepted decoder.
    controls = []
    for relative in ['raw-b/017-71f3.prg', 'raw-a/042-ec35.prg']:
        try:
            decode((DISK / relative).read_bytes(), ordinary_word_control=True)
        except ValueError as e:
            controls.append({'raw': relative, 'variant': 'ordinary unbounded Elias word',
                             'rejected': True, 'reason': str(e)})
        else:
            raise AssertionError('source-discriminating wrong word model did not reject')
    anchors = [
        ('a40', 0x283D, '20D20220D202AD4D28F0FB4C0088', 'two loads then JMP$8800'),
        ('a41', 0x883A, '206388A9F1200C02A93F8D02DD2C00DD10FBA9018D6188A90220D402AD6088F0FB4C0009', 'original side-change F1 caller'),
        ('b00', 0x0F3B, '20D2024C00E0', 'one load then JMP$E000'),
        ('b16', 0x083A, '20490820D202AD4808F0FB4C0080', 'one load then JMP$8000'),
        ('b17', 0x803A, '204B8020D202AD4A80F0FB4C0008', 'initialization/load then wait and JMP$0800'),
        ('b17', 0x8317, '4C0020', 'raster transfer to$2000'),
        ('b17', 0x205A, 'AC1435B980368DF84B', 'sprite pointer table consumer'),
        ('b18', 0xF0A4, '205BFF586C00A0', 'KERNAL reset then JMP($A000)'),
    ]
    code_anchors = []
    for name, pc, code, role in anchors:
        base, data = decoded[name]
        assert data[pc - base:pc - base + len(code) // 2] == bytes.fromhex(code)
        code_anchors.append({'case': name, 'pc': pc, 'hex': code, 'role': role})
    proof = {'schema': 'the-hat-dali-1', 'pass': True,
             'producer': meta(Path(__file__)), 'inputs': [meta(p) for p in PINS],
             'source_commit': '5a3964b533656332c12cc0904f2ce92f44499c6f',
             'source_license_notice': '\n'.join(resident[:24]),
             'source_anchors': source_anchors, 'original_runtime_guards': runtime,
             'cases': cases, 'outputs': outputs, 'code_anchors': code_anchors,
             'first_load_native_oracle': {'start': lo, 'bytes': len(body),
                                           'mismatches': 0,
                                           'prediction_uses_native_initial_RAM': False,
                                           'optional_initial_context_replay_equal': True},
             'rejected_word_model_controls': controls,
             'limits': [
                 'Typed stream semantics only; no CPU, loader I/O, timing or native process replay.',
                 'Native RAM files are pinned observations; lifecycle acceptance belongs to root native-case audit.',
                 'B17 is a source-bound raster candidate; its runtime ending identity needs original controller/native binding.',
                 'No artist-rendered font image is assumed byte-identical to these original bytes.',
                 'Only the eight selected streams are accepted; no assertion about all62 raw streams.',
                 'EOF offset256 is source-bound but not exercised by selected in-place terminated samples.',
                 'The original untouched tail remains packed-file data, not fabricated decoded zeros.'
             ]}
    (a.output / 'dali-proof.json').write_text(json.dumps(proof, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'cases': len(cases), 'native_oracle': proof['first_load_native_oracle'],
                      'proof': meta(a.output / 'dali-proof.json')}))


if __name__ == '__main__':
    main()
