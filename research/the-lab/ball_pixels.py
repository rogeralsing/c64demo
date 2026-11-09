#!/usr/bin/env python3
"""Scalar marker, bitmap and committed-color join for the fresh Lab ball capture.

This performs integer data transformations only. It executes no original
CPU instructions, emulator, subprocess or renderer binary.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import traceback

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/lab-polygons-20261109'
SOURCE = ROOT / 'build/research/the-lab/side2-analysis/depacked/22.ram.bin'
SOURCE_SHA = 'e95132427dc660f13e611bcb886636374d4f86e533b22a3dd286dc59896b5229'
FILL_PROOF = BASE/'display-source-analysis/fill-coverage-01/fill-coverage-proof.json'
FILL_PROOF_SHA = '77f08f657a2e9dc232fd2347f242b1e3136168e21895bda5916156429a6a0d78'
IMAGE20 = ROOT/'build/research/the-lab/side2-analysis/depacked/20.ram.bin'
IMAGE20_SHA = 'f866f5a03713f91979dc4ad8421f95b4a9da6b405faea55804112e9993e90ef8'
NATIVE_PROOF = BASE/'native-analysis/accepted-01/ball-native-proof.json'
NATIVE_SHA = '123732a8293916ffc9648b51686eeff314f1d0a9b371756efaab975976d968e5'
ATTRIBUTE_PROOF = BASE/'attribute-analysis/accepted-01/ball-attribute-proof.json'
ATTRIBUTE_SHA = 'f0f4fa7941b24e9d9a3d4fbea1d39cf7e59bc387f87f4fb3a49fe17791cacbb6'
PUBLICATION_PROOF = BASE/'publication-analysis/accepted-01/publication-proof.json'
PUBLICATION_SHA = '5eedbbdaf09863861c34edface3d2be117d5205603806c2e902b37aaa10f9238'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def pinned_proof(path, digest):
    assert sha(path.read_bytes()) == digest
    proof = json.loads(path.read_text())
    assert proof['pass_']
    for record in proof['outputs']:
        raw = (path.parent/record['name']).read_bytes()
        assert len(raw) == record['bytes'] and sha(raw) == record['sha256']
    return proof


def checked_record(record):
    path = ROOT/record['path']
    assert meta(path) == record
    return path.read_bytes()


def fill_contract():
    proof = pinned_proof(FILL_PROOF, FILL_PROOF_SHA)
    path = FILL_PROOF.parent/'fill_coverage_source.checked.py'
    spec = importlib.util.spec_from_file_location('lab_ball_frozen_fill', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    source = IMAGE20.read_bytes()
    assert sha(source) == IMAGE20_SHA
    return module, module.tables(source)


def decode_multicolor(bitmap, screen, color_ram, background):
    """Decode an ordinary 320x200 multicolor bitmap into physical color indices."""
    assert len(bitmap) == 8000 and len(screen) == 1000 and len(color_ram) == 1024
    assert 0 <= background < 16
    result = bytearray(64000)
    for y in range(200):
        tile_row, line = divmod(y, 8)
        for column in range(40):
            cell = tile_row*40+column
            colors = (background, screen[cell] >> 4, screen[cell] & 15, color_ram[cell] & 15)
            byte = bitmap[tile_row*320+column*8+line]
            for lane in range(4):
                color = colors[(byte >> (6-2*lane)) & 3]
                offset = y*320+column*8+lane*2
                result[offset:offset+2] = bytes((color, color))
    return result


def normal_viewport(body, border):
    """Conditional MOS8565 PAL normal-border geometry: raster rows16..287."""
    assert len(body) == 64000 and 0 <= border < 16
    result = bytearray([border])*(384*272)
    for row in range(200):
        first = (row+51-16)*384+32
        result[first:first+320] = body[row*320:row*320+320]
    return result


def predict(entry):
    """Predict markers, source bounds and pending bitmap from declared entry RAM."""
    assert len(entry) == 65536
    assert not any(entry[0xc800:0xda00]), 'This bounded input requires observed-zero markers.'
    offset_x, offset_y = entry[0x51], entry[0x52]
    source = SOURCE.read_bytes()
    assert sha(source) == SOURCE_SHA
    pointer = int.from_bytes(entry[0x3e:0x40], 'little')
    assert 0x9026 <= pointer < 0xc34c
    records, cursor = [], pointer
    while source[cursor] != 255:
        assert cursor+6 <= 0xc34c
        records.append(source[cursor:cursor+6])
        cursor += 6
    assert records
    markers, samples = bytearray(4608), 0
    minimum_x, maximum_x, minimum_y = 96, 0, 192
    for x0, x1, lo, hi, y0, attribute in records:
        assert 0 <= (x0 & 127) < (x1 & 127) < 96 and y0 < 192
        left = (entry[0x8b34+(x0 & 127)]+offset_x) & 255
        right = (entry[0x8b34+(x1 & 127)]+offset_x) & 255
        row = (entry[0x8a74+y0]+offset_y) & 255
        assert 0 <= left <= right <= 96 and row < 192
        if left == right:
            continue
        minimum_x, maximum_x = min(minimum_x, left), max(maximum_x, right)
        minimum_y = min(minimum_y, row)
        fraction, carry = 0, 0
        code = 2*(x0 >> 7)+(x1 >> 7)
        for x in range(left, right):
            assert 0 <= row < 192
            markers[(x//4)*192+row] ^= code << (6-2*(x % 4))
            samples += 1
            total = fraction+lo+carry
            fraction, carry = total & 255, total >> 8
            total = row+hi+carry
            row, carry = total & 255, total >> 8
        minimum_y = min(minimum_y, row)
    assert samples > 0 and minimum_x < maximum_x, 'Collapsed frames are outside this model.'
    fill, descriptors = fill_contract()
    bounds = fill.bounds_from_extrema(minimum_x, maximum_x, minimum_y)
    first_column = bounds['column_first']
    end_column = bounds['column_end_exclusive']
    first_char = bounds['global_top_character_row']
    assert entry[0x43] in (0, 1)
    bank = 0x4000 if entry[0x43] == 0 else 0xe000
    bitmap = bytearray(entry[bank:bank+8000])
    writes, columns = [], []
    spans = fill.coverage(descriptors, first_column, end_column, first_char, bank)
    for span in spans:
        column = span['byte_column']
        first_y = span['first_pixel_row']
        end_y = span['end_pixel_row_exclusive']
        assert 0 <= first_y <= end_y <= 192
        assert not any(markers[column*192:column*192+first_y])
        accumulator = 0
        for row, address in zip(range(first_y, end_y), span['addresses']):
            accumulator ^= markers[column*192+row]
            offset = address-bank
            bitmap[offset] = accumulator
            writes.append(dict(address=address, value=accumulator))
        columns.append(dict(column=column, first_y=first_y, end_y=end_y))
    return dict(markers=markers, bitmap=bitmap, bank=bank, records=len(records),
                samples=samples, frame_pointer=pointer, minimum_y=minimum_y,
                translation_bytes=[offset_x, offset_y],
                bounds=[first_column, end_column, first_char], columns=columns, writes=writes)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to(BASE/'pixel-analysis')
    out.mkdir(parents=True, exist_ok=False)
    checked = Path(__file__).read_bytes()
    (out/'ball_pixels.checked.py').write_bytes(checked)
    try:
        native = pinned_proof(NATIVE_PROOF, NATIVE_SHA)
        attributes = pinned_proof(ATTRIBUTE_PROOF, ATTRIBUTE_SHA)
        publication = pinned_proof(PUBLICATION_PROOF, PUBLICATION_SHA)
        pinned_proof(FILL_PROOF, FILL_PROOF_SHA)
        captures = {r['stem']: r for r in native['captures']}
        context = json.loads((NATIVE_PROOF.parent/'capture-machine-context.json').read_text())
        names = ['ball52-edge-entry', 'ball52-events-ready', 'ball52-render-done',
                 'ball52-bank-selected', 'ball52-color-copied', 'ball52-wrap-a', 'ball52-wrap-b']
        memories = {}
        for name in names:
            assert captures[name]['accepted_natural_phase'] and name not in native['rejected_capture_stems']
            memories[name] = checked_record(captures[name]['ram'])
            checked_record(captures[name]['snapshot'])
        entry = memories['ball52-edge-entry']
        mode = context['captures']['ball52-edge-entry']['summary']['VIC']
        assert entry[0x43] == 0
        assert [mode[k] for k in ('D011', 'D016', 'D015_sprite_enable', 'D020', 'D021')] == [0x3b, 0xd8, 0, 0, 0]
        assert any(q['expected_value'] == 'VICIIBorderMode=0' and q['sequence'] < captures[names[0]]['stop_sequence']
                   for q in context['actual_resource_queries'])
        assert context['captures'][names[0]]['frozen_core_and_extended_state']['vicii']['model'] == 1
        # Only genuine entry RAM and original source/crop contracts reach predict.
        prediction = predict(entry)
        bank = prediction['bank']
        assert prediction['markers'] == memories['ball52-events-ready'][0xc800:0xda00]
        assert prediction['markers'] == memories['ball52-render-done'][0xc800:0xda00]
        assert prediction['bounds'] == list(memories['ball52-events-ready'][0x53:0x56])
        assert prediction['bitmap'] == memories['ball52-render-done'][bank:bank+8000]
        screen_path = ATTRIBUTE_PROOF.parent/'predicted-back-screen-6000.bin'
        color_path = PUBLICATION_PROOF.parent/'predicted-color-ram-1024.bin'
        screen, colors = screen_path.read_bytes(), color_path.read_bytes()
        assert len(screen) == 1000 and len(colors) == 1024 and all(c < 16 for c in colors)
        # Screen and device colors come from the independent source predictors,
        # never the ending native screen/ColorRAM or retained framebuffer.
        body = decode_multicolor(prediction['bitmap'], screen, colors, mode['D021'])
        viewport = normal_viewport(body, mode['D020'])
        traces = json.loads((NATIVE_PROOF.parent/'trace-hits.json').read_text())
        low = captures['ball52-edge-entry']['registers']['clock']
        high = captures['ball52-wrap-b']['registers']['clock']
        bank_clock = captures['ball52-bank-selected']['registers']['clock']
        source_mode_stores, late_bank_stores = [], []
        for hit in traces:
            regs, address = hit['registers'], hit['monitored_address']
            if not low <= regs['clock'] <= high:
                continue
            assert regs['port00'] & 7 == 7
            if regs['port01'] & 7 != 5:
                continue  # Renderer RAM under D000 is not VIC I/O.
            if 0xd000 <= address < 0xd400 and address & 63 in (0x11, 0x15, 0x16, 0x20, 0x21):
                source_mode_stores.append(hit)
            if regs['clock'] > bank_clock and (0xdd00 <= address <= 0xdd03 or
                    0xd000 <= address < 0xd400 and address & 63 == 0x18):
                late_bank_stores.append(hit)
        assert not source_mode_stores and not late_bank_stores
        copy_clock = captures['ball52-color-copied']['registers']['clock']
        comparisons = []
        for name in ('ball52-wrap-a', 'ball52-wrap-b'):
            state = context['captures'][name]
            summary, full = state['summary'], state['frozen_core_and_extended_state']
            assert summary['VIC']['derived_bitmap'] == bank and summary['VIC']['derived_screen'] == 0x6000
            assert summary['VIC']['D015_sprite_enable'] == 0
            assert prediction['bitmap'] == memories[name][bank:bank+8000]
            assert screen == memories[name][0x6000:0x63e8]
            assert colors == bytes(full['vicii']['color_ram'])
            phase = captures[name]['registers']
            assert phase['line'] == full['raster_hardware_extension']['raster_store']['current_line'] == 0
            field_start = phase['clock']-phase['cycle']-312*63
            assert bank_clock < field_start and copy_clock < field_start+51*63
            native_view = NATIVE_PROOF.parent/(name+'-retained-viewport-384x272.bin')
            actual = native_view.read_bytes()
            assert len(actual) == len(viewport) == 104448
            assert viewport == actual
            comparisons.append(dict(stem=name, snapshot=captures[name]['snapshot'],
                native_pixel_oracle=meta(native_view), all104448_palette_indices_equal=True,
                field_start_clock=field_start, bank_selected_before_field=True,
                colors_ready_before_graphics_clock=field_start+51*63,
                copy_completion_clock=copy_clock, color_margin_cycles=field_start+51*63-copy_clock,
                actual_boundary_line=phase['line'], actual_boundary_cycle=phase['cycle']))
        data = {'predicted-markers.bin': prediction['markers'],
                'predicted-bitmap.bin': prediction['bitmap'], 'predicted-screen.bin': screen,
                'predicted-color-ram.bin': colors, 'predicted-body-320x200.bin': body,
                'predicted-viewport-384x272.bin': viewport}
        for name, raw in data.items():
            (out/name).write_bytes(raw)
        (out/'logical-bitmap-writes.json').write_text(json.dumps(prediction['writes'], indent=2)+'\n')
        outputs = [dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
                   for p in sorted(out.iterdir()) if p.is_file()]
        body_entry_clock = captures['ball52-body-entry']['registers']['clock']
        complete_clock = captures['ball52-render-done']['registers']['clock']
        proof = dict(pass_=True, producer=meta(Path(__file__)),
            scope='Independent scalar marker/dirty-bitmap prediction joined with independent screen and device-color predictions; two complete committed normal PAL viewports compared.',
            inputs=[meta(p) for p in (NATIVE_PROOF, ATTRIBUTE_PROOF, PUBLICATION_PROOF, FILL_PROOF,
                                     SOURCE, IMAGE20, screen_path, color_path)],
            declared_entry_capture=captures['ball52-edge-entry'],
            original_frame=dict(pointer=prediction['frame_pointer'], records=prediction['records'],
                samples=prediction['samples'], translation_bytes=prediction['translation_bytes'],
                palette=list(entry[0x9016:0x9026])),
            bitmap_prediction=dict(bounds=prediction['bounds'], minimum_source_y=prediction['minimum_y'],
                spans=prediction['columns'], logical_store_count=len(prediction['writes']),
                all4608_marker_bytes_equal=True, all8000_pending_bitmap_bytes_equal=True,
                outside_source_dirty_spans_preserved_from_entry=True,
                current_native_bitmap_store_trace_claimed=False),
            joined_independent_predictions=dict(attribute_receipt=meta(ATTRIBUTE_PROOF),
                publication_receipt=meta(PUBLICATION_PROOF), no_native_ending_attributes_as_inputs=True),
            geometry=dict(body=[320, 200], viewport=[384, 272], raster_rows=[16, 287],
                body_origin_in_unpadded_framebuffer=[32, 51], normal_border_resource=0,
                model=1, expanded_multicolor_physical_pixels_per_code=2,
                no_postselection_D018_or_CIA2_bank_control_stores=True),
            committed_viewport_comparisons=comparisons,
            observed_boundary_timing=dict(full_body_cycles=complete_clock-body_entry_clock,
                edge_entry_to_events_ready_cycles=captures['ball52-events-ready']['registers']['clock']-low,
                events_ready_to_render_done_cycles=complete_clock-captures['ball52-events-ready']['registers']['clock'],
                queued_to_bank_selected_cycles=bank_clock-captures['ball52-request-queued']['registers']['clock'],
                bank_selected_to_color_return_cycles=copy_clock-bank_clock,
                timing_is_observed_not_a_CPU_schedule_prediction=True, IRQ_and_VIC_work_included=True),
            outputs=outputs,
            limits=['One prepared frame52 at actual translated partial-palette entry state; no arbitrary-pose, clipping or collapsed-edge theorem.',
                'Scale/translation tables, previous background, initial event buffers, actual mode and initial device colors remain declared inputs.',
                'This proves the compared emulator palette-index viewports, not physical analog RGB or every intermediate CPU/VIC/bus state.',
                'Store addresses are scalar normal-filler predictions. Current watch ranges do not provide a complete actual bitmap/screen store trace.',
                'Later palette-table/shadow changes belong to the next pending render. They do not seed the displayed generation.',
                'No whole-animation/FPS, optimization, live3D, physical hardware or downloaded-host execution claim.'])
        (out/'ball-pixels-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
        print(json.dumps(dict(pass_=True, source_bitmap_stores=len(prediction['writes']),
            committed_viewports=len(comparisons), indices_per_viewport=len(viewport),
            receipt_bytes=(out/'ball-pixels-proof.json').stat().st_size,
            receipt_sha256=sha((out/'ball-pixels-proof.json').read_bytes()))))
    except Exception as error:
        (out/'failure.json').write_text(json.dumps(dict(pass_=False, error=str(error),
            traceback=traceback.format_exc(), producer=meta(Path(__file__))), indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
