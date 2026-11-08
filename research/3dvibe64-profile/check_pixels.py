#!/usr/bin/env python3
"""Check the three closed cost-profile frames with the frozen scalar reference.

No SDK, CPU, assembler, VICE, subprocess or live connection executes here.
The reference is imported without main(), and only its output root is changed.
"""

import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/3dvibe64-profile'
CASE = BASE / 'native-01'
OUT = BASE / 'pixel-analysis'
PROGRAM = ROOT / 'build/research/3dvibe64-native/build-01/products/3Dvibe64.prg'
CASE_SHA = '13bfd23f30bf0b7a2db7a9e8dc4ceb8dc69e77d81c76862fe9b372a1f23ef714'
DUMPS = 'm 0100 01ff; m 000b 002f; m b43b b441'
PINS = {
    'research/3dvibe64-native/pixels.py': '859e1ece975ea57c283cf0c4dcef47be95cf91c72d8d9eba29cd4765da8e16a2',
    'build/research/3dvibe64-native/pixel-analysis/pixel-proof.json': '6f579e43f1585a2e338909ff77f5c99997ee8e0f793a7fd0ed23a7d3cc699c30',
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'verify.py': '3c83d1f9996586157909277f9fdc80f8d8cc0de20845b9a82108e1fd27d3dd93',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'research/anomaly/scanout.py': 'c5e63a07f3060614710518aaf9b9e6c9365c297619af4e19719a4b5f8b62198f',
    'build/research/3dvibe64-native/build-01/products/3Dvibe64.prg': '69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb',
    'build/research/3dvibe64-native/build-01/products/3Dvibe64.asm': '22008b3a92b7896c699543b12f9036704797262aa3558cd9116d8a09c85b796f',
    'build/research/3dvibe64-native/build-analysis/build-proof.json': '4f051c805788c579f4ef6ecf0b96f067df916b7946944fdf926c34d8b14871fc',
    'palettes/colodore.vpl': 'cfc740890e811b94a73bbbe9f38c400f6714d37c6b6167935adf4f892422b972',
}


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


def wire_case():
    wire = load('profile_pixel_wire', 'research/verify_vice_live.py')
    wire.BASE, wire.CASE_PINS = BASE, {'native-01': CASE_SHA}
    text = (ROOT / 'research/verify_vice_live.py').read_text()
    node = next(n for n in ast.parse(text).body if isinstance(n, ast.FunctionDef) and n.name == 'audit_session')
    original = ast.get_source_segment(text, node) + '\n'
    before = 'assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    after = ('assert session["startup_mode"] == "autostart"\n'
             '    assert session["command"].count("-autostart") == 1\n'
             f'    assert session["command"][session["command"].index("-autostart") + 1] == {str(PROGRAM)!r}')
    assert original.count(before) == 1
    adapted = original.replace(before, after)
    exec(compile(adapted, '<profile-PRG-autostart-metadata>', 'exec'), wire.__dict__)
    case = wire.audit_session('native-01')
    assert not case['partial'] and not case['cancelled'] and not case['waits']
    launch = case['session']['command']
    assert case['session']['program'] == str(PROGRAM)
    assert launch[launch.index('-autostartprgmode') + 1] == '1'
    assert '-pal' in launch and launch[launch.index('-speed') + 1] == '100'
    return wire, case, dict(original_function_sha256=sha(original.encode()), adapted_function_sha256=sha(adapted.encode()),
        replaced_assertion=before, replacement=after, scope='Only generated-PRG autostart metadata is adapted.')


