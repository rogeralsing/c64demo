#!/usr/bin/env python3
"""Passively accept a fresh original Anomaly upper-sprite priority observation.

No emulator, original CPU, assembler, subprocess or live connection runs here.
The producer accepts only a closed, pinned capture and preserves any mismatch
between the older continuation prediction and this fresh original trajectory.
"""

from collections import Counter
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import re
import sys
import tarfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/anomaly'
CAPTURE = BASE / 'native-08'
OUT = BASE / 'native-priority-analysis'
DISK = BASE / 'original/WeAreTheAnomaly-Side1.d64'
CASE_SHA = '9cc937c7275a2697bb8c7aaec8cc6f203fd2582d96f68e690c7d3baad771f1a7'
ROLE_STEMS = dict(setup='candidate-prepared', active='priority-active', committed='priority-row-committed')
PINS = {
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/anomaly/scanout.py': 'c5e63a07f3060614710518aaf9b9e6c9365c297619af4e19719a4b5f8b62198f',
    'research/anomaly/upper_scanout.py': '70a71b45b4c469182d6b5c5c8841fd20741fe0638ba90d5979f89abbc5d3667a',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'build/research/anomaly/binary-analysis/side1-binary-proof.json': 'b8744b0184128330a069a7366c4f843193306074f4a55a03d10f092a6fa8800c',
    'build/research/anomaly/arcade-source-proof.json': '30e681b44b72f7a610bd8b151762813c591ad7339b153ca8ce8d18117e61e729',
    'build/research/anomaly/overlap-plan/overlap-plan.json': 'c1248d9b3b11751960e7576497879e595eef914e5f0df88aed5fc6ba037d6193',
    'build/research/anomaly/native-upper-fetch-analysis/native-upper-fetch-proof.json': '9e49c34e002474b9df311aca423519833cdf5118e39327f64d036a0e35bb09e2',
    'build/research/anomaly/original/WeAreTheAnomaly-Side1.d64': 'd452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
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
    assert sha((ROOT / relative).read_bytes()) == PINS[relative], relative
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def save(name, value):
    path = OUT / name
    path.write_text(json.dumps(value, indent=2) + '\n')
    return artifact(path)


def wire_case():
    """Adapt only the pinned wire auditor's manual-start metadata assertion."""
    if CASE_SHA is None:
        raise RuntimeError('Native case must be closed and pinned before acceptance')
    wire = load('anomaly08_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {'native-08': CASE_SHA}
    source = inspect.getsource(wire.audit_session)
    before = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    after = ('assert session["startup_mode"] == "autostart"\n'
             '    assert session["command"].count("-autostart") == 1\n'
             f'    assert session["command"][session["command"].index("-autostart") + 1] == {str(DISK)!r}')
    assert source.count(before) == 1
    adapted = source.replace(before, after)
    exec(compile(adapted, '<pinned-wire-auditor-autostart-contract>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-08')
    command = case['session']['command']
    assert case['session']['program'] == str(DISK)
    assert command[command.index('-8') + 1] == str(DISK)
    assert '-pal' in command and '-drive8truedrive' in command and '+autostart-warp' in command
    assert command[command.index('-speed') + 1] == '100'
    return wire, case, dict(original_function_sha256=sha(source.encode()),
                           adapted_function_sha256=sha(adapted.encode()),
                           replaced_assertion=before, replacement_assertions=after,
                           scope='Only original-disk autostart metadata replaces the manual-start assertion.')


def command_audit(wire, case):
    commands = [row for _, row in sorted(case['responses'].items())]
    assert not case['partial'] and not case['cancelled']
    last, contexts, rejected, interruptions, resumes = None, {}, [], [], []
    for index, row in enumerate(commands):
        command, response = row['command'], row['response']
        allowed = command in ('r', 'sidefx off', 'bank ram', 'bank cpu', 'warp', 'warp on', 'warp off',
                              'resourceget "Speed"', 'resourceget "WarpMode"', 'x')
        allowed |= bool(re.fullmatch(r'break (?:exec )?[0-9a-f]{1,4}(?: [0-9a-f]{1,4})?(?: if [^;\n]+)?', command))
        allowed |= bool(re.fullmatch(r'delete [0-9a-f]{1,4}', command))
        allowed |= command in ('trace store d000 d02e', 'trace store dd00 dd03',
                               'trace store cff8 cfff', 'trace store 4ff8 4fff')
        if command == 'resourceget "WarpMode"':
            assert response.split('(C:')[0].strip() == 'Unknown resource "WarpMode".' and row['status'] == 'completed'
            rejected.append(dict(sequence=row['sequence'], command=command, response=response,
                                 interpretation='Rejected read-only resource query; no state change or warp inference.'))
        else:
            assert not re.search(r'Unknown resource|ERROR --|Syntax error|[Mm]onitor observation failed', response)
        if command == 'r':
            last = wire.registers(response)
        if command == 'x':
            assert row['status'] in ('completed', 'interrupted')
            resumes.append(dict(sequence=row['sequence'], status=row['status'],
                                preceding_commands=[r['command'] for r in commands[max(0, index - 3):index]]))
            if row['status'] == 'interrupted':
                interruptions.append(dict(sequence=row['sequence'], registers=wire.registers(row['interrupt']['register_response']),
                                          reason=row['interrupt']['reason']))
            last = None
        match = re.fullmatch(r'(bsave|dump) "([^"\n]+)"( 0 0000 ffff)?', command)
        if match:
            kind, filename, suffix = match.groups()
            path = Path(filename)
            assert path.parent == CAPTURE and last is not None
            assert (kind == 'bsave') == (suffix is not None)
            assert commands[index - 1]['command'] == 'r'
            assert path.name not in contexts and row['status'] == 'completed'
            contexts[path.name] = dict(registers=last, command_sequence=row['sequence'])
            allowed = True
        screenshot = re.fullmatch(r'scrsh "([^"\n]+)" 2', command)
        if screenshot:
            assert Path(screenshot[1]).parent == CAPTURE and last is not None
            assert commands[index - 1]['command'] == 'r'
            allowed = True
        assert allowed, ('Unclassified monitor command', command)
    assert len(contexts) == 2 * len(list(CAPTURE.glob('*.vsf')))
    assert not any(row['command'].startswith(('undump ', 'load ', 'bload ', '> ', 'r pc=')) for row in commands)
    return contexts, dict(command_count=len(commands), command_counts=dict(Counter(r['command'].split()[0] for r in commands)),
                          rejected_read_only_queries=rejected, interrupted_navigation=interruptions,
                          resumes=resumes, restores=[], code_RAM_PC_register_writes=[],
                          scope='Fresh original-disk autostart; native07 is a prediction input, never a restored capture parent.')


def proof_speed(case, contexts):
    rows = [row for _, row in sorted(case['responses'].items())]
    setup_sequence = contexts[ROLE_STEMS['setup'] + '.vsf']['command_sequence']
    committed_sequence = contexts[ROLE_STEMS['committed'] + '.vsf']['command_sequence']
    observations = []
    for index, row in enumerate(rows):
        if row['command'] != 'x' or not setup_sequence < row['sequence'] < committed_sequence:
            continue
        warp = next(prior for prior in reversed(rows[:index]) if prior['command'] == 'warp')
        speed = next(prior for prior in reversed(rows[:index]) if prior['command'] == 'resourceget "Speed"')
        assert warp['response'].split('(C:')[0].strip() == 'Warp mode is off.'
        assert speed['response'].split('(C:')[0].strip() == 'Speed=100'
        assert row['status'] == 'completed'
        assert not any(prior['command'] in ('warp on', 'warp off')
                       for prior in rows if warp['sequence'] < prior['sequence'] < row['sequence'])
        observations.append(dict(resume_sequence=row['sequence'], warp_observation_sequence=warp['sequence'],
                                 speed_observation_sequence=speed['sequence'], warp=False, Speed=100))
    assert len(observations) == 2
    return observations


def captures(contexts, layout, reader):
    result = {}
    for path in sorted(CAPTURE.glob('*.vsf')):
        ram_path = CAPTURE / ('ram-' + path.stem + '.bin')
        registers = contexts[path.name]['registers']
        assert registers == contexts[ram_path.name]['registers']
        ram = ram_path.read_bytes()
        memory = reader.module_payload(path, 'C64MEM')
        assert len(ram) == 65536 and ram == memory[4:65540]
        assert (memory[1], memory[0]) == (registers['port00'], registers['port01'])
        cpu = reader.module_payload(path, 'MAINCPU')
        expected = dict(clock=int.from_bytes(cpu[:8], 'little'), a=cpu[8], x=cpu[9], y=cpu[10], sp=cpu[11],
                        pc=int.from_bytes(cpu[12:14], 'little'), flags=cpu[14])
        assert all(registers[key] == value for key, value in expected.items())
        state = reader.read_snapshot(path)
        vic = state['vicii']
        assert (vic['raster_line'], vic['raster_cycle']) == (registers['line'], registers['cycle'])
        pipe, meta, raster = layout.draw_state(reader.module_payload(path, 'VIC-II'))
        result[path.stem] = dict(ram=ram, state=state, pipe=pipe, meta=meta, raster=raster,
            entry=dict(stem=path.stem, ram=artifact(ram_path), snapshot=artifact(path), registers=registers,
                       RAM_pair_and_CPU_ports_beam_equal=True))
    assert set(ROLE_STEMS.values()) <= set(result)
    return result


def geometry(capture):
    cia, regs = capture['state']['cia']['CIA2'], capture['state']['vicii']['regs']
    pins = (cia['pra'] | (~cia['ddra'] & 255)) & 3
    bank = (~pins & 3) * 0x4000
    return dict(bank=bank, bitmap=bank + ((regs[0x18] & 8) << 10),
                screen=bank + ((regs[0x18] & 0xf0) << 6), pointer_table=bank + ((regs[0x18] & 0xf0) << 6) + 0x3f8,
                D011=regs[0x11], D016=regs[0x16], D018=regs[0x18])


def field_base(capture):
    r = capture['entry']['registers']
    return r['clock'] - 63 * r['line'] - r['cycle']


def trace_rows(case, layout):
    rows = []
    for sequence, response in sorted(case['responses'].items()):
        for match in layout.TRACE.finditer(response['response'].replace('\r\n', '\n')):
            row = match.groupdict()
            for key in ('checkpoint', 'line', 'cycle', 'clock'):
                row[key] = int(row[key])
            for key in ('target', 'pc', 'a', 'x', 'y', 'sp'):
                row[key] = int(row[key], 16)
            row['response_sequence'] = sequence
            rows.append(row)
    headers = sum(len(re.findall(r'(?m)^#\d+ \(Trace store ', response['response']))
                  for response in case['responses'].values())
    assert len(rows) == headers
    return rows


def pixel_layers(active, line, x):
    """Directly decode each actual 24-bit row latch, without a sprite shifter."""
    vic, pipe = active['state']['vicii'], active['pipe']
    regs = vic['regs']
    assert 35 <= vic['raster_cycle'] <= 46 and vic['raster_line'] == line == 110
    assert pipe['sprite_pending_bits'] == vic['sprite_display_bits'] and not pipe['sprite_halt_bits']
    assert pipe['sprite_mc_bits'] == regs[0x1c] and pipe['sprite_expx_bits'] == regs[0x1d]
    assert pipe['sprite_pri_bits'] == regs[0x1b]
    rows, layers = [], []
    geom = geometry(active)
    for sprite in range(8):
        bit, saved = 1 << sprite, vic['sprites'][sprite]
        actual_x = regs[2 * sprite] + (256 if regs[0x10] & bit else 0)
        assert saved['x'] == actual_x == pipe[f'sprite_x_pipe_{sprite}']
        expanded, multicolor = bool(regs[0x1d] & bit), bool(regs[0x1c] & bit)
        enabled = bool(regs[0x15] & bit)
        pending = bool(pipe['sprite_pending_bits'] & bit)
        left, width = actual_x + 8, 24 * (2 if expanded else 1)
        offset = x - left
        selector, source_index = 0, None
        if pending and 0 <= offset < width:
            if multicolor:
                source_index = offset // (4 if expanded else 2)
                selector = (saved['data'] >> (22 - 2 * source_index)) & 3
            else:
                source_index = offset // (2 if expanded else 1)
                selector = 2 if saved['data'] & (1 << (23 - source_index)) else 0
        palette = [None, regs[0x25], regs[0x27 + sprite], regs[0x26]]
        for address in (0x25, 0x26, 0x27 + sprite):
            assert pipe['cregs'][address] == regs[address]
        record = dict(sprite=sprite, enabled=enabled, pending_display=pending,
            DMA=bool(vic['sprite_dma'] & bit), X=actual_x, Y=regs[2 * sprite + 1],
            x_expanded=expanded, y_expanded=bool(regs[0x17] & bit), multicolor=multicolor,
            behind_bitmap=bool(regs[0x1b] & bit), left_in_raster=left, width=width,
            pointer=saved['pointer'], MC=saved['mc'], MCBASE=saved['mcbase'], data_latch=saved['data'],
            source_index=source_index, selector=selector, palette=palette,
            pixel_color=palette[selector], actual_nontransparent_at_target=bool(selector))
        if pending:
            assert enabled
            addresses = [geom['bank'] + saved['pointer'] * 64 + ((saved['mc'] - 3 + i) & 63) for i in range(3)]
            data = bytes(active['ram'][address] for address in addresses)
            assert saved['data'] == int.from_bytes(data, 'big')
            record.update(actual_fetch_addresses=addresses, actual_RAM_bytes=list(data), data_latch_equals_RAM=True)
        rows.append(record)
        if selector:
            layers.append(record)
    return rows, layers


def bitmap_pixel(active, x, line):
    vic, ram = active['state']['vicii'], active['ram']
    regs, geom = vic['regs'], geometry(active)
    assert regs[0x11] & 0x20 and not regs[0x11] & 0x40 and not regs[0x16] & 0x10
    assert not regs[0x16] & 8 and 39 <= x < 343
    row, fine = divmod(line - 51, 8)
    source_x = x - 39 + 7 - (regs[0x16] & 7)
    cell, bit = divmod(source_x, 8)
    pixel_address = geom['bitmap'] + row * 320 + cell * 8 + fine
    attr_address = geom['screen'] + row * 40 + cell
    value, attr = ram[pixel_address], ram[attr_address]
    foreground = bool(value & (128 >> bit))
    return dict(pixel_address=pixel_address, byte=value, attribute_address=attr_address,
                attribute=attr, foreground=foreground, color=attr >> 4 if foreground else attr & 15)


def priority_point(active, committed, x):
    rows, layers = pixel_layers(active, 110, x)
    background = bitmap_pixel(active, x, 110)
    actual = committed['raster'][110 * 384 + x]
    normal, reverse = layers[0] if layers else None, layers[-1] if layers else None
    def color(winner):
        return (background['color'] if winner is None or (background['foreground'] and winner['behind_bitmap'])
                else winner['pixel_color'])
    expected, reversed_color = color(normal), color(reverse)
    assert actual == expected, ('Actual palette-index point differs from independent all-eight selection', x, actual, expected)
    low_occlusion = [row['sprite'] for row in layers if row['sprite'] < 4]
    return dict(line=110, x=x, all_eight_rows=rows, nontransparent_sprite_layers=[row['sprite'] for row in layers],
                bitmap=background, normal_winner=None if normal is None else normal['sprite'],
                reversed_winner=None if reverse is None else reverse['sprite'], actual=actual,
                independent=expected, reversed_priority_control=reversed_color,
                differing_reverse_control=actual != reversed_color, sprites_0_through_3_occluding=low_occlusion)


def source_binding(binary, author, decoded, stores):
    original = checked(binary['bundles'][36]['RAM'])
    known = checked(binary['bundles'][36]['known_mask'])
    checks = []
    for role in ('setup', 'active', 'committed'):
        capture = decoded[ROLE_STEMS[role]]
        for first, end in ((0x3be8, 0x3d93), (0x39e9, 0x3ae9), (0x7400, 0x7500),
                           (0xb400, 0xb40c), (0xb40d, 0xb441)):
            assert all(known[first:end]) and capture['ram'][first:end] == original[first:end]
            checks.append(dict(role=role, first=first, end_exclusive=end, bytes=end - first,
                               original_sha256=sha(original[first:end]), exact=True))
        assert capture['ram'][0xca00:0xcb00] == original[0x7400:0x7500]
    observed = []
    setup = decoded[ROLE_STEMS['setup']]
    committed = decoded[ROLE_STEMS['committed']]
    for row in stores:
        if not setup['entry']['registers']['clock'] <= row['clock'] <= committed['entry']['registers']['clock']:
            continue
        pc, target = row['pc'], row['target']
        assert all(known[pc:pc + 3])
        opcode = original[pc]
        if opcode in (0x8d, 0x8e, 0x8c):
            assert original[pc + 1:pc + 3] == target.to_bytes(2, 'little')
            assert setup['ram'][pc:pc + 3] == committed['ram'][pc:pc + 3] == original[pc:pc + 3]
            observed.append(row)
    selected = []
    for relative in ('Parts/ArcadeScroller/ArcadeScroller.asm', 'Parts/ArcadeScroller/raster_irq.asm',
                     'Parts/ArcadeScroller/variables.asm', 'Build/6502/ArcadeScroller/ArcadeScroller.sym'):
        item = next(row for row in author['sources'] if row['source_path'] == relative)
        checked(item)
        selected.append(item)
    return dict(original_RAM=binary['bundles'][36]['RAM'], original_known_mask=binary['bundles'][36]['known_mask'],
                source_ranges=checks, source_bound_observed_absolute_stores=observed, author_files=selected)


def boot_binding(binary):
    """Bind the original attached disk to its retained DOS boot chain."""
    disk = DISK.read_bytes()
    boot = BASE / 'binary-analysis/side1-boot.prg'
    assert sha(boot.read_bytes()) == binary['boot_SHA256']
    data = bytearray()
    chain = binary['boot_chain']
    for index, entry in enumerate(chain):
        track, sector = entry['track'], entry['sector']
        counts = [21 if t <= 17 else 19 if t <= 24 else 18 if t <= 30 else 17 for t in range(1, track)]
        offset = (sum(counts) + sector) * 256
        block = disk[offset:offset + 256]
        assert sha(block) == entry['sha256']
        if index + 1 < len(chain):
            assert list(block[:2]) == [chain[index + 1]['track'], chain[index + 1]['sector']]
            data.extend(block[2:])
        else:
            assert block[0] == 0
            data.extend(block[2:block[1] + 1])
    assert bytes(data) == boot.read_bytes()
    return dict(original_disk=artifact(DISK), boot=artifact(boot), original_DOS_sector_chain=chain,
                disk_chain_bytes_equal_boot=True,
                scope='Attached original disk and its offline byte-bound boot chain; no direct native $0810 entry observation is inferred.')


def interval_invariants(setup, active, committed, stores):
    relevant = list(range(0x10)) + [0x10, 0x11, 0x15, 0x16, 0x17, 0x18, 0x1b, 0x1c, 0x1d] + list(range(0x20, 0x2f))
    for offset in relevant:
        values = [capture['state']['vicii']['regs'][offset] for capture in (setup, active, committed)]
        assert len(set(values)) == 1, (offset, values)
    geom = geometry(active)
    assert geometry(setup) == geometry(committed) == geom
    assert geom['bank'] in (0x4000, 0xc000)
    regs = active['state']['vicii']['regs']
    assert regs[0x15] & 0xf0 == regs[0x1c] & 0xf0 == regs[0x1d] & 0xf0 == 0xf0
    assert not (regs[0x17] | regs[0x1b]) & 0xf0
    assert not stores  # All configured MMIO ranges are continuously observed here.
    pointer_table = geom['pointer_table']
    assert pointer_table == 0x63f8
    pointer_bytes = [capture['ram'][pointer_table:pointer_table + 8] for capture in (setup, active, committed)]
    assert pointer_bytes[0] == pointer_bytes[1] == pointer_bytes[2]
    return dict(equal_VIC_register_offsets=relevant, equal_geometry=geom,
                MMIO_trace_events=0, observed_MMIO_ranges=[[0xd000, 0xd02e], [0xdd00, 0xdd03]],
                configured_pointer_trace_ranges=[[0x4ff8, 0x4fff], [0xcff8, 0xcfff]],
                actual_pointer_table=pointer_table, actual_pointer_bytes=list(pointer_bytes[0]),
                actual_pointer_table_in_trace_ranges=False,
                pointer_history_limit='The actual $63F8 table was not traced. Endpoint bytes and actual row latches agree; no continuous pointer-write history is claimed.')


def extended_strip(setup, active, committed, upper):
    """Rename only oracle RAM addresses for the frozen fixed-bank compositor."""
    geom, regs = geometry(active), active['state']['vicii']['regs']
    assert committed['meta']['current_line'] == 152
    lower = []
    for sprite in range(4):
        y = regs[sprite * 2 + 1]
        height = 21 * (2 if regs[0x17] & (1 << sprite) else 1)
        assert y + 1 > 151 and y + height < 312
        lower.append(dict(sprite=sprite, Y=y, source_height_in_lines=height,
                          next_start_line=y + 1, preceding_field_finished_before_line312=True))
    assert all(regs[2 * sprite + 1] + 21 < 152 for sprite in range(4, 8))
    # Mapping is an input-address transport for a frozen oracle. Native CIA,
    # VIC registers, physical RAM and capture files remain unchanged.
    view = bytearray(active['ram'])
    maps = [(geom['bitmap'], 0xe000, 13 * 320), (geom['screen'], 0xcc00, 13 * 40),
            (0x7400, 0xca00, 256)]
    records = []
    for first, target, count in maps:
        data = active['ram'][first:first + count]
        assert setup['ram'][first:first + count] == committed['ram'][first:first + count] == data
        view[target:target + count] = data
        records.append(dict(actual_source=first, oracle_address=target, bytes=count, sha256=sha(data)))
    pointers = []
    for sprite in range(4, 8):
        pointer = active['ram'][geom['pointer_table'] + sprite]
        physical = geom['bank'] + pointer * 64
        assert physical == 0x7400 + (sprite - 4) * 64
        canonical = (0xca00 + (physical - 0x7400) - 0xc000) // 64
        assert canonical == 0x28 + sprite - 4
        view[0xcff8 + sprite] = canonical
        pointers.append(dict(sprite=sprite, actual_pointer_table_slot=geom['pointer_table'] + sprite,
                             actual_pointer=pointer, actual_art_address=physical,
                             oracle_pointer_table_slot=0xcff8 + sprite, oracle_pointer=canonical))
    oracle_input = dict(ram=bytes(view), state=active['state'])
    expected, selected, overlaps = upper.compose(oracle_input)
    actual = committed['raster'][51 * 384:152 * 384]
    expected = expected[:len(actual)]
    assert len(actual) == 38784 and expected == actual
    actual_path, expected_path = OUT / 'upper-101-actual.bin', OUT / 'upper-101-independent.bin'
    actual_path.write_bytes(actual)
    expected_path.write_bytes(expected)
    controls = []
    for variant in ('no_sprites', 'reverse_sprite_priority'):
        alternative, _, _ = upper.compose(oracle_input, variant)
        differences = upper.delta(actual, alternative[:len(actual)])
        assert differences
        controls.append(dict(variant=variant, differences=len(differences), sample=differences[:8]))
    previous_receipt_path = ROOT / 'build/research/anomaly/native-upper-fetch-analysis/native-upper-fetch-proof.json'
    previous = json.loads(previous_receipt_path.read_text())
    old_entry = previous['final_continuation']
    old_ram = checked(old_entry['ram'])
    wall_changes = []
    stale_view = bytearray(view)
    for old_first, actual_first, canonical, size in ((0xe000, geom['bitmap'], 0xe000, 4160),
                                                   (0xcc00, geom['screen'], 0xcc00, 520)):
        old_data, new_data = old_ram[old_first:old_first + size], active['ram'][actual_first:actual_first + size]
        changes = sum(a != b for a, b in zip(old_data, new_data))
        assert changes
        wall_changes.append(dict(previous_first=old_first, actual_first=actual_first, bytes=size,
                                 previous_sha256=sha(old_data), actual_sha256=sha(new_data), changed_bytes=changes))
        stale_view[canonical:canonical + size] = old_data
    stale_wall, _, _ = upper.compose(dict(ram=bytes(stale_view), state=active['state']))
    stale_wall = stale_wall[:len(actual)]
    stale_errors = upper.delta(actual, stale_wall)
    assert stale_errors
    stale_path = OUT / 'upper-101-control-previous-wall.bin'
    stale_path.write_bytes(stale_wall)
    controls.append(dict(variant='previous_wall_with_current_sprites_and_scroll', differences=len(stale_errors),
                         sample=stale_errors[:8], evidence=artifact(stale_path),
                         held_fixed='Current sprite art, positions, palettes, priority and D016 fine scroll. Only bitmap and attributes are replaced.'))
    return dict(lines=[51, 151], rows=101, width=384, pixels=len(actual), differences=[],
                actual=artifact(actual_path), independent=artifact(expected_path),
                native_geometry=geom, oracle_RAM_address_maps=records, oracle_pointer_translation=pointers,
                actual_native_CIA_and_register_state_unchanged=True, input_is_address_transport_not_native_C000_observation=True,
                lower_sprite_exclusions=lower, selected_upper_sprite_pixels=selected,
                nontransparent_upper_overlap_pixels=overlaps, controls=controls,
                previous_wall_comparison=dict(previous_receipt=artifact(previous_receipt_path),
                    previous_capture=old_entry, ranges=wall_changes, bitmap_and_attributes_both_differ=True),
                current_line152_and_later_excluded=True, whole104_row_strip_proven=False)


def source_rules():
    names = ('src/viciisc/vicii-draw-cycle.c', 'src/viciisc/vicii-fetch.c',
             'src/viciisc/vicii-cycle.c', 'src/viciisc/vicii-snapshot.c',
             'src/autostart.c', 'src/vsync.c', 'src/monitor/mon_parse.y', 'src/monitor/monitor.c')
    navigation_guards = {
        'src/autostart.c': ('orig_warp_mode = vsync_get_warp_mode();',
                           'if (vsync_get_warp_mode() != orig_warp_mode)',
                           'set_warp_mode(orig_warp_mode);',
                           'restore_drive_emulation_state(autostart_disk_unit, autostart_disk_drive);'),
        'src/vsync.c': ('warp_enabled = val ? 1 : 0;', 'return warp_enabled;',
                        '{ "Speed", 100,', '{ "InitialWarpMode", 0,'),
        'src/monitor/mon_parse.y': ('| CMD_WARP end_cmd', 'vsync_get_warp_mode() ? "on" : "off"',
                                  '| CMD_WARP TOGGLE end_cmd'),
        'src/monitor/monitor.c': ('void mon_resource_get(const char *name)',
                                'switch (resources_query_type(name))',
                                'mon_out("Unknown resource \\"%s\\".\\n", name);'),
    }
    records = []
    archive = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    with tarfile.open(archive, 'r:gz') as tar:
        for name in names:
            member = 'vice-3.10/' + name
            data = tar.extractfile(member).read()
            text = data.decode()
            for guard in navigation_guards.get(name, ()):
                assert guard in text, (name, guard)
            if name == 'src/vsync.c':
                resources = text.split('static const resource_int_t resources_int[] = {', 1)[1].split('RESOURCE_INT_LIST_END', 1)[0]
                assert '"WarpMode"' not in resources
            target = OUT / 'source' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
            records.append(dict(member=member, guarded_fragments=len(navigation_guards.get(name, ())), **artifact(target)))
    return dict(archive=artifact(archive), files=records,
                interpretation='Actual pending/display state and complete row latches; direct bit/pair indexing and hardware-number priority, not a replayed shifter.',
                navigation_warp=dict(runtime_state_query='Bare monitor warp command reads vsync_get_warp_mode().',
                    startup_resource='InitialWarpMode is a startup preference, not current runtime warp.',
                    unsupported_query='WarpMode is absent from the vsync resource table; the exact rejected query is retained.',
                    observed_early_navigation_warp=False,
                    source_supported_possibility='Autostart saves original runtime warp and restores it at completion; manual warp-on during autostart can later revert.',
                    exact_cause_of_native08_observed_OFF_proven=False,
                    limit='The retained native08 log contains no decisive completion/off event tying this observed transition to autostart.'))


def prediction_comparison(setup, plan):
    predicted = json.loads(checked(plan['candidate']))
    expected = predicted['sprites']
    vic, ram = setup['state']['vicii'], setup['ram']
    actual = [dict(sprite=s, low_x=vic['regs'][s * 2], y=vic['regs'][s * 2 + 1],
                   phase=ram[0xe8 + s], wave_index=ram[0xe0 + s - 2], speed=ram[0xf0 + s - 2]) for s in range(4, 8)]
    result = dict(prediction_receipt=artifact(ROOT / 'build/research/anomaly/overlap-plan/overlap-plan.json'),
        predicted_scene_counter=plan['predicted_scene_counter'], actual_scene_counter=int.from_bytes(ram[0xf0:0xf2], 'little'),
        predicted_upper_mask=predicted['mask_upper_bits'], actual_upper_mask=ram[0xcb] & 0xf0,
        predicted_sprites=expected, actual_sprites=actual)
    result['matches'] = (result['predicted_scene_counter'] == result['actual_scene_counter'] and
                         result['predicted_upper_mask'] == result['actual_upper_mask'] and actual == expected)
    result['interpretation'] = ('Fresh original trajectory agrees with the older conditional prediction.' if result['matches'] else
                                'Rejected trajectory prediction retained. Acceptance uses actual fresh native state, never patched or forced predicted state.')
    return result


def main():
    if CASE_SHA is None:
        raise RuntimeError('Native case must be closed and pinned before acceptance')
    for relative, digest in PINS.items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
    wire, case, adaptation = wire_case()
    contexts, commands = command_audit(wire, case)
    proof_resumes = proof_speed(case, contexts)
    layout = load('anomaly08_layout', 'research/anomaly/scanout.py')
    reader = layout.reader()
    decoded = captures(contexts, layout, reader)
    setup, active, committed = (decoded[ROLE_STEMS[role]] for role in ('setup', 'active', 'committed'))
    expected_stops = ((setup, 0x3d83, 175034118, 271, 21),
                      (active, 0x08c1, 175043648, 110, 38),
                      (committed, 0xb400, 175046267, 152, 11))
    for capture, pc, clock, line, cycle in expected_stops:
        r = capture['entry']['registers']
        assert (r['pc'], r['clock'], r['line'], r['cycle']) == (pc, clock, line, cycle)
    assert setup['entry']['registers']['pc'] == 0x3d83
    assert committed['entry']['registers']['pc'] == 0xb400
    assert committed['meta']['current_line'] == 152
    assert field_base(active) == field_base(committed) == field_base(setup) + 19656
    assert setup['entry']['registers']['clock'] < active['entry']['registers']['clock'] < committed['entry']['registers']['clock']
    OUT.mkdir(parents=True, exist_ok=True)
    binary = json.loads((ROOT / 'build/research/anomaly/binary-analysis/side1-binary-proof.json').read_text())
    author = json.loads((ROOT / 'build/research/anomaly/arcade-source-proof.json').read_text())
    plan = json.loads((ROOT / 'build/research/anomaly/overlap-plan/overlap-plan.json').read_text())
    assert binary['pass'] and author['pass'] and plan['pass']
    stores = trace_rows(case, layout)
    binding = source_binding(binary, author, decoded, stores)
    interval = interval_invariants(setup, active, committed, stores)
    prediction = prediction_comparison(setup, plan)
    prediction_artifact = save('trajectory-comparison.json', prediction)
    points = [priority_point(active, committed, x) for x in (318, 319)]
    no_lower_occlusion = all(not point['sprites_0_through_3_occluding'] for point in points)
    distinguishes = all(point['differing_reverse_control'] for point in points)
    accepted = no_lower_occlusion and distinguishes
    upper = load('anomaly08_frozen_upper_compositor', 'research/anomaly/upper_scanout.py')
    extent = extended_strip(setup, active, committed, upper)
    active_stale_values = [active['raster'][110 * 384 + x] for x in (318, 319)]
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()),
        input_pins=[artifact(ROOT / relative) for relative in PINS], capture_directory_sha256=CASE_SHA,
        wire=wire.summary(case), startup_contract_adaptation=adaptation, command_audit=commands,
        proof_resume_speed_observations=proof_resumes, original_disk_boot=boot_binding(binary),
        lineage='Fresh original-disk autostart. No snapshot restore or state injection. Native07 contributes only a conditional host prediction.',
        direct_boot_entry_observed=any(row['entry']['registers']['pc'] == 0x0810 for row in decoded.values()),
        checkpoints=[row['entry'] for row in decoded.values()], RAM_snapshot_bytes=65536 * len(decoded),
        source=source_rules(), original_binding=binding, register_observations=stores,
        target_interval=interval,
        trajectory_comparison=prediction_artifact, trajectory_prediction_matches=prediction['matches'],
        active_geometry=geometry(active), all_eight_direct_points=points,
        no_sprites_0_through_3_occlusion=no_lower_occlusion, reversed_priority_distinguished=distinguishes,
        native_priority_witness_complete=accepted, actual_palette_indices=[point['actual'] for point in points],
        current_active_raster_is_not_committed_control=dict(values=active_stale_values,
            different_from_committed=sum(a != point['actual'] for a, point in zip(active_stale_values, points)),
            interpretation='At line110 the serialized raster row is still the previous field; only the later committed row is accepted as output.'),
        additional_committed_upper_strip=extent,
        screenshot=dict(**artifact(CAPTURE / 'priority-window.png'), scope='Retained output observation, not the palette-index oracle.'),
        final_continuation=committed['entry'], physical_chip_proven=False,
        bus_write_phase_certified=False, whole_frame_or_FPS_proof=False,
        limits=[
            'This producer is passive and requires the owned capture process to have closed and been reaped.',
            'Warped navigation and interrupted navigation are distinct from the explicitly unwarped proof interval.',
            'All-eight acceptance uses actual row latches and modes; it does not assume the older four-sprite trajectory or simulate future foreground movement.',
            'Only line 110, X 318..319 is the priority output witness; the line 152 snapshot does not make its uncommitted current-row tail a whole-field proof.',
            'The wider 101-row match uses explicit oracle RAM address renaming while native bank $4000 state remains unchanged; it is not an observed native bank $C000 display.',
            'The actual $63F8 sprite-pointer table was not in the armed $4FF8/$CFF8 trace ranges. Actual latches and endpoint RAM are verified; continuous pointer-write history is not claimed.',
            'Endpoint art equality does not prove absence of transient RAM writes. Observer clocks are not physical bus phases.',
            'A trajectory mismatch or actual lower-sprite occlusion is retained as an inconclusive candidate rather than forcing predicted state.'])
    result['pass'] = result.pop('pass_')
    receipt = save('native-priority-proof.json', result)
    (OUT / 'native_priority.checked.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(pass_=True, native_priority_witness_complete=accepted,
                         trajectory_prediction_matches=prediction['matches'], receipt=receipt), indent=2))


if __name__ == '__main__':
    main()
