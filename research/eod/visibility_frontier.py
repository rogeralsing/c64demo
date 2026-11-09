#!/usr/bin/env python3
"""Passive EOD visibility precision and remaining-scene planning study."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/eod'
PINS = {
    'research/eod/geometry.py': '7c70f18cc1f586ddb8be70f8a4be5bd9ce67a456eb2d4772ef74cb3f97415d4b',
    'build/research/eod/output-case-analysis/accepted-01/output-case-proof.json': '0fe2af337eb6a2674e6cb60b7f861b744457fa7ee8b65e05eed2d10bd9c6a0dd',
    'build/research/eod/multi-pose-analysis/accepted-01/multi-pose-proof.json': 'ca3baca1dd889b3b0e9ef9fe81d5f1f3c89f27c15d7a420f105a19d670f19a11',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-051.decoded.prg': 'e4899712681147b233a960d675aab369feebac4ba149073f1051d45f78b5312c',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-052.decoded.prg': '3adc5e1b6990cf41b3d93954de9d92bd3da62b4b562fc636cbd827cf94d67c04',
}
ANCHORS = {'baseline': 0, 'p110': 10, 'p096': 24, 'p072': 48, 'p024': 96, 'p206': 126}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load_geometry():
    spec = importlib.util.spec_from_file_location('eod_visibility_frontier_geometry', ROOT/'research/eod/geometry.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def area(points):
    (x0, y0), (x1, y1), (x2, y2) = points
    return (x1-x0)*(y2-y0)-(y1-y0)*(x2-x0)


def quotient_code(numerator, denominator):
    """Seven original quotient decisions, including the ratio-one endpoint."""
    remainder, code = numerator, 0
    for _ in range(7):
        remainder *= 2
        bit = int(remainder >= denominator)
        if bit:
            remainder -= denominator
        code = 2*code+bit
    return code


def precision(geometry):
    # This domain excludes zero factors and restricts differences to 1..127.
    # Doubling a reduced remainder then fits in the source's eight-bit path.
    buckets = defaultdict(list)
    for x in range(1, 128):
        for y in range(1, 128):
            low, high = min(x, y), max(x, y)
            actual = quotient_code(low, high)
            expected = min(127, (128*low)//high)
            assert actual == expected
            buckets[(int(x >= y), actual)].append((x, y))
    ordered_pairs = equal_area_pairs = positive_area_pairs = 0
    checked_pairs, first_nonzero = 0, None
    for key, vectors in sorted(buckets.items()):
        multiplicities = Counter(Fraction(x, y) for x, y in vectors)
        pairs = len(vectors)**2
        equal = sum(count**2 for count in multiplicities.values())
        ordered_pairs += pairs
        equal_area_pairs += equal
        positive_area_pairs += (pairs-equal)//2
        # Adjacent rational slopes exercise every distinct-ratio boundary in
        # each code bucket. The count above is a symmetry derivation, not a
        # claim to have executed every pair through face_carry.
        ordered = sorted(vectors, key=lambda vector: Fraction(*vector), reverse=True)
        for first, second in zip(ordered, ordered[1:]):
            points = [(0, 0), first, second]
            carry, details = geometry.face_carry(points)
            assert carry == 1 and details['path'] == 'seven equal quotient bits'
            assert area(points) >= 0
            checked_pairs += 1
            if area(points) > 0 and first_nonzero is None:
                first_nonzero = dict(points=points, signed_integer_area=area(points),
                    returned_carry=carry, face_flag=1-carry, code_bucket=list(key),
                    quotient_bits=details['quotient_bits'])
    assert first_nonzero is not None
    controls = []
    for points in ([(0, 0), (1, 126), (1, 127)], [(0, 0), (1, 127), (1, 126)]):
        carry, details = geometry.face_carry(points)
        assert carry == 1 and details['path'] == 'seven equal quotient bits'
        assert abs(area(points)) == 1
        controls.append(dict(points=points, signed_integer_area=area(points),
            face_flag=1-carry, path=details['path'], quotient_bits=details['quotient_bits']))
    return dict(domain='Origin plus two positive vectors with X,Y in1..127; no zero factors or byte-doubling overflow',
        normalized_vectors=127**2, quotient_formula='min(127,floor(128*min(X,Y)/max(X,Y)))',
        nonempty_order_code_buckets=len(buckets), same_bucket_ordered_pairs=ordered_pairs,
        exact_zero_area_pairs=equal_area_pairs, positive_area_pairs_culled=positive_area_pairs,
        negative_area_pairs_culled=positive_area_pairs,
        arithmetic_count_method='Within each same-order/code bucket: (N*N-sum(equal-ratio multiplicity squared))/2 for each nonzero orientation',
        explicitly_executed_adjacent_pairs=checked_pairs, first_positive_area_fallback=first_nonzero,
        unit_area_controls=controls,
        limit='Source-model precision result for the declared coordinate domain, not a native arbitrary-triangle test or a proof of visible defects.')


def trajectory(geometry, case):
    captures = {row['stem']: row for row in case['captures']}
    consumed = []
    memories = {}
    for name in ANCHORS:
        for stage in ('begin', 'body'):
            key = name+'-'+stage
            row = captures[key]['ram']
            path = ROOT/row['path']
            assert artifact(path) == row
            memories[key] = path.read_bytes()
            consumed.append(row)
    state = geometry.initialize_tables(memories['baseline-begin'])
    assert list(state[0x5513:0x5515]) == [120, 1]
    assert list(state[0x17ea:0x17ed]) == [127, 31, 94] and state[0x17ed] == 8
    assert [state[a+8] for a in (0x17ee, 0x17f7, 0x1800)] == [1, 3, 4]
    counts, first, fallbacks, mismatches, anchors, rows = Counter(), {}, [], [], [], []
    coordinate_max_difference = 0
    target_at = {offset: name for name, offset in ANCHORS.items()}
    for offset in range(133):
        before = bytes(state)
        entry = dict(offset=offset, phase=before[0x5514], counter=before[0x5513], angles=list(before[0x17ea:0x17ed]))
        state, ramp = geometry.ramp_stage(state)
        state, _ = geometry.coefficient_stage(state)
        state, _ = geometry.vertex_stage(state)
        state, visibility = geometry.visibility_stage(state)
        faces = []
        for face in visibility['faces']:
            details = face['arithmetic']
            path, signed_area = details['path'], area(details['points'])
            counts[path] += 1
            coordinate_max_difference = max(coordinate_max_difference, *details['absolute_differences'])
            record = dict(face=face['index'], path=path, points=details['points'],
                signed_integer_area=signed_area, face_flag=face['face_flag'],
                exact_positive_area_flag=int(signed_area > 0))
            if 'quotient_bits' in details:
                record['quotient_bits'] = details['quotient_bits']
            first.setdefault(path, dict(entry, **record))
            if path == 'seven equal quotient bits':
                fallbacks.append(dict(entry, **record))
            if face['face_flag'] != int(signed_area > 0):
                mismatches.append(dict(entry, **record))
            faces.append(record)
        rows.append(dict(entry, exit_ramp=ramp, faces=faces))
        if offset in target_at:
            name = target_at[offset]
            native_before, native_body = memories[name+'-begin'], memories[name+'-body']
            compared = []
            for stage, predicted, observed, ranges in (
                ('begin', before, native_before, ((0x5513,0x5515),(0x17ea,0x17ed))),
                ('body', state, native_body, ((0x5513,0x5515),(0x17ea,0x17ed),(0x40,0x70),(0x60ed,0x6103),(0x6133,0x613f)))):
                for start, end in ranges:
                    assert predicted[start:end] == observed[start:end], (name, stage, hex(start))
                    compared.append(dict(stage=stage,start=start,bytes=end-start,all_equal=True,sha256=sha(predicted[start:end])))
            anchors.append(dict(name=name,offset=offset,ranges=compared,all_equal=True))
    assert state[0x5514] == 3 and len(rows) == 133 and sum(counts.values()) == 798
    return dict(scope='Source-model remaining trajectory from one native baseline through133 bodies; six existing native anchors only',
        inputs=consumed, body_count=133,face_decisions=798,branch_counts=dict(sorted(counts.items())),
        first_predicted_branch_entries=first,seven_bit_fallbacks=fallbacks,
        differences_from_positive_integer_area=mismatches,max_absolute_coordinate_difference=coordinate_max_difference,
        six_native_anchors=anchors,rows=rows,
        limits=['Only baseline-begin seeds the trajectory; later native captures are comparison oracles.',
            'The semantic sequence runs ramp/coefficient/vertex/visibility only; it does not simulate other frame writes, a CPU, IRQs or elapsed cycles.',
            'Six range comparisons support the declared upstream progression; remaining predicted entries need their own original native observation.',
            'Projected integer area is an independent arithmetic comparison, not exact3D visibility or physical lighting.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE/'visibility-frontier-analysis').resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    for name, expected in PINS.items():
        assert sha((ROOT/name).read_bytes()) == expected, name
    case = json.loads((ROOT/'build/research/eod/output-case-analysis/accepted-01/output-case-proof.json').read_text())
    assert case['pass_']
    geometry = load_geometry()
    quantization, motion = precision(geometry), trajectory(geometry,case)
    checked = Path(__file__).read_bytes()
    out.mkdir(parents=True)
    (out/'visibility_frontier.checked.py').write_bytes(checked)
    proof = dict(pass_=True,scope='Declared-domain visibility precision and source-predicted remaining-scene branches with six existing native anchors',
        producer=artifact(Path(__file__)),inputs=[artifact(ROOT/name) for name in PINS],
        precision=quantization,trajectory=motion,
        outputs=[dict(name='visibility_frontier.checked.py',bytes=len(checked),sha256=sha(checked))],
        limits=['No new native execution or complete animation/display proof.',
            'A nonzero-area source-model fallback is not automatically a visible artifact or a bug.',
            'No product change, CPU interpreter, subprocess, build or frozen-source edit.'])
    raw = (json.dumps(proof,indent=2)+'\n').encode()
    (out/'visibility-frontier-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,receipt_bytes=len(raw),receipt_sha256=sha(raw),
        source_predicted_bodies=motion['body_count'],native_anchors=len(motion['six_native_anchors']),
        natural_fallbacks=len(motion['seven_bit_fallbacks']),area_differences=len(motion['differences_from_positive_integer_area']),
        bounded_positive_area_fallback_pairs=quantization['positive_area_pairs_culled']),indent=2))


if __name__ == '__main__':
    main()
