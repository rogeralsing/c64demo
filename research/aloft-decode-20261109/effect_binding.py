#!/usr/bin/env python3
"""Late finite byte association of source-only bundle generations and native oracles.

No token decoding, CPU execution, application simulation, native process or network.
All complete source generations and masks are pinned before native RAM is opened.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-decode-20261109/effect-analysis'
EXPLORATION = 'build/research/aloft-decode-20261109/stream-analysis/all-side1-exploration-01/all-side1-exploration.json'
EXPLORATION_SHA = 'ffc37070df52d17beb032e521a51b3c6fc42b068ab170f471fdf5a8871a11409'
COLOR = 'build/research/aloft-decode-20261109/color-analysis/accepted-01/color-stream-proof.json'
COLOR_SHA = '44bbc6a94b22db33d81dc9f15178f1303a2db19fb22484292e0c6f894f00f4b2'
NATIVE = 'build/research/aloft-20261109/native-analysis/accepted-01/native-proof.json'
NATIVE_SHA = '02243d0cbae68edad8aa5a51aec9e22e9cfa4c52f918f1ba30db9e5226b19eb4'
PARTS = 'build/research/aloft-20261109/part-analysis/accepted-01/part-localization-proof.json'
PARTS_SHA = '717eadcfc45d37accd79a272f80ffd1e4430c8ed8e68bb38fd20158cb84685c8'
KEFRENS = 'build/research/aloft-20261109/kefrens-analysis/accepted-02/kefrens-source-proof.json'
KEFRENS_SHA = '26d3cf4b4100a34e75feadab827fb72fcd08676c0c16817f340454c64b6c92d1'
BINDING = 'build/research/aloft-decode-20261109/binding-analysis/accepted-01/native-binding-proof.json'
BINDING_SHA = '60003d4a605b2891a385a31630ee752183c48f3002d577ac7c7f2a78fc07c06d'
READER = 'research/quondam/snapshot_state.py'
READER_SHA = 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a'

# Fixed contiguous windows, including data/padding where indicated. These are not
# inferred resource ends or a matching-byte selection mask. Every byte is checked.
# Existing part-localization routes justify the calls, lookup footprints and copy
# lengths. Broad code windows are explicitly finite windows, not reachability claims.
WINDOWS = [
    ('part01-wrapper', 'part01-entry', 0x0890, 0x089f, 'guarded dispatch including both calls and pushed continuation'),
    ('part01-code-window', 'part01-entry', 0x2c00, 0x2f00, 'selected 768-byte init/IRQ-generation window; includes data/padding'),
    ('part01-glyph-input', 'part01-entry', 0x7c00, 0x8000, 'full 1024-byte source of the native init copy to 2800'),
    ('part02-wrapper', 'part02-entry', 0x0890, 0x08a3, 'guarded changed wrapper through the E000 call'),
    ('part02-6600-window', 'part02-entry', 0x6600, 0x6800, 'selected 512-byte source window already loaded before the next call'),
    ('part03-6600-window', 'part03-entry', 0x6600, 0x6800, 'same complete window after the additional natural sequential return'),
    ('part04-E000-window', 'part04-entry', 0xe000, 0xe100, 'selected 256-byte later init generation'),
    ('part05-wrapper-window', 'part05-entry', 0x0890, 0x08c0, 'selected 48-byte dispatch window including table-test route'),
    ('part05-E000-window', 'part05-entry', 0xe000, 0xe180, 'selected 384-byte init/body/IRQ-source window'),
    ('part06-wrapper-window', 'part06-entry', 0x0890, 0x08dd, 'selected wrapper through relocation and clear sites'),
    ('part06-Kefrens-source', 'part06-entry', 0x4800, 0x5376, 'full 2934-byte source span declared by the frozen Kefrens study'),
    ('part06-relocation-input', 'part06-precopy', 0x6000, 0x7ffe, 'all 8190 source bytes of the separately proven native relocation'),
    ('part07-wrapper', 'part07-entry', 0x0890, 0x08ad, 'wrapper before and through background/text calls'),
    ('part07-8000-window', 'part07-entry', 0x8000, 0x83e4, 'selected 996-byte init/IRQ/background-copy window'),
    ('part07-text-generator-window', 'part07-entry', 0x2000, 0x2174, 'selected 372-byte four-stream generator window'),
    ('part07-text-inputs', 'part07-entry', 0x3db5, 0x3e8d, 'four contiguous 53-character streams plus terminators'),
    ('part07-glyph-values', 'part07-entry', 0x8800, 0x8900, 'all 256 glyph-value lookup bytes'),
    ('part07-glyph-indices', 'part07-entry', 0x8a00, 0x8b00, 'all 256 glyph-index lookup bytes'),
    ('part07-background-input', 'part07-entry', 0x9000, 0x9514, 'all 52 by 25 original background input bytes'),
    ('part08-wrapper', 'part08-entry', 0x0890, 0x089e, 'guarded changed clock-domain wrapper through F02B call'),
    ('part08-F000-window', 'part08-entry', 0xf000, 0xf840, 'selected 2112-byte source window containing setup, IRQ and generators'),
    ('part08-call-template', 'part08-entry', 0xf817, 0xf830, 'all 25 source bytes of the separately proven 0500 call-kernel template'),
    ('part09-wrapper-only', 'part09-entry', 0x0890, 0x0896, 'six dispatch bytes only; no renderer study or scene inference'),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def metadata(path):
    raw = path.read_bytes()
    return {'path': path.relative_to(ROOT).as_posix(), 'bytes': len(raw), 'sha256': sha(raw)}


def checked_ref(item):
    path = (ROOT / item['path']).resolve()
    path.relative_to(ROOT)
    raw = path.read_bytes()
    assert len(raw) == item['bytes'] and sha(raw) == item['sha256'], item['path']
    return raw


def pinned_json(relative, digest):
    path = ROOT / relative
    raw = path.read_bytes()
    assert sha(raw) == digest, relative
    return json.loads(raw), metadata(path)


def intervals(values):
    result = []
    for value in values:
        if result and result[-1][1] == value:
            result[-1][1] += 1
        else:
            result.append([value, value + 1])
    return result


def source_generations():
    """Validate the entire fixed source prediction before opening a native oracle."""
    source, source_meta = pinned_json(EXPLORATION, EXPLORATION_SHA)
    assert source['status'] == 'stopped-software-only-original-side1-exploration'
    assert all(source[key] is True for key in (
        'initial_RAM_unknown', 'native_RAM_oracles_never_read', 'token_semantics_unchanged'))
    assert source['decoded_completed_bundle_count'] == 22
    assert source['partial_bundle'] == 22 and source['packets_consumed'] == 386
    assert source['received_plan_packets'] == 597
    assert source['total_RAM_write_operations'] == 208957
    assert source['total_IO_bus_write_operations'] == 2
    assert source['partial_after_last_complete_RAM_writes'] == 0
    assert source['stop'] == {'reason': 'I/O-visible match/literal read needs device provenance',
        'address': 0xdbe7, 'bundle': 22, 'packet': 385, 'token': 49004, 'cursor': 129}
    for key in ('producer', 'frozen_model', 'original_transport_receipt', 'packet_plan'):
        checked_ref(source[key])
    assert source['frozen_model']['sha256'] == '180b2835ea06f7f7ae4d15d765eb3c64c9518f8d03fc6ee350d33ce9eccef036'
    assert source['original_transport_receipt']['sha256'] == '093a3f02ef4e05987d93f9d8f58199623dab47c9502b9aee804072f0bd9bb2eb'
    outputs = {item['path']: item for item in source['outputs']}
    assert len(outputs) == len(source['outputs']) == 96
    for item in source['outputs']:
        checked_ref(item)
    io_item = next(item for item in source['outputs'] if item['path'].endswith('/IO-write-events.json'))
    io = json.loads(checked_ref(io_item))
    assert [(item['address'], item['value'], item['bundle'], item['packet']) for item in io] == [
        (0xdbe8, 0x0c, 22, 385), (0xdbe7, 0x0f, 22, 385)]
    generations, reports, last_end = [], [], 0
    cumulative = bytes(65536)
    for number, item in enumerate(source['completed_bundles']):
        assert item['bundle'] == number
        assert item['first_RAM_write'] == last_end
        assert item['end_RAM_write'] - item['first_RAM_write'] == item['RAM_writes']
        assert item['IO_writes'] == 0
        last_end = item['end_RAM_write']
        files = {Path(ref['path']).name.removeprefix(f'bundle{number:03d}-'): ref for ref in item['files']}
        assert set(files) == {'memory.bin', 'known-mask.bin', 'cumulative-write-mask.bin', 'delta-write-mask.bin'}
        for ref in files.values():
            assert outputs[ref['path']] == ref
        data = {key: checked_ref(ref) for key, ref in files.items()}
        assert all(len(raw) == 65536 for raw in data.values())
        memory, known, written, delta = (data[name] for name in (
            'memory.bin', 'known-mask.bin', 'cumulative-write-mask.bin', 'delta-write-mask.bin'))
        assert set(known) <= {0, 1} and set(written) <= {0, 1} and set(delta) <= {0, 1}
        assert sum(known) == item['known_RAM_bytes']
        assert sum(written) == item['current_payload_RAM_bytes']
        assert sum(delta) == item['distinct_current_bundle_RAM_addresses']
        assert all(not written[i] or known[i] for i in range(65536))
        # The frozen decoder replaces0300..03FF with each received packet and
        # clears payload eligibility there. It is not a monotone payload mask
        # inside that transport buffer; do not reclassify received bytes as RAM
        # payload merely because an earlier bundle once wrote the same address.
        assert all(written[i] == bool(cumulative[i] or delta[i])
                   for i in range(65536) if not 0x300 <= i < 0x400)
        cumulative = written
        generations.append({'bundle': number, 'memory': memory, 'known': known,
            'written': written, 'delta': delta, 'files': files, 'record': item})
        reports.append({key: value for key, value in item.items() if key != 'files'} | {
            'files': item['files'], 'all_masks_binary': True,
            'all_payload_written_bytes_known': True,
            'cumulative_mask_union_matches_outside_packet_buffer': True,
            'packet_buffer_payload_eligibility_reset_range': [0x300, 0x400]})
    assert last_end == 208957 and len(generations) == 22
    return source, source_meta, generations, reports


def color_generations(strict):
    """A separately pinned source-only extension, still before any native read.

    This comparator consumes only its full physical-RAM values. The separately
    tracked ColorRAM low bits never become physical RAM or full-byte oracles.
    """
    source, source_meta = pinned_json(COLOR, COLOR_SHA)
    assert source['pass_'] is True
    assert source['all_initial_RAM_and_device_low_bits_unknown'] is True
    assert source['native_values_never_inputs'] is True
    assert source['completed_bundle_count'] == 43
    assert source['partial_bundle'] == 43 and source['packets_consumed'] == 597
    assert source['stop'] == {'reason': 'Original source packet plan exhausted', 'packets_consumed': 597}
    assert source['total_RAM_write_operations'] == 325106
    assert source['partial_RAM_writes_since_last_complete'] == 1
    assert source['frozen_RAM_only_prefix_predictions_equal'] == list(range(22))
    assert source['known_device_ColorRAM_cells'] == 1001
    assert source['producer']['sha256'] == 'b9ff969afb07320621dad0f107fc31a343a3e34c06566356143f9d8870cbd2c6'
    assert source['frozen_decoder']['sha256'] == '180b2835ea06f7f7ae4d15d765eb3c64c9518f8d03fc6ee350d33ce9eccef036'
    checked_ref(source['producer'])
    checked_ref(source['frozen_decoder'])
    for ref in source['inputs']:
        checked_ref(ref)
    folder = (ROOT / COLOR).parent
    refs = {}
    for ref in source['outputs']:
        name = ref['name']
        assert Path(name).name == name and name not in refs
        refs[name] = {'path': (folder / name).relative_to(ROOT).as_posix(),
            'bytes': ref['bytes'], 'sha256': ref['sha256']}
        checked_ref(refs[name])
    assert len(refs) == 271
    generations, reports, cumulative, last_end = [], [], bytes(65536), 0
    for number, item in enumerate(source['completed_bundles']):
        assert item['bundle'] == number
        assert item['first_RAM_write'] == last_end
        assert item['end_RAM_write'] - item['first_RAM_write'] == item['RAM_writes']
        last_end = item['end_RAM_write']
        files = {ref['name'].removeprefix(f'bundle{number:03d}-'): refs[ref['name']]
                 for ref in item['files']}
        for ref in item['files']:
            assert {key: refs[ref['name']][key] for key in ('bytes', 'sha256')} == {
                key: ref[key] for key in ('bytes', 'sha256')}
        assert set(files) == {'memory.bin', 'known-mask.bin', 'cumulative-write-mask.bin',
            'delta-write-mask.bin', 'ColorRAM-low-bits.bin', 'ColorRAM-known-mask.bin'}
        data = {name: checked_ref(ref) for name, ref in files.items()}
        memory, known, written, delta = (data[name] for name in (
            'memory.bin', 'known-mask.bin', 'cumulative-write-mask.bin', 'delta-write-mask.bin'))
        assert all(len(raw) == 65536 for raw in (memory, known, written, delta))
        assert set(known) <= {0, 1} and set(written) <= {0, 1} and set(delta) <= {0, 1}
        assert sum(known) == item['known_RAM_bytes']
        assert all(not written[i] or known[i] for i in range(65536))
        assert all(written[i] == bool(cumulative[i] or delta[i])
                   for i in range(65536) if not 0x300 <= i < 0x400)
        assert len(data['ColorRAM-low-bits.bin']) == len(data['ColorRAM-known-mask.bin']) == 1024
        assert set(data['ColorRAM-low-bits.bin']) <= set(range(16))
        assert set(data['ColorRAM-known-mask.bin']) <= {0, 15}
        assert sum(value == 15 for value in data['ColorRAM-known-mask.bin']) == item['known_device_ColorRAM_cells']
        cumulative = written
        if number < len(strict):
            for name, key in [('memory.bin', 'memory'), ('known-mask.bin', 'known'),
                              ('cumulative-write-mask.bin', 'written'), ('delta-write-mask.bin', 'delta')]:
                assert data[name] == strict[number][key], (number, name)
        generations.append({'bundle': number, 'memory': memory, 'known': known,
            'written': written, 'delta': delta, 'files': files, 'record': item})
        reports.append({key: value for key, value in item.items() if key != 'files'} | {
            'files': list(files.values()), 'all_RAM_masks_binary': True,
            'ColorRAM_low_nibbles_and_known_masks_separate_from_RAM': True,
            'full_RAM_prefix_equal_strict_prediction': number < 22,
            'all_payload_written_bytes_known': True,
            'cumulative_mask_union_matches_outside_packet_buffer': True})
    assert last_end == 325105 and len(generations) == 43
    return source, source_meta, generations, reports, list(refs.values())


def native_captures(proof):
    """Recheck selected full RAM/VSF/CPU identities; boot/wire audit stays delegated."""
    path = ROOT / READER
    assert sha(path.read_bytes()) == READER_SHA
    spec = importlib.util.spec_from_file_location('aloft_effect_snapshot_reader', path)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    entries = {item['stem']: item for item in proof['captures']}
    assert len(entries) == len(proof['captures']) == 25
    memories, captures = {}, []
    for stem in dict.fromkeys(item[1] for item in WINDOWS):
        item = entries[stem]
        raw = checked_ref(item['ram'])
        checked_ref(item['snapshot'])
        vsf = ROOT / item['snapshot']['path']
        state = reader.read_snapshot(vsf)
        cpu, mem = reader.module_payload(vsf, 'MAINCPU'), reader.module_payload(vsf, 'C64MEM')
        assert state['modules']['MAINCPU']['version'] == [1, 4] and len(cpu) == 103
        assert state['modules']['C64MEM']['version'] == [0, 1] and len(mem) == 65555
        assert len(raw) == 65536 and raw == mem[4:65540]
        pc, clock = int.from_bytes(cpu[12:14], 'little'), int.from_bytes(cpu[:8], 'little')
        registers = item['registers']
        assert (pc, clock, cpu[11], cpu[8], cpu[9], cpu[10], cpu[14]) == (
            registers['pc'], registers['clock'], registers['sp'], registers['a'],
            registers['x'], registers['y'], registers['flags'])
        assert item['stop']['natural'] is True and item['CPU_clock_flags_and_ports_equal'] is True
        assert item['all65536_physical_RAM_bytes_equal'] is True
        assert mem[1] == mem[65542] == 0x2f
        assert registers['port00'] == mem[65542] and registers['port01'] == mem[65541]
        assert mem[0] & mem[1] == mem[65541] & mem[1]
        assert (registers['line'], registers['cycle']) == (clock // 63 % 312, clock % 63)
        assert raw[0x088d] == item['wrapper_counter']
        memories[stem] = raw
        captures.append({'stem': stem, 'ram': item['ram'], 'snapshot': item['snapshot'],
            'stop_sequence': item['stop_sequence'], 'pc': pc, 'clock': clock,
            'sp': cpu[11], 'wrapper_bookkeeping_088D': item['wrapper_counter'],
            'CPU_ports': {'DDR': mem[1], 'latch': mem[0], 'read': mem[65541]},
            'beam': item['beam'], 'all65536_RAM_bytes_equal_snapshot': True,
            'native_wire_boot_and_checkpoint_custody': 'Delegated to pinned original native proof.'})
    return memories, captures


def compare_window(window, native, generations):
    name, stem, first, end, reason = window
    target = native[stem][first:end]
    states, matching = [], []
    for source in generations:
        memory, known, written, delta = (source[key] for key in ('memory', 'known', 'written', 'delta'))
        unknown = [i for i in range(first, end) if not known[i]]
        not_payload = [i for i in range(first, end) if not written[i]]
        differences = [(i, memory[i], native[stem][i]) for i in range(first, end)
                       if known[i] and memory[i] != native[stem][i]]
        full_equal = not unknown and not not_payload and not differences
        if full_equal:
            matching.append(source['bundle'])
        states.append({'bundle': source['bundle'], 'known_bytes': end - first - len(unknown),
            'payload_written_bytes': end - first - len(not_payload),
            'fresh_delta_written_bytes': sum(delta[first:end]),
            'unknown_ranges_half_open': intervals(unknown),
            'not_payload_written_ranges_half_open': intervals(not_payload),
            'known_byte_difference_count': len(differences),
            'all_known_differences_canonical_SHA256': sha(json.dumps(differences, separators=(',', ':')).encode()),
            'first16_known_differences_address_source_native': differences[:16],
            'full_known_payload_written_and_byte_equal': full_equal,
            'source_window_SHA256': sha(memory[first:end]) if not unknown else None})
    return {'name': name, 'capture': stem, 'first': first, 'end_exclusive': end,
        'bytes': len(target), 'range_contract': reason, 'native_window_SHA256': sha(target),
        'matching_complete_source_bundles': matching,
        'first_matching_complete_source_bundle': matching[0] if matching else None,
        'states': states,
        'association_scope': 'Exact complete selected byte window, not an inferred call, slot, filename, effect identity or resource extent.'}


def write_json(path, obj):
    path.write_text(json.dumps(obj, indent=2) + '\n')


def output_ref(path):
    return {'name': path.name, 'bytes': path.stat().st_size, 'sha256': sha(path.read_bytes())}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = (ROOT / args.output).resolve()
    out.relative_to(BASE.resolve())
    assert not out.exists(), 'fresh output directory required'
    # This call must precede every read of any native capture in this producer.
    source, source_meta, strict, validation = source_generations()
    color, color_meta, generations, color_validation, color_refs = color_generations(strict)
    native_proof, native_meta = pinned_json(NATIVE, NATIVE_SHA)
    parts, parts_meta = pinned_json(PARTS, PARTS_SHA)
    kefrens, kefrens_meta = pinned_json(KEFRENS, KEFRENS_SHA)
    binding, binding_meta = pinned_json(BINDING, BINDING_SHA)
    assert native_proof['pass_'] is True and parts['pass_'] is True and binding['pass_'] is True
    assert kefrens['pass_'] is True
    assert (kefrens['source_code_first'], kefrens['source_code_end_exclusive']) == (0x4800, 0x5376)
    assert parts['part06_relocation']['source'] == [0x6000, 0x7ffe]
    assert parts['part08_generated_calls']['template'] == [0xf817, 0xf830]
    memories, captures = native_captures(native_proof)
    strict_comparisons = [compare_window(window, memories, strict) for window in WINDOWS]
    comparisons = [compare_window(window, memories, generations) for window in WINDOWS]
    by_name = {item['name']: item for item in comparisons}
    strict_by_name = {item['name']: item for item in strict_comparisons}
    # Fixed finite positive and negative findings; no result-based byte selection.
    assert strict_by_name['part01-wrapper']['matching_complete_source_bundles'] == [20]
    assert strict_by_name['part01-code-window']['matching_complete_source_bundles'] == [20, 21]
    assert strict_by_name['part01-glyph-input']['matching_complete_source_bundles'] == [19, 20, 21]
    assert strict_by_name['part02-wrapper']['matching_complete_source_bundles'] == [21]
    assert strict_by_name['part02-6600-window']['matching_complete_source_bundles'] == [21]
    assert strict_by_name['part03-6600-window']['matching_complete_source_bundles'] == [21]
    assert memories['part02-entry'][0x6600:0x6800] == memories['part03-entry'][0x6600:0x6800]
    assert all(not strict_by_name[name]['matching_complete_source_bundles'] for name in (
        'part06-Kefrens-source', 'part06-relocation-input', 'part07-8000-window',
        'part07-text-generator-window', 'part08-F000-window'))
    expected = {
        'part01-wrapper': [20], 'part01-code-window': list(range(20, 26)),
        'part01-glyph-input': list(range(19, 28)), 'part02-wrapper': [21, 22, 23],
        'part02-6600-window': list(range(21, 28)), 'part03-6600-window': list(range(21, 28)),
        'part04-E000-window': list(range(23, 29)), 'part05-wrapper-window': [24],
        'part05-E000-window': list(range(23, 29)), 'part06-wrapper-window': [25, 26, 27, 28],
        'part06-Kefrens-source': [25, 26, 27, 28], 'part06-relocation-input': [28],
        'part07-wrapper': [29, 30], 'part07-8000-window': list(range(29, 38)),
        'part07-text-generator-window': [29, 30, 31, 32], 'part07-text-inputs': list(range(29, 34)),
        'part07-glyph-values': list(range(29, 35)), 'part07-glyph-indices': list(range(29, 35)),
        'part07-background-input': list(range(29, 34)), 'part08-wrapper': [31, 32],
        'part08-F000-window': [31, 32], 'part08-call-template': [30, 31, 32],
        'part09-wrapper-only': [33, 34, 35],
    }
    assert set(expected) == set(by_name)
    for name, numbers in expected.items():
        assert by_name[name]['matching_complete_source_bundles'] == numbers, name
    groups = []
    for names in (['part01-wrapper', 'part01-code-window', 'part01-glyph-input'],
                  ['part02-wrapper', 'part02-6600-window'],
                  ['part05-wrapper-window', 'part05-E000-window'],
                  ['part06-wrapper-window', 'part06-Kefrens-source'],
                  ['part07-wrapper', 'part07-8000-window', 'part07-text-generator-window',
                   'part07-text-inputs', 'part07-glyph-values', 'part07-glyph-indices', 'part07-background-input'],
                  ['part08-wrapper', 'part08-F000-window', 'part08-call-template']):
        common = set(range(len(generations)))
        for name in names:
            common &= set(by_name[name]['matching_complete_source_bundles'])
        groups.append({'windows': names, 'complete_source_states_matching_every_window': sorted(common),
            'limits': 'Source-byte association only. No wrapper counter arithmetic, inferred actual indexed request, or replay of intervening application/IRQ mutation.'})
    out.mkdir(parents=True)
    checked = out / 'effect_binding.checked.py'
    checked.write_bytes(Path(__file__).read_bytes())
    source_path = out / 'source-generation-validation.json'
    write_json(source_path, {'pass_': True, 'strict_source_receipt': source_meta,
        'all96_source_outputs_byte_hash_verified_before_native_RAM_reads': True,
        'only_complete_generations_in_comparisons': True, 'completed_bundles': validation,
        'color_extension_receipt': color_meta,
        'all_color_extension_outputs_byte_hash_verified_before_native_RAM_reads': True,
        'full_RAM_first22_color_generations_equal_strict_source': True,
        'color_extension_completed_bundles': color_validation,
        'partial_stop_excluded': source['stop'], 'observed_source_IO_write_records': [
            {'address': 0xdbe8, 'value': 0x0c}, {'address': 0xdbe7, 'value': 0x0f}],
        'source_partial_device_read_model_delegated_to_pinned_extension': True,
        'no_ColorRAM_device_state_used_as_physical_RAM_or_native_oracle': True,
        'color_extension_partial_stop_excluded': color['stop']})
    comparisons_path = out / 'generation-comparisons.json'
    write_json(comparisons_path, {'pass_': True, 'captures': captures,
        'every_declared_window_compared_against_all43_complete_states': True,
        'no_native_values_or_masks_supplied_to_source_prediction': True,
        'runtime_patch_normalization': 'None. All bytes in each contiguous window compared.',
        'strict_windows': strict_comparisons, 'windows': comparisons, 'joint_window_associations': groups,
        'part02_to_part03_6600_512_bytes_unchanged': True})
    files = [checked, source_path, comparisons_path]
    proof = {'pass_': True,
        'scope': 'Late independent exact selected-source-window associations for complete source-only generations0..42 with a separately pinned low-nibble device extension. Strict I/O boundary and later packet exhaustion retained. No whole-effect decode or CPU execution.',
        'producer': metadata(Path(__file__).resolve()),
        'inputs': [source_meta, color_meta, native_meta, parts_meta, kefrens_meta, binding_meta, metadata(ROOT / READER)],
        'source_before_oracle': {'all_source_outputs_verified_before_opening_native_RAM': True,
            'initial_RAM_unknown': True, 'source_model_native_inputs': False,
            'complete_generation_count': len(generations),
            'strict_source_outputs': source['outputs'], 'color_extension_outputs': color_refs,
            'source_dependencies': [source[key] for key in ('producer', 'frozen_model', 'original_transport_receipt', 'packet_plan')]},
        'native_selected_captures': captures,
        'joint_window_associations': groups,
        'matched_window_names': [item['name'] for item in comparisons if item['matching_complete_source_bundles']],
        'unmatched_window_names': [item['name'] for item in comparisons if not item['matching_complete_source_bundles']],
        'unsupported_boundary': {'partial_bundle': 22, 'stop': source['stop'],
            'two_prior_literal_IO_writes': [[0xdbe8, 0x0c], [0xdbe7, 0x0f]],
            'no_partial_bundle_used_as_completed_generation': True,
            'no_native_device_value_or_RAM_under_IO_seed': True},
        'later_source_associations': [{'name': item['name'], 'capture': item['capture'],
            'first': item['first'], 'end_exclusive': item['end_exclusive'], 'bytes': item['bytes'],
            'first_matching_complete_source_bundle': item['first_matching_complete_source_bundle'],
            'all_matching_complete_source_bundles': item['matching_complete_source_bundles'],
            'fresh_written_bytes_at_first_match': item['states'][item['first_matching_complete_source_bundle']]['fresh_delta_written_bytes']}
            for item in comparisons],
        'extended_boundary': {'partial_bundle': color['partial_bundle'],
            'stop': color['stop'], 'partial_RAM_writes_excluded': color['partial_RAM_writes_since_last_complete'],
            'no_full_side_or_resource_count_claim': True},
        'limits': [
            'Per-bundle software snapshots preserve earlier generations. Final or partial end-of-stream RAM is never substituted for an earlier completed state.',
            'Full known-mask and payload-written coverage, then equality of every declared byte, are required. Unknown values, matching subsets and output-derived patch masks cannot count as success.',
            'Fresh per-bundle delta writes and cumulative writes are reported separately. Surviving identical bytes do not identify a new load request.',
            'Selected contiguous source windows are not recovered original resource extents, full reachability graphs or entire loaded programs.',
            'The format simulation does not model intervening native application/IRQ execution or all possible physical packet arrival orders. Equality here is finite byte association, not an all-memory mutation theorem.',
            '088D is application bookkeeping, not a slot or bundle index. The prior binding separately establishes retained drive selection; no arithmetic mapping is made here.',
            'Strict states0..21 do not match the declared later Kefrens/airline/ribbon windows. Later full-byte RAM comparisons use only separately pinned ColorRAM-extension completed states, with full unknown-high-bit rules delegated to that proof.',
            'The named three-layer scene remains unbound; no new pixel, bus timing, full animation, FPS or optimization claim.',
            'Native wire/boot/checkpoint/process custody is delegated to the pinned closed native proof. This producer independently rechecks selected full RAM/VSF/CPU identity.',
        ], 'outputs': [output_ref(path) for path in files]}
    receipt = out / 'effect-binding-proof.json'
    write_json(receipt, proof)
    print(json.dumps({'pass_': True, 'receipt': metadata(receipt),
        'matched_windows': len(proof['matched_window_names']),
        'unmatched_windows': len(proof['unmatched_window_names'])}))


if __name__ == '__main__':
    main()
