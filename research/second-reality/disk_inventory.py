#!/usr/bin/env python3
"""Inventory pinned Second Reality DOS chains and literal text without execution.

Only original on-disk directory/sector links, PRG headers and static character
bytes are interpreted. Packed bytes are never treated as renderer instructions.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import struct
import zlib

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/second-reality'
ACQUISITION_SHA = 'df052184703650f3622fb977992cf28d457c42f0171a50a11fa4cf2492f06a8f'
DISK_HASHES = (
    '05aa03c00be26cab0618f8802477d0bc7226af029c003a253a34bd32c630acf2',
    '0f61c5fd673d2c0cd63d43feeca4bf9e49686c8f06df0dd69a2ff2415f5c9c17',
)
SECTORS = [21]*17 + [19]*7 + [18]*6 + [17]*5
WORDS = re.compile(r'SECOND|REALITY|SMASH|GRAF|GRAPH|MUSIC|CODE|OBJECT|ANIM|LOADER|SOURCE|NOTE|READ|START|DOS|POINT|CRED|DESIGN|VECTOR|CUBE|PLASMA|ZOOM|AEG|DCP|IDEFIX|SONEY|T[.]O[.]M|NICE|PARTY|FLOPPY', re.I)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def relative(path):
    return str(Path(path).resolve().relative_to(ROOT))


def record(path):
    data = Path(path).read_bytes()
    return dict(path=relative(path), bytes=len(data), sha256=sha(data))


def disk_offset(track, sector):
    if not (1 <= track <= 35 and 0 <= sector < SECTORS[track-1]):
        raise ValueError(f'Invalid track/sector {track}/{sector}')
    return 256 * (sum(SECTORS[:track-1]) + sector)


def page(data, track, sector):
    offset = disk_offset(track, sector)
    result = data[offset:offset+256]
    assert len(result) == 256
    return result


def display(raw):
    """ASCII subset of PETSCII only; raw bytes remain authoritative."""
    return ''.join(chr(value) if 32 <= value < 127 else '.' for value in raw)


def directory(data):
    track, sector, seen, entries, pages = 18, 1, set(), [], []
    while track:
        assert (track, sector) not in seen and len(seen) < 683
        seen.add((track, sector))
        body = page(data, track, sector)
        pages.append(dict(track=track, sector=sector, disk_offset=disk_offset(track, sector), sha256=sha(body)))
        for slot in range(8):
            offset = 2+slot*32
            raw = body[offset:offset+30]
            assert len(raw) == 30
            if not raw[0]:
                continue
            name = raw[3:19].rstrip(b'\xa0')
            entries.append(dict(index=len(entries), directory_track=track, directory_sector=sector,
                                slot=slot, disk_offset=disk_offset(track, sector)+offset,
                                raw_entry_hex=raw.hex(), name_hex=name.hex(), name_ascii_subset=display(name),
                                two_byte_name_prefix_hex=name[:2].hex(), two_byte_name_prefix_ascii=display(name[:2]),
                                type_byte=raw[0], type_low_bits=raw[0]&7, closed=bool(raw[0]&128), locked=bool(raw[0]&64),
                                start_track=raw[1], start_sector=raw[2], declared_blocks=int.from_bytes(raw[28:30], 'little')))
        track, sector = body[:2]
    return pages, entries


def follow_chain(data, track, sector):
    seen, sectors, payload, segments = set(), [], bytearray(), []
    termination = None
    while True:
        if (track, sector) in seen:
            termination = dict(kind='cycle', track=track, sector=sector)
            break
        try:
            body = page(data, track, sector)
        except ValueError as error:
            termination = dict(kind='invalid_pointer', track=track, sector=sector, error=str(error))
            break
        seen.add((track, sector))
        next_track, next_sector = body[:2]
        used = 254 if next_track else next_sector-1
        sectors.append(dict(track=track, sector=sector, disk_offset=disk_offset(track, sector), sha256=sha(body),
                            next_track=next_track, next_sector_or_last_count=next_sector, payload_bytes=used))
        if not 0 <= used <= 254:
            termination = dict(kind='invalid_last_count', track=track, sector=sector, count=next_sector)
            break
        segments.append(dict(file_offset=len(payload), disk_offset=disk_offset(track, sector)+2, bytes=used,
                             track=track, sector=sector))
        payload.extend(body[2:2+used])
        if next_track == 0:
            termination = dict(kind='valid_eof', track=track, sector=sector, last_sector_payload_bytes=used)
            break
        assert len(seen) <= 683
        track, sector = next_track, next_sector
    return bytes(payload), sectors, segments, termination


def literal_strings(data, encoding):
    """Return candidates, never proof that an arbitrary byte run is displayed."""
    if encoding == 'ascii':
        translated = ''.join(chr(value) if 32 <= value <= 126 else '\n' for value in data)
    elif encoding == 'screen-upper-subset':
        translated = ''.join(chr(64+value) if 1 <= value <= 26 else chr(value) if 32 <= value <= 63 else '\n' for value in data)
    elif encoding == 'screen-lower-subset':
        translated = ''.join(chr(96+value) if 1 <= value <= 26 else chr(value) if 32 <= value <= 90 else '\n' for value in data)
    else:
        raise ValueError(encoding)
    result = []
    for match in re.finditer(r'[^\n]{6,}', translated):
        value = match.group()
        if not re.search(r'[A-Za-z]{3}', value):
            continue
        result.append(dict(offset=match.start(), bytes=len(value), text=value,
                           raw_hex=data[match.start():match.end()].hex(), encoding=encoding,
                           keyword_candidate=bool(WORDS.search(value))))
    return result


def locate_file_byte(segments, offset):
    for segment in segments:
        if segment['file_offset'] <= offset < segment['file_offset']+segment['bytes']:
            return dict(track=segment['track'], sector=segment['sector'],
                        disk_offset=segment['disk_offset']+offset-segment['file_offset'])
    raise ValueError(offset)


def basic_lines(data):
    """Recognize only a literal well-linked BASIC header, without evaluating it."""
    if len(data) < 8:
        return []
    load = int.from_bytes(data[:2], 'little')
    cursor, lines = 2, []
    for _ in range(100):
        if cursor+2 > len(data):
            return []
        next_address = int.from_bytes(data[cursor:cursor+2], 'little')
        if not next_address:
            return lines
        next_offset = next_address-load+2
        if not (cursor+5 <= next_offset <= len(data)) or data[next_offset-1] != 0:
            return []
        body = data[cursor+4:next_offset-1]
        tokens = []
        for byte in body:
            tokens.append({0x9e:'{SYS}', 0x8f:'{REM}'}.get(byte, chr(byte) if 32 <= byte <= 126 else f'{{${byte:02X}}}'))
        lines.append(dict(file_offset=cursor, nominal_address=load+cursor-2,
                          next_address=next_address, line_number=int.from_bytes(data[cursor+2:cursor+4], 'little'),
                          body_hex=body.hex(), text=''.join(tokens)))
        cursor = next_offset
    return []


def credits_table(file_row):
    """Inventory the literal FE-separated table; do not invent effect names."""
    data = (ROOT/file_row['extracted']['path']).read_bytes()
    assert file_row['extracted']['sha256'] == '831a75966bd9d60bcbf4c54544dd9a967d3e7b945a45f9180f59908b24af4c9e'
    first, end = 0x3bc, 0x60a
    raw = data[first:end]
    assert raw.startswith(bytes.fromhex('c08847524146494353202d20414547')) and raw[-1] == 255
    assert raw.count(254) == 20 and raw.count(255) == 1
    blocks, cursor = [], first
    for index, part in enumerate(raw[:-1].split(bytes([254]))):
        strings = [dict(file_offset=cursor+match.start(), text=match.group().decode('ascii'),
                        location=locate_file_byte(file_row['file_segments'], cursor+match.start()))
                   for match in re.finditer(rb'[ -~]{6,}', part)]
        blocks.append(dict(ordinal=index, file_offset=cursor, bytes=len(part), raw_hex=part.hex(),
                           strings=strings, sha256=sha(part)))
        cursor += len(part)+1
    assert cursor == end
    return dict(file_id=file_row['file_id'], file_offset=first, end_exclusive=end, bytes=end-first, sha256=sha(raw),
                delimiter_hex='fe', terminal_hex='ff', block_count=len(blocks), blocks=blocks,
                scope='Literal adjacent credit strings grouped by stored FE separators. Ordinals are table order, not identified runtime part numbers or effect names.')


def inspect_embedded_note(memory_path, native_path, output):
    """Read an existing independently unpacked full RAM image, never execute it."""
    memory = memory_path.read_bytes()
    assert len(memory) == 65536
    mask_path = memory_path.with_name('file-derived-known-mask.bin')
    owner_proof_path = memory_path.with_name('boot-proof.json')
    owner_boot_path = memory_path.with_name('side1-boot.prg')
    mask = mask_path.read_bytes()
    owner_proof = json.loads(owner_proof_path.read_text())
    assert owner_proof['pass'] and owner_proof['disk_sha256'] == DISK_HASHES[0]
    assert owner_proof['boot_sha256'] == sha(owner_boot_path.read_bytes()) == 'c62598561f3bb6d74e9c399385df6e1dd21890c9fc0abbd952a2a61548a286f5'
    assert owner_proof['RAM_only_decompressor']['RAM_sha256'] == sha(memory)
    assert len(mask) == 65536 and owner_proof['RAM_only_decompressor']['known_mask_sha256'] == sha(mask)
    first, end, width = 0xb000, 0xb800, 32
    raw = memory[first:end]
    assert all(mask[first:end])
    def character(value):
        if 1 <= value <= 26:
            return chr(value+96)
        if 0x81 <= value <= 0x9a:
            return chr(value-0x80+64)
        if 32 <= value <= 63:
            return chr(value)
        if value == 0xa0:
            return ' '
        raise ValueError(f'Unsupported note glyph ${value:02X}')
    rows = [''.join(character(value) for value in raw[i:i+width]) for i in range(0,len(raw),width)]
    assert len(rows) == 64 and 'signed: AEG/Smash-Designs' in rows[-1]
    assert rows[0].strip() == 'Smash-Designs 1997'
    raw_path, text_path = output/'info1sds-note.raw', output/'info1sds-note-rows.txt'
    raw_path.write_bytes(raw)
    text_path.write_text('\n'.join(rows)+'\n')
    # Render the actual stored a-z/A-Z font bytes to make the character mapping
    # inspectable. This is a glyph sheet, not an emulated screen or edited image.
    codes = list(range(1,27))+list(range(0x81,0x9b))
    pixels = [[255]* (26*8*3) for _ in range(16)]
    glyphs = []
    for index,code in enumerate(codes):
        address = 0xb800+8*code
        body = memory[address:address+8]
        assert all(mask[address:address+8])
        glyphs.append(dict(code=code, letter=character(code), font_address=address, bytes_hex=body.hex()))
        for y in range(8):
            for x in range(8):
                value = 255 if body[y] & (128>>x) else 0
                target_x, target_y = (index%26)*8+x, (index//26)*8+y
                pixels[target_y][target_x*3:target_x*3+3] = [value]*3
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    png_path = output/'note-alphabet-font.png'
    png_path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',208,16,8,2,0,0,0))
                         +chunk(b'IDAT',zlib.compress(b''.join(b'\0'+bytes(row) for row in pixels),9))+chunk(b'IEND',b''))
    result = dict(memory=record(memory_path), known_mask=record(mask_path), owner_boot_proof=record(owner_proof_path),
                  owner_boot_prg=record(owner_boot_path), all_note_and_alphabet_bytes_known=True,
                  note_first=first, note_end_exclusive=end, note_bytes=len(raw),
                  rows=64, columns=32, note=record(raw_path), decoded_rows=record(text_path),
                  character_mapping='01..1A -> a..z; 81..9A -> A..Z; 20..3F -> ASCII punctuation/digits; A0 -> space.',
                  font_base=0xb800, font_glyph_sheet=record(png_path), alphabet_glyphs=glyphs,
                  scope='Passive decoding of the independently recovered note and its stored alphabet glyphs. No DOS-emulation command, text reader, CPU or VIC was executed here.')
    commands = []
    for address,length in ((0x9940,13), (0x9960,17)):
        raw_command = memory[address:address+32]
        assert all(mask[address:address+32])
        decoded = ''.join(character(value) for value in raw_command[:length])
        assert decoded.startswith('read info1sds')
        commands.append(dict(address=address, raw_hex=raw_command.hex(), text=decoded, decoded_prefix_bytes=length,
                             remaining_bytes_scope='Padding/command-table bytes retained raw; not decoded with the note alphabet.'))
    result['literal_dos_command_strings'] = commands
    if native_path:
        native = native_path.read_bytes()
        assert len(native)==65536
        result['native_corroboration'] = dict(memory=record(native_path),
                                              note_exact=native[first:end]==raw,
                                              alphabet_glyphs_exact=all(native[g['font_address']:g['font_address']+8]==memory[g['font_address']:g['font_address']+8] for g in glyphs),
                                              scope='Existing original native first-entry bytes only; no new playback or timing/pixel claim.')
        assert result['native_corroboration']['note_exact'] and result['native_corroboration']['alphabet_glyphs_exact']
    return result


def inventory(side, member, output):
    path = ROOT / member['path']
    data = path.read_bytes()
    assert len(data) == 174848 and sha(data) == DISK_HASHES[side-1] == member['sha256']
    pages, entries = directory(data)
    # Cross-check the earlier independently recorded directory, including every
    # raw filename and declared value. This parser owns its chain analysis.
    old = member['DOS_directory']['entries']
    assert len(old) == len(entries)
    for actual, expected in zip(entries, old):
        assert (actual['name_hex'], actual['type_byte'], actual['start_track'], actual['start_sector'], actual['declared_blocks']) == (
            expected['name_hex'], expected['file_type'], expected['track'], expected['sector'], expected['blocks'])
    files, owners = [], defaultdict(list)
    for entry in entries:
        if entry['type_low_bits'] != 2:
            entry['chain_scope'] = 'DEL/decorative entry; pointer retained but not interpreted as a live PRG file.'
            continue
        file_id = f'side{side}-entry{entry["index"]:02d}-{entry["two_byte_name_prefix_ascii"]}'
        body, sectors, segments, termination = follow_chain(data, entry['start_track'], entry['start_sector'])
        target = output / (file_id + '.prg')
        target.write_bytes(body)
        for sector in sectors:
            owners[(sector['track'], sector['sector'])].append(file_id)
        load = int.from_bytes(body[:2], 'little') if len(body) >= 2 else None
        row = dict(file_id=file_id, directory_entry_index=entry['index'], name_ascii_subset=entry['name_ascii_subset'],
                   name_hex=entry['name_hex'], name_prefix_ascii=entry['two_byte_name_prefix_ascii'],
                   start=[entry['start_track'], entry['start_sector']], declared_blocks=entry['declared_blocks'],
                   actual_sectors=len(sectors), declared_blocks_match_chain=entry['declared_blocks']==len(sectors),
                   extracted=record(target), termination=termination, sectors=sectors, file_segments=segments,
                   first_32_bytes_hex=body[:32].hex(), nominal_prg_load_address=load,
                   nominal_prg_data_bytes=max(0,len(body)-2), nominal_prg_end_exclusive=load+len(body)-2 if load is not None else None,
                   prg_header_scope='Literal first two bytes interpreted under the directory PRG type; no actual load/depack/runtime behavior established.',
                   basic_header_lines=basic_lines(body))
        strings = []
        for encoding in ('ascii', 'screen-upper-subset', 'screen-lower-subset'):
            for item in literal_strings(body, encoding):
                item['location'] = locate_file_byte(segments, item['offset'])
                strings.append(item)
        row['literal_string_candidates'] = strings
        row['keyword_candidate_count'] = sum(item['keyword_candidate'] for item in strings)
        files.append(row)
        entry['file_id'] = file_id
    groups = defaultdict(list)
    starts = defaultdict(list)
    for row in files:
        groups[row['extracted']['sha256']].append(row['file_id'])
        starts[tuple(row['start'])].append(row['file_id'])
    overlaps = [dict(track=pair[0], sector=pair[1], file_ids=ids) for pair,ids in sorted(owners.items()) if len(ids)>1]
    bam = page(data,18,0)
    return dict(side=side, disk=record(path), directory_pages=pages, entries=entries, files=files,
                bam=dict(disk_name_hex=bam[0x90:0xa0].hex(), disk_name_ascii_subset=display(bam[0x90:0xa0].rstrip(b'\xa0')),
                         disk_id_hex=bam[0xa2:0xa4].hex(), dos_type_hex=bam[0xa5:0xa7].hex()),
                summary=dict(directory_entries=len(entries), prg_entries=len(files), decorative_del_entries=len(entries)-len(files),
                             valid_prg_chains=sum(row['termination']['kind']=='valid_eof' for row in files),
                             unique_prg_starts=len(starts), unique_prg_contents=len(groups),
                             sectors_across_all_chains=sum(row['actual_sectors'] for row in files), unique_prg_sectors=len(owners),
                             shared_prg_sectors=len(overlaps), declared_block_mismatches=sum(not row['declared_blocks_match_chain'] for row in files)),
                same_start_alias_groups=[dict(start=list(start), file_ids=ids) for start,ids in starts.items() if len(ids)>1],
                identical_content_groups=[dict(sha256=digest,file_ids=ids) for digest,ids in groups.items() if len(ids)>1],
                shared_prg_sector_ownership=overlaps,
                raw_disk_keyword_candidates=[item for encoding in ('ascii','screen-upper-subset','screen-lower-subset') for item in literal_strings(data,encoding) if item['keyword_candidate']])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BASE / 'disk-map')
    parser.add_argument('--boot-ram',type=Path,help='Existing independently unpacked 65536-byte RAM image; no CPU is run.')
    parser.add_argument('--native-ram',type=Path,help='Optional existing native RAM image, only for exact note/font byte corroboration.')
    args = parser.parse_args()
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    acquisition_path = BASE / 'acquisition.json'
    assert sha(acquisition_path.read_bytes()) == ACQUISITION_SHA
    acquisition = json.loads(acquisition_path.read_text())
    members = next(item for item in acquisition['archives'] if item['acquisition']['name']=='csdb-2ndreality.zip')['members']
    assert len(members) == 2
    disks = [inventory(side, member, output) for side,member in enumerate(members,1)]
    tsv_path = output / 'files.tsv'
    rows = ['side\tentry\tprefix\tstart\tdeclared_blocks\tactual_sectors\tfile_bytes\tnominal_load_hex\tsha256\tname_ascii_subset']
    for disk in disks:
        for item in disk['files']:
            rows.append('\t'.join(map(str,(disk['side'],item['directory_entry_index'],item['name_prefix_ascii'],
                                          '/'.join(map(str,item['start'])),item['declared_blocks'],item['actual_sectors'],
                                          item['extracted']['bytes'],f'{item["nominal_prg_load_address"]:04X}',
                                          item['extracted']['sha256'],item['name_ascii_subset']))))
    tsv_path.write_text('\n'.join(rows)+'\n')
    strings_path = output / 'keyword-candidates.txt'
    lines = ['Literal candidates only: binary coincidences and character-encoding ambiguity remain. No display/code/source identity is asserted.']
    for disk in disks:
        for item in disk['files']:
            for string in item['literal_string_candidates']:
                if string['keyword_candidate']:
                    lines.append(f'{item["file_id"]} file+${string["offset"]:04X} disk+${string["location"]["disk_offset"]:05X} {string["encoding"]}: {string["text"]}')
    strings_path.write_text('\n'.join(lines)+'\n')
    credits = credits_table(next(row for row in disks[1]['files'] if row['name_prefix_ascii']=='VA'))
    credit_path = output / 'credit-blocks.json'
    credit_path.write_text(json.dumps(credits,indent=2)+'\n')
    global_hashes, prefixes = defaultdict(list), defaultdict(list)
    for disk in disks:
        for row in disk['files']:
            global_hashes[row['extracted']['sha256']].append(row['file_id'])
            prefixes[row['name_prefix_ascii']].append(row['file_id'])
    proof = dict(description=__doc__, script=record(Path(__file__)), acquisition=record(acquisition_path),
                 disks=disks, file_table=record(tsv_path), keyword_candidates=record(strings_path),
                 literal_credit_table=record(credit_path),
                 global_prg_contents=len(global_hashes),
                 identical_contents_across_disks=[dict(sha256=digest,file_ids=ids) for digest,ids in global_hashes.items() if len({item[:5] for item in ids})>1],
                 reused_two_byte_prefixes=[dict(prefix=prefix,file_ids=ids) for prefix,ids in sorted(prefixes.items()) if len(ids)>1],
                 all_prg_chains_valid=all(row['termination']['kind']=='valid_eof' for disk in disks for row in disk['files']),
                 scope='DOS directory and exact sector chains, nominal PRG headers and literal static text only; no CPU, depack, renderer disassembly, emulator, drive or new web request.',
                 limitations=['DEL/decorative pointers are preserved but not followed as live file chains.',
                              'A literal PRG header is not proof that its full payload is loaded unchanged at that address.',
                              'Printable binary runs and alphabet-subset screen codes can be accidental; candidates are not automatically notes/source or part identities.',
                              'No conclusion that embedded text/source is absent from packed or custom-encoded material.'])
    if args.boot_ram:
        proof['embedded_note'] = inspect_embedded_note(args.boot_ram.resolve(), args.native_ram.resolve() if args.native_ram else None,output)
    proof_path = output / 'disk-inventory.json'
    proof_path.write_text(json.dumps(proof,indent=2)+'\n')
    print(json.dumps(dict(receipt=relative(proof_path),sha256=sha(proof_path.read_bytes()),
                          all_prg_chains_valid=proof['all_prg_chains_valid'],disks=[disk['summary'] for disk in disks]),indent=2))


if __name__ == '__main__':
    main()
