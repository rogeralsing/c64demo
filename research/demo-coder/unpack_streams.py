#!/usr/bin/env python3
"""Extract Demo Coder's raw Bitfire files and run its original plain Dali path.

DOS aliases are not part names. Extraction uses the writer's documented sector
ordering and checks the release's own directory. The CPU starts at $02cc, not
the hardware loader. Mapped I/O/ROM reads and loader entry are rejected.
"""
import argparse
from collections import Counter
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

from inspect_boot import ROOT, DISK_SHA, sha, sector, sectors, ranges, GuardedRam
sys.path.insert(0, str(ROOT / 'research/next-round'))
from unpack_files import DaliCpu

WRITER_COMMIT = '5a3964b533656332c12cc0904f2ce92f44499c6f'


def order(track):
    step = 4 if track <= 17 else 3
    return [n for residue in range(step) for n in range(residue, sectors(track), step)]


def extract(disk):
    result = []
    previous_end = None
    for directory_number in (18, 17):
        directory = sector(disk, 18, directory_number)
        track, slot, byte, tag = directory[:4]
        if directory_number == 18:
            assert (track, slot, byte, tag) == (1, 0, 0, 0xf0)
        else:
            assert [track, slot, byte] == previous_end
        count = 0
        for index in range(63):
            fields = [directory[4 + index + 63*k] for k in range(4)]
            if not any(fields):
                assert not any(directory[4 + j + 63*k]
                               for j in range(index, 63) for k in range(4))
                break
            lo, high_minus_one, length_lo, length_hi = fields
            load = lo | (((high_minus_one + 1) & 255) << 8)
            length = 1 + length_lo + 256 * length_hi
            start = [track, slot, byte]
            payload, used = bytearray(), []
            while len(payload) < length:
                if slot == len(order(track)):
                    track += 1
                    if track == 18:
                        track += 1
                    slot = 0
                physical_sector = order(track)[slot]
                block = sector(disk, track, physical_sector)
                take = min(256 - byte, length - len(payload))
                used.append(dict(track=track, logical_slot=slot,
                                 physical_sector=physical_sector, first=byte,
                                 end_exclusive=byte + take))
                payload.extend(block[byte:byte + take])
                byte += take
                if byte == 256:
                    slot += 1
                    byte = 0
            result.append(dict(file=len(result), load=load, packed_bytes=length,
                               directory_sector=directory_number,
                               directory_slot=index, directory_fields=fields,
                               stream_start=start, stream_end=[track, slot, byte],
                               segments=used, payload=bytes(payload)))
            count += 1
        previous_end = [track, slot, byte]
        if count < 63:
            break
    assert len(result) == 68
    return result


class PlainRam(GuardedRam):
    def __init__(self, memory, known):
        self.data, self.known = memory, known
        self.pc = 0
        self.writes, self.stores = Counter(), Counter()
        self.uninitialized_reads = Counter()
        self.port_writes, self.output_events = [], []
        self.back_reference_reads = 0
        self.packed_reads = Counter()
        self.ignored_nop_reads = Counter()

    def __getitem__(self, address):
        if not self.known[address]:
            assert self.data[self.pc] == 0x0c, ('Unestablished input read', self.pc, address)
            # Stable NMOS $0c NOP reads its absolute target but uses no value.
            # Preserve that read and report it rather than inventing input data.
            self.ignored_nop_reads[(self.pc, address)] += 1
        if self.pc == 0x3c7:
            # Operand fetches at $03c8/$03c9 are not dictionary reads.
            if address not in (0x3c7, 0x3c8, 0x3c9):
                assert self.known[address], ('Back-reference lacks established RAM', address)
                self.back_reference_reads += 1
        if self.pc in (0x2ee, 0x32e, 0x384) and address >= 0x400:
            self.packed_reads[address] += 1
        return super().__getitem__(address)

    def __setitem__(self, address, value):
        super().__setitem__(address, value)
        if self.pc in (0x386, 0x3ca):
            self.output_events.append((address, value))


