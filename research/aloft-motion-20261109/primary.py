#!/usr/bin/env python3
"""Passive creator follow-up and typed Perpetual Fragility Exomizer parsing.

This is our Python translation of the guarded byte/bit/token format, not a CPU
interpreter, assembler, or execution of downloaded host code. Format attribution:
Magnus Lind, Exomizer. Primary C and assembly sources retain their full notices.
No native RAM or expected unpacked payload is an input.
"""
import argparse
import hashlib
import io
import json
import tarfile
import zipfile
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin

ROOT = Path(__file__).resolve().parents[2]
BASE = 'build/research/aloft-motion-20261109/primary-analysis/'
PRG = 'build/research/aloft-pixels-20261109/reading-analysis/acquisition-01/perpetual-prg.prg'
PRG_SHA = '9770854332c3a60bb25eaa580d91e47f5d98ff6d47c7b6fdfec1a60b82e985df'
MANIFESTS = {
    'acquisition-01/http-retention.json': 'be3eb0bd60e70d8e78aa218334feb0ba94c5254e78cf6e40868929b1a63e67fc',
    'acquisition-02/http-retention.json': '9c8270b7dfb88ff7f2aa38f5f043ade75d7c76fc8d51e85632fa7453ad5698a0',
    'acquisition-03/http-retention.json': '54859c5ca3c7ffae0225a076ddaa83611a39da6b8d895fa34fb58b65a9b6fac7',
    'acquisition-04/http-retention.json': '99ff9a5107cdf2ca93b04e4e7e4ecee505c2ebfcb88d17ddb2b83aab2dda8bbe',
    'exomizer-source-01/http-retention.json': '560487481e55bc286c0f09df3fd1119bb925146c6fe3f3a34b119093e809dcf2',
    'exomizer-source-02/http-retention.json': '5c37e2d2e75cc1eb775d7529b88d98d07b29009ba360bf856c19e58636328416',
    'exomizer-source-03/http-retention.json': '6c54cc73530bd153ea816fb5d2956a8bae861cc3a3f86ba39c46a5afe7ba6ffb',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def ref(path):
    path = Path(path)
    data = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(data), sha256=sha(data))


class HTML(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text, self.links, self.images, self.frames = [], [], [], []
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in ('script', 'style'):
            self.skip += 1
        if tag == 'a' and 'href' in attrs:
            self.links.append(attrs['href'])
        if tag == 'img' and 'src' in attrs:
            self.images.append(attrs['src'])
        if tag == 'iframe' and 'src' in attrs:
            self.frames.append(attrs['src'])

    def handle_endtag(self, tag):
        if tag in ('script', 'style'):
            self.skip -= 1

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data)


def html(data):
    parser = HTML()
    parser.feed(data.decode('utf-8', errors='replace'))
    return parser, ' '.join(' '.join(parser.text).split())


def http_audit():
    attempts, inputs = [], []
    for suffix, expected in MANIFESTS.items():
        path = ROOT / BASE / suffix
        assert sha(path.read_bytes()) == expected
        inputs.append(ref(path))
        data = json.loads(path.read_bytes())
        rows = data.get('attempts', [data])
        for row in rows:
            assert row['TLS_verification_bypassed'] is False
            if 'body' in row:
                assert ref(ROOT / row['body']['path']) == row['body']
            attempts.append(row)
    assert len(attempts) == 22
    return dict(pass_=True, manifests=inputs, attempts=attempts,
                status_counts=dict(Counter(str(row.get('status', 'exception')) for row in attempts)),
                retained_body_bytes=sum(row.get('body', {}).get('bytes', 0) for row in attempts),
                no_network_or_downloaded_host_execution_on_replay=True)


