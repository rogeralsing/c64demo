#!/usr/bin/env python3
"""Passive source-bound Aloft drive construction and directory-state catalog."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-20261109/loader-analysis'
SOURCE = BASE / 'catalog-source-02'
OLD_SOURCE = BASE / 'catalog-source-01'
DISK = ROOT / 'build/research/aloft-20261109/disk-analysis/accepted-01'
COMMIT = 'f354e3b52c9361bf89ebad4f2f1d43504c213381'
PINS = {
    'sparkle.cpp': '270767bed77d894a468ff74c4bfd40ae707663db80713364193dff13ee6e64ee',
    'packer.cpp': 'bb60128abbe2c5af5f3a1965f7ea66a5f4ef3bcb2523b2a8324758555bb32a6a',
    'resources__sd.asm': '7d6b673ff21f6efef523e04d9fb46a53eb05852d4a7182109365d33af684510a',
    'sd.cpp': '0e28b8eb743494fab9ad6f914f047d05f4b729c4cc000820267172951ef06537',
    'common.h': 'e78291be67860af5ddc407c64713bebab7e1e08ac8ee78f0dd4751a5428a45f5',
    'loader.cpp': '78649471dfd302500e0c0b8053869043879d87e0566a450f2eb2e7b041e1162d',
    'resources__sl.asm': '46b28b74e9d2528b808e0c3fd0df08ef0ce7537d4a143527932bee46d9dcab60',
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def meta(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': digest(data)}


def encode(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def load_pin(path, expected):
    data = path.read_bytes()
    assert digest(data) == expected, str(path)
    return data


def array(text, name):
    m = re.search(r'unsigned char ' + name + r'\[' + name + r'_size\] = \{(.*?)\};', text, re.S)
    assert m
    result = bytes(int(v, 16) for v in re.findall(r'0x([\da-fA-F]{2})', m[1]))
    declared = re.search(r'const int ' + name + r'_size = (\d+);', text)
    assert declared and len(result) == int(declared[1])
    return result


def sectors(track):
    assert 1 <= track <= 40
    return 21 if track <= 17 else 19 if track <= 24 else 18 if track <= 30 else 17


def sector(data, track, number):
    assert 0 <= number < sectors(track)
    offset = (sum(sectors(t) for t in range(1, track)) + number) * 256
    assert offset + 256 <= len(data)
    return data[offset:offset + 256]


def transform(value):
    """Source EORtransform, an involution on all 256 possible bytes."""
    assert 0 <= value <= 255
    return value ^ (0x7F if value & 9 in (0, 9) else 0x76)


def reverse_sector(block):
    assert len(block) == 256
    return bytes(block[(-i) & 255] for i in range(256))


def bcd(value):
    assert 0 <= value < 100
    return (value // 10) * 16 + value % 10


def source_version(text):
    def integer(name):
        m = re.search(r'constexpr int ' + name + r' = (\d+);', text)
        assert m
        return int(m[1])
    date = integer('FullDate')
    return [16 * integer('VersionMajor') + integer('VersionMinor'),
            bcd((date // 10000) % 100), bcd((date // 100) % 100), bcd(date % 100)]


def predicted_drive(sd, version, bam):
    """Typed host data construction, not execution of upstream C++ or 6502."""
    assert len(sd) <= 1536
    drive = bytearray(1536)  # Upstream explicitly declares Drive[6*256]{}.
    drive[:len(sd)] = sd
    block3 = bytes(drive[0x300:0x400])
    for offset, value in zip([0x2F, 0x32, 0x3D, 0x3F], version):
        drive[offset] = value
    drive[0x5FC:0x600] = bytes(version)
    product = bytes(transform(bam[i]) for i in [0xF9, 0xF8, 0xF7])
    drive[0x6B:0x6E] = product
    drive[0x300:0x400] = drive[0x400:0x500]
    drive[0x400:0x500] = drive[0x500:0x600]
    drive[0x500:0x600] = block3
    inverse_interleave_and_next = bytes(transform(bam[i]) for i in [0xFE, 0xFD, 0xFC, 0xFB, 0xFA])
    drive[0x360:0x365] = inverse_interleave_and_next
    return bytes(drive), {
        'version_BCD': version, 'product_ID_hex': product.hex(),
        'next_side_ID_encoded_domain': inverse_interleave_and_next[3],
        'side_ID_encoded_domain': transform(bam[0xFF]),
        'interleaves_IL0_IL1_IL2_IL3': [
            (-inverse_interleave_and_next[i]) & 255 for i in [4, 2, 1, 0]],
        'BAM_input_offsets': [0xF7, 0xF8, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF],
    }


def calc_tabs(interleaves, tracks=35):
    """Source CalcTabs sector-order recurrence; explicit D64 track geometry."""
    table = []
    starts = {}
    current_sector = 0
    for track in range(1, tracks + 1):
        if track == 18:
            current_sector += 2
            continue
        maximum = sectors(track)
        zone = 0 if track <= 17 else 1 if track <= 24 else 2 if track <= 30 else 3
        step = interleaves[zone] % maximum
        assert 0 < step < maximum
        visited = set()
        if current_sector >= maximum:
            current_sector -= maximum
            if current_sector > 0:
                current_sector -= 1
        starts[track] = current_sector
        while len(visited) < maximum:
            assert 0 <= current_sector < maximum
            if current_sector not in visited:
                table.append({'block_ordinal': len(table), 'track': track, 'sector': current_sector,
                              'start_sector_on_track': starts[track],
                              'remaining_sectors_on_track': maximum - len(visited)})
                visited.add(current_sector)
                current_sector += step
                if current_sector >= maximum:
                    current_sector -= maximum
                    if current_sector > 0:
                        current_sector -= 1
            else:
                current_sector += 1
                if current_sector >= maximum:
                    current_sector = 0
        assert len(visited) == maximum
    assert len(table) == sum(sectors(t) for t in range(1, tracks + 1) if t != 18)
    return table


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to(BASE) and out.name.startswith('catalog-')
    out.mkdir(parents=True, exist_ok=False)
    disk_proof_path = DISK / 'disk-proof.json'
    disk_proof = json.loads(load_pin(disk_proof_path,
        '113eadc069fbf46bb1011d7c9373d175f4c3536950f7a7ee173f471b8f1eef84'))
    assert disk_proof['pass_']
    source = {name: load_pin(SOURCE / name, value).decode() for name, value in PINS.items()}
    tree_path = SOURCE / 'tree.body'
    tree = json.loads(load_pin(tree_path,
        '0aabf92bc2d4a3413ad4349bc7b1901ccffe04a5021548062a65415f02ed2dc4'))
    assert tree['sha'] == COMMIT and not tree['truncated']
    tree_blobs = {row['path']: row['sha'] for row in tree['tree']}
    source_metadata = []
    retrieval_metadata = [meta(SOURCE / 'tree.body.response.json')]
    for name in PINS:
        path = SOURCE / name
        remote_path = name.replace('__', '/')
        payload = path.read_bytes()
        response = json.loads((SOURCE / (name + '.response.json')).read_bytes())
        assert response['status'] == 200 and COMMIT in response['url']
        assert response['url'] == 'https://raw.githubusercontent.com/spartaomg/SparkleCPP/' + COMMIT + '/' + remote_path
        assert response['final_url'] == response['url']
        assert response['bytes'] == len(payload) and response['sha256'] == digest(payload)
        blob = hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest()
        assert blob == tree_blobs[remote_path]
        source_metadata.append({**meta(path), 'original_url': response['url'], 'Git_blob_SHA1': blob})
        retrieval_metadata.append(meta(SOURCE / (name + '.response.json')))
    cpp = source['sparkle.cpp']
    version = source_version(cpp)
    assert version == [0x33, 0x25, 0x12, 0x30]
    # Complete pinned files plus these clauses bind each named pure transformation.
    for clause in ['unsigned char Drive[6 * 256]{};', 'int VI = 0x2f;', 'int PID = 0x6b;',
                   'Drive[(3 * 256) + i] = Drive[(4 * 256) + i];',
                   'Drive[(4 * 256) + i] = Drive[(5 * 256) + i];',
                   'Drive[(5 * 256) + i] = B3[i];', 'int ZPILTabLoc = 0x60;',
                   'Disk[Track[18] + (17 * 256) + i] = DirBlocks[i];',
                   'TabSCnt[i] = SMax - SCnt;', 'if (S > 0)', 'S += 2;']:
        assert clause in cpp
    assert 'ByteSt[((BufferCnt - 1) * 256) + B] = Buffer[i];' in source['packer.cpp']
    assert all(transform(transform(v)) == v for v in range(256))
    assert all(reverse_sector(reverse_sector(bytes(range(256))))[v] == v for v in range(256))
    sd = array(source['sd.cpp'], 'sd')
    assert len(sd) == 1427
    loader = array(source['loader.cpp'], 'loader')
    assert len(loader) == 832
    source_line_contract = {
        'version': [13, 23], 'EORtransform': [684, 698], 'directory_injection': [702, 789],
        'drive_injection': [5698, 5864], 'sector_order': [6079, 6181],
        'packer_sector_permutation': [99, 127],
    }
    sides = []
    input_meta = [meta(disk_proof_path)]
    for number in range(1, 4):
        path = DISK / f'Aloft-Side{number}.d64'
        d64 = path.read_bytes()
        expected_disk = next(x for x in disk_proof['outputs'] if x['name'] == path.name)
        assert digest(d64) == expected_disk['sha256'] and len(d64) == 174848
        input_meta.append(meta(path))
        boot_path = DISK / f'bootstrap-side{number}.prg'
        boot = load_pin(boot_path, '7e283e390a10c2b7784ac1885081234c21a754d161e938babd504a13da2ee2e5')
        input_meta.append(meta(boot_path))
        differences = [{'PRG_offset': i, 'CPU_address': i + 0x7FF, 'reference': a, 'original': b}
                       for i, (a, b) in enumerate(zip(loader, boot)) if a != b]
        assert differences == [
            {'PRG_offset': 0xFB, 'CPU_address': 0x8FA, 'reference': 0x10, 'original': 0xFD},
            {'PRG_offset': 0xFE, 'CPU_address': 0x8FD, 'reference': 0xAD, 'original': 0xFF},
        ]
        bam = sector(d64, 18, 0)
        predicted, parameters = predicted_drive(sd, version, bam)
        actual_drive = b''.join(sector(d64, 18, s) for s in range(11, 17))
        assert predicted == actual_drive
        (out / f'side{number}-predicted-drive.bin').write_bytes(predicted)
        table = calc_tabs(parameters['interleaves_IL0_IL1_IL2_IL3'])
        by_state = {(r['track'], r['start_sector_on_track'], r['remaining_sectors_on_track']): r
                    for r in table}
        assert len(by_state) == len(table)
        logical = b''.join(reverse_sector(sector(d64, 18, s)) for s in [17, 18])
        entries = []
        for index in range(128):
            raw = logical[4 * index:4 * index + 4]
            t, start, remaining = [transform(v) for v in raw[:3]]
            assert t & 0x80 == 0  # No plugin entry is silently treated as compressed data.
            state = by_state[(t, start, remaining)]
            entries.append({'slot': index, 'stored_logical_bytes_hex': raw.hex(),
                            'track': t, 'start_sector_on_track': start,
                            'remaining_sectors_on_track': remaining, 'stream_pointer': raw[3],
                            'derived_first_block': {'track': t, 'sector': state['sector'],
                                                    'block_ordinal': state['block_ordinal']}})
        unique = {(x['track'], x['start_sector_on_track'], x['remaining_sectors_on_track'], x['stream_pointer'])
                  for x in entries}
        file_name = f'side{number}-directory-slots.json'
        (out / file_name).write_bytes(encode(entries))
        # A byte-level forward inverse check, separate from the source recurrence checks.
        reconstructed = b''.join(bytes([transform(x['track']), transform(x['start_sector_on_track']),
                                         transform(x['remaining_sectors_on_track']), x['stream_pointer']])
                                 for x in entries)
        assert reconstructed == logical
        assert b''.join(reverse_sector(reconstructed[i:i + 256]) for i in [0, 256]) == b''.join(
            sector(d64, 18, s) for s in [17, 18])
        sides.append({'side': number, 'parameters_from_BAM': parameters,
                      'full_drive_bytes_compared': 1536, 'drive_mismatches': 0,
                      'predicted_drive_sha256': digest(predicted),
                      'canonical_loader_bytes_compared': 832, 'canonical_loader_differences': differences,
                      'directory_slots': 128, 'distinct_drive_state_and_pointer_records': len(unique),
                      'directory_slots_file': file_name, 'all_slots_match_source_sector_order': True,
                      'directory_encoded_bytes_roundtripped': 512,
                      'regular_data_sectors_in_source_order': len(table)})
    assert [s['distinct_drive_state_and_pointer_records'] for s in sides] == [44, 29, 40]
    (out / 'catalog.checked.py').write_bytes(Path(__file__).read_bytes())
    proof = {
        'pass_': True, 'scope': 'Original drive construction and 384 directory slots, not resource decoding',
        'producer': meta(Path(__file__).resolve()), 'source_commit': COMMIT,
        'source': source_metadata, 'source_tree': meta(tree_path),
        'retrieval_metadata': retrieval_metadata,
        'source_line_contract': source_line_contract, 'inputs': input_meta,
        'source_version_BCD': version, 'canonical_sd_bytes': len(sd), 'canonical_sd_sha256': digest(sd),
        'canonical_loader_sha256': digest(loader), 'sides': sides,
        'finite_checks': {'EOR_involution_values': 256, 'sector_permutation_indices': 256},
        'outputs': [{'name': f.name, 'bytes': f.stat().st_size, 'sha256': digest(f.read_bytes())}
                    for f in sorted(out.iterdir())],
        'limits': [
            'No upstream source, host binary, CPU, emulator, native process or build was executed.',
            'Exact original drive bytes bind this implementation; they do not prove the precise host executable/build used.',
            'BAM bytes are declared parameter inputs; original drive sectors are comparison oracles only.',
            'Directory slots may alias or pad to a prior/default bundle. Distinct slot records are not a count of resources or scenes.',
            'First sector on track in the directory is not the first sector of its bundle; the latter is derived via source CalcTabs.',
            'No complete packed resource, resource end, match dependency or layered-pattern part has been decoded or identified.',
            'Plugin-marked track fields reject rather than being silently normalized; none occur in these three directories.',
        ],
    }
    (out / 'catalog-proof.json').write_bytes(encode(proof))
    print(json.dumps({'pass_': True, 'sides': 3, 'drive_bytes': 4608,
                      'directory_slots': 384, 'distinct_states': [44, 29, 40]}))


if __name__ == '__main__':
    main()
