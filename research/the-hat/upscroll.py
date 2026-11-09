#!/usr/bin/env python3
"""Source-bound finite scheduling checks for The Hat's B8/B9 upscroll.

No CPU interpreter, subprocess, native control or downloaded execution.
The finite write stencil is an explicit vector transformation, not a machine.
"""
import argparse
import hashlib
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
INPUT = ROOT / 'build/research/the-hat/dali-analysis/neighbor-probe-02/accepted-01'
VICE = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def meta(path):
    path = path.resolve()
    b = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(b), 'sha256': digest(b)}


def outmeta(path):
    b = path.read_bytes()
    return {'name': path.name, 'bytes': len(b), 'sha256': digest(b)}


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')
    return outmeta(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).resolve()
    (args.output / 'upscroll.checked.py').write_bytes(source.read_bytes())
    pins = {
        INPUT / 'source-classification.json': '838ed0bd5534acce676b06528f4c311adbccc8f1fc62462d5b68abfe628dcb8f',
        INPUT / 'b08.bin': '5c8150c48068c62f8a77d8c97b18de33360dcb03046e0f5e9ffcb01ca6704ba6',
        INPUT / 'b09.bin': '9d0f80b7bc33c981a7befe2274ac98f30bf00c77916702016588b5e028e9a578',
        VICE: '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
    }
    for path, expected in pins.items():
        assert digest(path.read_bytes()) == expected
    b8 = (INPUT / 'b08.bin').read_bytes()
    b9 = (INPUT / 'b09.bin').read_bytes()

    def read8(address, length=1):
        assert 0x4000 <= address <= address + length <= 0xD000
        return b8[address - 0x4000:address - 0x4000 + length]

    def read9(address, length=1):
        assert 0xE000 <= address <= address + length <= 0xF800
        return b9[address - 0xE000:address - 0xE000 + length]

    guards = []
    for address, h, role in [
        (0x819D, 'AD7D818D01D08D03D08D05D08D07D08D09D08D0BD08D0DD08D0FD0', 'shared sprite Y from motion state'),
        (0x81B8, 'AD7E81186920AA8EF843E88EF943E88EFA43E88EFB43E88EFC43E88EFD43E88EFE43E88EFF43', 'eight initial pointers from phase plus$20'),
        (0x81F3, '2000E0', 'prepared motion controller call'),
        (0x821C, 'AD01D038E9028D12D0AABDCC828D06DCBDCC838D07DC', 'raster Y minus2 and CIA1 timer-B latch tables'),
        (0x8267, 'A9198D0FDCA9FF8D12D08D19D0A98B8D11D0BA8E8B82A98C8DFEFFA9828DFFFF584C1685', 'timer start, saved SP, cutoff vector and raster transfer'),
        (0x828C, 'A9FE8D18D1AD0DDCAE8B829AA9008D15D0', 'mirrored D018, CIA acknowledge, abandoned raster stack'),
        (0x8516, 'ADF8432908F0034CAAA8', 'program parity selection from pointer bit3'),
        (0x8521, 'A9F08D00D0A9288D02D0A9588D04D0A9888D06D0A9B88D08D0A9E88D0AD0A9188D0CD0A9488D0ED0', 'even-program base X coordinates'),
        (0x895D, 'A9008D18D0AC12D1B900F48D7689B900F58D7789', 'mirrored raster read drives even dispatch'),
        (0xA8AA, 'A9F18D00D0A9298D02D0A9598D04D0A9898D06D0A9B98D08D0A9E98D0AD0A9198D0CD0A9498D0ED0', 'odd-program base X coordinates'),
    ]:
        assert read8(address, len(h) // 2) == bytes.fromhex(h)
        guards.append({'asset': 'b08', 'pc': address, 'hex': h, 'role': role})
    for address, h, role in [
        (0xE140, 'A9AE8502A9E18503A97E8504A9E98505A000B1028D7D81B1048D7E81', 'prepared table bases and state writes'),
        (0xE167, 'E602D002E603E604D002E605', 'parallel byte-cursor increment'),
        (0xE173, 'A503C9E8900DD006A502C9B69005A9018D4DE0', 'late-motion fade request'),
        (0xE186, 'A503C9E990C4D006A502C97E90BC', 'motion-table exclusive endpoint'),
    ]:
        assert read9(address, len(h) // 2) == bytes.fromhex(h)
        guards.append({'asset': 'b09', 'pc': address, 'hex': h, 'role': role})

    # All 2000 prepared states, using two independent address formulae.
    y = read9(0xE1AE, 2000)
    phase = read9(0xE97E, 2000)
    assert min(y) == 8 and max(y) == 206
    assert set(phase) == set(range(0, 137, 8))
    states = []
    for index, (yy, pp) in enumerate(zip(y, phase)):
        pointers = [0x20 + pp + sprite for sprite in range(8)]
        source_addresses = [0x4000 + pointer * 64 for pointer in pointers]
        alternate = [0x4800 + (pp // 8) * 512 + sprite * 64 for sprite in range(8)]
        assert source_addresses == alternate
        states.append({'index': index, 'y': yy, 'phase': pp,
                       'pointer_table': [0x43F8, 0x4400], 'pointers': pointers,
                       'sprite_first_byte_addresses_if_bank4000': source_addresses,
                       'kernel': 0xA8DF if pointers[0] & 8 else 0x8556,
                       'source_y_address': 0xE1AE + index,
                       'source_phase_address': 0xE97E + index})
    states_meta = write_json(args.output / 'prepared-state-schedules.json', states)

    # Original latch data, not measured elapsed clocks.
    timer = [read8(0x82CC + x)[0] | read8(0x83CC + x)[0] << 8 for x in range(256)]
    assert all(value == 0x440F - 63 * x for x, value in enumerate(timer))
    latch = [{'motion_index': row['index'], 'irq_low_line': row['y'] - 2,
              'timer_b_latch': timer[row['y'] - 2]} for row in states]
    timer_meta = write_json(args.output / 'timer-latch-schedules.json', {
        'formula': '0x440F - 63*x', 'all_256_table_entries_equal': True,
        'prepared_states': latch, 'not_absolute_irq_clock_predictions': True})

    # Runtime tail dispatch remains conditional on actual raster reads.
    dispatch = []
    expected_targets = [
        {0x8556, 0x8978, 0x8DEC, 0x9261, 0x96D6, 0x9B4B, 0x9FC0, 0xA435},
        {0xA8DF, 0xAD01, 0xB174, 0xB5E9, 0xBA5D, 0xC346},
    ]
    for variant, (low, high) in enumerate([(0xF400, 0xF500), (0xF600, 0xF700)]):
        targets = [read9(low + line)[0] | read9(high + line)[0] << 8 for line in range(256)]
        assert set(targets) == expected_targets[variant]
        for target in targets:
            assert read8(target, 3) == bytes.fromhex('CE16D0')
        dispatch.append({'variant': variant, 'low_table': low, 'high_table': high,
                         'targets_by_raster_low': targets})
    dispatch_meta = write_json(args.output / 'conditional-tail-dispatch.json', dispatch)

    # A closed, regular X-write stencil, with instruction-level final effects.
    # No flags, CPU stack, instruction dispatch or general memory execution.
    stencil_pc = 0x88EF
    descriptors = [('dec_x', 0), ('dec_x', 1), ('dec_x', 2), ('nop', None),
                   ('force_x', 3), ('dec_x', 4), ('dec_x', 5),
                   ('restore_d016', None), ('decrement_d016', None),
                   ('dec_x', 6), ('dec_x', 7),
                   ('inc_x', 0), ('inc_x', 1), ('inc_x', 2), ('inc_x', 3),
                   ('restore_d016', None), ('decrement_d016', None),
                   ('inc_x', 4), ('inc_x', 5), ('inc_x', 6), ('inc_x', 7)]
    encodings = {'dec_x': 0xCE, 'inc_x': 0xEE, 'force_x': 0x8E,
                 'restore_d016': 0x8E, 'decrement_d016': 0xCE}
    cells = []
    pc = stencil_pc
    for kind, sprite in descriptors:
        if kind == 'nop':
            data = bytes([0xEA])
            address = None
        else:
            address = 0xD000 + 2 * sprite if sprite is not None else 0xD016
            data = bytes([encodings[kind], address & 255, address >> 8])
        assert read8(pc, len(data)) == data
        cells.append({'pc': pc, 'kind': kind, 'sprite': sprite, 'address': address,
                      'hex': data.hex().upper()})
        pc += len(data)
    assert pc == 0x892C

    def stencil(values):
        values = list(values)
        d016 = 0xC7
        writes = []
        for cell in cells:
            kind, sprite = cell['kind'], cell['sprite']
            if kind == 'nop':
                continue
            if kind == 'dec_x':
                values[sprite] = (values[sprite] - 1) & 255
                value = values[sprite]
            elif kind == 'inc_x':
                values[sprite] = (values[sprite] + 1) & 255
                value = values[sprite]
            elif kind == 'force_x':
                values[sprite] = value = 0x88
            elif kind == 'restore_d016':
                d016 = value = 0x88
            else:
                assert kind == 'decrement_d016'
                d016 = value = ((d016 | 0xC0) - 1) & 255
            writes.append({'pc': cell['pc'], 'address': cell['address'], 'value': value})
        return values, d016, writes

    initial = [0xF0, 0x28, 0x58, 0x89, 0xB8, 0xE8, 0x18, 0x48]
    final, d016, writes = stencil(initial)
    assert final == initial and d016 == 0xC7 and len(writes) == 20
    checks = 0
    for sprite in range(8):
        if sprite == 3:
            continue
        for value in range(256):
            varied = list(initial)
            varied[sprite] = value
            assert stencil(varied)[0] == varied
            checks += 1
    wrong = list(initial)
    wrong[3] = 0x88
    assert stencil(wrong)[0] != wrong
    stencil_meta = write_json(args.output / 'finite-write-stencil.json', {
        'pc_range': [stencil_pc, pc], 'source_cells': cells,
        'initial_x_low': initial, 'initial_d016': 0xC7, 'final_x_low': final,
        'final_d016': d016, 'instruction_final_writes': writes,
        'independent_component_closure_checks': checks,
        'sprite3_precondition': 0x89,
        'wrong_sprite3_precondition_rejected': True,
        'physical_RMW_dummy_writes_and_cycles_modeled': False,
        'native_stencil_entry_state_not_assumed': True})

    # Primary x64sc rules for aliases and software-visible D016 RMW reads.
    member_name = 'vice-3.10/src/viciisc/vicii-mem.c'
    with tarfile.open(VICE, 'r|gz') as archive:
        for member in archive:
            if member.name == member_name:
                vicii = archive.extractfile(member).read()
                break
        else:
            raise AssertionError('missing viciisc member')
    assert digest(vicii) == 'f8e2bdd30fbe8abf60a7e77647723f4615834e5b414f2695698ed28b31857edf'
    source_lines = vicii.decode().splitlines()
    rules = []
    for lo, hi, role in [(176, 181, 'store complete software register byte'),
                         (334, 341, 'write aliases mask to6address bits'),
                         (562, 568, 'read aliases mask to6address bits'),
                         (627, 631, 'D016 read ORsC0')]:
        rules.append({'first_line': lo, 'last_line': hi, 'role': role,
                      'text': '\n'.join(source_lines[lo - 1:hi])})
    assert 'addr &= 0x3f;' in rules[1]['text'] and 'addr &= 0x3f;' in rules[2]['text']
    assert 'vicii.regs[addr] | 0xc0' in rules[3]['text']

    proof = {'schema': 'the-hat-upscroll-source-1', 'producer': meta(source),
             'inputs': [meta(path) for path in pins], 'source_code_guards': guards,
             'prepared_states': states_meta, 'timer_latches': timer_meta,
             'conditional_dispatch': dispatch_meta, 'finite_stencil': stencil_meta,
             'vice_member': {'archive': meta(VICE), 'name': member_name,
                             'bytes': len(vicii), 'sha256': digest(vicii), 'rules': rules},
             'source_lifetime_domains': {
                 'b8_loaded': [0x4000, 0xD000], 'b9_loaded': [0xE000, 0xF800],
                 'VIC_bank_if_effective_CIA2_pins_low2_are2': [0x4000, 0x8000],
                 'initial_pointer_tables': [[0x43F8, 0x4400], [0x47F8, 0x4800]],
                 'raster_program': [0x8516, 0xC7BA],
                 'motion_table_Y': [0xE1AE, 0xE97E],
                 'motion_table_pointer_phase': [0xE97E, 0xF14E],
                 'raster_D011_table': [0xF200, 0xF300],
                 'raster_sprite_color_table': [0xF300, 0xF400],
                 'dispatch_tables': [0xF400, 0xF800],
                 'external_timing_helpers_need_native_binding': [0x019F, 0x01AC]},
             'source_D011_table': {'values': sorted(set(read9(0xF200, 256))),
                                  'DEN_clear_for_all_entries': all(not (v & 0x10) for v in read9(0xF200, 256))},
             'capture_anchors': {'post_init': 0x8042, 'pair_before': 0xE152,
                                 'pair_after': 0xE15C, 'raster_selector': 0x8516,
                                 'cutoff_entry': 0x828C, 'after_TXS': 0x8298},
             'limits': [
                 'Source/data proof, not native lifecycle or full committed display acceptance.',
                 'Movement/image bytes are prepared before this consumer; their host generator is not recovered.',
                 'Finite stencil requires stated steady-entry state; it is not a full raster-program CPU replay.',
                 'No absolute raster clock, bus ownership, physical RMW write count or FPS prediction.',
                 'Actual CIA2 pins, CPU port and interrupt phase must be bound by native snapshots.',
                 'Lookup dispatch depends on live raster reads; source tables alone do not choose their observed path.',
                 'Raster work is intentionally abandoned by an IRQ restoring the saved stack, not a normal return.'
             ]}
    result = args.output / 'upscroll-source-proof.json'
    write_json(result, proof)
    print(json.dumps({'proof': outmeta(result), 'states': len(states),
                      'timer_entries': len(timer), 'stencil_checks': checks}))


if __name__ == '__main__':
    main()