def installed(boot):
    memory = bytearray(boot)
    # Literal original $8078 loop, in its actual X order. The four overlapping
    # destination bytes receive exactly the same original source values.
    destinations = {}
    for x in (0, *range(255, 0, -1)):
        for source, target in ((0x82b1, 0x200), (0x83ad, 0x2fc)):
            address, value = target + x, boot[source + x]
            if address in destinations:
                assert destinations[address] == value
            destinations[address] = value
            memory[address] = value
    assert set(destinations) == set(range(0x200, 0x3fc))
    assert memory[0x2cc:0x2d2] == bytes.fromhex('a9 96 a2 60 d0 09')
    assert memory[0x386:0x388] == b'\x91\xf3'
    assert memory[0x3ca:0x3cc] == b'\x91\xf3'
    return memory


def unpack(entry, memory, known, resident):
    load, payload = entry['load'], entry['payload']
    assert load + len(payload) <= 65536
    memory[load:load + len(payload)] = payload
    known[load:load + len(payload)] = bytes([1]) * len(payload)
    memory[0x200:0x3fc] = resident
    known[0x200:0x3fc] = bytes([1]) * len(resident)
    # Controlled plain-depack precondition: all RAM visible, including RAM
    # under I/O. This is not execution of any effect's hardware-call wrapper.
    memory[0:2] = b'\x2f\x34'
    known[0:2] = b'\x01\x01'
    memory[0xf0:0xf2] = load.to_bytes(2, 'little')
    known[0xf0:0xf2] = b'\x01\x01'
    ram = PlainRam(memory, known)
    cpu = DaliCpu(memory=ram, pc=0x2cc)
    cpu.p, cpu.sp = cpu.UNUSED, 255
    cpu.stPushWord(0x1ffe)  # Diagnostic return; never execute $1fff.
    ram.writes.clear()
    counts = Counter()
    for steps in range(3_000_000):
        if cpu.pc == 0x1fff:
            break
        assert 0x200 <= cpu.pc < 0x3fa, ('Unexpected control transfer', cpu.pc)
        assert cpu.pc not in (0x20c, 0x224, 0x22e, 0x300), ('Hardware/IRQ entry rejected', cpu.pc)
        ram.pc = cpu.pc
        opcode = ram[cpu.pc]
        assert cpu.instruct[opcode].__name__ != 'inst_not_implemented', (cpu.pc, opcode)
        counts[cpu.pc] += 1
        cpu.step()
    else:
        raise AssertionError(('Instruction limit', cpu.pc))
    target = int.from_bytes(payload[:2], 'little')
    written_end = int.from_bytes(memory[0xf3:0xf5], 'little')
    written_size = (written_end - target) & 65535
    addresses = set(a for a, _ in ram.output_events)
    assert addresses == {(target + i) & 65535 for i in range(written_size)}
    assert len(ram.output_events) == written_size
    assert sum(ram.uninitialized_reads.values()) == sum(ram.ignored_nop_reads.values())
    # The original $03d3..$03df path stops when source and destination meet.
    # In-place Dali deliberately leaves the rest as unencoded raw literals.
    # Those bytes were loaded in their final addresses and are not STA output.
    converged = counts[0x3dd] == 1
    assert converged, 'This release proof currently establishes only its in-place streams'
    end = load + len(payload)
    assert target <= written_end <= end
    tail = bytes(memory[written_end:end])
    assert tail == payload[written_end - load:], 'Untouched raw tail changed'
    assert not addresses.intersection(range(written_end, end))
    size = end - target
    output = bytes(memory[(target + i) & 65535] for i in range(size))
    record = {k: v for k, v in entry.items() if k != 'payload'}
    record.update(target=target, output_end=end, output_bytes=size,
                  output_sha256=sha(output), packed_sha256=sha(payload),
                  termination='in-place source/destination convergence',
                  cpu_written_end=written_end, cpu_written_bytes=written_size,
                  cpu_written_sha256=sha(output[:written_size]),
                  untouched_raw_tail_bytes=len(tail), untouched_raw_tail_sha256=sha(tail),
                  untouched_raw_tail_packed_offset=written_end-load,
                  output_write_ranges=ranges(addresses),
                  output_event_sha256=sha(b''.join(a.to_bytes(2, 'little') + bytes([v])
                                                 for a, v in ram.output_events)),
                  original_instructions=steps, nominal_cpu_cycles=cpu.processorCycles,
                  back_reference_reads=ram.back_reference_reads,
                  ignored_nop_reads=[dict(pc=pc, address=a, count=n)
                                     for (pc, a), n in sorted(ram.ignored_nop_reads.items())],
                  packed_addresses_read=len(ram.packed_reads),
                  final_source_pointer=int.from_bytes(memory[0xf0:0xf2], 'little'),
                  instruction_counts=dict(sorted(counts.items())),
                  status='returned')
    return output, record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disk', type=Path, default=ROOT / 'build/research/frontier-followup/demo-coder.d64')
    parser.add_argument('--boot', type=Path, default=ROOT / 'build/research/demo-coder/boot-handoff.ram')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/research/demo-coder/streams')
    parser.add_argument('--limit', type=int, default=68, help='Prefix of the original file order, maximum 68')
    args = parser.parse_args()
    assert 1 <= args.limit <= 68
    disk, boot = args.disk.read_bytes(), args.boot.read_bytes()
    assert len(disk) == 196608 and sha(disk) == DISK_SHA
    proof = json.loads(args.boot.with_name('boot-proof.json').read_text())
    assert proof['pass'] and sha(boot) == proof['runs'][0]['ram_sha256']
    memory = installed(boot)
    resident = memory[0x200:0x3fc]
    known = bytearray(65536)
    for first, end in proof['output_ranges']:
        known[first:end] = bytes([1]) * (end - first)
    # Dali's other ZP slots must be written before use; preserved boot ZP values
    # are deliberately not marked as known dictionary or scratch input.
    files = extract(disk)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'resident.bin').write_bytes(resident)
    results = []
    for entry in files[:args.limit]:
        stem = f"{entry['file']:03d}-{entry['load']:04x}"
        packed_path = args.output / (stem + '-packed.prg')
        packed_path.write_bytes(entry['load'].to_bytes(2, 'little') + entry['payload'])
        output, result = unpack(entry, memory, known, resident)
        path = args.output / f"{entry['file']:03d}-{result['target']:04x}-unpacked.prg"
        path.write_bytes(result['target'].to_bytes(2, 'little') + output)
        result.update(packed_path=str(packed_path.relative_to(ROOT)),
                      output_path=str(path.relative_to(ROOT)))
        results.append(result)
        print(f"{entry['file']:02d}: {entry['load']:04x} packed {len(entry['payload']):5d} -> "
              f"{result['target']:04x} {len(output):5d} bytes; {result['original_instructions']} instructions", flush=True)
    report = dict(pass_=True, disk_sha256=DISK_SHA, boot_sha256=sha(boot),
                  resident_sha256=sha(resident), resident_source=[0x82b1, 0x84ad],
                  resident_destination=[0x200, 0x3fc], plain_entry=0x2cc,
                  source_pointer=[0xf0, 0xf1], output_pointer=[0xf3, 0xf4],
                  host_memory_precondition=dict(port00=0x2f, port01=0x34,
                                                mapping='All RAM, no ROM/I/O reads supplied'),
                  writer_commit_for_directory_layout=WRITER_COMMIT,
                  total_directory_files=len(files), files=results,
                  script_sha256=sha(Path(__file__).read_bytes()),
                  cpu_source_sha256=sha((ROOT / 'research/next-round/unpack_files.py').read_bytes()),
                  py65_version=importlib.metadata.version('py65'),
                  scope='Original plain depacker in raw-file order; installed pristine resident before each call; no IRQ/drive/ROM/I/O execution. Native load order and effect identity remain unproved.')
    report['pass'] = report.pop('pass_')
    (args.output / 'unpacked-index.json').write_text(json.dumps(report, indent=2) + '\n')


if __name__ == '__main__':
    main()