def source_anchors():
    """Bind retained author C/ASM bytes to their official archive members."""
    inputs, anchors = [], []
    for version, suffix in [('3.1.2', 'exomizer-source-01/official-source-tar.body'),
                            ('2.0.11', 'exomizer-source-02/official-2.0.11.tar.gz'),
                            ('3.1.1', 'exomizer-source-03/official-3.1.1.tar.gz')]:
        path = ROOT / BASE / suffix
        inputs.append(ref(path))
        archive = tarfile.open(fileobj=io.BytesIO(path.read_bytes()), mode='r:gz')
        if version != '3.1.1':
            continue
        for name in ['src/sfxdecr.s', 'src/exodec.c', 'rawdecrs/exodecr.c', 'src/flags.h']:
            member = next(m for m in archive.getmembers() if m.name.endswith('/' + name))
            copy = ROOT / BASE / 'exomizer-source-03' / (
                'flags.h' if name == 'src/flags.h' else name.replace('/', '__'))
            assert archive.extractfile(member).read() == copy.read_bytes()
            inputs.append(ref(copy))
        cp = ROOT / BASE / 'exomizer-source-03/src__exodec.c'
        lines = cp.read_text().splitlines()
        for lo, hi, terms, role in [
            (29, 52, ['PFLAG_BITS_ORDER_BE', '0x80'], 'MSB-first sentinel bit rotation'),
            (75, 116, ['PFLAG_BITS_COPY_GT_7', 'count &= 7'], 'Interleaved bit and raw-byte reader'),
            (144, 195, ['end = 52', 'get_bits(ctx, 3)', 'get_bits(ctx, 1) << 3'], '52 coding entries with three offset tables'),
            (282, 386, ['PFLAG_IMPL_1LITERAL', 'val == 16', 'val == 17', 'PFLAG_REUSE_OFFSET'], 'Literal/match/end grammar and optional protocol features')]:
            text = '\n'.join(lines[lo-1:hi])
            assert all(term in text for term in terms), role
            anchors.append(dict(source=ref(cp), first_line=lo, last_line=hi,
                                role=role, required_terms=terms, fragment=text))
        cp = ROOT / BASE / 'exomizer-source-03/flags.h'
        text = '\n'.join(cp.read_text().splitlines()[33:61])
        assert 'PBIT_BITS_ORDER_BE     0' in text and 'PBIT_BITS_COPY_GT_7    1' in text
        anchors.append(dict(source=ref(cp), first_line=34, last_line=61,
                            role='Protocol feature bit definitions; admitted profile bits 0 and 1 only',
                            fragment=text))
    return dict(pass_=True, inputs=inputs, anchors=anchors,
                attribution='Magnus Lind, official Exomizer source',
                source_version_is_not_claimed_to_be_original_packer_version=True)


def creator_followup():
    findings = []
    for label, suffix in [
        ('Quiss homepage', 'acquisition-01/quiss-home.body'),
        ('Quiss writings', 'acquisition-02/quiss-writings.body'),
        ('Quiss projects', 'acquisition-02/quiss-projects.body'),
        ('Quiss legacy', 'acquisition-02/quiss-legacy.body'),
        ('Quiss blog index', 'acquisition-03/quiss-blog-index.body'),
        ('Raistlin article index', 'acquisition-01/raistlin-article-index.body')]:
        p = ROOT / BASE / suffix
        parsed, text = html(p.read_bytes())
        assert 'aloft' not in text.casefold()
        findings.append(dict(source=ref(p), label=label, Aloft_text_matches=0,
                             links=parsed.links, inspected_text=text))
    hidden = ROOT / BASE / 'acquisition-01/aloft-creator-notes.body'
    _, text = html(hidden.read_bytes())
    assert 'Use a joystick to control the movement of the flipped Kefrens bars on Side 2.' in text
    assert 'In the first hangar scene, the space invaders in the upper left corner is playable.' in text
    screen1 = ROOT / BASE / 'acquisition-04/aloft-csdb-screenshot.png'
    screen2 = ROOT / BASE / 'acquisition-04/aloft-creator-pouet-screenshot.png'
    assert screen1.read_bytes() == screen2.read_bytes()
    assert screen1.read_bytes().startswith(b'\x89PNG\r\n\x1a\n')
    release = ROOT / BASE / 'acquisition-01/aloft-release.body'
    parsed, _ = html(release.read_bytes())
    assert '/gfx/releases/259000/259056.png' in parsed.images
    pouet = ROOT / BASE / 'acquisition-03/aloft-pouet.body'
    parsed, _ = html(pouet.read_bytes())
    assert 'https://content.pouet.net/files/screenshots/00105/00105671.png' in parsed.images
    return dict(pass_=True, bounded_creator_pages=findings, author_interaction_page=ref(hidden),
                interaction_note_is_not_a_rendering_explanation=True,
                release_screenshot=ref(screen1), creator_submission_screenshot=ref(screen2),
                screenshot_bytes_equal=True,
                manual_image_observation='Airplane against blue sky/clouds, not the striped prediction preview',
                gallery_failures=['Demozoo production page HTTP403', 'Demozoo production API HTTP403'],
                no_author_mechanism_or_named_striped_scene_recovered=True,
                no_claim_that_no_such_source_exists_elsewhere=True,
                peer_comments_excluded_as_implementation_authority=True,
                no_video_caption_retry_or_remote_media_download=True)


