#!/usr/bin/env python3
"""Recover one Relax24 $991D resource with two functional models, no CPU.

Only the proven dead-value literal LDA at $99F2 is omitted. Its physical read,
bus effects and timing are not modeled. Frozen producer proofs stay read-only.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/relax24'
OUT = BASE / 'resource-recovery-01'
CONSUMER_SHA = 'e41c974f734065a2fec5d8162f464bb8a6ce0c28154d85f901e4f41129b4ce22'
INNER_SHA = 'd86df447082e7ee3d7d55bf8bfaabdc9abe0ff09784746a28656ba78f43eb9cd'
CHECKPOINT_SHA = '7276be5e402e1a21cbbf9b678b8c127e50bdc429b5400fa1ac135f1ebd07954d'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path.resolve().relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def checked(item):
    data = (ROOT / item['path']).read_bytes()
    assert len(data) == item['bytes'] and sha(data) == item['sha256'], item
    return data


def ranges(addresses):
    result = []
    for address in sorted(set(addresses)):
        if result and result[-1][1] == address:
            result[-1][1] += 1
        else:
            result.append([address, address + 1])
    return result


class EndOfStream(Exception):
    pass


class Memory:
    """Require established bytes for every meaningful mutable source read."""
    def __init__(self, data, known):
        self.data, self.known = bytearray(data), bytearray(known)
        self.inputs, self.outputs, self.reads = [], [], []
        self.output_addresses = set()
        self.match_provenance = Counter()
        self.compressed_overwritten = 0

    def read(self, address, purpose):
        address &= 65535
        assert self.known[address], ('Unknown meaningful read', address, purpose)
        value = self.data[address]
        self.reads.append(dict(address=address, value=value, purpose=purpose))
        if purpose == 'match':
            self.match_provenance['prior_resource_output' if address in self.output_addresses
                                  else 'established_input_image'] += 1
        return value

    def state(self, address, value):
        address &= 65535
        self.data[address] = value & 255
        self.known[address] = 1

    def word(self, address):
        return self.read(address, 'state') + 256 * self.read(address + 1, 'state')

    def setword(self, address, value):
        self.state(address, value)
        self.state(address + 1, value >> 8)

    def raw(self, address, kind):
        address &= 65535
        value = self.read(address, 'compressed-' + kind)
        self.inputs.append(dict(address=address, value=value, kind=kind))
        self.compressed_overwritten += address in self.output_addresses
        return value

    def put(self, address, value, kind):
        address &= 65535
        assert address not in self.output_addresses, ('Repeated resource output', address)
        self.state(address, value)
        self.output_addresses.add(address)
        self.outputs.append(dict(address=address, value=value, kind=kind))
        assert len(self.outputs) <= 65536


class Resource:
    """Transcribe format-relevant byte state, not original CPU execution.

