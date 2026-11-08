#!/usr/bin/env python3
"""Passive independent Anomaly floor/sprite composition from closed evidence.

This is a direct bit/pair-to-pixel oracle with a bounded vertical DMA counter
model. It does not execute C64 code or reproduce the VICE cycle renderer.
"""
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
OUT = BASE / 'sprite-scanout-analysis'
SCANOUT_SHA = 'c5e63a07f3060614710518aaf9b9e6c9365c297619af4e19719a4b5f8b62198f'
OWNER_SHA = '70fe556b8c80bf6a73721b4f51852e30bc9f6b103f1e3bff06e4e2e1b1e7dfa2'
TAIL_SHA = '6a059c275606b55e1fc6bfa14a6ac2093112548981fb78182209883d2274ba9e'
FROZEN_SHA = '9cb1ba973b5cb94b69e6b6e2735bcc524b25593fb8d96e5d9959beb352cae1ff'
BINARY_SHA = 'b8744b0184128330a069a7366c4f843193306074f4a55a03d10f092a6fa8800c'
SOURCE_RECEIPT_SHA = '30e681b44b72f7a610bd8b151762813c591ad7339b153ca8ce8d18117e61e729'
ARCHIVE_SHA = '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def checked(item):
    data = (ROOT / item['path']).read_bytes()
    assert len(data) == item['bytes'] and sha(data) == item['sha256']
    return data


def receipt(path, expected):
    assert sha(path.read_bytes()) == expected, ('Changed receipt', path)
    result = json.loads(path.read_text())
    assert result['pass']
    return result


