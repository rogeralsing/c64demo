#!/usr/bin/env python3
"""Root's exact passive-replay checks for the two new cell source models."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-cells-20261109'


def meta(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())


def main():
    for lane, accepted, replay, receipt, expected_files in [
        ('cell-analysis', 'accepted-02', 'root-replay-02', 'cell-generator-proof.json', 10),
        ('semantic-analysis', 'accepted-01', 'root-replay-01', 'cell-semantics-proof.json', 7),
    ]:
        first, second = BASE / lane / accepted, BASE / lane / replay
        names = sorted(p.name for p in first.iterdir() if p.is_file())
        assert names == sorted(p.name for p in second.iterdir() if p.is_file())
        assert len(names) == expected_files
        rows = []
        for name in names:
            a, b = meta(first / name), meta(second / name)
            assert a['bytes'] == b['bytes'] and a['sha256'] == b['sha256'], name
            rows.append(dict(accepted=a, replay=b))
        proof = json.loads((first / receipt).read_text())
        assert proof['pass_']
        if lane == 'cell-analysis':
            assert proof['cell_count'] == 312 and proof['generated_bytes'] == 11232
            assert proof['full_generated_byte_equality']
            assert proof['surrounding_source_footprints']['predecessor_does_not_mutate_original_cell_templates_or_group_operand']
            scope = 'Original paired-page generator and its surrounding disjoint source footprints; selected native byte comparisons follow prediction.'
        else:
            assert proof['source_predicted_descriptors'] == 312
            assert proof['source_generated_cell_bytes'] == 11232
            summary = proof['declared_runtime_input_summary']
            assert (summary['calls'], summary['normal_calls'], summary['row_end_calls']) == (200, 175, 25)
            assert summary['unique_declared_call_targets'] == 69
            assert summary['native_post_cell_oracle_available'] is False
            scope = 'Source semantics and conditional arithmetic composition from declared entry inputs; no native post-cell equality or raster timing.'
        path = BASE / lane / 'root-replay-check.json'
        assert not path.exists()
        report = dict(pass_=True, comparison_job=meta(Path(__file__)),
            producer=proof['producer'], accepted_receipt=meta(first / receipt),
            root_review='Complete producer source and exact-generation boundaries reviewed; no material issue. Generator02 adds the requested predecessor/later-store footprint guards without changing predicted cell bytes.',
            compared_files=len(rows), compared_bytes=sum(row['accepted']['bytes'] for row in rows),
            files=rows, all_outputs_byte_identical=True, no_path_normalization=True,
            executes_no_CPU_native_or_downloaded_host_code=True, scope=scope)
        path.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(meta(path)))


if __name__ == '__main__':
    main()
