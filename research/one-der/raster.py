#!/usr/bin/env python3
"""Replay one retained One-Der triangle-to-buffer frame with scalar gradients."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/one-der'
PINS = {
    'research/one-der/analyze.py': '8b46d13c021f2d691bacfd87c2194e77450459b8d5c1b3ea24da0e71ed6338f4',
    'build/research/one-der/analysis/accepted-02/one-der-proof.json': 'e5eaaa1c454462e84de564b0984b8d587a37993b2b42457cc504bff0925f1532',
    'research/one-der/gradient.py': '40f978f7f6b20cb0ae8c4dbd4fac18808513c38e5c5ab7a28890b1e33b4eca1a',
    'build/research/one-der/gradient-analysis/accepted-02/gradient-proof.json': '85485febf43fcf9263b9508c823552fcb36a1443f363085e6a15214adb031071',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def source_guards(source, before, after):
    # The original NMOS SHY test selects the 10-byte edge cells, not fallback STY.
    assert source[0x2207:0x221f] == bytes.fromhex('a0eba256a9aa8d003e9d003e9c003eeaeabd003ec92bf003')
    assert source[0x23bc:0x23c7] == bytes.fromhex('8d003f8a6503aa986502a8')
    assert source[0x23d8:0x23e2] == bytes.fromhex('e502b0036503c89c003e')
    assert source[0x23e2:0x23ec] == bytes.fromhex('e503c8b0fb65029c003e')
    assert source[0xd6e:0xd7e] == bytes.fromhex('00000306030603060603060306030000')
    assert source[0xd28:0xd34] == bytes.fromhex('a200a54a4901854ad01ea9ff')
    assert source[0xe56:0xe76] == bytes.fromhex('a200a000a5238d940e8dbd108da00f8dcf1106222623a54af0034c9a10200010')
    # The last JSR is patched during initialization; retain the actual generators.
    assert before[0xe68:0xe76] == after[0xe68:0xe76] == bytes.fromhex('06222623a54af0034c9a1020804a')
    assert before[0x109a:0x109f] == after[0x109a:0x109f] == bytes.fromhex('a90020a14c')
    for memory in (before, after):
        for row in range(128):
            start = 0x4500 + 11 * row
            assert memory[start:start+11] == b'\x8d' + (0x3f00+row).to_bytes(2, 'little') + bytes.fromhex('8a6503aa986502a8')
        for start, first, second in ((0x4a80, 0x12cf, 0x1360), (0x4ca1, 0x13f1, 0x1482)):
            for k in range(32):
                operand = 1 if k % 2 == 0 else 4
                expected = b''.join(b'\x8d' + a.to_bytes(2, 'little') for a in
                                    (0x3f80+k, first+9*(k//2)+operand, second+9*(k//2)+operand))
                expected += bytes.fromhex('8a6522aa986523a8')
                assert memory[start+17*k:start+17*(k+1)] == expected
            assert memory[start+17*32] == 0x60
    return dict(NMOS_SHY_test=0x2207, edge_templates=[0x23d8, 0x23e2],
                intensity_template=0x23bc, intensity_cells=128,
                offset_generators=[0x4a80, 0x4ca1], offset_cells_each=32,
                both_offset_entries_A_zero=True, no_CPU_execution=True)


def edge(a, b, left, right, intensity, touched, include_endpoint=True):
    """Original in-range integer recurrences; construction includes both endpoints."""
    x0, y0, i0 = a
    x1, y1, i1 = b
    if y0 == y1:
        return dict(horizontal=True, stores=0)
    if y1 > y0:
        side, side_name = left, 'left'
        h, dx, xs, ys = y1-y0, x1-x0, x0, y0
        delta = abs(i1-i0)*256//h
        q = i0*256
        for k in range(h+int(include_endpoint)):
            assert 0 <= q//256 <= 255
            intensity[ys+k] = q//256
            touched['intensity'].add(ys+k)
            q += delta if i1 >= i0 else -delta
    else:
        side, side_name = right, 'right'
        h, dx, xs, ys = y0-y1, x0-x1, x1, y1
    step = 1 if dx >= 0 else -1
    if dx >= 0:
        if h >= dx:
            d, t, error, x, steep = dx+1, h+2, h+2, xs, True
        else:
            d, t, error, x, steep = dx, h+1, dx, xs-1, False
    else:
        d = -dx+1
        if h >= d:
            t, error, x, steep = h+2, h+2, xs, True
        else:
            d, t, error, x, steep = d+1, h+1, 0, xs+1, False
    for k in range(h+int(include_endpoint)):
        if steep:
            error -= d
            if error < 0:
                error += t
                x += step
        else:
            while True:
                error -= t
                x += step
                if error < 0:
                    break
            error += d
        assert 0 <= ys+k < 128 and 0 <= x < 64
        side[ys+k] = x & 63  # SHY abs,X with operand page $3E and no page crossing.
        touched[side_name].add(ys+k)
    return dict(horizontal=False, side=side_name, height=h, dx=dx,
                kind='steep' if steep else 'shallow', stores=h+int(include_endpoint))


def offsets(lo, hi):
    """Preserve the generated ADC chain's carry, including wrap back into fraction."""
    dl, dh = (lo << 1) & 255, ((hi << 1) | (lo >> 7)) & 255
    fraction = integer = a = 0
    carry = hi >> 7
    result = []
    for _ in range(32):
        result.append(a)
        value = fraction + dl + carry
        fraction, carry = value & 255, value >> 8
        value = integer + dh + carry
        integer, carry = value & 255, value >> 8
        a = integer
    return result


