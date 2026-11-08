#!/usr/bin/env python3
"""Exhaust captured face-group omissions with the frozen scalar reference.

Offline only: no SDK, CPU, VICE, build, process or product action. Output
records use local filenames, so proof bytes are independent of --output.
"""

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import struct
import sys
import zlib

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUTPUT_ROOT = ROOT / 'build/research/3dvibe64-overdraw/omission-analysis'
PROFILE_PROOF = 'build/research/3dvibe64-profile/pixel-analysis/profile-pixels-proof.json'
PINS = {
    'research/3dvibe64-native/pixels.py': '859e1ece975ea57c283cf0c4dcef47be95cf91c72d8d9eba29cd4765da8e16a2',
    'research/3dvibe64-profile/check_pixels.py': 'c6c4d9e4d72b2c31f2a29a69f60f127555c5ab4a5c4aa9b70f8f75f81bbb3f94',
    PROFILE_PROOF: 'a564dc770db6b02afc66607b259cd71971b9ef2810200c642fd5c4cae1cb2710',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'palettes/colodore.vpl': 'cfc740890e811b94a73bbbe9f38c400f6714d37c6b6167935adf4f892422b972',
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


def output_file(directory, name, data):
    assert Path(name).name == name
    (directory / name).write_bytes(data)
    return dict(file=name, bytes=len(data), sha256=sha(data))


def output_json(directory, name, value):
    return output_file(directory, name, (json.dumps(value, indent=2) + '\n').encode())


def display_indices(model, background):
    """Decode both physical bitmap rows, without assuming row duplication."""
    result = bytearray()
    for y in range(200):
        for x in range(160):
            offset = (y // 8) * 320 + (x // 4) * 8 + y % 8
            code = (model['bitmap'][offset] >> (6 - 2 * (x & 3))) & 3
            cell = (y // 8) * 40 + x // 4
            attr = model['attributes'][cell]
            color = (background, attr >> 4, attr & 15, model['color_ram'][cell] & 15)[code]
            result.extend((color, color))
    assert len(result) == 64000
    return bytes(result)


def png_indices(pixels):
    palette = [bytes(int(v, 16) for v in line.split()[:3])
               for line in (ROOT / 'palettes/colodore.vpl').read_text().splitlines()
               if len(line.split()) >= 3 and not line.strip().startswith('#')]
    assert len(palette) == 16
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    rows = b''.join(b'\0' + pixels[y * 320:(y + 1) * 320] for y in range(200))
    return (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 320, 200, 8, 3, 0, 0, 0)) +
            chunk(b'PLTE', b''.join(palette)) + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b''))


def differing(a, b):
    assert len(a) == len(b)
    return [i for i, (x, y) in enumerate(zip(a, b)) if x != y]


