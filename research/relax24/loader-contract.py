#!/usr/bin/env python3
"""Bind original Relax24 drive/C64 loader bytes at a byte-level boundary.

This is a functional protocol model with source-byte gates, not CPU, drive-ROM,
IEC pin, timing, initialized-menu or native execution. Sector service success
and completed byte handshakes are explicit assumptions, never synthesized CPU
or hardware responses. Earlier decoder/consumer receipts stay read-only.
"""
from collections import Counter
import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/relax24'
OUT = BASE / 'loader-contract-01'
PINS = {
    'archive-proof.json': '0c68892c3a73cdeda0854eaa28db205672a9b02ed3f04ce185dbda72ad656fac',
    'decoder-analysis/inner-proof.json': 'd86df447082e7ee3d7d55bf8bfaabdc9abe0ff09784746a28656ba78f43eb9cd',
    'article-analysis/consumer-proof.json': 'e41c974f734065a2fec5d8162f464bb8a6ce0c28154d85f901e4f41129b4ce22',
    'resource-recovery-01/resource-proof.json': 'f56b8b0b650d104433c46cea100dd3d08a82e43175a76b43cd7eb10b87a8ca7b',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=str(path.resolve().relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def checked(item):
    data = (ROOT / item['path']).read_bytes()
    assert len(data) == item['bytes'] and sha(data) == item['sha256'], item
    return data


def word(data):
    assert len(data) == 2
    return data[0] + 256 * data[1]


def sector_offset(track, sector):
    """35-track D64 geometry; original archive extraction is the other owner."""
    assert 1 <= track <= 35, ('Track outside pinned image', track)
    counts = [21 if t <= 17 else 19 if t <= 24 else 18 if t <= 30 else 17
              for t in range(1, 36)]
    assert 0 <= sector < counts[track - 1], ('Invalid sector', track, sector)
    return 256 * (sum(counts[:track - 1]) + sector)


def read_sector(disk, track, sector):
    offset = sector_offset(track, sector)
    data = disk[offset:offset + 256]
    assert len(data) == 256
    return data


def directory_lookup(disk, request):
    """$0503..$056B after completed $05C3 receive / $05FB sector calls.

    The first byte is returned in A by $05C3 then discarded by $0506 LDA $0E.
    $0512 always resets track to $12, ignoring the directory link track byte;
    the next-sector byte's sign bit terminates lookup at $0543.
    """
    assert len(request) == 3
    name = request[1:]
    directory_sector, visited, attempts = 1, set(), []
    for _ in range(256):
        assert directory_sector not in visited, 'Directory cycle'
        visited.add(directory_sector)
        page = read_sector(disk, 18, directory_sector)
        y = 2
        for _ in range(8):
            entry = dict(track=18, sector=directory_sector, type_offset=y,
                         type_byte=page[y], name_prefix=list(page[y + 3:y + 5]),
                         accepted_type=(page[y] & 0x83) == 0x82)
            attempts.append(entry)
            if entry['accepted_type'] and page[y + 3:y + 5] == name:
                return dict(start=[page[y + 1], page[y + 2]], selected=entry,
                            attempts=attempts, directory_pages=sorted(visited))
            # TYA / CLC / ADC #$20 / TAY; carry leaves the page after slot7.
            y = (y + 32) & 255
        assert y == 2
        if page[1] & 128:
            return dict(start=None, selected=None, attempts=attempts,
                        directory_pages=sorted(visited))
        directory_sector = page[1]
    raise AssertionError('Directory budget')


def emit_byte(wire, value):
    # $058A..$0596 doubles $AC, including any occurrences in the load header.
    if value == 0xac:
        wire.append(value)
    wire.append(value)


def drive_stream(disk, request):
    """Transcribe the actual directory/file/escape path at a byte interface.

    A successful $05FB call establishes disk sector data at drive $0700.
    Neither that asynchronous resident job service nor $062F serial pins run.
    """
    lookup = directory_lookup(disk, request)
    wire, raw, ledger = bytearray(), bytearray(), []
    if lookup['start'] is None:
        # $0545..$0560: not-found and sector-error paths share this response.
        return bytes.fromhex('fe fe ac f7'), b'', lookup, ledger
    track, sector = lookup['start']
    visited = set()
    for _ in range(683):
        assert (track, sector) not in visited, 'File sector cycle'
        visited.add((track, sector))
        page = read_sector(disk, track, sector)
        next_track, next_sector = page[:2]
        stop = 0 if next_track else (next_sector + 1) & 255
        first_raw, first_wire, y = len(raw), len(wire), 2
        for _ in range(256):
            raw.append(page[y])
            emit_byte(wire, page[y])
            y = (y + 1) & 255
            if y == stop:
                break
        else:
            raise AssertionError('Sector loop did not complete')
        count = len(raw) - first_raw
        # All actual files have a normal, nonempty last sector. Keep the
        # original count edge explicit instead of silently using DOS slicing.
        assert count == (254 if next_track else next_sector - 1), (
            'Unobserved final-sector count edge', track, sector, next_sector, count)
        ledger.append(dict(track=track, sector=sector,
                           disk_offset=sector_offset(track, sector),
                           sector_sha256=sha(page), next=[next_track, next_sector],
                           raw_first=first_raw, raw_bytes=count,
                           wire_first=first_wire, wire_data_bytes=len(wire) - first_wire))
        wire.extend((0xac, 0xc3 if next_track else 0xff))
        if not next_track:
            return bytes(wire), bytes(raw), lookup, ledger
        track, sector = next_track, next_sector
    raise AssertionError('File sector budget')


def c64_receive(wire):
    """$AC24..$AC62 after completed $ACDC/$AC83 handshakes.

    The first two wire bytes are an unescaped little-endian address. Unknown
    $AC controls (including drive's $C3) perform the inter-sector handshake;
    $FF completes with carry clear, $F7 with carry set. A failure's $FE $FE
    bytes are ordinary data once the address header has been consumed. Stores
    require no existing destination value. No source CPU is stepped or skipped.
    """
    assert len(wire) >= 4
    cursor = word(wire[:2])
    memory, known = bytearray(65536), bytearray(65536)
    values, addresses, controls = bytearray(), [], []
    position = 2
    for _ in range(131072):
        assert position < len(wire), 'Truncated stream'
        value = wire[position]
        position += 1
        if value == 0xac:
            assert position < len(wire), 'Truncated control'
            value = wire[position]
            position += 1
            if value != 0xac:
                controls.append(dict(wire_offset=position - 2, value=value))
                if value in (0xff, 0xf7):
                    return dict(cursor=cursor, carry=int(value == 0xf7), consumed=position,
                                controls=controls, values=bytes(values), addresses=addresses,
                                memory=bytes(memory), known=bytes(known))
                continue
        assert not known[cursor], ('Repeated or wrapped output', cursor)
        memory[cursor], known[cursor] = value, 1
        values.append(value)
        addresses.append(cursor)
        cursor = (cursor + 1) & 65535
        # $AC57 BNE is on the high-byte INC when the low byte wraps. A full
        # $FFFF->$0000 wrap falls through $AC59 CLC and returns before
        # consuming the next stream control.
        if cursor == 0:
            return dict(cursor=cursor, carry=0, consumed=position, controls=controls,
                        values=bytes(values), addresses=addresses,
                        memory=bytes(memory), known=bytes(known), pointer_wrap=True)
    raise AssertionError('Receive budget')


def byte_contract_checks():
    """Exhaust byte values / byte assembly, not hypothetical IEC pin behavior."""
    for value in range(256):
        # The source LSRs send low bit first. Eight RORs into an 8-bit register
        # discard its unavailable previous value, so no initial $14/$FA needed.
        low_bits = [(value >> bit) & 1 for bit in range(8)]
        for previous in (0, 0xff):
            result = previous
            for carry in low_bits:
                result = (result >> 1) | (carry << 7)
            assert result == value
        encoded = bytearray(b'\x00\x20')
        emit_byte(encoded, value)
        encoded.extend((0xac, 0xff))
        got = c64_receive(encoded)
        assert got['values'] == bytes([value]) and got['cursor'] == 0x2001
        assert got['carry'] == 0 and got['consumed'] == len(encoded)
    # The full alphabet catches reserved $C3/$F7/$FF data as well as $AC.
    encoded = bytearray(b'\x00\x20')
    for value in range(256):
        emit_byte(encoded, value)
    encoded.extend((0xac, 0xc3, 0xac, 0xff))
    got = c64_receive(encoded)
    assert got['values'] == bytes(range(256)) and got['cursor'] == 0x2100
    assert [item['value'] for item in got['controls']] == [0xc3, 0xff]
    # Bounded synthetic byte-interface cases, not captured drive/CPU states.
    # INC $AF=$00 sets Z, so $AC57 falls through $AC59 CLC. The EOF control
    # remains unread; this early return is not equivalent to consuming EOF.
    wrapped = c64_receive(bytes.fromhex('ff ff 55 ac ff'))
    assert wrapped['pointer_wrap'] and wrapped['carry'] == 0
    assert wrapped['cursor'] == 0 and wrapped['consumed'] == 3
    assert wrapped['values'] == b'\x55' and wrapped['addresses'] == [0xffff]
    assert not wrapped['controls'] and sum(wrapped['known']) == 1
    # The same drive failure sender can run after a previous sector supplied
    # the load header. Its two $FE bytes then become data before $AC $F7.
    late_failure = c64_receive(bytes.fromhex('00 20 55 fe fe ac f7'))
    assert late_failure['values'] == bytes.fromhex('55 fe fe')
    assert late_failure['addresses'] == [0x2000, 0x2001, 0x2002]
    assert late_failure['carry'] == 1 and late_failure['cursor'] == 0x2003
    assert late_failure['consumed'] == 7
    return dict(byte_values=256, assembly_initial_values=[0, 255],
                all_values_and_controls_round_trip=True,
                bounded_synthetic_edges=dict(
                    pointer_wrap=dict(wire_hex='ff ff 55 ac ff', output_addresses=[0xffff],
                                      cursor=0, carry=0, consumed=3, unread_bytes=2),
                    postheader_failure=dict(wire_hex='00 20 55 fe fe ac f7',
                                            output_hex='55 fe fe', cursor=0x2003,
                                            carry=1, consumed=7),
                    scope='Byte-interface source contracts only; no CPU or hardware state supplied.'),
                scope='Byte ordering/escaping only; physical IEC mapping and handshakes excluded.')


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    receipts = {}
    for name, expected in PINS.items():
        path = BASE / name
        assert sha(path.read_bytes()) == expected, ('Frozen receipt changed', name)
        receipts[name] = json.loads(path.read_text())
    correction_archive_path = OUT / 'checkpoint-archive/wrap-carry-correction-before.json'
    correction_archive = json.loads(correction_archive_path.read_text())
    assert [item['sha256'] for item in correction_archive['items']] == [
        '47c4d0762ac73b0190624287ae86b7ea55518b62857a133632453e6466df46e0',
        '0c5daaff2fb3f61c59cd5cca20d2167378b20dac6d1544e65cf6252d3e40425c']
    for item in correction_archive['items']:
        checked(dict(path=item['archived'], bytes=item['bytes'], sha256=item['sha256']))
    archive = receipts['archive-proof.json']
    inner_proof = receipts['decoder-analysis/inner-proof.json']
    resource_proof = receipts['resource-recovery-01/resource-proof.json']
    assert archive['pass'] and inner_proof['pass'] and resource_proof['pass']
    inner_item = next(x for x in inner_proof['artifacts'] if x['path'].endswith('/inner-decoded.ram'))
    inner = checked(inner_item)
    resource_item = next(x for x in resource_proof['artifacts'] if x['path'].endswith('/resource.ram'))
    resource = checked(resource_item)
    disk_item = next(x for x in archive['members'] if x['path'].endswith('/REL24_S2.D64'))
    disk = checked(disk_item)
    drive = bytearray(65536)
    drive[0x500:0x6f0] = inner[0x25a8:0x2798]
    assert sha(drive[0x500:0x6f0]) == 'd0225bd8f23d19858bddf5ff2dd1cbfa7a95c12bd9ec556522c9e49606d29748'
    sites = []

    def site(image, first, expected, purpose):
        expected = bytes.fromhex(expected)
        data = {'inner': inner, 'drive': drive, 'resource': resource}[image]
        assert data[first:first + len(expected)] == expected, (image, hex(first), purpose)
        sites.append(dict(image=image, first=first, end_exclusive=first + len(expected),
                          hex=expected.hex(' '), purpose=purpose))

    # Gate model decisions on the actual original instructions, rather than a
    # guessed signature or metadata-derived filename/format interpretation.
    site('inner', 0x2515, 'a2 a8 a0 25 86 02 84 03', 'Upload source pointer')
    site('inner', 0x251d, 'a9 4d 20 a8 ff a9 2d 20 a8 ff a9 57 20 a8 ff', 'M-W prefix')
    site('inner', 0x252c, 'a5 02 38 e9 a8 08 18 20 a8 ff 28 a5 03 e9 20 18 20 a8 ff a9 10 20 a8 ff', 'Target equals source minus20A8 and count16')
    site('inner', 0x2544, 'a0 00 b1 02 20 a8 ff c8 c0 10 d0 f6', 'Transmit16 original bytes')
    site('inner', 0x2572, 'a5 02 18 69 10 85 02 90 02 e6 03 c9 98 a5 03 e9 27 90 98', 'Upload loop end2798')
    site('inner', 0x25a0, '4d 2d 45 00 05 0d', 'Execute0500 command')
    site('drive', 0x500, '20 7f 06 20 c3 05 a5 0e 8d a5 06 a5 0f 8d a6 06', 'Handshake, receive and discard command A')
    site('drive', 0x510, 'a0 01 a2 12 86 0e 84 0f 20 fb 05 a0 02', 'Directory18/1 with type offset2')
    site('drive', 0x51d, 'b9 00 07 29 83 c9 82 d0 13 b9 03 07 cd a5 06 d0 0b b9 04 07 cd a6 06 d0 03 4c 61 05', 'Closed PRG mask and two-byte name match')
    site('drive', 0x539, '98 18 69 20 a8 90 dd ac 01 07 10 cd', '32-byte slots then sign-terminated next directory sector')
    site('drive', 0x545, 'a9 00 8d 00 18 a2 fe 20 2f 06 a2 fe 20 2f 06 a2 ac 20 2f 06 a2 f7 20 2f 06 4c 22 eb', 'Error response and external ROM exit')
    site('drive', 0x561, 'b9 01 07 85 0e b9 02 07 85 0f 20 fb 05 a0 00 ad 00 07 85 0e d0 04 ac 01 07 c8 8c a5 06 ad 01 07 85 0f a0 02', 'File start, sector service, link and last-sector stop')
    site('drive', 0x585, 'a9 00 8d 00 18 be 00 07 e0 ac d0 05 20 2f 06 a2 ac 20 2f 06 c8 cc a5 06 d0 eb', 'EscapeAC and actual sector byte loop')
    site('drive', 0x59f, 'ad 00 07 f0 12 a2 ac 20 2f 06 a2 c3 20 2f 06 a9 08 8d 00 18 4c 6b 05 a2 ac 20 2f 06 a2 ff 20 2f 06 4c 03 05', 'Sector separator and EOF controls')
    site('drive', 0x5de, '20 5d 06 48 20 5d 06 85 0e 20 5d 06 85 0f', 'Receive command then name bytes')
    site('drive', 0x5f9, '68 60', 'Return first byte in A')
    site('drive', 0x5fb, 'a0 05 84 8b 58 a9 80 85 04 a5 04 30 fc c9 01 f0 21', 'Resident asynchronous sector service request/wait')
    site('drive', 0x60c, 'c6 8b a4 8b 30 16 c0 02 d0 04 a9 c0 85 04 a5 16 85 12 a5 17 85 13 a5 04 30 fc 10 d7', 'Retry/recovery path requires resident drive state')
    site('drive', 0x628, '68 68 4c 45 05 78 60', 'Exhausted retry and successful service return')
    site('drive', 0x62f, '86 14 a9 04 20 3c 06 20 3c 06 20 3c 06', 'Three calls and fallthrough send four bit pairs')
    site('drive', 0x63c, '46 14 a2 02 90 02 a2 00 2c 00 18 d0 fb 8e 00 18 46 14 a2 02 90 02 a2 00 2c 00 18 f0 fb 8e 00 18 60', 'LSB-first transmit and hardware waits')
    site('drive', 0x65d, 'a0 04 a9 04 2c 00 18 f0 fb ad 00 18 4a 66 14 a9 04 2c 00 18 d0 fb ad 00 18 4a 66 14 88 d0 e3 a5 14 60', 'Four receive pairs shift into14')
    site('resource', 0xac00, 'ad 00 dd 29 0f 8d cf ac 49 10 8d c0 ac 49 30 8d 6b ac 49 b0 8d 96 ac 49 50 8d a5 ac 8d e9 ac', 'Preserve CIA2 low nibble while patching serial immediates')
    site('resource', 0xac1f, 'a9 02 20 63 ac 20 dc ac 20 83 ac 85 ae 20 83 ac 85 af', 'Command02 followed by raw load address')
    site('resource', 0xac31, '20 83 ac c9 ac d0 15 20 83 ac c9 ac f0 0e c9 ff f0 16 c9 f7 f0 13 20 dc ac 4c 31 ac', 'Unescape, EOF, error and separator dispatch')
    site('resource', 0xac4d, 'a0 00 91 ae e6 ae d0 02 e6 af d0 d8 18 ae f8 ac ac f9 ac a9 00 60', 'Ascending output, carry and restored name return')
    site('resource', 0xac63, '48 8e f8 ac 8c f9 ac a9 24 8d 00 dd 20 dc ac 68 20 b0 ac ad f8 ac 20 b0 ac ad f9 ac 20 b0 ac 60', 'Save X/Y and send three bytes')
    site('resource', 0xac83, '20 95 ac 20 95 ac 20 95 ac 20 95 ac 20 94 ac a5 fa 60', 'Four receive bit-pairs; fifth call is RTS')
    site('resource', 0xac95, 'a2 94 ad 00 dd 8e 00 dd 0a 66 fa 48 68 48 68 a2 c4 ad 00 dd 8e 00 dd 0a 66 fa 60', 'Sample bit7 and RORFA twice')
    site('resource', 0xacb0, '85 fa 20 bf ac 20 bf ac 20 bf ac 20 bf ac 60', 'Send four bit-pairs')
    site('resource', 0xacbf, 'a9 14 46 fa 90 02 09 20 8d 00 dd ea ea ea ea a9 04 46 fa 90 02 09 20 8d 00 dd ea ea 60', 'LSRFA and output bit5 twice')
    site('resource', 0xacdc, 'a2 32 ca d0 fd ad 00 dd 29 40 f0 f9 a9 c4 8d 00 dd a9 fe 8d fa ac a2 05 ca d0 fd 60', 'CIA2 bit6 polling and delay remain hardware boundary')
    site('resource', 0xc156, 'a2 30 a0 30 20 00 ac', 'First foreground request00')
    site('resource', 0xc15d, 'a5 ae 38 e9 02 85 ae a5 af e9 00 85 af a0 00 b1 ae 8d b2 c3 c8 b1 ae 8d b3 c3 a2 ff a0 ff 20 00 ac', 'Read final little-endian word into later JMP, then requestFFFF')
    site('resource', 0xc380, '78 a2 00 a0 20 86 04 84 05 a2 01 a0 08 86 02 84 03 a0 00 b1 04 91 02 c8 d0 f9 e6 03 e6 05 a5 05 c9 ac d0 ed', 'Later source2000..ABFF copy to0801..9400')
    site('resource', 0xc3a4, 'a9 37 85 01 20 a3 fd 20 15 fd 20 5b ff 4c ea ea', 'Hardware/ROM calls precede patched JMP')

    uploads = []
    source = 0x25a8
    while source < 0x2798:
        destination = (source - 0x20a8) & 65535
        uploads.append(dict(source=source, destination=destination,
                            bytes=16, sha256=sha(inner[source:source + 16])))
        source += 16
    assert len(uploads) == 31 and source == 0x2798
    assert [x['destination'] for x in uploads] == list(range(0x500, 0x6f0, 16))
    # These output files are byte-level expectations, not captured hardware.
    (OUT / 'drive0500-06ef.bin').write_bytes(drive[0x500:0x6f0])
    (OUT / 'c64-ac00-acf7.bin').write_bytes(resource[0xac00:0xacf8])
    (OUT / 'source-sites.json').write_text(json.dumps(sites, indent=2) + '\n')

    # Compare every actual disk-file stream against the older, independently
    # implemented directory/chain extractor; do not load article headers as PRGs.
    file_checks = []
    for entry in archive['side2_files']:
        name = bytes.fromhex(entry['directory_entry']['name_hex'])[:2]
        wire, raw, lookup, ledger = drive_stream(disk, b'\x02' + name)
        expected = checked(entry['extracted'])
        assert raw == expected, ('Drive stream differs from archive extraction', name)
        assert len(ledger) == entry['directory_entry']['declared_blocks']
        assert [x['sector_sha256'] for x in ledger] == [x['sha256'] for x in entry['sectors']]
        assert lookup['start'] == [entry['directory_entry']['start_track'], entry['directory_entry']['start_sector']]
        file_checks.append(dict(name_hex=name.hex(), file_bytes=len(raw), sectors=len(ledger),
                                file_sha256=sha(raw), wire_bytes=len(wire)))
    assert len(file_checks) == 21

    wire, raw, lookup, ledger = drive_stream(disk, bytes.fromhex('02 30 30'))
    assert len(raw) == 13822 and len(ledger) == 55
    assert sha(raw) == '889a7648417cf6734832dd4cf8f5883415d8dc31457b33803e7272630a2bbc6a'
    assert lookup['selected']['sector'] == 1 and lookup['selected']['type_offset'] == 34
    assert lookup['selected']['type_byte'] == 0xc2 and lookup['start'] == [17, 0]
    assert raw[:2] == bytes.fromhex('00 20') and raw[-2:] == bytes.fromhex('0c 08')
    assert len(wire) == 13980 and raw.count(0xac) == 48
    received = c64_receive(wire)
    assert received['consumed'] == len(wire) and received['carry'] == 0
    assert received['values'] == raw[2:]
    assert received['addresses'] == list(range(0x2000, 0x55fc))
    assert received['cursor'] == 0x55fc and sum(received['known']) == 13820
    assert Counter(x['value'] for x in received['controls']) == {0xc3: 54, 0xff: 1}
    assert received['memory'][0x2000:0x55fc] == raw[2:]
    # The model never writes over its C64 loader or the later consumer code.
    assert not any(received['known'][0xac00:0xd000])
    final_word_address = (received['cursor'] - 2) & 65535
    assert final_word_address == 0x55fa
    jump = word(received['memory'][final_word_address:final_word_address + 2])
    assert jump == 0x080c
    # $C380's later copy maps the received body back to a BASIC-layout image.
    # Only transfer-established source bytes are copied; the remaining copy
    # tail is deliberately unknown in this isolated transfer model.
    relocated = bytearray(65536)
    relocated_known = bytearray(65536)
    for source in range(0x2000, 0xac00):
        destination = source - 0x2000 + 0x0801
        if received['known'][source]:
            relocated[destination] = received['memory'][source]
            relocated_known[destination] = 1
    assert sum(relocated_known) == 13820
    assert all(relocated_known[jump:jump + 3])
    assert relocated[jump:jump + 3] == bytes.fromhex('a0 00 78')
    assert relocated[0x801:0x801 + 13820] == raw[2:]
    assert word(relocated[0x801:0x803]) == 0x080c

    missing_wire, missing_raw, missing_lookup, missing_ledger = drive_stream(disk, bytes.fromhex('02 ff ff'))
    assert missing_wire == bytes.fromhex('fe fe ac f7') and not missing_raw and not missing_ledger
    assert missing_lookup['directory_pages'] == [1, 4, 7] and len(missing_lookup['attempts']) == 24
    missing = c64_receive(missing_wire)
    assert missing['carry'] == 1 and missing['cursor'] == 0xfefe and not missing['values']

    # $05C3's command byte cannot affect the subsequent source lookup: all256
    # requests reach the same first matching entry. No invented command table.
    for command in range(256):
        assert directory_lookup(disk, bytes((command, 0x30, 0x30))) == lookup
    checks = byte_contract_checks()
    artifacts = []
    for name, data in [('request00-wire.bin', wire), ('request00-file.prg', raw),
                       ('request00-loaded.ram', received['memory']),
                       ('request00-loaded-known-mask.bin', received['known']),
                       ('request00-relocated-known.ram', relocated),
                       ('request00-relocated-known-mask.bin', relocated_known)]:
        path = OUT / name
        path.write_bytes(data)
        artifacts.append(record(path))
    for name, data in [('request00-sector-ledger.json', ledger), ('request00-lookup.json', lookup),
                       ('request00-controls.json', received['controls']),
                       ('side2-drive-stream-checks.json', file_checks),
                       ('requestffff-lookup.json', missing_lookup)]:
        path = OUT / name
        path.write_text(json.dumps(data, indent=2) + '\n')
        artifacts.append(record(path))
    artifacts.extend(record(OUT / name) for name in ['drive0500-06ef.bin', 'c64-ac00-acf7.bin', 'source-sites.json'])
    report = dict(
        pass_=True, script=record(Path(__file__)),
        frozen_receipts=[record(BASE / name) for name in PINS],
        correction_archive=record(correction_archive_path),
        inputs=[inner_item, resource_item, disk_item],
        source_sites=len(sites),
        upload=dict(source=[0x25a8, 0x2798], destination=[0x500, 0x6f0], bytes=496,
                    image_sha256=sha(drive[0x500:0x6f0]), chunks=uploads,
                    execution_command_hex='4d 2d 45 00 05 0d'),
        request=dict(bytes=[2, 48, 48], command_byte_discarded=True,
                     match_prefix_hex='3030', directory_track=18, directory_sector=1,
                     slot=1, masked_type=0x82, actual_type=0xc2, file_start=[17, 0],
                     all_command_values_same_lookup=True),
        byte_protocol=dict(escape=0xac, escaped_literal=[0xac, 0xac],
                           sector_separator=[0xac, 0xc3], normal_eof=[0xac, 0xff],
                           failure_response=[0xfe, 0xfe, 0xac, 0xf7],
                           load_header_unescaped=True, ordering='LSB first', checks=checks),
        file00=dict(bytes=len(raw), sha256=sha(raw), sectors=len(ledger),
                    escaped_ac_bytes=48, sector_separators=54, wire_bytes=len(wire),
                    wire_sha256=sha(wire)),
        receive=dict(load_address=0x2000, bytes=13820, output=[0x2000, 0x55fc],
                     returned_cursor=received['cursor'], carry=0,
                     output_sha256=sha(received['values']),
                     final_word_address=final_word_address, final_word_hex='0c08',
                     patched_jmp_target=jump, restored_xy=[0x30, 0x30],
                     known_only_through_stream=True, no_loader_or_consumer_overlap=True),
        later_copy=dict(source=[0x2000, 0xac00], destination=[0x0801, 0x9401],
                        transfer_known_destination=[0x0801, 0x3dfd],
                        transfer_unknown_source=[0x55fc, 0xac00],
                        bytes_at_patched_target_hex='a0 00 78',
                        scope='Address mapping and known bytes only; C380 reachability and ROM calls excluded.'),
        second_request=dict(bytes=[2, 255, 255], matched=False,
                            directory_pages=[1, 4, 7], slots_checked=24,
                            response_hex=missing_wire.hex(' '), received_cursor=0xfefe,
                            received_stores=0, carry=1, drive_external_jump=0xeb22),
        all_original_files=dict(files=21, exact_against_independent_extraction=True,
                                scope='Drive byte-stream/file identity only; article headers are not loaded as C64 addresses.'),
        native_capture_needed=dict(
            drive_image='After actual M-W upload, drive RAM0500..06EF must match pinned image.',
            first_return='At real C15D after C15A returns: AE/AF, registers/flags and C64 RAM2000..55FB.',
            expected_first_return=dict(cursor=0x55fc, output_sha256=sha(raw[2:]), carry=0),
            sector_service='Actual resident drive state/job04 and buffer0700 must establish requested track/sector data, with successful service at062D.',
            physical_protocol='Capture real drive/C64 byte or IEC/port activity; no pin mapping, device timing or interrupt state is assumed proved.'),
        exclusions=[
            'No VICE/native process, original CPU execution, drive-ROM call, interrupt delivery or serial hardware runs.',
            'Successful05FB sector calls and completed062F/065D/AC83/ACB0 handshakes are functional call contracts only.',
            'No value is supplied for the frozen original-resource CPU stop at0223; all earlier proof bytes remain unchanged.',
            'Initial resident drive firmware/zero page, VIA/CIA DDRs, port values, timers, ROM entryEB22 and KERNAL behavior remain unproved.',
            'The C64 first-two-byte header path does not unescape; hypotheticalAC header bytes are outside the checked00 input.',
            'Zero-byte final DOS sectors are outside the checked inputs. Full cursor wrap and postheader failure are bounded byte-interface cases, not native observations or ordinary EOF.',
            'The transfer-established tail ends55FB; no fullC380 copy, initialized menu, original article decoding or coding-review identity is claimed.',
        ], artifacts=artifacts,
        scope='Original-byte-gated functional loader contract; neither captured transfer nor whole-machine execution.')
    report['pass'] = report.pop('pass_')
    path = OUT / 'loader-proof.json'
    path.write_text(json.dumps(report, indent=2) + '\n')
    # Ensure this checker never reissues or mutates the frozen prior proofs.
    assert all(sha((BASE / name).read_bytes()) == expected for name, expected in PINS.items())
    print(json.dumps(dict(pass_=True, receipt=record(path), drive_image_sha256=report['upload']['image_sha256'],
                          wire_bytes=len(wire), output_bytes=len(received['values']),
                          returned_cursor=f'{received["cursor"]:04X}', patched_jmp=f'{jump:04X}',
                          scope=report['scope']), indent=2))


if __name__ == '__main__':
    main()
