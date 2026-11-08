#!/usr/bin/env python3
"""Independently index retained Anomaly upper bitmap/sprite palette pixels.

Passive saved evidence only. No C64 CPU, emulator, downloaded host program,
VICE renderer, screenshot palette or fitted output crop is executed here.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/anomaly'
OUT = BASE / 'upper-scanout-analysis'
PINS = {
    'binary-analysis/side1-binary-proof.json': 'b8744b0184128330a069a7366c4f843193306074f4a55a03d10f092a6fa8800c',
    'native-upper-analysis/native-upper-evidence.json': '53274dec47bf09e196878d973ec6c5f10782497d61ff36cf50f97db31bc108fd',
    'native-scanout-analysis/native-scanout-evidence.json': '70fe556b8c80bf6a73721b4f51852e30bc9f6b103f1e3bff06e4e2e1b1e7dfa2',
    'native-tail-analysis/native-tail-evidence.json': '6a059c275606b55e1fc6bfa14a6ac2093112548981fb78182209883d2274ba9e',
    'upper-analysis/upper-proof.json': '67ac3c820f62f2f8bdfa1342a8790459c4ce673145c1080393f471a896a4ff3f',
    'sprite-scanout-analysis/sprite-scanout-proof.json': 'f0c67d0a1a674e9f15e19caa75a16d2b346d2aaaab886b1536d6220dc97b47b4',
    'arcade-source-proof.json': '30e681b44b72f7a610bd8b151762813c591ad7339b153ca8ce8d18117e61e729',
}
LAYOUT_SHA = 'c5e63a07f3060614710518aaf9b9e6c9365c297619af4e19719a4b5f8b62198f'
ARCHIVE_SHA = '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'
STABLE = ((0xe000, 0xf040), (0xcc00, 0xce08), (0xca00, 0xcb00),
          (0xcffc, 0xd000), (0x7400, 0x7500))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def checked(item):
    data = (ROOT / item['path']).read_bytes()
    assert len(data) == item['bytes'] and sha(data) == item['sha256'], item['path']
    return data


def receipts():
    result = {}
    for name, digest in PINS.items():
        path = BASE / name
        assert sha(path.read_bytes()) == digest, name
        value = json.loads(path.read_text())
        assert value['pass']
        result[name] = value
    return result


def readers():
    path = ROOT / 'research/anomaly/scanout.py'
    assert sha(path.read_bytes()) == LAYOUT_SHA
    spec = importlib.util.spec_from_file_location('frozen_upper_layout', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module.reader()


def sources(author):
    archive = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    assert sha(archive.read_bytes()) == ARCHIVE_SHA
    guards = {
        'src/viciisc/viciitypes.h': ['#define VICII_25ROW_START_LINE    0x33',
                                    '#define VICII_25ROW_STOP_LINE     0xfb'],
        'src/viciisc/vicii-fetch.c': ['a = (vicii.vc << 3) | vicii.rc;',
            'a |= (vicii.regs[0x18] & 0x8) << 10;',
            'vicii.sprite[i].pointer = fetch_phi1(v_fetch_addr(0x3f8 + i));',
            'sprdata = fetch_phi1((vicii.sprite[i].pointer << 6) + vicii.sprite[i].mc);',
            'vicii.vmli++;', 'vicii.vc++;'],
        'src/viciisc/vicii-cycle.c': ['vicii.sprite[i].mc = vicii.sprite[i].mcbase;',
            'vicii.sprite[i].mcbase = 0;', 'vicii.sprite[i].exp_flop ^= 1;',
            'line == (rsel ? VICII_25ROW_START_LINE : VICII_24ROW_START_LINE)'],
        'src/viciisc/vicii-draw-cycle.c': [
            'COL_VBUF_L, COL_VBUF_L, COL_VBUF_H, COL_VBUF_H,',
            'COL_D021, COL_VBUF_H, COL_VBUF_L, COL_CBUF,',
            'sbuf_pixel_reg[s] = (uint8_t)((sbuf_reg[s] >> 22) & 0x03);',
            'for (s = 7; s >= 0; --s)', 'if (!(pixel_pri && spri))',
            'memset(render_buffer, COL_D020, 7)', 'render_buffer[7] = COL_D020;',
            'draw_sprites8(cycle_flags_pipe);', 'draw_border8();'],
        'src/viciisc/vicii-draw.c': ['#define DBUF_OFFSET (17 * 8 - vicii.screen_leftborderwidth)'],
    }
    files = []
    with tarfile.open(archive, 'r:gz') as tar:
        for name, needles in guards.items():
            member = 'vice-3.10/' + name
            data = tar.extractfile(member).read()
            assert all(needle in data.decode() for needle in needles), name
            target = OUT / 'source' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            files.append(dict(member=member, **artifact(target)))
    selected = {}
    for name in ('ArcadeScroller.asm', 'raster_irq.asm', 'init_functions.asm',
                 'double_buffer_functions.asm', 'upper_scroll_logic.asm', 'variables.asm'):
        entry = next(x for x in author['sources'] if x['source_path'] == 'Parts/ArcadeScroller/' + name)
        checked(entry)
        selected[name] = entry
    assert 'sta $d01d' in checked(selected['ArcadeScroller.asm']).decode()
    assert 'sta upper_sprites_bank_3,x' in checked(selected['init_functions.asm']).decode()
    return dict(archive=artifact(archive), files=files,
                source_guards=sum(map(len, guards.values())), author_files=selected,
                url='https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/')


def native(entry, layout, reader):
    ram = checked(entry['ram'])
    checked(entry['snapshot'])
    path = ROOT / entry['snapshot']['path']
    assert ram == reader.module_payload(path, 'C64MEM')[4:65540]
    state = reader.read_snapshot(path)
    pipe, meta, raster = layout.draw_state(reader.module_payload(path, 'VIC-II'))
    cpu = reader.module_payload(path, 'MAINCPU')
    decoded = dict(clock=int.from_bytes(cpu[:8], 'little'), a=cpu[8], x=cpu[9], y=cpu[10],
                   sp=cpu[11], pc=int.from_bytes(cpu[12:14], 'little'), flags=cpu[14])
    assert all(entry['registers'][key] == value for key, value in decoded.items())
    assert state['vicii']['raster_line'] == entry['registers']['raster_line']
    assert state['vicii']['raster_cycle'] == entry['registers']['raster_cycle']
    return dict(entry=entry, ram=ram, state=state, pipe=pipe, meta=meta, raster=raster, cpu=decoded)


def bank(state):
    cia = state['cia']['CIA2']
    pins = (cia['pra'] & cia['ddra']) | (3 & ~cia['ddra'])
    return ((~pins) & 3) * 0x4000


def geometry(capture):
    vic = capture['state']['vicii']
    regs = vic['regs']
    b = bank(capture['state'])
    return dict(bank=b, bitmap=b + ((regs[0x18] & 8) << 10),
                screen=b + ((regs[0x18] & 0xf0) << 6), D011=regs[0x11],
                D016=regs[0x16], D018=regs[0x18], D020=regs[0x20])


def field_base(capture):
    vic = capture['state']['vicii']
    return capture['cpu']['clock'] - 63 * vic['raster_line'] - vic['raster_cycle']


def compose(capture, variant=None):
    """Direct cell/bit/pair indexing; no emulated sprite shifter or CPU."""
    ram, vic = capture['ram'], capture['state']['vicii']
    regs, colors = vic['regs'], vic['color_ram']
    rows, selected, collisions = [], {s: 0 for s in range(4, 8)}, 0
    for line in range(51, 155):
        n = line - 51
        row, fine = divmod(n, 8)
        pixels, foreground = [], []
        for cell in range(40):
            value = ram[0xe000 + row * 320 + cell * 8 + fine]
            attr = ram[0xcc00 + row * 40 + cell]
            if variant == 'bitmap_multicolor':
                palette = [regs[0x21], attr >> 4, attr & 15, colors[row * 40 + cell]]
                for pair in range(4):
                    code = (value >> (6 - 2 * pair)) & 3
                    pixels.extend([palette[code]] * 2)
                    foreground.extend([bool(code & 2)] * 2)
            else:
                for bit in range(8):
                    on = bool(value & (128 >> bit))
                    pixels.append(attr >> 4 if on else attr & 15)
                    foreground.append(on)
        output = bytearray(384)
        pri = [False] * 384
        scroll = regs[0x16] & 7
        output[39:343] = bytes(pixels[7 - scroll:311 - scroll])
        pri[39:343] = foreground[7 - scroll:311 - scroll]
        covered = [0] * 384
        order = range(7, 3, -1) if variant == 'reverse_sprite_priority' else range(4, 8)
        if variant == 'no_sprites':
            order = ()
        for sprite in order:
            source_row = line - regs[sprite * 2 + 1] - 1
            if not 0 <= source_row < 21:
                continue
            pointer = ram[0xcff8 + sprite]
            address = 0xc000 + pointer * 64 + source_row * 3
            value = int.from_bytes(ram[address:address + 3], 'big')
            palette = [None, regs[0x25], regs[0x27 + sprite], regs[0x26]]
            sprite_pixels = []
            expanded = variant != 'no_x_expansion'
            if variant == 'sprites_as_hires':
                for bit in range(24):
                    color = palette[2] if value & (1 << (23 - bit)) else None
                    sprite_pixels.extend([color] * (2 if expanded else 1))
            else:
                for pair in range(12):
                    sprite_pixels.extend([palette[(value >> (22 - 2 * pair)) & 3]] * (4 if expanded else 2))
            xpos = regs[sprite * 2] + (256 if regs[0x10] & (1 << sprite) else 0) + 8
            for offset, color in enumerate(sprite_pixels):
                x = xpos + offset
                if color is None or not 39 <= x < 343:
                    continue
                if covered[x]:
                    collisions += 1
                    continue
                covered[x] = sprite + 1
                if variant == 'sprites_behind_bitmap' and pri[x]:
                    continue
                output[x] = color
                selected[sprite] += 1
        rows.append(bytes(output))
    return b''.join(rows), selected, collisions


def delta(actual, expected, first=51):
    assert len(actual) == len(expected)
    return [dict(line=first + i // 384, x=i % 384, actual=a, expected=b)
            for i, (a, b) in enumerate(zip(actual, expected)) if a != b]


def code_and_motion(previous, current, original):
    a, b = previous['ram'], current['ram']
    pv, qv = previous['state']['vicii'], current['state']['vicii']
    assert field_base(current) - field_base(previous) == 312 * 63
    for ram in (a, b):
        assert ram[0x3be8:0x3d93] == original[0x3be8:0x3d93]
        assert ram[0xb82a:0xb864] == original[0xb82a:0xb864]
        assert ram[0x3d89:0x3d8c] == bytes.fromhex('2c c2 66')  # BIT, no fade call.
    assert a[0xcb] == b[0xcb] == qv['regs'][0x10] == 0x60
    records = []
    for sprite in range(4, 8):
        low = pv['regs'][sprite * 2]
        speed = a[0xf0 + sprite - 2]
        high_phase = bool(a[0xe8 + sprite])
        assert low >= speed  # These four actual transitions do not borrow.
        new = low - speed
        if not high_phase:
            assert new >= 6  # These actual low-phase transitions do not wrap.
        assert qv['regs'][sprite * 2] == new
        assert pv['regs'][sprite * 2 + 1] == qv['regs'][sprite * 2 + 1]
        assert a[0xe8 + sprite] == b[0xe8 + sprite]
        assert a[0xf0 + sprite - 2] == b[0xf0 + sprite - 2]
        assert qv['sprites'][sprite]['x'] == new + (256 if b[0xcb] & (1 << sprite) else 0)
        records.append(dict(sprite=sprite, old_low_x=low, speed=speed, new_low_x=new,
                            high_phase=high_phase, actual_x=qv['sprites'][sprite]['x'],
                            y=qv['regs'][sprite * 2 + 1]))
    return dict(previous=previous['entry']['snapshot'], current=current['entry']['snapshot'],
                snapshot_field_base_delta=312 * 63,
                scope='Source-exact no-borrow/no-wrap branches for these four transitions only.', sprites=records)


def field(number, before, after, original, known):
    ram, vic = before['ram'], before['state']['vicii']
    regs = vic['regs']
    assert geometry(before) == dict(bank=0xc000, bitmap=0xe000, screen=0xcc00,
                                    D011=0x3b, D016=0xc7, D018=0x38, D020=0)
    assert before['state']['cia']['CIA2']['pra'] == 0xf8
    assert before['state']['cia']['CIA2']['ddra'] == 0x3f
    assert regs[0x15] == 255 and regs[0x17] & 0xf0 == 0
    assert regs[0x1b] == 0 and regs[0x1c] & 0xf0 == 0xf0 and regs[0x1d] == 255
    assert regs[9:16:2] == [113, 85, 96, 120]
    assert (regs[0x25], regs[0x26], *regs[0x2b:0x2f]) == (1, 3, 14, 14, 14, 14)
    assert not any(51 <= y <= 154 for y in regs[1:8:2])
    assert vic['sprite_dma'] == vic['sprite_display_bits'] == 0
    assert before['pipe']['sprite_active_bits'] == before['pipe']['sprite_pending_bits'] == 0
    assert before['meta']['current_line'] == vic['raster_line'] == 152
    assert after['meta']['current_line'] == after['state']['vicii']['raster_line'] == 250
    assert field_base(before) == field_base(after)
    assert bytes(ram[0xcffc:0xd000]) == bytes([0x28, 0x29, 0x2a, 0x2b])
    assert [vic['sprites'][sprite]['pointer'] for sprite in range(4, 8)] == [0x28, 0x29, 0x2a, 0x2b]
    assert before['pipe']['sprite_pri_bits'] == 0
    assert before['pipe']['sprite_mc_bits'] == 0xf2 and before['pipe']['sprite_expx_bits'] == 255
    assert all(before['pipe']['sprite_x_pipe_' + str(sprite)] == vic['sprites'][sprite]['x'] for sprite in range(4, 8))
    for first, end in STABLE:
        assert ram[first:end] == after['ram'][first:end]
    assert all(known[0x7400:0x7500])
    assert ram[0xca00:0xcb00] == ram[0x7400:0x7500] == original[0x7400:0x7500]
    # The actual last upper matrix row is still latched at B400 entry.
    assert vic['vcbase'] == 480 and vic['rc'] == 5
    assert bytes(vic['vbuf']) == ram[0xcde0:0xce08]
    assert vic['cbuf'] == vic['color_ram'][480:520]
    actual = after['raster'][51 * 384:155 * 384]
    independent, selected, overlaps = compose(before)
    errors = delta(actual, independent)
    assert not errors, errors[:10]
    actual_path = OUT / ('field-%02d-upper-actual.indices' % number)
    expected_path = OUT / ('field-%02d-upper-independent.indices' % number)
    actual_path.write_bytes(actual)
    expected_path.write_bytes(independent)
    controls = []
    for variant in ('no_sprites', 'sprites_as_hires', 'no_x_expansion', 'bitmap_multicolor',
                    'sprites_behind_bitmap', 'reverse_sprite_priority'):
        alternative, _, _ = compose(before, variant)
        errors = delta(actual, alternative)
        control_path = OUT / ('field-%02d-control-%s.json' % (number, variant))
        control_path.write_text(json.dumps(dict(variant=variant, differences=errors,
            difference_count=len(errors), discriminating=bool(errors),
            explanation=('No overlapping nontransparent sprite pixels in these samples.'
                         if variant == 'reverse_sprite_priority' and not errors else None)), indent=2) + '\n')
        if variant != 'reverse_sprite_priority':
            assert errors, variant
        controls.append(dict(variant=variant, differences=len(errors), evidence=artifact(control_path),
                             discriminating=bool(errors)))
    stale = delta(before['raster'][51 * 384:155 * 384], independent)
    stale_path = OUT / ('field-%02d-prestate-tail-control.json' % number)
    stale_path.write_text(json.dumps(dict(assumption='All104 rows in the line152 pre-snapshot are current-field output.',
                                         differences=stale, discriminating=bool(stale)), indent=2) + '\n')
    if number == 1:
        assert len(stale) == 70 and {e['line'] for e in stale} == {152, 153, 154}
    prefix = actual[:35 * 384]
    return dict(number=number, pre=before['entry'], post=after['entry'], lines=[51, 154],
                rows=104, width=384, pixels=len(actual), nonzero_pixels=sum(bool(v) for v in actual),
                snapshot_field_base_clock=field_base(before),
                actual=artifact(actual_path), independent=artifact(expected_path), differences=[],
                geometry=geometry(before), sprite_x=[vic['sprites'][s]['x'] for s in range(4, 8)],
                sprite_y=regs[9:16:2], sprite_selected_pixels=selected, sprite_nontransparent_overlaps=overlaps,
                saved_pointer_latches=[vic['sprites'][s]['pointer'] for s in range(4, 8)],
                stable_inputs=[dict(first=a, end_exclusive=z, sha256=sha(ram[a:z])) for a, z in STABLE],
                actual_upper_matrix_latch=dict(vcbase=480, rc=5, screen_first=0xcde0, bytes=40,
                                               VBUF_sha256=sha(bytes(vic['vbuf'])), CBUF_sha256=sha(bytes(vic['cbuf']))),
                sprite_free_prefix=dict(lines=[51, 85], pixels=len(prefix), nonzero_pixels=sum(bool(v) for v in prefix), sha256=sha(prefix)),
                controls=controls, prestate_current_row_tail_control=dict(evidence=artifact(stale_path), differences=len(stale))), independent


def latch_witnesses(pinned, layout, reader):
    rows = []
    for name in ('pixel-row-post', 'job-09-post', 'job-13-post', 'job-28-post'):
        capture = native(pinned[name], layout, reader)
        ram, vic, pipe = capture['ram'], capture['state']['vicii'], capture['pipe']
        geom = geometry(capture)
        assert geom['bank'] == geom['bitmap'] == 0x4000 and geom['screen'] == 0x6000
        fetch_vc = (vic['vc'] - 1) & 1023
        address = geom['bitmap'] + ((fetch_vc << 3) | vic['rc'])
        assert 18 <= vic['raster_cycle'] <= 53 and 0 < vic['vmli'] < 40
        assert ram[address] == vic['gbuf'] == pipe['gbuf_pipe0'] != 0
        matrix_first = geom['screen'] + vic['vcbase']
        assert bytes(vic['vbuf']) == ram[matrix_first:matrix_first + 40]
        assert vic['cbuf'] == vic['color_ram'][vic['vcbase']:vic['vcbase'] + 40]
        sprites = []
        for sprite in range(4, 8):
            data = vic['sprites'][sprite]
            if not vic['sprite_dma'] & (1 << sprite) or not data['data']:
                continue
            row = vic['raster_line'] - vic['regs'][sprite * 2 + 1] - 1
            first = geom['bank'] + data['pointer'] * 64 + row * 3
            assert 0 <= row < 21
            assert data['data'] == int.from_bytes(ram[first:first + 3], 'big')
            sprites.append(dict(sprite=sprite, pointer=data['pointer'], row=row, address=first,
                                bytes=list(ram[first:first + 3]), actual_VIC_data=data['data']))
        rows.append(dict(checkpoint=capture['entry'], geometry=geom,
                         line=vic['raster_line'], raw_cycle=vic['raster_cycle'],
                         VC=vic['vc'], fetch_VC=fetch_vc, RC=vic['rc'], VMLI=vic['vmli'],
                         bitmap_address=address, actual_GBUF=vic['gbuf'], actual_pipe0=pipe['gbuf_pipe0'],
                         matrix_first=matrix_first, matrix_bytes=40, nonzero_sprite_latches=sprites,
                         scope='Earlier bank4000 upper fetches; not active bankC000 fetch witnesses for the four compared fields.'))
    assert sum(len(row['nonzero_sprite_latches']) for row in rows) == 2
    return rows


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    inputs = receipts()
    layout, reader = readers()
    original_proof = inputs['binary-analysis/side1-binary-proof.json']
    original = checked(original_proof['bundles'][36]['RAM'])
    known = checked(original_proof['bundles'][36]['known_mask'])
    assert all(known[0x3be8:0x3d93]) and all(known[0xb82a:0xb864])
    owner04 = inputs['native-upper-analysis/native-upper-evidence.json']
    owner05 = inputs['native-scanout-analysis/native-scanout-evidence.json']
    tail = inputs['native-tail-analysis/native-tail-evidence.json']
    for owner in (owner04, owner05, tail):
        assert owner['session']['closed_utc'] and owner['session']['exit_code'] == -15
        checked(owner['transcript'])
    for key in ('inputs', 'RAM_or_code_writes', 'register_or_PC_writes', 'resource_writes'):
        assert owner04['observation_audit'][key] == []
    assert owner05['data_or_PC_writes'] == tail['data_or_PC_writes'] == []
    assert owner05['warp_off_before_each_resume'] and tail['warp_off_before_each_resume']
    pinned04 = {entry['stem']: entry for entry in owner04['checkpoints']}
    pinned05 = {entry['stem']: entry for entry in owner05['checkpoints']}
    pinned06 = {entry['stem']: entry for entry in tail['checkpoints']}
    fields, oracles, motions = [], [], []
    previous = native(pinned04['publication-post'], layout, reader)
    publication = inputs['upper-analysis/upper-proof.json']['publication']
    assert publication['post']['snapshot'] == previous['entry']['snapshot']
    assert publication['completed_before_swap'] and publication['completed_image_preserved_until_publication']
    assert geometry(previous) == dict(bank=0xc000, bitmap=0xe000, screen=0xcc00,
                                      D011=0x3b, D016=0xc7, D018=0x38, D020=0)
    baseline = previous['ram']
    prepared_image = inputs['upper-analysis/upper-proof.json']['completed_chain']['independent_final_image']
    assert not prepared_image['differences']
    assert sha(baseline[0xe000:0xf040]) == prepared_image['bitmap_sha256']
    assert sha(baseline[0xcc00:0xce08]) == prepared_image['screen_sha256']
    for number, pre_name, post_name in ((1, 'field-pre', 'field-post'),
                                      (2, 'field-02-pre', 'field-02-post'),
                                      (3, 'field-03-pre', 'field-03-post'),
                                      (4, 'restored-arcade', 'floor-line-drawn')):
        before = native(pinned05[pre_name] if number == 4 else pinned04[pre_name], layout, reader)
        after = native(pinned06[post_name] if number == 4 else pinned04[post_name], layout, reader)
        if number == 4:
            for module in ('C64MEM', 'MAINCPU', 'VIC-II', 'CIA1', 'CIA2'):
                assert reader.module_payload(ROOT / before['entry']['snapshot']['path'], module) == reader.module_payload(ROOT / pinned04['field-04-pre']['snapshot']['path'], module)
            assert tail['parent'] == pinned05['field-post']['snapshot']
        for first, end in STABLE:
            assert baseline[first:end] == before['ram'][first:end] == after['ram'][first:end]
        motions.append(code_and_motion(previous, before, original))
        result, oracle = field(number, before, after, original, known)
        fields.append(result)
        oracles.append(oracle)
        previous = after
    history = owner04['separate_upper_D016_stores']
    assert len(history) == 3 and all(e['pc'] == 0xb857 and e['a'] == 0xc7 and e['line'] == 251 for e in history)
    assert len({row['actual']['sha256'] for row in fields}) == 4
    assert len({row['sprite_free_prefix']['sha256'] for row in fields}) == 1
    floor = inputs['sprite-scanout-analysis/sprite-scanout-proof.json']
    assert floor['full_96_row_floor'] and floor['full_floor']['pixels'] == 96 * 384
    assert floor['native06_tail']['checkpoints']['floor-line-drawn'] == pinned06['floor-line-drawn']
    assert floor['snapshots']['restored-arcade'] == pinned05['restored-arcade']
    floor_actual = checked(floor['full_floor']['actual'])
    floor_oracle = checked(floor['full_floor']['independent'])
    final = native(pinned06['floor-line-drawn'], layout, reader)
    observed = final['raster'][51 * 384:250 * 384] + bytes(final['state']['vicii']['dbuf'][104:488])
    joined_actual, joined_oracle = checked(fields[3]['actual']) + floor_actual, oracles[3] + floor_oracle
    assert observed == joined_actual == joined_oracle and len(observed) == 200 * 384
    combined_path, combined_oracle_path = OUT / 'field04-200rows-actual.indices', OUT / 'field04-200rows-independent.indices'
    combined_path.write_bytes(joined_actual)
    combined_oracle_path.write_bytes(joined_oracle)
    source = sources(inputs['arcade-source-proof.json'])
    latches = latch_witnesses(pinned04, layout, reader)
    result = dict(pass_=True, script=artifact(Path(__file__)),
                  scope='Four complete104x384 upper strips; one coherent200x384 bitmap-window composition joined to the already proved same-field floor.',
                  receipts=[artifact(BASE / name) for name in PINS], source=source,
                  snapshot_layout_reader=artifact(ROOT / 'research/anomaly/scanout.py'),
                  snapshot_schema_reader=artifact(ROOT / 'research/quondam/snapshot_state.py'),
                  original_RAM=original_proof['bundles'][36]['RAM'], original_known_mask=original_proof['bundles'][36]['known_mask'],
                  fields=fields, compared_upper_pixels=sum(row['pixels'] for row in fields),
                  upper_fields=4, distinct_upper_outputs=4, distinct_front_bitmap_images=1,
                  distinct_front_attribute_images=1, identical_sprite_free_prefixes=4,
                  original_sprite_bytes=256, motion_history=motions,
                  independently_prepared_published_image=prepared_image,
                  observed_upper_D016_history=history,
                  mode_and_sprite_code=dict(music_irq=0x3be8, D011_store=0x3bf8,
                      D01D_store=0x3c07, sprite_XY_range=[0x3c0e, 0x3d80], D010_store=0x3d80,
                      upper_D016_store=0xb857, upper_D018_store=0xb85c, upper_DD02_store=0xb861),
                  actual_earlier_upper_fetch_latches=latches,
                  same_field_combination=dict(field=4, lines=[51, 250], rows=200, width=384,
                      pixels=len(observed), completed_raster_rows=199, completed_current_DBUF_rows=1,
                      actual=artifact(combined_path), independent=artifact(combined_oracle_path),
                      final_snapshot=pinned06['floor-line-drawn']['snapshot'], final_clock=167013188,
                      source_floor_receipt=artifact(BASE / 'sprite-scanout-analysis/sprite-scanout-proof.json')),
                  bus_write_phase_certified=False, physical_chip_proven=False,
                  whole_frame_or_runtime_witness_complete=False,
                  limits=[
                      'Four fields reuse one prepared wall bitmap/attribute image. Moving upper sprites make the four output strips distinct.',
                      'No continuously traced upper-bank/D018/D011/sprite register history; actual endpoints, original code/motion, D016 observations and exact independent output are distinct evidence.',
                      'Native04 line152 snapshots retain the final upper matrix row, but the active nonzero graphics/sprite fetch witnesses are earlier bank4000 captures, not active bankC000 latches in these four fields.',
                      'Reverse sprite priority is inconclusive because these retained nontransparent sprite rows do not overlap.',
                      'The combined200-row interval excludes top/bottom raster lines outside51..250 and is not a complete312-line frame or FPS/deadline proof.',
                      'No emulator, native process, downloaded host code or original6502 instructions are executed by this producer.'])
    result['pass'] = result.pop('pass_')
    (OUT / 'upper-scanout-proof.json').write_text(json.dumps(result, indent=2) + '\n')
    (OUT / 'upper_scanout.checked.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(passed=True, upper_fields=4, rows_per_field=104,
        upper_palette_indices=result['compared_upper_pixels'], distinct_upper_outputs=4,
        prepared_wall_images=1, same_field_combined_rows=200, same_field_combined_pixels=len(observed),
        new_native_execution=False, whole_frame_or_FPS_proof=False)))


if __name__ == '__main__':
    main()