def command_audit(wire, case):
    rows = [r for _, r in sorted(case['responses'].items())]
    contexts, rejected, last = {}, [], None
    for index, row in enumerate(rows):
        command, response = row['command'], row['response']
        assert row['status'] == 'completed'
        if row['sequence'] in (4, 5):
            assert command == ('resourceget Speed' if row['sequence'] == 4 else 'resourceget WarpMode')
            assert response.startswith('ERROR -- Wrong syntax:')
            rejected.append(dict(sequence=row['sequence'], command=command, response=response))
        elif row['sequence'] == 10:
            assert command == 'resourceget "WarpMode"' and response.startswith('Unknown resource "WarpMode".')
            rejected.append(dict(sequence=10, command=command, response=response))
        else:
            assert not re.search(r'ERROR --|Syntax error|Unknown resource|[Mm]onitor observation failed', response)
        allowed = command in ('r', 'sidefx off', 'help resourceget', 'bank ram', 'x',
            'resourceget Speed', 'resourceget WarpMode', 'resourceget "Speed"',
            'resourceget "WarpMode"', 'resourceget "InitialWarpMode"')
        allowed |= bool(re.fullmatch(r'(?:break|trace exec) [0-9a-f]{4}', command))
        allowed |= bool(re.fullmatch(r'delete \d+', command))
        attached = re.fullmatch(r'command \d+ "([^"\n]+)"', command)
        if attached:
            assert attached[1] in ('m 0100 01ff', DUMPS)
            allowed = True
        if command == 'r':
            last = wire.registers(response)
        if command == 'x':
            last = None
        match = re.fullmatch(r'(bsave|dump) "([^"\n]+)"( 0 0000 ffff)?', command)
        if match:
            kind, filename, suffix = match.groups()
            path = Path(filename)
            assert path.parent == CASE and last is not None and rows[index - 1]['command'] == 'r'
            assert (kind == 'bsave') == (suffix is not None) and path.name not in contexts
            contexts[path.name] = dict(registers=last, sequence=row['sequence'])
            allowed = True
        assert allowed, command
    assert len(rows) == 153 and len(contexts) == 22 and len(rejected) == 3
    speed_queries = [r for r in rows if r['command'] == 'resourceget "Speed"']
    assert len(speed_queries) == 2 and all(r['response'].split('(C:')[0].strip() == 'Speed=100' for r in speed_queries)
    return contexts, dict(ordinary_commands=153, rejected_read_only_queries=rejected,
        interrupted_resumes=[], snapshot_restores=[], later_manual_CPU_RAM_register_writes=[],
        startup='Declared PRG autostart mode1 loader injection; original disk boot is not claimed.',
        speed_query_sequences=[r['sequence'] for r in speed_queries],
        runtime_warp_observed=False,
        InitialWarpMode_interpretation='Retained startup resource only; not proof of current runtime warp state.')


def captures(reader, contexts):
    decoded = {}
    for path in sorted(CASE.glob('*.vsf')):
        registers = contexts[path.name]['registers']
        ram_path = path.with_suffix('.bin')
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
        decoded[path.stem] = dict(ram=ram, state=state, entry=dict(stem=path.stem, ram=artifact(ram_path),
            snapshot=artifact(path), registers=registers, paired_RAM_CPU_ports_clock_beam_equal=True))
    assert len(decoded) == 11
    program = PROGRAM.read_bytes()
    assert decoded['start']['entry']['registers']['pc'] == 0x080d
    assert decoded['start']['ram'][0x0801:0x0801 + len(program) - 2] == program[2:]
    assert program[2 + 0x957a - 0x0801:2 + 0x957d - 0x0801] == bytes.fromhex('20 00 a0')
    return decoded


