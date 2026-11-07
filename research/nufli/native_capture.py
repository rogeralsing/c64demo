#!/usr/bin/env python3
"""Compare existing Smoking Fish native captures; never control an emulator.

The primary image comparison is fixed at NUFLI's observed origin (32,32),
using exact palette RGB values. Every mismatching pixel remains in the receipt.
Only the source-identified runtime bank-byte patch at $19bc is treated specially.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

from PIL import Image

from decode_nuf import decode
from extract import ROOT, OUT

sys.path.insert(0, str(ROOT/'research/quondam'))
from snapshot_state import module_payload, read_snapshot  # noqa: E402

PROGRAM = OUT/'amigaconverts+samples/02-SMOKING_FISH.NUF.prg'
PROGRAM_SHA = 'f44e6c1c3285683d2d73864e6d676e68539b77beb3e43daabd4a22adaa929093'
GENERATOR_RAM_SHA = 'cb67dfd925869bfe7337fb045f6f827c1d243e4459655a14412ee954be91e594'
ORIGIN = (32,32)
STANDARD_ORIGIN_TRIAL_SHA = 'ed4856dde4d3ab6b601d1b32ed10b8731e9278093717e8f785672dd0134498e2'
REJECTED = {
    'attempt-quoted-keybuf-entry.vsf',
    'attempt-quoted-keybuf-ram-entry.bin',
}
REGISTER = re.compile(
    r'^\.;([0-9a-f]{4})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+'
    r'([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([01]{8})\s+(\d+)\s+(\d+)\s+(\d+)',re.I)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def contexts(text):
    current, result = None, []
    for number,line in enumerate(text.splitlines(),1):
        if line.strip() == 'x':
            current = None
        match = REGISTER.match(line.strip())
        if match:
            values = match.groups()
            current = dict(zip(('pc','a','x','y','sp','port00','port01'),
                               (int(x,16) for x in values[:7])))
            current.update(flags=int(values[7],2), raster_line=int(values[8]),
                           raster_cycle=int(values[9]), clock=int(values[10]))
        match = re.match(r'\s*(bsave|dump|screenshot|scrsh) "([^"]+)"',line)
        if match:
            assert current is not None, ('Capture without register observation',line)
            result.append(dict(filename=Path(match[2]).name,command=match[1],
                               transcript_line=number,registers=deepcopy(current)))
    return result


def captured_name(record):
    name,pc = record['filename'],record['registers']['pc']
    # The original failed capture commands used these ordinary names. Root
    # preserved those files under explicit attempt names before the valid retry.
    if pc in (0xe5cf,0xe5d1) and name in ('entry.vsf','ram-entry.bin'):
        return 'attempt-quoted-keybuf-'+name
    return name


def ram_from_snapshot(path):
    state = read_snapshot(path)
    meta = state['modules']['C64MEM']
    assert meta['version'] == [0,1] and meta['payload_size'] == 65555
    return module_payload(path,'C64MEM')[4:65540]


def exact_region(actual, expected, first, last):
    differences = [dict(address=first+i, expected=a, actual=b)
                   for i,(a,b) in enumerate(zip(expected[first:last],actual[first:last])) if a != b]
    return dict(first=first, last_exclusive=last, bytes=last-first,
                matches=(last-first)-len(differences), differences=differences,
                exact=not differences, sha256=sha(actual[first:last]))


def palette(path):
    result = [tuple(int(v,16) for v in line.split()[:3]) for line in path.read_text().splitlines()
              if line.strip() and not line.lstrip().startswith('#')]
    assert len(result) == 16 and len(set(result)) == 16
    return result


def vic_checkpoint(state):
    vic = state['vicii']
    return dict(model=vic['model'],raster_line=vic['raster_line'],raster_cycle=vic['raster_cycle'],
                ysmooth=vic['ysmooth'],vborder=vic['vborder'],main_border=vic['main_border'],
                idle_state=vic['idle_state'],rc=vic['rc'],vcbase=vic['vcbase'],
                stored_d011=vic['regs'][0x11],stored_d016=vic['regs'][0x16],stored_d018=vic['regs'][0x18])


def image_comparison(path, expected, colors, destination):
    image = Image.open(path).convert('RGB')
    assert image.size == (384,272), ('Expected PAL normal-border screenshot',image.size)
    lookup = {color:index for index,color in enumerate(colors)}
    left,top = ORIGIN
    rectangle = (left,top,left+320,top+200)
    actual_rgb = list(image.crop(rectangle).get_flattened_data())
    assert len(expected) == len(actual_rgb) == 64000
    actual = [lookup.get(color,-1) for color in actual_rgb]
    mismatches = [dict(x=i%320,y=i//320,expected=int(expected[i]),actual=value,
                       rgb=list(actual_rgb[i]))
                  for i,value in enumerate(actual) if value != expected[i]]
    unknown = Counter(actual_rgb[i] for i,value in enumerate(actual) if value == -1)
    # This diagnostic marks every mismatch; no area is cropped away to pass.
    diff = Image.new('RGB',(320,200),(0,0,0))
    for point in mismatches:
        diff.putpixel((point['x'],point['y']),(255,0,255))
    diff_path = destination/(path.stem+'-difference.png'); diff.save(diff_path)
    image.crop(rectangle).save(destination/(path.stem+'-crop.png'))
    nonblack = [(x,y) for y in range(image.height) for x in range(image.width)
                if image.getpixel((x,y)) != colors[0]]
    bounds = [min(x for x,y in nonblack),min(y for x,y in nonblack),
              max(x for x,y in nonblack)+1,max(y for x,y in nonblack)+1]
    by_row, by_column = Counter(p['y'] for p in mismatches), Counter(p['x'] for p in mismatches)
    return dict(file=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()),
                dimensions=list(image.size), fixed_bitmap_origin=list(ORIGIN),
                native_bitmap_rgb_sha256=sha(bytes(v for color in actual_rgb for v in color)),
                full_frame_nonblack_bounds=bounds,
                exact_pixels=64000-len(mismatches), mismatch_count=len(mismatches),
                exact=not mismatches, unknown_rgb=[dict(rgb=list(k),count=v) for k,v in unknown.items()],
                mismatches=mismatches, mismatches_by_row=dict(sorted(by_row.items())),
                mismatches_by_column=dict(sorted(by_column.items())),
                regions={name:sum(1 for p in mismatches if lo <= p['x'] < hi)
                         for name,lo,hi in (('left_flibug',0,24),('normal_underlay',24,312),('right_no_sprite',312,320))},
                difference_image=str(diff_path.relative_to(ROOT)),
                border_comparison='Outside320x200 is not part of the image oracle; no rasterbar/border claim')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture','--session',dest='capture',type=Path,default=OUT/'native-02')
    parser.add_argument('--output',type=Path,default=OUT/'native-analysis')
    parser.add_argument('--palette',type=Path,default=ROOT/'palettes/colodore.vpl')
    args = parser.parse_args()
    directory, destination = args.capture.resolve(), args.output.resolve()
    session = json.loads((directory/'session.json').read_text())
    assert session.get('closed_utc'), 'Analyze a closed captured session, not a partial live log.'
    transcript_path = directory/'monitor.log'
    context = contexts(transcript_path.read_text(errors='replace'))
    program = PROGRAM.read_bytes()
    assert sha(program) == PROGRAM_SHA and len(program) == 23042
    generator = json.loads((OUT/'generator-validation.json').read_text())
    reference = next(row for row in generator['files'] if row['prg_sha256'] == PROGRAM_SHA)
    generated = (OUT/'02-SMOKING_FISH.NUF-generated.ram').read_bytes()
    assert len(generated) == 65536 and sha(generated) == GENERATOR_RAM_SHA
    assert sha(generated[0x1000:0x1f42]) == reference['generated_sha256']
    logical,owners,_,uncovered = decode(program)
    assert uncovered == 0
    decode_receipt = json.loads((OUT/'decode-validation.json').read_text())
    expected_hash = next(row['indices_sha256'] for row in decode_receipt['files'] if row['prg_sha256'] == PROGRAM_SHA)
    assert sha(logical) == expected_hash
    destination.mkdir(parents=True,exist_ok=True)
    records, snapshots, images, rejected = [], {}, [], []
    for record in context:
        name = captured_name(record)
        path = directory/name
        assert path.exists(), ('Missing captured file',name)
        if name in REJECTED:
            assert record['registers']['pc'] in (0xe5cf,0xe5d1)
            rejected.append(dict(file=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()),
                                 registers=record['registers'],used_for_display_proof=False,
                                 transcript_filename=record['filename'],transcript_line=record['transcript_line'],
                                 reason='Monitor keybuf quotes were typed literally: BASIC syntax error, not a viewer entry. Raw unquoted SYS12288 retry is separate.'))
            continue
        if record['command'] == 'dump':
            state = read_snapshot(path)
            actual_clock = int.from_bytes(module_payload(path,'MAINCPU')[:8],'little')
            assert actual_clock == record['registers']['clock']
            key = (record['registers']['pc'],actual_clock)
            snapshots[key] = (path,state)
    for record in context:
        name = captured_name(record)
        if name in REJECTED:
            continue
        path, register = directory/name,record['registers']
        if record['command'] == 'bsave':
            actual = path.read_bytes(); assert len(actual) == 65536
            pc = register['pc']
            if pc == 0x3000:
                loaded = bytearray(65536); loaded[0x2000:0x7a00] = program[2:]
                regions = [exact_region(actual,loaded,0x2000,0x7a00)]
                phase = 'original_entry'
            elif pc == 0x3109:
                regions = [exact_region(actual,generated,a,b) for a,b in
                           ((0x1000,0x1f42),(0x2000,0x7a00),(0x280,0x2a8),
                            (0x3f8,0x400),(0x7f8,0x800),(0x7ff8,0x8000))]
                phase = 'after_generator_before_irq'
            elif pc in (0x3110,0x31e0):
                regions = [exact_region(actual,generated,a,b) for a,b in
                           ((0x1000,0x19bc),(0x19bd,0x1f42),(0x2000,0x7a00))]
                assert actual[0x19bc] & 3 == 3, 'Runtime bank patch must select VIC bank0.'
                phase = 'frame_checkpoint'
            else:
                raise AssertionError(('Unclassified raw RAM checkpoint',name,hex(pc)))
            key = pc,register['clock']
            assert key in snapshots, ('No same-stop VSF for rawRAM',name)
            snapshot_path,state = snapshots[key]
            assert ram_from_snapshot(snapshot_path) == actual, 'All65536 RAM bytes must agree with VSF.'
            records.append(dict(file=str(path.relative_to(ROOT)),sha256=sha(actual),phase=phase,
                                registers=register,regions=regions,exact=all(r['exact'] for r in regions),
                                runtime_bank_patch=(dict(address=0x19bc,reference=generated[0x19bc],actual=actual[0x19bc],
                                                         semantics='Upper CIA2 port bits preserved; lowbits3 selects VICbank0')
                                                    if phase=='frame_checkpoint' else None),
                                snapshot=str(snapshot_path.relative_to(ROOT)),snapshot_sha256=state['file_sha256'],
                                vic_checkpoint=vic_checkpoint(state),
                                vic_raster=[state['vicii']['raster_line'],state['vicii']['raster_cycle']]))
        elif record['command'] in ('screenshot','scrsh'):
            assert register['pc'] in (0x3110,0x31e0), ('PNG outside a completed-display checkpoint',name)
            key = register['pc'],register['clock']
            assert key in snapshots, ('No same-stop VSF for PNG',name)
            comparison = image_comparison(path,logical,palette(args.palette),destination)
            snapshot_path,state = snapshots[key]
            comparison.update(registers=register,snapshot=str(snapshot_path.relative_to(ROOT)),
                              snapshot_sha256=state['file_sha256'],vic_checkpoint=vic_checkpoint(state),
                              vic_raster=[state['vicii']['raster_line'],state['vicii']['raster_cycle']])
            if register['pc'] == 0x3110:
                assert state['vicii']['vborder'] == 0 and state['vicii']['ysmooth'] == 0
            images.append(comparison)
    assert any(r['phase']=='original_entry' for r in records)
    assert any(r['phase']=='after_generator_before_irq' for r in records)
    assert any(r['phase']=='frame_checkpoint' for r in records) and images
    image_intervals = []
    ordered_images = sorted(images,key=lambda row:row['registers']['clock'])
    for first,second in zip(ordered_images,ordered_images[1:]):
        a,b = first['registers'],second['registers']
        delta = b['clock']-a['clock']
        position_delta = 63*(b['raster_line']-a['raster_line'])+b['raster_cycle']-a['raster_cycle']
        remainder = delta-position_delta
        image_intervals.append(dict(first=first['file'],second=second['file'],raw_cycles=delta,
                                    raster_position_delta=position_delta,pal_periods=remainder//19656,
                                    exactly_pal_aligned=(remainder % 19656 == 0)))
    failed_launch = None
    failed_directory = OUT/'native-01'
    if directory != failed_directory.resolve() and (failed_directory/'session.json').exists():
        failed_session = json.loads((failed_directory/'session.json').read_text())
        assert failed_session.get('closed_utc')
        artifacts = [failed_directory/'session.json',failed_directory/'monitor.log',
                     *(failed_directory/name for name in sorted(REJECTED))]
        assert all(path.exists() for path in artifacts)
        failed_launch = dict(session=failed_session,used_for_display_proof=False,
                             reason='Failed BASIC input launch: quoted keybuf and uppercase PETSCII attempts; no successful viewer entry captured. Fresh native02 uses normal lowercase SYS input.',
                             artifacts=[dict(file=str(p.relative_to(ROOT)),sha256=sha(p.read_bytes())) for p in artifacts])
    result = dict(program_sha256=PROGRAM_SHA,script_sha256=sha(Path(__file__).read_bytes()),
                  snapshot_reader_sha256=sha((ROOT/'research/quondam/snapshot_state.py').read_bytes()),
                  generator_receipt_sha256=sha((OUT/'generator-validation.json').read_bytes()),
                  generated_reference_ram_sha256=GENERATOR_RAM_SHA,
                  logical_decoder_sha256=sha((ROOT/'research/nufli/decode_nuf.py').read_bytes()),
                  transcript_sha256=sha(transcript_path.read_bytes()),session=session,
                  palette=dict(file=str(args.palette.resolve().relative_to(ROOT)),sha256=sha(args.palette.read_bytes())),
                  original_generator_code_bytes=3906,logical_indices_sha256=sha(logical),ownership=owners,
                  ram_captures=records,images=images,
                  screenshot_clock_intervals=image_intervals,
                  repeated_native_bitmap_identical=(len({r['native_bitmap_rgb_sha256'] for r in images})==1 if len(images)>1 else None),
                  exact_byte_checks_pass=all(r['exact'] for r in records),
                  exact_full_image_match=all(r['exact'] for r in images),
                  rejected_observations=rejected,
                  earlier_failed_launch=failed_launch,
                  scope='Captured original NUF in native VICE; fixed full-image comparison. No physical-machine/NTSC/border/all-picture claim.')
    standard_trial = destination/'standard-origin-trial/native-comparison.json'
    assert sha(standard_trial.read_bytes()) == STANDARD_ORIGIN_TRIAL_SHA
    result['rejected_standard_origin_assumption'] = dict(
        receipt=str(standard_trial.relative_to(ROOT)),sha256=STANDARD_ORIGIN_TRIAL_SHA,
        origin=[32,35],mismatches_per_capture=39372,used_as_final_image_origin=False,
        correction='Normal bitmap y51 was the wrong NUFLI origin. The native nonblack image spans PNG y32..231 (raster48..247), consistent with the viewer YSCROLL0/first-DMA-line setup. Fixed NUFLI origin32,32 compares all64000pixels, without exclusions or offset minimization.')
    origin_path = ROOT/'build/research/quondam/hardware-source/nufli-origin-proof.json'
    origin_proof = json.loads(origin_path.read_text())
    assert origin_proof['status'] == 'pass'
    for observation in origin_proof['observations']:
        assert sha((ROOT/observation['png']).read_bytes()) == observation['png_sha256']
        assert sha((ROOT/observation['snapshot']).read_bytes()) == observation['snapshot_sha256']
        assert observation['png_rgb_mismatches'] == 0
        assert observation['png_nonblack_bounds_exclusive'] == [32,32,352,232]
    result['independent_origin_geometry'] = dict(
        receipt=str(origin_path.relative_to(ROOT)),sha256=sha(origin_path.read_bytes()),
        formula=origin_proof['formula'],explanation=origin_proof['explanation'])
    output = destination/'native-comparison.json'
    output.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(exact_byte_checks_pass=result['exact_byte_checks_pass'],
                          screenshots=[dict(file=r['file'],mismatches=r['mismatch_count'],regions=r['regions']) for r in images],
                          receipt=str(output.relative_to(ROOT))),indent=2))


if __name__ == '__main__':
    main()
