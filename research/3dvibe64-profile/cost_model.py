#!/usr/bin/env python3
"""Count source-level work in accepted spans; do not execute a CPU or renderer.

This is a hypothesis/workload model, not measured cycle attribution. Small
nominal instruction-cost ceilings deliberately exclude candidate setup costs,
page penalties, VIC stalls and IRQs. No product or frozen evidence is edited.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/3dvibe64-native'
OUT = ROOT / 'build/research/3dvibe64-profile/hypothesis-analysis'
PINS = {
    'build/research/3dvibe64-native/build-01/products/3Dvibe64.asm': '22008b3a92b7896c699543b12f9036704797262aa3558cd9116d8a09c85b796f',
    'build/research/3dvibe64-native/build-01/products/3Dvibe64.prg': '69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb',
    'build/research/3dvibe64-native/symbols-01/3Dvibe64.labels': '265a1770fe7a605139f0cdfd9d2983f6ddb314a1cf234a6f3a14d6f3b344e847',
    'build/research/3dvibe64-native/pixel-analysis/pixel-proof.json': '6f579e43f1585a2e338909ff77f5c99997ee8e0f793a7fd0ed23a7d3cc699c30',
    'build/research/3dvibe64-native/pixel-analysis/sample1-spans.json': '48af0395cf567db4de3b50cdb79232f05da7358d8c7ef9c943edf96a33f0f201',
    'build/research/3dvibe64-native/pixel-analysis/sample2-spans.json': 'fbb0c718e5e3d4c47b86d08098f5866ff52f0adaaa2c02bde7b39f3dffc3cee4',
    'build/research/3dvibe64/source/work/build-3Dvibe64.ps1': 'b03d5d7ce6e9e5af85d47c04950841da96f1f3e6dc7b50f5c26a1f97c5bb7e70',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def rank(x, y):
    return 8 * ((x & 1) ^ (y & 1)) + 4 * (y & 1) + 2 * (((x >> 1) ^ (y >> 1)) & 1) + ((y >> 1) & 1)


def packed(shade, y):
    return sum(((2 if rank(x, y & 3) < shade else 1) if shade <= 16
                else (3 if rank(x, y & 3) < shade - 16 else 2)) << (6 - 2 * x) for x in range(4))


def workload(spans, accepted):
    count = Counter()
    cells, long_constant_runs = set(), []
    for span in spans:
        x0, x1, y, extent, delta = (span[k] for k in ('x0', 'x1', 'y', 'extent', 'delta'))
        assert extent == x1 - x0 and 0 <= x0 <= x1 < 160 and 0 <= y < 100
        count['spans'] += 1
        count['input_pixels'] += extent + 1
        count['shorter_than_eight_pixels'] += extent < 7
        columns = list(range(x0 // 4, x1 // 4 + 1))
        count['material_cell_touches'] += len(columns)
        cells.update((y // 4, column) for column in columns)
        eligible = extent >= 7
        uniform = eligible and packed(span['shade0'], y) == packed(span['shade1'], y)
        count['classifier_spans'] += eligible
        count['classifier_LUT_reads'] += 2 * eligible
        count['uniform_spans'] += uniform
        count['uniform_pixels'] += (extent + 1) if uniform else 0
        if uniform:
            count['uniform_bitmap_byte_groups'] += len(columns)
            count['uniform_boundary_RMW_byte_groups'] += 2
            continue
        count['gradient_spans'] += 1
        count['gradient_pixels'] += extent + 1
        full_columns = set()
        for column in columns:
            first, last = max(x0, 4 * column), min(x1, 4 * column + 3)
            if last - first == 3:
                full_columns.add(column)
                count['gradient_full_byte_groups'] += 1
            else:
                count['gradient_partial_byte_groups'] += 1
                count['gradient_partial_pixels'] += last - first + 1
        count['gradient_LUT_reads'] += extent + 1
        at_most_one = extent > 0 and delta <= extent
        count['gradient_spans_delta_le_extent'] += at_most_one
        last_pattern, run_length = None, 0
        for k in range(extent + 1):
            shade = span['shade0'] + span['direction'] * (k * delta // extent if extent else 0)
            pattern = packed(shade, y)
            if pattern == last_pattern:
                run_length += 1
            else:
                if run_length >= 8:
                    long_constant_runs.append(run_length)
                last_pattern, run_length = pattern, 1
            if k == extent:
                continue
            x = x0 + k
            register = x // 4 in full_columns and (x & 3) < 3
            increments = ((k + 1) * delta // extent) - (k * delta // extent)
            suffix = 'register' if register else 'RAM'
            count['DDA_advances_' + suffix] += 1
            count['DDA_shade_increments_' + suffix] += increments
            count['DDA_multistep_advances'] += increments > 1
            count['DDA_max_shade_increments_per_advance'] = max(count['DDA_max_shade_increments_per_advance'], increments)
            if at_most_one:
                count['one_step_domain_shade_increments_' + suffix] += increments
        if run_length >= 8:
            long_constant_runs.append(run_length)
    assert count['spans'] == accepted['span_count'] and count['input_pixels'] == accepted['pixel_writes']
    assert count['uniform_spans'] == accepted['classifier_eligible_uniform_spans']
    assert count['gradient_pixels'] == 4 * count['gradient_full_byte_groups'] + count['gradient_partial_pixels']
    assert count['DDA_advances_register'] == 3 * count['gradient_full_byte_groups']
    assert count['DDA_advances_register'] + count['DDA_advances_RAM'] == count['gradient_pixels'] - count['gradient_spans']
    count['unique_material_cells'] = len(cells)
    count['repeated_material_cell_touches_same_fixed_ramp'] = count['material_cell_touches'] - len(cells)
    groups = count['uniform_bitmap_byte_groups'] + count['gradient_full_byte_groups'] + count['gradient_partial_byte_groups']
    count['bitmap_stores_two_physical_rows'] = 2 * groups
    count['bitmap_reads_partial_boundaries'] = 2 * (count['gradient_partial_byte_groups'] + count['uniform_boundary_RMW_byte_groups'])
    count['long_constant_packet_runs_inside_gradient_spans'] = len(long_constant_runs)
    count['pixels_in_those_runs'] = sum(long_constant_runs)
    interval = accepted['timing']['cycles']
    nominal = {
        'all_material_STAs_only': 12 * count['material_cell_touches'],
        'direct_material_call_JSR_pointer_loops_RTS': 44 * count['material_cell_touches'] +
            sum(45 if span['drawbuf'] == 0 else 42 for span in spans),
        'repeated_material_STAs_only': 12 * count['repeated_material_cell_touches_same_fixed_ramp'],
        'duplicate_bitmap_STAs_only': 6 * groups,
        'duplicate_bitmap_row_instructions':
            19 * (count['gradient_partial_byte_groups'] + count['uniform_boundary_RMW_byte_groups']) +
            8 * (count['gradient_full_byte_groups'] + count['uniform_bitmap_byte_groups'] - count['uniform_boundary_RMW_byte_groups']),
        'Bayer_constant_high_byte_lookup_and_7_operand_STAs': 32 * len(spans),
        'Mode6_unused_ptr1_initializer_half': 22 * len(spans),
        'one_step_retest_gross_register': 14 * count['one_step_domain_shade_increments_register'],
        'one_step_retest_gross_RAM': 18 * count['one_step_domain_shade_increments_RAM'],
    }
    return dict(source_predicted_work=dict(sorted(count.items())),
        selected_nominal_existing_instruction_costs={k: dict(cycles=v, fraction_of_accepted_interval=v / interval)
                                                    for k, v in nominal.items()},
        nominal_cost_limits='These are isolated existing instruction costs, not predicted net savings. New dispatch/setup, liveout preservation, page penalties, VIC stalls and IRQs are not modeled. Do not sum them into measured CPU attribution.',
        accepted_interval_cycles=interval, mean_input_pixels_per_span=count['input_pixels'] / len(spans),
        uniform_path_individually_observed=False, accepted_bitmap_oracle_reexecuted=False)


def main():
    for relative, digest in PINS.items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
    asm = (BASE / 'build-01/products/3Dvibe64.asm').read_text()
    for flag, value in [('GOURAUD_BYTE_SPAN_KERNEL', 1), ('MATERIAL_CELL_SPAN_CACHE', 1),
                        ('FACE_MATERIAL_ACTIVE_ONLY', 0), ('FACE_REFLECTIVITY_ACTIVE_ONLY', 0), ('VIC_COLOR_POLICY_ENABLE', 0)]:
        assert re.search(r'(?m)^' + flag + r' = \$' + f'{value:02x}' + r'$', asm, re.I)
    symbols = {m[2]: int(m[1], 16) for m in re.finditer(r'(?m)^al ([0-9a-f]+) \.(\w+)$',
        (BASE / 'symbols-01/3Dvibe64.labels').read_text(), re.I)}
    rows = [symbols['gouraud_bayer_code_lut_y' + str(i)] for i in range(4)]
    assert rows == [0xb526, 0xb547, 0xb568, 0xb589] and len({r >> 8 for r in rows}) == 1
    proof = json.loads((BASE / 'pixel-analysis/pixel-proof.json').read_text())
    results = []
    for index, accepted in enumerate(proof['accepted_samples'], 1):
        spans = json.loads((BASE / f'pixel-analysis/sample{index}-spans.json').read_text())
        results.append(dict(name=f'sample{index}', **workload(spans, accepted)))
    OUT.mkdir(parents=True, exist_ok=True)
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()),
        inputs=[artifact(ROOT / p) for p in PINS], samples=results, Bayer_row_addresses=rows,
        Bayer_high_byte_compile_time_constant=0xb5,
        scope='Source-derived operation counts and bounded hypotheses only. No native CPU, SDK/build/process or optimization is executed; measured call-tree attribution is a separate lane.')
    result['pass'] = result.pop('pass_')
    path = OUT / 'cost-hypotheses.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    (OUT / 'cost_model.checked.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(receipt=artifact(path), samples=results), indent=2))


if __name__ == '__main__':
    main()
