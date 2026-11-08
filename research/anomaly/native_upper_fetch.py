#!/usr/bin/env python3
"""Passively audit Anomaly native-07 upper fetch, motion and fifth strip.

Only retained files and pinned local parsers are read. No emulator, subprocess,
CPU interpreter, downloaded host program or live connection is started.
"""

from collections import Counter
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tarfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/anomaly'
CAPTURE = BASE / 'native-07'
OUT = BASE / 'native-upper-fetch-analysis'
CASE_SHA = 'e2a86a8cbbb9136388e4dbed04ce0294151fee01840b016e09a1c84dcf0fd428'
PARENT_SHA = '2428affe32e414636d3444b1cfa72f41d25d7e466adf0ff0ad07dbabf28d32c8'
DISK_SHA = 'd452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd'
PIXEL_SHA = '5d6e4137a4f411372db1ca5d657a9f74300a765425d50a87eac032133fd3b984'
PINS = {
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/anomaly/upper_scanout.py': '70a71b45b4c469182d6b5c5c8841fd20741fe0638ba90d5979f89abbc5d3667a',
    'research/anomaly/scanout.py': 'c5e63a07f3060614710518aaf9b9e6c9365c297619af4e19719a4b5f8b62198f',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'build/research/anomaly/upper-scanout-analysis/upper-scanout-proof.json': '7a6f5a32c52adb85cde0b851ecff47f5154ca301240e48e52d1a810b5ccdc4d3',
    'build/research/anomaly/native-tail-analysis/native-tail-evidence.json': '6a059c275606b55e1fc6bfa14a6ac2093112548981fb78182209883d2274ba9e',
    'build/research/anomaly/binary-analysis/side1-binary-proof.json': 'b8744b0184128330a069a7366c4f843193306074f4a55a03d10f092a6fa8800c',
    'build/research/anomaly/arcade-source-proof.json': '30e681b44b72f7a610bd8b151762813c591ad7339b153ca8ce8d18117e61e729',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
}
EXPECTED = {
    'restored-floor': (0xb82a, 167013188, 250, 62),
    'upper-selected': (0xb864, 167013227, 251, 38),
    'sprites-prepared': (0x3d83, 167014848, 277, 21),
    'upper-fetch': (0x08c1, 167022487, 86, 37),
    'fifth-field-pre': (0xb400, 167026619, 152, 11),
    'upper-complete': (0xb47b, 167026856, 155, 59),
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def checked(item):
    data = (ROOT / item['path']).read_bytes()
    assert len(data) == item['bytes'] and sha(data) == item['sha256'], item['path']
    return data


def load(name, relative):
    path = ROOT / relative
    assert sha(path.read_bytes()) == PINS[relative], relative
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def read_proof(relative):
    path = ROOT / relative
    assert sha(path.read_bytes()) == PINS[relative], relative
    value = json.loads(path.read_text())
    assert value['pass'], relative
    return value


def observe_commands(case, wire):
    """Classify every sent command; capture registers come from the same wire."""
    commands = [row for _, row in sorted(case['responses'].items())]
    assert not case['partial'] and not case['cancelled']
    assert all(row['status'] == 'completed' for row in commands)
    last_registers, captures, resumes, restores = None, {}, [], []
    parent = BASE / 'native-06/floor-line-drawn.vsf'
    for index, row in enumerate(commands):
        command = row['command']
        allowed = command in ('r', 'sidefx off', 'bank ram', 'warp', 'resourceget "Speed"', 'x')
        allowed |= bool(re.fullmatch(r'(?:break|delete) [0-9a-f]{1,4}', command))
        allowed |= command in (
            'trace store d000 d02e', 'trace store dd00 dd03', 'trace store cff8 cfff',
            'break exec 0000 ffff if (RL == $56) && (CY >= $23)',
            'break exec 0000 ffff if (RL == $9b) && (CY >= $3b)')
        if command == f'undump "{parent}"':
            allowed = True
            restores.append(row['sequence'])
            last_registers = None
        if command == 'r':
            last_registers = wire.registers(row['response'])
        if command == 'warp':
            assert row['response'].split('(C:')[0].strip() == 'Warp mode is off.'
        if command == 'resourceget "Speed"':
            assert row['response'].split('(C:')[0].strip() == 'Speed=100'
        if command == 'x':
            assert [r['command'] for r in commands[index - 2:index]] == ['warp', 'resourceget "Speed"']
            resumes.append(row['sequence'])
            last_registers = None
        match = re.fullmatch(r'(bsave|dump) "([^"\n]+)"( 0 0000 ffff)?', command)
        if match:
            kind, path_text, suffix = match.groups()
            path = Path(path_text)
            assert path.parent == CAPTURE and last_registers is not None
            assert (kind == 'bsave') == (suffix is not None)
            assert commands[index - 1]['command'] == 'r'
            assert path.name not in captures
            captures[path.name] = dict(kind=kind, registers=last_registers, sequence=row['sequence'])
            allowed = True
        assert allowed, ('Unclassified command', command)
        assert '[Monitor observation failed:' not in row['response']
    assert len(restores) == 1 and len(resumes) == 5 and len(captures) == 12
    return captures, dict(commands=len(commands), resumes=resumes, restores=restores,
                         command_counts=dict(Counter(row['command'].split()[0] for row in commands)),
                         warp_off_before_every_resume=True, speed_before_every_resume=100,
                         RAM_code_PC_or_register_writes=[], inputs_to_original_program=[],
                         source_restore=str(parent.relative_to(ROOT)))


def capture(stem, contexts, layout, reader):
    ram_path, snapshot = CAPTURE / f'ram-{stem}.bin', CAPTURE / f'{stem}.vsf'
    a, b = contexts[ram_path.name], contexts[snapshot.name]
    assert a['registers'] == b['registers']
    registers = a['registers']
    ram = ram_path.read_bytes()
    memory = reader.module_payload(snapshot, 'C64MEM')
    assert len(ram) == 65536 and ram == memory[4:65540]
    assert (memory[1], memory[0]) == (registers['port00'], registers['port01'])
    payload = reader.module_payload(snapshot, 'MAINCPU')
    cpu = dict(clock=int.from_bytes(payload[:8], 'little'), a=payload[8], x=payload[9], y=payload[10],
               sp=payload[11], pc=int.from_bytes(payload[12:14], 'little'), flags=payload[14])
    assert all(registers[key] == value for key, value in cpu.items())
    state = reader.read_snapshot(snapshot)
    vic = state['vicii']
    assert (vic['raster_line'], vic['raster_cycle']) == (registers['line'], registers['cycle'])
    assert (cpu['pc'], cpu['clock'], vic['raster_line'], vic['raster_cycle']) == EXPECTED[stem]
    pipe, meta, raster = layout.draw_state(reader.module_payload(snapshot, 'VIC-II'))
    entry = dict(stem=stem, ram=artifact(ram_path), snapshot=artifact(snapshot), registers=registers,
                 serialized_CPU_ports_and_beam_equal=True, complete_RAM_pair_equal=True)
    return dict(entry=entry, ram=ram, state=state, pipe=pipe, meta=meta, raster=raster, cpu=cpu)


def source_rules(author):
    """Retain source for the fetch-counter and committed-raster interpretation."""
    archive = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    guards = {
        'src/viciisc/vicii-fetch.c': (
            'a = (vicii.vc << 3) | vicii.rc;', 'vicii.gbuf = data;', 'vicii.vc++;',
            'vicii.sprite[i].pointer = fetch_phi1(v_fetch_addr(0x3f8 + i));',
            'sprdata = fetch_phi1((vicii.sprite[i].pointer << 6) + vicii.sprite[i].mc);',
            'vicii.sprite[i].mc++;'),
        'src/viciisc/vicii-cycle.c': ('vicii.sprite[i].mc = vicii.sprite[i].mcbase;',
                                    'vicii.sprite[i].mcbase = vicii.sprite[i].mc;'),
        'src/viciisc/vicii-snapshot.c': ('SMW_BA(m, vicii.dbuf, VICII_DRAW_BUFFER_SIZE)',),
        'src/raster/raster-snapshot.c': ('SMW_DW(m, raster->current_line)',
                                       'SMW_BA(m, draw_buffer->draw_buffer_padded_allocations[0], padded_size)'),
    }
    files = []
    with tarfile.open(archive, 'r:gz') as tar:
        for relative, needles in guards.items():
            member = 'vice-3.10/' + relative
            data = tar.extractfile(member).read()
            assert all(needle in data.decode() for needle in needles), relative
            destination = OUT / 'source' / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(data)
            files.append(dict(member=member, **artifact(destination)))
    main = next(row for row in author['sources'] if row['source_path'] == 'Parts/ArcadeScroller/ArcadeScroller.asm')
    variables = next(row for row in author['sources'] if row['source_path'] == 'Parts/ArcadeScroller/variables.asm')
    text = checked(main).decode()
    # The arithmetic model below follows this branch, including its temporary
    # correction store and subsequent low-phase subtraction from the old X.
    assert 'adc #12' in text and 'cmp #$06' in text and 'lda #$60' in text
    checked(variables)
    return dict(archive=artifact(archive), files=files, author_motion_source=main,
                author_variables=variables, source_guards=sum(map(len, guards.values())))


def stores_from_wire(case, layout):
    # Keep the wire audit byte-exact. Only this text parser accepts CRLF and
    # separates completed prompt responses before matching trace headers.
    text = '\n'.join(row['response'].replace('\r\n', '\n')
                     for _, row in sorted(case['responses'].items()))
    stores = []
    for match in layout.TRACE.finditer(text):
        row = match.groupdict()
        for key in ('checkpoint', 'line', 'cycle', 'clock'):
            row[key] = int(row[key])
        for key in ('target', 'pc', 'a', 'x', 'y', 'sp'):
            row[key] = int(row[key], 16)
        stores.append(row)
    assert len(stores) == len(re.findall(r'^#\d+ \(Trace store ', text, re.M))
    assert all(a['clock'] <= b['clock'] for a, b in zip(stores, stores[1:]))
    return stores


def motion(previous, prepared, original, known, stores):
    before, after = previous['ram'], prepared['ram']
    old_regs, regs = previous['state']['vicii']['regs'], prepared['state']['vicii']['regs']
    for first, end in ((0x3be8, 0x3d93), (0xb82a, 0xb864), (0x39e9, 0x3ae9)):
        assert all(known[first:end])
        assert before[first:end] == after[first:end] == original[first:end]
    mask, rows = before[0xcb], []
    assert mask == 0x60 and old_regs[0x10] == 4  # Floor D010 is not saved upper D010.
    assert before[0x3d89:0x3d8c] == bytes.fromhex('2c c2 66')  # BIT, not fade JSR.
    for sprite in range(4, 8):
        index = sprite - 2
        low, y = old_regs[sprite * 2:sprite * 2 + 2]
        speed, phase, wave = before[0xf0 + index], before[0xe8 + sprite], before[0xe0 + index]
        assert speed == after[0xf0 + index]
        writes, borrowed, wrapped, new_phase, new_wave = [], False, False, phase, wave
        difference = low - speed
        if phase:
            writes.append(difference & 255)
            if difference < 0:
                borrowed = True
                writes.append((difference + 12) & 255)
                new_phase = 0
                mask &= ~(1 << sprite)
        if not phase or borrowed:
            writes.append(difference & 255)
            if (difference & 255) < 6:
                wrapped = True
                mask |= 1 << sprite
                writes.append(0x60)
                new_phase = 0x60
                y = before[0x39e9 + wave]
                new_wave = (wave + 1) & 255
        observed = [row for row in stores if row['target'] == 0xd000 + sprite * 2
                    and row['clock'] <= prepared['cpu']['clock']]
        assert [row['a'] for row in observed] == writes
        assert regs[sprite * 2:sprite * 2 + 2] == [writes[-1], y]
        assert (after[0xe8 + sprite], after[0xe0 + index]) == (new_phase, new_wave)
        rows.append(dict(sprite=sprite, old_low_X=low, old_upper_high_bit=bool(before[0xcb] & (1 << sprite)),
                         old_Y=old_regs[sprite * 2 + 1], speed=speed, high_phase_before=phase,
                         high_phase_after=new_phase, borrowed=borrowed, wrapped=wrapped,
                         low_X_store_values=writes, observed_low_X_stores=observed,
                         new_low_X=writes[-1], new_Y=y, wave_index_before=wave, wave_index_after=new_wave,
                         wave_address=(0x39e9 + wave if wrapped else None)))
    assert mask == after[0xcb] == regs[0x10] == 0x80
    assert [row['borrowed'] for row in rows] == [False, True, True, False]
    assert [row['wrapped'] for row in rows] == [False, False, False, True]
    assert [row['low_X_store_values'] for row in rows] == [[56], [244, 0, 244], [244, 0, 244], [2, 96]]
    high = next(row for row in stores if row['target'] == 0xd010 and row['pc'] == 0x3d80)
    assert high['y'] == mask and high['clock'] == prepared['cpu']['clock']
    vertical = [row for row in stores if row['target'] == 0xd00f]
    assert len(vertical) == 1 and vertical[0]['a'] == 77
    return dict(saved_upper_mask_before=before[0xcb], unrelated_floor_D010=old_regs[0x10],
                upper_mask_after=mask, final_D010_store=high, sprite7_Y_store=vertical[0], sprites=rows,
                source_ranges=[dict(first=a, end_exclusive=b, bytes=b - a, sha256=sha(original[a:b]))
                               for a, b in ((0x3be8, 0x3d93), (0xb82a, 0xb864), (0x39e9, 0x3ae9))],
                scope='Independent source arithmetic and actual intermediate MMIO stores; no CPU interpreter.')


def active_fetch(current, upper):
    ram, vic, pipe = current['ram'], current['state']['vicii'], current['pipe']
    geometry = upper.geometry(current)
    assert geometry == dict(bank=0xc000, bitmap=0xe000, screen=0xcc00,
                            D011=0x3b, D016=0xc7, D018=0x38, D020=0)
    assert (vic['raster_line'], vic['raster_cycle'], vic['vc'], vic['rc'], vic['vmli']) == (86, 37, 183, 3, 23)
    assert not vic['idle_state'] and not vic['vborder']
    fetch_vc = (vic['vc'] - 1) & 1023
    address = geometry['bitmap'] + ((fetch_vc << 3) | vic['rc'])
    assert address == 0xe5b3 and ram[address] == vic['gbuf'] == pipe['gbuf_pipe0'] == 0x7e
    matrix = geometry['screen'] + vic['vcbase']
    assert matrix == 0xcca0 and bytes(vic['vbuf']) == ram[matrix:matrix + 40]
    assert vic['cbuf'] == vic['color_ram'][vic['vcbase']:vic['vcbase'] + 40]
    rows = []
    for sprite in (5, 7):
        data = vic['sprites'][sprite]
        assert vic['sprite_dma'] & vic['sprite_display_bits'] & (1 << sprite)
        assert data['pointer'] == ram[0xcff8 + sprite]
        row = vic['raster_line'] - vic['regs'][sprite * 2 + 1] - 1
        first = geometry['bank'] + data['pointer'] * 64 + row * 3
        assert data['mc'] == data['mcbase'] == 3 * (row + 1)
        assert data['data'] == int.from_bytes(ram[first:first + 3], 'big')
        rows.append(dict(sprite=sprite, pointer=data['pointer'], row=row, address=first,
                         bytes=list(ram[first:first + 3]), data_latch=data['data'], MC=data['mc'],
                         MCBASE=data['mcbase'], x=data['x'], y=vic['regs'][sprite * 2 + 1],
                         nonzero_witness=bool(data['data'])))
    assert rows[0]['address'] == 0xca40 and rows[0]['bytes'] == [0x28, 0, 0]
    assert rows[1]['data_latch'] == 0  # Retained zero state, not a nonzero witness.
    return dict(checkpoint=current['entry'], geometry=geometry, line=86, raw_cycle=37,
                VC=vic['vc'], fetch_VC=fetch_vc, RC=vic['rc'], VMLI=vic['vmli'],
                bitmap_address=address, RAM_value=ram[address], GBUF=vic['gbuf'], pipe0=pipe['gbuf_pipe0'],
                matrix_first=matrix, matrix_bytes=40, matrix_equal=True, color_RAM_equal=True,
                sprites=rows, source_rule='Graphics fetch stores GBUF before incrementing VC/VMLI; sprite MC advances three bytes before this stop.',
                scope='Actual active bank C000 graphics and sprite latches. No physical bus timestamp or physical-chip claim.')


def fifth_field(captures, upper, old):
    before, after = captures['fifth-field-pre'], captures['upper-complete']
    baseline = checked(old['fields'][-1]['pre']['ram'])
    ram, vic = before['ram'], before['state']['vicii']
    assert upper.geometry(before) == dict(bank=0xc000, bitmap=0xe000, screen=0xcc00,
                                         D011=0x3b, D016=0xc7, D018=0x38, D020=0)
    for first, end in upper.STABLE:
        assert baseline[first:end] == ram[first:end] == after['ram'][first:end]
    assert ram[0xca00:0xcb00] == ram[0x7400:0x7500]
    regs = vic['regs']
    assert regs[0x15] == regs[0x1d] == 255 and regs[0x1c] & 0xf0 == 0xf0
    assert not regs[0x17] & 0xf0 and not regs[0x1b] & 0xf0
    assert list(ram[0xcffc:0xd000]) == [0x28, 0x29, 0x2a, 0x2b]
    assert upper.field_base(before) - upper.field_base(captures['restored-floor']) == 19656
    assert upper.field_base(after) == upper.field_base(before)
    assert after['meta']['current_line'] == 155
    independent, selected, overlap = upper.compose(before)  # Do not call old four-field branch guards.
    actual = after['raster'][51 * 384:155 * 384]
    assert len(actual) == len(independent) == 39936 and actual == independent and sha(actual) == PIXEL_SHA
    assert selected == {4: 12, 5: 36, 6: 84, 7: 0} and overlap == 0
    actual_path, expected_path = OUT / 'field-05-actual.bin', OUT / 'field-05-independent.bin'
    actual_path.write_bytes(actual)
    expected_path.write_bytes(independent)
    controls = []
    for variant in ('no_sprites', 'sprites_as_hires', 'no_x_expansion', 'bitmap_multicolor',
                    'sprites_behind_bitmap', 'reverse_sprite_priority'):
        alternative, _, _ = upper.compose(before, variant)
        errors = upper.delta(actual, alternative)
        assert errors or variant == 'reverse_sprite_priority', variant
        path = OUT / f'field-05-control-{variant}.json'
        path.write_text(json.dumps(dict(variant=variant, differences=errors,
            difference_count=len(errors), discriminating=bool(errors)), indent=2) + '\n')
        controls.append(dict(variant=variant, differences=len(errors), discriminating=bool(errors), evidence=artifact(path)))
    previous_positions = copy.deepcopy(before)
    previous_regs = captures['restored-floor']['state']['vicii']['regs']
    for sprite in range(4, 8):
        previous_positions['state']['vicii']['regs'][sprite * 2:sprite * 2 + 2] = previous_regs[sprite * 2:sprite * 2 + 2]
    previous_positions['state']['vicii']['regs'][0x10] = captures['restored-floor']['ram'][0xcb]
    stale, _, _ = upper.compose(previous_positions)
    stale_errors = upper.delta(actual, stale)
    assert stale_errors
    stale_path = OUT / 'field-05-control-previous-upper-positions.json'
    stale_path.write_text(json.dumps(dict(assumption='Reuse previous upper X/Y positions and saved upper high-X mask.',
                                         differences=stale_errors, difference_count=len(stale_errors)), indent=2) + '\n')
    return dict(number=5, lines=[51, 154], rows=104, width=384, pixels=len(actual),
                actual=artifact(actual_path), independent=artifact(expected_path), differences=[],
                field_base_clock=upper.field_base(before), committed_raster_line=after['meta']['current_line'],
                pre=before['entry'], post=after['entry'], geometry=upper.geometry(before),
                sprite_selected_pixels=selected, sprite_nontransparent_overlaps=overlap,
                controls=controls, previous_positions_control=dict(differences=len(stale_errors), evidence=artifact(stale_path)),
                stable_inputs=[dict(first=a, end_exclusive=b, bytes=b - a, sha256=sha(ram[a:b])) for a, b in upper.STABLE],
                old_four_field_receipt_unchanged=True, old_four_pixels=old['compared_upper_pixels'],
                total_separately_proved_upper_fields=5, total_separately_compared_upper_pixels=old['compared_upper_pixels'] + len(actual))


def main():
    for relative, digest in PINS.items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
    OUT.mkdir(parents=True, exist_ok=True)
    wire = load('anomaly07_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {'native-07': CASE_SHA}
    case = wire.audit_session('native-07')
    disk = BASE / 'original/WeAreTheAnomaly-Side1.d64'
    parent = BASE / 'native-06/floor-line-drawn.vsf'
    assert sha(disk.read_bytes()) == DISK_SHA and sha(parent.read_bytes()) == PARENT_SHA
    assert case['session']['program'] == str(disk)
    command = case['session']['command']
    assert command[command.index('-8') + 1] == str(disk) and '-pal' in command
    contexts, command_audit = observe_commands(case, wire)
    upper = load('anomaly07_upper_compositor', 'research/anomaly/upper_scanout.py')
    layout, reader = upper.readers()
    captures = {stem: capture(stem, contexts, layout, reader) for stem in EXPECTED}
    restored = CAPTURE / 'restored-floor.vsf'
    modules = ('C64MEM', 'MAINCPU', 'CIA1', 'CIA2', 'VIC-II')
    for name in modules:
        assert reader.module_payload(parent, name) == reader.module_payload(restored, name), name
    tail = read_proof('build/research/anomaly/native-tail-analysis/native-tail-evidence.json')
    assert tail['checkpoints'][-1]['snapshot'] == artifact(parent)
    old = read_proof('build/research/anomaly/upper-scanout-analysis/upper-scanout-proof.json')
    assert old['upper_fields'] == 4 and old['compared_upper_pixels'] == 159744
    binary = read_proof('build/research/anomaly/binary-analysis/side1-binary-proof.json')
    original, known = (checked(binary['bundles'][36][name]) for name in ('RAM', 'known_mask'))
    author = read_proof('build/research/anomaly/arcade-source-proof.json')
    source = source_rules(author)
    stores = stores_from_wire(case, layout)
    setup = []
    for pc, address, value in ((0xb857, 0xd016, 0xc7), (0xb85c, 0xd018, 0x38), (0xb861, 0xdd02, 0x3f)):
        row = next(row for row in stores if row['pc'] == pc)
        assert row['target'] == address and row['a'] == value
        assert original[pc:pc + 3] == bytes((0x8d, address & 255, address >> 8))
        setup.append(row)
    assert captures['upper-selected']['state']['cia']['CIA2']['ddra'] == 0x3f
    motion_result = motion(captures['restored-floor'], captures['sprites-prepared'], original, known, stores)
    fetch = active_fetch(captures['upper-fetch'], upper)
    field = fifth_field(captures, upper, old)
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()),
                  scope='Closed native-07 lineage, active C000 fetch, source-derived borrow/wrap transition and independent fifth 104-row upper palette-index strip.',
                  input_pins=[artifact(ROOT / relative) for relative in PINS],
                  capture_directory_sha256=CASE_SHA, wire=wire.summary(case), command_audit=command_audit,
                  original_disk=artifact(disk), parent=artifact(parent),
                  restore=dict(complete_equal_modules=list(modules), ports_CPU_and_beam_equal=True),
                  checkpoints=[captures[stem]['entry'] for stem in EXPECTED], RAM_snapshot_bytes=6 * 65536,
                  source=source, upper_setup_stores=setup, register_observations=stores,
                  observed_target_counts={f'{address:04x}': count for address, count in Counter(row['target'] for row in stores).items()},
                  motion=motion_result, active_upper_fetch=fetch, fifth_upper_field=field,
                  final_continuation=captures['upper-complete']['entry'],
                  new_native_execution=False, physical_chip_proven=False, bus_write_phase_certified=False,
                  whole_frame_or_FPS_proof=False,
                  limits=[
                      'This producer is passive; the retained capture process already closed and was reaped.',
                      'Trace clocks identify observer instruction coordinates, not individual hardware bus phases; RMW hooks do not enumerate every dummy/final bus write.',
                      'The delayed DD02 and D010 trace rows appear after the following resume; paired snapshots already contain the completed register stores.',
                      'Stable bitmap/art RAM at captured endpoints and exact output do not establish the absence of transient writes between checkpoints.',
                      'Sprite7 has an active zero data latch and lies beyond the right border; this is not a nonzero visible sprite witness.',
                      'Reverse sprite priority remains inconclusive because nontransparent sprite pixels do not overlap.',
                      'The old four-field receipt remains unchanged. This separate fifth strip adds 39936 indices; no complete 312-line frame or demo FPS claim follows.'])
    result['pass'] = result.pop('pass_')
    destination = OUT / 'native-upper-fetch-proof.json'
    destination.write_text(json.dumps(result, indent=2) + '\n')
    (OUT / 'native_upper_fetch.checked.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(pass_=True, RAM_snapshot_bytes=result['RAM_snapshot_bytes'],
                         commands=command_audit['commands'], resumes=5, active_bitmap_address=fetch['bitmap_address'],
                         fifth_upper_pixels=field['pixels'], pixel_differences=0,
                         total_separately_proved_fields=5, receipt=artifact(destination)), indent=2))


if __name__ == '__main__':
    main()
