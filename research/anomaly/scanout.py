#!/usr/bin/env python3
"""Reconstruct bounded Anomaly floor scanout from retained original observations.

No CPU, emulator, hardware response or downloaded program is executed. The
oracle indexes the real bitmap and screen cells directly. The output side is
the palette-index raster buffer serialized by VICE, not a screenshot decoder.
"""
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import sys
import tarfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/anomaly'
OUT = BASE / 'scanout-analysis'
NATIVE_SHA = '53274dec47bf09e196878d973ec6c5f10782497d61ff36cf50f97db31bc108fd'
NATIVE05_SHA = '70fe556b8c80bf6a73721b4f51852e30bc9f6b103f1e3bff06e4e2e1b1e7dfa2'
BINARY_SHA = 'b8744b0184128330a069a7366c4f843193306074f4a55a03d10f092a6fa8800c'
HELPER_SHA = 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a'
ARCHIVE_SHA = '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'
SOURCES = (
    'src/viciisc/vicii-snapshot.c', 'src/viciisc/vicii-draw-cycle.c',
    'src/viciisc/vicii-fetch.c', 'src/viciisc/vicii-cycle.c',
    'src/viciisc/vicii-draw.c', 'src/raster/raster-snapshot.c',
    'src/raster/raster.c')
TRACE = re.compile(
    r'^#(?P<checkpoint>\d+) \(Trace\s+(?P<kind>store|exec)\s+(?P<target>[0-9a-f]{4})\)\s+'
    r'(?P<line>\d+)/\$[0-9a-f]+,\s+(?P<cycle>\d+)/\$[0-9a-f]+\n'
    r'\.C:(?P<pc>[0-9a-f]+)\s+[^\n]*?'
    r'- A:(?P<a>[0-9a-f]+) X:(?P<x>[0-9a-f]+) Y:(?P<y>[0-9a-f]+) '
    r'SP:(?P<sp>[0-9a-f]+) [^\n]*?\s+(?P<clock>\d+)\n', re.M | re.I)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def checked(item):
    data = (ROOT / item['path']).read_bytes()
    assert len(data) == item['bytes'] and sha(data) == item['sha256']
    return data


def proof(path, expected):
    assert sha(path.read_bytes()) == expected, ('Changed parent receipt', path)
    result = json.loads(path.read_text())
    assert result['pass']
    return result


def sources():
    """Read the official source archive; do not execute any archived code."""
    archive = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    assert sha(archive.read_bytes()) == ARCHIVE_SHA
    records, text = [], {}
    with tarfile.open(archive, 'r:gz') as tar:
        for name in SOURCES:
            member = 'vice-3.10/' + name
            data = tar.extractfile(member).read()
            target = OUT / 'source' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            records.append(dict(member=member, **artifact(target)))
            text[name] = data.decode()
    # These guards tie the parser and the independent geometry to the actual
    # serialized fields and fetch/draw rules in this exact release.
    guards = {
        'src/viciisc/vicii-snapshot.c': [
            'SMW_BA(m, vicii.dbuf, VICII_DRAW_BUFFER_SIZE)',
            'vicii_draw_cycle_snapshot_write(m)',
            'raster_snapshot_write(m, &vicii.raster)'],
        'src/viciisc/vicii-draw-cycle.c': [
            'SMW_B(m, gbuf_pipe0_reg)', 'SMW_DW(m, (uint32_t)cycle_flags_pipe)',
            'memset(render_buffer, COL_D020, 7)',
            'render_buffer[7] = COL_D020;',
            'COL_VBUF_L, COL_VBUF_L, COL_VBUF_H, COL_VBUF_H,',
            'vbuf_reg = vbuf_pipe1_reg;', 'gbuf_reg = gbuf_pipe1_reg;',
            'if (i == xscroll_pipe)', 'vicii.dbuf[offs + i] = pixel_buffer[i];'],
        'src/viciisc/vicii-fetch.c': [
            'a = (vicii.vc << 3) | vicii.rc;',
            'a |= (vicii.regs[0x18] & 0x8) << 10;',
            'vicii.vbuf[vicii.vmli] = fetch_phi2(v_fetch_addr(vicii.vc));',
            'vicii.vmli++;', 'vicii.vc++;', 'vicii.gbuf = data;'],
        'src/viciisc/vicii-draw.c': [
            '#define DBUF_OFFSET (17 * 8 - vicii.screen_leftborderwidth)',
            'src = &(vicii.dbuf[DBUF_OFFSET + xs * 8]);'],
        'src/raster/raster-snapshot.c': [
            'SMW_DW(m, raster->current_line)',
            'SMW_DW(m, draw_buffer->draw_buffer_pitch)',
            'SMW_BA(m, draw_buffer->draw_buffer_padded_allocations[0], padded_size)'],
        'src/raster/raster.c': [
            '*padded_size = fb_width * (fb_height + 4);',
            '*unpadded_offset = fb_width * 2;'],
    }
    for name, needles in guards.items():
        for needle in needles:
            assert needle in text[name], (name, needle)
    return dict(archive=artifact(archive), files=records,
                urls=['https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/',
                      'https://vice-emu.sourceforge.io/vice_12.html'],
                source_guards=sum(map(len, guards.values())))


