#!/usr/bin/env python3
"""Extract the current original Colors disks and stop their boot before ROM.

Only six original official 6502 instructions precede the first KERNAL call.
No KERNAL, drive, I/O, IRQ, packed part, or effect is supplied or executed.
"""
import argparse
from collections import Counter, deque
import hashlib
import importlib.metadata
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/colors'
DISK_SHAS = [
    '94bde11ed515f6312fbd77efff9f1fe5c2cdbf25587f0eabada566e0430b1ad6',
    'f1b2e7ace21a9492f05860666397790a5b42aa9f22d2083100de8af592783d04',
    '1c1532eb273e01a81c590557f92b7d9305d961d23615e3f43f4c4de325775585',
]
BOOT_SHAS = [
    '6c83458c3ab427c4d3a11abe50ffbfcb6d8922f99da864b4a54cac412f967f3b',
    '1122e6e2e32fd8e0891bf8a45df9c7d4744834d2725e0d47bea6a392c32c44ac',
    '96ab40fb745fbfac51e419093c2523d80c7e3296fb740e6029e020a3a4c56e88',
]
SIGNATURE = bytes.fromhex('a9 ff 85 fc a2 04 a9 08 85 ba a5 ba 20 0c ed')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def sectors(track):
    assert 1 <= track <= 35
    return 21 if track <= 17 else 19 if track <= 24 else 18 if track <= 30 else 17


def sector(disk, track, number):
    assert 0 <= number < sectors(track)
    offset = 256 * (sum(sectors(t) for t in range(1, track)) + number)
    return disk[offset:offset+256]


def linked(disk, track, number):
    data, chain, seen = bytearray(), [], set()
    while track:
        assert (track, number) not in seen
        seen.add((track, number))
        block = sector(disk, track, number)
        chain.append(dict(track=track, sector=number, sha256=sha(block)))
        data.extend(block[2:256 if block[0] else block[1]+1])
        track, number = block[:2]
    return bytes(data), chain


def directory(disk):
    records, seen, track, number = [], set(), 18, 1
    while track:
        assert (track, number) not in seen
        seen.add((track, number))
        block = sector(disk, track, number)
        for slot in range(8):
            item = block[2+32*slot:32+32*slot]
            if item[0]:
                records.append(dict(directory_track=track, directory_sector=number,
                                    slot=slot, type=item[0], type_low_bits=item[0]&7,
                                    first_track=item[1], first_sector=item[2],
                                    raw_name_hex=item[3:19].hex(),
                                    blocks=int.from_bytes(item[28:30], 'little')))
        track, number = block[:2]
    return records


class InitialRam:
    def __init__(self, blob):
        self.data = bytearray(65536)
        self.known = bytearray(65536)
        first = int.from_bytes(blob[:2], 'little')
        self.data[first:first+len(blob)-2] = blob[2:]
        self.known[first:first+len(blob)-2] = bytes([1])*(len(blob)-2)
        self.data[:2] = b'\x2f\x37'
        self.known[:2] = b'\x01\x01'
        self.pc, self.writes = 0, []

    def __getitem__(self, address):
        assert 0 <= address < 0xa000, ('ROM/I/O read rejected', self.pc, address)
        assert self.known[address], ('Unestablished initial input', self.pc, address)
        return self.data[address]

    def __setitem__(self, address, value):
        assert 0 <= address < 0xa000
        self.data[address], self.known[address] = value, 1
        self.writes.append(dict(pc=self.pc, address=address, value=value))


def bounded_entry(blob):
    from py65.devices.mpu6502 import MPU
    ram = InitialRam(blob)
    cpu = MPU(memory=ram, pc=0x810)
    cpu.p, cpu.sp = cpu.UNUSED, 255
    instructions = []
    for _ in range(6):
        ram.pc = cpu.pc
        instructions.append(dict(pc=cpu.pc, opcode=ram[cpu.pc]))
        cpu.step()
    assert cpu.pc == 0x81c and ram.data[0x81c:0x81f] == b'\x20\x0c\xed'
    assert cpu.a == 8 and cpu.x == 4 and ram.data[0xba] == 8 and ram.data[0xfc] == 255
    return dict(original_instructions=6, stop_pc=cpu.pc,
                first_external_call=dict(pc=0x81c, opcode=0x20, target=0xed0c),
                instructions=instructions, writes=ram.writes,
                artificial_initial_state=dict(port00=0x2f, port01=0x37, flags=cpu.UNUSED, sp=255),
                stop_registers=dict(a=cpu.a, x=cpu.x, y=cpu.y, p=cpu.p, sp=cpu.sp),
                nominal_cpu_cycles=cpu.processorCycles,
                scope='Only six original official instructions; stop before JSR KERNAL. No ROM/drive/I/O responses or decompression fabricated.')


