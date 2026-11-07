#!/usr/bin/env python3
"""Bounded archive/notes inventory of Smash Designs' C64 Second Reality.

No CPU, depacker, emulator, drive, downloaded host program, or C64 program is
executed. The unrelated PC Future Crew source is outside this inventory.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
from html import unescape
import io
import json
from pathlib import Path, PurePosixPath
import re
import urllib.error
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT/'build/research/second-reality'
URLS = (
    ('csdb-release.html', 'https://csdb.dk/release/?id=908'),
    ('demozoo.html', 'https://demozoo.org/productions/19822/'),
    ('csdb-2ndreality.zip', 'https://csdb.dk/getinternalfile.php/71054/2ndreality.zip'),
    ('author-https.zip', 'https://www.smash-designs.de/releases/c64/2nd_reality.zip'),
    ('author-http.zip', 'http://www.smash-designs.de/releases/c64/2nd_reality.zip'),
    ('author-home.html', 'http://www.smash-designs.de/'),
    ('author-c64-releases.html', 'http://www.smash-designs.de/c64demo.html'),
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text(data):
    return re.sub(r'\s+', ' ', unescape(re.sub(r'<[^>]+>', ' ', data))).strip()


def fetch(pair):
    name, url = pair
    item = dict(name=name, requested_url=url, requested_utc=datetime.now(timezone.utc).isoformat())
    try:
        request = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0 C64 original-release research'})
        try:
            response = urllib.request.urlopen(request, timeout=15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = response.read(8_000_001)
            assert len(data) <= 8_000_000
            item.update(http_status=response.status, final_url=response.geturl(),
                        headers={k:response.headers[k] for k in ('Content-Type','Content-Length','ETag','Last-Modified') if k in response.headers},
                        success=200 <= response.status < 300, bytes=len(data), sha256=sha(data))
        target = OUT/name
        if target.exists() and target.read_bytes() != data:
            old = OUT/(name+'.previous-'+sha(target.read_bytes())[:12])
            if not old.exists():
                old.write_bytes(target.read_bytes())
        target.write_bytes(data)
        item['path'] = str(target.relative_to(ROOT))
    except (OSError, urllib.error.URLError, AssertionError) as error:
        item.update(success=False, http_status=None, error_type=type(error).__name__, error=str(error), path=None)
    return item


def directory35(data):
    """Read standard DOS directory entries as data; no loader interpretation."""
    def sector(track, number):
        counts = [21]*17+[19]*7+[18]*6+[17]*5
        assert 1 <= track <= 35 and 0 <= number < counts[track-1]
        offset = 256*(sum(counts[:track-1])+number)
        return data[offset:offset+256]
    track, number, seen, entries = 18, 1, set(), []
    while track:
        assert (track, number) not in seen and len(seen) < 32
        seen.add((track, number))
        page = sector(track, number)
        for i in range(8):
            entry = page[2+i*32:32+i*32]
            if entry[0]:
                name = entry[3:19].rstrip(b'\xa0')
                entries.append(dict(name_hex=name.hex(),
                                    name_ascii_display=''.join(chr(c) if 32 <= c < 127 else '.' for c in name),
                                    file_type=entry[0], track=entry[1], sector=entry[2],
                                    blocks=int.from_bytes(entry[28:30], 'little')))
        track, number = page[:2]
    return dict(directory_sectors=[list(pair) for pair in sorted(seen)], entries=entries,
                scope='Standard DOS directory only. Names do not establish contents or identify raw-loader streams; no PRG or note is run/unpacked.')


def inventory(record):
    path = ROOT/record['path']
    data = path.read_bytes()
    assert sha(data) == record['sha256']
    result = dict(acquisition=record, valid_zip=zipfile.is_zipfile(io.BytesIO(data)), members=[])
    if not result['valid_zip']:
        return result
    folder = OUT/(path.stem+'-members')
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert len(archive.infolist()) <= 100
        assert sum(info.file_size for info in archive.infolist()) <= 8_000_000
        for info in archive.infolist():
            member = PurePosixPath(info.filename)
            assert not member.is_absolute() and '..' not in member.parts and '\\' not in info.filename
            if info.is_dir():
                continue
            body = archive.read(info)
            output = folder.joinpath(*member.parts)
            output.parent.mkdir(parents=True, exist_ok=True)
            assert not output.exists() or output.read_bytes() == body
            output.write_bytes(body)
            row = dict(name=info.filename, path=str(output.relative_to(ROOT)), bytes=len(body), sha256=sha(body), crc32=f'{info.CRC:08x}')
            suffix = member.suffix.lower()
            if suffix == '.d64':
                row['disk_geometry'] = ('35 tracks, 683 sectors, no error bytes' if len(body) == 174848 else
                                        '40 tracks, 768 sectors, no error bytes' if len(body) == 196608 else 'not inferred')
                if len(body) == 174848:
                    row['DOS_directory'] = directory35(body)
            if suffix in ('.asm','.s','.c','.h','.txt','.nfo','.diz','.doc','.md') or member.name.lower().startswith(('readme','license','copying')):
                row['document_or_source_candidate'] = True
                row['text_latin1'] = body.decode('latin1')
            result['members'].append(row)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fetch', action='store_true', help='Retrieve only the explicit original-release/author routes.')
    parser.add_argument('--fetch-missing', action='store_true', help='Fetch new listed routes, retaining earlier success and failure receipts.')
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    ledger = OUT/'acquired-pages.json'
    if args.fetch or args.fetch_missing:
        previous = json.loads(ledger.read_text()) if args.fetch_missing and ledger.exists() else []
        names = {row['name'] for row in previous}
        with ThreadPoolExecutor(max_workers=4) as pool:
            records = previous+list(pool.map(fetch, [pair for pair in URLS if pair[0] not in names]))
        if ledger.exists():
            backup = OUT/('acquired-pages.previous-'+sha(ledger.read_bytes())[:12]+'.json')
            if not backup.exists():
                backup.write_bytes(ledger.read_bytes())
        ledger.write_text(json.dumps(records, indent=2)+'\n')
    else:
        records = json.loads(ledger.read_text())
    by_name = {row['name']:row for row in records}
    release = (ROOT/by_name['csdb-release.html']['path']).read_bytes()
    assert by_name['csdb-release.html']['success']
    release_text = text(release.decode())
    assert 'Second Reality' in release_text and '29 December 1997' in release_text and 'C64 Demo' in release_text
    assert 'C64 Demo Competition at The Party 1997 : #1' in release_text
    if by_name['demozoo.html']['success']:
        demozoo = (ROOT/by_name['demozoo.html']['path']).read_bytes()
        demozoo_text = text(demozoo.decode())
        assert '1st in' in demozoo_text and 'The Party 1997 C64 Demo' in demozoo_text
        author_links = [unescape(url) for url in re.findall(r'href=[\"\']([^\"\']+)', demozoo.decode()) if 'smash-designs.de' in url]
        assert any(url.endswith('/releases/c64/2nd_reality.zip') for url in author_links)
        author_route_provenance = dict(method='Parsed successful raw HTML response', links=author_links)
    else:
        observation_path = OUT/'demozoo-web-observation.json'
        author_route_provenance = json.loads(observation_path.read_text())
        author_route_provenance['observation_file_sha256'] = sha(observation_path.read_bytes())
        author_links = author_route_provenance['author_download_links']
    archives = [inventory(row) for row in records if row['success'] and row['name'].endswith('.zip')]
    csdb_archive = next(row for row in archives if row['acquisition']['name'] == 'csdb-2ndreality.zip')
    assert csdb_archive['valid_zip']
    original_members = sorted((row['name'], row['bytes'], row['sha256']) for row in csdb_archive['members'])
    for archive in archives:
        archive['same_named_payloads_as_current_CSDb'] = sorted((row['name'], row['bytes'], row['sha256']) for row in archive['members']) == original_members
        archive['same_payload_hashes_ignoring_names'] = sorted((row['bytes'], row['sha256']) for row in archive['members']) == sorted((row['bytes'], row['sha256']) for row in csdb_archive['members'])
    author_page_record = by_name['author-c64-releases.html']
    assert author_page_record['success']
    author_page = (ROOT/author_page_record['path']).read_bytes()
    author_decoded = author_page.decode('latin1')
    assert 'Second Reality #1 c64 demo The Party 97' in text(author_decoded)
    assert 'href="releases/c64/2nd_reality.zip"' in author_decoded
    assert any('28.12.97' in entry['name_ascii_display'] for member in csdb_archive['members']
               for entry in member.get('DOS_directory', {}).get('entries', []))
    author_page_evidence = dict(url=author_page_record['final_url'], sha256=sha(author_page),
                                label='Second Reality, #1 C64 demo The Party 97',
                                actual_relative_download_href='releases/c64/2nd_reality.zip',
                                decoding='Latin1 for byte-preserving text inspection; exact bytes/hash retained.')
    result = dict(pass_=True, script_sha256=sha(Path(__file__).read_bytes()),
                  acquisitions=records, author_links_from_Demozoo=author_links,
                  author_route_provenance=author_route_provenance,
                  author_release_page=author_page_evidence,
                  release=dict(title='Second Reality', alias='2nd Reality', groups=['Smash Designs','The Obsessed Maniacs'],
                               platform='Commodore 64', release_date='1997-12-29', party='The Party 1997', C64_demo_rank=1,
                               code=['AEG','DCP'], music=['kb'], graphics=['AEG','Idefix'],
                               sources=['https://csdb.dk/release/?id=908','https://demozoo.org/productions/19822/']),
                  archive_note_scope=dict(outer_text_or_source_files=[m['name'] for m in csdb_archive['members'] if m.get('document_or_source_candidate')],
                                          directory_art_date='28.12.97',
                                          date_scope='Side 1 directory artwork contains this date; catalogues list 29 December 1997. It is not silently used to replace the catalogued release date.',
                                          embedded_notes_or_sources_unproved=True),
                  archives=archives,
                  user_capture_context=dict(raw_title_context='Ultimate64EliteII+SIDKick2350+PDsid8580',
                                            scope='User-supplied recording context only; not a requirement established for the 1997 demo.'),
                  scope='Acquisition, release identity, ZIP integrity, outer document/source inventory and standard DOS directory reading. No CPU, depacker, emulator, drive, native playback, hardware-requirement or pixel claim. Future Crew PC 1993 source is not C64 source.')
    result['pass'] = result.pop('pass_')
    (OUT/'acquisition.json').write_text(json.dumps(result, indent=2)+'\n')
    print(f'C64 Second Reality identity confirmed; {len(archives)} successful ZIP routes; {len(csdb_archive["members"])} current CSDb members inventoried.')


if __name__ == '__main__':
    main()
