#!/usr/bin/env python3
"""Passive closed-case custody for original packed Perpetual Fragility.

The worker performs no native/process/socket/CPU/build action. Acceptance is
closed until the owner supplies an authoritative terminal profile and pins.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/perpetual-20261109'
ANALYSIS = BASE / 'native-analysis'
PACKED = ROOT / 'build/research/aloft-pixels-20261109/reading-analysis/acquisition-01/perpetual-prg.prg'
PACKED_SHA = '9770854332c3a60bb25eaa580d91e47f5d98ff6d47c7b6fdfec1a60b82e985df'
PREDICTION_BASE = ROOT / 'build/research/aloft-motion-20261109/primary-analysis/accepted-01'
PREDICTION_SHA = '37327f79e5fd255b78d4c7754e561c40135ce35076ee5ff2d6b7e6fcf5f307ea'
WIRE = ROOT / 'research/verify_vice_live.py'
WIRE_SHA = 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a'
CONTROLLER = ROOT / 'research/eod/controller.py'
CONTROLLER_SHA = '033bafb6ac6e97283175ac6713af0eef60cb7991b653ee1c98c47a1a4afa83c9'
READER = ROOT / 'research/quondam/snapshot_state.py'
READER_SHA = 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a'
CLOSED_PROFILE = None
CLOSED_PROFILE_SHA = None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(path, digest):
    raw = path.read_bytes()
    assert sha(raw) == digest, str(path)
    return raw


def meta(path):
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=sha(raw))


def checked_ref(ref):
    raw = pinned(ROOT / ref['path'], ref['sha256'])
    assert len(raw) == ref['bytes']
    return raw


def load(name, path, digest):
    pinned(path, digest)
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def function_source(path, name):
    text = path.read_text()
    nodes = [n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(nodes) == 1
    return ast.get_source_segment(text, nodes[0]) + '\n'


def source_prediction():
    """Pin source-only predictions before opening any native capture file."""
    path = PREDICTION_BASE / 'primary-proof.json'
    proof = json.loads(pinned(path, PREDICTION_SHA))
    assert proof['pass_'] is True and proof['Perpetual_Fragility']['pass_'] is True
    outputs = {row['name']: row for row in proof['outputs']}
    def output(name):
        row = outputs[name]
        raw = pinned(PREDICTION_BASE / name, row['sha256'])
        assert len(raw) == row['bytes']
        return raw
    memory = output('perpetual-predicted-memory.bin')
    known = output('perpetual-predicted-known.bin')
    unpacked = output('perpetual-unpacked.prg')
    packed = pinned(PACKED, PACKED_SHA)
    assert len(packed) == 9469 and packed[:2] == bytes.fromhex('0108')
    assert packed[14:29] == bytes.fromhex('a035babd042c9dfc00cad0f74cb42b')
    assert len(memory) == len(known) == 65536
    assert sum(bool(x) for x in known) == 17403
    assert [i for i, x in enumerate(known) if x] == list(range(0x801, 0x4bfc))
    assert unpacked == bytes.fromhex('0108') + memory[0x801:0x4bfc]
    assert memory[0x80d:0x817] == bytes.fromhex('a97f8d0ddc78a9358501')
    return packed, memory, known, dict(proof=meta(path), original_packed_PRG=meta(PACKED),
        memory=meta(PREDICTION_BASE/'perpetual-predicted-memory.bin'),
        known_mask=meta(PREDICTION_BASE/'perpetual-predicted-known.bin'),
        unpacked_PRG=meta(PREDICTION_BASE/'perpetual-unpacked.prg'),
        source_prediction_frozen_before_case=True)


def closed_inventory(profile):
    assert profile['owner_closed'] is True and profile['owned_process_reaped'] is True
    assert profile['unified_handle_terminal'] is True
    case = (ROOT / profile['case_relative']).resolve()
    case.relative_to(BASE)
    manifest = json.loads(checked_ref(profile['manifest']))
    rows = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
            for p in sorted(case.iterdir()) if p.is_file()]
    assert rows == manifest['files']
    assert len(rows) == manifest['file_count'] == profile['file_count']
    assert sum(r['bytes'] for r in rows) == manifest['bytes'] == profile['case_bytes']
    canonical = sha(json.dumps(rows,sort_keys=True,separators=(',',':')).encode())
    assert canonical == profile['canonical_listing_sha256']
    return case, rows


def audit_wire(profile, case_path):
    wire = load('perpetual_frozen_wire', WIRE, WIRE_SHA)
    wire.BASE = case_path.parent
    wire.CASE_PINS = {case_path.name: profile['canonical_listing_sha256']}
    original = function_source(WIRE, 'audit_session')
    old = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    replacement = ('assert session["startup_mode"] == "autostart"\n'
        '    assert session["program"] == ' + repr(str(PACKED.resolve())) + '\n'
        '    assert session["command"].count("-autostart") == 1\n'
        '    assert session["command"][session["command"].index("-autostart")+1] == ' + repr(str(PACKED.resolve())) + '\n'
        '    assert "-8" not in session["command"]\n'
        '    assert session["command"].count("-autostartprgmode") == 1\n'
        '    assert session["command"][session["command"].index("-autostartprgmode")+1] == "1"')
    assert original.count(old) == 1
    adapted = original.replace(old, replacement)
    exec(compile(adapted,'<Perpetual-original-autostart-PRG-only-adapter>','exec'),wire.__dict__)
    case = wire.audit_session(case_path.name)
    return wire, case, dict(original_function_sha256=sha(original.encode()),
        adapted_function_sha256=sha(adapted.encode()), replacements=1,
        exact_old_assertion=old, exact_PRG_replacement=replacement,
        ordinary_register_and_raw_event_readers_unchanged=True,
        no_D64_or_explicit_drive8_attachment=True)


def paired_captures(wire, case, case_path):
    controller = load('perpetual_frozen_pairs', CONTROLLER, CONTROLLER_SHA)
    controller.CASE = case_path
    reader = load('perpetual_frozen_snapshot', READER, READER_SHA)
    memories, captures = controller.capture_pairs(reader, wire, case)
    return reader, memories, captures, dict(frozen_capture_pairs_unchanged=True,
        CPU_DDR_2F_precondition_not_relaxed=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    assert CLOSED_PROFILE is not None and CLOSED_PROFILE_SHA is not None, 'owner closure/profile pins pending'
    profile = json.loads(pinned(CLOSED_PROFILE, CLOSED_PROFILE_SHA))
    assert profile['owner_closed'] is True
    out = (ROOT / args.output).resolve()
    out.relative_to(ANALYSIS)
    assert not out.exists(), 'fresh output required'
    packed, prediction, known, prediction_meta = source_prediction()
    case_path, listing = closed_inventory(profile)
    wire, case, startup_adapter = audit_wire(profile,case_path)
    reader, memories, captures, pair_adapter = paired_captures(wire,case,case_path)
    raise AssertionError('closed role/sequence/renderer map pending; no accepted receipt is emitted')


if __name__ == '__main__':
    main()