def helpers():
    path = ROOT / 'research/anomaly/scanout.py'
    assert sha(path.read_bytes()) == SCANOUT_SHA
    spec = importlib.util.spec_from_file_location('frozen_anomaly_scanout', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Reuse only its pinned snapshot decoder and serialized raster layout.
    return module, module.reader()


def source_rules():
    archive = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    assert sha(archive.read_bytes()) == ARCHIVE_SHA
    guards = {
        'vicii-fetch.c': [
            'vicii.sprite[i].pointer = fetch_phi1(v_fetch_addr(0x3f8 + i));',
            'sprdata = fetch_phi1((vicii.sprite[i].pointer << 6) + vicii.sprite[i].mc);',
            'vicii.sprite[i].mc &= 0x3f;'],
        'vicii-cycle.c': [
            'vicii.sprite[i].mc = vicii.sprite[i].mcbase;',
            'vicii.sprite[i].mcbase = vicii.sprite[i].mc;',
            'if (vicii.sprite[i].mcbase == 63)',
            'vicii.sprite[i].exp_flop ^= 1;',
            'vicii.sprite[i].mcbase = 0;', 'vicii.sprite[i].exp_flop = 1;'],
        'vicii-mem.c': [
            'if (value == vicii.regs[0x17])',
            'if (!(value & b) && !vicii.sprite[i].exp_flop)',
            'if (cycle_is_check_spr_crunch(vicii.cycle_flags))',
            'vicii.sprite[i].mc = (0x2a & (mcbase & mc)) | (0x15 & (mcbase | mc));'],
        'vicii-draw-cycle.c': [
            'for (s = 7; s >= 0; --s)',
            'sbuf_pixel_reg[s] = (uint8_t)((sbuf_reg[s] >> 22) & 0x03);',
            'sbuf_pixel_reg[s] = (uint8_t)(((sbuf_reg[s] >> 23) & 0x01 ) << 1);',
            'uint8_t spri = sprite_pri_bits & (1 << as);',
            'if (!(pixel_pri && spri))', 'render_buffer[i] = COL_D025;',
            'render_buffer[i] = COL_D027 + as;', 'render_buffer[i] = COL_D026;'],
        'vicii-chip-model.c': [
            '{ Phi1(1),  0x194, None,    SprPtr(3)',
            '{ Phi1(58), 0x164, None,    SprPtr(0)',
            '{ Phi1(60), 0x174, None,    SprPtr(1)',
            '{ Phi1(62), 0x184, None,    SprPtr(2)',
            'UpdateMcBase', 'ChkSprDma', 'ChkSprExp', 'ChkSprDisp'],
    }
    files = []
    with tarfile.open(archive, 'r:gz') as tar:
        for name, needles in guards.items():
            member = 'vice-3.10/src/viciisc/' + name
            data = tar.extractfile(member).read()
            text = data.decode()
            assert all(needle in text for needle in needles), name
            target = OUT / 'source' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            files.append(dict(member=member, **artifact(target)))
    return dict(archive=artifact(archive), files=files,
                guarded_rules=sum(map(len, guards.values())),
                url='https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/')


def bitmap_line(ram, line):
    n = line - 155
    row, fine = divmod(n, 8)
    row += 13
    scroll = ram[8 + n] & 7
    pixels, foreground = [], []
    for cell in range(40):
        bits = ram[0x4000 + row * 320 + cell * 8 + fine]
        attr = ram[0x6000 + row * 40 + cell]
        for bit in range(8):
            on = bool(bits & (128 >> bit))
            pixels.append(attr >> 4 if on else attr & 15)
            foreground.append(on)
    output = bytearray(384)
    priority = [False] * 384
    output[39:343] = bytes(pixels[7 - scroll:311 - scroll])
    priority[39:343] = foreground[7 - scroll:311 - scroll]
    return output, priority


def store_inventory(ram):
    """Decode the bounded original control block statically, never execute it.

    Its admitted opcodes contain no indirect/indexed stores or calls. Every
    possible write therefore has a literal target; none can mutate artwork.
    """
    lengths = {op: 1 for op in (0x58, 0x9a, 0xba, 0xc8, 0xca, 0xe8, 0xea)}
    lengths.update({op: 2 for op in (0x24, 0x84, 0x85, 0x86, 0xa0, 0xa2,
                                    0xa6, 0xa9, 0xb5, 0xc0, 0xc1, 0xd0, 0xf0)})
    lengths.update({op: 3 for op in (0x0e, 0x4c, 0x8d, 0x8e, 0xbd, 0xcd, 0xee)})
    writes = {0x84, 0x85, 0x86, 0x8d, 0x8e, 0x0e, 0xee}
    allowed = {5, 6, 0xc9, 0xdf, 0xb559, 0xb55e, 0xdd02, 0xfffe, 0xffff}
    allowed.update(range(0xd000, 0xd02f))
    allowed.update(range(0x63f8, 0x63fc))
    pc, instructions, stores, jumps = 0xb400, set(), [], []
    while pc < 0xb828:
        instructions.add(pc)
        opcode = ram[pc]
        size = lengths[opcode]
        operand = int.from_bytes(ram[pc + 1:pc + size], 'little')
        if opcode in writes:
            assert operand in allowed, (pc, operand)
            stores.append(dict(pc=pc, opcode=opcode, target=operand))
        if opcode == 0x4c:
            jumps.append(operand)
        elif opcode in (0xd0, 0xf0):
            jumps.append(pc + 2 + (operand if operand < 128 else operand - 256))
        pc += size
    assert pc == 0xb828 and all(target in instructions | {0xb828} for target in jumps)
    return stores


def vertical_schedule(ram, vic, events):
    """Source-derived line recurrence, with no invented CPU bus timestamps.

    Sprite3 fetches early in each line; sprites0..2 fetch at the end of the
    previous line. Every relevant register/pointer store is separated from
    these fetch/counter decisions by a checked instruction-boundary margin.
    """
    states = [dict(mc=s['mc'], mcbase=s['mcbase'], exp_flop=s['exp_flop'],
                   dma=bool(vic['sprite_dma'] & (1 << i)),
                   display=bool(vic['sprite_display_bits'] & (1 << i)))
              for i, s in enumerate(vic['sprites'][:4])]
    regs = list(vic['regs'])
    pointers = list(ram[0x63f8:0x63fc])
    by_line = {}
    for e in events:
        by_line.setdefault(e['line'], []).append(e)
    pending = {}
    result, counter_history, fetches = {}, [], []

    def fetch(sprite, line, phase):
        state = states[sprite]
        if not state['dma']:
            return None
        counter = state['mc']
        address = 0x4000 + pointers[sprite] * 64 + counter
        assert counter <= 60 and counter % 3 == 0
        data = ram[address:address + 3]
        state['mc'] = (counter + 3) & 63
        record = dict(sprite=sprite, fetch_line=line, phase=phase,
                      pointer=pointers[sprite], byte_counter=counter,
                      address=address, bytes=list(data), data=int.from_bytes(data, 'big'))
        fetches.append(record)
        return record

    for line in range(179, 251):
        # Entry colors and coordinates precede the CPU's later same-line stores.
        # Sprite0/1 X64 pixels finish at PAL cycle24, before the D027 store.
        row = dict(regs=list(regs), sprites=dict(pending))
        early = fetch(3, line, 'early PAL cycles1..2')
        if early and states[3]['display']:
            row['sprites'][3] = early
        result[line] = row
        for state in states:
            if state['exp_flop']:
                state['mcbase'] = state['mc']
                if state['mcbase'] == 63:
                    state['dma'] = False
        # All lower-field D017/Y/pointer writes occur after PAL cycle16 and
        # before PAL cycle55. D027 is later than sprite0/1's rendered pixels.
        for e in by_line.get(line, []):
            target, value = e['target'], e['a']
            if target == 0xd017:
                assert 17 <= e['cycle'] <= 18 and value == 12
                old = regs[0x17]
                # The changed write occurs after the special PAL cycle15
                # crunch check. The handler also resets any NEW-zero-bit
                # sprite's low flop, even without a falling bit transition.
                if value != old:
                    assert all(state['exp_flop'] for i, state in enumerate(states)
                               if not value & (1 << i))
                regs[0x17] = value
            elif target == 0xd007:
                assert 23 <= e['cycle'] <= 24 and value == 240
                regs[7] = value
            elif 0x63f8 <= target <= 0x63fb:
                assert target == 0x63fb and 29 <= e['cycle'] <= 30 and value == 0x9a
                pointers[target - 0x63f8] = value
            elif target in (0xd025, 0xd026, 0xd027, 0xd029, 0xd02a):
                regs[target - 0xd000] = value
            else:
                assert target in (0xd016, 0xd012, 0xd019), hex(target)
        for i, state in enumerate(states):
            if regs[0x15] & (1 << i) and regs[2 * i + 1] == line and not state['dma']:
                state.update(dma=True, mcbase=0, exp_flop=1)
            if state['dma'] and regs[0x17] & (1 << i):
                state['exp_flop'] ^= 1
            state['mc'] = state['mcbase']
            if state['dma']:
                if regs[0x15] & (1 << i) and regs[2 * i + 1] == line:
                    state['display'] = True
            else:
                state['display'] = False
        counter_history.append(dict(line=line, after_PAL_cycle58=copy.deepcopy(states)))
        if line < 250:
            pending = {}
            for i in range(3):
                fetched = fetch(i, line, 'late PAL cycles%d..%d' % (58 + i * 2, 59 + i * 2))
                if fetched and states[i]['display']:
                    pending[i] = fetched
    return result, counter_history, fetches


def sprite_pixels(data, multicolor, expanded, colors):
    result = []
    if multicolor:
        for pair in range(12):
            value = (data >> (22 - 2 * pair)) & 3
            result.extend([colors[value]] * (4 if expanded else 2))
    else:
        for bit in range(24):
            value = bool(data & (1 << (23 - bit)))
            result.extend([colors[2] if value else None] * (2 if expanded else 1))
    return result


def compose(ram, schedule, line, variant=None):
    output, background_priority = bitmap_line(ram, line)
    row = schedule[line]
    regs = row['regs']
    sprites = dict(row['sprites'])
    if variant == 'no_sprites':
        sprites = {}
    mask = bytearray(384)
    contributions = {i: 0 for i in range(4)}
    # Lower index wins sprite/sprite priority, including when its selected
    # pixel is behind a bitmap foreground pixel. D01B is actually zero here.
    order = range(3, -1, -1) if variant == 'reverse_sprite_priority' else range(4)
    for sprite in order:
        if sprite not in sprites:
            continue
        data = sprites[sprite]['data']
        colors = [None, regs[0x25], regs[0x27 + sprite], regs[0x26]]
        multicolor = bool(regs[0x1c] & (1 << sprite))
        if variant == 'multicolor_as_hires':
            multicolor = False
        pixels = sprite_pixels(data, multicolor, bool(regs[0x1d] & (1 << sprite)), colors)
        xpos = regs[2 * sprite] + (256 if regs[0x10] & (1 << sprite) else 0) + 8
        for offset, color in enumerate(pixels):
            x = xpos + offset
            if color is None or not 39 <= x < 343 or mask[x]:
                continue
            mask[x] = sprite + 1
            if not (regs[0x1b] & (1 << sprite) and background_priority[x]):
                output[x] = color
                contributions[sprite] += 1
    return bytes(output), mask, contributions


def differences(actual, expected, first_line):
    return [dict(line=first_line + i // 384, x=i % 384, actual=a, expected=b)
            for i, (a, b) in enumerate(zip(actual, expected)) if a != b]


def frozen_prior():
    path = OUT / 'frozen-native05/freeze-manifest.json'
    assert sha(path.read_bytes()) == FROZEN_SHA
    manifest = json.loads(path.read_text())
    for item in manifest['files']:
        checked(item)
    producer = OUT / 'frozen-native05/sprite_scanout.py'
    proof = OUT / 'frozen-native05/sprite-scanout-proof.json'
    old = json.loads(proof.read_text())
    assert old['pass'] and old['total_new_compared_pixels'] == 27616
    assert not old['full_96_row_floor']
    return dict(manifest=artifact(path), producer=artifact(producer), receipt=artifact(proof),
                preserved_files=len(manifest['files']), prior_new_pixels=27616)


def complete_tail(frozen, reader, parent_entry, parent_raster):
    """Consume the sole native owner's closed original five-clock extension."""
    path = BASE / 'native-tail-analysis/native-tail-evidence.json'
    owner = receipt(path, TAIL_SHA)
    assert owner['session']['closed_utc'] and owner['session']['exit_code'] == -15
    for key in ('script', 'transcript', 'session_metadata', 'original_disk'):
        checked(owner[key])
    assert owner['parent'] == parent_entry['snapshot']
    checked(owner['parent'])
    assert owner['parent_owner_receipt']['sha256'] == OWNER_SHA
    checked(owner['parent_owner_receipt'])
    assert all(owner['restore'].values())
    assert owner['elapsed_cycles'] == 5 and owner['restores'] == owner['observation_resumes'] == 1
    entries = {entry['stem']: entry for entry in owner['checkpoints']}
    parent = ROOT / parent_entry['snapshot']['path']
    captures = {}
    for name in ('restored-floor-post', 'floor-line-drawn'):
        entry = entries[name]
        ram = checked(entry['ram'])
        checked(entry['snapshot'])
        snapshot = ROOT / entry['snapshot']['path']
        memory = reader.module_payload(snapshot, 'C64MEM')
        assert ram == memory[4:65540]
        state = reader.read_snapshot(snapshot)
        pipe, meta, raster = frozen.draw_state(reader.module_payload(snapshot, 'VIC-II'))
        cpu = reader.module_payload(snapshot, 'MAINCPU')
        decoded = dict(clock=int.from_bytes(cpu[:8], 'little'), a=cpu[8], x=cpu[9],
                       y=cpu[10], sp=cpu[11], pc=int.from_bytes(cpu[12:14], 'little'), flags=cpu[14])
        assert all(entry['registers'][key] == value for key, value in decoded.items())
        assert (memory[1], memory[0]) == (entry['registers']['port00'], entry['registers']['port01'])
        captures[name] = (ram, state, pipe, meta, raster, decoded, memory)
    restored = ROOT / entries['restored-floor-post']['snapshot']['path']
    for module in ('C64MEM', 'MAINCPU', 'VIC-II', 'CIA1', 'CIA2'):
        assert reader.module_payload(restored, module) == reader.module_payload(parent, module)
    before, pre, _, pre_meta, pre_raster, cpu0, mem0 = captures['restored-floor-post']
    after, post, _, post_meta, post_raster, cpu1, mem1 = captures['floor-line-drawn']
    assert (cpu0['pc'], cpu0['clock'], pre['vicii']['raster_line'], pre['vicii']['raster_cycle']) == (0xb828, 167013183, 250, 57)
    assert (cpu1['pc'], cpu1['clock'], post['vicii']['raster_line'], post['vicii']['raster_cycle']) == (0xb82a, 167013188, 250, 62)
    assert before[0xb828:0xb82a] == after[0xb828:0xb82a] == bytes.fromhex('e6 d9')
    assert [i for i in range(65536) if before[i] != after[i]] == [0xd9]
    assert after[0xd9] == (before[0xd9] + 1) & 255
    assert [i for i in range(len(mem0)) if mem0[i] != mem1[i]] == [4 + 0xd9]
    assert all(cpu0[key] == cpu1[key] for key in ('a', 'x', 'y', 'sp'))
    expected_flags = (cpu0['flags'] & ~0x82) | (after[0xd9] & 0x80) | (2 if after[0xd9] == 0 else 0)
    assert cpu1['flags'] == expected_flags
    assert pre['vicii']['regs'] == post['vicii']['regs']
    assert pre_meta['current_line'] == post_meta['current_line'] == 250
    assert pre['vicii']['dbuf_offset'] == 456 and post['vicii']['dbuf_offset'] == 496
    assert post['vicii']['dbuf_offset'] >= 104 + 384
    for chip in ('CIA1', 'CIA2'):
        for key in ('pra', 'prb', 'ddra', 'ddrb', 'cra', 'crb'):
            assert pre['cia'][chip][key] == post['cia'][chip][key]
    # Do not assert complete CIA equality across elapsed clocks: running timer
    # counters and TOD-relative scheduling naturally advance in this interval.
    assert parent_raster[155 * 384:250 * 384] == pre_raster[155 * 384:250 * 384] == post_raster[155 * 384:250 * 384]
    current = bytes(post['vicii']['dbuf'][104:488])
    assert current[:352] == bytes(pre['vicii']['dbuf'][104:456])
    return current, dict(owner_receipt=artifact(path), checkpoints=entries,
                         complete_restore_modules=['C64MEM', 'MAINCPU', 'VIC-II', 'CIA1', 'CIA2'],
                         elapsed_clocks=5, original_instruction=dict(pc=0xb828, bytes='e6 d9', mnemonic='INC $D9'),
                         RAM_delta=[dict(address=0xd9, before=before[0xd9], after=after[0xd9])],
                         final_cpu=cpu1, final_beam=dict(line=250, raw_cycle=62),
                         decoded_raster=post_meta, current_line=250, DBUF_first=104,
                         DBUF_end_exclusive=488, DBUF_written_end_exclusive=496,
                         completed_current_line_pixels=384, previously_checked_prefix_pixels=352,
                         newly_available_tail_pixels=32)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    prior = frozen_prior()
    frozen, reader = helpers()
    owner_path = BASE / 'native-scanout-analysis/native-scanout-evidence.json'
    owner = receipt(owner_path, OWNER_SHA)
    assert owner['session']['closed_utc'] and owner['session']['exit_code'] == -15
    binary_path = BASE / 'binary-analysis/side1-binary-proof.json'
    binary = receipt(binary_path, BINARY_SHA)
    original = checked(binary['bundles'][36]['RAM'])
    known = checked(binary['bundles'][36]['known_mask'])
    pinned = {entry['stem']: entry for entry in owner['checkpoints']}
    snapshots = {}
    for name in ('restored-arcade', 'floor-strip-drawn', 'field-post'):
        entry = pinned[name]
        ram = checked(entry['ram'])
        checked(entry['snapshot'])
        path = ROOT / entry['snapshot']['path']
        state = reader.read_snapshot(path)
        assert ram == reader.module_payload(path, 'C64MEM')[4:65540]
        pipe, meta, raster = frozen.draw_state(reader.module_payload(path, 'VIC-II'))
        snapshots[name] = (ram, state, pipe, meta, raster)
    ram, pre, pre_pipe, _, _ = snapshots['floor-strip-drawn']
    initial = snapshots['restored-arcade'][0]
    entry_vic = snapshots['restored-arcade'][1]['vicii']
    entry_pipe = snapshots['restored-arcade'][2]
    final_ram, post, post_pipe, meta, raster = snapshots['field-post']
    assert (pre['vicii']['raster_line'], pre['vicii']['raster_cycle']) == (178, 59)
    assert (post['vicii']['raster_line'], post['vicii']['raster_cycle'], meta['current_line']) == (250, 57, 250)
    assert pre['vicii']['sprite_dma'] == pre['vicii']['sprite_display_bits'] == 0
    assert pre_pipe['sprite_pending_bits'] == pre_pipe['sprite_active_bits'] == 0
    assert entry_vic['sprite_dma'] == entry_vic['sprite_display_bits'] == 0
    assert entry_pipe['sprite_pending_bits'] == entry_pipe['sprite_active_bits'] == 0
    assert not any(155 <= y <= 178 for y in entry_vic['regs'][1:16:2])
    assert pre['vicii']['regs'][0x15] == 255
    assert pre['vicii']['regs'][0x1b:0x1e] == [0, 0xf2, 4]
    assert pre['vicii']['regs'][0x17] == 4
    assert pre['vicii']['regs'][1:16:2] == [179, 179, 208, 208, 113, 85, 96, 120]
    assert all(s['exp_flop'] == 1 for s in pre['vicii']['sprites'])
    for state in (pre, post):
        regs = state['vicii']['regs']
        assert regs[0x11] == 0x3b and regs[0x18] == 0x80 and regs[0x20] == 0
        cia = state['cia']['CIA2']
        assert cia['pra'] == 0xf8 and cia['ddra'] == 0x3d
        pins = (cia['pra'] & cia['ddra']) | (3 & ~cia['ddra'])
        assert ((~pins) & 3) * 0x4000 == 0x4000
    stable = ((8, 104), (0x5040, 0x5f40), (0x6208, 0x63e8),
              (0x6400, 0x66c0), (0x7600, 0x7640))
    for a, z in stable:
        assert initial[a:z] == ram[a:z] == final_ram[a:z], (a, z)
    for a, z in ((0x6400, 0x66c0), (0x7600, 0x7640)):
        assert all(known[a:z]) and initial[a:z] == original[a:z]
    assert all(known[0xb400:0xb828])
    patches = {0xb40c, 0xb442, 0xb44f, 0xb47f, 0xb559, 0xb55e}
    code_differences = [a for a in range(0xb400, 0xb828) if initial[a] != original[a]]
    assert set(code_differences) <= patches
    changed_code = [a for a in range(0xb400, 0xb828) if initial[a] != final_ram[a]]
    assert set(changed_code) == {0xb559, 0xb55e}
    assert initial[0xb800:0xb81b] == bytes.fromhex(
        '16 d0 a9 0c 8d 17 d0 a9 f0 8d 07 d0 a9 9a 8d fb 63 a9 01 8d 25 d0 a9 03 8d 26 d0')
    stores = store_inventory(initial)
    # Re-parse the owner's actual closed transcript, rather than trusting a
    # second handwritten register history.
    trace = checked(owner['transcript']).decode()
    events = []
    for match in frozen.TRACE.finditer(trace):
        raw = match.groupdict()
        if raw['kind'].lower() == 'store':
            event = {key: int(value, 10 if key in ('checkpoint', 'line', 'cycle', 'clock') else 16)
                     for key, value in raw.items() if key != 'kind'}
            event['kind'] = 'store'
            events.append(event)
    assert events == owner['register_observations']
    store_sites = {(entry['pc'], entry['target']) for entry in stores}
    assert all((e['pc'], e['target']) in store_sites for e in events)
    scroll = [e for e in events if e['target'] == 0xd016]
    assert len(scroll) == 96 and [e['line'] for e in scroll] == list(range(155, 251))
    assert all(0xc0 <= e['a'] <= 0xc7 and e['a'] == ram[8 + n] for n, e in enumerate(scroll))
    setup = [e for e in events if e['target'] in (0xd011, 0xd018, 0xd020, 0xdd00, 0xdd02)]
    assert [(e['target'], e['pc'], e['a'], e['line']) for e in setup] == [
        (0xdd02, 0xb468, 0x3d, 154), (0xd018, 0xb472, 0x80, 155),
        (0xd018, 0xb472, 0x80, 163), (0xd018, 0xb472, 0x80, 171)]
    y_writes = [e for e in events if e['target'] in range(0xd001, 0xd010, 2)]
    assert [(e['target'], e['a'], e['line']) for e in y_writes] == [
        (0xd005, 208, 154), (0xd007, 208, 154),
        *[(0xd007, 240, line) for line in (218, 226, 234, 242, 250)]]
    lower = [e for e in events if e['line'] >= 179]
    assert len([e for e in lower if e['target'] == 0xd016]) == 72
    assert [(e['line'], e['a']) for e in lower if e['target'] == 0xd017] == [(n, 12) for n in (218, 226, 234, 242, 250)]
    assert [(e['line'], e['a']) for e in lower if e['target'] == 0x63fb] == [(n, 0x9a) for n in (218, 226, 234, 242, 250)]
    for e in lower:
        if e['target'] == 0xd016:
            assert e['a'] == ram[8 + e['line'] - 155]
    schedule, counters, fetches = vertical_schedule(ram, pre['vicii'], lower)
    endpoint = counters[-1]['after_PAL_cycle58']
    for i, state in enumerate(endpoint):
        actual = post['vicii']['sprites'][i]
        for field in ('mc', 'mcbase', 'exp_flop'):
            assert state[field] == actual[field], (i, field, state, actual)
        assert state['dma'] == bool(post['vicii']['sprite_dma'] & (1 << i))
        assert state['display'] == bool(post['vicii']['sprite_display_bits'] & (1 << i))
    latch_witnesses = []
    for i in (2, 3):
        fetched = schedule[250]['sprites'][i]
        actual = post['vicii']['sprites'][i]
        assert fetched['data'] == actual['data']
        assert fetched['pointer'] == actual['pointer']
        latch_witnesses.append(dict(**fetched, actual_VIC_data=actual['data'], actual_pointer=actual['pointer']))
    current_line, tail = complete_tail(frozen, reader, pinned['field-post'], raster)
    actual = raster[179 * 384:250 * 384] + current_line
    outputs = [compose(ram, schedule, line) for line in range(179, 251)]
    independent = b''.join(row[0] for row in outputs)
    errors = differences(actual, independent, 179)
    # Always retain failed output/model hypotheses with their exact coordinates.
    rejected = []
    for variant in ('no_sprites', 'multicolor_as_hires', 'reverse_sprite_priority'):
        alternative = b''.join(compose(ram, schedule, line, variant)[0] for line in range(179, 251))
        diffs = differences(actual, alternative, 179)
        assert diffs, variant
        target = OUT / ('rejected-' + variant + '.json')
        target.write_text(json.dumps(dict(assumption=variant, differences=diffs,
                                         actual_sha256=sha(actual), rejected_sha256=sha(alternative)), indent=2) + '\n')
        rejected.append(dict(assumption=variant, differences=len(diffs), evidence=artifact(target)))
    if errors:
        (OUT / 'rejected-current-model.json').write_text(json.dumps(errors, indent=2) + '\n')
        (OUT / 'rejected-current-model.py').write_bytes(Path(__file__).read_bytes())
    assert not errors, errors[:10]
    actual_path, expected_path = OUT / 'rows179-250-actual.indices', OUT / 'rows179-250-independent.indices'
    actual_path.write_bytes(actual)
    expected_path.write_bytes(independent)
    # Source DBUF_OFFSET=17*8-leftborderwidth=104. Consume only bytes already
    # written this line, with a conservative exclusive dbuf_offset bound.
    vic = post['vicii']
    written_width = min(384, vic['dbuf_offset'] - 104)
    assert written_width == 352
    partial_actual = bytes(vic['dbuf'][104:104 + written_width])
    partial_expected = compose(ram, schedule, 250)[0][:written_width]
    assert partial_actual == partial_expected
    # A new full-field contract: independently index all96 bitmap rows and
    # compose the real lower sprites. The first24 rows have no active sprites;
    # this does not rerun or alter the frozen four-strip checker.
    first24 = b''.join(bitmap_line(ram, line)[0] for line in range(155, 179))
    full_expected = first24 + independent
    full_actual = raster[155 * 384:250 * 384] + current_line
    full_errors = differences(full_actual, full_expected, 155)
    assert len(full_actual) == len(full_expected) == 96 * 384
    assert not full_errors, full_errors[:10]
    full_actual_path, full_expected_path = OUT / 'floor155-250-actual.indices', OUT / 'floor155-250-independent.indices'
    full_actual_path.write_bytes(full_actual)
    full_expected_path.write_bytes(full_expected)
    coverage = {i: sum(row[2][i] for row in outputs) for i in range(4)}
    source = source_rules()
    crunch_rejection = OUT / 'rejected-clearing-edge-explanation.json'
    crunch_rejection.write_text(json.dumps(dict(
        rejected='No old-to-new clearing edge alone excludes all D017 flop/crunch handling.',
        source_rule='After any changed D017 value, NEW-zero-bit sprites with flop0 are handled; a falling edge is not required.',
        actual_field='Changed store is after the special crunch cycle, and all new-zero-bit sprites have flop1.',
        original_producer=artifact(OUT / 'rejected-pointer-negative-control.py')),
        indent=2) + '\n')
    source_receipt = receipt(BASE / 'arcade-source-proof.json',
                             SOURCE_RECEIPT_SHA)
    raster_source = next(x for x in source_receipt['sources'] if x['source_path'] == 'Parts/ArcadeScroller/raster_irq.asm')
    source_text = checked(raster_source).decode()
    assert 'sta $d017' in source_text and 'sta screen_0+$03f8+3' in source_text
    schedule_path = OUT / 'sprite-row-fetches.json'
    schedule_path.write_text(json.dumps(dict(fetches=fetches, counter_history=counters), indent=2) + '\n')
    result = dict(pass_=True, script=artifact(Path(__file__)),
                  scope='One complete coherent96x384 floor field, including original sprite composition and both borders.',
                  frozen_native05_prior=prior, native06_tail=tail,
                  frozen_layout_reader=artifact(ROOT / 'research/anomaly/scanout.py'),
                  owner_receipt=artifact(owner_path), transcript=owner['transcript'],
                  original_binary_receipt=artifact(binary_path), original_RAM=binary['bundles'][36]['RAM'],
                  original_known_mask=binary['bundles'][36]['known_mask'], source=source,
                  original_raster_source=raster_source,
                  original_source_receipt=artifact(BASE / 'arcade-source-proof.json'),
                  snapshots={name: pinned[name] for name in snapshots},
                  compared_rows=[179, 250], full_width_rows=72, width=384,
                  new_full_row_pixels=len(actual), actual=artifact(actual_path), independent=artifact(expected_path),
                  differences=errors, visible_sprite_pixels_by_number=coverage,
                  stable_inputs=[dict(first=a, end_exclusive=z, sha256=sha(ram[a:z])) for a, z in stable],
                  original_sprite_ranges=[[0x6400, 0x66c0], [0x7600, 0x7640]],
                  original_code_live_patches=code_differences, code_changes_during_field=changed_code,
                  bounded_code_write_inventory=stores,
                  row_fetch_schedule=artifact(schedule_path), endpoint_counter_states=endpoint,
                  actual_endpoint_latch_witnesses=latch_witnesses,
                  native05_current_line_prefix=dict(line=250, width=written_width, pixels=written_width,
                                           dbuf_offset=vic['dbuf_offset'], DBUF_first=104,
                                           actual_sha256=sha(partial_actual), independent_sha256=sha(partial_expected)),
                  total_new_compared_pixels=len(actual), additional_pixels_since_frozen_prior=32,
                  full_floor=dict(lines=[155, 250], rows=96, width=384, pixels=len(full_actual),
                                  completed_raster_rows=95, completed_current_DBUF_rows=1,
                                  actual=artifact(full_actual_path), independent=artifact(full_expected_path),
                                  differences=full_errors, D016_table=list(ram[8:104]),
                                  scroll_store_observations=scroll, mode_bank_observations=setup),
                  rejected_assumptions=rejected, full_96_row_floor=True,
                  rejected_checker_guards=[artifact(OUT / 'rejected-code-guard.json'),
                                           artifact(OUT / 'rejected-code-guard.py')],
                  inconclusive_pointer_pixel_control=[artifact(OUT / 'rejected-pointer-negative-control.json'),
                                                      artifact(OUT / 'rejected-pointer-negative-control.py')],
                  rejected_crunch_explanation=artifact(crunch_rejection),
                  completed_output_only=True, final_row_storage='Completed current-line DBUF, not yet committed raster allocation.',
                  bus_write_phase_certified=False,
                  runtime_witness_complete=False,
                  limits=[
                      'One native05 field plus its closed native06 five-clock continuation; this checker starts no native session.',
                      'Completed raster rows155..249 plus all384 already written current-line250 DBUF bytes; no stale tail pixels.',
                      'Sprite2 DMA/data/Y expansion is checked, but its X336 output lies beyond the closed right border.',
                      'D01B is zero in this field; no claim of observed behind-bitmap-priority behavior.',
                      'The changed D017 store follows the special crunch cycle; all new-zero-bit sprites have expansion flop1. No row crunch occurs in this interval.',
                      'Sprite99 rows5..20 are already zero. The pointer99-to-9A transition has source/latch evidence but no distinguishing visible pixel witness.',
                      'Monitor stores remain instruction-boundary observations; no bus-write phase is inferred.',
                      'No upper-wall, physical-chip, full-demo timing or whole-run runtime proof.'])
    result['pass'] = result.pop('pass_')
    path = OUT / 'sprite-scanout-proof.json'
    path.write_text(json.dumps(result, indent=2) + '\n')
    (OUT / 'sprite_scanout.checked.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(passed=True, full_rows=96, full_floor_pixels=len(full_actual), new_full_row_pixels=len(actual),
                          previous_current_line_prefix=written_width, additional_tail_pixels=32,
                          differences=len(errors), visible_sprite_pixels=coverage,
                          full_96_row_floor=True)))


if __name__ == '__main__':
    main()