def raster_frame(before, entries, gradient=None):
    """One bounded B-buffer replay; gradient=None is the retained conditional check."""
    left, right, intensity = [list(before[a:a+128]) for a in (0x3e00, 0x3e80, 0x3f00)]
    touched = {name: set() for name in ('left', 'right', 'intensity')}
    target = bytearray([255]*2048)
    target_writes = set()
    covered_bits = [0]*2048
    triangles = []
    assert len(entries) == 4
    for index, entry in enumerate(entries):
        vertices = entry['vertex_triples']
        assert len(vertices) == 3 and all(len(v) == 3 and 0 <= v[0] < 64 and 0 <= v[1] < 128 and 0 <= v[2] < 256 for v in vertices)
        this_triangle = {name: set() for name in touched}
        edge_rows = [edge(vertices[j], vertices[(j+1)%3], left, right, intensity, this_triangle) for j in range(3)]
        result = entry['result_20_to_27'] if gradient is None else gradient(vertices)['result_20_to_27']
        assert result == entry['result_20_to_27']
        lo, hi = result[2:4]
        column = offsets(lo, hi)
        y0, y1 = min(v[1] for v in vertices), max(v[1] for v in vertices)
        assert all(set(range(y0, y1)) <= this_triangle[name] for name in this_triangle)
        for name in touched:
            touched[name].update(this_triangle[name])
        spans = byte_visits = 0
        for y in range(y0, y1):
            l, r = left[y], right[y]
            if r < l:
                continue
            spans += 1
            origin = (intensity[y] - (hi if l & 1 else 0) - column[l//2]) & 255
            lm, rm = (0, 192, 240, 252)[l & 3], (63, 15, 3, 0)[r & 3]
            for c in range(l//4, r//4+1):
                ta, tb = (0x3000, 0x3200) if y % 2 == 0 else (0x3400, 0x3600)
                color = before[ta+origin+column[2*c]] | before[tb+origin+column[2*c+1]]
                mask = (lm if c == l//4 else 0) | (rm if c == r//4 else 0)
                offset = 128*c+y
                target[offset] = (target[offset] & mask) | (color & (~mask & 255))
                target_writes.add(offset)
                covered_bits[offset] |= ~mask & 255
                byte_visits += 1
        triangles.append(dict(index=index, vertices=vertices, gradient_fraction=lo,
                              gradient_integer_byte=hi, edge_rows=edge_rows,
                              raster_Y_half_open=[y0,y1], nonempty_spans=spans,
                              software_byte_visits=byte_visits, horizontal_offsets=column))
    return dict(target=bytes(target), workspace=bytes(left+right+intensity), column=bytes(column),
                left=left, right=right, intensity=intensity, touched=touched,
                target_writes=target_writes, covered_bits=covered_bits, triangles=triangles)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE/'raster-analysis').resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    for name, pin in PINS.items():
        assert sha((ROOT/name).read_bytes()) == pin, name
    accepted = json.loads((BASE/'analysis/accepted-02/one-der-proof.json').read_text())
    captures = {r['stem']: r for r in accepted['captures']}
    memories, inputs = {}, [artifact(ROOT/p) for p in PINS]
    for stem in ('part2', 'later-frame', 'draw-end'):
        record = captures[stem]['ram']
        path = ROOT/record['path']
        raw = path.read_bytes()
        assert len(raw) == record['bytes'] == 65536 and sha(raw) == record['sha256']
        memories[stem] = raw
        inputs.append(artifact(path))
    source, before, after = (memories[s] for s in ('part2', 'later-frame', 'draw-end'))
    guards = source_guards(source, before, after)
    assert before[0x4a] == 0 and after[0x4a] == 1
    assert before[0x9d3:0x9d6] == after[0x9d3:0x9d6] == bytes.fromhex('201d1b')
    assert before[0x3000:0x3800] == after[0x3000:0x3800]
    spec = importlib.util.spec_from_file_location('one_der_raster_gradient', ROOT/'research/one-der/gradient.py')
    gradient_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gradient_module)
    gradient_proof = json.loads((BASE/'gradient-analysis/accepted-02/gradient-proof.json').read_text())
    assert gradient_proof['pass_'] and len(gradient_proof['samples']) == 4
    entries = accepted['gradient_trace']['triangles']
    gradient_checks = []
    for index, entry in enumerate(entries):
        model = gradient_module.gradient(entry['vertex_triples'])
        native = gradient_proof['samples'][index]
        assert native['vertex_triples'] == entry['vertex_triples']
        assert model['result_20_to_27'] == native['native_output_20_to_27'] == entry['result_20_to_27']
        assert model['carry'] == native['native_carry']
        gradient_checks.append(dict(index=index, all_eight_native_bytes_equal=True,
                                    native_carry_equal=True, output_20_to_27=model['result_20_to_27']))
    conditional = raster_frame(before, entries)
    independent = raster_frame(before, entries, gradient_module.gradient)
    assert conditional == independent
    target, workspace, column = (independent[k] for k in ('target', 'workspace', 'column'))
    touched, target_writes, covered_bits, triangles = (independent[k] for k in ('touched', 'target_writes', 'covered_bits', 'triangles'))
    left, right, intensity = (independent[k] for k in ('left', 'right', 'intensity'))
    assert workspace == after[0x3e00:0x3f80]
    assert bytes(column) == after[0x3f80:0x3fa0]
    assert target == after[0x2800:0x3000]
    assert all(target[i] == 255 for i in range(2048) if i not in target_writes)
    # A rejected source interpretation: omitting each edge's terminal-row store.
    wrong_arrays = [list(before[a:a+128]) for a in (0x3e00, 0x3e80, 0x3f00)]
    wrong_touched = {name: set() for name in touched}
    for entry in entries:
        vertices = entry['vertex_triples']
        for j in range(3):
            edge(vertices[j], vertices[(j+1)%3], *wrong_arrays, wrong_touched, include_endpoint=False)
    wrong_workspace = bytes(sum(wrong_arrays, []))
    wrong_differences = [dict(address=0x3e00+i, modeled=a, native=b)
                         for i, (a, b) in enumerate(zip(wrong_workspace, after[0x3e00:0x3f80])) if a != b]
    assert len(wrong_differences) == 4
    array_checks = {}
    for name, actual, incoming, output in (
            ('left', after[0x3e00:0x3e80], before[0x3e00:0x3e80], left),
            ('right', after[0x3e80:0x3f00], before[0x3e80:0x3f00], right),
            ('intensity', after[0x3f00:0x3f80], before[0x3f00:0x3f80], intensity)):
        seeded = set(range(128))-touched[name]
        assert all(output[i] == incoming[i] == actual[i] for i in seeded)
        array_checks[name] = dict(compared_bytes=128, computed_written_bytes=len(touched[name]),
                                 preserved_seed_bytes=len(seeded), written_rows=sorted(touched[name]))
    out.mkdir(parents=True)
    outputs = []
    for name, raw in (('buffer-2800.bin', bytes(target)), ('workspace-3e00.bin', workspace+bytes(column)),
                      ('raster.checked.py', Path(__file__).read_bytes())):
        (out/name).write_bytes(raw)
        outputs.append(dict(name=name, bytes=len(raw), sha256=sha(raw)))
    proof = dict(pass_=True, scope='One source-bound B-buffer frame from four captured accepted triangle inputs through scalar gradients, edges and spans; no CPU emulation, independent rotation/culling or scanout claim',
                 producer=artifact(Path(__file__)), inputs=inputs, capture_acceptance_reused=True,
                 source_guards=guards, triangle_order_from='accepted-02 gradient_trace',
                 gradient_checks=gradient_checks,
                 conditional_and_independent_passes_equal=True,
                 both_passes_equal_native=dict(target_bytes=2048, edge_and_intensity_bytes=384, last_offset_bytes=32),
                 endpoint_control=dict(variant='h stores instead of original h+1 endpoint-inclusive construction',
                                       workspace_mismatches=wrong_differences, rejected=True,
                                       scope='Same inputs/initial workspace; edge/intensity workspace only.'),
                 triangles=triangles, target=dict(base=0x2800, bytes=2048, all_bytes_equal=True,
                     sha256=sha(target), clear_value=255, written_unique_bytes=len(target_writes),
                     clear_only_bytes=2048-len(target_writes), covered_unique_bits=sum(x.bit_count() for x in covered_bits),
                     remaining_clear_bits=16384-sum(x.bit_count() for x in covered_bits)),
                 workspace=dict(all384_bytes_equal=True, arrays=array_checks,
                                last32_horizontal_offsets_equal=True, offset_sha256=sha(bytes(column))),
                 limits=['Captured triangle acceptance/order and XYZ/intensity triples are inputs; rotation, intensity origin and culling are not independently reproduced.',
                         'The first pass uses captured gradients; the second calls pinned gradient.py from triangle triples and compares all eight native gradient bytes and carry before rasterization.',
                         'In-range vertices, edge samples and intensity values are guarded; this is not a proof for wrapping, clipped or arbitrary triangles.',
                         'Untouched workspace cells are seeded from the incoming capture and separately counted.',
                         'The target software buffer starts cleared to FF; displayed selection, palette, VIC fetch chronology and FPS are separate.',
                         'Both source offset entries start A=0; an earlier provisional bank-A A=gradient-high interpretation was incorrect. Only B-buffer output is compared.'], outputs=outputs)
    raw = (json.dumps(proof, indent=2)+'\n').encode()
    (out/'raster-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True, proof_bytes=len(raw), proof_sha256=sha(raw),
                          target=proof['target'], gradient_calls=len(gradient_checks),
                          workspace_matching_bytes=384, last_offset_matching_bytes=32,
                          rejected_endpoint_workspace_mismatches=len(wrong_differences)), indent=2))


if __name__ == '__main__':
    main()