def reader():
    path = ROOT / 'research/quondam/snapshot_state.py'
    assert sha(path.read_bytes()) == HELPER_SHA
    spec = importlib.util.spec_from_file_location('anomaly_snapshot_reader', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def draw_state(payload):
    """Read the previously opaque174-byte draw pipe and raster allocation."""
    # VIC core1881 bytes is decoded/guarded by the frozen parent reader.
    offset = 1881
    fields = {}

    def take(name, size, array=False):
        nonlocal offset
        raw = payload[offset:offset + size]
        assert len(raw) == size
        offset += size
        fields[name] = list(raw) if array else int.from_bytes(raw, 'little')

    for name in ('gbuf_pipe0', 'cbuf_pipe0', 'vbuf_pipe0', 'gbuf_pipe1',
                 'cbuf_pipe1', 'vbuf_pipe1', 'xscroll_pipe', 'vmode11_pipe',
                 'vmode16_pipe', 'vmode16_pipe2', 'gbuf_reg', 'gbuf_mc_flop',
                 'gbuf_pixel_reg', 'cbuf_reg', 'vbuf_reg', 'dmli'):
        take(name, 1)
    for index in range(8):
        take('sprite_x_pipe_' + str(index), 4)
    for name in ('sprite_pri_bits', 'sprite_mc_bits', 'sprite_expx_bits',
                 'sprite_pending_bits', 'sprite_active_bits', 'sprite_halt_bits'):
        take(name, 1)
    for index in range(8):
        take('sbuf_reg_' + str(index), 4)
    take('sbuf_pixel_reg', 8, True)
    for name in ('sbuf_expx_flops', 'sbuf_mc_flops', 'border_state'):
        take(name, 1)
    for name, size in (('render_buffer', 8), ('pri_buffer', 8),
                       ('pixel_buffer', 8), ('cregs', 47)):
        take(name, size, True)
    take('last_color_reg', 1)
    take('last_color_value', 1)
    take('cycle_flags_pipe', 4)
    assert offset == 2055
    current, width, height, pitch = struct.unpack_from('<4I', payload, offset)
    offset += 16
    assert (width, height, pitch) == (384, 312, 384)
    allocation = payload[offset:]
    assert len(allocation) == width * (height + 4)
    raster = allocation[2 * width:2 * width + pitch * height]
    return fields, dict(current_line=current, width=width, height=height,
                        pitch=pitch, header_payload_offset=2055,
                        padded_allocation_payload_offset=offset,
                        top_padding_lines=2, allocation_sha256=sha(allocation),
                        raster_sha256=sha(raster)), raster


def native_state(module, directory, name, pinned):
    entry = pinned[name]
    ram = checked(entry['ram'])
    path = ROOT / entry['snapshot']['path']
    checked(entry['snapshot'])
    assert path == directory / (name + '.vsf')
    state = module.read_snapshot(path)
    assert ram == module.module_payload(path, 'C64MEM')[4:65540]
    draw, meta, raster = draw_state(module.module_payload(path, 'VIC-II'))
    return ram, state, draw, meta, raster


def first24_model(ram, field):
    """Direct cell/bit indexing, without emulating6502 or VICE draw code."""
    rows = []
    for index in range(24):
        row, fine = divmod(index, 8)
        row += 13
        scroll = ram[8 + index] & 7
        assert field['writes'][index]['a'] == ram[8 + index]
        assert field['writes'][index]['line'] == 155 + index
        pixels = []
        for cell in range(40):
            bits = ram[0x4000 + 320 * row + 8 * cell + fine]
            attribute = ram[0x6000 + 40 * row + cell]
            pixels.extend(attribute >> 4 if bits & (128 >> bit)
                          else attribute & 15 for bit in range(8))
        result = bytearray(384)  # Actual stable D020=0, including both borders.
        # The CSEL=0 transition preserves pixel7 at the left edge and masks
        # pixel7 at the right edge. Source-derived interval, not fitted crop.
        result[32 + 7:32 + 311] = bytes(pixels[7 - scroll:311 - scroll])
        rows.append(bytes(result))
    return b''.join(rows)


def check_field(module, field, pinned, original, directory=None):
    directory = directory or BASE / 'native-04'
    before, pre, pre_draw, pre_meta, _ = native_state(module, directory, field['pre'], pinned)
    after, post, post_draw, post_meta, raster = native_state(module, directory, field['post'], pinned)
    pv, qv = pre['vicii'], post['vicii']
    assert (pv['raster_line'], qv['raster_line']) == (152, 250)
    assert (pv['vcbase'], pv['rc'], pv['idle_state'], pv['ysmooth'],
            pv['allow_bad_lines'], pv['reg11_delay']) == (480, 5, 0, 3, 1, 0x3b)
    assert post_meta['current_line'] == 250 and post_meta['current_line'] > 178
    assert pv['regs'][0x11] == qv['regs'][0x11] == 0x3b  # hires bitmap, DEN
    assert pv['regs'][0x20] == qv['regs'][0x20] == 0
    assert pv['regs'][0x16] & 0x18 == qv['regs'][0x16] & 0x18 == 0
    assert pv['sprite_dma'] == pv['sprite_display_bits'] == 0
    assert pre_draw['sprite_active_bits'] == pre_draw['sprite_pending_bits'] == 0
    # None of the eight saved spriteY values can start DMA in155..178.
    # The only Y stores in the bounded first24-line code set sprites2/3 to208.
    ys = pv['regs'][1:16:2]
    assert not any(155 <= value <= 178 for value in ys)
    assert before[0xb446:0xb44e] == bytes.fromhex('a9 d0 8d 05 d0 8d 07 d0')
    # Bind executable code to original Sparkle bytes, allowing only the four
    # source-labelled, live immediate operands in this actual captured path.
    patches = {0xb40c, 0xb442, 0xb44f, 0xb47f}
    source_differences = [a for a in range(0xb400, 0xb54a)
                          if before[a] != original[a]]
    assert set(source_differences) <= patches
    assert before[0xb400:0xb54a] == after[0xb400:0xb54a]
    # Bank1 setup and hires bitmap/screen selection execute before C/G fetch.
    assert before[0xb466:0xb47a] == bytes.fromhex(
        'a9 3d 8d 02 dd b5 08 8d 16 d0 a9 80 8d 18 d0 8e 17 d0 e8 b5')
    cia = post['cia']['CIA2']
    assert cia['pra'] == pre['cia']['CIA2']['pra'] == 0xf8
    assert cia['ddra'] == 0x3d and qv['regs'][0x18] == 0x80
    pins = (cia['pra'] & cia['ddra']) | (3 & ~cia['ddra'])
    bank = ((~pins) & 3) * 0x4000
    screen = bank + ((qv['regs'][0x18] & 0xf0) << 6)
    bitmap = bank + ((qv['regs'][0x18] & 8) << 10)
    assert (bank, screen, bitmap) == (0x4000, 0x6000, 0x4000)
    stable = ((0x5040, 0x5400), (0x6208, 0x6280), (8, 32))
    for first, end in stable:
        assert before[first:end] == after[first:end]
    actual = b''.join(raster[line * 384:(line + 1) * 384] for line in range(155, 179))
    expected = first24_model(before, field)
    differences = [dict(line=155 + index // 384, x=index % 384,
                        actual=a, expected=b)
                   for index, (a, b) in enumerate(zip(actual, expected)) if a != b]
    # Retain the failed initial edge assumption as an explicit negative check.
    # It would include graphics x311 instead of the real CSEL0 right border.
    rejected = []
    for index in range(24):
        row, fine = divmod(index, 8)
        row += 13
        scroll = before[index + 8] & 7
        source_x = 311 - scroll
        cell, bit = divmod(source_x, 8)
        bits = before[0x4000 + 320 * row + cell * 8 + fine]
        attribute = before[0x6000 + 40 * row + cell]
        value = attribute >> 4 if bits & (128 >> bit) else attribute & 15
        observed = actual[index * 384 + 343]
        if value != observed:
            rejected.append(dict(line=155 + index, x=343,
                                 actual=observed, rejected_expected=value))
    assert rejected and not differences
    actual_path = OUT / ('field-%02d-actual.indices' % field['number'])
    expected_path = OUT / ('field-%02d-independent.indices' % field['number'])
    actual_path.write_bytes(actual)
    expected_path.write_bytes(expected)
    return dict(number=field['number'], pre=pinned[field['pre']], post=pinned[field['post']],
                decoded_raster=post_meta, lines=[155, 178], rows=24, width=384,
                pixels=len(expected), active_pixels=24 * 304,
                actual_sha256=sha(actual), independent_sha256=sha(expected),
                actual_indices=artifact(actual_path), independent_indices=artifact(expected_path),
                differences=differences, bank=bank, screen=screen, bitmap=bitmap,
                stable_input_ranges=[dict(first=a, end_exclusive=b,
                                          sha256=sha(before[a:b])) for a, b in stable],
                D016_values=list(before[8:32]), source_patch_addresses=source_differences,
                VIC_entry_counters={key: pv[key] for key in
                    ('vcbase', 'vc', 'rc', 'vmli', 'ysmooth', 'idle_state', 'allow_bad_lines')},
                sprite_Y_at_entry=ys,
                rejected_x8_through_x311_assumption=rejected)


def nested_artifacts(value):
    """Collect artifact identities without assuming the owner's receipt schema."""
    result = []
    if isinstance(value, dict):
        if all(key in value for key in ('path', 'bytes', 'sha256')):
            result.append({key: value[key] for key in ('path', 'bytes', 'sha256')})
        for child in value.values():
            result.extend(nested_artifacts(child))
    elif isinstance(value, list):
        for child in value:
            result.extend(nested_artifacts(child))
    return result


def extension_check(receipt_path, receipt_sha, module, original):
    """Consume the sole owner's closed native05 capture, without execution."""
    owner = proof(receipt_path, receipt_sha)
    inventory = nested_artifacts(owner)
    directory = BASE / 'native-05'
    names = ('restored-arcade', 'first-row-fetched', 'floor-strip-complete',
             'floor-strip-drawn', 'field-post')
    pinned = {}
    for name in names:
        entry = dict(stem=name,
                     ram=artifact(directory / ('ram-' + name + '.bin')),
                     snapshot=artifact(directory / (name + '.vsf')))
        assert entry['ram'] in inventory and entry['snapshot'] in inventory
        pinned[name] = entry
    transcript = artifact(directory / 'monitor.log')
    assert transcript in inventory
    events = []
    for match in TRACE.finditer(checked(transcript).decode()):
        raw = match.groupdict()
        event = {key: int(value, 10 if key in ('checkpoint', 'line', 'cycle', 'clock') else 16)
                 for key, value in raw.items() if key != 'kind'}
        event['kind'] = raw['kind'].lower()
        events.append(event)
    stores = [event for event in events if event['kind'] == 'store']
    scroll = [event for event in stores if event['target'] == 0xd016]
    assert len(scroll) == 96 and [event['line'] for event in scroll] == list(range(155, 251))
    field = dict(number=4, pre='restored-arcade', post='field-post', writes=scroll)
    strip = check_field(module, field, pinned, original, directory)
    states = {name: native_state(module, directory, name, pinned) for name in names}
    initial = states['restored-arcade'][0]
    # This scope has no B857 upper setup store; all96 recorded D016 accesses
    # belong to this floor field. The owner audit checks the actual session.
    history = [event for event in stores
               if event['target'] in (0xd011, 0xd018, 0xd020, 0xdd00, 0xdd02)]
    assert [(event['target'], event['pc'], event['a'], event['line']) for event in history] == [
        (0xdd02, 0xb468, 0x3d, 154), (0xd018, 0xb472, 0x80, 155),
        (0xd018, 0xb472, 0x80, 163), (0xd018, 0xb472, 0x80, 171)]
    first_ram, first, first_pipe, _, _ = states['first-row-fetched']
    fv = first['vicii']
    assert (fv['raster_line'], fv['raster_cycle'], fv['vcbase'], fv['vc'],
            fv['rc'], fv['vmli'], fv['bad_line']) == (155, 59, 520, 560, 1, 40, 1)
    assert bytes(fv['vbuf']) == first_ram[0x6208:0x6230]
    assert fv['cbuf'] == fv['color_ram'][520:560]
    assert (first_pipe['xscroll_pipe'], first_pipe['vmode11_pipe'],
            first_pipe['vmode16_pipe']) == (initial[8] & 7, 8, 0)
    expected = first24_model(initial, field)
    assert fv['dbuf_offset'] >= 447
    first_active = bytes(fv['dbuf'][143:447])
    assert first_active == expected[39:343]
    ram, state, pipe, _, _ = states['floor-strip-complete']
    vic = state['vicii']
    assert (vic['raster_line'], vic['raster_cycle'], vic['vcbase'], vic['vc'],
            vic['rc'], vic['vmli']) == (178, 53, 600, 639, 7, 39)
    # fetch_graphics() saves GBUF, then increments VC/VMLI. At this stop,
    # the last fetched cell therefore used638, not the saved postincrement639.
    fetched_vc = (vic['vc'] - 1) & 0x3ff
    fetched_address = 0x4000 + ((fetched_vc << 3) | vic['rc'])
    assert fetched_address == 0x53f7
    assert vic['gbuf'] == pipe['gbuf_pipe0'] == ram[fetched_address] == 7
    assert bytes(vic['vbuf']) == ram[0x6258:0x6280]
    assert vic['cbuf'] == vic['color_ram'][600:640]
    _, drawn, drawn_pipe, drawn_meta, raster = states['floor-strip-drawn']
    dv = drawn['vicii']
    assert (dv['raster_line'], dv['raster_cycle'], drawn_meta['current_line']) == (178, 59, 178)
    assert dv['dbuf_offset'] >= 447
    assert dv['sprite_dma'] == dv['sprite_display_bits'] == 0
    assert drawn_pipe['sprite_pending_bits'] == drawn_pipe['sprite_active_bits'] == 0
    prior_rows = raster[155 * 384:178 * 384]
    final_active = bytes(dv['dbuf'][143:447])
    assert prior_rows == expected[:23 * 384]
    assert final_active == expected[23 * 384 + 39:23 * 384 + 343]
    return dict(owner_receipt=artifact(receipt_path), transcript=transcript,
                checkpoints=pinned, field=strip, observer_register_history=history,
                register_history_scope='Reported instruction boundaries; no bus-clock normalization.',
                first_badline_latches=dict(vcbase=520, vc=560, vmli=40, rc=1,
                    screen_first=0x6208, screen_bytes=40, vbuf_sha256=sha(bytes(fv['vbuf'])),
                    color_ram_first=520, color_ram_bytes=40, cbuf_sha256=sha(bytes(fv['cbuf'])),
                    active_pixels=304, actual_sha256=sha(first_active)),
                interior_graphics_fetch=dict(line=178, raw_cycle=53, saved_vc=639,
                    fetch_vc=fetched_vc, row_counter=7, address=fetched_address,
                    RAM_value=ram[fetched_address], GBUF=vic['gbuf'],
                    draw_pipe0=pipe['gbuf_pipe0'], source_rule='Fetch saves GBUF before incrementing VC/VMLI.'),
                prefix_draw=dict(committed_raster_rows=23, current_line_active_pixels=304,
                    exact=True, active_sprite_bits=0,
                    basis='Completed prior rows plus already written current-line DBUF; stale tail pixels excluded.'))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    native_path = BASE / 'native-upper-analysis/native-upper-evidence.json'
    native = proof(native_path, NATIVE_SHA)
    binary_path = BASE / 'binary-analysis/side1-binary-proof.json'
    binary = proof(binary_path, BINARY_SHA)
    original = checked(binary['bundles'][36]['RAM'])
    known = checked(binary['bundles'][36]['known_mask'])
    assert all(known[0xb400:0xb54a])
    pinned = {item['stem']: item for item in native['checkpoints']}
    source = sources()
    module = reader()
    fields = [check_field(module, field, pinned, original) for field in native['floor_fields']]
    assert len(fields) == 3
    extension = extension_check(BASE / 'native-scanout-analysis/native-scanout-evidence.json',
                                NATIVE05_SHA, module, original)
    fields.append(extension['field'])
    result = dict(pass_=True, scope='Four coherent24-line floor strips, including borders, and saved native matrix/graphics latch witnesses.',
                  source=source,
                  script=artifact(Path(__file__)), snapshot_reader=artifact(ROOT / 'research/quondam/snapshot_state.py'),
                  native_receipt=artifact(native_path), original_binary_receipt=artifact(binary_path),
                  rejected_checker_guard=artifact(OUT / 'rejected-source-guard.json'),
                  rejected_checker_producer=artifact(OUT / 'rejected-source-guard-producer.py'),
                  rejected_single_D018_assumption=artifact(OUT / 'rejected-single-D018.json'),
                  rejected_single_D018_producer=artifact(OUT / 'rejected-single-D018-producer.py'),
                  original_RAM=binary['bundles'][36]['RAM'], original_known_mask=binary['bundles'][36]['known_mask'],
                  fields=fields, native05_fetch_and_draw=extension,
                  compared_pixels=sum(f['pixels'] for f in fields),
                  independently_reconstructed=True, full_floor_or_upper_scanout=False,
                  bus_write_phase_certified=False, runtime_witness_complete=False,
                  limits=['No full6502/VIC simulation or physical-chip result.',
                          'No claim that monitor store time is the register bus-write phase.',
                          'No sprite-overlap, later floor lines, upper-wall pixels or full-screen oracle.',
                          'Serialized current-field rows are consumed only after their raster draw completed.',
                          'Saved native fetch/latch witnesses cover the first matrix row and one interior graphics byte; no claim that every fetch was bus-traced.'])
    result['pass'] = result.pop('pass_')
    (OUT / 'scanout-proof.json').write_text(json.dumps(result, indent=2) + '\n')
    (OUT / 'scanout.checked.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(passed=True, fields=len(fields), rows_per_field=24,
                          palette_index_pixels=result['compared_pixels'],
                          native_graphics_fetch_address=extension['interior_graphics_fetch']['address'],
                          full_floor_scanout=False, certified_bus_phase=False)))


if __name__ == '__main__':
    main()
