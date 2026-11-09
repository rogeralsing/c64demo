#!/usr/bin/env python3
"""Passive, bounded extraction of the three pinned Edge of Disgrace D64s."""
# BB1 bitstream conventions are adapted from jblang/demotools, commit
# 08492ee030dfaa362912a4ee616a17130267b36a, booze.py. No upstream module runs.
#
# Copyright (c) 2021 J.B. Langston
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/eod'
DISKS = {
    'EdgeOfDisgrace_0.d64': 'ee9570df68c3ddd1fda60ea3360dd5880c2ac95ed110bbe1bd60fdb91dec3f61',
    'EdgeOfDisgrace_1a.d64': '0624697997c57209929fc36ff7121ec7c61760a88576edbf0768d63e77d28956',
    'EdgeOfDisgrace_1b.d64': 'b348369ba5c7644019e4bf7f3cb8a5e81529b220e10b76dc5c0b7ad548310628',
}
PINS = {
    'build/research/eod/tool-source/booze.py': '558eb4c03e0e1fdf55cfebb6aa2c59aa3da735931245393e244a2b560377617a',
    'build/research/eod/tool-source/disk.py': '0e1bef76a0f0c52613a49404db68e3f9d95ef7189dd98683ba6deb62030235e3',
    'build/research/eod/tool-source/README.md': '107d51a1591e362aa3862db5d478bab7f04375d4dd84d788a162d6615eddddd6',
    'build/research/eod/tool-source/commit.json': 'b9facd6f8a9be644d66a2912abac20553472158231aa58ae5f1337f5926ed70f',
    'build/research/eod/tool-source/retrievals.json': 'a0c3e180a04fc8d473d89211ac1eb521db2e333fe15b3ec2d7fbaafc088bdfd8',
    'build/research/eod/release-extraction.json': '0ada48b084ea1e3a58c6f3955d4f3f0a51173fddeaa5134127f9c38603359f96',
    'build/research/stock-gouraud/analysis/accepted-02/source-proof.json': '9f7641d1eea14ce9b7580b534772f18cd43f93091e0e829996a1a3c1d11ee36e',
    'build/research/stock-gouraud/analysis/accepted-02/eod-nfo.txt': 'df83f97024816c13b53539e20d78b45276437f4cfac106204e931469d5807e0f',
}
SECTORS = [0] + [21]*17 + [19]*7 + [18]*6 + [17]*5
START = [sum(SECTORS[:t]) for t in range(36)]
# (whole-PRG signature, initial-bit byte, destination low byte, next stream byte)
FORMATS = {
    'b1normal': ('01080b0800009e3230363100000078a9348501a23b', 0x11c, 0x11d, 0x11f),
    'b1clean': ('01080b0800009e3230363100000078a9348501a23d', 0x112, 0x113, 0x115),
    'b1loader': ('01080b0800009e323036340000004c3c08a5ba20b1', 0x16a, 0x16b, 0x16d),
    # Original disk0 soundtrack replaces the port setup with JSR $73C7/NOP.
    # Its pinned bytes retain the same BB1 stream-header locations.
    'b1normal_soundtrack': ('01080b0800009e323036310000007820c773eaa23b', 0x11c, 0x11d, 0x11f),
}


class Invalid(ValueError):
    pass


