#!/usr/bin/env python3
"""Extract the original Demo Coder DOS boot and interpret only its depacker.

The original NMOS 6502 bytes run in py65 with mapped ROM/I/O reads rejected.
This stops before the first unpacked wrapper instruction at $8a00; no drive,
VIC, ROM, IRQ, or native timing is supplied. No downloaded host code is run.
"""
import argparse
from collections import Counter, deque
import hashlib
import importlib.metadata
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'research/next-round'))
from analyze_boot import BootCpu

DISK_SHA = 'b8c54fc1ca41c00cd81773ecff780649d892bc6497a84b7c67c79a9235d95e9b'
BOOT_SHA = 'b184ba219fa92d8ca46da54a423ba6f19b1a40352765ac96b8f1481dbe1aa532'
HANDOFF = 0x8a00
SIGNATURE = bytes.fromhex('a9 18 2c 11 d0 10 fb 2c 11 d0 30 fb')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sectors(track):
    assert 1 <= track <= 40
    return 21 if track <= 17 else 19 if track <= 24 else 18 if track <= 30 else 17


def sector(disk, track, number):
    assert 0 <= number < sectors(track)
    offset = 256 * (sum(sectors(t) for t in range(1, track)) + number)
    return disk[offset:offset + 256]


def linked(disk, track, number):
    result, chain, seen = bytearray(), [], set()
    while track:
        assert (track, number) not in seen
        seen.add((track, number))
        block = sector(disk, track, number)
        chain.append(dict(track=track, sector=number, sha256=sha(block)))
        result.extend(block[2:256 if block[0] else block[1] + 1])
        track, number = block[:2]
    return bytes(result), chain


def directory(disk):
    track, number, seen, records = 18, 1, set(), []
    while track:
        assert (track, number) not in seen
        seen.add((track, number))
        block = sector(disk, track, number)
        for index in range(8):
            entry = block[2 + 32 * index:32 + 32 * index]
            if not entry[0]:
                continue
            records.append(dict(directory_track=track, directory_sector=number,
                                directory_slot=index, type=entry[0],
                                start_track=entry[1], start_sector=entry[2],
                                name_hex=entry[3:19].hex(),
                                blocks=int.from_bytes(entry[28:30], 'little')))
        track, number = block[:2]
    return records


def ranges(addresses):
    result = []
    for address in sorted(addresses):
        if result and result[-1][1] == address:
            result[-1][1] += 1
        else:
            result.append([address, address + 1])
    return result


class GuardedRam:
    def __init__(self, blob, fill):
        self.data = bytearray([fill]) * 65536
        self.known = bytearray(65536)
        load = int.from_bytes(blob[:2], 'little')
        self.data[load:load + len(blob) - 2] = blob[2:]
        self.known[load:load + len(blob) - 2] = bytes([1]) * (len(blob) - 2)
        self.data[0:2] = b'\x2f\x37'
        self.known[0:2] = b'\x01\x01'
        self.pc = 0
        self.writes = Counter()
        self.stores = Counter()
        self.uninitialized_reads = Counter()
        self.port_writes = []

    def mapped(self, address):
        # The unmodelled cassette inputs have pull-ups. Only the low three
        # output pins choose the RAM/ROM/I/O overlays used by this depacker.
        pins = (self.data[1] & self.data[0]) | (7 & ~self.data[0])
        if 0xd000 <= address < 0xe000 and pins & 3:
            return 'I/O' if pins & 4 else 'character ROM'
        if 0xa000 <= address < 0xc000 and pins & 3 == 3:
            return 'BASIC ROM'
        if address >= 0xe000 and pins & 2:
            return 'KERNAL ROM'
        return None

    def __getitem__(self, address):
        assert isinstance(address, int) and 0 <= address < 65536
        mapping = self.mapped(address)
        if mapping:
            raise AssertionError(('Unmodelled read rejected', self.pc, address, mapping))
        if not self.known[address]:
            self.uninitialized_reads[address] += 1
        return self.data[address]

    def __setitem__(self, address, value):
        assert 0 <= address < 65536 and 0 <= value < 256
        mapping = self.mapped(address)
        assert mapping != 'I/O', ('Unmodelled I/O write rejected', self.pc, address)
        # ROM overlays do not inhibit writes to underlying RAM.
        self.data[address] = value
        self.known[address] = 1
        self.writes[address] += 1
        self.stores[(self.pc, address)] += 1
        if address <= 1:
            self.port_writes.append(dict(pc=self.pc, address=address, value=value))


