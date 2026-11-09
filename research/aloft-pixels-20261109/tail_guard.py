#!/usr/bin/env python3
"""Prove the original read-only wait protects the final row's remaining fetches.

Finite source and interval checks only. No CPU instruction interpreter,
native control, pixel oracle or expected glyph-value input is used.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-pixels-20261109/tail-analysis'
PINS = {
    'build/research/aloft-decode-20261109/color-analysis/accepted-01/bundle031-memory.bin': '95a344b261b1b28d229da9778df80bae06eff39470ff4515820ce4e1fa86869e',
    'build/research/aloft-execution-20261109/native-analysis/accepted-02/native-proof.json': '5db9694db276541a5fd2b5cb386e92639e6da2c0d6cd644caf758eb113cc2326',
    'build/research/aloft-execution-20261109/cell-analysis/accepted-01/cell-execution-proof.json': 'b3bf0ae5e74059bc17b29717174587bb679bfe3701a388dad0f9a3d88b8ebdf5',
    'build/research/aloft-execution-20261109/fetch-analysis/binding-accepted-01/fetch-binding-proof.json': '31efa766ff16b02d04c834ba107c40c868d0124fb4c0ea2e499e5b6f6644916c',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def ref(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def checked(row):
    path = ROOT / row['path']
    raw = path.read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256'], row['path']
    return raw


def exported(proof, directory, name):
    row = next(row for row in proof['outputs'] if row['name'] == name)
    return checked(dict(path=str((directory / name).relative_to(ROOT)),
                        bytes=row['bytes'], sha256=row['sha256']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to(BASE)
    assert not out.exists()
    raw = {}
    for name, expected in PINS.items():
        value = (ROOT / name).read_bytes()
        assert sha(value) == expected, name
        raw[name] = value
    names = list(PINS)
    source = raw[names[0]]
    native, model, fetch = [json.loads(raw[name]) for name in names[1:]]
    assert native['pass_'] and model['pass_'] and fetch['pass_']
    assert fetch['per_field_logical_graphics_requests'] == 8000
    # These are complete instructions, not an arbitrary matching byte window.
    wait = bytes.fromhex('a2f8ec12d0d0fb')
    assert source[0xf0b1:0xf0b8] == wait
    # LDX#F8; CPX $D012; BNE $F0B3. Fallthrough starts the later D011 change.
    assert source[0xf0b8:0xf0bf] == bytes.fromhex('a9108d11d0a9ff')
    descriptors = [dict(PC=0xf0b1, opcode='LDX immediate', bytes='a2f8', memory_writes=[]),
                   dict(PC=0xf0b3, opcode='CPX absolute', bytes='ec12d0', read_address=0xd012, memory_writes=[]),
                   dict(PC=0xf0b6, opcode='BNE relative', bytes='d0fb',
                        taken_PC=0xf0b3, fallthrough_PC=0xf0b8, memory_writes=[])]
    inputs = json.loads(exported(native, ROOT / Path(names[1]).parent, 'independent-inputs.json'))
    captures = {row['stem']: row for row in native['captures']}
    guards, expected = [], []
    for field in inputs['fields']:
        label, initial, roles = field['label'], field['input'], field['roles']
        entry = initial['initial_CPU']
        assert entry['pc'] == 0x500 and entry['flags'] & 4
        # Only code bytes are taken from the genuine input's RAM export.
        memory = checked(initial['capture']['ram'])
        assert memory[0xf0b1:0xf0bf] == source[0xf0b1:0xf0bf]
        first_row = entry['clock'] // 63 + 1
        final_g_clock = (first_row + 199) * 63 + 54
        return_clock = entry['clock'] + 12606
        assert return_clock < final_g_clock
        expected.append(dict(label=label, roles=roles,
            source_guard_bytes=source[0xf0b1:0xf0bf].hex(), genuine_input=initial['capture'],
            post_dispatcher_return_PC=0xf0b1, predicted_return_clock=return_clock,
            last_logical_graphics_clock=final_g_clock,
            tail_admitted_PC_domain=[0xf0b1, 0xf0b3, 0xf0b6], first_fallthrough_PC=0xf0b8,
            admitted_tail_memory_write_set=[],
            glyph_values_remain_unchanged_until_first_fallthrough=True,
            assumptions=['No unmodeled external NMI/control diversion or RAM-writing DMA.',
                         'Captured CPU mapping remains in force.',
                         'No snapshot restore, reset, PC/RAM patch or restart.'],
            pixel_values_or_final_glyph_RAM_consumed=False))
    out.mkdir(parents=True)
    checked_source = out / 'tail_guard.checked.py'
    checked_source.write_bytes(Path(__file__).read_bytes())
    prediction = out / 'tail-predictions.json'
    prediction.write_text(json.dumps(dict(source_instructions=descriptors, fields=expected), indent=2) + '\n')
    # Source/interval predictions above exist before these endpoint/trace checks.
    hooks = json.loads(exported(native, ROOT / Path(names[1]).parent, 'hook-oracles.json'))['all_hooks']
    comparisons = []
    for row in expected:
        roles = row['roles']
        before, after = captures[roles['post_all']], captures[roles['after_line']]
        a, b = before['registers'], after['registers']
        assert a['pc'] == 0xf0b1 and a['clock'] == row['predicted_return_clock']
        assert b['pc'] == 0xf0b8 and b['clock'] > row['last_logical_graphics_clock']
        assert a['flags'] & 4 and b['flags'] & 4
        assert (a['line'], a['cycle'], b['line'], b['cycle']) == (247, 30, 248, 3)
        for capture in (before, after):
            memory = checked(capture['ram'])
            assert memory[0xf0b1:0xf0bf] == source[0xf0b1:0xf0bf]
            guards.append(dict(stem=capture['stem'], code_bytes_equal_original=True,
                               ram=capture['ram']))
        middle = [hit for hit in hooks if a['clock'] < hit['registers']['clock'] <= b['clock']]
        assert middle == [], 'Unexpected watched activity in the original read-only wait'
        comparisons.append(dict(label=row['label'], before=before, after=after,
            last_graphics_precedes_wait_fallthrough=True,
            no_reported_hook_during_wait=True, source_memory_write_set_empty=True))
    result = dict(pass_=True, producer=ref(Path(__file__)), inputs=[ref(ROOT / name) for name in PINS],
        prediction_written_before_endpoint_and_hook_evaluation=True,
        predictions=dict(name=prediction.name, bytes=prediction.stat().st_size,
                         sha256=sha(prediction.read_bytes())),
        outputs=[dict(name=path.name, bytes=path.stat().st_size, sha256=sha(path.read_bytes()))
                 for path in (prediction, checked_source)],
        comparisons=comparisons, captured_code_guards=guards,
        scope='Two original source-admitted waits protect the remaining final-row logical graphics requests after dispatcher return.',
        actual_wait_bus_read_timestamps_predicted=False,
        fetched_bytes_or_pixels_predicted=False,
        no_CPU_native_or_downloaded_host_execution=True,
        limits=['Conditional source closure retains external NMI/DMA/mapping assumptions.',
                'The natural fallthrough is an observed deadline, not an independently timed CPX operand read.',
                'Protection ends at F0B8; later D011 changes, glyph reset, music and field tail need separate treatment.'])
    path = out / 'tail-guard-proof.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(ref(path)))


if __name__ == '__main__':
    main()