class Exo3Reader:
    def __init__(self, packed, low, end, initial_bits):
        self.packed, self.low, self.cursor = packed, low, end
        self.bitbuf = initial_bits
        self.reads = []

    def byte(self):
        assert self.cursor > self.low, 'compressed source exhausted'
        self.cursor -= 1
        self.reads.append(self.cursor)
        return self.packed[self.cursor-self.low]

    def bits(self, count):
        assert 0 <= count <= 16
        value = 0
        for _ in range(count & 7):
            carry = self.bitbuf >> 7
            self.bitbuf = (self.bitbuf << 1) & 255
            if not self.bitbuf:
                byte = self.byte()
                carry = byte >> 7
                self.bitbuf = ((byte << 1) | 1) & 255
            value = (value << 1) | carry
        for _ in range(count >> 3):
            value = (value << 8) | self.byte()
        return value


def perpetual(out):
    prg = (ROOT / PRG).read_bytes()
    assert len(prg) == 9469 and sha(prg) == PRG_SHA
    load = int.from_bytes(prg[:2], 'little')
    assert load == 0x0801
    def original(lo, hi):
        assert load <= lo <= hi <= load+len(prg)-2
        return prg[2+lo-load:2+hi-load]
    guards = [
        (0x0801, '0b081e009e32303631000000', 'BASIC SYS2061'),
        (0x080d, 'a035babd042c9dfc00cad0f74cb42b', 'Static first transfer and stage2 branch'),
        (0x2bb4, 'b9c62c99e60788d0f7', '53-byte file1 transfer, indexed operands are starts minus one'),
        (0x2bf9, 'c034d0c1a0fca0fc8a4c9f0122004b', '52-entry table bound and destination/bit-buffer metadata'),
        (0x2c08, '69800a100f06fdd00848201a012a85fd682a30f170016038859f', 'Exomizer3 MSB/copy-byte bit-reader'),
        (0x2c4b, '2a85fde890f3f0e5e011b05e', 'Explicit first literal flag and gamma terminator class'),
        (0x2c6b, 'a9f1e003b003bdbc01b820050118aa', 'Three offset tables, no offset-reuse branch'),
        (0x2c38, '98d002c6ff88201a0191feca', 'Predecrement literal destination and explicit next token'),
        (0x2ca7, '869ff098c69e4c8c01', 'Stage2 entry clears high accumulator then branches to explicit token'),
        (0x2cbc, '201a01aab0d24c0d08ccf2', 'Literal block tail, JMP080D and static offset constants')]
    bound = []
    for address, encoded, role in guards:
        raw = bytes.fromhex(encoded)
        assert original(address, address+len(raw)) == raw, (hex(address), role)
        bound.append(dict(address=address, end_exclusive=address+len(raw), hex=encoded, role=role))
    # Derive the first compressed prefix from the guarded original operands.
    transfer_len = original(0x080e, 0x080f)[0]
    source_minus_one = int.from_bytes(original(0x2bb5, 0x2bb7), 'little')
    dest_minus_one = int.from_bytes(original(0x2bb8, 0x2bba), 'little')
    low = dest_minus_one+1
    stream_end = int.from_bytes(original(0x2c35, 0x2c37), 'little')
    assert (transfer_len, source_minus_one, low, stream_end) == (53, 0x2cc6, 0x07e7, 0x2bb4)
    transferred = original(source_minus_one+1, source_minus_one+1+transfer_len)
    packed = transferred + original(low+transfer_len, stream_end)
    assert len(packed) == stream_end-low
    reader = Exo3Reader(packed, low, stream_end, original(0x2c05, 0x2c06)[0])
    tables, base = [], 1
    for index in range(52):
        if index % 16 == 0:
            base = 1
        width = reader.bits(3) | (reader.bits(1) << 3)
        assert 0 <= width <= 15 and 1 <= base <= 65535
        tables.append(dict(base=base, width=width))
        base += 1 << width
    memory, known = bytearray(65536), bytearray(65536)
    dest_end = (original(0x2c07, 0x2c08)[0] << 8) | original(0x2c00, 0x2c01)[0]
    assert dest_end == 0x4bfc
    dest, tokens, counts = dest_end, [], Counter()
    for token_index in range(65536):
        source_before = reader.cursor
        literal = reader.bits(1)
        gamma, offset = None, None
        if literal:
            length = 1
        else:
            gamma = 0
            while reader.bits(1) == 0:
                gamma += 1
                assert gamma <= 17, 'unrecognized gamma tag'
            if gamma == 16:
                counts['end'] += 1
                break
            if gamma == 17:
                literal, length = True, reader.bits(16)
            else:
                entry = tables[gamma]
                length = entry['base'] + reader.bits(entry['width'])
                index = (48+reader.bits(2)) if length == 1 else (
                    (32+reader.bits(4)) if length == 2 else (16+reader.bits(4)))
                entry = tables[index]
                offset = entry['base']+reader.bits(entry['width'])
        assert 0 < length <= 65535 and dest >= length
        end = dest
        for _ in range(length):
            dest -= 1
            if literal:
                value = reader.byte()
            else:
                match = dest+offset
                assert match < 65536 and known[match], ('unknown match read', match)
                value = memory[match]
            assert not low <= dest < reader.cursor, ('unread compressed source overwrite', dest)
            assert not known[dest], 'duplicate output address'
            memory[dest], known[dest] = value, 1
        kind = 'literal' if literal else 'match'
        counts[kind+'_tokens'] += 1
        counts[kind+'_bytes'] += length
        tokens.append(dict(index=token_index, kind=kind, gamma=gamma, length=length,
                           offset=offset, dest_low=dest, dest_end=end,
                           packed_before=source_before, packed_after=reader.cursor))
    else:
        raise AssertionError('token bound exhausted')
    assert counts['end'] == 1 and sum(known) == dest_end-dest
    assert reader.cursor == low and reader.bitbuf == 0x80, 'Noncanonical trailing packed bytes or bits'
    for name, data in [('perpetual-packed-data.bin', packed),
                       ('perpetual-predicted-memory.bin', memory),
                       ('perpetual-predicted-known.bin', known),
                       ('perpetual-unpacked.prg', dest.to_bytes(2, 'little')+memory[dest:dest_end])]:
        (out/name).write_bytes(data)
    (out/'perpetual-token-ledger.json').write_text(json.dumps(tokens, indent=2)+'\n')
    return dict(pass_=True, original_PRG=ref(ROOT/PRG), original_byte_guards=bound,
                format='Exomizer3 MSB-first, raw-byte extension, 52 coding entries, three offset tables',
                protocol_feature_mask=3,
                implicit_first_literal=False, reuse_offset=False, exact_packer_host_version_proved=False,
                original_source_profile_determined_without_trial_of_target_outputs=True,
                transfer=dict(length=transfer_len, source_first=source_minus_one+1,
                              source_end=source_minus_one+1+transfer_len, dest_first=low,
                              dest_end=low+transfer_len),
                stage3_stored_range=[0x2c08, 0x2cc7], stage3_logical_range=[0x0100, 0x01bf],
                initial_stage1_stack_requirement='Copying the complete resident requires TSX >= $C2; no runtime SP witness is claimed',
                table_count=len(tables), tables=tables, counts=dict(counts),
                output_range=[dest, dest_end], output_bytes=sum(known),
                source_range=[low, stream_end], source_bytes=len(packed),
                source_cursor_at_terminator=reader.cursor, unread_source_bytes=reader.cursor-low,
                remaining_bit_buffer=reader.bitbuf,
                no_unknown_memory_or_unread_input_overwrite=True,
                no_native_or_expected_payload_input=True, native_payload_comparison=False,
                released_demo_entry=0x080d, source_predictions_only=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = ROOT/args.output
    out.mkdir(parents=True, exist_ok=False)
    (out/'primary.checked.py').write_bytes(Path(__file__).read_bytes())
    results = {'http-audit.json': http_audit(), 'creator-followup.json': creator_followup(),
               'packer-primary-anchors.json': source_anchors()}
    for name, result in results.items():
        (out/name).write_text(json.dumps(result, indent=2)+'\n')
    results['perpetual-format-result.json'] = perpetual(out)
    (out/'perpetual-format-result.json').write_text(json.dumps(results['perpetual-format-result.json'], indent=2)+'\n')
    proof = dict(pass_=True, schema='aloft-motion-primary-and-perpetual-format-v1',
                 producer=ref(Path(__file__).resolve()),
                 outputs=[dict(name=p.name, bytes=p.stat().st_size, sha256=sha(p.read_bytes()))
                          for p in sorted(out.iterdir())],
                 HTTP_attempts=22, statuses=results['http-audit.json']['status_counts'],
                 retained_HTTP_bytes=results['http-audit.json']['retained_body_bytes'],
                 Perpetual_Fragility=results['perpetual-format-result.json'],
                 no_Aloft_author_or_named_scene_mechanism_match=True,
                 scope_limits=['The creator-route negative is bounded to retained pages, not the entire web',
                               'The original PRG receives a strict typed compressed-format prediction, not CPU or native execution',
                               'No snowfall coordinate identification, WIZ implementation match, complete display, timing or FPS claim',
                               'Refreshed Lunatico pages/archive are prior-result identities, not a newly recovered mechanism'])
    (out/'primary-proof.json').write_text(json.dumps(proof, indent=2)+'\n')
    print(json.dumps(dict(pass_=True, output=args.output,
                          payload=proof['Perpetual_Fragility']['output_range'],
                          bytes=proof['Perpetual_Fragility']['output_bytes'])))


if __name__ == '__main__':
    main()
