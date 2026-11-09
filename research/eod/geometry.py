#!/usr/bin/env python3
"""Passive scalar reconstruction of original EOD stages before $5B56."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/eod'
EXTRACT = BASE/'file-analysis/accepted-03/EdgeOfDisgrace_1a'
PINS = {
    'build/research/eod/file-analysis/accepted-03/file-proof.json': 'fb8e819f854fd500acb34ea023508a9966f95914f38e1c6de0db77e3f2381db9',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-051.decoded.prg': 'e4899712681147b233a960d675aab369feebac4ba149073f1051d45f78b5312c',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-052.decoded.prg': '3adc5e1b6990cf41b3d93954de9d92bd3da62b4b562fc636cbd827cf94d67c04',
    'build/research/eod/controller-analysis/accepted-01/controller-proof.json': '256828263de51e95cb374db0c177e146e948752f61cc6651ff5371fe956532f6',
    'build/research/eod/shader-analysis/accepted-03/shader-proof.json': '275cd3c59f5056b60ca7c63f66b931e504b6f44eb66772d0f02911d97ebd085f',
    'build/research/eod/frame-analysis/accepted-01/frame-proof.json': 'ef77c7a2d93d110ce5caa8c60c313d8d7313325ba51e9d355cff9e855535bb50',
    'build/research/eod/frame-analysis/accepted-01/frame_case.checked.py': 'dccc4527a0a12f4df9f190dfcbd504a9b20c2747611e54fc20a404e062b886de',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def word(memory, address):
    return memory[address] | memory[address+1] << 8


def store_word(memory, address, value):
    memory[address:address+2] = (value & 65535).to_bytes(2, 'little')


def half(value):
    """Arithmetic right shift of the original wrapped sixteen-bit word."""
    value &= 65535
    return (value >> 1) | (value & 32768)


def initialize_tables(incoming):
    """Declared table outputs of original $1283 and $549D, as integer formulas."""
    memory = bytearray(incoming)
    for index in range(512):
        square, reverse = index*index//4, (255-index)*(255-index)//4
        memory[0xb000+index], memory[0xb200+index] = square & 255, square >> 8
        memory[0xb400+index], memory[0xb600+index] = reverse & 255, reverse >> 8
    for index in range(256):
        memory[0xa000+index], memory[0xa100+index] = 16*(index//16), index//16
        reciprocal = 1048576//index if index else 0xffffff
        for page, shift in ((0xa200, 0), (0xa300, 8), (0xa400, 16)):
            memory[page+index] = (reciprocal >> shift) & 255
    return memory


def product_identity_checks(memory):
    comparisons, borrow_cases, first_borrow = 0, 0, None
    for scale in range(256):
        for magnitude in range(128):
            left, right = scale+2*magnitude, (scale ^ 255)+2*magnitude
            q = memory[0xb000+left] | memory[0xb200+left] << 8
            r = memory[0xb400+right] | memory[0xb600+right] << 8
            assert q-r == 2*scale*magnitude
            borrow = int((q & 255) < (r & 255))
            assert (((q >> 8)-(r >> 8)-borrow) & 255) == (2*scale*magnitude >> 8)
            comparisons += 1
            if borrow:
                borrow_cases += 1
                if first_borrow is None:
                    first_borrow = dict(scale=scale, magnitude=magnitude, left_word=q, right_word=r)
    return dict(comparisons=comparisons, low_borrow_required_cases=borrow_cases,
                first_low_borrow_example=first_borrow,
                scope='All byte scales and seven-bit magnitudes; exact quarter-square identity and high-byte borrow, not a projection-rounding substitute.')


def ramp_stage(incoming):
    memory = bytearray(incoming)
    counter, phase = memory[0x5513:0x5515]
    window = None
    if phase == 0:
        window = (27-counter) & 255
        counter = (counter+1) & 255
        if counter >= 13:
            counter, phase = 120, (phase+1) & 255
    elif phase == 1:
        counter = (counter-1) & 255
        if counter == 0:
            phase = 2
    elif phase == 2:
        window = (15+counter) & 255
        counter = (counter+1) & 255
        if counter >= 13:
            phase = 3
    if window is not None:
        # $555F copies descending Y/X, retaining byte wrapping of its index.
        for index in range(15, -1, -1):
            memory[0x60ed+index] = memory[0x556d+((window-(15-index)) & 255)]
    memory[0x5513:0x5515] = bytes((counter, phase))
    return memory, dict(counter=counter, phase=phase, window_top_index=window)


def coefficient_stage(incoming):
    """$5586..$5758: table identities, wrapped words, and arithmetic halves."""
    memory = bytearray(incoming)
    selector = memory[0x17ed]
    old = list(memory[0x17ea:0x17ed])
    angles = [(old[i]+memory[base+selector]) & 255
              for i, base in enumerate((0x17ee, 0x17f7, 0x1800))]
    memory[0x17ea:0x17ed] = bytes(angles)
    memory[0x90:0x93] = bytes(angles)
    a, b, c = angles
    reads = []
    def table(offset, phase):
        phase &= 255
        low, high = 0x0b00+offset+phase, 0x0d00+offset+phase
        value = memory[low] | memory[high] << 8
        reads.append(dict(offset=offset, phase=phase, low_address=low, high_address=high, word=value))
        return value
    x, y = (c+b+a) & 255, (c-b+a) & 255
    u = half(table(0, x)-table(0, y))
    v = half(table(64, x)-table(64, y))
    x, y = (c+b-a) & 255, (c-b-a) & 255
    w = half(table(0, x)-table(0, y))
    q = half(table(64, x)-table(64, y))
    for address, value in zip(range(0x80, 0x88, 2), (u, v, w, q)):
        store_word(memory, address, value)
    x, y = (c-a) & 255, (c+a) & 255
    coefficients = {
        0x1e: q-v+table(0, x)+table(0, y),
        0x1a: q+v+table(0, x)-table(0, y),
        0x20: u+w-(table(64, x)-table(64, y)),
        0x18: u-w+table(64, x)+table(64, y),
    }
    store_word(memory, 0x88, u-w)
    store_word(memory, 0x8a, table(64, x)+table(64, y))
    x, y = (c-b) & 255, (c+b) & 255
    coefficients[0x1c] = table(64, x)+table(64, y)
    coefficients[0x16] = table(128, x)+table(128, y)
    coefficients[0x10] = 2*table(128, b)
    x, y = (a-b) & 255, (a+b) & 255
    coefficients[0x12] = table(0, x)+table(0, y)
    coefficients[0x14] = table(64, x)+table(64, y)
    for address, value in coefficients.items():
        store_word(memory, address, half(value))
    return memory, dict(previous_angles=old, selector=selector, updated_angles=angles,
        coefficients=[dict(address=address, word=word(memory, address)) for address in range(0x10, 0x22, 2)],
        original_table_reads=reads)


def projected_value(memory, value, scale, reads):
    """$598E: original ones-complement sign handling and two-byte borrow."""
    negative = bool(value & 128)
    magnitude = value ^ (255 if negative else 0)
    index = (2*magnitude) & 255
    addresses = [base+low+index for base, low in
                 ((0xb000, scale), (0xb400, scale ^ 255),
                  (0xb200, scale), (0xb600, scale ^ 255))]
    values = [memory[address] for address in addresses]
    borrow = int(values[0] < values[1])
    high = (values[2]-values[3]-borrow) & 255
    restored = high ^ (0 if negative else 255)
    result = ((restored ^ 127)-64) & 255
    reads.append(dict(input=value, scale=scale, index=index, addresses=addresses,
                      bytes=values, low_borrow=borrow, returned=result))
    return result


def vertex_stage(incoming):
    """$5759..$59A8: four corner sums and four complemented counterparts."""
    memory = bytearray(incoming)
    assert [memory[a] for a in (0xe9, 0xeb, 0xed, 0xef)] == [0xb0, 0xb2, 0xb4, 0xb6]
    pointer = word(memory, 0x26)
    rows = [[word(memory, base+offset) for base in (0x10, 0x16, 0x1c)] for offset in (0, 2, 4)]
    reads, records = [], []
    for index, (sy, sz) in enumerate(((1, 1), (1, -1), (-1, 1), (-1, -1))):
        raw = [(row[0]+sy*row[1]+sz*row[2]) & 65535 for row in rows]
        base, opposite = 0x40+6*index, 0x58+6*index
        for offset, value in zip((0, 2, 4), raw):
            store_word(memory, base+offset, value)
        depth = (raw[2] >> 8) ^ 128
        memory[base+5], memory[opposite+5] = depth, depth ^ 255
        for target, invert, z in ((base, False, depth), (opposite, True, depth ^ 255)):
            scale = memory[(pointer+z) & 65535]
            x = (raw[0] >> 8) ^ (255 if invert else 0)
            y = (raw[1] >> 8) ^ (255 if invert else 0)
            # Source evaluates Y before X; preserving the read order is useful provenance.
            memory[target+3] = projected_value(memory, y, scale, reads)
            memory[target+1] = projected_value(memory, x, scale, reads) >> 1
            records.append(dict(base=target, raw_source_words=raw, complemented=invert,
                projected_X=memory[target+1], projected_Y=memory[target+3],
                depth_selector=z, scale_pointer=pointer, scale_address=(pointer+z) & 65535, scale=scale))
    last_scale = memory[(pointer+memory[0x6f]) & 65535]
    memory[0xe8], memory[0xea] = last_scale, last_scale
    memory[0xec], memory[0xee] = last_scale ^ 255, last_scale ^ 255
    return memory, dict(records=records, product_table_reads=reads,
        low_slots='Only records40/46/4C/52 receive raw low bytes; opposite-record low slots are preserved.')


def face_carry(points):
    """$5A25: zero/sign cases followed by at most seven quotient-bit tests."""
    (x0, y0), (x1, y1), (x2, y2) = points
    dx1, dy1, dx2, dy2 = x1-x0, y1-y0, x2-x0, y2-y0
    u, v, w, t = map(abs, (dx1, dy1, dx2, dy2))
    sign_a = int((dx1 < 0) != (dy2 < 0))
    sign_b = int((dy1 < 0) != (dx2 < 0))
    zeros = sum(value == 0 for value in (u, v, w, t))
    details = dict(points=points, absolute_differences=[u, v, w, t],
                   product_signs=[sign_a, sign_b], zero_count=zeros)
    if zeros == 0 and sign_a != sign_b:
        return int(not sign_b), dict(details, path='opposite product signs')
    if zeros >= 3:
        return 1, dict(details, path='at least three zero factors')
    if zeros == 1:
        if u == 0 or t == 0:
            return int(not sign_b), dict(details, path='first product zero')
        return sign_a, dict(details, path='second product zero')
    if zeros == 2:
        if v == 0 and w == 0:
            return sign_a, dict(details, path='second product has both zero factors')
        if u == 0 and t == 0:
            return int(not sign_b), dict(details, path='first product has both zero factors')
        return 1, dict(details, path='both products zero')
    # Equal product signs: ratios are normalized by each pair's magnitude.
    r1, d1, order1 = min(u, v), max(u, v), int(u >= v)
    r2, d2, order2 = min(w, t), max(w, t), int(w >= t)
    if order1 != order2:
        return order2 ^ sign_b, dict(details, path='different normalized order')
    parity = order2 ^ sign_b
    bits = []
    for _ in range(7):
        r1, r2 = (2*r1) & 255, (2*r2) & 255
        q1, q2 = int(r1 >= d1), int(r2 >= d2)
        if q1:
            r1 -= d1
        if q2:
            r2 -= d2
        bits.append([q1, q2])
        if q1 != q2:
            normalized_sign = int(q1 > q2)
            carry = int((normalized_sign ^ parity) != 1)
            return carry, dict(details, path='quotient-bit difference', quotient_bits=bits)
    return 1, dict(details, path='seven equal quotient bits', quotient_bits=bits)


def visibility_stage(incoming):
    """$59A9..$5B55: six exact helper decisions and twelve adjacency sums."""
    memory = bytearray(incoming)
    calls = ((0, 12, 6), (0, 42, 12), (0, 6, 42),
             (24, 30, 36), (24, 18, 30), (24, 36, 18))
    faces = []
    for index, offsets in enumerate(calls):
        points = [(memory[0x41+offset], memory[0x43+offset]) for offset in offsets]
        carry, details = face_carry(points)
        memory[0x60fd+index] = 1-carry
        faces.append(dict(index=index, record_offsets=offsets, returned_carry=carry,
                          face_flag=1-carry, arithmetic=details))
    edges = []
    for index in range(11, -1, -1):
        first, second = memory[0x6157+index], memory[0x6163+index]
        assert 0 <= first < 6 and 0 <= second < 6
        flag = memory[0x60fd+first]+memory[0x60fd+second]
        assert 0 <= flag <= 2  # No ADC carry can propagate into the next edge.
        memory[0x6133+index] = flag
        edges.append(dict(index=index, adjacent_faces=[first, second], flag=flag))
    return memory, dict(faces=faces, edges=edges,
        scope='Exact original projected-coordinate decision tree, including its seven-bit fallback; not an ideal area-sign replacement.')


def original_memory():
    memory = bytearray(65536)
    for number in (51, 52):
        raw = (EXTRACT/f'trackmo-{number:03}.decoded.prg').read_bytes()
        start = int.from_bytes(raw[:2], 'little')
        memory[start:start+len(raw)-2] = raw[2:]
    return memory


def native_stages(original):
    proof_path = BASE/'frame-analysis/accepted-01/frame-proof.json'
    accepted = json.loads(proof_path.read_text())
    assert accepted['pass_'] and accepted['case_sha256'] == 'b5218a5a088bb0343970327b8ddfc03ea3c177f6bf471db5a739f4bd00817af9'
    captures = {row['stem']: row for row in accepted['captures']}
    memories, inputs = {}, []
    for stem in ('begin', 'ramp', 'coefficients', 'vertices', 'visibility'):
        row = captures[stem]['ram']
        path = ROOT/row['path']
        raw = path.read_bytes()
        assert len(raw) == row['bytes'] == 65536 and sha(raw) == row['sha256']
        memories[stem] = raw
        inputs.append(artifact(path))
    before = memories['begin']
    bound_sources = []
    for start, end in ((0x0b00, 0x0c80), (0x0d00, 0x0e80), (0x1283, 0x12f6),
                       (0x549d, 0x5513), (0x5515, 0x556d), (0x5586, 0x5b56),
                       (0x6157, 0x616f), (0x6490, 0x6590)):
        assert before[start:end] == original[start:end]
        bound_sources.append(dict(start=start, end_exclusive=end, sha256=sha(before[start:end])))
    predicted = initialize_tables(before)
    table_results = []
    for start, end in ((0xa000, 0xa500), (0xb000, 0xb800)):
        assert predicted[start:end] == before[start:end]
        table_results.append(dict(start=start, bytes=end-start, all_equal=True, sha256=sha(predicted[start:end])))
    stage_rows = []
    calls = (
        ('ramp', ramp_stage, 0x546a, 0x546d, ((0x5513,0x5515), (0x60ed,0x60fd))),
        ('coefficients', coefficient_stage, 0x546d, 0x5470,
         ((0x10,0x22), (0x80,0x8c), (0x90,0x93), (0x17ea,0x17ed))),
        ('vertices', vertex_stage, 0x5470, 0x5473, ((0x40,0x70), (0xe8,0xf0))),
        ('visibility', visibility_stage, 0x5473, 0x5476, ((0x60fd,0x6103), (0x6133,0x613f))),
    )
    previous_stem = 'begin'
    for stem, function, entry_pc, return_pc, ranges in calls:
        source_state = captures[previous_stem]['registers']
        target_state = captures[stem]['registers']
        assert (source_state['pc'], target_state['pc']) == (entry_pc, return_pc)
        assert source_state['sp'] == target_state['sp'] == 0xe9
        predicted, details = function(predicted)
        comparisons = []
        for start, end in ranges:
            assert predicted[start:end] == memories[stem][start:end], (stem, hex(start))
            comparisons.append(dict(start=start, bytes=end-start, all_equal=True,
                                    predicted_sha256=sha(predicted[start:end])))
        stage_rows.append(dict(stage=stem, entry=entry_pc, continuation=return_pc,
            compared_bytes=sum(end-start for start,end in ranges), ranges=comparisons,
            observed_elapsed_cycles=target_state['clock']-source_state['clock'], calculation=details))
        previous_stem = stem
    return dict(accepted_frame_proof=artifact(proof_path), consumed_capture_inputs=inputs,
        source_ranges_equal=bound_sources, independently_regenerated_tables=table_results,
        chained_from='begin only; no native current-frame return bytes enter the next prediction',
        stages=stage_rows, compared_stage_bytes=sum(row['compared_bytes'] for row in stage_rows),
        limits=['One captured pose and stable ramp phase; no general animation/corner-case acceptance.',
            'Compared arrays include declared preserved slots; other scratch RAM, CPU flags/registers and stack writes are not modeled.',
            'Visibility scratch70..79 is not reconstructed and is not read by the separate contour scalar.',
            'Clock differences are accepted observed elapsed stage windows, not scalar instruction-time estimates or FPS.']), predicted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE/'geometry-analysis').resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    for name, pin in PINS.items():
        assert sha((ROOT/name).read_bytes()) == pin, name
    memory = original_memory()
    guards = []
    def guard(start, expected, role):
        raw = bytes.fromhex(expected)
        assert memory[start:start+len(raw)] == raw
        guards.append(dict(start=start, bytes=expected, role=role))
    guard(0x546a, '20155520865520595720a95920565b', 'four upstream calls and pre-contour continuation')
    guard(0x574b, 'a210b5110a76117610caca10f560', 'arithmetic half of all nine coefficient words')
    guard(0x598e, '08100249ff0aa838b1e8f1ecb1eaf1ee28300249ff497f38e94060', 'borrow-sensitive projection and ones-complement signs')
    guard(0x5a0f, '18a20bbc5761b9fd60bc636179fd609d3361ca10ee60', 'edge visibility adjacency sum')
    tables = initialize_tables(memory)
    multiplication = product_identity_checks(tables)
    witness, predicted = native_stages(memory)
    outputs = []
    out.mkdir(parents=True)
    for name, raw in (('tables-a000.bin', bytes(predicted[0xa000:0xa500])),
                      ('tables-b000.bin', bytes(predicted[0xb000:0xb800])),
                      ('coefficients-0010.bin', bytes(predicted[0x10:0x22])),
                      ('vertices-0040.bin', bytes(predicted[0x40:0x70])),
                      ('visibility.bin', bytes(predicted[0x60fd:0x6103]+predicted[0x6133:0x613f])),
                      ('geometry.checked.py', Path(__file__).read_bytes())):
        (out/name).write_bytes(raw)
        outputs.append(dict(name=name, bytes=len(raw), sha256=sha(raw)))
    proof = dict(pass_=True, phase='independent scalar upstream stages compared at original native continuations',
        producer=artifact(Path(__file__)), inputs=[artifact(ROOT/p) for p in PINS], guards=guards,
        stages=[dict(entry=a, continuation=b, role=role) for a, b, role in
            ((0x5515, 0x546d, 'ramp counter/window'), (0x5586, 0x5470, 'nine signed-word coefficients'),
             (0x5759, 0x5473, 'eight projected corner records'), (0x59a9, 0x5476, 'six face/twelve edge flags'))],
        original_code_ranges=[dict(start=a, end_exclusive=b, sha256=sha(memory[a:b])) for a,b in
            ((0x1283, 0x12f6), (0x549d, 0x5513), (0x5515, 0x556d),
             (0x5586, 0x5759), (0x5759, 0x59a9), (0x59a9, 0x5b56))],
        input_contract=dict(angles=[0x17ea, 0x17eb, 0x17ec], velocity_selector=0x17ed,
            velocity_table_bases=[0x17ee, 0x17f7, 0x1800], coefficient_words=list(range(0x10, 0x22, 2)),
            projection_scale_pointer=0x26, prepared_product_pages=[0xb000,0xb200,0xb400,0xb600]),
        output_contract=dict(vertex_bases=list(range(0x40,0x70,6)), projected_X_offset=1,
            projected_Y_offset=3, depth_and_intensity_selector_offset=5,
            face_flags=[0x60fd,0x6103], edge_flags=[0x6133,0x613f]),
        product_identity=multiplication,
        native_witness=witness,
        limits=['Source-specific scalar functions; no CPU instruction interpreter, native execution or build.',
            'Current-frame predicted outputs are chained from begin; native stage returns are comparison oracles only.',
            'Depth selector supplies contour intensity bins; no independent normal/light-vector calculation identified in these stages.'],
        outputs=outputs)
    raw = (json.dumps(proof, indent=2)+'\n').encode()
    (out/'geometry-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True, receipt_bytes=len(raw), receipt_sha256=sha(raw)), indent=2))


if __name__ == '__main__':
    main()
