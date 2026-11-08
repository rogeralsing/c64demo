#!/usr/bin/env python3
"""Independent artwork, floor arithmetic, hidden-job and native scanout oracle.

Protects actual per-line fine scroll/coarse wrap, signed gate boundaries, hidden
copy ordering and completion-gated publication. Uses the real runnable PRG;
there are no production test flags or monitor writes to code/registers/data.
"""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import socket
import subprocess

from PIL import Image, ImageChops

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
OUT = HERE / 'build/verification'
TRACE = re.compile(r'#\d+ \(Trace store ([0-9a-f]+)\)\s+(\d+)/[^\n]*\n'
                   r'\.C:([0-9a-f]+)[^\n]* A:([0-9a-f]+)[^\n]*\s(\d+)\s*$', re.I | re.M)
GLYPHS = ((14,17,31,17,17), (30,17,30,18,17), (15,16,16,16,15),
          (14,17,31,17,17), (30,17,17,17,30), (31,16,30,16,31))
BITMAPS = (0x2000, 0x6000)
SCREENS = (0x0400, 0x4400)
SLOTS = (35, 163, 36, 164)


def wall_pixel(x, y):
    x %= 64
    if y < 8:
        return y in (1, 6) or x in (2, 61)
    if y < 24:
        letter_x = x - 14
        ink = (0 <= letter_x < 36 and 12 <= y < 17 and letter_x % 6 < 5
               and GLYPHS[letter_x // 6][y - 12] & (16 >> (letter_x % 6)))
        return bool(ink) or x in (7, 56) or y == 21
    if y < 68:
        ink = x in (7, 56) or y in (25, 66)
        if 12 <= x < 52 and 30 <= y < 61:
            ink = x in (12, 51) or y in (30, 60)
            ax, ay = x - 32, y - 45
            if abs(ax) <= 10 and abs(ay) <= 7:
                ink = ((abs(ay) <= 4 and abs(ax) < 8) or
                       (abs(ay) == 7 and abs(ax) == 7) or (ay == 6 and abs(ax) == 9))
                if ay == -1 and ax in (-4, 4):
                    ink = False
            ink |= y == 55 and x % 8 < 3
        return ink
    if y < 88:
        return (x in (7, 56) or y in (68, 86) or
                (72 <= y <= 78 and (16 <= x <= 20 or 38 <= x <= 42 or (x == 29 and y < 76))))
    return x in (7, 56) or y == 101 or (y == 95 and 22 <= x <= 41)


def wall_color(column, row):
    return (3 if row in (0, 2, 8, 10) else (3, 14, 7, 13)[(column // 8) % 4]) << 4


def horizon_pixel(x, y):
    return y in (0, 3, 27, 31) or abs(x - 160) == (31 - y) * 4 or (y > 12 and x % 64 < 2)


def initial_phase(line):
    return (line + 2 * (line // 16)) % 8


def floor_pixel(line, x):
    spacing = 16 + line
    return (x + 256) % spacing < 2 or line in (0, 6, 16, 31, 53) or (
        line >= 32 and ((x + 256) // spacing + (line - 32) // 22) % 2 == 1)


def floor_byte(line, stream_column):
    return sum(128 >> bit for bit in range(8)
               if floor_pixel(line, (stream_column % 64) * 8 + bit + initial_phase(line)))


def floor_state(updates):
    fine, accum, incoming, bitmap, coarse = bytearray(), bytearray(), bytearray(), bytearray(2560), []
    for line in range(64):
        carries, fractional = divmod(updates * (112 + line), 256)
        wrapped = (carries + 7 - initial_phase(line)) // 8
        fine.append((initial_phase(line) - carries) % 8)
        accum.append(fractional)
        incoming.append((40 + wrapped) % 64)
        coarse.append(wrapped)
        for column in range(40):
            bitmap[(line // 8) * 320 + column * 8 + line % 8] = floor_byte(line, wrapped + column)
    return bytes(fine + accum + incoming), bytes(bitmap), coarse


def initial_wall():
    bitmap = bytearray(5440)
    attrs = bytearray(1024)
    for row in range(17):
        for col in range(40):
            attrs[row * 40 + col] = wall_color(col, row) if row < 13 else 0x30
            for line in range(8):
                bitmap[row * 320 + col * 8 + line] = sum(
                    128 >> bit for bit in range(8) if (
                        wall_pixel(col * 8 + bit, row * 8 + line) if row < 13
                        else horizon_pixel(col * 8 + bit, (row - 13) * 8 + line)))
    return [bitmap.copy(), bitmap.copy()], [attrs.copy(), attrs.copy()]


def coherent_wall(publication):
    bitmap, attrs = initial_wall()
    bitmap, attrs = bitmap[0], attrs[0]
    for row in range(13):
        for col in range(40):
            attrs[row * 40 + col] = wall_color(col + publication, row)
            for line in range(8):
                bitmap[row * 320 + col * 8 + line] = sum(
                    128 >> bit for bit in range(8) if wall_pixel((col + publication) * 8 + bit, row * 8 + line))
    return bitmap, attrs


def expected_image(publication, fine, updates, palette):
    image = Image.new('RGB', (384, 272), palette[0])
    for y in range(200):
        # The8565's38-column border opens one hirespixel before cell1.
        for x in range(7, 311):
            color = 0
            if y < 104:
                source_x = x - fine + publication * 8
                if wall_pixel(source_x, y):
                    color = wall_color(source_x // 8, y // 8) >> 4
            elif y < 136:
                if horizon_pixel(x - fine, y - 104):
                    color = 3
            else:
                line = y - 136
                carries = updates * (112 + line) // 256
                if floor_pixel(line, x + carries):
                    color = 6 if (y // 8) % 2 else 14
            image.putpixel((32 + x, 35 + y), palette[color])
    return image


def workload(phases):
    counts = []
    old = [0] * 64
    for update in range(1, 2049):
        coarse = [((update * (112 + line) // 256) + 7 - phases[line]) // 8 for line in range(64)]
        counts.append(sum(a - b for a, b in zip(coarse, old)))
        old = coarse
    return {'total_coarse_copies': sum(counts), 'maximum_coincident_lines': max(counts),
            'mean_lines_per_call': sum(counts) / len(counts)}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / 'proof.json').unlink(missing_ok=True)
    spec = importlib.util.spec_from_file_location('shared_monitor', ROOT / 'verify.py')
    common = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(common)
    labels = common.read_labels(HERE / 'build/main.sym')
    palette = [tuple(int(v, 16) for v in line.split()[:3])
               for line in (ROOT / 'palettes/colodore.vpl').read_text().splitlines()
               if line and not line.startswith('#')]
    with socket.socket() as reservation:
        reservation.bind(('127.0.0.1', 0))
        port = reservation.getsockname()[1]
    program = HERE / 'build/example.prg'
    command = common.vice_command(os.environ.get('VICE', 'x64sc'), program, port, ROOT / 'palettes/colodore.vpl')
    bitmaps, attrs = initial_wall()
    wall = dict(front=0, publication=0, fine=7, tick=0, wrap=0, job=0, pending=1)
    fields, gates, copies, publications, floor_updates, pictures, stores = [], [], [], [], [], [], []
    inflight = None
    floor_begin = None
    monitor = None
    selected = {0, 1, 7, 15, 31, 47, 55, 56, 57, 63, 79, 111, 112, 113, 127, 143}
    hardware_fields = 144
    held = 0
    bitmap_bytes = 0
    attribute_bytes = 0

    def state(ram, name, size=1):
        return int.from_bytes(ram[labels[name]:labels[name] + size], 'little')

    def check_wall_state(ram):
        for key, name in (('front','frontBuffer'), ('publication','publicationCounter'),
                          ('fine','wallFine'), ('tick','wallTick'), ('wrap','wallWrap'),
                          ('job','jobIndex'), ('pending','wallPending')):
            assert state(ram, name) == wall[key], (name, state(ram, name), wall[key])

    def check_buffers(ram):
        for bank in range(2):
            assert ram[BITMAPS[bank]:BITMAPS[bank] + 5440] == bitmaps[bank], ('wall bitmap', bank)
            assert ram[SCREENS[bank]:SCREENS[bank] + 1024] == attrs[bank], ('wall attributes', bank)

    def plan_copy(job):
        front, hidden = wall['front'], wall['front'] ^ 1
        domain = 'bitmap' if job < 13 or job == 27 else 'attributes'
        source = bitmaps if domain == 'bitmap' else attrs
        writes = []
        if job < 13:
            row = job
            writes = [(row * 320 + column * 8 + line, source[front][row * 320 + (column + 1) * 8 + line])
                      for line in range(8) for column in range(40)]
        elif job < 26:
            row = job - 13
            writes = [(row * 40 + column, source[front][row * 40 + column + 1]) for column in range(40)]
        elif job == 26:
            writes = [(row * 40 + 39, wall_color(40 + wall['publication'], row)) for row in range(13)]
        else:
            writes = [(row * 320 + 312 + line, sum(128 >> bit for bit in range(8)
                       if wall_pixel((40 + wall['publication']) * 8 + bit, row * 8 + line)))
                      for row in range(13) for line in range(8)]
        post = source[hidden].copy()
        for offset, value in writes:
            post[offset] = value
        return dict(job=job, hidden=hidden, domain=domain, writes=writes,
                    before=source[hidden].copy(), after=post)

    with (OUT / 'vice.log').open('w') as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
        try:
            monitor = common.Monitor(common.connect_monitor(process, port))
            monitor.run('r')
            checkpoints = {}
            for name in ('gateWallJob','gateComplete','fieldComplete','floorUpdateBegin','floorUpdateComplete'):
                response=monitor.run(f'break {labels[name]:04x}')
                checkpoints[name]=int(re.search(r'BREAK:\s*(\d+)',response)[1])
            tracepoints=[]
            for address in ('d016','dd00'):
                response=monitor.run(f'trace store {address}')
                tracepoints.append(int(re.search(r'TRACE:\s*(\d+)',response)[1]))
            for stop in range(1200):
                response = monitor.run('x')
                for address, raster, pc, value, clock in TRACE.findall(response):
                    stores.append(dict(address=int(address,16), raster=int(raster), pc=int(pc,16),
                                       value=int(value,16), clock=int(clock)))
                pc, raster, clock = monitor.registers()
                monitor.run('bank ram')
                ram = monitor.memory(OUT / 'latest-ram.bin', 0, 65535)
                if pc == labels['gateWallJob']:
                    check_wall_state(ram)
                    check_buffers(ram)
                    field = state(ram,'fieldCounter',2)
                    target = SLOTS[field % 4]
                    entry_registers = monitor.run('r')
                    sampled = int(re.search(r'^\.;[0-9a-f]+\s+([0-9a-f]+)',entry_registers,re.I|re.M)[1],16)
                    assert sampled == target, (field,raster,sampled,target)
                    assert raster in (target,target+1), (field,raster,target)
                    assert inflight is None
                    inflight = dict(field=field, clock=clock, raster=raster, sample=sampled,
                                    accepted=((sampled - 0x24) & 0x80) != 0,
                                    job=wall['job'], copied=wall['pending'] != 0)
                    if inflight['accepted'] and inflight['copied']:
                        inflight['copy'] = plan_copy(wall['job'])
                elif pc == labels['gateComplete']:
                    assert inflight is not None
                    sample = state(ram,'gateSample')
                    assert sample == inflight['sample']
                    assert bool(state(ram,'gateAccepted')) == inflight['accepted']
                    did_run = inflight['accepted'] and inflight['copied']
                    assert bool(state(ram,'jobDidRun')) == did_run
                    assert state(ram,'jobBefore') == inflight['job']
                    if did_run:
                        copy = inflight['copy']
                        domain = bitmaps if copy['domain'] == 'bitmap' else attrs
                        domain[copy['hidden']] = copy['after']
                        wall['job'] += 1
                        wall['pending'] = int(wall['job'] < 28)
                        copies.append(dict(field=inflight['field'], job=copy['job'], domain=copy['domain'],
                                           bytes=len(copy['writes']), clocks=clock-inflight['clock'],
                                           start_raster=inflight['raster'], end_raster=raster,
                                           interrupted_copy_prefix=inflight.get('prefix_at_floor_end')))
                    check_wall_state(ram)
                    check_buffers(ram)
                    gates.append(dict(field=inflight['field'],sample=sample,accepted=inflight['accepted'],
                                      job_ran=did_run,job_before=inflight['job'],job_after=wall['job']))
                    inflight = None
                elif pc == labels['floorUpdateBegin']:
                    assert floor_begin is None
                    floor_begin = (clock, state(ram,'updateCounter',2), raster)
                elif pc == labels['floorUpdateComplete']:
                    assert floor_begin is not None
                    updates = state(ram,'updateCounter',2)
                    assert updates == floor_begin[1] + 1
                    expected_state, expected_bitmap, coarse = floor_state(updates)
                    assert ram[0x8000:0x80c0] == expected_state, ('floor state', updates)
                    assert ram[0xb540:0xbf40] == expected_bitmap, ('floor live shift', updates)
                    assert raster >= 252 or raster < 163, ('floor updater missed its following gate', updates, raster)
                    assert clock-floor_begin[0] < (312-floor_begin[2]+163)*63
                    previous_coarse = floor_state(updates-1)[2]
                    floor_updates.append(dict(update=updates,clocks=clock-floor_begin[0],
                                              begin_raster=floor_begin[2],end_raster=raster,
                                              coarse_lines=sum(a-b for a,b in zip(coarse,previous_coarse))))
                    floor_begin = None
                elif pc == labels['fieldComplete']:
                    field = state(ram,'fieldCounter',2)
                    assert field == len(fields)
                    check_wall_state(ram)
                    front = wall['front']
                    expected_front, expected_attrs = coherent_wall(wall['publication'])
                    assert ram[BITMAPS[front]:BITMAPS[front]+5440] == expected_front
                    assert ram[SCREENS[front]:SCREENS[front]+1024] == expected_attrs
                    if inflight is not None and 'copy' in inflight:
                        copy = inflight['copy']
                        base = BITMAPS[copy['hidden']] if copy['domain']=='bitmap' else SCREENS[copy['hidden']]
                        current = ram[base:base+len(copy['before'])]
                        prefix = copy['before'].copy()
                        candidates=[]
                        for count in range(len(copy['writes'])+1):
                            if prefix==current:candidates.append(count)
                            if count<len(copy['writes']):
                                offset,value=copy['writes'][count];prefix[offset]=value
                        assert candidates, ('interrupted hidden job did not match a real copy prefix',field)
                        inflight['prefix_at_floor_end']=[min(candidates),max(candidates)]
                    else:
                        check_buffers(ram)
                    updates = state(ram,'updateCounter',2)
                    assert updates == (field+1)//2
                    expected_state, expected_bitmap, _ = floor_state(updates)
                    assert ram[0x8000:0x80c0] == expected_state
                    assert ram[0xb540:0xbf40] == expected_bitmap
                    bitmap_bytes += 5440 + 2560
                    attribute_bytes += 1024
                    events=[event for event in stores if labels['rasterKernel'] <= event['pc'] < labels['fieldComplete']]
                    assert len(events)==64, (field,len(events))
                    assert [event['value'] for event in events]==list(expected_state[:64])
                    assert [event['raster'] for event in events]==list(range(187,251)), (field,events)
                    if fields:
                        intervals=[a['clock']-b['clock'] for a,b in zip(events,fields[-1]['floor_stores'])]
                        assert len(set(intervals))==1 and 19655<=intervals[0]<=19657, (field,intervals)
                    assert [event['clock']-events[0]['clock'] for event in events]==[63*i for i in range(64)]
                    bank_events=[event for event in stores if event['address']==0xdd00]
                    assert bank_events[-1]['value']==1 and bank_events[-1]['raster']==186
                    upper_events=[event for event in stores if event['address']==0xd016
                                  and not labels['rasterKernel']<=event['pc']<labels['fieldComplete']]
                    if field:
                        assert len(bank_events)==2 and bank_events[0]['value']==(front^3)
                        assert 252<=bank_events[0]['raster']<256
                        assert len(upper_events)==1 and upper_events[0]['value']==wall['fine']
                        assert 252<=upper_events[0]['raster']<256
                    record=dict(field=field,clock=clock,raster=raster,updates=updates,
                                front=front,publication=wall['publication'],fine=wall['fine'],
                                pending=wall['pending'],job=wall['job'],floor_stores=events,
                                bank_stores=bank_events,upper_scroll_stores=upper_events)
                    if field in selected:
                        shot=OUT/f'field-{field:03d}.png'
                        monitor.run(f'screenshot "{shot}" 2')
                        actual=Image.open(shot).convert('RGB')
                        expected=expected_image(wall['publication'],wall['fine'],updates,palette)
                        difference=ImageChops.difference(actual,expected)
                        if difference.getbbox():
                            expected.save(OUT/'expected-failed.png');difference.save(OUT/'difference-failed.png')
                            raise AssertionError((field,'full-field pixels',difference.getbbox(),
                                                  sum(a!=b for a,b in zip(actual.get_flattened_data(),expected.get_flattened_data()))))
                        pictures.append(actual)
                        record['screenshot']=shot.name
                    fields.append(record)
                    stores=[]
                    wall['tick']=(wall['tick']+1)&255
                    if not wall['wrap'] and wall['tick']>=6:
                        wall['tick']=0
                        if wall['fine']:
                            wall['fine']-=1
                        else:
                            wall['wrap']=1
                    if wall['wrap']:
                        if wall['pending']:
                            held+=1
                        else:
                            assert bitmaps[front^1]==coherent_wall(wall['publication']+1)[0]
                            assert attrs[front^1]==coherent_wall(wall['publication']+1)[1]
                            publications.append(dict(after_field=field,completed_jobs=28,
                                                     front=front^1,publication=wall['publication']+1))
                            wall.update(front=front^1,publication=wall['publication']+1,
                                        fine=7,tick=0,wrap=0,job=0,pending=1)
                    if len(fields)==hardware_fields:
                        break
                else:
                    raise AssertionError(('unexpected stop',hex(pc)))
            else:
                raise AssertionError('Bounded native run did not reach requested fields')

            # The first maximum18-copy call in the complete arithmetic period
            # is291. Reach it naturally, without tracing/reading skipped fields.
            # This witnesses its real cost without claiming a full581-field
            # wall-job/scanout audit for the intervening continuation.
            for checkpoint in (*checkpoints.values(),*tracepoints):
                monitor.run(f'disable {checkpoint}')
            for name,updates in (('floorUpdateBegin',290),('floorUpdateComplete',291)):
                low,high=updates&255,updates>>8
                monitor.run(f'condition {checkpoints[name]} if (@ram:${labels["updateCounter"]:04x} == ${low:02x}) && (@ram:${labels["updateCounter"]+1:04x} == ${high:02x})')
            monitor.run(f'enable {checkpoints["floorUpdateBegin"]}')
            monitor.run('x')
            pc,peak_start_raster,peak_start_clock=monitor.registers()
            assert pc==labels['floorUpdateBegin']
            monitor.run('bank ram')
            peak_before=monitor.memory(OUT/'peak-before.ram',0,65535)
            assert state(peak_before,'updateCounter',2)==290
            assert peak_before[0x8000:0x80c0]==floor_state(290)[0]
            assert peak_before[0xb540:0xbf40]==floor_state(290)[1]
            monitor.run(f'disable {checkpoints["floorUpdateBegin"]}')
            monitor.run(f'enable {checkpoints["floorUpdateComplete"]}')
            monitor.run('x')
            pc,peak_end_raster,peak_end_clock=monitor.registers()
            assert pc==labels['floorUpdateComplete']
            monitor.run('bank ram')
            peak_after=monitor.memory(OUT/'peak-after.ram',0,65535)
            assert state(peak_after,'updateCounter',2)==291
            assert peak_after[0x8000:0x80c0]==floor_state(291)[0]
            assert peak_after[0xb540:0xbf40]==floor_state(291)[1]
            peak_count=sum(a-b for a,b in zip(floor_state(291)[2],floor_state(290)[2]))
            assert peak_count==18
            assert peak_end_raster>=252 or peak_end_raster<163
            assert peak_end_clock-peak_start_clock<(312-peak_start_raster+163)*63
            monitor.run(f'disable {checkpoints["floorUpdateComplete"]}')
            monitor.run(f'enable {checkpoints["fieldComplete"]}')
            for tracepoint in tracepoints:monitor.run(f'enable {tracepoint}')
            response=monitor.run('x')
            peak_events=[dict(address=int(address,16),raster=int(raster),pc=int(pc,16),
                              value=int(value,16),clock=int(clock))
                         for address,raster,pc,value,clock in TRACE.findall(response)]
            peak_stores=[row for row in peak_events if row['address']==0xd016]
            assert len(peak_stores)==64
            assert [row['raster'] for row in peak_stores]==list(range(187,251))
            assert [row['value'] for row in peak_stores]==list(floor_state(291)[0][:64])
            monitor.run('bank ram')
            peak_frame=monitor.memory(OUT/'peak-field.ram',0,65535)
            peak_field=state(peak_frame,'fieldCounter',2)
            assert peak_field==581
            peak_publication=(peak_field-1)//56
            peak_fine=max(0,7-(peak_field-(peak_publication*56+1))//6)
            assert state(peak_frame,'publicationCounter')==peak_publication
            assert state(peak_frame,'wallFine')==peak_fine
            expected_front,expected_attrs=coherent_wall(peak_publication)
            peak_front=peak_publication&1
            assert state(peak_frame,'frontBuffer')==peak_front
            assert peak_frame[BITMAPS[peak_front]:BITMAPS[peak_front]+5440]==expected_front
            assert peak_frame[SCREENS[peak_front]:SCREENS[peak_front]+1024]==expected_attrs
            shot=OUT/'peak-update-291.png'
            monitor.run(f'screenshot "{shot}" 2')
            actual=Image.open(shot).convert('RGB')
            expected=expected_image(peak_publication,peak_fine,291,palette)
            difference=ImageChops.difference(actual,expected)
            if difference.getbbox():
                expected.save(OUT/'expected-failed.png');difference.save(OUT/'difference-failed.png')
                raise AssertionError(('peak full-field pixels',difference.getbbox()))
            pictures.append(actual)
            peak_witness=dict(update=291,field=peak_field,coarse_lines=peak_count,
                              clocks=peak_end_clock-peak_start_clock,
                              begin_raster=peak_start_raster,end_raster=peak_end_raster,
                              floor_stores=peak_stores,screenshot=shot.name,
                              skipped_fields_audited=False,wall_publication=peak_publication)
            bitmap_bytes+=8000
            attribute_bytes+=1024
            monitor.connection.sendall(b'quit\n')
            process.wait(timeout=10)
        finally:
            if process.poll() is None:
                process.kill();process.wait(timeout=5)
            if monitor:
                (OUT/'monitor.log').write_text('\n'.join(monitor.transcript))
                monitor.connection.close()
    assert len(fields)==hardware_fields and len(publications)>=2 and held>0
    assert {(gate['sample'],gate['accepted']) for gate in gates}=={(35,True),(36,False),(163,False),(164,True)}
    for chain in range(len(copies)//28):
        assert [copy['job'] for copy in copies[chain*28:(chain+1)*28]]==list(range(28))
    patterns={name:workload(phases) for name,phases in (
        ('staggered',[initial_phase(line) for line in range(64)]),('aligned_zero',[0]*64),('aligned_seven',[7]*64))}
    assert len({case['total_coarse_copies'] for case in patterns.values()})==1
    assert patterns['staggered']['maximum_coincident_lines']<patterns['aligned_zero']['maximum_coincident_lines']
    pictures[0].save(OUT/'arcade-scroller.gif',save_all=True,append_images=pictures[1:],duration=160,loop=0)
    proof=dict(pass_=True,program_sha256=hashlib.sha256(program.read_bytes()).hexdigest(),
               command=command,process_exit=process.returncode,PAL_fields_checked=len(fields),
               actual_floor_D016_stores=(len(fields)+1)*64,full_screenshot_pixels=len(pictures)*384*272,
               visible_bitmap_bytes_compared=bitmap_bytes,visible_attribute_bytes_compared=attribute_bytes,
               gated_calls=len(gates),complete_copy_jobs=len(copies),publication_holds=held,
               publications=publications,floor_update_cadence_fields=2,
               floor_update_clock_range=[min(row['clocks'] for row in floor_updates),max(max(row['clocks'] for row in floor_updates),peak_witness['clocks'])],
               additional_peak_witness=peak_witness,
               theoretical_2048_call_workloads=patterns,fields=fields,gates=gates,copies=copies,floor_updates=floor_updates,
               limits=['Own64-line floor and cabinets; no original936x96 artwork or release code.',
                       'PAL VICE8565 bounded execution; no original50Hz or physical-hardware deadline claim.',
                       'Store trace beam coordinates are observer timestamps, not certified bus-write phases.',
                       'Sampled GIF frames use uniform160ms playback and do not describe native cadence.'])
    proof['pass']=proof.pop('pass_')
    (OUT/'proof.json').write_text(json.dumps(proof,indent=2)+'\n')
    summary={key:value for key,value in proof.items() if key not in ('command','fields','gates','copies','floor_updates')}
    summary['additional_peak_witness']={key:value for key,value in peak_witness.items() if key!='floor_stores'}
    print(json.dumps(summary,indent=2))


if __name__=='__main__':
    main()
