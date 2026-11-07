#!/usr/bin/env python3
"""Check original Arcade upper jobs against independently indexed native RAM.

Passive inputs only: no CPU, emulator, downloaded program or hardware response
is executed. Native prestate supplies the current artwork and mutable pointers.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/anomaly'
BINARY_SHA = 'b8744b0184128330a069a7366c4f843193306074f4a55a03d10f092a6fa8800c'
RUNTIME_HELPER_SHA = 'c016696ab829fec52b9b10830af2b8111806cc629f734d40b3c7cbc5a392b978'
JOBS = {0x36f3: 'pixel-row', 0x38bb: 'color-row',
        0x39b1: 'new-color-column', 0x39ca: 'new-pixel-column'}
UPPER_DOMAINS = ((0x4000, 0x5040), (0xe000, 0xf040),
                 (0x6000, 0x6208), (0xcc00, 0xce08))
STATE = (7, *range(0xcc, 0xd0), 0xd4, *range(0xd5, 0xd9),
         *range(0xdb, 0xdf), 0x36f1, 0x36f2, 0x399c)
PATCHES = {0x3899, 0x389a, 0x389e, 0x389f, 0x38a3, 0x38a4,
           0x38a8, 0x38a9, 0x399c, 0x39b2, 0x39b3, 0x39cb, 0x39cc}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def checked(item):
    data = (ROOT / item['path']).read_bytes()
    assert len(data) == item['bytes'] and sha(data) == item['sha256']
    return data


def word(memory, address):
    return memory[address] | memory[address + 1] << 8


def setword(memory, address, value):
    memory[address] = value & 255
    memory[address + 1] = value >> 8 & 255


def inputs():
    path = BASE / 'binary-analysis/side1-binary-proof.json'
    assert sha(path.read_bytes()) == BINARY_SHA
    proof = json.loads(path.read_text())
    assert proof['pass'] and proof['bundles'][36]['bundle'] == 36
    source = checked(proof['bundles'][36]['RAM'])
    known = checked(proof['bundles'][36]['known_mask'])
    assert len(source) == len(known) == 65536
    for first, end in ((0x36e3, 0x39e9), (0x6700, 0x67ee),
                       (0x6b82, 0x72be), (0x7500, 0x75d0), (0xb400, 0xb864)):
        assert all(known[first:end])
    helper_path = ROOT / 'research/anomaly/inspect_arcade.py'
    assert sha(helper_path.read_bytes()) == RUNTIME_HELPER_SHA
    spec = importlib.util.spec_from_file_location('anomaly_frozen_capture_reader', helper_path)
    helper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(helper)
    return source, helper, dict(binary_proof=record(path),
        original_RAM=proof['bundles'][36]['RAM'],
        original_known_mask=proof['bundles'][36]['known_mask'],
        passive_snapshot_reader=record(helper_path),
        snapshot_schema_reader=record(ROOT / 'research/quondam/snapshot_state.py'))


def guard(memory, source):
    fixed = [a for a in range(0x36f3, 0x39e9) if a not in PATCHES]
    fixed += list(range(0x6b82, 0x72be)) + list(range(0x7500, 0x75d0))
    assert all(memory[a] == source[a] for a in fixed), 'Original upper code/table identity differs'
    assert memory[0x36f0] == 0x4c
    tables = (0x7500, 0x750d, 0x751a, 0x7527) if memory[0xd0] == 0 else (0x7568, 0x7575, 0x7582, 0x758f)
    assert [word(memory, a) for a in (0x3899, 0x389e, 0x38a3, 0x38a8)] == list(tables)


def predicted(before, pc):
    """Independent row/column geometry with source-exact pointer transitions."""
    memory = bytearray(before)
    events = []
    assert len(memory) == 65536 and before[7] != 0
    assert word(before, 0x36f1) == pc and pc in JOBS
    assert before[0xd0] in (0, 255)
    back_bitmap, back_screen = ((0xe000, 0xcc00) if before[0xd0] == 0 else (0x4000, 0x6000))
    front_bitmap, front_screen = ((0x4000, 0x6000) if before[0xd0] == 0 else (0xe000, 0xcc00))

    def transfer(source, destination):
        source &= 65535
        destination &= 65535
        assert source not in (0, 1) and not 0xd000 <= source < 0xe000
        assert destination not in (0, 1) and not 0xd000 <= destination < 0xe000
        value = memory[source]  # Read after previous writes, preserving overlap.
        memory[destination] = value
        events.append(dict(source=source, address=destination, value=value))

    row = None
    if pc == 0x36f3:
        row = before[0xd4]
        assert row < 13
        source, destination = word(before, 0xcc), word(before, 0xce)
        assert source == front_bitmap + 320 * row + 8
        assert destination == back_bitmap + 320 * row
        for offset in range(256):
            transfer(source + offset, destination + offset)
        memory[0xcd] = (memory[0xcd] + 1) & 255
        memory[0xcf] = (memory[0xcf] + 1) & 255
        for offset in range(64):
            transfer(word(memory, 0xcc) + offset, word(memory, 0xce) + offset)
        memory[0xd4] = row + 1
        # Row 13 is still read before dispatch changes. These are the adjacent
        # table bytes, not a manufactured fourteenth row or a clamped index.
        for instruction, pointer in ((0x3898, 0xcc), (0x389d, 0xcd),
                                     (0x38a2, 0xce), (0x38a7, 0xcf)):
            memory[pointer] = memory[(word(before, instruction + 1) + row + 1) & 65535]
        if row == 12:
            setword(memory, 0x36f1, 0x38bb)
    elif pc == 0x38bb:
        row = before[0x399c]
        assert row < 13
        source, destination = word(before, 0xd5), word(before, 0xd7)
        assert source == front_screen + 40 * row + 1
        assert destination == back_screen + 40 * row
        for offset in range(40):
            transfer(source + offset, destination + offset)
        # The original increments both highs from SOURCE carry only. The
        # second ADC's destination-low carry is deliberately not propagated.
        total = before[0xd5] + 40
        memory[0xd5] = total & 255
        if total >= 256:
            memory[0xd6] = (memory[0xd6] + 1) & 255
            memory[0xd8] = (memory[0xd8] + 1) & 255
        memory[0xd7] = (before[0xd7] + 40) & 255
        memory[0x399c] = row + 1
        if row == 12:
            memory[0x399c] = 0
            setword(memory, 0x36f1, 0x39b1)
    elif pc == 0x39b1:
        helper = word(before, 0x39b2)
        assert helper == (0x6bd2 if back_screen == 0xcc00 else 0x6b82)
        pointer = word(before, 0xdb)
        for offset in range(13):
            transfer(pointer + offset, back_screen + 40 * offset + 39)
        setword(memory, 0xdb, pointer + 13)
        setword(memory, 0x36f1, 0x39ca)
    else:
        helper = word(before, 0x39cb)
        assert helper == (0x6f70 if back_bitmap == 0xe000 else 0x6c22)
        pointer = word(before, 0xdd)
        for offset in range(104):
            row, fine = divmod(offset, 8)
            transfer(pointer + offset, back_bitmap + 320 * row + 312 + fine)
        setword(memory, 0xdd, pointer + 104)
        memory[7] = 0
        setword(memory, 0x36f1, 0x36f3)
        row = None
    return memory, dict(job=JOBS[pc], row=row, expected_data_stores=len(events),
        expected_store_order=events, state_before={f'{a:04x}': before[a] for a in STATE},
        state_after={f'{a:04x}': memory[a] for a in STATE},
        source_scope='Actual native prestate; original code supplies geometry and transition rules.')


def differences(actual, expected, addresses):
    return [dict(address=a, actual=actual[a], expected=expected[a])
            for a in sorted(set(addresses)) if actual[a] != expected[a]]


def publication(before):
    """RAM transition from B84B through the two calls and three port stores."""
    memory = bytearray(before)
    assert before[0xd0] in (0, 255)
    memory[0xd0] ^= 255
    memory[0xd3] = memory[0xd4] = 0
    if memory[0xd0] == 255:
        memory[0xd1], memory[0xd2] = 0x38, 0x3f
        tables = (0x7568, 0x7575, 0x7582, 0x758f, 0x759c, 0x75a9, 0x75b6, 0x75c3)
        color, pixels = 0x6b82, 0x6c22
    else:
        memory[0xd1], memory[0xd2] = 0x80, 0x3d
        tables = (0x7500, 0x750d, 0x751a, 0x7527, 0x7534, 0x7541, 0x754e, 0x755b)
        color, pixels = 0x6bd2, 0x6f70
    for pointer, table in zip((0xcc, 0xcd, 0xce, 0xcf, 0xd5, 0xd6, 0xd7, 0xd8), tables):
        memory[pointer] = before[table]
    for operand, table in zip((0x3899, 0x389e, 0x38a3, 0x38a8), tables[:4]):
        setword(memory, operand, table)
    setword(memory, 0x39b2, color)
    setword(memory, 0x39cb, pixels)
    memory[7] = 1
    # Dispatch and colour-row counter are NOT reset by publication.
    return memory


def chain_check(directory, reader, jobs):
    expected = [('pixel-row', i) for i in range(13)] + [('color-row', i) for i in range(13)]
    expected += [('new-color-column', None), ('new-pixel-column', None)]
    actual = [(row['job'], row['row']) for row in jobs]
    assert actual == expected, ('Only one complete first 28-job sequence belongs to this witness', actual)
    immutable_between_jobs = set(STATE) | {0xd0}
    for first, end in UPPER_DOMAINS:
        immutable_between_jobs.update(range(first, end))
    links = []
    for prior, following in zip(jobs, jobs[1:]):
        a, _ = reader.native(directory, prior['name'] + '-post')
        b, _ = reader.native(directory, following['name'] + '-pre')
        diff = differences(b, a, immutable_between_jobs)
        assert not diff, ('Upper data/state changed between recorded jobs', prior['name'], following['name'], diff)
        links.append(dict(before=prior['name'], after=following['name'], exact=True))
    initial, _ = reader.native(directory, jobs[0]['name'] + '-pre')
    final, _ = reader.native(directory, jobs[-1]['name'] + '-post')
    assert initial[7] == 1 and final[7] == 0
    front_bitmap, front_screen, back_bitmap, back_screen = ((0x4000, 0x6000, 0xe000, 0xcc00)
        if initial[0xd0] == 0 else (0xe000, 0xcc00, 0x4000, 0x6000))
    image = bytearray(initial)
    for row in range(13):
        for column in range(39):
            for fine in range(8):
                image[back_bitmap + 320*row + 8*column + fine] = initial[front_bitmap + 320*row + 8*(column+1) + fine]
            image[back_screen + 40*row + column] = initial[front_screen + 40*row + column+1]
        for fine in range(8):
            image[back_bitmap + 320*row + 312 + fine] = initial[word(initial, 0xdd) + 8*row + fine]
        image[back_screen + 40*row + 39] = initial[word(initial, 0xdb) + row]
    final_image_diff = differences(final, image,
        list(range(back_bitmap, back_bitmap+4160)) + list(range(back_screen, back_screen+520)))
    assert not final_image_diff
    return dict(jobs=28, exact_order=True, between_job_links=links,
        payload_stores=sum(row['expected_data_stores'] for row in jobs),
        initial=jobs[0]['pre'], final=jobs[-1]['post'],
        initial_status=initial[7], final_status=final[7],
        independent_final_image=dict(bitmap_first=back_bitmap, bitmap_bytes=4160,
            bitmap_sha256=sha(image[back_bitmap:back_bitmap+4160]),
            screen_first=back_screen, screen_bytes=520,
            screen_sha256=sha(image[back_screen:back_screen+520]), differences=final_image_diff,
            basis='Direct 39-cell left shift plus original incoming column, indexed from the first native prestate; not repeated job simulation.'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, default=BASE / 'native-04')
    parser.add_argument('--output', type=Path, default=BASE / 'upper-analysis')
    args = parser.parse_args()
    directory, output = args.capture.resolve(), args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    source, reader, provenance = inputs()
    session_path = directory / 'session.json'
    session = json.loads(session_path.read_text())
    jobs = []
    for path in directory.glob('*-pre.vsf'):
        stem = path.stem[:-4]
        post_path = directory / (stem + '-post.vsf')
        if not post_path.exists():
            continue
        before, pre = reader.native(directory, stem + '-pre')
        pc = pre['registers']['pc']
        if pc not in JOBS:
            continue
        after, post = reader.native(directory, stem + '-post')
        assert post['registers']['pc'] == 0x3d89
        assert post['registers']['clock'] > pre['registers']['clock']
        reader.RAM_visible(pre)
        reader.RAM_visible(post)
        guard(before, source)
        guard(after, source)
        expected, model = predicted(before, pc)
        domains = [dict(first=first, end_exclusive=end, bytes=end-first,
            expected_sha256=sha(expected[first:end]), actual_sha256=sha(after[first:end]),
            differences=differences(after, expected, range(first, end)))
            for first, end in UPPER_DOMAINS]
        state_diff = differences(after, expected, STATE)
        outside = differences(after, expected, range(65536))
        jobs.append(dict(name=stem, pre=pre, post=post, **model, domains=domains,
            mutable_state_differences=state_diff,
            elapsed_native_clocks=post['registers']['clock']-pre['registers']['clock'],
            all_RAM_observed_changes=differences(after, before, range(65536)),
            all_RAM_vs_host_model_differences=outside,
            exact=not state_diff and all(not d['differences'] for d in domains)))
    jobs.sort(key=lambda row: row['pre']['registers']['clock'])
    assert jobs, 'No complete accepted-job entry/return pair was supplied'
    counts = {name: sum(job['job'] == name for job in jobs) for name in JOBS.values()}
    chain = chain_check(directory, reader, jobs) if len(jobs) == 28 else None
    gate = None
    if (directory / 'gate-pixel-pre.vsf').exists():
        memory, state = reader.native(directory, 'gate-pixel-pre')
        assert state['registers']['pc'] == 0x36e6
        assert memory[0x36e6] == 0xc9 and memory[0x36e8:0x36f1] == source[0x36e8:0x36f1]
        value, threshold = state['registers']['a'], memory[0x36e7]
        assert (value-threshold) & 0x80 and memory[7] != 0
        entry, metadata = reader.native(directory, jobs[0]['name'] + '-pre')
        diff = differences(entry, memory, range(65536))
        assert not diff
        gate = dict(pre=state, accepted_by_signed_difference=True,
            actual_sampled_D012_low=value, threshold=threshold,
            entry=metadata, all_RAM_differences=diff,
            elapsed_native_clocks=metadata['registers']['clock']-state['registers']['clock'])
    publish = None
    if all((directory / (name + '.vsf')).exists() for name in ('publication-pre', 'publication-post')):
        before, pre = reader.native(directory, 'publication-pre')
        after, post = reader.native(directory, 'publication-post')
        assert pre['registers']['pc'] == 0xb84b and post['registers']['pc'] == 0xb864
        reader.RAM_visible(pre)
        reader.RAM_visible(post)
        for first, end in ((0x6700, 0x67ee), (0xb84b, 0xb856), (0xb857, 0xb864)):
            assert before[first:end] == source[first:end] == after[first:end]
        assert before[7] == 0, 'Observed first publication must follow a completed chain'
        last, _ = reader.native(directory, jobs[-1]['name'] + '-post')
        stable = set(STATE) | {0xd0}
        for first, end in UPPER_DOMAINS:
            stable.update(range(first, end))
        ready_diff = differences(before, last, stable)
        assert not ready_diff, 'Completed upper data/state changed before publication'
        expected = publication(before)
        addresses = set(STATE) | set(PATCHES) | set(range(0xd0, 0xd4))
        for first, end in UPPER_DOMAINS:
            addresses.update(range(first, end))
        diff = differences(after, expected, addresses)
        assert not diff
        from snapshot_state import read_snapshot
        snapshot = read_snapshot(directory / 'publication-post.vsf')
        ports = dict(D016=post['VIC_regs'][0x16], D018=post['VIC_regs'][0x18],
                     DD02=snapshot['cia']['CIA2']['ddra'])
        assert ports == dict(D016=expected[0xb856], D018=expected[0xd1], DD02=expected[0xd2])
        publish = dict(pre=pre, post=post, completed_before_swap=True,
            completed_image_preserved_until_publication=True,
            completed_image_or_state_differences=ready_diff,
            elapsed_native_clocks=post['registers']['clock']-pre['registers']['clock'],
            mutable_state_differences=diff, actual_ports=ports,
            selected_bitmap=0xe000 if after[0xd0] else 0x4000,
            selected_screen=0xcc00 if after[0xd0] else 0x6000,
            all_RAM_vs_host_model_differences=differences(after, expected, range(65536)),
            warning='This source publishes unconditionally; only this observed first publication is checked as complete.')
    schedule = reader.D016_schedule(source)
    field_plans = []
    for path in sorted(directory.glob('field*-pre.vsf')):
        name = path.stem[:-4]
        before, pre = reader.native(directory, name + '-pre')
        assert pre['registers']['pc'] == 0xb400
        plan = [dict(**row, expected_value=before[row['table_address']]) for row in schedule]
        for row in plan:
            pc = row['pc']
            assert before[pc-2:pc+3] == source[pc-2:pc+3]
            assert 0xc0 <= row['expected_value'] <= 0xc7
        post = None
        if (directory / (name + '-post.vsf')).exists():
            after, post = reader.native(directory, name + '-post')
            assert post['registers']['pc'] == 0xb828 and before[8:0x68] == after[8:0x68]
        field_plans.append(dict(name=name, pre=pre, post=post, expected_D016_stores=plan,
            scope='Original 96-site/index schedule and actual prestate values; native trace comparison belongs to the parent-owned native audit.'))
    field_plans.sort(key=lambda row: row['pre']['registers']['clock'])
    result = dict(pass_=all(job['exact'] for job in jobs),
        scope='Conditional native RAM upper-job witnesses. No CPU/IRQ/VIC simulation, full-image or whole-demo frame-rate claim.',
        script=record(Path(__file__).resolve()), inputs=provenance,
        session=record(session_path), session_closed=bool(session.get('closed_utc')),
        lifecycle_scope='Closure metadata is observed here; the parent-owned native audit owns observer/session provenance.',
        upper_domains=[dict(first=a, end_exclusive=b) for a, b in UPPER_DOMAINS],
        jobs=jobs, job_counts=counts, expected_first_chain_counts=dict(zip(JOBS.values(), (13, 13, 1, 1))),
        accepted_gate=gate, completed_chain=chain, publication=publish,
        bounded_upper_chain_complete=chain is not None and publish is not None,
        floor_field_plans=field_plans,
        unmodeled_RAM_scope='Every actual-versus-host difference is retained, including stack/IRQ/music state; none is silently excluded.',
        runtime_witness_complete=False)
    result['pass'] = result.pop('pass_')
    target = output / 'upper-proof.json'
    target.write_text(json.dumps(result, indent=2) + '\n')
    (output / 'checked-inspect_upper.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({key: result[key] for key in ('pass', 'session_closed', 'job_counts')}, indent=2))
    if not result['pass']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
