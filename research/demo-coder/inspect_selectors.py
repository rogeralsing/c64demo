#!/usr/bin/env python3
"""Check one source-linked raster-selector family in complete stream 46.

This is a finite byte/table proof, not execution of the raster effect. In
particular, nominal CPU costs exclude VIC DMA, IRQ entry, and write phase.
"""
import argparse
from collections import Counter
import json
from pathlib import Path

from inspect_boot import ROOT, sha

IMAGE_SHA = '3be2386eeb9c9f0d3bb274eab04fd7aa48f7df3b3a10199df3d49cecaabec31c'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--index', type=Path, default=ROOT / 'build/research/demo-coder/streams/unpacked-index.json')
    parser.add_argument('--output', type=Path, default=ROOT / 'build/research/demo-coder/selector-analysis')
    args = parser.parse_args()
    index = json.loads(args.index.read_text())
    entry = index['files'][46]
    blob = (ROOT / entry['output_path']).read_bytes()
    assert blob[:2] == b'\x00\x20' and sha(blob[2:]) == entry['output_sha256'] == IMAGE_SHA
    memory = bytearray(65536)
    memory[0x2000:0xc001] = blob[2:]
    # These actual consumers load the low/high tables and patch JMP $68b9.
    # $6858 clamps the table index to49 before the initial selection.
    assert memory[0x6858:0x6867] == bytes.fromhex('c9 31 90 02 a9 31 a8 a5 0b 8d 05 67 8d ae 68')
    consumer = bytes.fromhex('b9 64 bb 8d ba 68 b9 96 bb 8d bb 68')
    assert memory[0x6867:0x6873] == consumer
    assert memory[0x692c:0x6938] == consumer
    assert memory[0x68b9:0x68bc] == bytes.fromhex('4c b9 68')
    assert memory[0x6332:0x6335] == bytes.fromhex('4c aa 68')
    assert memory[0x68aa:0x68b9] == bytes.fromhex('20 3a 60 a9 00 85 10 ea ea ea 24 ea ae 12 d0')
    targets = [memory[0xbb64+i]+256*memory[0xbb96+i] for i in range(50)]
    assert targets[0] == 0x69c1
    records, all_values = [], Counter()
    for index_value, start in enumerate(targets):
        count = index_value+1
        if index_value:
            assert start == targets[index_value-1]+15*index_value+3
        values = []
        for row in range(count):
            pc = start+15*row
            cell = memory[pc:pc+15]
            assert cell[:7] == bytes.fromhex('bd 00 b8 8d 11 d0 a9')
            assert cell[8:] == bytes.fromhex('8d 00 dd 8d 18 d0 e8')
            values.append(cell[7])
        endpoint = start+15*count
        assert memory[endpoint:endpoint+3] == bytes.fromhex('4c bc 68')
        all_values.update(values)
        records.append(dict(index=index_value, first=start, cells=count,
                            end_exclusive=endpoint+3, selectors=values,
                            nominal_cpu_cycles=20*count+3))
    assert records[-1]['end_exclusive'] == 0xb50c
    assert sum(r['cells'] for r in records) == 1275
    assert set(all_values) == {0xfb, 0x72, 0x70, 0xf8}
    assert memory[0xb800:0xb900] == bytes(0x70 | ((i+1)&7) for i in range(256))
    assert memory[0xb900:0xba00] == bytes(0x70 | ((i+2)&7) for i in range(256))
    # This reachable coroutine removes ECM from eight table entries in each
    # of the two pages. Its runtime phase is not interpreted by this script.
    assert memory[0x64ef:0x6505] == bytes.fromhex(
        'a0 07 bd 00 b9 29 3f 9d 00 b9 bd 00 b8 29 3f 9d 00 b8 ca 88 10 ec')
    decoded_selectors = []
    for value in sorted(all_values):
        bank = ((~value)&3)*0x4000
        decoded_selectors.append(dict(value=value, static_cells=all_values[value],
                                      vic_bank=bank,
                                      screen=bank+((value>>4)&15)*1024,
                                      bitmap_base_if_BMM=bank+(0x2000 if value&8 else 0)))
    report = dict(pass_=True, stream=46, image_sha256=IMAGE_SHA,
                  index_sha256=sha(args.index.read_bytes()),
                  script_sha256=sha(Path(__file__).read_bytes()),
                  wrapper_entry=0x6000, initial_irq=0x6238,
                  raster_irq=0x62ea, dispatch_jump=0x68b9,
                  table_low=0xbb64, table_high=0xbb96, table_entries=50,
                  raster_cells=1275, family_first=0x69c1, family_end=0xb50c,
                  family_bytes=0xb50c-0x69c1, nominal_cell_cycles=20,
                  cell_instructions=['LDA $B800,X: 4', 'STA $D011: 4', 'LDA #selector: 2',
                                     'STA $DD00: 4', 'STA $D018: 4', 'INX: 2'],
                  literal_initial_d011_tables=dict(first=0xb800, end_exclusive=0xba00,
                                                  high_bits=0x70, periods=8),
                  table_ecm_clear_coroutine=0x64ef,
                  selectors=decoded_selectors, cases=records,
                  scope='Complete original bytes and literal consumers; static finite checks only. No native execution, timing under DMA, physical color, row-counter or visual-effect identity proof.')
    report['pass'] = report.pop('pass_')
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'selector-proof.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f"50 original routines / 1,275 cells / {report['family_bytes']} bytes: exact")


if __name__ == '__main__':
    main()
