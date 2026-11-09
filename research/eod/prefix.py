#!/usr/bin/env python3
"""Reconstruct EOD's common prefix output from independently predicted markers."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/eod'
PINS = {
    'build/research/eod/frame-analysis/accepted-01/frame-proof.json': 'ef77c7a2d93d110ce5caa8c60c313d8d7313325ba51e9d355cff9e855535bb50',
    'build/research/eod/contour-analysis/accepted-01/contour-proof.json': 'b8396182b088637ecb91aaba9f2bfd257b99efe7289b254dcd0dba612c3e5b98',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def descriptor_groups(memory):
    """Read only the fixed TXA / EOR-STA descriptors, validating their layout."""
    assert memory[0x1a73:0x1a7d] == bytes.fromhex('a2004c00d8a9004c00c4')
    assert memory[0x125c:0x1262] == bytes.fromhex('4d00788d0070')
    pc, groups = 0xd800, []
    for group in range(32):
        assert memory[pc] == 0x8a  # Entry sets X=0; TXA resets the running XOR.
        pc += 1
        plane, column = divmod(group, 16)
        pairs = []
        while pc+6 < 65536 and memory[pc] == 0x4d:
            assert memory[pc+3] == 0x8d
            marker = int.from_bytes(memory[pc+1:pc+3], 'little')
            output = int.from_bytes(memory[pc+4:pc+6], 'little')
            row = marker-(0x7800+1024*plane+64*column)
            assert 0 <= row < 64
            assert output == 0x7000+128*column+2*row+plane
            if pairs:
                assert row == pairs[-1]['row']+1
            pairs.append(dict(marker=marker, output=output, row=row))
            pc += 6
        assert pairs
        groups.append(dict(plane=plane, column=column, pairs=pairs))
    assert memory[pc] == 0x60
    assert pc == 0xfecc and sum(len(g['pairs']) for g in groups) == 1650
    assert len({p['marker'] for g in groups for p in g['pairs']}) == 1650
    assert len({p['output'] for g in groups for p in g['pairs']}) == 1650
    clear = 0xc400
    for group in groups:
        for pair in group['pairs']:
            assert memory[clear:clear+3] == b'\x8d'+pair['marker'].to_bytes(2, 'little')
            clear += 3
    assert memory[clear] == 0x60
    return groups, dict(prefix_code=[0xd800, pc+1], clear_code=[0xc400, clear+1],
        source='Pinned incoming generated descriptors, checked against fixed original templates and independent column/plane address formulas.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE/'prefix-analysis').resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    for name, expected in PINS.items():
        assert sha((ROOT/name).read_bytes()) == expected, name
    frame = json.loads((BASE/'frame-analysis/accepted-01/frame-proof.json').read_text())
    contour_path = BASE/'contour-analysis/accepted-01/contour-proof.json'
    contour = json.loads(contour_path.read_text())
    assert frame['pass_'] and contour['pass_']
    rows = {r['stem']: r for r in frame['captures']}
    states, inputs = {}, []
    for stem in ('prefix-before', 'prefix-filled', 'prefix-cleared'):
        record = rows[stem]['ram']
        path = ROOT/record['path']
        raw = path.read_bytes()
        assert len(raw) == record['bytes'] == 65536 and sha(raw) == record['sha256']
        states[stem] = raw
        inputs.append(artifact(path))
    marker_path = contour_path.parent/'predicted-frame-marker-7800.bin'
    marker_record = next(r for r in contour['outputs'] if r['name'] == marker_path.name)
    marker = marker_path.read_bytes()
    assert len(marker) == marker_record['bytes'] == 2048 and sha(marker) == marker_record['sha256']
    before, filled, cleared = (states[s] for s in ('prefix-before', 'prefix-filled', 'prefix-cleared'))
    assert marker == before[0x7800:0x8000]  # Validation only: marker input is the independent contour output.
    groups, context = descriptor_groups(before)
    output, reset = bytearray(before[0x7000:0x7800]), bytearray(marker)
    for group in groups:
        accumulator = 0
        for pair in group['pairs']:
            accumulator ^= marker[pair['marker']-0x7800]
            output[pair['output']-0x7000] = accumulator
            reset[pair['marker']-0x7800] = 0
    assert output == filled[0x7000:0x7800] == cleared[0x7000:0x7800]
    assert marker == filled[0x7800:0x8000]
    assert reset == cleared[0x7800:0x8000]
    all_sources, all_targets = set(), set()
    for plane in range(2):
        for column in range(16):
            for row in range(64):
                all_sources.add(1024*plane+64*column+row)
                all_targets.add(128*column+2*row+plane)
    assert all_sources == all_targets == set(range(2048))
    out.mkdir(parents=True)
    outputs = []
    for name, raw in (('predicted-output-7000.bin', bytes(output)),
                      ('predicted-cleared-markers.bin', bytes(reset)),
                      ('prefix.checked.py', Path(__file__).read_bytes())):
        (out/name).write_bytes(raw)
        outputs.append(dict(name=name, bytes=len(raw), sha256=sha(raw)))
    proof = dict(pass_=True, scope='One original software output buffer and common marker reset from the independent whole-frame contour marker prediction; no VIC scanout or general animation acceptance',
        producer=artifact(Path(__file__)), inputs=[artifact(ROOT/p) for p in PINS]+inputs+[artifact(marker_path)],
        generated_descriptor_context=context,
        groups=[dict(plane=g['plane'], column=g['column'], row_start=g['pairs'][0]['row'],
                     row_end_exclusive=g['pairs'][-1]['row']+1) for g in groups],
        address_contract=dict(marker='7800+1024*plane+64*column+row',
                              output='7000+128*column+2*row+plane',
                              bounds='plane0..1,column0..15,row0..63; 2048 source/output offsets are bijective before cropping'),
        output_comparison=dict(bytes=2048, computed_bytes=1650, preserved_incoming_bytes=398,
                               all_equal=True, sha256=sha(output)),
        marker_reset_comparison=dict(bytes=2048, zero_stores=1650, preserved_incoming_bytes=398,
                                     all_equal=True, retained_nonzero_bytes=sum(bool(x) for x in reset), sha256=sha(reset)),
        observed_elapsed_cycles=dict(prefix=rows['prefix-filled']['registers']['clock']-rows['prefix-before']['registers']['clock'],
            clear=rows['prefix-cleared']['registers']['clock']-rows['prefix-filled']['registers']['clock']),
        limits=['The generated crop plan is an incoming input, not independently reconstructed geometry/bounds-generation code.',
            'Old output supplies the398 unwritten bytes; completed native output enters comparisons only.',
            'Only the active1650 marker cells are cleared; nonzero bytes outside the crop are retained, not silently normalized.',
            'Prepared LUTs and previous state are declared by the independent contour/geometry chain; no current-frame stage targets seed that chain.',
            'Fixed descriptors are validated as data; no CPU interpreter, native process, subprocess or build runs.',
            'Software pixels/markers do not establish actual VIC fetches, palette mapping, publication, whole-scene FPS or savings.'], outputs=outputs)
    raw = (json.dumps(proof, indent=2)+'\n').encode()
    (out/'prefix-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True, receipt_bytes=len(raw), receipt_sha256=sha(raw), output_bytes=2048)))


if __name__ == '__main__':
    main()
