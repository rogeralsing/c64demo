#!/usr/bin/env python3
"""Prove retained C64SC phi1 RAM mapping; byte evolution is a separate ABI."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-pixels-20261109/physical-analysis'
SOURCE = BASE / 'source-01/source.json'
SOURCE_SHA = 'aac12596a624bc421e342bbe50b35f774ee78c67fc46250538f8e72294d3518b'
NATIVE = ROOT / 'build/research/aloft-execution-20261109/native-analysis/accepted-02/native-proof.json'
NATIVE_SHA = '5db9694db276541a5fd2b5cb386e92639e6da2c0d6cd644caf758eb113cc2326'
LOGICAL = ROOT / 'build/research/aloft-execution-20261109/fetch-analysis/binding-accepted-01/fetch-binding-proof.json'
LOGICAL_SHA = '31efa766ff16b02d04c834ba107c40c868d0124fb4c0ea2e499e5b6f6644916c'
READER = ROOT / 'research/quondam/snapshot_state.py'
READER_SHA = 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a'
MAPPING = dict(schema='aloft-c64sc-phi1-mainram-v1', ram_object='mem_ram',
    vbank_phi1=0, address_mask=0xffff, address_offset=0,
    chargen_mask=0x7000, chargen_value=0x1000, ultimax_phi1=False)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=digest(raw))


def checked(path, sha):
    raw = path.read_bytes()
    assert digest(raw) == sha, path
    return raw


def export(proof, folder, name):
    row = next(r for r in proof['outputs'] if r.get('name', Path(r.get('path', '')).name) == name)
    raw = checked(folder / name, row['sha256'])
    assert len(raw) == row['bytes']
    return json.loads(raw)


def resolve_phi1(logical_address, mapping):
    """Only the proved low-address domain and exact mapping tuple are admitted."""
    if mapping != MAPPING or not isinstance(logical_address, int) or not 0 <= logical_address < 0x800:
        raise ValueError('outside the proved plain-C64SC phi1 mapping')
    physical = ((logical_address + mapping['vbank_phi1']) & mapping['address_mask']) | mapping['address_offset']
    assert not mapping['ultimax_phi1']
    assert physical & mapping['chargen_mask'] != mapping['chargen_value']
    return dict(region='mainRAM', physical_address=physical, cpu_port_overlay=False)


def write(out, name, value):
    raw = (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()
    (out / name).write_bytes(raw)
    return dict(name=name, bytes=len(raw), sha256=digest(raw))


def anchor(text, first, last, required):
    fragment = ''.join(text.splitlines(keepends=True)[first - 1:last])
    assert all(token in fragment for token in required), (first, required)
    return dict(first_line=first, last_line=last, fragment_sha256=digest(fragment.encode()), required=required)


def enabled(point, sequence):
    if point['created_sequence'] >= sequence or point.get('deleted_sequence', sequence + 1) <= sequence:
        return False
    state = True
    for update in point['updates']:
        if update['sequence'] > sequence:
            break
        if update['command'].startswith('disable '):
            state = False
        elif update['command'].startswith('enable '):
            state = True
    return state


def coverage(points, first, last, start, end):
    possible = [p for p in points if p['kind'] == 'TRACE' and p['operation'] == 'Trace store'
        and p['first'] <= first and p['last'] >= last and p.get('attached_command') == 'r']
    for point in possible:
        boundaries = [start, end] + [u['sequence'] for u in point['updates'] if start <= u['sequence'] <= end]
        if all(enabled(point, seq) for seq in boundaries):
            return point
    raise ValueError('missing continuous mapping watch coverage')


def produce(out):
    out.relative_to(BASE)
    assert not out.exists()
    source = json.loads(checked(SOURCE, SOURCE_SHA))
    archive = ROOT / source['archive']['path']
    checked(archive, source['archive']['sha256'])
    texts, source_inputs = {}, [meta(SOURCE), meta(archive)]
    with tarfile.open(archive) as tar:
        for item in source['members']:
            path = ROOT / item['path']
            raw = checked(path, item['sha256'])
            assert raw == tar.extractfile(item['member']).read()
            texts[item['member'].removeprefix('vice-3.10/')] = raw.decode()
            source_inputs.append(meta(path))
        inventory_path = ROOT / source['setter_sites']['path']
        inventory = json.loads(checked(inventory_path, source['setter_sites']['sha256']))
        # Recompute every direct API token and map-field assignment from the original archive.
        terms = inventory['functions'] + ['mem_set_vbank']
        tokens, assignments = [], []
        token_pattern = re.compile(r'\b(' + '|'.join(terms) + r')\b')
        field_pattern = re.compile(r'\bvicii\.(ram_base_phi1|vaddr_mask_phi1|vaddr_offset_phi1|vaddr_chargen_mask_phi1|vaddr_chargen_value_phi1|vbank_phi1)\s*=')
        for member in tar.getmembers():
            if not member.isfile() or not member.name.endswith(('.c', '.h')):
                continue
            text = tar.extractfile(member).read().decode(errors='replace')
            for match in token_pattern.finditer(text):
                assert text[match.end():].lstrip().startswith('('), 'unclassified indirect API reference'
                tokens.append(dict(member=member.name, line=text.count('\n', 0, match.start()) + 1, function=match[0]))
            for match in field_pattern.finditer(text):
                assignments.append(dict(member=member.name, line=text.count('\n', 0, match.start()) + 1, field=match[1]))
        assert len(tokens) == 92
        assert {a['member'] for a in assignments if '/viciisc/' in a['member']} == {'vice-3.10/src/viciisc/vicii.c'}
    source_inputs.append(meta(inventory_path))
    make = texts['src/Makefile.am']
    sc_block = make.split('x64sc_libs =', 1)[1].split('x64sc_SOURCES', 1)[0]
    assert '$(c64sc_lib)' in sc_block and '$(viciisc_lib)' in sc_block
    assert all(token not in sc_block for token in ['$(c64_lib)', '$(xcbm5x0_lib)', '$(c128_lib)', '$(scpu64_lib)', '$(c64dtv_lib)'])
    sources = texts['src/c64/Makefile.am'].split('libc64sc_a_SOURCES =', 1)[1].split('\nlib', 1)[0]
    assert 'c64memsc.c' in sources and '\tc64mem.c' not in sources
    primary = {
        'src/viciisc/vicii.c': [anchor(texts['src/viciisc/vicii.c'], 330, 355,
            ['vicii.ram_base_phi1 = mem_ram;', 'vicii.vaddr_mask_phi1 = 0xffff;', 'vicii.vaddr_offset_phi1 = 0;']),
            anchor(texts['src/viciisc/vicii.c'], 365, 375, ['num_vbank << 14', 'vicii.vbank_phi1 = vbank_p1;'])],
        'src/viciisc/vicii-fetch.c': [anchor(texts['src/viciisc/vicii-fetch.c'], 50, 74,
            ['vicii.vbank_phi1', 'export.ultimax_phi1', 'p = vicii.ram_base_phi1 + addr;', 'return *p;'])],
        'src/c64/c64memsc.c': [anchor(texts['src/c64/c64memsc.c'], 89, 89, ['uint8_t mem_ram[C64_RAM_SIZE];']),
            anchor(texts['src/c64/c64memsc.c'], 246, 274,
            ['return mem_ram[addr & 0xff];', 'return pport.dir_read;', 'retval = pport.data_read;']),
            anchor(texts['src/c64/c64memsc.c'], 347, 365, ['mem_ram[addr] = value;']),
            anchor(texts['src/c64/c64memsc.c'], 519, 522, ['mem_ram[addr] = value;']),
            anchor(texts['src/c64/c64memsc.c'], 495, 499, ['zero_store_dma(addr, value);']),
            anchor(texts['src/c64/c64memsc.c'], 805, 831, ['mem_set_write_hook(i, 0, zero_store);', 'ram_store']),
            anchor(texts['src/c64/c64memsc.c'], 910, 915, ['vicii_set_chargen_addr_options(0x7000, 0x1000);', 'export.exrom = 0;']),
            anchor(texts['src/c64/c64memsc.c'], 959, 963, ['vicii_set_vbank(new_vbank);'])],
        'src/c64/cart/c64carthooks.c': [anchor(texts['src/c64/cart/c64carthooks.c'], 3281, 3326,
            ['C64CART_DUMP_VER_MINOR   1', 'SMW_B(m, number_of_carts)', 'if (number_of_carts == 0)'])],
        'src/c64/c64-memory-hacks.c': [anchor(texts['src/c64/c64-memory-hacks.c'], 74, 108,
            ['set_c64_256k_enabled(0, 0)', 'set_plus256k_enabled(0, 0)', 'memory_hack = value;']),
            anchor(texts['src/c64/c64-memory-hacks.c'], 161, 207, ['SMW_B(m, (uint8_t)memory_hack)', 'case MEMORY_HACK_NONE:'])],
        'src/c64/c64-memory-hacks.h': [anchor(texts['src/c64/c64-memory-hacks.h'], 30, 40,
            ['MEMORY_HACK_NONE = 0'])],
        'src/c64/c64memsnapshot.c': [anchor(texts['src/c64/c64memsnapshot.c'], 201, 230,
            ['SNAP_MINOR 1', 'SMW_B(m, pport.data)', 'SMW_B(m, pport.dir)',
             'SMW_B(m, export.exrom)', 'SMW_B(m, export.game)', 'SMW_BA(m, mem_ram, C64_RAM_SIZE)'])],
        'src/c64/cart/c64cartmem.c': [anchor(texts['src/c64/cart/c64cartmem.c'], 149, 153, ['export_t export = { 0, 0, 0, 0 }'])],
        'src/core/ciacore.c': [anchor(texts['src/core/ciacore.c'], 801, 810, ['CIA_PRA] | ~(cia_context->c_cia[CIA_DDRA])'])],
        'src/c64/c64cia2.c': [anchor(texts['src/c64/c64cia2.c'], 150, 155, ['new_vbank = tmp & 3;', 'c64_glue_set_vbank'])],
        'src/c64/c64gluelogic.c': [anchor(texts['src/c64/c64gluelogic.c'], 51, 106,
            ['mem_set_vbank(vbank);', 'perform_vbank_switch(old_vbank);', 'glue_alarm_unset();', 'old_vbank = vbank;']),
            anchor(texts['src/c64/c64gluelogic.c'], 169, 197,
            ['SNAP_MAJOR 1', 'SNAP_MINOR 0', 'SMW_B(m, (uint8_t)old_vbank)', 'SMW_B(m, (uint8_t)glue_alarm_active)'])],
    }
    native = json.loads(checked(NATIVE, NATIVE_SHA))
    logical = json.loads(checked(LOGICAL, LOGICAL_SHA))
    assert native['pass_'] and logical['pass_']
    assert native['command_audit']['no_PC_RAM_writes_restores_restart_or_disk_change_commands']
    command = native['session']['command']
    assert Path(command[0]).name == 'x64sc' and '-default' in command
    assert native['session']['startup_mode'] == 'autostart'
    assert native['owner_closure']['snapshot_restores'] == native['owner_closure']['restarts'] == 0
    sent = ROOT / 'build/research/aloft-execution-20261109/native-01/sent.bin'
    raw_sent = checked(sent, native['wire']['sent']['sha256'])
    commands = raw_sent.decode('ascii').splitlines()
    allowed = {'bank', 'break', 'bsave', 'command', 'condition', 'delete', 'disable', 'dummy',
               'dump', 'enable', 'help', 'ignore', 'm', 'r', 'resourceget', 'sidefx', 'trace', 'warp', 'x'}
    assert all(c.split()[0] in allowed for c in commands)
    assert all(c == 'r' for c in commands if c.split()[0] == 'r')
    assert all(re.fullmatch(r'command \d+ "r"', c) for c in commands if c.split()[0] == 'command')
    checked(READER, READER_SHA)
    spec = importlib.util.spec_from_file_location('frozen_physical_state_reader', READER)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    captures = {c['stem']: c for c in native['captures']}
    states, observations = {}, []
    for item in native['captures']:
        path = ROOT / item['snapshot']['path']
        checked(path, item['snapshot']['sha256'])
        state = reader.read_snapshot(path)
        mem = reader.module_payload(path, 'C64MEM')
        assert state['modules']['C64MEM']['version'] == [0, 1] and len(mem) == 65555
        assert mem[2:4] == b'\x00\x00'
        for name, version in [('C64CART', [0, 1]), ('C64MEMHACKS', [0, 0])]:
            assert state['modules'][name]['version'] == version
            assert reader.module_payload(path, name) == b'\x00'
        assert state['header']['machine'] == 'C64SC'
        states[item['stem']] = state
        observations.append(dict(stem=item['stem'], snapshot=item['snapshot'], no_cartridges=True,
            no_memory_hacks=True, C64MEM_game_exrom=[0, 0]))
    hooks = export(native, NATIVE.parent, 'hook-oracles.json')['all_hooks']
    abi, physical = [], []
    for field in native['fields']:
        label, roles = field['label'], field['roles']
        input_capture, after_capture = captures[roles['dispatcher']], captures[roles['after_line']]
        state = states[roles['dispatcher']]
        cia, vic = state['cia']['CIA2'], state['vicii']
        assert (cia['pra'], cia['ddra']) == (8, 0x3c)
        pins = (cia['pra'] | (~cia['ddra'] & 255)) & 255
        assert (~pins) & 3 == 0
        snapshot = ROOT / input_capture['snapshot']['path']
        assert state['modules']['GLUE']['version'] == [1, 0]
        assert reader.module_payload(snapshot, 'GLUE') == bytes.fromhex('010000')
        pred = export(logical, LOGICAL.parent, label + '-logical-fetch-prediction.json')
        start, end = input_capture['registers']['clock'], pred['last_g_clock']
        assert after_capture['registers']['clock'] > end
        guards = [coverage(native['checkpoint_generations'], a, b, input_capture['stop_sequence'],
                           after_capture['stop_sequence']) for a, b in [(0, 1), (0xd018, 0xd018), (0xdd00, 0xdd03)]]
        mapping_changes = [h for h in hooks if start <= h['registers']['clock'] <= end
            and h['operation'] == 'store' and (h['monitored_address'] in [0, 1, 0xd018]
            or 0xdd00 <= h['monitored_address'] <= 0xdd03)]
        assert mapping_changes == []
        expected_mapping = dict(MAPPING)
        entries = []
        for row in pred['lines']:
            index = row['call_index']
            assert all(a & 7 == 7 and a < 0x800 for a in row['logical_row7_addresses'])
            entries.append(dict(raster_line=row['line'],
                first_fetch_clock=pred['first_g_clock'] + 63 * index,
                last_fetch_clock=pred['first_g_clock'] + 63 * index + 39,
                requests=[dict(slot=i, logical_address=a, **resolve_phi1(a, expected_mapping))
                          for i, a in enumerate(row['logical_row7_addresses'])]))
        assert len(entries) == 200 and sum(len(r['requests']) for r in entries) == 8000
        abi.append(dict(label=label, mapping=expected_mapping, valid_clock_interval=[start, end],
            input_capture=input_capture, observed_run_after_last_g=after_capture,
            CIA2_effective_pins=pins, GLUE_payload='010000', continuous_watch_guards=guards,
            native_final_RAM_bytes_not_used=True, mapping_changes_in_interval=0,
            admitted_glyph_CPU_stores_alias_same_mem_ram=True,
            glyph_store_domain='Forty row7 addresses; never CPU-port0/1.'))
        physical.append(dict(label=label, rows=entries))
    table = [dict(logical_address=a, **resolve_phi1(a, MAPPING)) for a in range(0x800)]
    assert all(r['physical_address'] == r['logical_address'] and r['region'] == 'mainRAM' for r in table)
    out.mkdir(parents=True)
    outputs = [write(out, 'primary-mapping-source.json', dict(sources=source_inputs, anchors=primary,
        direct_API_tokens=tokens, mapping_field_assignments=assignments,
        source_selection='x64sc links libc64sc/c64memsc and viciisc; alternate platform mappings are excluded.')),
        write(out, 'machine-mapping-observations.json', dict(captures=observations,
            startup=native['session'], no_runtime_mapping_resource_or_cart_command=True)),
        write(out, 'mapping-abi.json', dict(schema='aloft-c64sc-phi1-mainram-fields-v1', fields=abi,
            resolver='resolve_phi1(logical_address,mapping)', domain=[0, 0x7ff], returned_byte_join_owner='glyph stream lane')),
        write(out, 'physical-requests.json', dict(fields=physical, no_returned_byte_or_pixel_values=True)),
        write(out, 'finite-low-RAM-table.json', dict(rows=table,
            logical0_and1_are_underlying_RAM=True, CPU_port_read_route_is_separate=True))]
    write(out, 'physical-fetch-proof.json', dict(pass_=True, producer=meta(Path(__file__)),
        inputs=[meta(p) for p in [NATIVE, LOGICAL, READER, SOURCE, sent]], outputs=outputs,
        scope='Two retained phi1 windows resolve the forty logical low glyph addresses to plain mainRAM; no target RAM byte values seed the mapping.',
        field_count=2, physical_RAM_requests_per_field=8000, physical_glyph_address_count=40,
        mainRAM_base_bank0_maskFFFF_offset0_proved=True, no_character_ROM_or_Ultimax_match=True,
        no_cartridge_or_memory_hack_all18_snapshots=True, finite_low_RAM_cases=2048,
        CPU00_01_device_overlay_not_used_by_phi1=True, actual_mapping_is_no_longer_conditional=True,
        actual40_CPU_glyph_store_addresses_alias_phi1_RAM=True,
        source_copies_equal_pinned_archive_members=True, no_CPU_native_or_downloaded_host_execution=True,
        returned_glyph_data_join_not_implemented_here=True,
        limits=['Mapping holds within two declared clocks under inherited source/external-actor closure.',
            'Direct API/direct-assignment inventory is a bounded source audit, not a general compiler call graph.',
            'Byte evolution/store-vs-fetch timing belongs to the separately pinned glyph stream lane.',
            'No independent pixel, viewport, all-frame or FPS claim.']))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    produce(args.output.resolve())