The relocation and $CE..$E2 state remain in mutable memory. This does not
replace the actual instructions' unknown dead load with an invented CPU value.
"""
    def __init__(self, data, known, end):
        self.m = Memory(data, known)
        self.bits = 0
        self.blocks, self.dead_reads = [], []
        self.stage = 'setup'
        # Actual descriptor does not cross the setup's DEC/BNE low-byte edge.
        assert end & 255 >= 6
        for offset in range(28, -1, -1):
            self.m.state(0xd8 + offset, self.m.read(0x9900 + offset, 'relocation'))
        for offset in range(5):
            self.m.state(0xd3 + offset, self.m.read(end - 5 + offset, 'descriptor'))
        self.m.setword(0xe1, end - 5)
        self.end = end
        self.initial_counter = self.m.word(0xd4)
        self.initial_cursor = self.m.word(0xd6)
        self.input_first = end - 5 - self.initial_counter

    def raw(self, kind):
        pointer = (self.m.word(0xe1) - 1) & 65535
        self.m.setword(0xe1, pointer)
        assert self.input_first <= pointer < self.end - 5, ('Compressed pointer', pointer)
        return self.m.raw(pointer, kind)

    def bit(self):
        buffer = self.m.read(0xd3, 'buffer')
        self.m.state(0xd3, buffer >> 1)
        carry = buffer & 1
        if not buffer >> 1:
            counter = self.m.word(0xd4)
            if not counter:
                raise EndOfStream(dict(stage=self.stage, pointer=self.m.word(0xe1),
                                       bits_returned=self.bits))
            self.m.setword(0xd4, counter - 1)
            byte = self.raw('refill')
            self.m.state(0xd3, 128 | byte >> 1)
            carry = byte & 1
        self.bits += 1
        return carry

    def literal_length(self):
        self.stage = 'literal-length'
        self.m.state(0xce, 0)
        self.m.state(0xd0, 0)
        low = 0
        for _ in range(65536):
            total = 2 * low + self.bit()
            low, carry = total & 255, total >> 8
            if low == 0 and not carry:
                return None
            self.m.state(0xd0, (2 * self.m.read(0xd0, 'literal-high') + carry) & 255)
            if not self.bit():
                self.m.state(0xcf, low)
                return low + 256 * self.m.read(0xd0, 'literal-high')
        raise AssertionError('Literal bit budget')

    def copy_begin(self):
        y = self.m.read(0xcf, 'length-low')
        if y:
            result = self.m.read(0xd6, 'destination-low') - y
            self.m.state(0xd6, result)
            if result < 0:
                self.m.state(0xd7, self.m.read(0xd7, 'destination-high') - 1)
        return y

    def copy(self, kind):
        """Original $99E3..$9A0A byte/page loop, including zero/sign edges."""
        y = self.copy_begin()
        count = 0
        while True:
            if y == 0 and count == 0:
                # Initial Y=0 jumps to CPY D0, not a 256-byte body iteration.
                high = self.m.read(0xd0, 'length-high')
                if high == 0:
                    return 0
                self.m.state(0xd2, self.m.read(0xd2, 'match-high') - 1)
                self.m.state(0xd0, high - 1)
                if self.m.read(0xd0, 'length-high') & 128:
                    return 0
                self.m.state(0xd7, self.m.read(0xd7, 'destination-high') - 1)
            source = (self.m.word(0xd1) + y) & 65535
            if kind == 'literal':
                self.dead_reads.append(dict(address=source, known=bool(self.m.known[source])))
                value = self.raw('literal')
            else:
                value = self.m.read(source, 'match')
            y = (y - 1) & 255
            self.m.put(self.m.word(0xd6) + y, value, kind)
            count += 1
            if y:
                continue
            high = self.m.read(0xd0, 'length-high')
            if high == 0:
                return count
            self.m.state(0xd2, self.m.read(0xd2, 'match-high') - 1)
            self.m.state(0xd0, high - 1)
            if self.m.read(0xd0, 'length-high') & 128:
                return count
            self.m.state(0xd7, self.m.read(0xd7, 'destination-high') - 1)
            # Y=0 now enters once; DEY=$FF begins a 256-byte page.

    def literal_setup(self, length):
        counter = self.m.word(0xd4)
        assert counter >= length, ('Literal counter underflow', counter, length)
        low, high = self.m.read(0xcf, 'literal-low'), self.m.read(0xd0, 'literal-high')
        # Retain both original high-byte SBC steps and their carry.
        result = self.m.read(0xd4, 'counter-low') - low
        self.m.state(0xd1, result)
        self.m.state(0xd4, result)
        result_high = self.m.read(0xd5, 'counter-high') - int(result < 0)
        self.m.state(0xd2, result_high)
        self.m.state(0xd5, result_high - high - int(result_high < 0))
        assert self.m.word(0xd4) == counter - length
        return high

    def literals(self, length):
        high = self.literal_setup(length)
        self.stage = 'literal-copy'
        count = self.copy('literal')
        assert high <= 128 and count == length, ('Nonordinary literal page edge', high, count, length)
        return count

    def match(self):
        self.stage = 'match-length'
        self.m.setword(0xd1, 0)
        n = 0
        while True:
            total = 2 * n + self.bit()
            n, carry = total & 255, total >> 8
            assert carry == 0, 'Match-prefix incoming ADC carry must be zero'
            if not n:
                break
            if n & 128:
                self.m.state(0xce, self.m.read(0xce, 'bucket') + 1)
                break
            if not self.bit():
                self.m.state(0xce, self.m.read(0xce, 'bucket') + 1)
                break
        length = (n + 2) & 255
        self.m.state(0xcf, length)
        if length & 252:
            self.m.state(0xce, self.m.read(0xce, 'bucket') + 1)
        bucket = self.m.read(0xce, 'bucket')
        self.stage = 'gap-selector'
        for _ in range(3):
            self.m.state(0xce, 2 * self.m.read(0xce, 'selector') + self.bit())
        selected = self.m.read(0xce, 'selector') & 7
        self.stage = 'gap-payload'
        while True:
            code = self.m.read(0xce, 'selector')
            packed = self.m.read(0xe4 + (code >> 1), 'gap-table')
            width = (packed if code & 1 else packed >> 3) & 7
            for _ in range(width):
                value = (2 * self.m.word(0xd1) + self.bit()) & 65535
                self.m.setword(0xd1, value)
            if not self.m.read(0xce, 'selector') & 7:
                break
            self.m.setword(0xd1, self.m.word(0xd1) + 1)
            self.m.state(0xce, self.m.read(0xce, 'selector') - 1)
        gap = self.m.word(0xd1)
        self.m.setword(0xd1, self.m.word(0xd6) + gap - 1)
        self.m.state(0xce, self.m.read(0xce, 'mode') + 1)
        self.stage = 'match-copy'
        assert self.m.read(0xd0, 'literal-high-final') == 0
        copied = self.copy('match')
        assert copied == length
        return dict(length=length, bucket=bucket, selector=selected, gap=gap)

    def run(self):
        for index in range(65536):
            block = dict(index=index, input_first_event=len(self.m.inputs),
                         output_first_event=len(self.m.outputs), cursor=self.m.word(0xd6))
            self.blocks.append(block)
            try:
                length = self.literal_length()
                block['literal_length'] = 0 if length is None else length
                if length is not None:
                    self.literals(length)
                block['match'] = self.match()
            except EndOfStream as end:
                self.termination = end.args[0]
                block['termination'] = self.termination
                return
            finally:
                block.update(input_end_event=len(self.m.inputs), output_end_event=len(self.m.outputs),
                             cursor_end=self.m.word(0xd6), remaining=self.m.word(0xd4),
                             buffer=self.m.read(0xd3, 'buffer'))
        raise AssertionError('Resource command budget')


class StreamReference:
    """Independent integer/interval parser without register transcription.

