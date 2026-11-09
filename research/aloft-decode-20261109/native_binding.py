#!/usr/bin/env python3
"""Bind retained source/drive/C64 states; no CPU, native process or network."""
import argparse
import hashlib
import importlib.util
import json
import re
import tarfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-decode-20261109/binding-analysis'
OLD_PROOF = 'build/research/aloft-20261109/native-analysis/accepted-01/native-proof.json'
OLD_PROOF_SHA = '02243d0cbae68edad8aa5a51aec9e22e9cfa4c52f918f1ba30db9e5226b19eb4'
CATALOG_PROOF = 'build/research/aloft-20261109/loader-analysis/catalog-accepted-01/catalog-proof.json'
CATALOG_PROOF_SHA = 'a8109b96af82701bf61af84e7b054e8fff8048b1efcfefe52c631e54ee88f2b4'
SOURCE = ROOT / 'build/research/aloft-20261109/loader-analysis/catalog-source-02'
PINS = {
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
    'research/aloft-20261109/catalog.py': 'd7a0785fec84a3bfdd3d7eec1dadc16b40540dcaceaf0101bca4dee5ba4fd497',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'build/research/aloft-20261109/loader-analysis/catalog-source-02/resources__sl.asm': '46b28b74e9d2528b808e0c3fd0df08ef0ce7537d4a143527932bee46d9dcab60',
    'build/research/aloft-20261109/loader-analysis/catalog-source-02/resources__sd.asm': '7d6b673ff21f6efef523e04d9fb46a53eb05852d4a7182109365d33af684510a',
    'build/research/aloft-20261109/loader-analysis/catalog-source-02/sd.cpp': '0e28b8eb743494fab9ad6f914f047d05f4b729c4cc000820267172951ef06537',
    'build/research/aloft-20261109/loader-analysis/catalog-source-02/sparkle.cpp': '270767bed77d894a468ff74c4bfd40ae707663db80713364193dff13ee6e64ee',
    'build/research/aloft-decode-20261109/binding-analysis/snapshot-source-01/drivecpu.c': 'ae97a8c055e7ce1986f3bb507af1469ad9dc0a09c38a2577dbe79ffee379077c',
    'build/research/aloft-decode-20261109/binding-analysis/snapshot-source-01/drive-snapshot.c': '1904cf494aae10898f3586a6929a9c9910e0da432b20e6a064d10c644ac184e6',
    'build/research/aloft-decode-20261109/binding-analysis/snapshot-source-01/interrupt.c': '1c044ecf6aca0d382880fd8003e5230ef54c8fdeb1f7746e76bec759c43ea9fc',
    'build/research/aloft-decode-20261109/binding-analysis/snapshot-source-01/snapshot.h': '3df6889655fea9c7c6feccbab5692d0fc180ace1cc2540cbc3a3ed26f731ce65',
    'build/research/aloft-decode-20261109/binding-analysis/snapshot-source-01/source-record.json': '03ca0944d477ba813c4943af8f33ec6c70bcec906e68bd505409a6c8e0883516',
}
NEW_NATIVE_PROOF = 'build/research/aloft-decode-20261109/native-analysis/accepted-01/native-proof.json'
NEW_NATIVE_PROOF_SHA = 'bf53a544369a8acddde7354874b9f93302728497bd59a12c5c97b19e5c691b41'
BLOCK_PROOF = 'build/research/aloft-decode-20261109/block-analysis/accepted-01/block-proof.json'
BLOCK_PROOF_SHA = '768a37475c5e8e07c73fc8e0ab64c5ef80eea508212e462a3e8b58b8033e6ec3'
STREAM_PROOF = 'build/research/aloft-decode-20261109/stream-analysis/accepted-01/stream-proof.json'
STREAM_PROOF_SHA = '26c58f950464d7e37d94d99ecb19c79584004f5458306c0d3979168cb5c91b09'
PREFIX_PROOF = 'build/research/aloft-decode-20261109/block-analysis/sequential-prefix-accepted-01/prefix-export-proof.json'
PREFIX_PROOF_SHA = 'ac3b5f1f0f2731a51d1a6bbbfaf658869b588d842088ce0c130256d501d63e61'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def metadata(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def pinned_json(relative, expected):
    raw = (ROOT / relative).read_bytes()
    assert sha(raw) == expected, relative
    return json.loads(raw)


def module(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def verify_snapshot_source():
    """Retained official source is read as data; it is never compiled or executed."""
    folder = BASE / 'snapshot-source-01'
    record = json.loads((folder / 'source-record.json').read_text())
    archive = ROOT / record['archive']
    assert sha(archive.read_bytes()) == record['archive_sha256']
    with tarfile.open(archive) as source:
        for row in record['members']:
            members = [item for item in source.getmembers() if item.isfile() and item.name == row['member']]
            assert len(members) == 1
            raw = source.extractfile(members[0]).read()
            assert raw == (ROOT / row['path']).read_bytes()
            assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    interrupt = (folder / 'interrupt.c').read_text()
    old = interrupt.split('int interrupt_write_snapshot(', 1)[1].split('int interrupt_write_new_snapshot(', 1)[0]
    new = interrupt.split('int interrupt_write_new_snapshot(', 1)[1].split('int interrupt_write_sc_snapshot(', 1)[0]
    assert old.count('SMW_CLOCK') == 5 and new.count('SMW_DW') == 3
    assert '#define SMW_CLOCK    snapshot_module_write_qword' in (folder / 'snapshot.h').read_text()


def drive_snapshot(reader, path):
    """Official DRIVECPU1.3:52-byte CPU prefix +40 interrupt +2048RAM +12 interrupt."""
    state = reader.read_snapshot(path)
    payload = reader.module_payload(path, 'DRIVECPU0')
    drive = reader.module_payload(path, 'DRIVE8')
    assert state['modules']['DRIVECPU0']['version'] == [1, 3]
    assert len(payload) == 52 + 40 + 2048 + 12 == 2152
    assert state['modules']['DRIVE8']['version'] == [2, 0] and len(drive) == 145
    assert list(drive[:2]) == [1, 1] and int.from_bytes(drive[40:44], 'little') == 1541
    ram = payload[92:2140]
    return ram, {'pc': int.from_bytes(payload[12:14], 'little'),
        'clock_raw': int.from_bytes(payload[:8], 'little'), 'a': payload[8],
        'x': payload[9], 'y': payload[10], 'sp': payload[11],
        'flags': payload[14], 'RAM_payload_offset': 92, 'RAM_bytes': 2048,
        'RAM_sha256': sha(ram), 'module_payload_sha256': sha(payload),
        'drive_type': 1541, 'true_drive_enabled': True}


def source_contract(catalog):
    sd = catalog.array((SOURCE / 'sd.cpp').read_text(), 'sd')
    # The compiled exact primary array and named assembly contract independently
    # bind the sole self-modified index byte; no whole-runtime normalization.
    pattern = bytes.fromhex('a203bd00079520ca10f8a2c08776293f8520')
    assert sd.count(pattern) == 1
    dirloop = 0x0300 + sd.index(pattern) + 2
    assert dirloop == 0x05a5
    assert bytes.fromhex('0a8d') + (dirloop + 1).to_bytes(2, 'little') in sd
    source = (SOURCE / 'resources__sd.asm').read_text()
    assert all(text in source for text in [
        'sta DirLoop+1', 'adc #$11', 'cmp DirSector', 'DirLoop:\tlda $0700,x',
        'sta LastT,x', '.label BPtr\t\t\t=$23', 'inc Random'])
    return sd, dirloop, pattern[2:]


def expected_caches(catalog, catalog_proof):
    """All directory candidates come from original disks, before reading native RAM."""
    candidates = []
    for side in catalog_proof['sides']:
        # The frozen catalog explicitly supplies each original disk identity.
        disk_meta = next(row for row in catalog_proof['inputs']
                         if row['path'].endswith(f"/Aloft-Side{side['side']}.d64"))
        path = ROOT / disk_meta['path']
        assert metadata(path) == disk_meta
        disk = path.read_bytes()
        for sector in [17, 18]:
            logical = catalog.reverse_sector(catalog.sector(disk, 18, sector))
            candidates.append({'side': side['side'], 'directory_sector': sector,
                'disk': disk_meta, 'bytes': bytes(catalog.transform(value) for value in logical),
                'logical': logical})
    assert len(candidates) == 6
    return candidates


def associate_drive(ram, context, candidates, dirloop, canonical):
    current = ram[dirloop:dirloop + len(canonical)]
    installed = current[:1] == canonical[:1] and current[2:] == canonical[2:]
    result = {'drive_CPU': context, 'Sparkle_DirLoop_generation_present': installed,
        'directory_sector_state': ram[0x5e],
        'dynamic_state': {'current_track': ram[0], 'current_sector': ram[1],
            'next_sector': ram[2], 'blocks_left': ram[3], 'LastT': ram[0x20],
            'LastS': ram[0x21], 'SCtr': ram[0x22], 'BPtr_encoded': ram[0x23],
            'Random': ram[0x18], 'NBC': ram[0x5c]}}
    if not installed or ram[0x5e] not in (17, 18):
        result['binding'] = 'No loaded-directory/index association at this pre-cache generation.'
        return result
    index_byte = current[1]
    assert index_byte % 4 == 0
    matches = [item for item in candidates if ram[0x700:0x800] == item['bytes']]
    assert len(matches) == 1, ('directory cache not uniquely original-source bound', len(matches))
    match = matches[0]
    assert match['directory_sector'] == ram[0x5e]
    slot = (ram[0x5e] - 17) * 64 + index_byte // 4
    raw = match['logical'][index_byte:index_byte + 4]
    assert len(raw) == 4
    # BPtr retains the transformed fourth directory byte, while LastT/LastS/SCtr
    # are subsequently changed by track/block progress and must not be frozen.
    assert ram[0x23] == match['bytes'][index_byte + 3]
    result.update({'binding': 'Last drive-directory selection, including bootstrap slot0; not a current sequential-bundle index or proof of an explicit C64 command.',
        'side': match['side'], 'slot': slot, 'DirLoop_PC': dirloop,
        'DirLoop_operand': 0x0700 + index_byte, 'cached_all256_bytes_equal_original': True,
        'cached_directory_sha256': sha(ram[0x700:0x800]),
        'raw_directory_record_hex': raw.hex(), 'raw_stream_pointer': raw[3],
        'drive_pointer_encoded': ram[0x23], 'original_disk': match['disk']})
    return result


def inspect_case(reader, proof, family, candidates, dirloop, canonical):
    records = []
    case_root = (ROOT / proof['captures'][0]['ram']['path']).parent
    events_path = case_root / 'events.jsonl'
    received_path = case_root / 'received.bin'
    events = [json.loads(line) for line in events_path.read_text().splitlines()]
    received = received_path.read_bytes()
    responses = {row['sequence']: row for row in events if row['kind'] == 'response'}
    for capture in proof['captures']:
        ram_path, snapshot_path = ROOT / capture['ram']['path'], ROOT / capture['snapshot']['path']
        assert metadata(ram_path) == capture['ram'] and metadata(snapshot_path) == capture['snapshot']
        c64 = ram_path.read_bytes()
        state = reader.read_snapshot(snapshot_path)
        assert reader.module_payload(snapshot_path, 'C64MEM')[4:65540] == c64
        drive, context = drive_snapshot(reader, snapshot_path)
        record = {'case_family': family, 'stem': capture['stem'], 'ram': capture['ram'],
            'snapshot': capture['snapshot'], 'C64_registers': capture['registers'],
            'wrapper_counter_088D': c64[0x088d],
            'C64_packet_buffer_oracle': {'first': 0x0300, 'bytes': 256,
                'sha256': sha(c64[0x300:0x400]), 'cursor_or_header_03FF': c64[0x3ff],
                'role': 'Comparison/context only, never original packet prediction input.'},
            'drive_association': associate_drive(drive, context, candidates, dirloop, canonical)}
        refs = []
        for sequence in [capture['stop_sequence'], capture['register_sequence']]:
            row = responses[sequence]
            first, end = row['received_first'], row['received_end']
            raw = received[first:end]
            assert raw.decode('utf-8', errors='replace') == row['response']
            refs.append({'sequence': sequence, 'command': row['command'], 'status': row['status'],
                         'first': first, 'end': end, 'bytes': len(raw), 'raw_sha256': sha(raw),
                         'whole_received': metadata(received_path), 'whole_events': metadata(events_path)})
        record['source_capture_wire_refs'] = refs
        if capture['stem'] == 'loadnext01' and family == 'old-native01':
            regs = capture['registers']
            assert regs['pc'] == 0x021c and regs['sp'] == 0x5d
            continuation = (int.from_bytes(c64[0x101 + regs['sp']:0x103 + regs['sp']], 'little') + 1) & 65535
            assert continuation == 0x0890 and c64[0x3ff] == 0x33
            record['external_call_binding'] = {'api': 'LoadNext', 'saved_RTS_continuation': continuation,
                'buffer_state': 'Previously consumed packet; next sequential bundle starts from saved cursor, not a new indexed directory request.',
                'no_directory_index_inferred_from_088D': True}
        records.append(record)
    return records


def prediction_output(proof_path, proof, name):
    row = next(row for row in proof['outputs'] if row['name'] == name)
    path = proof_path.parent / name
    raw = path.read_bytes()
    assert len(raw) == row['bytes'] and sha(raw) == row['sha256']
    return raw, metadata(path)


def compare_mask(predicted, mask, actual):
    """Comparison only: target bytes neither change prediction nor supply an initial state."""
    assert len(predicted) == len(mask) == len(actual) == 65536
    assert set(mask) <= {0, 1} and not any(mask[:2])
    mismatches = [address for address, known in enumerate(mask)
                  if known and predicted[address] != actual[address]]
    assert not mismatches, mismatches[:32]
    addresses = [address for address, known in enumerate(mask) if known]
    spans = []
    for address in addresses:
        if spans and spans[-1][1] == address:
            spans[-1][1] += 1
        else:
            spans.append([address, address + 1])
    return {'compared_bytes': len(addresses), 'all_equal': True, 'spans_exclusive': spans,
            'compared_prediction_bytes_sha256': sha(bytes(predicted[a] for a in addresses))}


def bundle_state(bundle, ledger, descriptor, packets):
    """Materialize already predicted writes/format state. Unknown zeros are storage only."""
    predicted, written = bytearray(65536), bytearray(65536)
    for row in ledger[:descriptor['end_RAM_write']]:
        assert row['bundle'] <= bundle and 0 <= row['address'] <= 65535
        predicted[row['address']] = row['value']
        written[row['address']] = 1
    known = bytearray(written)
    packet = bytearray(packets[descriptor['packet_at_return']])
    # Historical SL writes Buffer0 at destination-header setup and BufferFF
    # at EndOfBundle. Format-state bytes are distinct from decoded payload.
    packet[0], packet[255] = 0, descriptor['saved_LastX']
    predicted[0x300:0x400] = packet
    known[0x300:0x400] = bytes([1]) * 256
    assert not any(written[0x300:0x400])
    return bytes(predicted), bytes(written), bytes(known)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(BASE.resolve())
    assert not out.exists(), 'fresh output directory required'
    for name, expected in PINS.items():
        assert sha((ROOT / name).read_bytes()) == expected, name
    verify_snapshot_source()
    reader = module('aloft_binding_snapshot', 'research/quondam/snapshot_state.py')
    catalog = module('aloft_binding_catalog', 'research/aloft-20261109/catalog.py')
    old = pinned_json(OLD_PROOF, OLD_PROOF_SHA)
    new = pinned_json(NEW_NATIVE_PROOF, NEW_NATIVE_PROOF_SHA)
    catalog_proof = pinned_json(CATALOG_PROOF, CATALOG_PROOF_SHA)
    block = pinned_json(BLOCK_PROOF, BLOCK_PROOF_SHA)
    stream = pinned_json(STREAM_PROOF, STREAM_PROOF_SHA)
    prefix = pinned_json(PREFIX_PROOF, PREFIX_PROOF_SHA)
    proofs = [old, new, catalog_proof, block, stream, prefix]
    for proof in proofs:
        assert proof['pass_'] and metadata(ROOT / proof['producer']['path']) == proof['producer']
        for row in proof.get('inputs', []):
            assert metadata(ROOT / row['path']) == row
    assert len(old['captures']) == 25 and len(new['captures']) == 7
    assert old['session']['owned_process_reaped'] and new['session']['owned_process_reaped']
    assert old['case_manifest']['path'] != new['case_manifest']['path']
    for proof in [old, new]:
        assert metadata(ROOT / proof['case_manifest']['path']) == proof['case_manifest']
    assert stream['initial_RAM_is_unknown']
    assert stream['native_expected_RAM_or_pixels_are_never_inputs']
    assert stream['decoded_IO_bus_writes'] == 0 and stream['decoded_RAM_unique_bytes'] == 5977
    assert len(stream['bundles']) == 2 and stream['received_packets'] == 13
    sd, dirloop, canonical = source_contract(catalog)
    candidates = expected_caches(catalog, catalog_proof)
    old_rows = inspect_case(reader, old, 'old-native01', candidates, dirloop, canonical)
    new_rows = inspect_case(reader, new, 'fresh-native01', candidates, dirloop, canonical)
    assert all(row['drive_association'].get('slot') == 5 and row['drive_association']['side'] == 1 for row in old_rows)
    assert {row['wrapper_counter_088D'] for row in old_rows} != {5}
    ncap = {row['stem']: row for row in new['captures']}
    nrows = {row['stem']: row for row in new_rows}
    native_ram = {name: (ROOT / row['ram']['path']).read_bytes() for name, row in ncap.items()}
    for name in ['first-packet-ready', 'first-payload-entry', 'second-request', 'second-return']:
        assert nrows[name]['drive_association']['slot'] == 0
        assert nrows[name]['drive_association']['side'] == 1
    for name, pc in [('first-receive-entry', 0x019f), ('first-packet-ready', 0x021c),
                     ('first-payload-entry', 0xfe00), ('second-request', 0xfe41), ('second-return', 0xfe44)]:
        assert ncap[name]['registers']['pc'] == pc
    ready_regs = ncap['first-packet-ready']['registers']
    ready_ram = native_ram['first-packet-ready']
    continuation = (int.from_bytes(ready_ram[0x101 + ready_regs['sp']:0x103 + ready_regs['sp']], 'little') + 1) & 65535
    assert continuation == 0xfe00

    stream_path, block_path, prefix_path = ROOT / STREAM_PROOF, ROOT / BLOCK_PROOF, ROOT / PREFIX_PROOF
    raw_ledger, ledger_meta = prediction_output(stream_path, stream, 'decoded-RAM-writes.json')
    ledger = json.loads(raw_ledger)
    used_raw, used_meta = prediction_output(stream_path, stream, 'source-packets-used.json')
    used = json.loads(used_raw)
    plan_meta = used['plan']
    plan_path = ROOT / plan_meta['path']
    assert metadata(plan_path) == plan_meta
    plan = json.loads(plan_path.read_text())
    assert plan['indexed_slot'] == 0 and len(plan['packets']) == 128
    plan_record = next(row for row in prefix['outputs'] if row['name'] == plan_path.name)
    assert (plan_record['bytes'], plan_record['sha256']) == (plan_meta['bytes'], plan_meta['sha256'])
    packets, packet_refs = [], []
    for item in plan['packets'][:13]:
        path = plan_path.parent / item['path']
        raw = path.read_bytes()
        assert len(raw) == item['bytes'] == 256 and sha(raw) == item['sha256']
        packets.append(raw)
        packet_refs.append(metadata(path))
    original_first, original_first_meta = prediction_output(block_path, block, 'side1-slot000-packet000.bin')
    assert packets[0] == original_first == ready_ram[0x300:0x400]
    states = [bundle_state(index, ledger, desc, packets) for index, desc in enumerate(stream['bundles'])]
    assert sum(states[0][1]) == 493 and sum(states[0][2]) == 749
    assert sum(states[1][1]) == 5977 and sum(states[1][2]) == 6233
    final_predicted, final_meta = prediction_output(stream_path, stream, 'predicted-memory.bin')
    final_written, written_meta = prediction_output(stream_path, stream, 'decoded-RAM-write-mask.bin')
    final_known, known_meta = prediction_output(stream_path, stream, 'known-memory-mask.bin')
    assert states[1][1:] == (final_written, final_known)
    compare_mask(states[1][0], final_known, final_predicted)
    comparisons = {
        'unconsumed_packet': {'source': original_first_meta, 'oracle': ncap['first-packet-ready']['ram'],
                             'all256_equal': True, 'prior_LD_Fetched_entry': ncap['first-receive-entry']['ram']},
        'bundle0_payload': compare_mask(states[0][0], states[0][1], native_ram['first-payload-entry']),
        'bundle0_all_known': compare_mask(states[0][0], states[0][2], native_ram['first-payload-entry']),
        'application_boundary_invariant': compare_mask(states[0][0], states[0][2], native_ram['second-request']),
        'bundle1_payload': compare_mask(states[1][0], states[1][1], native_ram['second-return']),
        'bundle1_all_known': compare_mask(states[1][0], states[1][2], native_ram['second-return'])}
    assert native_ram['first-payload-entry'][0x300:0x400] == native_ram['second-request'][0x300:0x400]
    source_prediction = states[0][0]
    assert source_prediction[0xfe3c:0xfe47] == bytes.fromhex('a2008eff08201c02207afe')
    assert source_prediction[0x0809:0x080f] == bytes.fromhex('ee8d084c1c02')
    source_stores = [{'pc': pc, 'address': address, 'value': value, 'space': space}
        for pc, address, value, space in [(0xfe13, 0xdc07, 0, 'IO'), (0xfe18, 0xdc06, 0x3e, 'IO'),
            (0xfe1c, 0xd01a, 1, 'IO'), (0xfe21, 0xdc02, 255, 'IO'), (0xfe2c, 0xdc0f, 0x11, 'IO'),
            (0xfe3e, 0x08ff, 0, 'RAM')]]
    assert native_ram['second-request'][0x08ff] == 0 and not states[0][2][0x08ff]
    logical_slots = json.loads((ROOT / 'build/research/aloft-20261109/loader-analysis/catalog-accepted-01/side1-directory-slots.json').read_text())
    returns = []
    for desc in stream['bundles']:
        source_packet = plan['packets'][desc['packet_at_return']]['source']
        matches = [slot for slot in logical_slots if slot['derived_first_block']['block_ordinal'] == source_packet['writer_block_ordinal']
                   and slot['stream_pointer'] == desc['saved_LastX']]
        assert len(matches) == 1
        returns.append({'decoded_bundle': desc['bundle'], 'saved_LastX': desc['saved_LastX'],
            'source_writer_ordinal': source_packet['writer_block_ordinal'], 'directory_equivalent_slot': matches[0]['slot'],
            'meaning': 'Logical continuation equivalence; no new indexed C64 command or drive-directory selection is implied.'})
    assert [row['directory_equivalent_slot'] for row in returns] == [1, 2]
    inputs = [metadata(ROOT / name) for name in PINS]
    inputs += [metadata(ROOT / name) for name in [OLD_PROOF, NEW_NATIVE_PROOF, CATALOG_PROOF, BLOCK_PROOF, PREFIX_PROOF, STREAM_PROOF]]
    inputs += [ledger_meta, used_meta, plan_meta, final_meta, written_meta, known_meta] + packet_refs
    inputs += [metadata(ROOT / 'build/research/aloft-20261109/loader-analysis/catalog-accepted-01/side1-directory-slots.json')]
    associations = {'old_case': old_rows, 'fresh_case': new_rows,
        'source_call_boundaries': {'first_receive_RTS_continuation': continuation,
            'first_return': 0xfe00, 'next_call_PC': 0xfe41, 'next_call_opcode': 'JSR021C', 'next_return_PC': 0xfe44,
            'sequential_no_index_parameter': True}, 'logical_continuations': returns,
        'main_path_source_stores_before_second_call': source_stores}
    out.mkdir(parents=True)
    checked, details, checks = out / 'native_binding.checked.py', out / 'case-associations.json', out / 'oracle-comparisons.json'
    checked.write_bytes(Path(__file__).read_bytes())
    details.write_text(json.dumps(associations, indent=2) + '\n')
    checks.write_text(json.dumps(comparisons, indent=2) + '\n')
    outputs = [{'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())} for path in [checked, details, checks]]
    proof = {'pass_': True, 'scope': 'Independent native drive-directory/source-call association and post-prediction comparison of two original decoded bundles.',
        'producer': metadata(Path(__file__).resolve()), 'inputs': inputs,
        'native_families': [{'name': 'old-native01', 'proof': metadata(ROOT / OLD_PROOF), 'captures': 25},
                            {'name': 'fresh-native01', 'proof': metadata(ROOT / NEW_NATIVE_PROOF), 'captures': 7}],
        'drive_snapshot_schema': {'module': 'DRIVECPU0', 'version': [1, 3], 'CPU_prefix': 52,
            'old_interrupt_bytes': 40, 'RAM_offset': 92, 'RAM_bytes': 2048, 'new_interrupt_bytes': 12,
            'payload_bytes': 2152, 'drive_type_module': 'DRIVE8v2.0', 'drive_type_offset': 40, 'drive_type': 1541},
        'directory_association': {'old25_all_side': 1, 'old25_last_selected_slot': 5,
            'old_DirLoop_operand': 0x0714, 'fresh_postreceive_selected_slot': 0,
            'raw_and_drive_pointer_domains_differ': True, 'all_cached256_directory_bytes_checked': True,
            'wrapper_counter_is_not_directory_slot': True, 'DirLoop_PC_source_derived': dirloop},
        'source_call_boundaries': associations['source_call_boundaries'], 'logical_continuations': returns,
        'native_oracle_comparisons': comparisons,
        'prediction_source_only_UNKNOWN_start': True, 'target_data_or_changed_masks_never_prediction_inputs': True,
        'actual_rotational_order_claimed': False, 'named_three_layer_effect_identified': False,
        'limits': ['DriveDirLoop records the last directory selection, including drive-bootstrap slot0, not every current sequential bundle.',
            'Old orientation and later cases have observed slot5 anchor; intervening source stream generations are not assigned by088D arithmetic.',
            'The declared13-packet canonical source order is not a native transfer-order trace or an all-order equivalence theorem.',
            'The749-byte application-boundary invariant is an endpoint comparison, not absence of transient IRQ or hardware mutations.',
            'Only two bundles and their clean return states are compared; later decoder exploration remains separate.',
            'The three-layer pattern, physical IEC timing, complete effects, committed pixels, whole-animation/FPS and products remain outside scope.'],
        'outputs': outputs}
    receipt = out / 'native-binding-proof.json'
    receipt.write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({'pass_': True, 'receipt': metadata(receipt), 'captures': 32,
                      'payload_comparisons': [493, 5977], 'format_state_separate': True}))


if __name__ == '__main__':
    main()