def interpret(blob, fill):
    ram = GuardedRam(blob, fill)
    cpu = BootCpu(memory=ram, pc=0x080d)
    cpu.p, cpu.sp = cpu.UNUSED, 255
    history, counts, first_bytes = deque(maxlen=32), Counter(), {}
    for count in range(300_000):
        if cpu.pc == HANDOFF:
            break
        ram.pc = cpu.pc
        opcode = ram[cpu.pc]
        assert cpu.instruct[opcode].__name__ != 'inst_not_implemented', (cpu.pc, opcode)
        first_bytes.setdefault(cpu.pc, bytes(ram.data[cpu.pc:cpu.pc + 3]).hex(' '))
        history.append(dict(pc=cpu.pc, opcode=opcode, a=cpu.a, x=cpu.x,
                            y=cpu.y, p=cpu.p, sp=cpu.sp))
        counts[cpu.pc] += 1
        cpu.step()
    else:
        raise AssertionError(('Instruction limit', cpu.pc))
    assert bytes(ram.data[HANDOFF:HANDOFF + len(SIGNATURE)]) == SIGNATURE
    per_pc = {}
    for (pc, address), writes in ram.stores.items():
        item = per_pc.setdefault(pc, dict(writes=0, addresses=set()))
        item['writes'] += writes
        item['addresses'].add(address)
    receipt = dict(startup_fill=fill, steps=count, stop_pc=cpu.pc,
                   nominal_cpu_cycles=cpu.processorCycles,
                   stop_registers=dict(a=cpu.a, x=cpu.x, y=cpu.y, p=cpu.p,
                                       sp=cpu.sp, port00=ram.data[0], port01=ram.data[1]),
                   ram_sha256=sha(ram.data), last_instructions=list(history),
                   instruction_counts=dict(sorted(counts.items())),
                   first_instruction_bytes=dict(sorted(first_bytes.items())),
                   port_writes=ram.port_writes,
                   distinct_written_addresses=len(ram.writes),
                   write_ranges=ranges(ram.writes),
                   stores=[dict(pc=pc, writes=v['writes'],
                                ranges=ranges(v['addresses']))
                           for pc, v in sorted(per_pc.items())],
                   startup_read_addresses=dict(sorted(ram.uninitialized_reads.items())),
                   known_at_stop_ranges=ranges(a for a, v in enumerate(ram.known) if v))
    return ram, receipt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--disk', type=Path, default=ROOT / 'build/research/frontier-followup/demo-coder.d64')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/research/demo-coder')
    args = parser.parse_args()
    disk = args.disk.read_bytes()
    assert len(disk) == 196608 and sha(disk) == DISK_SHA
    records = directory(disk)
    assert len(records) == 10
    assert {(e['start_track'], e['start_sector']) for e in records} == {(18, 2)}
    boot, chain = linked(disk, 18, 2)
    assert len(boot) == 2675 and sha(boot) == BOOT_SHA
    assert boot[:14] == bytes.fromhex('01 08 0b 08 42 06 9e 32 30 36 31 00 00 00')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'boot.prg').write_bytes(boot)
    runs = [interpret(boot, fill) for fill in (0, 0xa5)]
    # Literal STA ($6b),Y and self-modified back-reference STA absolute,Y
    # are output writes. Backups, relocation and scratch writes are separate.
    output_sites = (0x30, 0x6a)
    for _, run in runs:
        assert run['first_instruction_bytes'][0x30].startswith('91 6b')
        assert run['first_instruction_bytes'][0x6a] == '99 00 40'
    output_addresses = [set(a for (pc, a) in ram.stores if pc in output_sites) for ram, _ in runs]
    assert output_addresses[0] == output_addresses[1]
    output = sorted(output_addresses[0])
    assert output, 'Output store site changed; inspect original instructions'
    assert all(runs[0][0].data[a] == runs[1][0].data[a] for a in output)
    for (ram, run) in runs:
        name = f"boot-handoff-{run['startup_fill']:02x}.ram"
        (args.output / name).write_bytes(ram.data)
        run['ram_path'] = str((args.output / name).relative_to(ROOT))
    (args.output / 'boot-handoff.ram').write_bytes(runs[0][0].data)
    report = dict(pass_=True, disk_sha256=DISK_SHA, disk_bytes=len(disk),
                  geometry_tracks=40, boot_sha256=BOOT_SHA, boot_bytes=len(boot),
                  dos_directory=records, dos_boot_chain=chain,
                  handoff=HANDOFF, handoff_signature=SIGNATURE.hex(' '),
                  bootstrap_cpu_source='research/next-round/analyze_boot.py',
                  bootstrap_cpu_sha256=sha((ROOT / 'research/next-round/analyze_boot.py').read_bytes()),
                  script_sha256=sha(Path(__file__).read_bytes()),
                  py65_version=importlib.metadata.version('py65'),
                  runs=[run for _, run in runs],
                  depacker_output_store_pcs=list(output_sites), output_bytes=len(output),
                  output_ranges=ranges(output),
                  output_equal_for_two_startup_fills=True,
                  output_sha256=sha(bytes(runs[0][0].data[a] for a in output)),
                  scope='Original boot instructions, two artificial startup RAM fills; mapped hardware/ROM reads rejected; stop before $8a00 wrapper. No native, VIC, drive, or ROM proof.')
    report['pass'] = report.pop('pass_')
    (args.output / 'boot-proof.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k: report[k] for k in ('pass', 'boot_bytes', 'handoff', 'output_bytes', 'output_ranges')}, indent=2))


if __name__ == '__main__':
    main()