def static_map(blob):
    from py65.devices.mpu6502 import MPU
    from py65.disassembler import Disassembler
    memory = bytearray(65536)
    first = int.from_bytes(blob[:2], 'little')
    end = first+len(blob)-2
    memory[first:end] = blob[2:]
    cpu = MPU(memory=memory)
    dis = Disassembler(cpu)
    queue, nodes, external, stops = deque([0x810]), {}, [], []
    while queue:
        pc = queue.popleft()
        if pc in nodes or not first <= pc < end:
            continue
        opcode = memory[pc]
        if cpu.instruct[opcode].__name__ == 'inst_not_implemented':
            stops.append(dict(pc=pc, reason='unsupported opcode', opcode=opcode)); continue
        length, text = dis.instruction_at(pc)
        assert pc+length <= end
        nodes[pc] = dict(pc=pc, bytes=memory[pc:pc+length].hex(' '), text=text)
        if opcode in (0x00, 0x40, 0x60): continue
        if opcode == 0x6c:
            stops.append(dict(pc=pc, reason='indirect jump', pointer=int.from_bytes(memory[pc+1:pc+3], 'little')))
            continue
        if opcode in (0x20, 0x4c):
            target = int.from_bytes(memory[pc+1:pc+3], 'little')
            if first <= target < end: queue.append(target)
            else: external.append(dict(pc=pc, kind='call' if opcode==0x20 else 'jump', target=target))
            if opcode == 0x4c: continue
        elif cpu.disassemble[opcode][1] == 'rel':
            offset = memory[pc+1]
            queue.append((pc+2+(offset if offset<128 else offset-256))&65535)
        queue.append(pc+length)
    return dict(nodes=[nodes[p] for p in sorted(nodes)], external_transfers=external,
                stops=stops, scope='Static direct-branch overapproximation only; ROM returns/hardware conditions are not executed or supplied.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BASE/'binary')
    args = parser.parse_args()
    acquisition = json.loads((BASE/'acquisition.json').read_text())
    assert acquisition['pass'] and len(acquisition['members']) == 3
    args.output.mkdir(parents=True, exist_ok=True)
    records, blobs = [], []
    for index, member in enumerate(acquisition['members']):
        disk = (ROOT/member['path']).read_bytes()
        assert len(disk) == 174848 and sha(disk) == member['sha256'] == DISK_SHAS[index]
        entries = directory(disk)
        assert len(entries) == 13 and entries[0]['type'] == 0x82
        assert all(e['type'] == 0x80 for e in entries[1:])
        assert {(e['first_track'],e['first_sector']) for e in entries} == {(18,7)}
        blob, chain = linked(disk,18,7)
        assert len(blob) == 849 and sha(blob) == BOOT_SHAS[index]
        assert blob[:14] == bytes.fromhex('01 08 0b 08 0a 00 9e 32 30 36 34 00 00 00')
        assert blob[0x810-0x801+2:0x81f-0x801+2] == SIGNATURE
        path = args.output/f'side{index+1}-boot.prg'
        path.write_bytes(blob); blobs.append(blob)
        mapping = static_map(blob)
        listing = args.output/f'side{index+1}-boot-reachable.txt'
        listing.write_text('\n'.join(f"{n['pc']:04x}  {n['bytes']:9}  {n['text']}" for n in mapping.pop('nodes'))+'\n')
        records.append(dict(side=index+1, disk_path=member['path'], disk_sha256=sha(disk),
                            bam_title_id_hex=sector(disk,18,0)[0x90:0xab].hex(),
                            directory=entries, unique_DOS_chain_count=1, boot_chain=chain,
                            boot_path=str(path.relative_to(ROOT)), boot_bytes=len(blob), boot_sha256=sha(blob),
                            load=0x801, end_exclusive=0x801+len(blob)-2, basic_SYS=2064,
                            entry=0x810, entry_signature=SIGNATURE.hex(' '),
                            bounded_CPU=bounded_entry(blob),
                            static_map=mapping, listing=str(listing.relative_to(ROOT))))
    differences = []
    for side in (1,2):
        differences.append(dict(first_side=1, other_side=side+1,
            bytes=[dict(file_offset=i, memory_address=0x801+i-2, first=a, other=b)
                   for i,(a,b) in enumerate(zip(blobs[0],blobs[side])) if a!=b]))
    result = dict(pass_=True, acquisition_sha256=sha((BASE/'acquisition.json').read_bytes()),
                  script_sha256=sha(Path(__file__).read_bytes()), py65_version=importlib.metadata.version('py65'),
                  disks=records, boot_differences=differences,
                  DOS_technical_note_found=False,
                  note_scope='The only distinct DOS chain on each disk is its boot PRG; no separate DOS author note is present. No claim about hidden raw sectors or external author notes.',
                  scope='Original current three-disk DOS extraction, six instructions per boot and bounded static listing; no loader/drive/effect execution.')
    result['pass'] = result.pop('pass_')
    (args.output/'boot-proof.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(pass_=True, disks=len(records), SYS=2064, entry=0x810,
                         stop_before_ROM_call=0x81c, unique_DOS_files_per_disk=1),indent=2))


if __name__ == '__main__':
    main()
