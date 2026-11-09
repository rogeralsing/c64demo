#!/usr/bin/env python3
"""Passive multi-pose EOD geometry, contours and common-prefix acceptance."""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/eod'
OUTPUT_ROOT = BASE/'multi-pose-analysis'
# The original native04 case was closed before these accepted pins were set.
CASE_PROOF = 'build/research/eod/output-case-analysis/accepted-01/output-case-proof.json'
CASE_PROOF_SHA256 = '0fe2af337eb6a2674e6cb60b7f861b744457fa7ee8b65e05eed2d10bd9c6a0dd'
PINS = {
    'research/eod/geometry.py': '7c70f18cc1f586ddb8be70f8a4be5bd9ce67a456eb2d4772ef74cb3f97415d4b',
    'research/eod/contours.py': '2fce8719143284f21b232b6a9fa80696b08cb63f9f81c5fb1ecda49270cca7d5',
    'research/eod/prefix.py': '72bfb8b93646af03f204fec689f095929b0e6920b532cdae104ac8b2cc828938',
    'build/research/eod/geometry-analysis/accepted-01/geometry-proof.json': '33d4119215b249e76c8093a71d655cacb6b9d8c58804c73315915ef734a55cec',
    'build/research/eod/contour-analysis/accepted-01/contour-proof.json': 'b8396182b088637ecb91aaba9f2bfd257b99efe7289b254dcd0dba612c3e5b98',
    'build/research/eod/prefix-analysis/accepted-01/prefix-proof.json': '3bc7c07dc281850885dc1671cbca55a2c9a42a1340d99bd8fe19afb919ec057b',
    'build/research/eod/frame-analysis/accepted-01/frame-proof.json': 'ef77c7a2d93d110ce5caa8c60c313d8d7313325ba51e9d355cff9e855535bb50',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-051.decoded.prg': 'e4899712681147b233a960d675aab369feebac4ba149073f1051d45f78b5312c',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-052.decoded.prg': '3adc5e1b6990cf41b3d93954de9d92bd3da62b4b562fc636cbd827cf94d67c04',
}
TARGETS = (
    ('baseline', 1, 120, 0, [127, 31, 94]),
    ('p110', 1, 110, 10, [137, 61, 134]),
    ('p096', 1, 96, 24, [151, 103, 190]),
    ('p072', 1, 72, 48, [175, 175, 30]),
    ('p024', 1, 24, 96, [223, 63, 222]),
    ('p206', 2, 6, 126, [253, 153, 86]),
)
STAGES = {'begin': 0x546a, 'body': 0x17db, 'prefix-before': 0x1a73,
          'filled': 0x1750, 'cleared': 0x1753}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def compare(predicted, observed, start):
    assert len(predicted) == len(observed)
    errors = [dict(address=start+i, predicted=a, observed=b)
              for i, (a, b) in enumerate(zip(predicted, observed)) if a != b]
    return dict(bytes=len(predicted), all_equal=not errors, mismatches=len(errors),
                predicted_sha256=sha(predicted), observed_sha256=sha(observed),
                examples=errors[:8])


def read_capture(record):
    path = ROOT/record['ram']['path']
    raw = path.read_bytes()
    assert len(raw) == record['ram']['bytes'] == 65536
    assert sha(raw) == record['ram']['sha256']
    assert not record['registers']['flags'] & 8, 'Decimal mode is not supported'
    return raw, artifact(path)


def source_guards(memory, geometry):
    """Bind original stage code/data, with only four declared SMC operands."""
    original = geometry.original_memory()
    calls = (0x1993, 0x1a69, 0x601e, 0x60b6)
    mutable = {address+offset for address in calls for offset in (1, 2)}
    for address in calls:
        assert original[address] == memory[address] == 0x20
    ranges = ((0x0b00,0x0c80), (0x0d00,0x0e80), (0x1283,0x12f6),
              (0x1856,0x1a73), (0x549d,0x5513), (0x5515,0x60cc),
              (0x6103,0x6133), (0x613f,0x616f), (0x6187,0x61a0),
              (0x6490,0x6590))
    results = []
    for start, end in ranges:
        addresses = [address for address in range(start,end) if address not in mutable]
        actual = bytes(memory[address] for address in addresses)
        expected = bytes(original[address] for address in addresses)
        assert actual == expected, ('Original stage code/data mismatch', hex(start), hex(end))
        results.append(dict(start=start, end_exclusive=end, checked_bytes=len(addresses),
                            sha256=sha(actual), excluded_JSR_operand_bytes=[
                                address for address in range(start,end) if address in mutable]))
    return dict(original_ranges=results, declared_SMC_calls=[dict(address=address,
        incoming_operand=int.from_bytes(memory[address+1:address+3], 'little')) for address in calls],
        SMC_scope='Only the two-byte target operands of four original generated-cell JSR sites are excluded; opcodes and all remaining range bytes match original. Used cells and pointers are separately checked by the frozen contour model.')


