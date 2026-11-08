#!/usr/bin/env python3
"""Check native cached-row wrapping, prepared glyphs and complete tunnel pixels.

Uses the project's audited VICE 3.10 snapshot schema, not release-program data.
Observation PCs are located from actual hardware-store instructions; no debug
dispatch table or test-only production mode is added to the raster program.
"""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import socket
import subprocess

from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'build/native'
OUT.mkdir(parents=True, exist_ok=True)
(OUT / 'proof.json').unlink(missing_ok=True)


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


common = module('tunnel_monitor', ROOT / 'verify.py')
schema = module('tunnel_snapshot', ROOT / 'research/quondam/snapshot_state.py')
labels = common.read_labels(HERE / 'build/main.sym')
program = HERE / 'build/example.prg'
data = program.read_bytes()
load = int.from_bytes(data[:2], 'little')
code = data[2 + labels['rasterKernel'] - load:2 + labels['fieldComplete'] - load]
windows = [labels['rasterKernel'] + match.start()
           for match in re.finditer(re.escape(bytes.fromhex('a9 1a 8d 11 d0')), code)]
assert len(windows) == 23, len(windows)
palette = [tuple(int(v, 16) for v in line.split()[:3])
           for line in (ROOT / 'palettes/colodore.vpl').read_text().splitlines()
           if line and not line.startswith('#')]
offsets = (0, 0x800, 0x2000, 0x2800, 0x3000, 0x3800)


def selector(x, y, phase):
    dx, dy = abs(x - 80), abs(y - 96) / 2
    radius, across = max(dx, dy), min(dx, dy)
    return (math.floor(180 / (radius + 4)) + phase
            + 2 * math.floor(across * 8 / (radius + 1))) & 3


def glyph_bytes(band):
    return bytes(sum(selector(column * 4 + pixel, band * 8 + row, phase)
                     << (6 - pixel * 2) for pixel in range(4))
                 for phase in range(4) for column in range(40) for row in range(8))