Accept only ordinary observed lengths/counters; do not generalize byte edges.
"""
    def __init__(self, data, known, descriptor, end, widths):
        self.m = Memory(data, known)
        self.buffer = descriptor[0]
        self.remaining = int.from_bytes(descriptor[1:3], 'little')
        self.cursor = int.from_bytes(descriptor[3:5], 'little')
        self.pointer = end - 5
        self.widths = widths
        self.bits = 0
        self.stage = 'literal-length'

    def raw(self, kind):
        self.pointer = (self.pointer - 1) & 65535
        return self.m.raw(self.pointer, kind)

    def bit(self):
        if self.buffer == 1:
            if self.remaining == 0:
                self.buffer = 0  # Original sentinel LSR precedes the EOF test.
                raise EndOfStream(dict(stage=self.stage, pointer=self.pointer, bits_returned=self.bits))
            self.remaining -= 1
            byte = self.raw('refill')
            self.buffer = 128 | byte // 2
            result = byte % 2
        else:
            assert self.buffer > 1
            result = self.buffer % 2
            self.buffer //= 2
        self.bits += 1
        return result

    def integer(self, match=False):
        value = self.bit()
        while value and (not match or value < 128):
            if not self.bit():
                break
            value = 2 * value + self.bit()
            assert value <= (255 if match else 32768), ('Reference length edge', value)
        return value

    def run(self):
        try:
            for _ in range(65536):
                self.stage = 'literal-length'
                length = self.integer()
                assert length <= self.remaining
                self.remaining -= length
                self.stage = 'literal-copy'
                for offset in range(length):
                    self.m.put(self.cursor - 1 - offset, self.raw('literal'), 'literal')
                self.cursor = (self.cursor - length) & 65535
                self.stage = 'match-length'
                encoded = self.integer(True)
                length = (encoded + 2) & 255
                bucket = int(encoded != 0) + int(length & 252 != 0)
                self.stage = 'gap-selector'
                selected = 0
                for _ in range(3):
                    selected = 2 * selected + self.bit()
                gap = 0
                self.stage = 'gap-payload'
                for field in range(selected, -1, -1):
                    for _ in range(self.widths[8 * bucket + field]):
                        gap = (2 * gap + self.bit()) & 65535
                    if field:
                        gap = (gap + 1) & 65535
                self.stage = 'match-copy'
                for offset in range(length):
                    source = (self.cursor + gap + length - 1 - offset) & 65535
                    value = self.m.read(source, 'match')
                    self.m.put(self.cursor - 1 - offset, value, 'match')
                self.cursor = (self.cursor - length) & 65535
        except EndOfStream as end:
            self.termination = end.args[0]
            return
        raise AssertionError('Reference command budget')


def consumer_sites(image):
    """Assert only identified instruction sites, never sweep assets as code."""
    sites = [
        (0xc000, '78 a9 7f 8d 0d dc 2c 0d dc',
         'SEI; disable CIA1 interrupt sources and read ICR. First hardware boundary is C003.'),
        (0xc016, 'a2 f8 a0 c1 8e fa ff 8c fb ff', 'Install NMI vector C1F8.'),
        (0xc020, 'a9 75 a2 00 a0 ae 8d 12 d0 8e fe ff 8c ff ff',
         'Request raster75 and IRQ vector AE00; no timing or actual delivery claim.'),
        (0xc02f, 'a9 15 85 01', 'Request CPU port15; no port execution modeled.'),
        (0xc156, 'a2 30 a0 30 20 00 ac', 'First foreground AC00 call has X=30,Y=30.'),
        (0xc15d, 'a5 ae 38 e9 02 85 ae a5 af e9 00 85 af a0 00 b1 ae 8d b2 c3 c8 b1 ae 8d b3 c3',
         'Subtract2 from returned AE/AF and patch C3B1 JMP operand from the trailing two bytes.'),
        (0xc177, 'a2 ff a0 ff 20 00 ac', 'Second foreground AC00 call has X=FF,Y=FF.'),
        (0xc18b, 'a2 00 8a 9d 00 c8 9d 00 c9 e8 d0 f7 a9 ae 8d ff ff 4c 9c c1',
         'Clear C800/C900, set IRQ-vector high byteAE and wait at C19C.'),
        (0xac1f, 'a9 02 20 63 ac 20 dc ac 20 83 ac 85 ae 20 83 ac 85 af',
         'AC00 sends command02 with supplied X/Y, then receives low/high output pointer.'),
        (0xac4d, 'a0 00 91 ae e6 ae d0 02 e6 af d0 d8',
         'Received data byte stored through AE/AF; increment cursor before next byte.'),
        (0xac59, '18 ae f8 ac ac f9 ac a9 00 60',
         'Clear-carry return path restores request X/Y and returns A=0.'),
        (0xac63, '48 8e f8 ac 8c f9 ac a9 24 8d 00 dd 20 dc ac 68 20 b0 ac ad f8 ac 20 b0 ac ad f9 ac 20 b0 ac 60',
         'Store request X/Y; send original A, then saved X, then saved Y via ACB0/DD00.'),
        (0xc380, '78 a2 00 a0 20 86 04 84 05 a2 01 a0 08 86 02 84 03 a0 00 b1 04 91 02 c8 d0 f9 e6 03 e6 05 a5 05 c9 ac d0 ed',
         'Later source contains relocation2000..ABFF to0801..9400; reachability not executed.'),
        (0xc3a4, 'a9 37 85 01 20 a3 fd 20 15 fd 20 5b ff 4c ea ea',
         'Later port/KERNAL calls and patched JMP; not executed or given ROM responses.'),
    ]
    result = []
    for address, encoded, meaning in sites:
        code = bytes.fromhex(encoded)
        assert image[address:address + len(code)] == code, (hex(address), encoded)
        result.append(dict(address=address, end_exclusive=address + len(code),
                           bytes=code.hex(' '), interpretation=meaning))
    return result


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    consumer_path = BASE / 'article-analysis/consumer-proof.json'
    inner_path = BASE / 'decoder-analysis/inner-proof.json'
    checkpoint_path = BASE / 'resource-analysis/format-checkpoint.json'
    assert sha(consumer_path.read_bytes()) == CONSUMER_SHA
    assert sha(inner_path.read_bytes()) == INNER_SHA
    assert sha(checkpoint_path.read_bytes()) == CHECKPOINT_SHA
    consumer = json.loads(consumer_path.read_text())
    inner = json.loads(inner_path.read_text())
    checkpoint = json.loads(checkpoint_path.read_text())
    assert consumer['pass'] and inner['pass'] and checkpoint['pass']
    source = checked(consumer['source'])
    mask_item = next(item for item in inner['artifacts'] if item['path'].endswith('inner-known-mask.bin'))
    producer_known = checked(mask_item)
    assert all(producer_known[0x801:0xffff])
    # Exclude the producer's decoder workspace/relocation knowledge. This
    # resource starts only from its proven output bytes, as the consumer did.
    known = bytearray(65536)
    known[0x801:0xffff] = producer_known[0x801:0xffff]
    assert sha(source[0x801:0xffff]) == inner['format_decode']['output_sha256']
    assert source[0x99f2:0x99fe] == bytes.fromhex('b1 d1 a6 ce d0 03 20 d8 00 88 91 d6')
    assert source[0x9900:0x990c] == bytes.fromhex('a5 e1 d0 02 c6 e2 c6 e1 ad 00 00 60')
    resource = next(item for item in consumer['resource_calls'] if item['end_pointer'] == 0x8df6)
    assert source[0x8df1:0x8df6] == bytes.fromhex('27 f1 0d 00 d0')
    # Match every frozen format byte at the original CPU's strict first-read
    # boundary. This is an arithmetic check; that CPU fragment is not rerun.
    anchor = Resource(source, known, 0x9f57)
    anchor_length = anchor.literal_length()
    assert anchor_length == 4
    anchor.literal_setup(anchor_length)
    anchor_y = anchor.copy_begin()
    frozen = consumer['strict_resource_call']
    anchor_states = {key: anchor.m.data[int(key, 16)] for key in frozen['format_state']}
    assert anchor_states == frozen['format_state']
    assert frozen['boundary'] == ['unknown read', 0x99f2, 0x223]
    assert anchor.m.word(0xd1) + anchor_y == 0x223 and not anchor.m.known[0x223]
    packed = source[0x990c:0x991d]
    widths = [((packed[index // 2] >> 3) if index % 2 == 0 else packed[index // 2]) & 7
              for index in range(24)]
    actual = Resource(source, known, 0x8df6)
    actual.run()
    reference = StreamReference(source, known, source[0x8df1:0x8df6], 0x8df6, widths)
    reference.run()
    checks = dict(all_input_events_exact=actual.m.inputs == reference.m.inputs,
                  all_output_events_exact=actual.m.outputs == reference.m.outputs,
                  output_image_exact=all(actual.m.data[a] == reference.m.data[a]
                                         for a in actual.m.output_addresses),
                  output_addresses_exact=actual.m.output_addresses == reference.m.output_addresses,
                  final_cursor_exact=actual.m.word(0xd6) == reference.cursor,
                  final_input_pointer_exact=actual.m.word(0xe1) == reference.pointer,
                  final_counter_exact=actual.m.word(0xd4) == reference.remaining,
                  final_bit_buffer_exact=actual.m.read(0xd3, 'buffer') == reference.buffer,
                  final_bits_exact=actual.bits == reference.bits,
                  termination_exact=actual.termination == reference.termination,
                  complete_input_consumption=len(actual.m.inputs) == resource['remaining_byte_counter']
                  and reference.remaining == 0 and reference.pointer == 0x8000)
    assert all(checks.values()), checks
    output_ranges = ranges(actual.m.output_addresses)
    assert len(output_ranges) == 1
    first, end = output_ranges[0]
    assert len(actual.m.outputs) == end - first and end == actual.initial_cursor
    assert [item['address'] for item in actual.m.outputs] == list(range(end - 1, first - 1, -1))
    sites = consumer_sites(actual.m.data)
    checks['identified_consumer_sites_exact'] = True
    artifacts = []
    for name, value in [('resource.ram', actual.m.data), ('resource-known-mask.bin', actual.m.known),
                        ('resource-output.prg', first.to_bytes(2, 'little') + actual.m.data[first:end])]:
        path = OUT / name
        path.write_bytes(value)
        artifacts.append(record(path))
    for name, value in [('input-events.json', actual.m.inputs), ('output-events.json', actual.m.outputs),
                        ('commands.json', actual.blocks), ('meaningful-read-events.json', actual.m.reads),
                        ('dead-literal-reads.json', actual.dead_reads), ('consumer-sites.json', sites)]:
        path = OUT / name
        path.write_text(json.dumps(value, indent=2) + '\n')
        artifacts.append(record(path))
    report = dict(script=record(Path(__file__)), consumer_proof=record(consumer_path),
                  inner_proof=record(inner_path), checkpoint=record(checkpoint_path),
                  source=consumer['source'], producer_known_mask=mask_item,
                  initial_known_ranges=[[0x801, 0xffff]],
                  frozen_original_CPU_prefix_anchor=dict(known_format_bytes_exact=True,
                      literal_length=anchor_length, bits=anchor.bits, boundary=frozen['boundary'],
                      completed_original_instructions=frozen['completed_instructions'],
                      scope='All frozen format-state bytes match arithmetic setup; no new CPU run.'),
                  descriptor=resource, format_comparison=checks,
                  output=dict(first=first, end_exclusive=end, bytes=end - first,
                              sha256=sha(actual.m.data[first:end]), stores=len(actual.m.outputs)),
                  input=dict(bytes=len(actual.m.inputs), ranges=ranges(item['address'] for item in actual.m.inputs),
                             refills=sum(item['kind'] == 'refill' for item in actual.m.inputs),
                             literals=sum(item['kind'] == 'literal' for item in actual.m.inputs),
                             bits=actual.bits, overwritten_compressed_reads=actual.m.compressed_overwritten),
                  command_count=len(actual.blocks), termination=actual.termination,
                  match_provenance=dict(actual.m.match_provenance),
                  recovered_consumer=dict(entry=0xc000, first_hardware_instruction=0xc003,
                      first_request_call=0xc15a, first_request=[2, 0x30, 0x30],
                      second_request_call=0xc17b, second_request=[2, 255, 255],
                      source_sites_checked=len(sites),
                      scope='Instruction-derived source path only. Two request bytes spell ASCII00; '
                            'drive directory matching, transferred file identity and whole-menu state remain open.'),
                  literal_dead_read_abstraction=dict(instruction=0x99f2, mode_condition='CE=0',
                      omitted_value_reads=len(actual.dead_reads),
                      omitted_unknown_value_reads=sum(not item['known'] for item in actual.dead_reads),
                      scope='Only value/N/Z dependency omitted in both pure models. No CPU byte/state supplied, '
                            'physical read emulated, bus/side-effect/timing or continuous CPU claim.'),
                  preconditions=['Pinned independently checked inner output and its exact known mask only.',
                      'Functional memory is mutable, 16-bit addressed RAM; no IRQ/ROM/I/O responses.',
                      'Every meaningful compressed/table/match read requires an established byte.',
                      'This isolates the final embedded resource; preceding initialization is not executed.'],
                  artifacts=artifacts,
                  scope='Functional resource-format recovery and independent stream-model event agreement only. '
                        'No original-CPU/native execution, initialized whole-menu state or side-2/article claim.',
                  pass_=all(checks.values()))
    report['pass'] = report.pop('pass_')
    path = OUT / 'resource-proof.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(dict(receipt=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()),
                         output=report['output'], input=report['input'], pass_=report['pass']), indent=2))


if __name__ == '__main__':
    main()
