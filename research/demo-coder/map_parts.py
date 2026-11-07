#!/usr/bin/env python3
"""Bounded static map of unpacked Demo Coder entry and IRQ candidates.

Only the actual first $e000 handoff and exact repeated wrapper prologues seed
disassembly. Direct calls/branches and literal IRQ-vector installations are
followed within that file. No data-reference scanning becomes execution proof;
indirect jumps, self-modification and cross-file state remain explicit limits.
"""
import argparse
from collections import Counter, deque
import json
from pathlib import Path
import sys

from inspect_boot import ROOT, sha
sys.path.insert(0, str(ROOT / 'research/next-round'))
from unpack_files import DaliCpu
from py65.disassembler import Disassembler

PROLOGUE = bytes.fromhex('a9 f9 cd 12 d0 d0 fb a9 00 8d f6 01 8d f7 01 78')


def map_file(entry, payload):
    first, end = entry['target'], entry['output_end']
    memory = bytearray(65536)
    memory[first:end] = payload
    cpu = DaliCpu(memory=memory)
    dis = Disassembler(cpu)
    seeds = [first + i for i in range(len(payload)) if payload.startswith(PROLOGUE, i)]
    if entry['file'] == 0:
        seeds.append(0xe000)
    queue, nodes, external, vectors, stopped = deque(seeds), {}, [], [], []
    while queue:
        pc = queue.popleft()
        if pc in nodes or not first <= pc < end:
            continue
        opcode = memory[pc]
        if cpu.instruct[opcode].__name__ == 'inst_not_implemented':
            stopped.append(dict(pc=pc, reason='unsupported opcode', opcode=opcode))
            continue
        length, text = dis.instruction_at(pc)
        if pc + length > end:
            stopped.append(dict(pc=pc, reason='instruction extends outside image'))
            continue
        nodes[pc] = dict(pc=pc, bytes=memory[pc:pc+length].hex(' '), text=text)
        # Literal LDA/STA vector pair: both complete instructions must appear
        # in this original file. Dynamic table-derived vectors are not guessed.
        block = memory[pc:pc+10]
        if (len(block) == 10 and block[0] == block[5] == 0xa9
                and block[2] == block[7] == 0x8d
                and block[3:5] in (b'\xfe\xff', b'\xfa\xff')
                and block[8:10] == bytes([block[3]+1, 255])):
            target = block[1] + 256*block[6]
            vectors.append(dict(pc=pc, vector=block[3]+0xff00, target=target))
            if first <= target < end:
                queue.append(target)
        if opcode in (0x00, 0x40, 0x60):
            continue
        if opcode == 0x6c:
            stopped.append(dict(pc=pc, reason='indirect jump', pointer=memory[pc+1]+256*memory[pc+2]))
            continue
        if opcode in (0x20, 0x4c):
            target = memory[pc+1]+256*memory[pc+2]
            if first <= target < end:
                queue.append(target)
            else:
                external.append(dict(pc=pc, kind='call' if opcode == 0x20 else 'jump', target=target))
            if opcode == 0x4c:
                continue
        elif cpu.disassemble[opcode][1] == 'rel':
            offset = memory[pc+1]
            target = (pc+2+(offset if offset < 128 else offset-256)) & 65535
            if first <= target < end:
                queue.append(target)
            else:
                external.append(dict(pc=pc, kind='branch', target=target))
        queue.append(pc+length)
    stores = []
    for pc in sorted(nodes):
        if memory[pc] in (0x8d, 0x8e, 0x8c):
            address = memory[pc+1]+256*memory[pc+2]
            if 0xd000 <= address < 0xe000:
                stores.append(dict(pc=pc, address=address, opcode=memory[pc]))
    return dict(file=entry['file'], first=first, end_exclusive=end,
                entry_seeds=seeds, original_bytes_sha256=sha(payload),
                static_nodes=len(nodes), vector_installations=vectors,
                direct_external_transfers=external, stops=stopped,
                literal_io_stores=stores,
                literal_io_store_counts=dict(sorted(Counter(s['address'] for s in stores).items())),
                nodes=[nodes[p] for p in sorted(nodes)])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, default=ROOT / 'build/research/demo-coder/streams/unpacked-index.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/research/demo-coder/static-map')
    args = parser.parse_args()
    index = json.loads(args.index.read_text())
    assert index['pass'] and len(index['files']) == 68
    args.output.mkdir(parents=True, exist_ok=True)
    records = []
    for entry in index['files']:
        blob = (ROOT / entry['output_path']).read_bytes()
        assert int.from_bytes(blob[:2], 'little') == entry['target']
        assert len(blob)-2 == entry['output_bytes'] and sha(blob[2:]) == entry['output_sha256']
        record = map_file(entry, blob[2:])
        if not record['entry_seeds']:
            continue
        listing = args.output / f"{entry['file']:03d}-{entry['target']:04x}-reachable.txt"
        listing.write_text('\n'.join(f"{n['pc']:04x}  {n['bytes']:9}  {n['text']}" for n in record.pop('nodes'))+'\n')
        record['listing'] = str(listing.relative_to(ROOT))
        records.append(record)
    receipt = dict(pass_=True, input_index_sha256=sha(args.index.read_bytes()),
                   script_sha256=sha(Path(__file__).read_bytes()),
                   exact_wrapper_prologue=PROLOGUE.hex(' '), files=records,
                   scope='Static branch overapproximation within validated full images; literal IRQ targets only; no effect execution, native timing, visual identity, indirect-jump or SMC resolution.')
    receipt['pass'] = receipt.pop('pass_')
    (args.output / 'part-map.json').write_text(json.dumps(receipt, indent=2)+'\n')
    print(f"Mapped {len(records)} candidate images; {sum(r['static_nodes'] for r in records)} branch-reachable instructions")


if __name__ == '__main__':
    main()
