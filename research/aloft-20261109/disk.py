#!/usr/bin/env python3
"""Passive original Aloft archive/DOS directory/bootstrap-chain inventory.

This is a byte/record parser. It executes no 6502, drive, loader, emulator,
subprocess, downloaded host program or network request.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import traceback
import zipfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-20261109/disk-analysis'
ORIGINAL = ROOT / 'build/research/frontier-2026/february-analysis/aloft-original.zip'
ORIGINAL_SHA = '275c0873b84dcea8ef03210506481f605e93f9f9b263bd5ce4c75dc39a7a1203'
PRIOR = ROOT / 'build/research/frontier-2026/february-analysis/source-findings.json'
PRIOR_SHA = '8d809ffeffcca90f1bcf7bfb65e99533ab705b6b7013b29b9d5112dbb3276f42'
BOOT_SHA = '7e283e390a10c2b7784ac1885081234c21a754d161e938babd504a13da2ee2e5'
DISK_SHA = {
    'Aloft-Side1.d64': 'd13eae8daeada64bc61772a2dad2d3e62d1a0d30a34b29103119535610e4cfce',
    'Aloft-Side2.d64': 'a40374bc8b59ab13c06d577331dde5d3ccaef23ef5b434762d8ed9700b944d31',
    'Aloft-Side3.d64': '3b2844016e697111fa8ccd1e419bb281e4ffa04ae3f542f01b0ef39f91719a1e',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def sectors_per_track(track):
    assert 1 <= track <= 35
    return 21 if track <= 17 else 19 if track <= 24 else 18 if track <= 30 else 17


def sector(image, track, number):
    assert len(image) == 174848
    assert 1 <= track <= 35 and 0 <= number < sectors_per_track(track)
    offset = (sum(sectors_per_track(t) for t in range(1, track)) + number) * 256
    raw = image[offset:offset + 256]
    assert len(raw) == 256
    return raw, offset


def directory(image):
    bam, bam_offset = sector(image, 18, 0)
    track, number = bam[:2]
    assert (track, number) == (18, 1)
    visited, entries, pages = [], [], []
    while track:
        assert [track, number] not in visited, 'Directory sector cycle'
        visited.append([track, number])
        raw, offset = sector(image, track, number)
        pages.append(dict(track=track, sector=number, image_offset=offset,
            next_track=raw[0], next_sector=raw[1], sha256=sha(raw)))
        for slot in range(8):
            entry = raw[slot * 32:(slot + 1) * 32]
            if not entry[2]:
                continue
            entries.append(dict(index=len(entries), directory_track=track,
                directory_sector=number, slot=slot, image_offset=offset + slot * 32,
                raw_32bytes_hex=entry.hex(), type_byte=entry[2], closed=bool(entry[2] & 128),
                type_low_three_bits=entry[2] & 7, first_track=entry[3], first_sector=entry[4],
                filename_petscii_hex=entry[5:21].hex(), declared_blocks=int.from_bytes(entry[30:32], 'little')))
        track, number = raw[:2]
    return dict(BAM=dict(image_offset=bam_offset, sha256=sha(bam),
        raw_256bytes_hex=bam.hex(), disk_name_petscii_hex=bam[144:160].hex(),
        disk_ID_petscii_hex=bam[162:164].hex(), DOS_type_hex=bam[165:167].hex()),
        pages=pages, entries=entries, final_link=[track, number])


def file_chain(image, start_track, start_sector):
    track, number = start_track, start_sector
    visited, chunks, records = [], [], []
    while track:
        assert [track, number] not in visited, 'File sector cycle'
        visited.append([track, number])
        raw, offset = sector(image, track, number)
        next_track, next_sector = raw[:2]
        if next_track:
            payload = raw[2:]
        else:
            assert 1 <= next_sector <= 255
            payload = raw[2:next_sector + 1]
            assert len(payload) == next_sector - 1
        records.append(dict(track=track, sector=number, image_offset=offset,
            next_track=next_track, next_sector_or_last_byte_plus_one=next_sector,
            data_first_in_sector=2, data_bytes=len(payload),
            sector_sha256=sha(raw), data_sha256=sha(payload)))
        chunks.append(payload)
        track, number = next_track, next_sector
    return b''.join(chunks), records


def disk_inventory(name, image, output):
    assert name in DISK_SHA and len(image) == 174848 and sha(image) == DISK_SHA[name]
    info = directory(image)
    entries = info['entries']
    assert len(entries) == 48 and [row['sector'] for row in info['pages']] == list(range(1, 7))
    assert all(row['directory_track'] == 18 for row in entries)
    assert all(row['type_byte'] == 0x82 and (row['first_track'], row['first_sector']) == (18, 7) for row in entries)
    assert [row['declared_blocks'] for row in entries] == [4] + [0] * 47
    bootstrap, chain = file_chain(image, 18, 7)
    assert [(row['track'], row['sector']) for row in chain] == [(18, n) for n in range(7, 11)]
    assert [row['data_bytes'] for row in chain] == [254, 254, 254, 70]
    assert len(bootstrap) == 832 and sha(bootstrap) == BOOT_SHA
    assert bootstrap[:2] == bytes.fromhex('0108')
    assert bootstrap[2:17] == bytes.fromhex('0b080a009e32303634000000000000')
    entry_prefix = bytes.fromhex('a9ff85fca204a90885baa5ba200ceda96f20b9ed303aa5ba85fb20fe')
    assert bootstrap[17:17 + len(entry_prefix)] == entry_prefix
    boot_name = 'bootstrap-' + name.removesuffix('.d64').lower().replace('aloft-', '') + '.prg'
    (output / boot_name).write_bytes(bootstrap)
    for row in entries:
        row['logical_file_chain_identity'] = [18, 7]
        row['recovered_PRG_sha256'] = BOOT_SHA
    info['bootstrap'] = dict(output_name=boot_name, bytes=len(bootstrap), sha256=BOOT_SHA,
        physical_chain=chain, distinct_start_chains=1, load_address=0x801,
        loaded_payload_bytes=830, loaded_end_exclusive=0xb3f,
        BASIC_line_number=10, BASIC_next_line=0x80b, BASIC_SYS_decimal=2064,
        entry=0x810, entry_prefix_hex=entry_prefix.hex(),
        authentic_DOS_PRG=True, directory_art_aliases_same_PRG=48,
        independent_side_boot_success_not_established=True)
    info['image'] = dict(name=name, bytes=len(image), sha256=sha(image),
        geometry=dict(tracks=35, sectors=683, bytes_per_sector=256, error_trailer_bytes=0))
    return info


def run(output):
    output.relative_to(BASE)
    output.mkdir(parents=True, exist_ok=False)
    source = Path(__file__).read_bytes()
    (output / 'disk.checked.py').write_bytes(source)
    try:
        assert artifact(ORIGINAL)['sha256'] == ORIGINAL_SHA and ORIGINAL.stat().st_size == 419712
        assert artifact(PRIOR)['sha256'] == PRIOR_SHA
        prior = json.loads(PRIOR.read_text())
        assert prior['pass']
        acquisitions = [row for row in prior['acquisitions'] if row['requested_url'] == 'https://csdb.dk/getinternalfile.php/276871/Aloft.zip']
        assert len(acquisitions) == 1 and acquisitions[0]['artifact'] == artifact(ORIGINAL)
        assert acquisitions[0]['status'] == 200 and acquisitions[0]['success']
        expected = [row for row in prior['original_archives'] if row['artifact'] == artifact(ORIGINAL)]
        assert len(expected) == 1
        expected_members = {row['name']: row for row in expected[0]['members']}
        members, disks = [], []
        with zipfile.ZipFile(ORIGINAL) as archive:
            assert len(archive.infolist()) == 8 and len({i.filename for i in archive.infolist()}) == 8
            for item in archive.infolist():
                name = PurePosixPath(item.filename)
                assert not name.is_absolute() and '..' not in name.parts
                raw = archive.read(item)
                row = dict(name=item.filename, bytes=len(raw), sha256=sha(raw),
                    ZIP_crc32=item.CRC, ZIP_compression=item.compress_type,
                    ZIP_compressed_bytes=item.compress_size, directory=item.is_dir())
                if item.is_dir():
                    assert item.filename == 'SID/' and not raw
                else:
                    assert dict(name=item.filename, bytes=len(raw), sha256=sha(raw)) == expected_members[item.filename]
                    path = output / item.filename
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(raw)
                    if item.filename in DISK_SHA:
                        disks.append(disk_inventory(item.filename, raw, output))
                    else:
                        assert item.filename.startswith('SID/') and item.filename.endswith('.sid')
                members.append(row)
        assert len(disks) == 3 and len([row for row in members if not row['directory']]) == 7
        assert {row['bootstrap']['sha256'] for row in disks} == {BOOT_SHA}
        (output / 'directory-inventory.json').write_text(json.dumps(disks, indent=2) + '\n')
        outputs = [dict(name=str(path.relative_to(output)), bytes=path.stat().st_size, sha256=sha(path.read_bytes()))
            for path in sorted(output.rglob('*')) if path.is_file()]
        proof = dict(pass_=True, scope='Original Aloft archive members, DOS directory records and authentic bootstrap sector chains only.',
            producer=artifact(Path(__file__)), original_archive=artifact(ORIGINAL),
            prior_acquisition_receipt=artifact(PRIOR), original_acquisition=acquisitions[0],
            archive_members=members, disks=[dict(name=row['image']['name'], image=row['image'],
                directory_entries=len(row['entries']), directory_pages=row['pages'], bootstrap=row['bootstrap']) for row in disks],
            all_three_bootstrap_PRGs_identical=True, DOS_entry_count=144, distinct_bootstrap_byte_objects=1,
            outputs=outputs,
            limits=['No loader/depacker algorithm, custom disk-resource format, loaded part entry, native bootstrap success, rendering, input consumer, pixels or timing is established.',
                'Every decorative DOS entry is an alias to the same four-sector bootstrap on its disk;144entries do not imply144independentfiles.',
                'A BASIC SYS entry and identical bootstrap on all sides do not prove standalone side2/side3 boot or intended side sequencing.',
                'No assembly/text source member is in the ZIP; embedded D64 source/notes remain unexamined.',
                'Only passive integer/record/ZIP parsing is executed. No CPU, drive, emulator, native process, build, socket or downloaded host program is executed.'])
        (output / 'disk-proof.json').write_text(json.dumps(proof, indent=2) + '\n')
        print(json.dumps(dict(pass_=True, proof=artifact(output / 'disk-proof.json'),
            original_disks=3, directory_entries=144, distinct_bootstrap_hashes=1, bootstrap_bytes=832)))
    except Exception as error:
        (output / 'failure.json').write_text(json.dumps(dict(pass_=False, error=repr(error),
            traceback=traceback.format_exc(), producer_sha256=sha(source)), indent=2) + '\n')
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    run(parser.parse_args().output.resolve())
