#!/usr/bin/env python3
"""Extract retained native viewport oracles without predicting any pixels."""
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-execution-20261109'
PINS = {
    'research/the-hat/raster_hardware.py': 'f9d15a6d26b877f63591b3c1ff7e31d3cf9430165783c89cb53b35ea6e32a12f',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'build/research/aloft-execution-20261109/native-analysis/accepted-02/native-proof.json': '5db9694db276541a5fd2b5cb386e92639e6da2c0d6cd644caf758eb113cc2326',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ref(path):
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=sha(raw))


def main():
    for name, digest in PINS.items():
        assert sha((ROOT / name).read_bytes()) == digest
    spec = importlib.util.spec_from_file_location('frozen_aloft_viewport_reader', ROOT / next(iter(PINS)))
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    proof = json.loads((ROOT / list(PINS)[-1]).read_bytes())
    assert proof['pass_'] and proof['wrap_scope']['same_preceding_field_not_two_displayed_generations']
    query = next(row for row in proof['command_audit']['queries'] if row['sequence'] == 186)
    assert query['command'] == 'resourceget "VICIIBorderMode"'
    assert query['response'] == 'VICIIBorderMode=0\n(C:$01ac) '
    out = BASE / 'viewport-probe-01'
    assert not out.exists()
    results, pixels = [], []
    for stem, line in [('later-wrap-zero', 0), ('later-wrap-one', 1)]:
        capture = next(row for row in proof['captures'] if row['stem'] == stem)
        path = ROOT / capture['snapshot']['path']
        assert ref(path) == capture['snapshot']
        state = reader.read_extended_snapshot(path, border_mode=0)
        raster = state['raster_hardware_extension']['raster_store']
        assert raster['current_line'] == capture['registers']['line'] == line
        assert capture['registers']['cycle'] == 2
        full = reader.framebuffer_bytes(path)
        viewport = full[16 * 384:288 * 384]
        assert len(viewport) == 104448
        results.append(dict(stem=stem, snapshot=capture['snapshot'], clock=capture['registers']['clock'],
                            raster=line, cycle=2, schema=raster, viewport_sha256=sha(viewport)))
        pixels.append(viewport)
    assert results[1]['clock'] - results[0]['clock'] == 63
    assert pixels[0] == pixels[1]
    out.mkdir()
    outputs = []
    for result, viewport in zip(results, pixels):
        path = out / (result['stem'] + '-viewport-384x272.bin')
        path.write_bytes(viewport)
        outputs.append(ref(path))
    report = dict(pass_=True, classification='Native retained-viewport extraction only; not an independent pixel prediction.',
        inputs=[ref(ROOT / name) for name in PINS], producer=ref(Path(__file__)),
        captures=results, outputs=outputs, identical_palette_indices=104448,
        preceding_field_generations=1, same_field_observations=2, elapsed_cycles=63,
        limits=['Raster rows16..287 only; current row0/1 and other allocation rows are outside the viewport.',
                'Two identical retained oracles do not prove a renderer, physical output, animation cadence or FPS.',
                'Source-derived glyph values and fetch/color composition still require a separate model.'])
    (out / 'viewport-probe.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'report': ref(out / 'viewport-probe.json'), 'outputs': outputs}))


if __name__ == '__main__':
    main()
