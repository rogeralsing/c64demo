#!/usr/bin/env python3
"""Finite MOS8565 MC-text draw transform for two original Aloft body windows.

This recognizes a fixed source mode and its finite eight-pixel pipeline. It is
not a CPU/VIC machine interpreter and never uses target pixels as model inputs.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-pixels-20261109/display-analysis'
ARCHIVE = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
ARCHIVE_SHA = '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'
READER = ROOT / 'research/the-hat/raster_hardware.py'
READER_SHA = 'f9d15a6d26b877f63591b3c1ff7e31d3cf9430165783c89cb53b35ea6e32a12f'
NATIVE_BASE = ROOT / 'build/research/aloft-execution-20261109/native-01'
NATIVE_PROOF = ROOT / 'build/research/aloft-execution-20261109/native-analysis/accepted-02/native-proof.json'
NATIVE_SHA = '5db9694db276541a5fd2b5cb386e92639e6da2c0d6cd644caf758eb113cc2326'
MATH_BASE = ROOT / 'build/research/aloft-execution-20261109/cell-analysis/accepted-01'
MATH_SHA = 'b3bf0ae5e74059bc17b29717174587bb679bfe3701a388dad0f9a3d88b8ebdf5'
TAIL_PROOF = ROOT / 'build/research/aloft-pixels-20261109/tail-analysis/accepted-01/tail-guard-proof.json'
TAIL_SHA = 'f88ec772bd11d0c6e4669b0541578319cd6c1500e57a4ae8d66e57116c130029'
PHYSICAL_PROOF = ROOT / 'build/research/aloft-pixels-20261109/physical-analysis/accepted-01/physical-fetch-proof.json'
PHYSICAL_SHA = 'e4e815d4b793cbeb85c693ba6b963d5f0c3e41f7641ab5e36ec0c00a1d805678'
STORE_PROOF = BASE / 'source-route-01/store-route-proof.json'
STORE_SHA = '2e7acf05f320399b27759d8811a0c0c074ba47511ac0466418740d65dfbf483a'
GLYPH_PROOF = ROOT / 'build/research/aloft-pixels-20261109/glyph-analysis/accepted-01/glyph-stream-proof.json'
GLYPH_SHA = '5628a150bac452423de3ccc2a4a2fc2ef67c5abb9372f0fe57f6c8bbb8be45a8'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=sha(raw))


def pinned(path, expected):
    raw = path.read_bytes()
    assert sha(raw) == expected, str(path)
    return raw


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def output_meta(path):
    return dict(name=path.name, bytes=path.stat().st_size, sha256=sha(path.read_bytes()))


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def source_contract():
    """Read only pinned official C data/source; never compile or execute it."""
    pinned(ARCHIVE, ARCHIVE_SHA)
    names = ['viciisc/vicii-draw-cycle.c', 'viciisc/vicii-draw.c',
             'viciisc/vicii-cycle.c', 'viciisc/vicii-chip-model.c',
             'viciisc/vicii-timing.h', 'viciisc/vicii-timing.c',
             'viciisc/vicii.c', 'raster/raster-line.c']
    sources, members = {}, []
    with tarfile.open(ARCHIVE) as archive:
        for name in names:
            member = 'vice-3.10/src/' + name
            raw = archive.extractfile(member).read()
            sources[name] = raw.decode()
            members.append(dict(member=member, bytes=len(raw), sha256=sha(raw)))
    spans = {
        'viciisc/vicii-draw-cycle.c': [(133, 225, ['COL_D021, COL_D022, COL_D023, COL_CBUF_MC', 'i == xscroll_pipe', 'gbuf_mc_flop ^= 1']),
            (227, 295, ['vmode16_pipe2 = vmode16_pipe', 'gbuf_pipe1_reg = gbuf_pipe0_reg', 'gbuf_pipe0_reg = vicii.gbuf', 'vicii.cbuf[dmli]']),
            (541, 575, ['border_state = vicii.main_border', 'memset(render_buffer, COL_D020, 8)']),
            (606, 663, ['pixel_buffer[lookup_index] == last_color_reg', 'vicii.dbuf[offs + i] = pixel_buffer[i]', 'pixel_buffer[i] = render_buffer[i]']),
            (672, 688, ['vicii.raster_cycle == 1', 'draw_graphics8(cycle_flags_pipe)', 'cycle_flags_pipe = vicii.cycle_flags'])],
        'viciisc/vicii-chip-model.c': [(260, 268, ['"MOS8565"', '63,', '312,', '0,               /* color latency */']),
            (738, 765, ['case FetchG:', 'PHI1_FETCH_G', 'FetchC)', 'entry |= VISIBLE_M'])],
        'viciisc/vicii-cycle.c': [(175, 200, ['check_vborder_bottom', 'vicii.vborder = vicii.set_vborder', 'vicii.main_border = 1']),
            (391, 411, ['next_vicii_cycle()', 'cycle_phi1_fetch', 'check_hborder', 'vicii_draw_cycle()']),
            (447, 482, ['vicii_cycle_end_of_line()', 'vicii.raster_line++', 'vicii.vborder = vicii.set_vborder'])],
        'viciisc/vicii-draw.c': [(68, 101, ['#define DBUF_OFFSET (17 * 8 - vicii.screen_leftborderwidth)', 'src = &(vicii.dbuf[DBUF_OFFSET + xs * 8])', 'memcpy(dest, src'])],
        'viciisc/vicii.c': [(170, 195, ['vicii.screen_leftborderwidth + VICII_SCREEN_XPIX', 'vicii.first_displayed_line', 'vicii.raster.dont_cache_all = 1']),
            (418, 438, ['vicii_raster_draw_handler', 'raster_line_emulate(&vicii.raster)'])],
        'viciisc/vicii-timing.h': [(30, 36, ['NORMAL_LEFTBORDERWIDTH      0x20', 'NORMAL_RIGHTBORDERWIDTH     0x20']),
            (68, 73, ['0x10', '0x11f']), (116, 117, ['NORMAL_WIDTH', 'NORMAL_HEIGHT'])],
        'viciisc/vicii-timing.c': [(124, 133, ['case MACHINE_SYNC_PAL:', 'case VICII_NORMAL_BORDERS:', 'VICII_PAL_NORMAL_FIRST_DISPLAYED_LINE'])],
        'raster/raster-line.c': [(651, 680, ['raster_draw_buffer_ptr_update', 'first_displayed_line', 'handle_visible_line']),
            (708, 710, ['raster->current_line++'])],
    }
    atlas = {}
    for name, blocks in spans.items():
        rows = sources[name].splitlines()
        atlas[name] = []
        for first, last, needles in blocks:
            text = '\n'.join(rows[first - 1:last]) + '\n'
            for needle in needles:
                assert needle in text, (name, first, needle)
            atlas[name].append(dict(first_line=first, last_line=last, text=text, sha256=sha(text.encode())))
    table = sources['viciisc/vicii-chip-model.c'].split('cycle_tab_pal[] = {', 1)[1].split('};', 1)[0]
    rows = re.findall(r'\{ Phi([12])\((\d+)\),\s*(0x[0-9a-f]+),\s*(.*?),\s*(\w+(?:\([^)]*\))?),\s*(.*?),\s*(.*?)\s*\}', table)
    assert len(rows) == 126
    schedule = []
    for cycle in range(63):
        one, two = rows[cycle * 2:cycle * 2 + 2]
        assert one[:2] == ('1', str(cycle + 1)) and two[:2] == ('2', str(cycle + 1))
        schedule.append(dict(cycle=cycle, phi1_graphics_fetch=one[4] == 'FetchG',
                             visible_flag=two[4] == 'FetchC',
                             border_left_CSEL1='ChkBrdL1' in (one[6] + two[6]),
                             border_right_CSEL1='ChkBrdR1' in (one[6] + two[6])))
    assert [x['cycle'] for x in schedule if x['phi1_graphics_fetch']] == list(range(15, 55))
    assert [x['cycle'] for x in schedule if x['visible_flag']] == list(range(14, 54))
    assert [x['cycle'] for x in schedule if x['border_left_CSEL1']] == [16]
    assert [x['cycle'] for x in schedule if x['border_right_CSEL1']] == [56]
    return members, atlas, schedule


def mc_text_byte(value, cbuf, palette):
    """Four MSB-first two-bit symbols, each held for two physical pixels."""
    assert 0 <= value <= 255 and 8 <= cbuf <= 15
    assert len(palette) == 3 and all(0 <= x <= 15 for x in palette)
    colors = [*palette, cbuf & 7]
    return bytes(colors[(value >> shift) & 3] for shift in (6, 6, 4, 4, 2, 2, 0, 0))


def draw_fixed_row(glyphs, palette, border_color, schedule, seed=0):
    """Specialized finite source transform: 63 eight-pixel groups, no machine.

    Fixed conditions: model8565 latency0, MC text, cbuf8, XSCROLL0,
    CSEL1, no active/pending sprites, open vertical border, no color writes.
    The line begins with main/border latches closed from preceding right edge.
    All visible results erase arbitrary incoming byte/shift pipeline values.
    """
    assert len(glyphs) == 40 and 0 <= seed <= 255
    pipe0, pipe1, shift = seed, seed ^ 255, seed
    cpipe0 = cpipe1 = cbuf = 8
    xscroll = 0
    mc_flop, pixel = seed & 1, seed & 3
    border_state = main_border = 1
    previous_tokens = [seed & 15] * 8
    dbuf = bytearray([255] * 520)
    offset = 0
    trace = []
    for cycle in range(1, 63):
        if schedule[cycle]['border_left_CSEL1']:
            main_border = 0
        if schedule[cycle]['border_right_CSEL1']:
            main_border = 1
        rendered = []
        for i in range(8):
            if i == xscroll:
                shift, cbuf, mc_flop = pipe1, cpipe1, 1
            if mc_flop:
                pixel = shift >> 6
            shift = (shift << 1) & 255
            mc_flop ^= 1
            rendered.append((0x21, 0x22, 0x23, cbuf & 7)[pixel])
        pipe1, cpipe1 = pipe0, cpipe0
        vis = schedule[cycle - 1]['visible_flag']
        pipe0 = glyphs[cycle - 15] if vis else 0
        cpipe0 = 8 if vis else cpipe0
        if border_state:
            rendered = [0x20] * 8
        border_state = main_border
        regs = {0x20: border_color, 0x21: palette[0], 0x22: palette[1], 0x23: palette[2]}
        resolved = bytes(regs.get(token, token) for token in previous_tokens)
        dbuf[offset:offset + 8] = resolved
        previous_tokens = rendered
        trace.append(dict(cycle=cycle, dbuf_first=offset, viewport_first=offset - 104,
                          latched_graphics_column=cycle - 15 if vis else None,
                          border_latch=border_state))
        offset += 8
    viewport = bytes(dbuf[104:488])
    assert len(viewport) == 384
    return viewport, trace


def finite_domain(schedule):
    """Exhaust byte alphabet in each of40 columns, with displaced seed states."""
    cases, digest = 0, hashlib.sha256()
    palette, border = [14, 10, 4], 4
    for seed in (0, 255, 0x55, 0xaa):
        for value in range(256):
            glyphs = bytes((value + col * 73) & 255 for col in range(40))
            result, _ = draw_fixed_row(glyphs, palette, border, schedule, seed)
            direct = bytes([border] * 32) + b''.join(mc_text_byte(x, 8, palette) for x in glyphs) + bytes([border] * 32)
            assert result == direct
            digest.update(result)
            cases += 1
    row, trace = draw_fixed_row(bytes(range(40)), palette, border, schedule)
    return dict(rows=cases, glyph_column_cases=cases * 40, every_byte_in_every_column=True,
                arbitrary_incoming_byte_seed_domain=[0, 255, 0x55, 0xaa],
                seed_samples_are_checks_not_a_universal_state_enumeration=True,
                independence_argument='Before the viewport begins, continuous left border replaces prior pixel tokens. Invisible cycles clear both g pipes; first visible cbuf8/gbuf values reach render17 and dbuf18. Every active group then loads a new shift register at pixel0.',
                results_sha256=digest.hexdigest(), example_pipeline=trace,
                graphics_x=[32, 352], body_raster_y=[48, 248], normal_viewport_y=[32, 232])


def prestate(reader, label):
    stem, expected = ('dispatcher', '566bb2963054ed3d95cbd6e4caf3a2ad45d84fcf80c5bbda6ee77b3d5d3bf114') if label == 'first' else ('later-dispatcher', 'e72b0f34c71f6c13c031ba07adf25510c812bd54ed2e048cca54cbce55584019')
    path = NATIVE_BASE / (stem + '.vsf')
    pinned(path, expected)
    state = reader.read_extended_snapshot(path, border_mode=0)
    vic = state['vicii']
    draw = state['raster_hardware_extension']['draw_pipeline']['values']
    assert vic['model'] == 1 and (vic['raster_line'], vic['raster_cycle']) == (47, 24)
    assert [vic[k] for k in ('vborder', 'set_vborder', 'main_border')] == [0, 0, 0]
    assert (vic['regs'][0x11], vic['regs'][0x16], vic['regs'][0x18], vic['regs'][0x15]) == (0x18, 0x18, 0x10, 0)
    assert vic['cbuf'] == [8] * 40
    assert vic['sprite_display_bits'] == vic['sprite_dma'] == 0
    assert draw['sprite_pending_bits'] == draw['sprite_active_bits'] == 0
    assert draw['xscroll_pipe'] == draw['vmode11_pipe'] == 0
    assert draw['vmode16_pipe'] == draw['vmode16_pipe2'] == 4
    assert draw['cregs'][:16] == list(range(16)) and draw['last_color_reg'] == 255
    assert draw['cregs'][0x20:0x24] == vic['regs'][0x20:0x24]
    return dict(label=label, capture=meta(path), raster=[47, 24],
                initial_clock=130204329 if label == 'first' else 131462313,
                genuine_border_and_mode=dict(vborder=0, set_vborder=0, main_border=0, D011=24, D016=24, D018=16),
                palette=vic['regs'][0x21:0x24], border_color=vic['regs'][0x20], cbuf=vic['cbuf'],
                initial_draw_pipeline=draw,
                initial_line47_idle=bool(vic['idle_state']),
                line47_excluded=True, rows16_through46_not_independently_predicted=True)


def mode_lifetime_guards():
    """Parse the raw wire solely for control-mode absence and source PC/order.

    Native pixel values, GBUF, post-call RAM and post-call snapshots are never
    read here. Direct-store register values are discarded by this projection.
    """
    path = ROOT / 'research/aloft-execution-20261109/native.py'
    pinned(path, '99bea080d4e2fa74f4c3656dfd6084af752e0747247c1ef67e7688c1ec92d967')
    native = module('display_frozen_native_wire', path)
    profile_path = ROOT / 'build/research/aloft-execution-20261109/native-analysis/closed-profile-01.json'
    profile = json.loads(pinned(profile_path, 'cb077129b7206a748cbc0e562c63ffe7dc0e66778a0cfd3d79cd55b384472fb6'))
    wire, case, adapter = native.audit_wire(profile, ROOT / profile['case_relative'])
    generations = native.checkpoint_generations(case)
    hooks = native.trace_hooks(case, wire, generations, captures=[])
    mathematical = json.loads(pinned(MATH_BASE / 'cell-execution-proof.json', MATH_SHA))
    tail = json.loads(pinned(TAIL_PROOF, TAIL_SHA))
    assert mathematical['pass_'] is True and tail['pass_'] is True
    assert all(x['source_memory_write_set_empty'] and x['no_reported_hook_during_wait'] for x in tail['comparisons'])
    rows = []
    for label, first_sequence, last_sequence, first_clock, last_clock in (
            ('first', 61, 104, 130204329, 130216971),
            ('later', 136, 164, 131462313, 131474955)):
        watches = []
        for lo, hi in ((0xd000, 0xd03f), (0xdd00, 0xdd03)):
            found = [g for g in generations if g['kind'] == 'TRACE' and g['operation'] == 'Trace store'
                     and g['first'] == lo and g['last'] == hi and g['created_sequence'] < first_sequence
                     and g.get('deleted_sequence', 10**9) > last_sequence]
            assert len(found) == 1
            point = found[0]
            assert native.enabled_at(point, first_sequence)
            assert not any(first_sequence < u['sequence'] <= last_sequence and u['command'].startswith(('disable ', 'condition ')) for u in point['updates'])
            watches.append(dict(first=lo, last=hi, checkpoint=point['id'], setup=point['setup'],
                                attached_r_sequence=point['attached_r_sequence'], interval_sequences=[first_sequence, last_sequence]))
        selected = [h for h in hooks if first_clock < h['registers']['clock'] <= last_clock
                    and h['operation'] == 'store' and 0xd000 <= h['monitored_address'] < 0xe000]
        assert len(selected) == 375
        assert all(h['monitored_address'] == 0xd011 for h in selected)
        prediction_meta = next(f['full_prediction'] for f in mathematical['fields'] if f['label'] == label)
        prediction_path = MATH_BASE / prediction_meta['name']
        prediction = json.loads(pinned(prediction_path, prediction_meta['sha256']))
        expected = [x for x in prediction['predicted_D011_accesses'] if x['operation'] == 'store']
        assert all(0x18 <= x['value'] <= 0x1f for x in expected)
        assert [(h['instruction_PC'], h['monitored_address']) for h in selected] == [(x['instruction_PC'], x['address']) for x in expected]
        rows.append(dict(label=label, clocks=[first_clock, last_clock], watches=watches,
                         mathematical_prediction=meta(prediction_path),
                         predicted_D011_values=sorted(set(x['value'] for x in expected)),
                         all375_actual_VIC_store_hooks_are_source_D011=True,
                         no_D015_D016_D018_color_or_CIA2_store_in_interval=True,
                         source_and_external_actor_assumptions=prediction['source_closure']['machine_assumptions'],
                         control_projection=[dict(instruction_PC=h['instruction_PC'], instruction_hex=h['instruction_hex'],
                             address=h['monitored_address'], completion_clock=h['registers']['clock'],
                             received_first=h['received_first'], received_end=h['received_end'],
                             raw_block_sha256=h['raw_block_sha256']) for h in selected]))
    return dict(inputs=[meta(path), meta(profile_path), meta(MATH_BASE / 'cell-execution-proof.json'), meta(TAIL_PROOF)],
                all_raw_hooks_parsed=len(hooks), fields=rows,
                expected_native_pixel_values_used=False,
                typed_source_closure_not_endpoint_equality_proves_no_other_stores=True,
                watched_ranges_are_continuous_but_not_all_IO_mirrors=True,
                raw_bus_access_timestamps_not_inferred=True)


def predict_body(glyph_bytes, genuine, schedule):
    assert len(glyph_bytes) == 8000 and genuine['cbuf'] == [8] * 40
    full, graphics = bytearray(), bytearray()
    for index in range(200):
        glyphs = glyph_bytes[index * 40:(index + 1) * 40]
        row, _ = draw_fixed_row(glyphs, genuine['palette'], genuine['border_color'], schedule)
        reference = bytes([genuine['border_color']] * 32) + b''.join(mc_text_byte(x, 8, genuine['palette']) for x in glyphs) + bytes([genuine['border_color']] * 32)
        assert row == reference
        full.extend(row)
        graphics.extend(row[32:352])
    assert len(full) == 76800 and len(graphics) == 64000
    return bytes(full), bytes(graphics)


def inverse_injective_graphics(graphics, palette):
    """Late oracle check only: recover the input bytes from four distinct colors."""
    colors = [*palette, 0]
    assert len(graphics) == 64000 and len(set(colors)) == 4
    selectors = {color: index for index, color in enumerate(colors)}
    result = bytearray()
    for first in range(0, len(graphics), 8):
        pixels = graphics[first:first + 8]
        assert all(pixels[i] == pixels[i + 1] for i in (0, 2, 4, 6))
        value = 0
        for pixel in pixels[::2]:
            assert pixel in selectors
            value = (value << 2) | selectors[pixel]
        result.append(value)
    assert len(result) == 8000
    return bytes(result)


def compare_body_oracle(reader, out, label, predicted, genuine, glyph_bytes):
    """Called only after BOTH fields' independent output files are on disk."""
    stem, expected = ('after-line', 'e9db1366ee980a27ec5d9120305faad04a3cd379b6d9a70cfbced94948bdd3ce') if label == 'first' else ('later-after-line', 'b18c8b1763bacad19fd2ea9fe4c71823dc958dc1c7df43bcbc76cae017afdb95')
    path = NATIVE_BASE / (stem + '.vsf')
    pinned(path, expected)
    state = reader.read_extended_snapshot(path, border_mode=0)
    vic = state['vicii']
    store = state['raster_hardware_extension']['raster_store']
    assert (vic['raster_line'], vic['raster_cycle'], store['current_line']) == (248, 3, 248)
    assert vic['model'] == 1 and (store['width'], store['height'], store['pitch']) == (384, 312, 384)
    raw = reader.framebuffer_bytes(path)
    body = raw[384 * 48:384 * 248]
    assert len(body) == 76800
    observed = out / (label + '-oracle-body-384x200.bin')
    observed.write_bytes(body)
    differences = [i for i, (a, b) in enumerate(zip(predicted, body)) if a != b]
    assert not differences, (label, len(differences), differences[:16])
    graphics = b''.join(body[y * 384 + 32:y * 384 + 352] for y in range(200))
    result = dict(label=label, snapshot=meta(path), oracle_export=output_meta(observed),
                  compared_palette_indices=76800, differences=0,
                  graphics_indices=64000, body_raster=[48, 248], graphics_x=[32, 352],
                  snapshot_stop=[248, 3], raster_store_current_line=store['current_line'],
                  body_fully_committed=True, target_data_used_only_after_predictions_written=True,
                  palette_degenerate=len(set([*genuine['palette'], 0])) != 4)
    if label == 'later':
        recovered = inverse_injective_graphics(graphics, genuine['palette'])
        assert recovered == glyph_bytes
        inverse_path = out / 'later-inverse-oracle-glyph-bytes.bin'
        inverse_path.write_bytes(recovered)
        result['independent_late_inverse'] = dict(palette=[*genuine['palette'], 0], injective=True,
            recovered_bytes=8000, all_equal_independent_glyph_stream=True, output=output_meta(inverse_path))
    else:
        result['black_oracle_cannot_discriminate_glyph_bits'] = True
    return result