def expected_pixels(phase):
    colors = (0, 6, 3, 1)
    return [palette[colors[selector(x // 2, y, phase)]] if y < 192 else palette[0]
            for y in range(200) for x in range(320)]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


with socket.socket() as reservation:
    reservation.bind(('127.0.0.1', 0))
    port = reservation.getsockname()[1]
command = common.vice_command(os.environ.get('VICE', 'x64sc'), program, port,
                              ROOT / 'palettes/colodore.vpl')
log = (OUT / 'vice.log').open('w')
process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
monitor = None
fields, wraps, entry_positions, entry_clocks = [], [], [], []
try:
    monitor = common.Monitor(common.connect_monitor(process, port))
    # Require register data before issuing mutations: a delayed initial greeting
    # must not be mistaken for the reply to the first breakpoint command.
    monitor.run('r')

    def stop(address):
        monitor.run('delete')
        monitor.run(f'break ${address:04x}')
        monitor.run('x')
        return monitor.run('r')

    def state(name):
        path = OUT / (name + '.vsf')
        monitor.run(f'dump "{path}"')
        return schema.read_snapshot(path)

    def ram(name):
        monitor.run('bank ram')
        return monitor.memory(OUT / (name + '.ram'), 0, 65535)

    def capture_field(name):
        memory = ram(name)
        field = int.from_bytes(memory[labels['fieldCounter']:labels['fieldCounter'] + 2], 'little')
        phase = memory[labels['phase']]
        assert phase == (field >> 2) & 3
        expected_codes = bytes(range(64 + phase * 40, 104 + phase * 40))
        assert memory[0x3000:0x3028] == expected_codes
        assert memory[0x3028:0x3050] == bytes([240]) * 40
        for band in range(24):
            address = (band // 6) * 0x4000 + offsets[band % 6] + 512
            assert memory[address:address + 1280] == glyph_bytes(band), (field, band)
        screenshot = OUT / (name + '.png')
        monitor.run(f'screenshot "{screenshot}" 2')
        image = Image.open(screenshot).convert('RGB')
        pixels = list(image.crop((32, 35, 352, 235)).get_flattened_data())
        expected = expected_pixels(phase)
        mismatches = sum(a != b for a, b in zip(pixels, expected))
        assert mismatches == 0, (name, field, phase, mismatches)
        fields.append({'name': name, 'field': field, 'phase': phase,
                       'glyph_bytes_compared': 24 * 1280,
                       'native_pixels_compared': 64000, 'pixel_mismatches': mismatches,
                       'screenshot': screenshot.name, 'screenshot_sha256': digest(screenshot),
                       'ram_sha256': hashlib.sha256(memory).hexdigest()})
        return memory

    # Four completed representative fields cover every prepared texture phase.
    monitor.run(f'break ${labels["fieldComplete"]:04x}')
    for index in range(16):
        monitor.run('x')
        if index in (3, 7, 11, 15):
            capture_field(f'field-{index:03d}')
            assert fields[-1]['field'] == index

    stop(windows[0])
    before_memory = ram('before-first-window')
    before = state('before-first-window')
    phase = before_memory[labels['phase']]
    codes = list(range(64 + phase * 40, 104 + phase * 40))
    vic = before['vicii']
    assert vic['model'] == 1
    assert (vic['raster_line'], vic['raster_cycle'], vic['rc'], vic['vcbase'], vic['bad_line']) == (58, 49, 7, 0, 0)
    assert vic['vbuf'] == codes and vic['cbuf'] == [9] * 40
    snapshot_ram = schema.module_payload(OUT / 'before-first-window.vsf', 'C64MEM')[4:65540]
    assert snapshot_ram == before_memory

    stop(windows[0] + 5)
    asserted = state('late-condition-asserted')
    vic = asserted['vicii']
    assert (vic['raster_line'], vic['raster_cycle'], vic['rc'], vic['bad_line']) == (58, 55, 7, 1)
    assert vic['vbuf'] == codes

    # Each next-line state is before the new line's matrix-fetch window.
    for index, window in enumerate(windows):
        stop(window + 15)
        current = state(f'after-window-{index + 1:02d}')
        vic, cia = current['vicii'], current['cia']['CIA2']
        band = index + 1
        assert (vic['raster_line'], vic['raster_cycle']) == (59 + index * 8, 4)
        assert (vic['rc'], vic['idle_state'], vic['vcbase'], vic['vc']) == (0, 0, band * 40, band * 40)
        assert vic['vbuf'] == codes and vic['cbuf'] == [9] * 40
        assert set(vic['color_ram']) == {9}
        assert cia['pra'] & 3 == 0 and cia['ddra'] == 0x3c + band // 6
        assert vic['regs'][0x18] & 0xfe == 0xc0 | (offsets[band % 6] >> 10)
        clock = int.from_bytes(schema.module_payload(OUT / f'after-window-{band:02d}.vsf', 'MAINCPU')[:8], 'little')
        if wraps:
            assert clock - wraps[-1]['clock'] == 504
        wraps.append({'window': band, 'raster_line': vic['raster_line'],
                      'raster_cycle': vic['raster_cycle'], 'rc': vic['rc'],
                      'clock': clock,
                      'vcbase': vic['vcbase'], 'cached_codes': vic['vbuf'],
                      'cached_colors': vic['cbuf'], 'cia2_direction': cia['ddra'],
                      'cia2_output_latch': cia['pra'], 'd018': vic['regs'][0x18]})
    stop(labels['fieldComplete'])
    capture_field('field-with-band-observations')

    # Repeated natural entries check stability across all four animation phases.
    for index in range(16):
        registers = stop(windows[0])
        match = re.search(r'^\.;[0-9a-fA-F]{4}\s+(.*)$', registers, re.M)
        position = tuple(map(int, match[1].split()[-3:-1]))
        assert position == (58, 49), (index, position)
        entry_positions.append(list(position))
        entry_clocks.append(int(match[1].split()[-1]))
    assert all(b - a == 19656 for a, b in zip(entry_clocks, entry_clocks[1:]))
    stop(labels['fieldComplete'])
    capture_field('field-without-band-snapshots')
    assert fields[-1]['phase'] == fields[-2]['phase']
    assert fields[-1]['screenshot_sha256'] == fields[-2]['screenshot_sha256']
    monitor.connection.sendall(b'quit\n')
    process.wait(timeout=5)
finally:
    if process.poll() is None:
        process.kill()
        process.wait(timeout=5)
    if monitor:
        (OUT / 'monitor.log').write_text('\n'.join(monitor.transcript))
        monitor.connection.close()
    log.close()

report = {'pass': True, 'program_sha256': digest(program), 'command': command,
          'fields': fields, 'cached_row_wraps': wraps, 'stable_entry_positions': entry_positions,
          'stable_entry_clocks': entry_clocks, 'pal_cycles_per_field': 19656,
          'vic_model': before['vicii']['model'], 'vice_version': before['header']['emulator_version'],
          'before_first_window': {k: before['vicii'][k] for k in ('raster_line', 'raster_cycle', 'rc', 'vcbase', 'bad_line')},
          'late_condition_asserted': {k: asserted['vicii'][k] for k in ('raster_line', 'raster_cycle', 'rc', 'vcbase', 'bad_line')},
          'native_pixels_compared': sum(field['native_pixels_compared'] for field in fields),
          'owned_process_returncode': process.returncode,
          'observer_limits': ['Raster cycles are zero-based instruction-boundary observations, not independently timestamped write buses.',
              'Serialized VIC cache/RC state proves the captured mechanism; screenshots prove six completed sampled fields.',
              'Matching screenshots do not assert complete CIA or whole-machine snapshot identity.',
              'No PC changes, RAM patches, snapshot restores or release payload substitutions were used.',
              'VICE 3.10 C64SC PAL model schema only; physical VIC revisions remain untested.']}
(OUT / 'proof.json').write_text(json.dumps(report, indent=2) + '\n')
print(json.dumps({'pass': report['pass'], 'fields': len(fields), 'row_wraps': len(wraps),
                  'stable_entries': len(entry_positions), 'native_pixels_compared': report['native_pixels_compared'],
                  'process_returncode': process.returncode}, indent=2))
