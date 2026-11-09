#!/usr/bin/env python3
"""Check retained Next Round RAM/snapshot identity without executing emulation."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/next-round-timing'
CASE = BASE / 'native-01'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    reader_path = ROOT / 'research/quondam/snapshot_state.py'
    assert sha(reader_path.read_bytes()) == 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a'
    spec = importlib.util.spec_from_file_location('next_round_snapshot', reader_path)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    pin = json.loads((BASE / 'native-01-pin.json').read_text())
    rows = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
            for p in sorted(CASE.iterdir()) if p.is_file()]
    assert rows == pin['files']
    assert sha(json.dumps(rows, sort_keys=True, separators=(',', ':')).encode()) == pin['sha256']
    events = [json.loads(line) for line in (CASE / 'events.jsonl').read_text().splitlines()]
    responses = {row['id']: row for row in events if row['kind'] == 'response' and row['id']}
    captures = []
    for stem, identifier, pc in [('entry', 'entry-registers', 0xe000),
                                 ('loop', 'loop-registers', 0x0600),
                                 ('end', 'scene-end-registers', 0x5d44)]:
        response = responses[identifier]['response']
        match = re.search(r'^\.;([0-9a-f]+) ((?:[0-9a-f]{2} ){6})([01]{8})\s+(\d+)\s+(\d+)\s+(\d+)$', response, re.M)
        assert match, response
        values = [int(match[1], 16), *[int(v, 16) for v in match[2].split()],
                  int(match[3], 2), *[int(match[i]) for i in (4, 5, 6)]]
        regs = dict(zip(('pc', 'a', 'x', 'y', 'sp', 'port00', 'port01', 'flags', 'line', 'cycle', 'clock'), values))
        ram_path, snapshot_path = CASE / f'{stem}-ram.bin', CASE / f'{stem}.vsf'
        ram = ram_path.read_bytes()
        mem = reader.module_payload(snapshot_path, 'C64MEM')
        cpu = reader.module_payload(snapshot_path, 'MAINCPU')
        state = reader.read_snapshot(snapshot_path)
        assert len(ram) == 65536 and ram == mem[4:65540]
        assert (mem[1], mem[0]) == (regs['port00'], regs['port01'])
        expected = dict(clock=int.from_bytes(cpu[:8], 'little'), a=cpu[8], x=cpu[9], y=cpu[10],
                        sp=cpu[11], pc=int.from_bytes(cpu[12:14], 'little'), flags=cpu[14])
        assert all(regs[key] == value for key, value in expected.items()) and regs['pc'] == pc
        assert (state['vicii']['raster_line'], state['vicii']['raster_cycle']) == (regs['line'], regs['cycle'])
        assert (regs['clock'] // 63 % 312, regs['clock'] % 63) == (regs['line'], regs['cycle'])
        captures.append(dict(stem=stem, registers=regs, ram=artifact(ram_path), snapshot=artifact(snapshot_path),
                             all_65536_RAM_bytes_CPU_ports_registers_clock_beam_equal=True))
    entry = (CASE / 'entry-ram.bin').read_bytes()
    payloads = []
    for name in ('006-2000.prg', '007-6cbd.prg', '008-e000.prg'):
        path = ROOT / 'build/research/next-round/boot-analysis/depacked-round3' / name
        raw = path.read_bytes()
        address = int.from_bytes(raw[:2], 'little')
        assert entry[address:address + len(raw) - 2] == raw[2:]
        payloads.append(dict(input=artifact(path), load_address=address, matching_bytes=len(raw) - 2))
    disk = ROOT / 'build/research/next-round/release/round3.d64'
    assert sha(disk.read_bytes()) == 'e1991a76fa7968743e81efd7fd46bd1c4f81cc831512f02b33fb8eef563a4179'
    result = dict(pass_=True, scope='Read-only RAM/snapshot/payload identity; no scanout or wall-time FPS proof',
                  producer=artifact(Path(__file__)), snapshot_reader=artifact(reader_path),
                  pin=artifact(BASE / 'native-01-pin.json'), case_sha256=pin['sha256'],
                  disk=artifact(disk), paired_captures=captures, original_payloads=payloads,
                  total_original_payload_bytes=sum(row['matching_bytes'] for row in payloads))
    with args.output.open('x') as stream:
        stream.write(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps(dict(pass_=True, paired_captures=len(captures), original_payload_bytes=result['total_original_payload_bytes'],
                          output=str(args.output), sha256=sha(args.output.read_bytes()))))


if __name__ == '__main__':
    main()