def prefix_output(memory, marker, prefix):
    """The frozen descriptor contract; no instruction/CPU execution."""
    groups, context = prefix.descriptor_groups(memory)
    output, cleared = bytearray(memory[0x7000:0x7800]), bytearray(marker)
    for group in groups:
        accumulator = 0
        for cell in group['pairs']:
            accumulator ^= marker[cell['marker']-0x7800]
            output[cell['output']-0x7000] = accumulator
            cleared[cell['marker']-0x7800] = 0
    return bytes(output), bytes(cleared), groups, context


def pipeline(before, geometry, contours, prefix):
    state = contours.initialize_contour_tables(geometry.initialize_tables(before))
    upstream = []
    for name in ('ramp_stage', 'coefficient_stage', 'vertex_stage', 'visibility_stage'):
        state, details = getattr(geometry, name)(state)
        upstream.append(dict(stage=name, details=details))
    model, stages = contours.run_stages(state)
    marker = stages['outer']
    output, cleared, groups, context = prefix_output(before, marker, prefix)
    return model, upstream, marker, output, cleared, groups, context


def branch_summary(model, upstream):
    lines = model.internal_lines
    directions = Counter('flat' if line['XY'][2] == line['XY'][3] else
                         'ascending' if line['XY'][2] < line['XY'][3] else 'descending'
                         for line in lines)
    parity = Counter(f"{line['XY'][0] & 1}{line['XY'][1] & 1}" for line in lines)
    visibility = next(row['details'] for row in upstream if row['stage'] == 'visibility_stage')
    return dict(active_face_ids=[row['index'] for row in visibility['faces'] if row['face_flag']],
        visibility_paths=dict(sorted(Counter(row['arithmetic']['path'] for row in visibility['faces']).items())),
        active_edges=len(model.edges), fresh_intersection_bytes=len(model.edge_writes),
        consumed_intersection_bytes=len(model.intersection_reads),
        consumed_intersections_all_fresh=model.intersection_reads <= model.edge_writes,
        internal_lines=len(lines), internal_Y_directions=dict(sorted(directions.items())),
        internal_X_endpoint_parities=dict(sorted(parity.items())),
        internal_zero_patterns=sum(not line['pattern'] for line in lines),
        outer_kinds=dict(sorted(Counter(edge['kind'] for edge in model.outer_edges).items())),
        plot_operations=len(model.marker_writes),
        zero_mask_operations=sum(not write['mask'] for write in model.marker_writes),
        distinct_marker_addresses=len({write['address'] for write in model.marker_writes}),
        generated_cells_guarded=len(model.cells_checked),
        half_X_generated_cells=sum(address < 0xbc00 for address in model.cells_checked),
        full_X_generated_cells=sum(address >= 0xbc00 for address in model.cells_checked))


