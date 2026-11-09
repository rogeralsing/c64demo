#!/usr/bin/env python3
"""Passive B17 endpoint context for two frozen strip-selection functions."""
import argparse
import hashlib
import importlib.machinery
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/the-hat'
PINS = {
    'build/research/the-hat/native-analysis/accepted-02/native-proof.json':
        '726b76be1f9560ff22697129c1de788da82e95beac7a3993fdc4ba498082e141',
    'build/research/the-hat/ending-analysis/accepted-02/ending-proof.json':
        '94fb63d5c8fc9ccecf7b595b3cd75973ee3c2ce36b222acb4d49d5f8f2ea030e',
    'build/research/the-hat/ending-analysis/accepted-02/ending.checked.py':
        '4cc8e89f7f324c64bff103bd1821e2d901857aba12ba4a4416fb7d911ddf6f4c',
    'build/research/the-hat/dali-analysis/accepted-03/b17-2000.bin':
        'fb41ff61943ba509b4cae952b50f48643006550633a0a181603565834aecaa72',
}
FIELDS = (
    ('direction', 0x34fe, 1), ('phase', 0x3501, 1), ('index', 0x3502, 1),
    ('selected', 0x3503, 8), ('xlow', 0x350b, 8),
    ('xhigh_mask', 0x3513, 1), ('render_selected', 0x3514, 8),
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def checked(record):
    path = ROOT / record['path']
    assert meta(path) == record, record['path']
    return path.read_bytes()


def frozen_functions(path):
    # This is our pinned passive source model, not a downloaded tool or CPU model.
    loader = importlib.machinery.SourceFileLoader('hat_ending_frozen', str(path))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module.source_selection, module.reference_selection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    out = args.output.resolve()
    assert not out.exists(), 'Use a fresh output directory; preserve prior results.'
    assert out.is_relative_to(BASE / 'ending-context-analysis')
    inputs = []
    for name, expected in PINS.items():
        record = meta(ROOT / name)
        assert record['sha256'] == expected, name
        inputs.append(record)
    native = json.loads((ROOT / next(iter(PINS))).read_text())
    static = json.loads((BASE / 'ending-analysis/accepted-02/ending-proof.json').read_text())
    assert native['pass_'] and static['pass_']
    assert static['producer']['sha256'] == PINS[
        'build/research/the-hat/ending-analysis/accepted-02/ending.checked.py']
    assert static['selection_domain']['comparisons'] == 22656
    payload = (BASE / 'dali-analysis/accepted-03/b17-2000.bin').read_bytes()
    assert len(payload) == 26402
    original = bytearray(65536)
    original[0x2000:0x2000 + len(payload)] = payload
    blank = list(original[0x336c:0x33ec])
    assert len(blank) == 128 and blank.count(1) == 80 and blank.count(0) == 48

    captures = {}
    memories = {}
    expected_pcs = {'b17-controller': 0x8000, 'b17-cutoff': 0x831b,
                    'b17-stack-restored': 0x831f, 'b17-complete': 0x8040}
    for stem, pc in expected_pcs.items():
        record, = [c for c in native['captures'] if c['stem'] == stem]
        assert record['registers']['pc'] == pc
        assert record['observed_stop_kind'] == 'natural exec breakpoint'
        assert not record['not_a_natural_phase_stop']
        assert record['all65536_physical_RAM_bytes_equal']
        assert record['CPU_clock_flags_and_beam_equal']
        ram = checked(record['ram'])
        checked(record['snapshot'])
        assert len(ram) == 65536
        captures[stem] = record
        memories[stem] = ram
    assert memories['b17-controller'][0x2000:0x8722] == payload
    guards = []
    for stem in ('b17-cutoff', 'b17-stack-restored', 'b17-complete'):
        ram = memories[stem]
        for first, end, purpose in ((0x3231, 0x3368, 'Frozen helper code'),
                                    (0x336c, 0x33ec, 'Original blank-strip flags'),
                                    (0x831b, 0x8329, 'Cutoff and stack-restore code')):
            expected = bytes(original[first:end])
            assert ram[first:end] == expected, (stem, hex(first))
            guards.append(dict(capture=stem, first=first, end_exclusive=end,
                               purpose=purpose, bytes=len(expected),
                               sha256=sha(expected), all_bytes_equal=True))

    before = memories['b17-cutoff']
    restored = memories['b17-stack-restored']
    finished = memories['b17-complete']
    br = captures['b17-cutoff']['registers']
    sr = captures['b17-stack-restored']['registers']
    er = captures['b17-complete']['registers']
    assert before == restored
    assert before[0x831b:0x831f] == bytes.fromhex('ae1a839a')
    assert before[0x831a] == sr['sp'] == 0x59 and br['sp'] == 0x56
    assert sr['clock'] - br['clock'] == 6
    assert er['clock'] > sr['clock']

    model_inputs = dict(phase=before[0x3501], index=before[0x3502],
                        direction=before[0x34fe], previous=list(before[0x3503:0x350b]),
                        blank=blank, speed=before[0x34fd])
    assert [model_inputs[k] for k in ('phase', 'index', 'direction', 'speed')] == [24, 51, 0, 4]
    source_selection, reference_selection = frozen_functions(
        BASE / 'ending-analysis/accepted-02/ending.checked.py')
    prediction = source_selection(**model_inputs)
    reference = reference_selection(**model_inputs)
    assert prediction == reference
    comparisons = []
    predicted_bytes = bytearray()
    for field, first, count in FIELDS:
        value = prediction[field]
        expected = bytes([value]) if count == 1 else bytes(value)
        assert len(expected) == count
        actual = finished[first:first + count]  # Oracle only, never model input.
        assert expected == actual, field
        predicted_bytes.extend(expected)
        comparisons.append(dict(field=field, first=first, bytes=count,
                                predicted=list(expected), actual=list(actual), all_equal=True))
    assert len(predicted_bytes) == 28
    assert finished[0x34fd] == before[0x34fd] == 4

    out.mkdir(parents=True)
    (out / 'selection-state.bin').write_bytes(predicted_bytes)
    (out / 'ending_context.checked.py').write_bytes(Path(__file__).read_bytes())
    outputs = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
               for p in sorted(out.iterdir())]
    proof = dict(
        pass_=True,
        scope='One captured original B17 cutoff-to-controller selection-state transition, compatible with one frozen helper update; no complete raster execution or display claim',
        producer=meta(Path(__file__).resolve()), inputs=inputs,
        custody='Natural stops, RAM/VSF equality, clock/beam/port concordance and original A-to-B load lineage are consumed from the pinned native01 acceptance; no wire audit is duplicated.',
        captures=list(captures.values()),
        original_B17_entry=dict(first=0x2000, end_exclusive=0x8722,
                                bytes=len(payload), sha256=sha(payload), all_bytes_equal=True),
        source_guards=guards,
        stack_restore=dict(first_pc=br['pc'], post_pc=sr['pc'], before_SP=br['sp'],
                           after_SP=sr['sp'], saved_SP=before[0x831a],
                           elapsed_cycles=sr['clock']-br['clock'], all65536_RAM_bytes_equal=True),
        input_state=dict(phase=model_inputs['phase'], index=model_inputs['index'],
                         direction=model_inputs['direction'], speed=model_inputs['speed'],
                         previous=model_inputs['previous'],
                         blank_source=dict(first=0x336c, bytes=128,
                                           sha256=sha(bytes(blank)), blank=80, nonblank=48)),
        prediction=prediction, independent_signed_reference=reference,
        two_models_equal=True, comparison_fields=comparisons, all28_state_bytes_equal=True,
        speed_input_preserved=True,
        observation_clocks=dict(cutoff=br['clock'], post_stack=sr['clock'], complete=er['clock'],
                                cutoff_to_complete_elapsed=er['clock']-br['clock']),
        outputs=outputs,
        limits=[
            'The completed RAM is an equality oracle only. Both predictions consume cutoff state and original decoded blank flags.',
            'The endpoint pair is compatible with one helper update; no trace here establishes its exact call count or precise entry/return clocks.',
            'The 1808 elapsed cutoff-to-controller cycles include work outside the selection helper and are not its measured cost.',
            'No full raster-body execution, VIC coordinate/pointer/DMA history, palette or committed pixels is reconstructed.',
            'B17 is the separate horizontal closing-logo carpet, not the B8/B9 vertical text upscroller.',
            'No native process, CPU interpreter, build, downloaded host tool, source mutation or shared-index edit is performed.',
        ])
    raw = (json.dumps(proof, indent=2) + '\n').encode()
    (out / 'ending-context-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True, receipt_bytes=len(raw), receipt_sha256=sha(raw),
                          compared_state_bytes=28, prediction=prediction), indent=2))


if __name__ == '__main__':
    main()
