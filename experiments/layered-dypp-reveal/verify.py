#!/usr/bin/env python3
"""Independent layer, live DYPP/reveal, publication and complete VIC proof.

The primary owner boundary is native pixels plus hidden/front font ownership.
An incorrect fine/coarse wrap, waveform phase, selector plane, aperture update,
or early publication changes those observations. Expected pixels use ordinary
source bitmaps and coordinate math, never the producer's windows or LUTs. Normal
render/pass/publication labels are observed without changing native state.
"""
from collections import Counter
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess

from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'build/verification'
TRACE = re.compile(r'^#\d+ \(Trace\s+(exec|store)\s+([0-9a-f]{4})\)\s+'
                   r'(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n'
                   r'\.C:([0-9a-f]+)\s+[^\n]*?- A:([0-9a-f]+) X:([0-9a-f]+) Y:([0-9a-f]+) '
                   r'SP:([0-9a-f]+) [^\n]*?\s+(\d+)\n', re.M | re.I)


def bitmap(raw, height):
    assert len(raw) == 32 * height
    return [[bool(raw[y * 32 + x // 8] & (128 >> (x % 8))) for x in range(256)] for y in range(height)]


def displacement(phase, amplitude, base):
    # A mathematical column wave, independent of the prepared sine byte table.
    return base + math.floor(amplitude * math.sin(phase * math.tau / 256) + 0.5)


def layer_reference(phase, pixels, picture=False):
    height = len(pixels)
    scroll = phase if picture else -2 * phase
    wave = 3 * phase if picture else 5 * phase
    step, amplitude, base, selector = (11, 12, 42, 2) if picture else (13, 18, 34, 1)
    chapter = phase % 64
    width = chapter if chapter < 16 else 16 if chapter < 32 else 48 - chapter if chapter < 48 else 0
    font = bytearray(2048)
    offsets = []
    coordinates = set()
    for column in range(16):
        top = displacement((wave + column * step) % 256, amplitude, base)
        offsets.append(top)
        for row in range(height):
            for lane in range(4):
                source_x = (scroll + column * 4 + lane) % 256
                if pixels[row][source_x] and (not picture or column < width):
                    font[column * 128 + top + row] |= selector << (6 - lane * 2)
                    coordinates.add((column * 4 + lane, top + row))
    return bytes(font), bytes(offsets), coordinates


def screenshot_reference(text_coordinates, picture_coordinates, palette):
    expected = Image.new('RGB', (384, 272), palette[0])
    for x, y in text_coordinates | picture_coordinates:
        selector = int((x, y) in text_coordinates) + 2 * int((x, y) in picture_coordinates)
        color = palette[(0, 14, 3, 1)[selector]]
        expected.putpixel((128 + 2 * x, 67 + y), color)
        expected.putpixel((129 + 2 * x, 67 + y), color)
    return expected


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'proof.json').unlink(missing_ok=True)
    spec = importlib.util.spec_from_file_location('shared_monitor', ROOT / 'verify.py')
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    labels = common.read_labels(HERE / 'build/main.sym')
    text = bitmap((HERE / 'build/text-raw.bin').read_bytes(), 24)
    picture = bitmap((HERE / 'build/picture-raw.bin').read_bytes(), 48)
    source_assets = {}
    for name, rows, base in (('text', text, 0x4000), ('picture', picture, 0x4800)):
        encoded = bytearray()
        for column in range(64):
            for row in rows:
                value = 0
                for bit in range(8):
                    if row[(4 * column + bit) % 256]:
                        value |= 128 >> bit
                encoded.append(value)
        assert (HERE / f'build/{name}-windows.bin').read_bytes() == encoded
        source_assets[base] = bytes(encoded)
    tables = bytes(sum(plane << (6 - lane * 2) for lane in range(4) if value & (128 >> (phase + lane)))
                   for plane in (1, 2) for phase in range(4) for value in range(256))
    assert (HERE / 'build/expand-text.bin').read_bytes() + (HERE / 'build/expand-picture.bin').read_bytes() == tables
    source_assets[0x5800] = tables
    source_assets[0x3000] = bytes((displacement(phase, amplitude, 0) & 255)
                                for amplitude in (18, 12) for phase in range(256))
    assert (HERE / 'build/sines.bin').read_bytes() == source_assets[0x3000]
    references = [(layer_reference(phase, text), layer_reference(phase, picture, True)) for phase in range(256)]
    screen, colors = bytearray(1024), bytearray(1024)
    for column in range(16):
        for row in range(16):
            cell = (row + 4) * 40 + column + 12
            screen[cell] = column * 16 + row
            colors[cell] = 9
    palette_path = ROOT / 'palettes/colodore.vpl'
    palette = [tuple(int(value, 16) for value in line.split()[:3]) for line in
               palette_path.read_text().splitlines() if line.strip() and not line.lstrip().startswith('#')]
    assert len(palette) == 16
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    program = HERE / 'build/example.prg'
    command = common.vice_command(os.environ.get('VICE', 'x64sc'), program, port, palette_path)
    monitor = None
    fonts = [bytes(2048), bytes(2048)]
    states, renders, presentations, publications, images = [], [], [], [], []
    stage_counts = Counter()
    previous_masks = None

    def value(ram, name, size=1):
        return int.from_bytes(ram[labels[name]:labels[name] + size], 'little')

    def check_fonts(ram):
        for buffer in range(2):
            address = 0x2000 + buffer * 2048
            assert ram[address:address + 2048] == fonts[buffer], ('font ownership/composition', stage_counts, buffer)
        assert ram[0x400:0x800] == screen, 'immutable screen mapping'

    def check_state(ram, sequence):
        nonlocal previous_masks
        phase = (sequence - 1) % 256
        chapter = phase % 64
        mode = chapter // 16
        width = chapter if chapter < 16 else 16 if chapter < 32 else 48 - chapter if chapter < 48 else 0
        tick = chapter % 16 if mode in (1, 3) else 0
        assert value(ram, 'poseUsed') == phase
        assert value(ram, 'textScroll') == (-2 * phase) % 256
        assert value(ram, 'pictureScroll') == phase
        assert value(ram, 'textWave') == (5 * phase) % 256
        assert value(ram, 'pictureWave') == (3 * phase) % 256
        assert (value(ram, 'revealMode'), value(ram, 'revealWidth'), value(ram, 'stageTick')) == (mode, width, tick)
        masks = ram[labels['revealMasks']:labels['revealMasks'] + 16]
        assert masks == bytes([255] * width + [0] * (16 - width))
        changed = [] if previous_masks is None else [column for column, pair in enumerate(zip(previous_masks, masks)) if pair[0] != pair[1]]
        if previous_masks is not None:
            previous_chapter = (phase - 1) % 64
            assert len(changed) == int(previous_chapter < 16 or 32 <= previous_chapter < 48)
            if changed:
                assert changed == ([width - 1] if previous_chapter < 16 else [width])
        previous_masks = masks
        return dict(sequence=sequence, phase=phase, mode=mode, width=width, tick=tick, changed_mask_columns=changed)

    with (OUT / 'vice.log').open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            monitor = common.Monitor(common.connect_monitor(process, port))
            monitor.run('r')
            for name in ('stateAdvanced', 'hiddenCleared', 'textLayerComplete', 'renderComplete', 'displayComplete'):
                monitor.run(f'break {labels[name]:04x}')
            monitor.run('trace store d018')
            for stop in range(1300):
                response = monitor.run('x')
                for kind, target, line, cycle, pc, a, x, y, sp, clock in TRACE.findall(response):
                    pc = int(pc, 16)
                    if labels['publishImage'] <= pc < labels['displayComplete']:
                        row = dict(raster=int(line), cycle=int(cycle), clock=int(clock), selection=int(a, 16))
                        assert row['raster'] < 8 and row['selection'] in (0x18, 0x1a)
                        publications.append(row)
                pc, raster, clock = monitor.registers()
                monitor.run('bank ram')
                ram = monitor.memory(OUT / 'latest.ram', 0, 65535)
                phase = value(ram, 'poseUsed')
                text_ref, picture_ref = references[phase]
                text_font, text_offsets, text_coordinates = text_ref
                picture_font, picture_offsets, picture_coordinates = picture_ref
                composite = bytes(a | b for a, b in zip(text_font, picture_font))
                field = value(ram, 'frameCounter', 2)
                if pc == labels['stateAdvanced']:
                    stage_counts['state'] += 1
                    state = check_state(ram, stage_counts['state'])
                    state.update(field=field, begin_clock=clock)
                    states.append(state)
                    check_fonts(ram)
                elif pc == labels['hiddenCleared']:
                    stage_counts['clear'] += 1
                    buffer = (value(ram, 'drawFontHigh') - 0x20) // 8
                    assert buffer == stage_counts['clear'] % 2
                    fonts[buffer] = bytes(2048)
                    check_fonts(ram)
                    states[-1].update(buffer=buffer, cleared_clock=clock, clear_clocks=clock - states[-1]['begin_clock'])
                elif pc == labels['textLayerComplete']:
                    stage_counts['text'] += 1
                    buffer = states[-1]['buffer']
                    fonts[buffer] = text_font
                    check_fonts(ram)
                    assert ram[labels['textOffsets']:labels['textOffsets'] + 16] == text_offsets
                    states[-1].update(text_clock=clock, text_clocks=clock - states[-1]['cleared_clock'])
                elif pc == labels['renderComplete']:
                    stage_counts['composite'] += 1
                    buffer = states[-1]['buffer']
                    fonts[buffer] = composite
                    check_fonts(ram)
                    actual = ram[(0x20 + buffer * 8) * 256:(0x20 + buffer * 8) * 256 + 2048]
                    assert bytes(a ^ b for a, b in zip(actual, text_font)) == picture_font, 'independent picture contribution'
                    assert bytes(value & 0x55 for value in actual) == text_font, 'text survives picture OR pass'
                    assert ram[labels['pictureOffsets']:labels['pictureOffsets'] + 16] == picture_offsets
                    for base, asset in source_assets.items():
                        assert ram[base:base + len(asset)] == asset, ('immutable source/LUT', hex(base))
                    overlap = len(text_coordinates & picture_coordinates)
                    renders.append(dict(sequence=len(renders) + 1, phase=phase, field=field,
                                        text_pixels=len(text_coordinates), picture_pixels=len(picture_coordinates), overlap_pixels=overlap,
                                        render_clocks=clock - states[-1]['begin_clock'],
                                        picture_clocks=clock - states[-1]['text_clock']))
                elif pc == labels['displayComplete']:
                    stage_counts['publication'] += 1
                    sequence = stage_counts['publication']
                    assert value(ram, 'presentationCounter', 2) == sequence
                    assert phase == value(ram, 'frontPose') == (sequence - 1) % 256
                    check_fonts(ram)
                    front = (value(ram, 'frontFontHigh') - 0x20) // 8
                    assert front == sequence % 2 and value(ram, 'frontScreenHigh') == 4
                    assert len(publications) == sequence and publications[-1]['selection'] == (0x18, 0x1a)[front]
                    monitor.run('bank io')
                    native_colors = monitor.memory(OUT / 'latest-colors.bin', 0xd800, 0xdbff)
                    assert bytes(value & 15 for value in native_colors) == colors
                    registers = monitor.memory(OUT / 'latest-vic.bin', 0xd000, 0xd03f)
                    assert registers[0x11] & 0x7f == 0x1b and registers[0x16] & 0x3f == 0x18
                    assert registers[0x18] & 0xfe == (0x18, 0x1a)[front] and registers[0x15] == 0
                    assert [value & 15 for value in registers[0x20:0x24]] == [0, 0, 14, 3]
                    shot = OUT / f'publication-{sequence:03d}-phase-{phase:03d}.png'
                    monitor.run(f'screenshot "{shot}" 2')
                    actual = Image.open(shot).convert('RGB')
                    expected = screenshot_reference(text_coordinates, picture_coordinates, palette)
                    difference = ImageChops.difference(actual, expected)
                    if difference.getbbox():
                        expected.save(OUT / 'expected-failed.png')
                        difference.save(OUT / 'difference-failed.png')
                        raise AssertionError((sequence, phase, 'full live VIC pixels', difference.getbbox()))
                    images.append(actual)
                    presentations.append(dict(sequence=sequence, phase=phase, field=field, clock=clock,
                                              width=states[-1]['width'], mode=states[-1]['mode'], screenshot=shot.name))
                    if sequence % 32 == 0:
                        print(f'Verified {sequence}/257 live presentations', flush=True)
                    if sequence == 257:
                        break
                else:
                    raise AssertionError(('unexpected native stop', hex(pc)))
            else:
                raise AssertionError('Bounded run did not complete 257 presentations')
            monitor.connection.sendall(b'quit\n')
            process.wait(timeout=10)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            if monitor:
                (OUT / 'monitor.log').write_text('\n'.join(monitor.transcript))
                monitor.connection.close()
    assert set(stage_counts.values()) == {257}
    assert {row['phase'] for row in states} == set(range(256))
    assert {row['mode'] for row in states} == set(range(4))
    assert all(row['text_pixels'] > 0 for row in renders)
    assert all(row['picture_pixels'] > 0 for row, state in zip(renders, states) if state['width'] > 0)
    assert all(row['picture_pixels'] == 0 for row, state in zip(renders, states) if state['width'] == 0)
    assert max(row['overlap_pixels'] for row in renders) > 0
    assert images[0].tobytes() == images[-1].tobytes(), 'complete source, wave and aperture state wraps at 256 updates'
    intervals = [b['field'] - a['field'] for a, b in zip(presentations, presentations[1:])]
    durations = [20 * interval for interval in intervals]
    images[0].save(OUT / 'layered-dypp-reveal.gif', save_all=True, append_images=images[1:],
                   duration=durations + [durations[0]], loop=0)
    proof = dict(pass_=True, program_sha256=hashlib.sha256(program.read_bytes()).hexdigest(), command=command,
                 process_exit=process.returncode, prepared_source_pixels=[256 * 24, 256 * 48],
                 prepared_source_windows_bytes=64 * (24 + 48), reusable_expansion_bytes=len(tables),
                 published_states=257, state_period=256, reveal_choreography_period=64,
                 layer_passes=514, complete_font_bytes_per_pass=2 * 2048, observed_passes=257 * 5,
                 full_screenshot_pixels=257 * 384 * 272, stateful_mask_byte_updates=sum(len(row['changed_mask_columns']) for row in states),
                 picture_pixels_range=[min(row['picture_pixels'] for row in renders), max(row['picture_pixels'] for row in renders)],
                 text_pixels_range=[min(row['text_pixels'] for row in renders), max(row['text_pixels'] for row in renders)],
                 overlap_pixels_range=[min(row['overlap_pixels'] for row in renders), max(row['overlap_pixels'] for row in renders)],
                 PAL_fields_per_publication=intervals, mean_PAL_fields_per_publication=sum(intervals) / len(intervals),
                 rendering_clock_range=[min(row['render_clocks'] for row in renders), max(row['render_clocks'] for row in renders)],
                 clear_clock_range=[min(row['clear_clocks'] for row in states), max(row['clear_clocks'] for row in states)],
                 states=states, renders=renders, presentations=presentations, publications=publications,
                 limits=['Original own scene and software column displacement, not recovered Demo Coder source or a released scene pixel match.',
                         'Sources and reusable tables are prepared; C64 performs scroll, sine addressing, selector compositing, aperture state and publication.',
                         '64x128 logical multicolor canvas, 128x128 physical pixels; no claimed original resolution or 50 Hz deadline.',
                         'PAL VICE 8565; store trace raster/cycle values are observer coordinates, not certified physical bus phases.',
                         'GIF durations follow observed 20 ms PAL-field counts; GIF playback timing is approximate.'])
    proof['pass'] = proof.pop('pass_')
    (OUT / 'proof.json').write_text(json.dumps(proof, indent=2) + '\n')
    print(json.dumps({key: value for key, value in proof.items() if key not in
                      ('command', 'states', 'renders', 'presentations', 'publications', 'PAL_fields_per_publication')}, indent=2))


if __name__ == '__main__':
    main()
