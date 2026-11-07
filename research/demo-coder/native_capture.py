#!/usr/bin/env python3
"""Passively compare original Demo Coder RAM/VSF captures with offline proofs.

No CPU, drive, emulator, process, or monitor is started. Full RAM/VSF pairs
must share a register-observed PC and clock. Every mismatch is retained.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/demo-coder'
spec = importlib.util.spec_from_file_location('nine_native_readers', ROOT / 'research/nine/native_capture.py')
nine_readers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(nine_readers)
contexts, physical_ram = nine_readers.contexts, nine_readers.physical_ram
comparison, sha = nine_readers.comparison, nine_readers.sha
sys.path.insert(0, str(ROOT / 'research/quondam'))
from snapshot_state import read_snapshot, module_payload

BOOT_PROOF_SHA = '3d4cadb8daa2356a9c9008ded2d5da8748e22f50dd9b3dc715fa9d2c4bb72de0'
INDEX_SHA = '307b6de0dd9a5ca8fa81d095260768088bb29d49937a7b0a5772a068e4d3f709'
DISK_SHA = 'b8c54fc1ca41c00cd81773ecff780649d892bc6497a84b7c67c79a9235d95e9b'
RESIDENT_SHA = '76a531b34d87230ac6d25e32900caaeb796e7d8957eba5be358ce53401c835c4'


def references():
    proof_path = BASE / 'boot-proof.json'
    index_path = BASE / 'streams/unpacked-index.json'
    assert sha(proof_path.read_bytes()) == BOOT_PROOF_SHA
    assert sha(index_path.read_bytes()) == INDEX_SHA
    proof, index = json.loads(proof_path.read_text()), json.loads(index_path.read_text())
    boot = (BASE / 'boot-handoff.ram').read_bytes()
    assert len(boot) == 65536 and sha(boot) == proof['runs'][0]['ram_sha256']
    assert sha((ROOT / 'build/research/frontier-followup/demo-coder.d64').read_bytes()) == DISK_SHA
    images = {}
    for number in (0, 46):
        entry = index['files'][number]
        blob = (ROOT / entry['output_path']).read_bytes()
        assert int.from_bytes(blob[:2], 'little') == entry['target']
        assert sha(blob[2:]) == entry['output_sha256'] and len(blob)-2 == entry['output_bytes']
        memory = bytearray(65536)
        memory[entry['target']:entry['output_end']] = blob[2:]
        images[number] = memory
    resident = bytearray(65536)
    resident[0x200:0x3fc] = boot[0x82b1:0x84ad]
    assert sha(resident[0x200:0x3fc]) == RESIDENT_SHA
    assert boot[0x8076:0x8087] == bytes.fromhex('a2 00 bd b1 82 9d 00 02 bd ad 83 9d fc 02 ca d0 f1')
    return boot, resident, images, index


def part46_guard(memory):
    return (memory[0x6000:0x6024] == bytes.fromhex(
        'a9 f9 cd 12 d0 d0 fb a9 00 8d f6 01 8d f7 01 78 '
        'a9 38 8d fe ff a9 62 8d ff ff a9 00 8d 12 d0 a9 01 8d 1a d0'))


def initialized_reference(entry_ram, entry_color):
    """Literal finite $606f initializer, without executing any CPU or IRQ.

    The original code's page and tail loops have fixed lengths. All expected
    SMC updates are values derived from their source/destination advancement.
    Interrupt effects outside these RAM contracts are not invented.
    """
    result = bytearray(entry_ram)
    color = list(entry_color)
    color[:1000] = [value & 15 for value in entry_ram[0x4000:0x43e8]]
    result[0x4000:0x5c00] = entry_ram[0x2001:0x3c01]
    result[0xc000:0xdc00] = entry_ram[0x2002:0x3c02]
    result[0xe000:0xfc00] = bytes(0x1c00)
    for target in (0x5c00, 0xdc00, 0xfc00):
        result[target:target+1000] = entry_ram[0x3c00:0x3fe8]
    updates = {
        0x60b1:0x43, 0x60b4:0xdb, 0x60e1:0x43, 0x60e4:0xdb,
        # Their zero-length tails branch around $6117/$6162, so the unused
        # tail-copy operands at $6133/$6136/$617e/$6181 remain original.
        0x6103:0x3c, 0x6106:0x5c, 0x614e:0x3c, 0x6151:0xdc,
        0x61e8:0x40, 0x61eb:0x60, 0x61ee:0xe0, 0x61f1:0x00, 0x61f4:0xe8,
        0xb519:0xa1, 0xb51a:0x01, 0xb51b:0xf2, 0xb51c:0x02,
        0xb51f:0xfb, 0xb520:0x03, 0x606c:0x01,
    }
    for address, value in updates.items():
        result[address] = value
    return result, color, [dict(address=a, before=entry_ram[a], expected=v,
                                reason=('Literal initialization parameter/publication' if a >= 0xb500 or a == 0x606c
                                        else 'Fixed page/tail copy advances its original operand'))
                            for a, v in sorted(updates.items())]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture', type=Path, default=BASE / 'native-01')
    parser.add_argument('--output', type=Path, default=BASE / 'native-analysis')
    parser.add_argument('--allow-live', action='store_true', help='Provisional existing-capture preflight; never finalizes the session')
    args = parser.parse_args()
    directory, output = args.capture.resolve(), args.output.resolve()
    session = json.loads((directory / 'session.json').read_text())
    if not args.allow_live:
        assert session.get('closed_utc'), 'Final evidence requires the owner to close its session.'
    boot, resident, images, index = references()
    text = (directory / 'monitor.log').read_text(errors='replace')
    events = contexts(text)
    snapshots, pending = {}, []
    for event in events:
        if event['command'] != 'dump':
            continue
        path = directory / event['filename']
        if not path.exists() and args.allow_live:
            pending.append(event)
            continue
        state = read_snapshot(path)
        assert state['modules']['MAINCPU']['version'] == [1, 4]
        cpu_payload = module_payload(path, 'MAINCPU')
        # Pinned mainc64cpu.c: CLOCK8, A/X/Y/SP4, then PCword.
        clock = int.from_bytes(cpu_payload[:8], 'little')
        assert clock == event['registers']['clock'], ('Snapshot/register clock mismatch', path)
        assert int.from_bytes(cpu_payload[12:14], 'little') == event['registers']['pc'], ('Snapshot/register PC mismatch', path)
        snapshots.setdefault((event['registers']['pc'], clock), []).append((path, state, event['transcript_line']))
    records, screenshots, entry46 = [], [], None
    first_raster_seen = False
    first_dispatch_seen = False
    for event in events:
        register = event['registers']
        key = register['pc'], register['clock']
        path = directory / event['filename']
        if event['command'] not in ('bsave', 'screenshot', 'scrsh'):
            continue
        if args.allow_live and (not path.exists() or key not in snapshots):
            pending.append(event)
            continue
        assert key in snapshots, ('No same-stop snapshot', path)
        choices = snapshots[key]
        # A restored traced/control pair can have identical PC and clock but
        # different device state. Match the owner's explicit capture names;
        # never overwrite one VSF with the other in a (PC,clock) dictionary.
        stem = path.stem.removeprefix('ram-')
        named = [choice for choice in choices if choice[0].stem == stem]
        if len(named) == 1:
            snapshot, state, _ = named[0]
        elif len(choices) == 1:
            snapshot, state, _ = choices[0]
        else:
            assert event['command'] != 'bsave', ('Ambiguous same-PC/same-clock RAM/VSF pair', path, [str(c[0]) for c in choices])
            ordered = sorted(choices, key=lambda c:abs(c[2]-event['transcript_line']))
            assert abs(ordered[0][2]-event['transcript_line']) != abs(ordered[1][2]-event['transcript_line'])
            snapshot, state, _ = ordered[0]
        if event['command'] != 'bsave':
            screenshots.append(dict(file=str(path.relative_to(ROOT)), sha256=sha(path.read_bytes()),
                                    registers=register, snapshot=str(snapshot.relative_to(ROOT)),
                                    scope='Native output observation; no independent pixel oracle.'))
            continue
        assert event['bank'] == 'ram' and event['first'] == 0 and event['end_inclusive'] == 65535
        actual = path.read_bytes()
        assert len(actual) == 65536
        checks = [comparison(actual, physical_ram(snapshot), 0, 65536, 'Full raw RAM versus same-stop VSF RAM')]
        observations = []
        pc = register['pc']
        stage, established = 'unclassified_observation', False
        detail = {}
        if pc == 0x8a00:
            stage, established = 'original_boot_unpacked_handoff', True
            assert actual[0x8a00:0x8a0c] == bytes.fromhex('a9 18 2c 11 d0 10 fb 2c 11 d0 30 fb')
            checks.append(comparison(actual, boot, 0x3fff, 0xc000, 'Every original boot output byte'))
        elif pc == 0x8087:
            stage, established = 'resident_installed_before_detection', True
            assert actual[0x8076:0x8087] == boot[0x8076:0x8087]
            checks.append(comparison(actual, resident, 0x200, 0x3fc, 'All 508 installed resident bytes before detector patches'))
            checks.append(comparison(actual, boot, 0x82b1, 0x84ad, 'Original resident-copy source'))
        elif pc == 0xe000 and actual[pc:pc+10] == images[0][pc:pc+10]:
            stage, established = 'stream0_natural_entry', True
            checks.append(comparison(actual, images[0], 0xe000, index['files'][0]['output_end'], 'Complete first in-place image'))
            observations.append(comparison(actual, resident, 0x200, 0x3fc, 'Later resident differences; not a pristine installation claim'))
        elif pc == 0x6000 and part46_guard(actual):
            stage, established = 'stream46_natural_entry', True
            checks.append(comparison(actual, images[46], 0x2000, 0xc001, 'Complete stream 46 before its initializer'))
            entry46 = (actual, state['vicii']['color_ram'])
        elif pc in (0x6237, 0x62ea, 0x6332, 0x68b9) and part46_guard(actual):
            assert entry46 is not None, 'Later stream 46 capture lacks its natural entry reference'
            established = True
            stage = {0x6237:'stream46_initializer_body_complete',
                     0x62ea:'stream46_raster_irq_entry', 0x6332:'stream46_before_dispatch',
                     0x68b9:'stream46_dispatch'}[pc]
            checks.append(comparison(actual, images[46], 0x69c1, 0xb50c, 'All 19275 prebuilt selector-family bytes'))
            checks.append(comparison(actual, images[46], 0xbb64, 0xbbc8, 'All 100 selector target-table bytes'))
            if pc == 0x6237:
                expected, color, updates = initialized_reference(*entry46)
                checks.append(comparison(actual, expected, 0x2000, 0xc001, 'Complete entry image after literal initializer writes/operand advancement'))
                checks.append(comparison(actual, expected, 0xc000, 0xffe8, 'Initializer RAM-under-I/O copies, clears and untouched gaps'))
                differences = [dict(index=i, expected=e, actual=a) for i, (e, a) in enumerate(zip(color, state['vicii']['color_ram'])) if e != a]
                checks.append(dict(label='All 1024 Color RAM cells after literal 1000-cell copy', bytes=1024,
                                   exact=not differences, matched_bytes=1024-len(differences), differences=differences))
                detail['derived_initializer_updates'] = updates
                detail['irq_scope'] = 'CLI precedes initialization; early IRQ/music activity is possible. This checks finite initializer RAM/Color RAM effects, not a pre-IRQ whole-machine state.'
            else:
                observations.append(comparison(actual, images[46], 0x2000, 0xc001, 'Every later full-image difference from original; no broad mutable range excluded'))
                observations.append(comparison(actual, images[46], 0xb800, 0xba00, 'D011 data-page changes retained for separate raster-consumer analysis'))
                target = int.from_bytes(actual[0x68ba:0x68bc], 'little')
                candidates = [images[46][0xbb64+i]+256*images[46][0xbb96+i] for i in range(50)]
                valid = target == 0x68b9 or target in candidates
                checks.append(dict(label='Derived two-byte SMC dispatch operand', exact=valid,
                                   opcode=actual[0x68b9], expected_opcode=0x4c, target=target,
                                   original_target=0x68b9,
                                   matching_table_indices=[i for i, value in enumerate(candidates) if value == target],
                                   source_consumers=[0x6867, 0x692c], differences=[] if valid else [dict(target=target)]))
                assert actual[0x68b9] == 0x4c
                if pc == 0x68b9 and not first_dispatch_seen:
                    # First preparation calls the original $64ef loop once:
                    # X=$fb, Y=7, AND#$3f in both pages, DEX/DEY/BPL.
                    # Compare every page byte; no mutable bit mask is accepted.
                    expected_pages = bytearray(images[46])
                    updates = []
                    for page in (0xb800, 0xb900):
                        for offset in range(0xf4, 0xfc):
                            address = page+offset
                            expected_pages[address] &= 0x3f
                            updates.append(dict(address=address, before=images[46][address],
                                                expected=expected_pages[address], source_pc=0x64ef))
                    checks.append(comparison(actual, expected_pages, 0xb800, 0xba00, 'All 512 D011-page bytes after literal first eight-entry preparation'))
                    assert target == candidates[0], 'First prepared dispatch must select table index zero'
                    assert actual[0x64d7:0x64d9] == b'\x01\x64'
                    assert actual[0x6567:0x6569] == b'\x21\x65'
                    detail['derived_first_preparation_updates'] = updates
                    first_dispatch_seen = True
                if pc == 0x62ea and not first_raster_seen:
                    detail['first_captured_raster_irq'] = True
                    # Root's natural init→first-IRQ capture should precede the
                    # bottom-of-frame preparation coroutine that edits these pages.
                    checks.append(comparison(actual, images[46], 0xb800, 0xba00, 'Original D011 pages at first captured raster IRQ'))
                    first_raster_seen = True
        elif entry46 is not None and part46_guard(actual):
            stage = 'stream46_later_observation'
            observations.append(comparison(actual, images[46], 0x2000, 0xc001, 'Every later full-image difference from original; causal trace proof is separate'))
        else:
            observations.append(dict(scope='No established byte contract for this PC/signature; capture remains observational.'))
        record = dict(file=str(path.relative_to(ROOT)), sha256=sha(actual), registers=register,
                      stage=stage, established_checkpoint=established, checks=checks,
                      observations=observations, detail=detail,
                      exact=all(c['exact'] for c in checks), snapshot=str(snapshot.relative_to(ROOT)),
                      snapshot_sha256=state['file_sha256'],
                      vic_raster=[state['vicii']['raster_line'], state['vicii']['raster_cycle']],
                      vic_registers=state['vicii']['regs'],
                      cia={name:{k:value[k] for k in ('pra','ddra','timer_a','timer_b','cra','crb')}
                           for name, value in state['cia'].items()})
        records.append(record)
    required = {'original_boot_unpacked_handoff', 'resident_installed_before_detection',
                'stream0_natural_entry', 'stream46_natural_entry',
                'stream46_initializer_body_complete', 'stream46_raster_irq_entry',
                'stream46_dispatch'}
    stages = {r['stage'] for r in records}
    complete = required <= stages and not pending
    result = dict(provisional=bool(args.allow_live), session_closed=bool(session.get('closed_utc')),
                  session=session, disk_sha256=DISK_SHA, boot_proof_sha256=BOOT_PROOF_SHA,
                  stream_index_sha256=INDEX_SHA, resident_sha256=RESIDENT_SHA,
                  script_sha256=sha(Path(__file__).read_bytes()),
                  borrowed_reader_sha256={name:sha((ROOT/name).read_bytes()) for name in
                                         ('research/nine/native_capture.py','research/quondam/snapshot_state.py')},
                  maincpu_schema=dict(version=[1,4], clock_payload_slice=[0,8], pc_payload_slice=[12,14],
                                      source='VICE 3.10 src/mainc64cpu.c:883-909',
                                      archive_sha256='8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'),
                  transcript_sha256=sha(text.encode()), checkpoints=records, screenshots=screenshots,
                  pending_capture_events=pending, missing_required_stages=sorted(required-stages),
                  all_native_ram_snapshot_pairs_exact=all(r['checks'][0]['exact'] for r in records),
                  established_checkpoints_exact=all(r['exact'] for r in records if r['established_checkpoint']),
                  complete=complete, scope='Passive original cold-boot byte comparisons and literal finite initializer contracts. No CPU/emulator execution, raster timing proof or independent pixel oracle.')
    result['pass'] = (result['all_native_ram_snapshot_pairs_exact'] and result['established_checkpoints_exact']
                      and (args.allow_live or complete))
    output.mkdir(parents=True, exist_ok=True)
    target = output / ('native-evidence-provisional.json' if args.allow_live else 'native-evidence.json')
    target.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('pass','provisional','complete','missing_required_stages')}, indent=2))
    assert result['pass'], f'Retained mismatches or missing captures in {target}'


if __name__ == '__main__':
    main()