def spans_from_raw(case, reference, layout, sequence, before, complete):
    raw = case['responses'][sequence]['response'].replace('\r\n', '\n')
    assert case['responses'][sequence]['command'] == 'x'
    headers = list(layout.TRACE.finditer(raw))
    spans = []
    for index, match in enumerate(headers):
        if int(match['pc'], 16) != 0xa000:
            continue
        assert match['kind'] == 'exec' and int(match['target'], 16) == 0xa000
        chunk = raw[match.end():headers[index + 1].start() if index + 1 < len(headers) else len(raw)]
        assert chunk.startswith('Executing: ' + DUMPS + '\n')
        memory = {}
        for line in reference.MEMORY.finditer(chunk):
            address = int(line[1], 16)
            for offset, value in enumerate(bytes.fromhex(line[2])):
                assert address + offset not in memory
                memory[address + offset] = value
        required = set(range(0x100, 0x200)) | set(range(0x0b, 0x30)) | set(range(0xb43b, 0xb442))
        assert set(memory) == required and len(memory) == 300
        sp = int(match['sp'], 16)
        stored_return = memory[0x100 + ((sp + 1) & 255)] + 256 * memory[0x100 + ((sp + 2) & 255)]
        assert stored_return + 1 == 0x957d
        x0, x1, delta, direction_byte, error, extent, shade0 = [memory[i] for i in range(0xb43b, 0xb442)]
        assert direction_byte in (1, 255)
        direction = 1 if direction_byte == 1 else -1
        y, draw = memory[47], memory[11]
        assert 0 <= x0 <= x1 < 160 and 0 <= y < 100 and extent == x1 - x0 and error == 0
        assert 0 <= shade0 <= 32 and 0 <= shade0 + direction * delta <= 32
        assert draw == before['ram'][11]
        base = 0x6000 if draw == 0 else 0x2000
        row = base + (y // 4) * 320 + 2 * (y % 4)
        assert memory[37] + 256 * memory[38] == row and memory[39] + 256 * memory[40] == row + 1
        assert (memory[41], memory[42]) == (x0, x1)
        clock = int(match['clock'])
        assert before['entry']['registers']['clock'] < clock < complete['entry']['registers']['clock']
        spans.append(dict(index=len(spans), response_sequence=sequence, clock=clock,
            line=int(match['line']), raw_cycle=int(match['cycle']), x0=x0, x1=x1, y=y,
            delta=delta, direction=direction, error0=error, extent=extent, shade0=shade0,
            shade1=shade0 + direction * delta, drawbuf=draw, row0=row, row1=row + 1,
            stack_pointer=sp, actual_saved_return_word=stored_return, actual_return_target=stored_return + 1,
            observed_faceidx_byte=memory[13],
            observed_face_id_latch=memory[12],
            stack_dump=bytes(memory[i] for i in range(0x100, 0x200)).hex(),
            zero_page_dump=bytes(memory[i] for i in range(0x0b, 0x30)).hex(),
            span_ABI_dump=bytes(memory[i] for i in range(0xb43b, 0xb442)).hex()))
    assert spans and len(spans) == len(re.findall(r'^#\d+ \(Trace\s+exec a000\)', raw, re.M))
    assert all(a['clock'] < b['clock'] for a, b in zip(spans, spans[1:]))
    return spans


def clear_outcome(decoded, third_spans, reference):
    first = decoded['first-complete']['ram'][0x2000:0x2000 + 8000]
    begin, shades = decoded['third-begin'], decoded['third-shades']
    before, after = begin['ram'][0x2000:0x2000 + 8000], shades['ram'][0x2000:0x2000 + 8000]
    assert begin['ram'][11] == shades['ram'][11] == 1
    assert first == before and any(before) and not any(after)
    stale_ram = bytearray(shades['ram'])
    stale_ram[0x2000:0x2000 + 8000] = before
    wrong = reference.scalar(dict(ram=stale_ram, state=shades['state']), third_spans)
    actual = decoded['third-complete']['ram'][0x2000:0x2000 + 8000]
    differences = reference.differences(wrong['bitmap'], actual)
    assert differences > 0
    return dict(previous_B_complete=decoded['first-complete']['entry'], third_begin=begin['entry'],
        third_shades=shades['entry'], bitmap_base=0x2000, bytes_compared=8000,
        first_completed_equals_third_begin=True, nonzero_bytes_before=sum(v != 0 for v in before),
        nonzero_bytes_after=sum(v != 0 for v in after), omitted_clear_control_different_bytes=differences,
        before_sha256=sha(before), after_sha256=sha(after),
        scope='Observed B-buffer reuse and clear outcome for this one third render, not independent verification of every dirty range/store or the general clearing algorithm.')


def main():
    for relative, digest in PINS.items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
    OUT.mkdir(parents=True, exist_ok=True)
    reference = load('frozen_gouraud_scalar_reference', 'research/3dvibe64-native/pixels.py')
    reference.OUT = OUT
    reader = load('profile_pixel_reader', 'research/quondam/snapshot_state.py')
    layout = load('profile_pixel_layout', 'research/anomaly/scanout.py')
    wire, case, adapter = wire_case()
    contexts, commands = command_audit(wire, case)
    decoded = captures(reader, contexts)
    assert [decoded[n + '-begin']['ram'][11] for n in ('first', 'second', 'third', 'fourth')] == [1, 0, 1, 0]
    samples, span_sets = [], []
    build = json.loads((ROOT / 'build/research/3dvibe64-native/build-analysis/build-proof.json').read_text())
    asm = (ROOT / 'build/research/3dvibe64-native/build-01/products/3Dvibe64.asm').read_text()
    for literal in ('mode4_current_face_id = $0c', 'sortj = $51', 'MODE4_FACE_ID_LATCH = $01',
                    'MESH_SOURCE_SHARING_RUNTIME = $00', 'CONSERVATIVE_FACE_CULL = $01',
                    'CONSERVATIVE_CULL_NEG_AREA = $20', 'CONSERVATIVE_EDGE_CULL_NEG_AREA = $60'):
        assert literal in asm
    workspace = []
    for name, sequence in [('first', 98), ('second', 119), ('third', 140)]:
        before, complete = decoded[name + '-shades'], decoded[name + '-complete']
        assert decoded[name + '-begin']['entry']['registers']['pc'] == 0x08cb
        spans = spans_from_raw(case, reference, layout, sequence, before, complete)
        accepted, _, _ = reference.sample(name, before, complete, spans, 985248)
        accepted.update(preclear_begin=decoded[name + '-begin']['entry'],
            actual_stack_return_checked_for_every_span=True, preview_scope='Decoded completed bitmap; this cost-profile case adds no committed-VIC pixel comparison.')
        samples.append(accepted)
        span_sets.append(spans)
        aliases = build['active_runtime_aliases']
        ram = complete['ram']
        groups = []
        for span in spans:
            face_id = span['observed_face_id_latch']
            assert 0 <= face_id < 8
            if not groups or groups[-1]['source_latched_face_id'] != face_id:
                groups.append(dict(source_latched_face_id=face_id, first_span=span['index'], spans=0,
                                   pixel_writes=0, min_width=160, max_width=0))
            group = groups[-1]
            width = span['extent'] + 1
            group['spans'] += 1
            group['pixel_writes'] += width
            group['min_width'], group['max_width'] = min(group['min_width'], width), max(group['max_width'], width)
            group['last_span'] = span['index']
        workspace.append(dict(frame=name, faceidx_0D_counts={str(v): sum(s['observed_faceidx_byte'] == v for s in spans)
            for v in sorted({s['observed_faceidx_byte'] for s in spans})},
            actual_face_id_latch_address=0x0c, contiguous_span_face_id_groups=groups,
            sx=list(ram[aliases['sx']:aliases['sx'] + 6]), sy=list(ram[aliases['sy']:aliases['sy'] + 6]),
            syQ2=[ram[aliases['syq2_lo'] + i] + 256 * ram[aliases['syq2_hi'] + i] for i in range(6)],
            lazy_projection_done_flags=list(ram[aliases['projdone']:aliases['projdone'] + 6]),
            scope='The source face-ID latch at0C identifies actual span groups. Collector faceidx0D=8 does not. Projected arrays are raw endpoint workspace and unprojected entries may be stale. No correct visible-face count or independent projection/culling result is inferred.'))
    clear = clear_outcome(decoded, span_sets[2], reference)
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()), inputs=[artifact(ROOT / p) for p in PINS],
        native_case_directory_sha256=CASE_SHA, wire=wire.summary(case), startup_adapter=adapter,
        command_audit=commands, RAM_snapshot_pairs=11, full_RAM_bytes_compared=11 * 65536,
        generated_PRG_loaded_payload_exact=True,
        reference_reuse=dict(path='research/3dvibe64-native/pixels.py', source_unchanged=True,
            functions=['scalar', 'logical_colors', 'expand', 'preview', 'sample'], output_root_only_redirected=str(OUT.relative_to(ROOT)),
            new_parser_scope='Raw trace blocks permit exactly the300-byte full-stack+zero-page+span ABI set. Every actual saved return must point to957D.'),
        checkpoints=[capture['entry'] for capture in decoded.values()], accepted_samples=samples,
        third_buffer_clear_outcome=clear, draw_identity_observations=workspace,
        conservative_culling_context=dict(enabled=True, negative_area_tolerance=0x20, edge_tolerance=0x60,
            scope='Pinned emitted constants provide possible context for conservative edge-on work; the exact extra draw-call cause is not established.'),
        final_continuation=decoded['fourth-begin']['entry'],
        limitations=['This reuses the frozen independent scalar reference from accepted actual span inputs; geometry, clipping, culling, edge shade construction and full lighting transforms remain outside the oracle.',
            'All three complete bitmap and palette arrays are checked. This case adds no committed VIC raster crop and no physical-hardware or FPS claim.',
            'The third B-buffer clearing result is a captured endpoint outcome, not proof of every dirty-tracking path or absence of transient writes.',
            'Cost partitioning and native event/return pairing are a separate producer; this checker verifies the pixels of the actual profiled frame inputs.'])
    result['pass'] = result.pop('pass_')
    receipt = save('profile-pixels-proof.json', result)
    (OUT / 'check_pixels.checked.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(pass_=True, frames=[dict(name=s['name'], spans=s['span_count'], pixel_writes=s['pixel_writes'],
        bitmap_differences=s['bitmap_differences'], palette_differences=s['screen_differences'] + s['color_RAM_differences']) for s in samples],
        clear_nonzero_before=clear['nonzero_bytes_before'], clear_nonzero_after=clear['nonzero_bytes_after'], receipt=receipt), indent=2))


if __name__ == '__main__':
    main()
