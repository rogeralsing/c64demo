#!/usr/bin/env python3
"""Decode literal Colors first-display pixels from existing native captures.

No CPU, emulator, process or monitor is started. This is independent of the
first_display.py helper interpretation: it reads real RAM, monochrome glyphs,
sprite masks and palette ownership. It is not an analog PAL/CRT color model.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import tarfile
from PIL import Image

from native_capture import contexts, physical_ram, read_snapshot, module_payload

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/colors'
FIRST_SHA = 'd03eee9b41f9142ac459609966b2396d77ec134fb1e055d2bf521aff0679e34f'
SOURCES = (0x96c0, 0x9700, 0x9740)
PHASES = {
    0:dict(font=0x2800, pointers=(0x8c, 0x8d), colors=(2, 5)),
    1:dict(font=0x3000, pointers=(0x8c, 0x8e), colors=(5, 2)),
    2:dict(font=0x3800, pointers=(0x8d, 0x8e), colors=(2, 5)),
}
TRACE = re.compile(
    r'^#(?P<checkpoint>\d+) \(Trace store (?P<target>[0-9a-f]{4})\)\s+'
    r'(?P<line>\d+)/\$[0-9a-f]+,\s+(?P<cycle>\d+)/\$[0-9a-f]+\n'
    r'\.C:(?P<pc>[0-9a-f]+)\s+[^\n]*?'
    r'- A:(?P<a>[0-9a-f]+) X:(?P<x>[0-9a-f]+) Y:(?P<y>[0-9a-f]+) '
    r'SP:(?P<sp>[0-9a-f]+) [^\n]*?\s+(?P<clock>\d+)\n', re.M | re.I)
VICE_SHA = '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def palette():
    path = ROOT/'palettes/colodore.vpl'
    colors = []
    for line in path.read_text().splitlines():
        match = re.match(r'^\s*([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})(?:\s|$)', line, re.I)
        if match:
            colors.append(tuple(int(v,16) for v in match.groups()))
    assert len(colors) == len(set(colors)) == 16
    return colors, dict(path=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()))


def png(indices, width, height, colors, path):
    image = Image.new('P', (width, height))
    image.putpalette([v for color in colors for v in color]+[0]*(768-48))
    image.putdata(indices)
    image.save(path)


def literal_masks(first):
    records = []
    planes = []
    for residue, address in enumerate(SOURCES):
        expected = bytearray(63)
        for y in range(21):
            for x in range(24):
                if (x+y)%3 == residue:
                    expected[3*y+x//8] |= 0x80>>(x&7)
        assert first[address:address+63] == expected
        records.append(dict(source=address, bytes=63, sha256=sha(expected),
                            independent_formula=f'(local_x + local_y) % 3 == {residue}', ones=sum(v.bit_count() for v in expected)))
        planes.append(expected)
    assert all((a & b) == (a & c) == (b & c) == 0 and (a | b | c) == 255 for a,b,c in zip(*planes))
    cycles = {0:[2,5,6], 1:[5,6,2], 2:[6,2,5]}
    return planes, dict(masks=records, each_plane_bits=168, disjoint=True,
                        union_covers_all504_sprite_pixels=True,
                        local_residue_color_over_phases=cycles,
                        scope='Literal diagonal sprite-mask classes and relative three-phase palette. Not three complete monochrome RGB scanlines or a perceived-color measurement.')


def timing_sources(output):
    archive_path = ROOT/'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    assert sha(archive_path.read_bytes()) == VICE_SHA
    ranges = {
        'src/c64/c64cia2.c':[(61,74),(136,155),(307,310)],
        'src/core/ciacore.c':[(783,809)],
        'src/c64/c64gluelogic.c':[(51,107),(169,193)],
        'src/c64/c64memsc.c':[(959,963)],
        'src/viciisc/vicii.c':[(125,132),(365,375)],
        'src/6510dtvcore.c':[(479,481),(1734,1736)],
        'src/c64/c64cpusc.c':[(47,51)],
        'src/viciisc/vicii-cycle.c':[(130,141),(382,402),(541,563)],
        'src/viciisc/vicii-chip-model.c':[(142,220),(805,809)],
        'src/viciisc/vicii-fetch.c':[(50,73),(158,181),(234,270)],
        'src/viciisc/vicii-draw-cycle.c':[(133,142),(342,410)],
    }
    records = []
    with tarfile.open(archive_path) as archive:
        for relative, line_ranges in ranges.items():
            member = 'vice-3.10/'+relative
            data = archive.extractfile(member).read()
            target = output/'hardware-source'/relative
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(data)
            records.append(dict(member=member,sha256=sha(data),line_ranges=line_ranges))
    monitor_proof = ROOT/'build/research/vice-trace-timing/source-proof.json'
    return dict(archive_sha256=VICE_SHA,members=records,
                monitor_boundary_source_proof=dict(path=str(monitor_proof.relative_to(ROOT)),sha256=sha(monitor_proof.read_bytes())),
                formula='Glyph column N fetches at raw cycle15+N. The STA callback is at T−1, after current Phi1. The first changed fetch is at raw T. Custom GLUE type1 bank1→2 exposes bank3 for that fetch; the alarm restores bank2 before the next fetch.',
                no_PNG_fitted_timing_parameter=True)


def trace_history(log, ram, first_clock, last_clock, phase):
    events = []
    for match in TRACE.finditer(log):
        fields = match.groupdict()
        item = {k:int(v,16 if k in ('target','pc','a','x','y','sp') else 10) for k,v in fields.items()}
        if first_clock < item['clock'] < last_clock:
            opcode = ram[item['pc']]
            if item['target'] == 0xd019:  # IRQ-ack RMW events retained, not palette values.
                item['value'] = None
            else:
                assert opcode in (0x8c,0x8d,0x8e)
                assert int.from_bytes(ram[item['pc']+1:item['pc']+3],'little') == item['target']
                item['value'] = item[{0x8c:'y',0x8d:'a',0x8e:'x'}[opcode]]
            events.append(item)
    banks = [event for event in events if event['target'] == 0xdd02]
    assert len(banks) == 4 and [event['value'] for event in banks] == [0x3c,0x3d,0x3e,0x3f]
    assert [event['line'] for event in banks] == [4,102,150,198]
    for event in banks:
        event['bank'] = (event['value']&3)*0x4000
        event['STA_final_Phi2_clock'] = event['clock']-1
        # Custom GLUE type1 exposes temporary bank3 on 1→2 for the next
        # Phi1 fetch. The alarm restores final2 after that fetch, before
        # the next instruction. This comes from the pinned source branch.
        event['temporary_first_fetch_bank'] = 0xc000 if event['value'] == 0x3e else None
    frame_clock = banks[0]['clock']-63*banks[0]['line']-banks[0]['cycle']
    assert all(event['clock'] == frame_clock+63*event['line']+event['cycle'] for event in banks)
    # Constant canvas state must follow the actual store history, not late
    # register inference. Sprite Y rewrites are allowed during the canvas.
    fixed = [event for event in events if event['target'] in (0xd011,0xd016,0xd017,0xd01b,0xd01c,0xd01d,0xd021)]
    assert not [event for event in fixed if 55 <= event['line'] <= 246]
    d018 = [event for event in events if event['target'] == 0xd018]
    assert len(d018) == 1 and d018[0]['line'] < 55 and d018[0]['value'] == (0x9a+2*phase)
    assert not [event for event in events if 55 <= event['line'] <= 246 and
                (event['target'] in (0xd000,0xd002,0xd004,0xd006,0xd008,0xd00a,0xd00c,0xd00e,0xd010) or 0xd027 <= event['target'] <= 0xd02e)]
    y_writes = [event for event in events if event['target'] == 0xd001]
    assert [event['value'] for event in y_writes] == [54,75,96,117,138,159,180,201,222,243]
    return dict(events=events, bank_events=banks, frame_start_clock=frame_clock,
                source_derived_first_new_glyph_columns=[event['cycle']-15 for event in banks[1:]],
                scope='Native store history. STA final Phi2 is monitor boundary−1; current-cycle Phi1 already happened. Custom GLUE exposes temporary3 for the first changed1→2 fetch, then final2.')


def decode(ram, vic, phase, history):
    """Literal text fetches, cached matrix codes, and repeated mono sprites."""
    config = PHASES[phase]
    registers = vic['regs']
    xs = [registers[2*i]+(256 if registers[0x10]&(1<<i) else 0)+8 for i in range(8)]
    output, ownership = bytearray(), Counter()
    for y in range(192):
        raster = 55+y
        global_row, glyph_row = divmod(y, 8)
        matrix_bank = (global_row//6)*0x4000
        sprite_row = y%21  # Y targets54,75,...; left-area pixels begin on the next raster.
        for x in range(320):
            physical_x = 32+x
            column, glyph_x = divmod(x, 8)
            # Matrix codes were fetched on the row's earlier badline and
            # remain cached. Midline bank writes change later glyph fetches,
            # not that already cached character code.
            code = ram[matrix_bank+0x2400+global_row*40+column]
            fetch_clock = history['frame_start_clock']+63*raster+15+column
            bank_event = max((event for event in history['bank_events'] if event['STA_final_Phi2_clock'] < fetch_clock),
                             key=lambda event:event['clock'])
            bank = bank_event['bank']
            if bank_event['temporary_first_fetch_bank'] is not None and fetch_clock == bank_event['clock']:
                bank = bank_event['temporary_first_fetch_bank']
            glyph = ram[bank+config['font']+8*code+glyph_row]
            foreground = bool(glyph & (0x80>>glyph_x))
            # Choose the lowest numbered opaque sprite first, then apply
            # sprite/graphics priority. Do not skip an occluded lower sprite
            # to reveal a higher numbered one.
            sprite = None
            for i in range(8):
                sx = physical_x-xs[i]
                if 0 <= sx < 24:
                    pointer = config['pointers'][i//4]
                    bits = ram[bank+pointer*64+3*sprite_row+sx//8]
                    if bits & (0x80>>(sx&7)):
                        sprite = i
                        break
            if foreground:
                color, owner = vic['color_ram'][global_row*40+column]&15, 'character_foreground'
            elif sprite is not None:
                color, owner = config['colors'][sprite//4], f'sprite_{sprite}'
            else:
                color, owner = 6, 'D021_background'
            output.append(color)
            ownership[owner] += 1
    return bytes(output), dict(physical_canvas=[32,55,320,192], PNG_canvas=[32,39,320,192],
                               sprite_physical_x=xs, ownership=dict(ownership),
                               assumptions=['No FLD in warmed steady path; rows55..246, RC0..7.',
                                            'Matrix code cached on each row badline; actual midline bank events select each later glyph fetch.',
                                            'Unexpanded hires sprites, repeated21-line patterns, all behind character foreground.',
                                            'D021=6 during canvas; late register values are not substituted for raster history.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,default=BASE/'native-01')
    parser.add_argument('--output',type=Path,default=BASE/'first-display-pixels')
    parser.add_argument('--allow-live',action='store_true')
    args = parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=True)
    first = (args.capture/'ram-first-entry.bin').read_bytes()
    assert len(first) == 65536 and sha(first) == FIRST_SHA
    planes, assets = literal_masks(first)
    colors, palette_record = palette()
    session = json.loads((args.capture/'session.json').read_text())
    assert args.allow_live or session.get('closed_utc'), 'Final receipt requires owner-closed session.'
    log = (args.capture/'monitor.log').read_text(errors='replace')
    events = {e['filename']:e for e in contexts(log)}
    records, predictions = [], []
    previous_clock = events['stable-field-d.vsf']['registers']['clock']
    for suffix in 'abc':
        stem = f'traced-field-{suffix}'
        raw, vsf, screenshot = (args.capture/f'ram-{stem}.bin', args.capture/f'{stem}.vsf', args.capture/f'{stem}.png')
        ram, state = raw.read_bytes(), read_snapshot(vsf)
        registers = events[vsf.name]['registers']
        assert events[raw.name]['registers'] == events[screenshot.name]['registers'] == registers
        assert registers['pc'] == 0x8e4e and registers['raster_line'] == 4
        assert ram == physical_ram(vsf) and len(ram) == 65536
        cpu = module_payload(vsf,'MAINCPU')
        assert int.from_bytes(cpu[:8],'little') == registers['clock'] and int.from_bytes(cpu[12:14],'little') == registers['pc']
        vic, cia = state['vicii'], state['cia']['CIA2']
        assert (vic['raster_line'],vic['raster_cycle']) == (registers['raster_line'],registers['raster_cycle'])
        assert cia['pra'] == 0xf8 and cia['ddra'] == 0x3f
        assert state['modules']['GLUE']['version'] == [1,0] and module_payload(vsf,'GLUE') == bytes((1,3,0))
        assert all(vic['regs'][offset] == value for offset,value in ((0x11,0x17),(0x15,255),(0x16,8),(0x17,0),(0x1b,255),(0x1c,0),(0x1d,0),(0x21,6)))
        assert set(vic['color_ram']) == {0} and ram[0x8443] == 63
        phase = ram[0x8046]
        assert phase in PHASES
        config = PHASES[phase]
        assert (vic['regs'][0x18]&0xfe) == 0x90+((config['font']//0x400)&14)
        for bank_index in range(4):
            bank = bank_index*0x4000
            for local_row in range(6):
                for column in range(40):
                    address = bank+0x2400+(bank_index*6+local_row)*40+column
                    assert ram[address] == 6*column+local_row
            for font in (0x2800,0x3000,0x3800):
                assert ram[bank+font:bank+font+1920] == first[bank+font:bank+font+1920]
            for residue in range(3):
                address = bank+0x2300+64*residue
                assert ram[address:address+63] == planes[residue]
            assert ram[bank+0x27f8:bank+0x2800] == bytes([config['pointers'][0]]*4+[config['pointers'][1]]*4)
        assert vic['regs'][0x27:0x2f] == [config['colors'][0]]*4+[config['colors'][1]]*4
        history = trace_history(log,ram,previous_clock,registers['clock'],phase)
        previous_clock = registers['clock']
        expected, geometry = decode(ram, vic, phase,history)
        predictions.append(expected)
        predicted_path = args.output/f'{stem}-predicted.png'
        png(expected,320,192,colors,predicted_path)
        (args.output/f'{stem}-predicted-indices.bin').write_bytes(expected)
        image = Image.open(screenshot).convert('RGB')
        actual_crop = image.crop((32,39,352,231))
        inverse = {color:index for index,color in enumerate(colors)}
        rgb_bytes = actual_crop.tobytes()
        actual = bytes(inverse[tuple(rgb_bytes[i:i+3])] for i in range(0,len(rgb_bytes),3))
        differences = [dict(x=i%320,y=i//320,raster=55+i//320,expected=e,actual=a) for i,(e,a) in enumerate(zip(expected,actual)) if e!=a]
        (args.output/f'{stem}-native-indices.bin').write_bytes(actual)
        records.append(dict(stem=stem,phase=phase,registers=registers,geometry=geometry,history=history,
                            raw_RAM_sha256=sha(ram),snapshot_sha256=sha(vsf.read_bytes()),PNG_sha256=sha(screenshot.read_bytes()),
                            all65536_raw_RAM_bytes_equal_snapshot=True,all23040_used_glyph_bytes_original=True,
                            all12_revealed_sprite_slots_exact=True,all1024_ColorRAM_zero=True,
                            expected_indices_sha256=sha(expected),actual_indices_sha256=sha(actual),
                            pixels=len(expected),mismatches=len(differences),first32_mismatches=differences[:32],
                            mismatch_rows=dict(Counter(d['y'] for d in differences)),exclusions=[]))
    assert [r['phase'] for r in records[1:]] == [(records[0]['phase']+i)%3 for i in (1,2)]
    triples = Counter(tuple(frame[i] for frame in predictions[:3]) for i in range(320*192))
    left = max(record['geometry']['sprite_physical_x'][0] for record in records)
    right = min(record['geometry']['sprite_physical_x'][0]+96 for record in records)
    assert left < right
    component_bits = {0:0,2:1,5:2,6:4}
    presence, examples = Counter(), {}
    for y in range(192):
        for physical_x in range(left,right):
            x = physical_x-32
            values = tuple(frame[y*320+x] for frame in predictions)
            code = 0
            for value in values:
                code |= component_bits[value]
            presence[code] += 1
            examples.setdefault(code,dict(canvas_x=x,canvas_y=y,physical_x=physical_x,raster=55+y,
                                          literal_field_colors=list(values),component_presence_code=code))
    rejected = args.output/'rejected-whole-bank-row-assumption/pixel-evidence-provisional.json'
    rejected_record = json.loads(rejected.read_text())
    assert not rejected_record['pass'] and [r['mismatches'] for r in rejected_record['fields']] == [18,15,14,23]
    result = dict(pass_=all(r['mismatches']==0 for r in records), provisional=not bool(session.get('closed_utc')),
                  script_sha256=sha(Path(__file__).read_bytes()), observed_input_RAM_sha256=FIRST_SHA,
                  transcript_sha256=sha((args.capture/'monitor.log').read_bytes()), session=session,
                  hardware_timing=timing_sources(args.output),
                  reader_sha256={path:sha((ROOT/path).read_bytes()) for path in
                                 ('research/colors/native_capture.py','research/nine/native_capture.py','research/quondam/snapshot_state.py')},
                  literal_asset_contract=assets,palette=palette_record,fields=records,
                  three_field_literal_color_triples=[dict(colors=list(k),pixels=v) for k,v in sorted(triples.items())],
                  common_sprite_window=dict(physical_x_start=left,physical_x_end_exclusive=right,rows=192,
                                            pixels=(right-left)*192,component_presence_counts=dict(presence),
                                            examples=[examples[k] for k in sorted(examples)],
                                            interpretation='Digital R/G/B component-presence codes only (R1,G2,B4), not calibrated intensity, perceived color count, or PAL/CRT averaging.'),
                  rejected_whole_bank_trial=dict(path=str(rejected.relative_to(ROOT)),sha256=sha(rejected.read_bytes()),
                                                mismatch_counts=[18,15,14,23],retained_as_rejected=True,
                                                scope='Different preceding untraced poses; their precise transition timings are not retroactively invented.'),
                  scope='Literal digital palette/owner decoding of one warmed original program. No CPU/IRQ simulation, synthetic source/clock, analog PAL/CRT blending, original image/export oracle or whole-Colors algorithm claim.')
    result['pass'] = result.pop('pass_')
    path = args.output/('pixel-evidence-provisional.json' if result['provisional'] else 'pixel-evidence.json')
    path.write_text(json.dumps(result,indent=2)+'\n')
    print('Literal first-display pixel mismatches:',[r['mismatches'] for r in records])
    assert result['pass'],f'Preserved all mismatch counts and pixel artifacts at {path}; no boundary exclusions.'


if __name__=='__main__':
    main()