def require(condition, reason):
    if not condition:
        raise Invalid(reason)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def identity(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def block(image, track, sector):
    require(1 <= track <= 35 and 0 <= sector < SECTORS[track], f'invalid sector {track}/{sector}')
    offset = (START[track]+sector)*256
    return image[offset:offset+256]


def chain(image, first, directory=False):
    current, seen, chunks, links = tuple(first), set(), [], []
    while current[0]:
        require(current not in seen, f'chain cycle at {current}')
        seen.add(current)
        value = block(image, *current)
        following = tuple(value[:2])
        if directory:
            chunks.append(value)
        elif following[0] == 0:
            require(1 <= following[1] <= 255, f'invalid terminal length {following[1]}')
            chunks.append(value[2:following[1]+1])
        else:
            chunks.append(value[2:])
        links.append(dict(track=current[0], sector=current[1], next_track=following[0], next_sector=following[1]))
        current = following
    return b''.join(chunks), links


def directory(image):
    require(block(image, 18, 0)[:2] == b'\x12\x01', 'unexpected directory head')
    raw, links = chain(image, (18, 1), directory=True)
    entries = []
    for position in range(0, len(raw), 32):
        item = raw[position:position+32]
        if item[2]:
            entries.append(dict(slot=position//32, type=item[2],
                start=list(item[3:5]), name_hex=item[5:21].hex(),
                name_ascii=''.join(chr(c) if 32 <= c < 127 else f'\\x{c:02x}' for c in item[5:21]),
                declared_sectors=int.from_bytes(item[30:32], 'little')))
    return entries, links


def index_pairs(image, disk):
    raw = block(image, 18, 6)
    if disk.endswith('_0.d64'):
        require(raw == b'\x00\xff'+bytes(254), 'disk0 unexpected index-sector contents')
        return [], 'absent: 00 FF then zeros; not a trackmo index'
    pairs, padding = [], False
    for offset in range(0, 256, 2):
        t, s = raw[offset:offset+2]
        if t == 0:
            require(s == 0, 'nonzero padding sector')
            padding = True
        else:
            require(not padding, 'nonzero pair after index padding')
            block(image, t, s)
            pairs.append([t, s])
    require(pairs and padding, 'missing index entries or terminator')
    require(len({tuple(p) for p in pairs}) == len(pairs), 'duplicate index starts')
    return pairs, 'validated T18/S6 pairs followed only by zero pairs'


def decode_bb1(data, kind):
    """Bounded integer bitstream decoder; overlapping backward copies are sequential."""
    if kind == 'b1none':
        first, dest_at, cursor = 2, 3, 5
    else:
        sig, first, dest_at, cursor = FORMATS[kind]
        require(data.startswith(bytes.fromhex(sig)), 'wrapper signature mismatch')
    require(len(data) > max(first, dest_at+1, cursor), 'truncated stream header')
    dest = int.from_bytes(data[dest_at:dest_at+2], 'little')
    bits, initial = data[first], cursor
    output, literals, matches, distances = bytearray(), 0, 0, []

    def byte():
        nonlocal cursor
        require(cursor < len(data), f'truncated stream at {cursor}')
        result = data[cursor]
        cursor += 1
        return result

    def bit():
        nonlocal bits
        bits = (bits << 1) & 511
        if bits & 255 == 0:
            bits = (byte() << 1) | (bits >> 8)
        return bits >> 8

    copy = False
    while True:
        copy = copy or bool(bit())
        length = 1
        while length < 128 and bit():
            length = (length << 1) | bit()
        if copy:
            if length == 255:
                break
            length += 1
            table_index = 4*int(length >= 3) + (bit() << 1) + bit()
            distance = 0
            while True:
                for _ in range((4, 2, 2, 2, 5, 2, 2, 3)[table_index]):
                    distance = (distance << 1) | bit()
                if table_index & 3 == 0:
                    break
                table_index -= 1
                distance += 1
            require(0 < distance <= len(output), f'non-backward or unwritten match distance {distance} at output {len(output)}')
            require(dest+len(output)+length <= 65536, 'output wraps 64K address space')
            for _ in range(length):
                output.append(output[-distance])
            matches += 1
            distances.append(distance)
            copy = False
        else:
            require(dest+len(output)+length <= 65536, 'output wraps 64K address space')
            for _ in range(length):
                output.append(byte())
            literals += 1
            copy = length < 255
    return dest.to_bytes(2, 'little')+output, dict(format=kind, destination=dest,
        initial_bits=data[first], first_byte_offset=initial, consumed_through=cursor,
        unused_trailing_bytes=len(data)-cursor, literal_runs=literals, match_runs=matches,
        largest_distance=max(distances, default=0), decoded_bytes=len(output),
        runtime_validation='not established by this passive decoder')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE/'file-analysis').resolve())
    require(not out.exists(), 'choose a fresh output directory')
    inputs = []
    for name, expected in PINS.items():
        path = ROOT/name
        require(sha(path.read_bytes()) == expected, f'input changed: {name}')
        inputs.append(identity(path))
    for name, expected in DISKS.items():
        path = BASE/'release'/name
        require(len(path.read_bytes()) == 174848 and sha(path.read_bytes()) == expected, f'disk changed: {name}')
        inputs.append(identity(path))
    out.mkdir(parents=True)
    outputs, disks, failures, rejected, note = [], [], [], [], None

    def save(name, raw):
        path = out/name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(raw)
        record = dict(name=name, bytes=len(raw), sha256=sha(raw))
        outputs.append(record)
        return record

    for disk in DISKS:
        image = (BASE/'release'/disk).read_bytes()
        entries, directory_links = directory(image)
        pairs, index_status = index_pairs(image, disk)
        diskname = disk[:-4]
        files, owners, extracted = [], {}, {}
        protected = {(18, 0), (18, 6)} | {(x['track'], x['sector']) for x in directory_links}
        candidates = [('dos', entry['slot'], entry['start'], entry) for entry in entries if entry['type'] & 15]
        candidates += [('trackmo', n, pair, None) for n, pair in enumerate(pairs)]
        for family, number, start, entry in candidates:
            label = f'{family}-{number:03d}'
            raw, links = chain(image, start)
            require(links, f'{disk}:{label} empty file chain')
            if entry is not None:
                require(len(links) == entry['declared_sectors'], f'{disk}:{label} directory sector count differs')
            for link in links:
                sector = link['track'], link['sector']
                require(sector not in protected, f'{disk}:{label} overlaps metadata {sector}')
                owners.setdefault(sector, []).append(label)
            raw_record = save(f'{diskname}/{label}.raw.prg', raw)
            extracted[label] = (raw, links)
            record = dict(family=family, number=number, start=start, directory_entry=entry,
                chain=links, raw=raw_record)
            if family == 'trackmo':
                if start == [18, 2]:
                    require(number == len(pairs)-1 and extracted['dos-001'] == (raw, links), 'unexpected bootstrap alias')
                    record['alias_of'] = 'dos-001'
                    kind = 'b1normal'
                    record['format_basis'] = 'exact DOS-bootstrap chain alias, including its original BB1 wrapper'
                else:
                    kind = 'b1none'
                    record['format_basis'] = 'headerless BB1 candidate from original side1a/1b trackmo index; subject to stream checks and later native binding'
            else:
                kind = next((k for k, v in FORMATS.items() if raw.startswith(bytes.fromhex(v[0]))), None)
            if kind:
                try:
                    decoded, detail = decode_bb1(raw, kind)
                    record['decode'] = detail
                    if len(decoded) == 2:
                        # A successful bitstream termination is not enough to
                        # accept a useful packed payload. Keep this original
                        # empty hypothesis and its raw input, explicitly rejected.
                        require(disk.endswith('_1b.d64') and family == 'trackmo' and number == 3
                            and start == [1, 16] and sha(raw) == '97d30b02c8a18b089118145407a00f248f3c333e08134bd5fc409c943a23178f',
                            'unexpected empty decoded candidate')
                        record['decode_status'] = 'rejected empty BB1 hypothesis: immediate terminator, not an accepted decoded payload'
                        record['rejected_candidate'] = save(f'{diskname}/{label}.rejected-empty.prg', decoded)
                        rejected.append(dict(disk=disk, label=label, start=start,
                            reason='FF initial state and FFFF destination immediately terminate; zero output data does not establish BB1 packing',
                            consumed_bytes=detail['consumed_through'], unused_bytes=detail['unused_trailing_bytes']))
                    else:
                        record['decoded'] = save(f'{diskname}/{label}.decoded.prg', decoded)
                    if disk.endswith('_0.d64') and entry is not None and entry['slot'] == 5:
                        note = decoded
                except Invalid as error:
                    record['decode_failure'] = str(error)
                    failures.append(dict(disk=disk, label=label, error=str(error)))
            else:
                record['decode_status'] = 'no recognized BB1 wrapper; raw file retained, not silently treated as decoded'
            files.append(record)
        overlaps = [dict(track=t, sector=s, owners=labels) for (t, s), labels in sorted(owners.items()) if len(labels) > 1]
        for shared in overlaps:
            require(shared['owners'] == ['dos-001', f'trackmo-{len(pairs)-1:03d}'] and shared['track'] == 18,
                f'{disk}: unexpected cross-file overlap {shared}')
            shared['classification'] = 'exact original emergency-bootstrap alias'
        disks.append(dict(name=disk, directory_entries=entries, directory_chain=directory_links,
            trackmo_index=dict(track=18, sector=6, status=index_status, pairs=pairs),
            files=files, cross_file_sector_overlaps=overlaps,
            allocated_unique_file_sectors=len(owners)))
    mirror = (ROOT/'build/research/stock-gouraud/analysis/accepted-02/eod-nfo.txt').read_bytes()
    note_check = dict(original_notefile_decoded=note is not None, mirror_exact_contiguous_match=False,
        limit='Whole-notefile byte equality is not established; the bounded shader section is compared under an explicit character/whitespace translation below.')
    if note is not None:
        at = note.find(mirror)
        note_check.update(decoded_PRG_bytes=len(note), decoded_PRG_sha256=sha(note),
            mirror_exact_contiguous_match=at >= 0, mirror_PRG_offset=at if at >= 0 else None,
            ascii_phrase_offsets={p: note.lower().find(p.encode()) for p in ('ditheredvector', 'tracing-line', 'three out of four', 'hcl on the keys')})
        # Conventional lower-case text charset values, stated explicitly rather
        # than assuming the note PRG contains an ASCII copy of the HTML mirror.
        encode = lambda s: bytes(ord(c) & 63 for c in s.upper())
        section_start = note.find(encode('ditheredvector:'))
        section_end = note.find(encode('ab-zoom:'), section_start)
        require(section_start >= 2 and section_end > section_start, 'missing original shader-section markers')
        original_section = note[section_start:section_end]
        require(all(1 <= b <= 26 or 32 <= b < 64 for b in original_section), 'unsupported shader-section character')
        text = ''.join(chr(b+96) if 1 <= b <= 26 else chr(b) for b in original_section)
        mirror_text = mirror.decode('utf-8')
        mirror_start = mirror_text.index('ditheredvector:')
        mirror_end = mirror_text.index('ab-zoom:', mirror_start)
        mirror_section = mirror_text[mirror_start:mirror_end]
        normalize = lambda s: ''.join(c for c in s if c not in ' \t\r\n').encode('ascii')
        translated, mirror_normalized = normalize(text), normalize(mirror_section)
        require(translated == mirror_normalized, 'original shader section differs after declared translation')
        note_check['shader_section'] = dict(
            original_address_start=0x800+section_start-2,
            original_address_end_exclusive=0x800+section_end-2,
            character_translation='original 01..1A become ASCII a..z; original20..3F unchanged',
            whitespace_normalization='remove only ASCII space, tab, CR and LF; preserve punctuation, order and case',
            original_raw=save('ditheredvector-original.bin', original_section),
            original_translated=save('ditheredvector-translated.txt', (text+'\n').encode()),
            identical_normalized=save('ditheredvector-normalized.txt', translated),
            mirror_normalized_bytes=len(mirror_normalized), mirror_normalized_sha256=sha(mirror_normalized),
            full_section_normalized_equal=True,
            native_notefile_execution_claimed=False)
    save('extract.checked.py', Path(__file__).read_bytes())
    proof = dict(pass_=not failures, scope='Structural extraction and bounded BB1 hypotheses; the known empty headerless hypothesis is retained but explicitly rejected as a decoded payload; no native or shader acceptance',
        producer=identity(Path(__file__)), inputs=inputs,
        upstream=dict(commit='08492ee030dfaa362912a4ee616a17130267b36a',
            URL='https://github.com/jblang/demotools', executed=False, MIT_notice_in_producer=True),
        disks=disks, decode_failures=failures, rejected_hypotheses=rejected, notefile_mirror=note_check,
        limitations=['Headerless trackmo BB1 decoding is a format hypothesis until original runtime comparison.',
            'No downloaded host entrypoint/module, C64 CPU interpreter, emulator or build is executed.',
            'Decoder rejects out-of-bounds sectors, chain loops, truncated streams, unwritten references and 64K output wrapping.',
            'No original Gouraud shader location, scanout, timing or FPS claim follows from extraction.'], outputs=outputs)
    raw = (json.dumps(proof, indent=2)+'\n').encode()
    (out/'file-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=proof['pass_'], proof_bytes=len(raw), proof_sha256=sha(raw),
        disks=[dict(name=d['name'], files=len(d['files']), trackmo=len(d['trackmo_index']['pairs']),
                    overlaps=len(d['cross_file_sector_overlaps'])) for d in disks],
        failures=failures, rejected_hypotheses=rejected, notefile_mirror=note_check), indent=2))
    if failures:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