def load_glyph_predictions():
    assert GLYPH_PROOF is not None and GLYPH_SHA is not None, 'pending independent glyph ABI pin'
    proof = json.loads(pinned(GLYPH_PROOF, GLYPH_SHA))
    physical = json.loads(pinned(PHYSICAL_PROOF, PHYSICAL_SHA))
    assert proof['pass_'] is True and physical['pass_'] is True
    assert len(proof['fields']) == 2
    results = {}
    for field in proof['fields']:
        label = field['label']
        assert label in ('first', 'later') and label not in results
        assert (field['rows'], field['requests']) == (200, 8000)
        row_meta, byte_meta = field['row_prediction'], field['byte_stream']
        assert row_meta['name'] == label + '-glyph-rows.json'
        assert byte_meta['name'] == label + '-glyph-fetch-bytes.bin'
        row_path, byte_path = GLYPH_PROOF.parent / row_meta['name'], GLYPH_PROOF.parent / byte_meta['name']
        rows = json.loads(pinned(row_path, row_meta['sha256']))
        stream = pinned(byte_path, byte_meta['sha256'])
        assert len(stream) == byte_meta['bytes'] == 8000
        assert rows['label'] == label and len(rows['rows']) == 200
        initial_clock = 130204329 if label == 'first' else 131462313
        all_bytes = bytearray()
        for index, row in enumerate(rows['rows']):
            assert row['call_index'] == index and row['raster_line'] == index + 48
            clocks = [initial_clock + 54 + index * 63 + column for column in range(40)]
            assert row['fetch_clocks'] == clocks
            assert row['absolute_line_number'] == clocks[0] // 63
            logical, physical_addresses = row['logical_glyph_addresses'], row['physical_addresses']
            assert len(logical) == len(physical_addresses) == len(row['fetched_bytes']) == 40
            assert logical == physical_addresses and all(0 <= a < 0x800 for a in logical)
            all_bytes.extend(row['fetched_bytes'])
        assert bytes(all_bytes) == stream
        assert rows['first_g_clock'] == initial_clock + 54
        assert rows['last_g_clock'] == initial_clock + 12630
        results[label] = dict(stream=stream, row_source=meta(row_path), byte_source=meta(byte_path),
                              first_g_clock=rows['first_g_clock'], last_g_clock=rows['last_g_clock'])
    assert set(results) == {'first', 'later'}
    return proof, results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--source-only', action='store_true')
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(BASE)
    out.mkdir(parents=True, exist_ok=False)
    checked = out / 'display_contract.checked.py'
    checked.write_bytes(Path(__file__).read_bytes())
    members, anchors, schedule = source_contract()
    finite = finite_domain(schedule)
    write_json(out / 'primary-draw-source.json', dict(archive=meta(ARCHIVE), members=members, anchors=anchors, schedule=schedule))
    write_json(out / 'finite-pipeline-domain.json', finite)
    proof = dict(pass_=True, producer=meta(Path(__file__).resolve()), source_only=args.source_only,
                 store_clock_contract=meta(STORE_PROOF), independent_pixel_oracle_opened=False,
                 no_CPU_VIC_interpreter_native_build_or_downloaded_host_execution=True,
                 geometry=dict(raw_framebuffer=[384, 312], normal_viewport_raster=[16, 288],
                               predicted_body_raster=[48, 248], predicted_graphics_x=[32, 352],
                               body_in_normal_viewport_y=[32, 232], dbuf_copy_offset=104),
                 finite_domain=dict(rows=finite['rows'], glyph_column_cases=finite['glyph_column_cases']),
                 accepted_native_pixel_comparison=False,
                 limits=['Fixed MC-text mode, CSEL1/XSCROLL0, sprites inactive, open vertical border and constant color registers only.',
                         'The first partial raster47 and preceding viewport rows are excluded, not borrowed as independent predictions.',
                         'Physical mapping and source-derived row-byte timing require separately frozen receipts.',
                         'No physical chip/analog output, full field, animation, scene identity or FPS claim.'])
    pinned(STORE_PROOF, STORE_SHA)
    if not args.source_only:
        pinned(NATIVE_PROOF, NATIVE_SHA)
        pinned(READER, READER_SHA)
        reader = module('display_frozen_extended_reader', READER)
        glyph_proof, glyphs = load_glyph_predictions()
        control = mode_lifetime_guards()
        genuine = {label: prestate(reader, label) for label in ('first', 'later')}
        write_json(out / 'genuine-prestate.json', genuine)
        write_json(out / 'mode-lifetime-guards.json', control)
        predictions, frozen_predictions = {}, []
        for label in ('first', 'later'):
            full, graphics = predict_body(glyphs[label]['stream'], genuine[label], schedule)
            full_path = out / (label + '-predicted-body-384x200.bin')
            graphics_path = out / (label + '-predicted-graphics-320x200.bin')
            full_path.write_bytes(full)
            graphics_path.write_bytes(graphics)
            predictions[label] = full
            frozen_predictions.extend([meta(full_path), meta(graphics_path)])
        # Both independent fields are now persisted. Only now open native pixels.
        comparisons = [compare_body_oracle(reader, out, label, predictions[label], genuine[label], glyphs[label]['stream'])
                       for label in ('first', 'later')]
        for row in frozen_predictions:
            assert meta(ROOT / row['path']) == row
        proof.update(inputs=[meta(NATIVE_PROOF), meta(READER), meta(GLYPH_PROOF), meta(PHYSICAL_PROOF),
                             meta(MATH_BASE / 'cell-execution-proof.json'), meta(TAIL_PROOF)],
                     independent_pixel_oracle_opened=True,
                     both_predictions_persisted_before_first_pixel_oracle_open=True,
                     accepted_native_pixel_comparison=True,
                     predicted_outputs=[dict(name=Path(x['path']).name, bytes=x['bytes'], sha256=x['sha256']) for x in frozen_predictions],
                     row_byte_inputs=[dict(label=label, row_source=glyphs[label]['row_source'],
                                          byte_source=glyphs[label]['byte_source']) for label in ('first', 'later')],
                     comparisons=comparisons,
                     body_palette_index_comparisons=153600,
                     graphics_palette_index_comparisons=128000,
                     later_inverse_glyph_bytes=8000,
                     first_black_pixel_comparison_is_degenerate=True,
                     copied_target_pixels_or_gbuf_used_as_prediction_input=False)
    proof['outputs'] = [output_meta(p) for p in sorted(out.iterdir()) if p.is_file()]
    path = out / 'display-contract-proof.json'
    write_json(path, proof)
    print(json.dumps(meta(path)))


if __name__ == '__main__':
    main()
