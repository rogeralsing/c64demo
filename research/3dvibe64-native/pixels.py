#!/usr/bin/env python3
"""Accept closed Mode6 rasterizer samples using captured inputs and scalar math.

No SDK code, original CPU, assembler, emulator, subprocess or live connection
runs here. Captured span parameters are inputs, not a geometry oracle.
"""

from collections import Counter
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import struct
import sys
import tarfile
import zlib

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/3dvibe64-native'
CASE = BASE / 'native-01'
OUT = BASE / 'pixel-analysis'
PROGRAM = BASE / 'build-01/products/3Dvibe64.prg'
CASE_SHA = 'ec17844d8b748e0914f6ffdba3b336c63247229bb62ada335172b4da30fe9281'
PINS = {
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'verify.py': '3c83d1f9996586157909277f9fdc80f8d8cc0de20845b9a82108e1fd27d3dd93',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'research/anomaly/scanout.py': 'c5e63a07f3060614710518aaf9b9e6c9365c297619af4e19719a4b5f8b62198f',
    'research/3dvibe64-native/inspect_build.py': '4ae2fa487554d57c313c10880ef32a613fb7c7dde170e2819386047dd6358bb7',
    'research/3dvibe64-native/scene.json': '2dc0c5d4a8bab84ae522a31da6b7e998e346cce1dd0ffe6693ab01990ca6f72a',
    'build/research/3dvibe64-native/build-analysis/build-proof.json': '4f051c805788c579f4ef6ecf0b96f067df916b7946944fdf926c34d8b14871fc',
    'build/research/3dvibe64-native/build-01/products/3Dvibe64.asm': '22008b3a92b7896c699543b12f9036704797262aa3558cd9116d8a09c85b796f',
    'build/research/3dvibe64-native/build-01/products/3Dvibe64.prg': '69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb',
    'build/research/3dvibe64-native/symbols-01/3Dvibe64.labels': '265a1770fe7a605139f0cdfd9d2983f6ddb314a1cf234a6f3a14d6f3b344e847',
    'build/research/3dvibe64-native/native-01-pin.json': '79c67956910a7024dac5afd85f751b4cf09b92f0ec485948cee27775694b0611',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
    'palettes/colodore.vpl': 'cfc740890e811b94a73bbbe9f38c400f6714d37c6b6167935adf4f892422b972',
}
DUMPS = 'm 000b 002f; m b43b b441'
MEMORY = re.compile(r'^>C:([0-9a-f]{4})  ([0-9a-f]{2}(?: [0-9a-f]{2}){0,3})(?=\s{2,}|$)', re.M | re.I)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


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


def binary(name, data):
    path = OUT / name
    path.write_bytes(data)
    return artifact(path)