def analyze_pose(target, captures, geometry, contours, prefix, out):
    name, phase, counter, delta, angles = target
    memories, input_records, registers = {}, [], {}
    for stage, expected_pc in STAGES.items():
        record = captures[f'{name}-{stage}']
        assert record['registers']['pc'] == expected_pc
        memories[stage], pin = read_capture(record)
        input_records.append(pin)
        registers[stage] = record['registers']
    before = memories['begin']
    assert before[0x1767] == 10 and list(before[0x5513:0x5515]) == [counter, phase]
    assert before[0x546a:0x5485] == bytes.fromhex('20155520865520595720a95920565b20505d20655ead1455c90360')
    assert before[0x17d8:0x17e1] == bytes.fromhex('206a5490b2ee671760')
    assert all(registers[a]['clock'] < registers[b]['clock']
               for a, b in zip(STAGES, list(STAGES)[1:]))
    original_guards = source_guards(before, geometry)
    # Prefix descriptors and preserved output are taken from the begin input.
    # These later fields are guards/comparison oracles, never model seeds.
    groups_before, context = prefix.descriptor_groups(before)
    groups_later, later_context = prefix.descriptor_groups(memories['prefix-before'])
    assert groups_before == groups_later and context == later_context
    incoming_output = compare(before[0x7000:0x7800], memories['prefix-before'][0x7000:0x7800], 0x7000)
    assert incoming_output['all_equal'], 'Output changed before the common prefix'
    hypothesis = dict(source_body_delta=delta, predicted_begin_angles=angles,
        actual_begin_angles=list(before[0x17ea:0x17ed]),
        angles_agree=list(before[0x17ea:0x17ed]) == angles,
        input_phase=phase, input_counter=counter,
        status='Planning hypothesis checked after capture; not a native checkpoint filter')
    result = dict(name=name, inputs=input_records, registers=registers,
                  planning_hypothesis=hypothesis, incoming_output_guard=incoming_output,
                  original_guards=original_guards)
    try:
        model, upstream, marker, output, cleared, groups, context = pipeline(before, geometry, contours, prefix)
    except (AssertionError, ValueError, IndexError) as error:
        # Preserve the native counterexample before considering a narrowly scoped
        # correction in this new wrapper. Frozen producers are never rewritten.
        result.update(pass_=False, model_error=dict(type=type(error).__name__, message=str(error)))
        return result, []
    comparisons = {
        'body_marker': compare(marker, memories['body'][0x7800:0x8000], 0x7800),
        'prefix_before_marker': compare(marker, memories['prefix-before'][0x7800:0x8000], 0x7800),
        'filled_marker': compare(marker, memories['filled'][0x7800:0x8000], 0x7800),
        'filled_output': compare(output, memories['filled'][0x7000:0x7800], 0x7000),
        'cleared_output': compare(output, memories['cleared'][0x7000:0x7800], 0x7000),
        'cleared_marker': compare(cleared, memories['cleared'][0x7800:0x8000], 0x7800),
    }
    outputs = []
    for suffix, raw in (('marker-7800.bin', marker), ('output-7000.bin', output), ('cleared-7800.bin', cleared)):
        filename = f'{name}-{suffix}'
        (out/filename).write_bytes(raw)
        outputs.append(dict(name=filename, bytes=len(raw), sha256=sha(raw)))
    result.update(pass_=all(row['all_equal'] for row in comparisons.values()),
        comparisons=comparisons, branch_coverage=branch_summary(model, upstream), upstream=upstream,
        ramp_after=bytes(model.m[0x60ed:0x60fd]).hex(),
        incoming_marker_nonzero_bytes=sum(bool(x) for x in before[0x7800:0x8000]),
        crop=dict(groups=len(groups), computed_bytes=sum(len(g['pairs']) for g in groups),
                  preserved_bytes=2048-sum(len(g['pairs']) for g in groups),
                  retained_nonzero_markers=sum(bool(x) for x in cleared), context=context),
        observed_elapsed_machine_cycles=dict(
            body=registers['body']['clock']-registers['begin']['clock'],
            prefix=registers['filled']['clock']-registers['prefix-before']['clock'],
            clear=registers['cleared']['clock']-registers['filled']['clock']),
        outputs=[row['name'] for row in outputs])
    return result, outputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to(OUTPUT_ROOT.resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    assert CASE_PROOF and CASE_PROOF_SHA256, 'Native04 is not yet closed and pinned'
    for path, expected in PINS.items():
        assert sha((ROOT/path).read_bytes()) == expected, path
    case_path = ROOT/CASE_PROOF
    assert sha(case_path.read_bytes()) == CASE_PROOF_SHA256
    case = json.loads(case_path.read_text())
    assert case['pass_']
    captures = {row['stem']: row for row in case['captures']}
    geometry = load('eod_multi_geometry', 'research/eod/geometry.py')
    contours = load('eod_multi_contours', 'research/eod/contours.py')
    prefix = load('eod_multi_prefix', 'research/eod/prefix.py')
    out.mkdir(parents=True)
    poses, outputs = [], []
    for target in TARGETS:
        result, files = analyze_pose(target, captures, geometry, contours, prefix, out)
        poses.append(result)
        outputs.extend(files)
    checked = Path(__file__).read_bytes()
    (out/'multi_pose.checked.py').write_bytes(checked)
    outputs.append(dict(name='multi_pose.checked.py', bytes=len(checked), sha256=sha(checked)))
    proof = dict(pass_=all(row['pass_'] for row in poses),
        scope='Six fresh original shader bodies and software prefix/reset outputs from each captured begin state: a baseline, four additional phase1 poses and one phase2 fade pose',
        producer=artifact(Path(__file__)), inputs=[artifact(ROOT/path) for path in PINS]+[artifact(case_path)],
        case_sha256=case['case_sha256'], poses=poses,
        planning_angle_hypotheses_all_match=all(row['planning_hypothesis']['angles_agree'] for row in poses),
        limits=[
            'Closed-case wire, snapshot, source boot lineage and actual phase/counter custody are consumed from the pinned parent acceptance, not re-audited here.',
            'Each current body starts only from its begin546A RAM; later marker/output captures are comparison oracles, never seeds.',
            'Prepared source tables, generated plot/crop descriptors and incoming prior-state bytes remain declared context; tables rebuilt by the frozen models replace their input copies.',
            'The398 cropped-out output/marker bytes preserve initial state. Full2048-byte identity does not imply every byte was written or cleared.',
            'The fresh baseline and four additional poses have stable phase1 shading; p206 is a deliberately different phase2 fade input.',
            'The source-derived target angles and branch predictions were planning hypotheses, not native breakpoint conditions.',
            'This is finite captured-workload acceptance, not arbitrary geometry, clipping, every visibility branch, independent physical lighting or a safe optimization policy.',
            'Software buffer equality does not itself prove actual VIC scanout, palette, publication, complete animation, delivered FPS or timing prediction.',
            'No CPU interpreter, native execution, process control, upstream build or frozen-source edit occurs here.'], outputs=outputs)
    raw = (json.dumps(proof, indent=2)+'\n').encode()
    (out/'multi-pose-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=proof['pass_'], receipt_bytes=len(raw), receipt_sha256=sha(raw),
                         poses=[dict(name=row['name'], pass_=row['pass_']) for row in poses]), indent=2))
    if not proof['pass_']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
