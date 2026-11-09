#!/usr/bin/env python3
"""Retained original part08 machine-state custody; no CPU or VIC execution."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-cells-20261109/context-analysis'
NATIVE = ROOT / 'build/research/aloft-20261109/native-analysis/accepted-01/native-proof.json'
NATIVE_SHA = '02243d0cbae68edad8aa5a51aec9e22e9cfa4c52f918f1ba30db9e5226b19eb4'
COLOR = ROOT / 'build/research/aloft-decode-20261109/color-analysis/accepted-01/color-stream-proof.json'
COLOR_SHA = '44bbc6a94b22db33d81dc9f15178f1303a2db19fb22484292e0c6f894f00f4b2'
ASSOCIATION = ROOT / 'build/research/aloft-decode-20261109/effect-analysis/accepted-01/effect-binding-proof.json'
ASSOCIATION_SHA = '882027ffe37e5651ec2c18ea7a3e511824d10f5d15da264c73b855fb6769c5ce'
READER = ROOT / 'research/quondam/snapshot_state.py'
READER_SHA = 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a'
VICE = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
VICE_SHA = '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'
STEMS = [('part08-entry', 0x0890, 129591314),
         ('part08-body', 0xf02b, 130163026),
         ('part08-frame01', 0xf080, 131462237)]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def checked(path, digest):
    raw = path.read_bytes()
    assert sha(raw) == digest, path
    return raw


def checked_ref(row):
    path = (ROOT / row['path']).resolve()
    path.relative_to(ROOT)
    assert meta(path) == row, path
    return path.read_bytes()


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def source_context():
    """Bind original code before opening retained native states."""
    color = json.loads(checked(COLOR, COLOR_SHA))
    assert color['pass_'] and color['all_initial_RAM_and_device_low_bits_unknown']
    assert color['native_values_never_inputs'] and color['completed_bundle_count'] == 43
    folder = COLOR.parent
    outputs = {row['name']: row for row in color['outputs']}
    files, values = [], {}
    for suffix in ['memory', 'known-mask', 'cumulative-write-mask']:
        name = f'bundle031-{suffix}.bin'
        row = outputs[name]
        path = folder / name
        assert path.stat().st_size == row['bytes'] == 65536
        values[suffix] = checked(path, row['sha256'])
        files.append(meta(path))
    original, known, written = [values[key] for key in ['memory', 'known-mask', 'cumulative-write-mask']]
    assert all(known[pc] == written[pc] == 1 for pc in range(0xf000, 0xf840))
    assert original[0xf080:0xf08e] == bytes.fromhex('c6008d2bf1a91e38ed06dc8d8ff0')
    assert original[0xf0a3:0xf0b1] == bytes.fromhex('a9188d11d0486848684868200005')
    assert original[0xf0b1:0xf0bf] == bytes.fromhex('a2f8ec12d0d0fba9108d11d0a9ff')
    association = json.loads(checked(ASSOCIATION, ASSOCIATION_SHA))
    assert association['pass_'] and len(association['matched_window_names']) == 23
    selected = next(row for row in association['later_source_associations']
                    if row['name'] == 'part08-F000-window')
    assert selected['first'] == 0xf000 and selected['end_exclusive'] == 0xf840
    assert selected['first_matching_complete_source_bundle'] == 31
    return original, files


def primary(output):
    checked(VICE, VICE_SHA)
    anchors = []
    with tarfile.open(VICE) as archive:
        for member, ranges in {
            'vice-3.10/src/core/ciacore.c': [(799, 811)],
            'vice-3.10/src/c64/c64cia2.c': [(136, 155)],
            'vice-3.10/src/c64/c64gluelogic.c': [(86, 107), (169, 197)],
            'vice-3.10/src/viciisc/vicii-mem.c': [(491, 512), (603, 609), (627, 643)],
        }.items():
            raw = archive.extractfile(member).read()
            lines = raw.decode().splitlines(keepends=True)
            for first, end in ranges:
                fragment = ''.join(lines[first-1:end])
                anchors.append(dict(member=member, member_sha256=sha(raw), first_line=first,
                    last_line=end, text=fragment, fragment_sha256=sha(fragment.encode())))
    assert 'CIA_PRA] | ~(cia_context->c_cia[CIA_DDRA])' in anchors[0]['text']
    assert 'new_vbank = tmp & 3;' in anchors[1]['text']
    assert 'old_vbank = vbank;' in anchors[2]['text']
    assert 'SMW_B(m, (uint8_t)old_vbank)' in anchors[3]['text']
    assert '(vicii.regs[addr] & 0x7f) | ((tmp & 0x100) >> 1)' in anchors[4]['text']
    assert 'vicii.regs[addr] | 0xc0' in anchors[6]['text']
    assert 'vicii.regs[addr] | 0x1' in anchors[6]['text']
    write(output / 'primary-context-source.json', dict(archive=meta(VICE), anchors=anchors,
        logical_bank_rule='(~(PRA | ~DDRA)) & 3; all byte complements masked to8bits',
        D011_same_stop_peek_rule='(stored&0x7F)|((VIC_raster_line&0x100)>>1)',
        limits=['Logical bank pins and stopped snapshots are not a timed physical-fetch history.',
                'No GLUE transition, VIC cached-fetch evolution, CPU bus read or RMW sequence is simulated.']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    output = parser.parse_args().output.resolve()
    output.relative_to(BASE)
    assert not output.exists(), output
    original, source_files = source_context()
    checked(READER, READER_SHA)
    spec = importlib.util.spec_from_file_location('frozen_original_vsf_reader', READER)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    proof = json.loads(checked(NATIVE, NATIVE_SHA))
    assert proof['pass_']
    captures = {row['stem']: row for row in proof['captures']}
    output.mkdir(parents=True)
    (output / 'context.checked.py').write_bytes(Path(__file__).read_bytes())
    primary(output)
    machine, inputs, declarations = [], [meta(NATIVE), meta(COLOR), meta(ASSOCIATION),
        meta(READER), meta(VICE)] + source_files, []
    for stem, expected_pc, expected_clock in STEMS:
        item = captures[stem]
        memory = checked_ref(item['ram'])
        checked_ref(item['snapshot'])
        snapshot = ROOT / item['snapshot']['path']
        state = reader.read_snapshot(snapshot)
        cpu = reader.module_payload(snapshot, 'MAINCPU')
        mem = reader.module_payload(snapshot, 'C64MEM')
        assert state['modules']['MAINCPU']['version'] == [1, 4] and len(cpu) == 103
        assert state['modules']['C64MEM']['version'] == [0, 1] and len(mem) == 65555
        assert len(memory) == 65536 and memory == mem[4:65540]
        regs = item['registers']
        pc, clock = int.from_bytes(cpu[12:14], 'little'), int.from_bytes(cpu[:8], 'little')
        assert (pc, clock) == (expected_pc, expected_clock) == (regs['pc'], regs['clock'])
        assert [cpu[index] for index in (8,9,10,11,14)] == [regs[key] for key in ('a','x','y','sp','flags')]
        assert item['stop']['natural'] and item['all65536_physical_RAM_bytes_equal']
        assert item['CPU_clock_flags_and_ports_equal']
        assert mem[1] == mem[65542] == regs['port00'] == 0x2f
        assert mem[65541] == regs['port01'] == 0x35
        assert mem[0] & mem[1] == mem[65541] & mem[1]
        vic, cia = state['vicii'], state['cia']['CIA2']
        assert [vic['raster_line'], vic['raster_cycle']] == [regs['line'], regs['cycle']]
        assert [clock // 63 % 312, clock % 63] == [regs['line'], regs['cycle']]
        assert vic['model'] == 1 and vic['regs'] == item['current_VIC_registers']
        assert cia == item['CIA2']
        glue = reader.module_payload(snapshot, 'GLUE')
        assert state['modules']['GLUE']['version'] == [1, 0] and glue == bytes.fromhex('010000')
        pins = (cia['pra'] | (~cia['ddra'] & 255)) & 255
        bank = (~pins) & 3
        assert cia['ddra'] == 0x3c and bank == glue[1] == 0 and glue[2] == 0
        assert vic['regs'][0x15] == 0
        changes = [dict(address=i, original=original[i], observed=memory[i])
                   for i in range(0xf000,0xf840) if original[i] != memory[i]]
        if stem == 'part08-entry':
            assert changes == []
        role = {'part08-entry': 'Before wrapper JSRF000, original source generation.',
                'part08-body': 'Before F02B IRQ setup; initialized cells exist, but not a pre0500 state.',
                'part08-frame01': 'Before observed IRQF080, not first-frame or pre0500 proof.'}[stem]
        machine.append(dict(stem=stem, role=role, ram=item['ram'], snapshot=item['snapshot'],
            registers=regs, port=dict(DDR=mem[1], latch=mem[0], read=mem[65541]),
            source_window_changes=changes, source_window_changes_are_observations_not_patch_normalization=True,
            stopped_device_context=dict(VIC_registers_stored=vic['regs'],
                D011_side_effect_free_peek=(vic['regs'][0x11]&0x7f)|((vic['raster_line']&256)>>1),
                D016_side_effect_free_peek=vic['regs'][0x16]|0xc0,
                D018_side_effect_free_peek=vic['regs'][0x18]|1,
                CIA2_PRA=cia['pra'], CIA2_DDRA=cia['ddra'], CIA2_logical_effective_pins=pins,
                CIA2_logical_bank=bank, GLUE_type=glue[0], GLUE_previous_bank=glue[1],
                GLUE_alarm_active=glue[2]),
            frozen_reader_state={key:value for key,value in state.items() if key!='file'},
            source_full2112bytes_bound_only_at_entry=(stem=='part08-entry')))
        zero = list(memory[:256])
        cpu_view = zero.copy()
        cpu_view[0],cpu_view[1] = regs['port00'],regs['port01']
        calls = []
        if stem != 'part08-entry':
            for index in range(200):
                pc_call = 0x500 + 3*index
                assert memory[pc_call] == 0x20
                target = memory[pc_call+1] | (memory[pc_call+2] << 8)
                calls.append(dict(index=index, call_PC=pc_call, target=target))
            assert memory[0x758] == 0x60
        declarations.append(dict(stem=stem, pc=pc, clock=clock, role=role,
            physical_RAM_ZP=zero, CPU_read_ZP_at_same_stop=cpu_view,
            actual_RAM_lookup0400=list(memory[0x400:0x500]),
            actual_call_targets0500=calls,
            call_targets_role='Declared observed motion/dispatch input, distinct from the2000/2023cell-body output oracle. No initial-generation or evolution claim.',
            actual_clock_increment_operands=[memory[0x801],memory[0x805]],
            warning='These are measured entry inputs, not independently predicted initialization or post-cell oracles. Apply the intervening exact source prefix before using as a later cell prestate. Port0/1 reads are device values, not underlying RAM.'))
        inputs.extend([item['ram'],item['snapshot']])
    write(output / 'machine-context.json',dict(pass_=True,captures=machine))
    write(output / 'declared-entry-inputs.json',dict(pass_=True,captures=declarations,
        no_native_2000_or2023_cell_body_bytes_are_exposed_as_prediction_inputs=True))
    outputs=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
             for p in sorted(output.iterdir()) if p.is_file()]
    write(output / 'context-proof.json',dict(pass_=True,producer=meta(Path(__file__)),inputs=inputs,
        scope='Three retained native entry-state/port/VIC/GLUE contexts, not a new native case or raster simulation.',
        source_prediction_pinned_before_native_reads=True,captures=3,full_RAM_bytes_compared=196608,
        every_pair_CPU_port_clock_beam_equal=True,source_code_bytes_equal_entry=2112,
        both_CIA2_bank_select_bits_are_inputs=True,all_stopped_logical_banks_zero=True,
        all_stopped_GLUE_alarm_flags_clear=True,all_stopped_sprite_enable_zero=True,
        no_CPU_native_VIC_or_downloaded_host_execution=True,outputs=outputs,
        limits=['A stopped mode is not a full-field mode or complete physical-fetch history.',
            'Pre-F02B and pre-F080 are different entry inputs; neither alone is a pre0500 state.',
            'frame01 is a capture alias, not proof of the first displayed animation frame.',
            'Underlying RAM and ColorRAM/CPU ports remain separate.',
            'Copied lookup/ZP values are declared observed inputs, not an independent initializer prediction.',
            'No timing, pixels, animation cadence or named layered-scene identity is established.']))
    print(json.dumps(meta(output / 'context-proof.json')))


if __name__ == '__main__':
    main()