def bounds(indices, width):
    return None if not indices else dict(x0=min(i % width for i in indices), y0=min(i // width for i in indices),
                                       x1=max(i % width for i in indices), y1=max(i // width for i in indices))


def group_spans(frame, spans):
    groups = []
    for index, span in enumerate(spans):
        assert span['index'] == index and 0 <= span['observed_face_id_latch'] < 8
        face = span['observed_face_id_latch']
        if not groups or groups[-1]['face_id'] != face:
            groups.append(dict(group_index=len(groups), frame=frame, face_id=face,
                first_span_index=index, first_span_clock=span['clock'], spans=[]))
        groups[-1]['spans'].append(span)
    assert len({g['face_id'] for g in groups}) == len(groups)
    return groups


def public_group(group):
    return dict(group_index=group['group_index'], frame=group['frame'], face_id=group['face_id'],
        first_span_index=group['first_span_index'], last_span_index=group['spans'][-1]['index'],
        first_span_clock=group['first_span_clock'], span_count=len(group['spans']),
        pixel_writes=sum(s['extent'] + 1 for s in group['spans']))


def load_capture(reader, entry):
    ram = checked(entry['ram'])
    checked(entry['snapshot'])
    path = ROOT / entry['snapshot']['path']
    assert reader.module_payload(path, 'C64MEM')[4:65540] == ram
    return dict(ram=ram, state=reader.read_snapshot(path))


def compare_model(model, full, image, full_image, background):
    bitmap = differing(model['bitmap'], full['bitmap'])
    screen = differing(model['attributes'], full['attributes'])
    colors = differing(model['color_ram'], full['color_ram'])
    pixels = differing(image, full_image)
    # Separate the effect of palette changes from missing bitmap pixels.
    fixed_attrs = dict(model, attributes=full['attributes'], color_ram=full['color_ram'])
    fixed_image = display_indices(fixed_attrs, background)
    attr_effect = differing(image, fixed_image)
    changed_cells = sorted(set(screen) | set(colors))
    invisible_cells = []
    for cell in changed_cells:
        if cell >= 1000:
            invisible_cells.append(cell)
            continue
        x0, y0 = (cell % 40) * 8, (cell // 40) * 8
        if all(image[y * 320 + x] == fixed_image[y * 320 + x]
               for y in range(y0, y0 + 8) for x in range(x0, x0 + 8)):
            invisible_cells.append(cell)
    return dict(bitmap_different_bytes=len(bitmap), screen_different_bytes=len(screen),
        physical_color_RAM_different_bytes=len(colors), decoded_display_different_pixels=len(pixels),
        decoded_display_difference_bounds=bounds(pixels, 320),
        all_memory_equal=not (bitmap or screen or colors), decoded_display_equal=not pixels,
        display_equal_but_memory_different=not pixels and bool(bitmap or screen or colors),
        attribute_effect_on_this_retained_bitmap_pixels=len(attr_effect),
        changed_attribute_cells=changed_cells, invisible_changed_attribute_cells=invisible_cells,
        bitmap_sha256=sha(model['bitmap']), screen_sha256=sha(model['attributes']),
        physical_color_RAM_sha256=sha(model['color_ram']), decoded_display_sha256=sha(image))


def short_result(row):
    fields = ('mask', 'retained_group_indices', 'retained_face_ids', 'omitted_face_ids', 'retained_span_count',
              'bitmap_different_bytes', 'screen_different_bytes', 'physical_color_RAM_different_bytes',
              'decoded_display_different_pixels', 'all_memory_equal', 'decoded_display_equal')
    return {key: row[key] for key in fields}


def inspect_frame(directory, reference, reader, accepted):
    name = accepted['name']
    before, complete = load_capture(reader, accepted['baseline']), load_capture(reader, accepted['completed'])
    spans = json.loads(checked(accepted['spans']))
    groups = group_spans(name, spans)
    assert len(groups) == (5 if name == 'third' else 4)
    full = reference.scalar(before, spans)
    assert full['bitmap'] == complete['ram'][full['base']:full['base'] + 8000]
    assert full['attributes'] == complete['ram'][full['screen']:full['screen'] + 1024]
    assert full['color_ram'] == bytearray(complete['state']['vicii']['color_ram'])
    background = complete['state']['vicii']['regs'][0x21] & 15
    full_image = display_indices(full, background)
    assert full_image == reference.expand(reference.logical_colors(full, background))
    outputs = [output_file(directory, name + '-full-bitmap.bin', full['bitmap']),
               output_file(directory, name + '-full-screen.bin', full['attributes']),
               output_file(directory, name + '-full-color-RAM.bin', full['color_ram']),
               output_file(directory, name + '-full-display-indices.bin', full_image),
               output_file(directory, name + '-full.png', png_indices(full_image))]
    rows, models = [], {}
    for mask in range(1 << len(groups)):
        retained = [group for i, group in enumerate(groups) if mask & (1 << i)]
        selected = [span for group in retained for span in group['spans']]
        # Groups and spans keep their original order, never face-ID sort order.
        assert [s['index'] for s in selected] == sorted(s['index'] for s in selected)
        model = reference.scalar(before, selected)
        image = display_indices(model, background)
        row = dict(frame=name, mask=mask, retained_group_count=len(retained),
            retained_group_indices=[g['group_index'] for g in retained],
            retained_face_ids=[g['face_id'] for g in retained],
            omitted_face_ids=[g['face_id'] for i, g in enumerate(groups) if not mask & (1 << i)],
            retained_span_count=len(selected), retained_pixel_writes=sum(s['extent'] + 1 for s in selected),
            **compare_model(model, full, image, full_image, background))
        rows.append(row)
        models[mask] = (model, image)
    full_mask = (1 << len(groups)) - 1
    assert rows[full_mask]['all_memory_equal'] and rows[full_mask]['decoded_display_equal']
    assert rows[0]['decoded_display_different_pixels'] > 0
    visible = [row for row in rows if row['decoded_display_equal']]
    memory = [row for row in rows if row['all_memory_equal']]
    minimum_visible = min(row['retained_group_count'] for row in visible)
    minimum_memory = min(row['retained_group_count'] for row in memory)
    visible_minima = [row for row in visible if row['retained_group_count'] == minimum_visible]
    memory_minima = [row for row in memory if row['retained_group_count'] == minimum_memory]
    single = [rows[full_mask ^ (1 << i)] for i in range(len(groups))]
    for index, row in enumerate(visible_minima, 1):
        outputs.append(output_file(directory, name + f'-minimum-display-{index}.png', png_indices(models[row['mask']][1])))
    detail = output_json(directory, name + '-all-subsets.json', rows)
    outputs.append(detail)
    used_inputs = [accepted['spans'], accepted['baseline']['ram'], accepted['baseline']['snapshot'],
                   accepted['completed']['ram'], accepted['completed']['snapshot']]
    return dict(frame=name, actual_draw_buffer=before['ram'][11], bitmap_base=full['base'],
        captured_baseline_preserved=True, original_span_order_preserved=True,
        groups=[public_group(g) for g in groups], subsets_examined=len(rows),
        full_model_equals_native_completed_bitmap_and_palettes=True,
        single_group_omissions=[short_result(row) for row in single],
        single_removable_face_ids_by_display=[row['omitted_face_ids'][0] for row in single if row['decoded_display_equal']],
        single_removable_face_ids_by_all_memory=[row['omitted_face_ids'][0] for row in single if row['all_memory_equal']],
        minimum_display_preserving_group_count=minimum_visible,
        minimum_display_preserving_subsets=[short_result(row) for row in visible_minima],
        minimum_all_memory_preserving_group_count=minimum_memory,
        minimum_all_memory_preserving_subsets=[short_result(row) for row in memory_minima],
        display_preserving_subsets=len(visible), all_memory_preserving_subsets=len(memory),
        display_preserving_with_memory_differences=sum(row['display_equal_but_memory_different'] for row in rows),
        subsets_with_invisible_changed_attribute_cells=sum(bool(row['invisible_changed_attribute_cells']) for row in rows),
        subset_details=detail, outputs=outputs), used_inputs


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUTPUT_ROOT / 'accepted-01',
                        help='Fresh output directory under the owned omission-analysis root.')
    args = parser.parse_args()
    directory = args.output.expanduser().resolve()
    directory.relative_to(OUTPUT_ROOT.resolve())
    if directory.exists() and any(directory.iterdir()):
        raise SystemExit('Output directory must be fresh or empty; choose a new --output directory.')
    for relative, digest in PINS.items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
    reference = load('frozen_omission_scalar', 'research/3dvibe64-native/pixels.py')
    reader = load('omission_snapshot_reader', 'research/quondam/snapshot_state.py')
    accepted = json.loads((ROOT / PROFILE_PROOF).read_text())
    assert accepted['pass'] and [s['name'] for s in accepted['accepted_samples']] == ['first', 'second', 'third']
    directory.mkdir(parents=True, exist_ok=True)
    frames, used_inputs = [], []
    for sample in accepted['accepted_samples']:
        frame, used = inspect_frame(directory, reference, reader, sample)
        frames.append(frame)
        used_inputs.extend(used)
    assert sum(f['subsets_examined'] for f in frames) == 64
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()),
        pinned_inputs=[artifact(ROOT / p) for p in PINS], accepted_frame_inputs=used_inputs,
        source_capture_receipt=artifact(ROOT / PROFILE_PROOF),
        independent_reference_reuse=dict(path='research/3dvibe64-native/pixels.py',
            unchanged_functions=['scalar'], CPU_or_SDK_code_executed=False,
            own_display_decode='Both physical bitmap rows are decoded separately into 320x200 palette indices.'),
        subset_count=64, frames=frames,
        limitations=['This omits captured span groups offline at fixed poses, retaining actual baselines and original order. No native program or culling policy is changed.',
            'Image-preserving here does not prove a safe general culling rule. A face ID removable in one frame may be required in another.',
            'Full bitmap/Screen/physical Color RAM equality is distinguished from decoded display equality and invisible attribute changes.',
            'No speedup is measured. Existing work-subtree costs from a separate producer are not automatically recoverable savings.',
            'These are decoded completed bitmap images, not new committed VIC raster or physical-hardware observations. Geometry, clipping, edge construction and lighting correctness remain outside the scalar span oracle.'])
    result['pass'] = result.pop('pass_')
    output_file(directory, 'omit_groups.checked.py', Path(__file__).read_bytes())
    receipt = output_json(directory, 'omission-proof.json', result)
    # This console path may vary; no output path or timestamp enters proof bytes.
    print(json.dumps(dict(output=str(directory), receipt=receipt,
        frames=[dict(frame=f['frame'], groups=[g['face_id'] for g in f['groups']],
            single_removable=f['single_removable_face_ids_by_display'],
            minimum=[r['retained_face_ids'] for r in f['minimum_display_preserving_subsets']]) for f in frames]), indent=2))


if __name__ == '__main__':
    main()