def wire_case():
    wire = load('gouraud_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {'native-01': CASE_SHA}
    source_text = (ROOT / 'research/verify_vice_live.py').read_text()
    node = next(node for node in ast.parse(source_text).body if isinstance(node, ast.FunctionDef) and node.name == 'audit_session')
    original = ast.get_source_segment(source_text, node) + '\n'
    before = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    after = ('assert session["startup_mode"] == "autostart"\n'
             '    assert session["command"].count("-autostart") == 1\n'
             f'    assert session["command"][session["command"].index("-autostart") + 1] == {str(PROGRAM)!r}')
    assert original.count(before) == 1
    adapted = original.replace(before, after)
    exec(compile(adapted, '<pinned-wire-PRG-autostart-contract>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-01')
    assert not case['partial'] and not case['cancelled'] and not case['waits']
    launch = case['session']['command']
    assert case['session']['program'] == str(PROGRAM) and '-pal' in launch
    assert launch[launch.index('-speed') + 1] == '100' and '+warp' in launch and '+autostart-warp' in launch
    assert launch[launch.index('-autostartprgmode') + 1] == '1'
    pin = json.loads((BASE / 'native-01-pin.json').read_text())
    assert pin['case_sha256'] == CASE_SHA
    return wire, case, dict(original_function_sha256=sha(original.encode()), adapted_function_sha256=sha(adapted.encode()),
                            replaced_assertion=before, replacement=after,
                            scope='Only exact generated-PRG autostart metadata replaces manual-load metadata.')


def commands(wire, case):
    rows = [row for _, row in sorted(case['responses'].items())]
    contexts, rejected, interrupted, last = {}, [], [], None
    for index, row in enumerate(rows):
        command, response = row['command'], row['response']
        if row['sequence'] == 29:
            assert command == 'break 09b1 if @ram:$000b == 0'
            assert response.startswith('ERROR -- Conditional operation missing an operand:')
            rejected.append(dict(sequence=29, command=command, response=response,
                interpretation='Rejected decimal-looking condition; it did not arm the intended publication checkpoint.'))
        else:
            assert not re.search(r'ERROR --|Syntax error|Unknown resource|[Mm]onitor observation failed', response)
        allowed = command in ('r', 'sidefx off', 'help command', 'help break', 'bank ram', 'x', 'trace exec a000',
                              'command 1 "' + DUMPS + '"')
        allowed |= bool(re.fullmatch(r'delete [0-9a-f]+', command))
        allowed |= bool(re.fullmatch(r'break [0-9a-f]{4}(?: [0-9a-f]{4})?(?: if [^;\n]+)?', command))
        if command == 'r':
            last = wire.registers(response)
        if command == 'x':
            if row['status'] == 'interrupted':
                assert row['sequence'] == 30 and row['interrupt']['reason'] == 'input'
                interrupted.append(dict(sequence=30, command='x', registers=wire.registers(row['interrupt']['register_response']),
                    interpretation='Same PID/socket was interrupted read-only after missing the intended first publication stop. No first publication is accepted.'))
            else:
                assert row['status'] == 'completed'
            last = None
        match = re.fullmatch(r'(bsave|dump) "([^"\n]+)"( 0 0000 ffff)?', command)
        if match:
            kind, filename, suffix = match.groups()
            path = Path(filename)
            assert path.parent == CASE and last is not None and rows[index - 1]['command'] == 'r'
            assert (kind == 'bsave') == (suffix is not None) and path.name not in contexts
            contexts[path.name] = dict(registers=last, sequence=row['sequence'])
            allowed = True
        assert allowed, ('Unclassified command', command)
    assert len(rows) == 63 and len(contexts) == 14 and len(rejected) == len(interrupted) == 1
    assert all(row['status'] == 'completed' for row in rows if row['sequence'] != 30)
    assert [row['sequence'] for row in rows if row['command'] == 'command 1 "' + DUMPS + '"'] == [20, 42]
    return contexts, dict(ordinary_commands=63, read_only_attached_commands=[20, 42], rejected_conditions=rejected,
        interrupted_resumes=interrupted, no_snapshot_restores=True,
        declared_PRG_autostart_mode1_loader_injection=True, no_later_manual_CPU_RAM_or_register_writes=True,
        startup_speed_contract=dict(PAL=True, launch_Speed=100, launch_warp_disabled=True,
            runtime_resource_queries_present=False,
            limitation='Launch flags are retained. No explicit runtime speed/warp query was made, and no wall-time FPS claim is derived.'))


def captures(reader, layout, contexts):
    result = {}
    for path in sorted(CASE.glob('*.vsf')):
        ram_path = path.with_suffix('.bin')
        registers = contexts[path.name]['registers']
        assert registers == contexts[ram_path.name]['registers']
        ram = ram_path.read_bytes()
        memory = reader.module_payload(path, 'C64MEM')
        assert len(ram) == 65536 and ram == memory[4:65540]
        assert (memory[1], memory[0]) == (registers['port00'], registers['port01'])
        cpu = reader.module_payload(path, 'MAINCPU')
        fields = dict(clock=int.from_bytes(cpu[:8], 'little'), a=cpu[8], x=cpu[9], y=cpu[10], sp=cpu[11],
                      pc=int.from_bytes(cpu[12:14], 'little'), flags=cpu[14])
        assert all(registers[k] == v for k, v in fields.items())
        state = reader.read_snapshot(path)
        assert (state['vicii']['raster_line'], state['vicii']['raster_cycle']) == (registers['line'], registers['cycle'])
        pipe, meta, raster = layout.draw_state(reader.module_payload(path, 'VIC-II'))
        result[path.stem] = dict(ram=ram, state=state, pipe=pipe, meta=meta, raster=raster,
            entry=dict(stem=path.stem, ram=artifact(ram_path), snapshot=artifact(path), registers=registers,
                       paired_RAM_CPU_ports_clock_and_beam_equal=True))
    assert len(result) == 7
    program = PROGRAM.read_bytes()
    load_address = int.from_bytes(program[:2], 'little')
    assert result['start']['entry']['registers']['pc'] == load_address + 12 == 0x080d
    assert result['start']['ram'][load_address:load_address + len(program) - 2] == program[2:]
    return result


def trace_spans(case, layout, sequence, baseline, completed):
    response = case['responses'][sequence]
    assert response['command'] == 'x' and response['status'] == 'completed'
    raw = response['response'].replace('\r\n', '\n')
    headers = list(layout.TRACE.finditer(raw))
    assert len(headers) == len(re.findall(r'^#\d+ \(Trace\s+exec a000\)', raw, re.M))
    spans = []
    for index, match in enumerate(headers):
        event = match.groupdict()
        assert event['kind'] == 'exec' and int(event['pc'], 16) == int(event['target'], 16) == 0xa000
        chunk = raw[match.end():headers[index + 1].start() if index + 1 < len(headers) else len(raw)]
        assert chunk.startswith('Executing: ' + DUMPS + '\n')
        memory = {}
        for line in MEMORY.finditer(chunk):
            address = int(line[1], 16)
            for offset, value in enumerate(bytes.fromhex(line[2])):
                assert address + offset not in memory
                memory[address + offset] = value
        assert set(memory) == set(range(0x0b, 0x30)) | set(range(0xb43b, 0xb442))
        x0, x1, delta, raw_direction, error, extent, shade0 = [memory[i] for i in range(0xb43b, 0xb442)]
        assert raw_direction in (1, 255)
        direction = 1 if raw_direction == 1 else -1
        shade1 = shade0 + direction * delta
        y, draw = memory[0x2f], memory[0x0b]
        assert 0 <= x0 <= x1 < 160 and 0 <= y < 100 and extent == x1 - x0 and error == 0
        assert 0 <= shade0 <= 32 and 0 <= shade1 <= 32 and draw == baseline['ram'][11]
        base = 0x6000 if draw == 0 else 0x2000
        row_offset = (y // 4) * 320 + 2 * (y % 4)
        row0, row1 = memory[0x25] + 256 * memory[0x26], memory[0x27] + 256 * memory[0x28]
        assert row0 == base + row_offset and row1 == row0 + 1
        assert (memory[0x29], memory[0x2a]) == (x0, x1)
        clock = int(event['clock'])
        assert baseline['entry']['registers']['clock'] < clock < completed['entry']['registers']['clock']
        spans.append(dict(index=index, response_sequence=sequence, clock=clock,
            line=int(event['line']), raw_cycle=int(event['cycle']), x0=x0, x1=x1, y=y,
            delta=delta, direction=direction, error0=error, extent=extent, shade0=shade0, shade1=shade1,
            drawbuf=draw, row0=row0, row1=row1,
            zero_page_dump=bytes(memory[i] for i in range(0x0b, 0x30)).hex(),
            span_ABI_dump=bytes(memory[i] for i in range(0xb43b, 0xb442)).hex()))
    assert spans and all(a['clock'] < b['clock'] for a, b in zip(spans, spans[1:]))
    return spans


def bayer_rank(x, y):
    # Two independent 2x2 binary ranks, high rank from low coordinate bits.
    return 8 * ((x & 1) ^ (y & 1)) + 4 * (y & 1) + 2 * (((x >> 1) ^ (y >> 1)) & 1) + ((y >> 1) & 1)


def slot(shade, x, y):
    rank = bayer_rank(x & 3, y & 3)
    return (2 if rank < shade else 1) if shade <= 16 else (3 if rank < shade - 16 else 2)


def scalar(baseline, spans, control=None):
    draw = baseline['ram'][11]
    bitmap, screen = (0x6000, 0x5c00) if draw == 0 else (0x2000, 0x0400)
    image = bytearray(baseline['ram'][bitmap:bitmap + 8000])
    attributes = bytearray(baseline['ram'][screen:screen + 1024])
    colors = bytearray(baseline['state']['vicii']['color_ram'])
    histogram, unique, samples = Counter(), set(), 0
    for span in spans:
        for x in range(span['x0'], span['x1'] + 1):
            k, extent = x - span['x0'], span['extent']
            increment = (k * span['delta']) // extent if extent else 0
            shade = span['shade0'] + span['direction'] * increment
            if control == 'flat':
                shade = span['shade0']
            elif control == 'floor_signed_increment' and extent:
                shade = span['shade0'] + (k * span['direction'] * span['delta']) // extent
            y = span['y']
            code = slot(shade, x, y + (1 if control == 'phase_y_plus1' else 0))
            offset = (y // 4) * 320 + (x // 4) * 8 + 2 * (y % 4)
            shift = 6 - 2 * (x & 3)
            for address in (offset,) if control == 'omit_duplicate_row' else (offset, offset + 1):
                image[address] = (image[address] & ~(3 << shift)) | (code << shift)
            histogram[shade] += 1
            unique.add((x, y))
            samples += 1
        for column in range(span['x0'] // 4, span['x1'] // 4 + 1):
            cell = (span['y'] // 4) * 40 + column
            attributes[cell], colors[cell] = 0xbf, 1
    return dict(bitmap=image, attributes=attributes, color_ram=colors, base=bitmap, screen=screen,
                samples=samples, unique_pixels=len(unique), shade_histogram=dict(sorted(histogram.items())))


def logical_colors(model, background):
    result = bytearray()
    for y in range(100):
        for x in range(160):
            offset = (y // 4) * 320 + (x // 4) * 8 + 2 * (y % 4)
            code = (model['bitmap'][offset] >> (6 - 2 * (x & 3))) & 3
            cell = (y // 4) * 40 + x // 4
            attr = model['attributes'][cell]
            result.append((background, attr >> 4, attr & 15, model['color_ram'][cell] & 15)[code])
    return bytes(result)


def expand(logical):
    return bytes(logical[(y // 2) * 160 + x // 2] for y in range(200) for x in range(320))


def preview(name, pixels):
    palette = [bytes(int(v, 16) for v in line.split()[:3])
               for line in (ROOT / 'palettes/colodore.vpl').read_text().splitlines()
               if len(line.split()) >= 3 and not line.strip().startswith('#')]
    assert len(palette) == 16
    def chunk(kind, data):
        return struct.pack('>I', len(data)) + kind + data + struct.pack('>I', zlib.crc32(kind + data))
    rows = b''.join(b'\0' + pixels[y * 320:(y + 1) * 320] for y in range(200))
    png = b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', 320, 200, 8, 3, 0, 0, 0))
    png += chunk(b'PLTE', b''.join(palette)) + chunk(b'IDAT', zlib.compress(rows, 9)) + chunk(b'IEND', b'')
    return binary(name, png)


def differences(a, b):
    assert len(a) == len(b)
    return sum(x != y for x, y in zip(a, b))


def sample(name, baseline, completed, spans, palette_clock):
    assert baseline['entry']['registers']['pc'] == 0x1153 and completed['entry']['registers']['pc'] == 0x08d4
    assert baseline['ram'][11] == completed['ram'][11] in (0, 1)
    model = scalar(baseline, spans)
    native = completed['ram'][model['base']:model['base'] + 8000]
    attrs = completed['ram'][model['screen']:model['screen'] + 1024]
    colors = completed['state']['vicii']['color_ram']
    assert differences(model['bitmap'], native) == differences(model['attributes'], attrs) == differences(model['color_ram'], colors) == 0
    control_results = {}
    for control in ('flat', 'floor_signed_increment', 'phase_y_plus1', 'omit_duplicate_row'):
        wrong = scalar(baseline, spans, control)
        count = differences(wrong['bitmap'], native)
        assert count > 0, ('Inconclusive selected control', name, control)
        control_results[control] = dict(changed_bitmap_bytes=count, rejected=True)
    logical = logical_colors(model, completed['state']['vicii']['regs'][0x21] & 15)
    display = expand(logical)
    delta = completed['entry']['registers']['clock'] - baseline['entry']['registers']['clock']
    assert delta > 0
    eligible = sum(span['extent'] >= 7 and
                   all(slot(span['shade0'], x, span['y']) == slot(span['shade1'], x, span['y']) for x in range(4))
                   for span in spans)
    result = dict(name=name, baseline=baseline['entry'], completed=completed['entry'],
        spans=save(name + '-spans.json', spans), span_count=len(spans), pixel_writes=model['samples'],
        unique_logical_pixels=model['unique_pixels'], shade_histogram=model['shade_histogram'],
        shade_range=[min(model['shade_histogram']), max(model['shade_histogram'])],
        descending_spans=sum(s['direction'] < 0 and s['delta'] > 0 for s in spans),
        singleton_spans=sum(s['extent'] == 0 for s in spans),
        classifier_eligible_uniform_spans=eligible, classifier_branch_individually_traced=False,
        bitmap_base=model['base'], screen_base=model['screen'], bitmap_bytes_compared=8000,
        screen_bytes_compared=1024, physical_color_RAM_bytes_compared=1024,
        bitmap_differences=0, screen_differences=0, color_RAM_differences=0,
        expected_bitmap=binary(name + '-expected-bitmap.bin', model['bitmap']),
        logical_color_indices=binary(name + '-logical-indices.bin', logical),
        display_color_indices=binary(name + '-display-indices.bin', display),
        preview=preview(name + '-preview.png', display), negative_controls=control_results,
        baseline_bitmap_nonzero_bytes=sum(v != 0 for v in baseline['ram'][model['base']:model['base'] + 8000]),
        clear_algorithm_independently_verified=False,
        timing=dict(start_clock=baseline['entry']['registers']['clock'], end_clock=completed['entry']['registers']['clock'],
            cycles=delta, PAL_refresh_cycles=19656, PAL_refresh_equivalents=delta / 19656,
            PAL_clock_Hz=palette_clock, emulated_seconds=delta / palette_clock,
            inverse_interval_renders_per_second_upper_bound=palette_clock / delta,
            whole_loop_or_delivered_FPS=False,
            scope='gous_done to render_frame_end: excludes earlier lighting/clear, presentation and the rest of the loop; includes geometry, fills, interrupts and VIC stalls.'))
    return result, model, display


def geometry(capture):
    regs, cia = capture['state']['vicii']['regs'], capture['state']['cia']['CIA2']
    bank = (~((cia['pra'] | (~cia['ddra'] & 255)) & 3) & 3) * 0x4000
    return dict(bank=bank, bitmap=bank + ((regs[0x18] & 8) << 10), screen=bank + (regs[0x18] >> 4) * 1024)


def field_base(capture):
    r = capture['entry']['registers']
    return r['clock'] - r['line'] * 63 - r['cycle']


def committed(decoded, model, display):
    published, visible = decoded['sample2-published'], decoded['sample2-visible']
    assert published['entry']['registers']['pc'] == 0x09b1
    assert (visible['entry']['registers']['line'], visible['entry']['registers']['cycle']) == (252, 3)
    assert field_base(published) == field_base(visible)
    for capture in (published, visible):
        geom = geometry(capture)
        assert geom['bitmap'] == model['base'] and geom['screen'] == model['screen']
        assert capture['ram'][11] == 1
        regs = capture['state']['vicii']['regs']
        assert regs[0x11] == 0x3b and regs[0x16] & 0x3f == 0x18 and regs[0x15] == 0
        assert capture['ram'][model['base']:model['base'] + 8000] == model['bitmap']
        assert capture['ram'][model['screen']:model['screen'] + 1024] == model['attributes']
        assert capture['state']['vicii']['color_ram'] == list(model['color_ram'])
    assert visible['meta']['current_line'] == 252
    native = bytes(visible['raster'][(y + 51) * 384 + x + 32] for y in range(200) for x in range(320))
    assert differences(display, native) == 0
    return dict(published=published['entry'], visible=visible['entry'],
        same_PAL_field=True, actual_display_geometry=geometry(visible),
        accepted_region=dict(first_raster_line=51, rows=200, first_raster_x=32, columns=320, palette_index_bytes=64000),
        committed_palette_index_differences=0, committed_indices=binary('sample2-native-committed-indices.bin', native),
        committed_sha256=sha(native), serialized_raster_metadata=visible['meta'],
        front_bitmap_and_attributes_equal_at_completed_published_visible_endpoints=True,
        no_transient_RAM_or_MMIO_write_claim=True, complete_312_line_raster_or_FPS_proof=False)


def source_rules():
    archive = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    names = ['src/c64/c64.h', 'src/monitor/mon_breakpoint.c', 'src/monitor/mon_parse.y', 'src/monitor/mon_lex.l']
    values = {}
    with tarfile.open(archive, 'r:gz') as container:
        for name in names:
            values[name] = container.extractfile('vice-3.10/' + name).read()
    header = values[names[0]].decode()
    clock = int(re.search(r'#define C64_PAL_CYCLES_PER_SEC\s+(\d+)', header)[1])
    assert clock == 985248 and '#define C64_PAL_CYCLES_PER_LINE 63' in header
    assert '#define C64_PAL_SCREEN_LINES    312' in header
    assert 'parse_and_execute_line(cp->command);' in values[names[1]].decode()
    assert 'mon_breakpoint_set_checkpoint_command($2, $4);' in values[names[2]].decode()
    assert 'return CMD_SEP;' in values[names[3]].decode()
    return clock, dict(archive=artifact(archive), members=[dict(member='vice-3.10/' + n, bytes=len(v), sha256=sha(v)) for n, v in values.items()],
        attached_command='A trace checkpoint executes its read-only attached monitor command; semicolon separates two memory displays.',
        bitmap_reference='Independent C64 cell/row/pair addressing and binary Bayer ranks; no packed renderer or CPU model is executed.')


def lighting(capture, build):
    ram = capture['ram']
    def signed(value):
        return value if value < 128 else value - 256
    cache = [signed(ram[i]) for i in (0x6f, 0x70, 0x71)]
    intensity = ram[0x72]
    assert 0 <= intensity <= 10
    targets = []
    for normal, center in zip(build['shade_normals'], build['center_dot_terms']):
        dot = sum(n * v for n, v in zip(normal, cache)) - center
        targets.append(0 if dot < 0 else min(32, (2 * min(63, dot // 256) * intensity + 7) // 15))
    values = list(ram[0xb520:0xb526])
    if capture['entry']['stem'] == 'before-spans':
        assert values == targets
    return dict(checkpoint=capture['entry']['stem'], actual_angles_whole=[ram[i] for i in (2, 3, 4)],
                actual_object_space_light_cache=cache, actual_intensity=intensity,
                independent_target_from_observed_light_cache=targets, actual_raw_vertex_shades=values,
                first_sample_targets_exact=values == targets,
                scope='First observed shade call compares target arithmetic from captured light-cache inputs. Full light transform is not independently reconstructed; sample2 prior slew history is unobserved.')


def main():
    for relative, digest in PINS.items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
    OUT.mkdir(parents=True, exist_ok=True)
    build = json.loads((BASE / 'build-analysis/build-proof.json').read_text())
    assert build['full_build_exit_code'] == 0 and build['symbol_reassembly_identical']
    wire, case, adapter = wire_case()
    contexts, command_audit = commands(wire, case)
    layout = load('gouraud_raster_layout', 'research/anomaly/scanout.py')
    reader = load('gouraud_snapshot_reader', 'research/quondam/snapshot_state.py')
    decoded = captures(reader, layout, contexts)
    pal_clock, rules = source_rules()
    sample1_spans = trace_spans(case, layout, 22, decoded['before-spans'], decoded['completed'])
    sample2_spans = trace_spans(case, layout, 44, decoded['sample2-before'], decoded['sample2-completed'])
    one, _, _ = sample('sample1', decoded['before-spans'], decoded['completed'], sample1_spans, pal_clock)
    two, model, display = sample('sample2', decoded['sample2-before'], decoded['sample2-completed'], sample2_spans, pal_clock)
    one.update(publication_captured=False, committed_first_publication_accepted=False,
               preview_scope='Decoded completed bitmap and predicted/verified palette; first publication was missed.')
    two.update(publication_captured=True, preview_scope='Scalar reference also matches committed native visible VIC region.')
    assert len(sample1_spans) == 168 and len(sample2_spans) == 161
    accepted = committed(decoded, model, display)
    shades = [lighting(decoded[name], build) for name in ('before-spans', 'sample2-before')]
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()), input_pins=[artifact(ROOT / p) for p in PINS],
        native_case_directory_sha256=CASE_SHA, wire=wire.summary(case), startup_adapter=adapter,
        commands=command_audit, source_rules=rules, full_RAM_snapshot_pairs=7, full_RAM_bytes_compared=7 * 65536,
        generated_PRG_loaded_payload_bytes=49709, boot_PRG_payload_exact=True,
        checkpoints=[capture['entry'] for capture in decoded.values()],
        independent_reference='Actual CPU span endpoints are input. Signed rational interpolation, binary Bayer rank, per-pair bitmap addressing and fixed material cell writes are independently calculated in captured order.',
        accepted_samples=[one, two], observed_vertex_lighting=shades, committed_sample2=accepted,
        final_continuation=decoded['sample2-visible']['entry'],
        limitations=['This is rasterizer acceptance from captured span inputs, not an independent geometry, clipping, culling, painter-order or edge-shade proof.',
            'No SDK renderer, CPU, assembler, VICE or downloaded executable runs in this producer.',
            'The baseline bitmap is actual memory after prior clearing; clearing correctness is not independently proved.',
            'First publication was missed after an explicit rejected condition and interrupted resume. Only sample2 has publication and committed visible-body evidence.',
            'Source geometry is an eight-triangle smooth octahedron; its current projection can read visually as a quadrilateral. A pixel match does not certify a persuasive silhouette.',
            'The observed raster intervals are about half a second on the PAL cycle model and exclude earlier/later work. They are slow; no 50 FPS, whole-loop FPS, acceleration or physical-hardware claim is made.',
            'Only the 320x200 visible bitmap body is compared with committed VIC output; borders, other raster lines and a complete 312-line field are not claimed.',
            'Endpoint memory/mode agreement is not proof of no transient writes. Preview RGB uses the pinned Colodore palette, while acceptance compares palette indices.'])
    result['pass'] = result.pop('pass_')
    receipt = save('pixel-proof.json', result)
    (OUT / 'pixels.checked.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(pass_=True, samples=[dict(spans=s['span_count'], pixel_writes=s['pixel_writes'],
        unique_pixels=s['unique_logical_pixels'], shades=s['shade_range'], cycles=s['timing']['cycles']) for s in (one, two)],
        committed_visible_bytes=64000, committed_differences=0, receipt=receipt), indent=2))


if __name__ == '__main__':
    main()
