#!/usr/bin/env python3
"""Inspect published Spires sources, original disks and prepared charset assets.

Passive local data analysis only. No original 6502 code, downloaded host tool,
assembler, emulator, subprocess or network request is executed by this file.
"""

from collections import Counter
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import stat
import struct
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/spires'
SOURCE = BASE / 'source'
OUT = BASE / 'analysis'
PINS = {
    'acquisitions.json': '43607601c40ed1e48cac80b3976caa3ab8137fe152eb7431703b0cafda15640b',
    'acquired/author.body': '670890e9b931488969b608aefddf712132b805a49d252e1e43d6bff1e32dfb5c',
    'acquired/github-repositories.body': 'b83d2a8f0950361860a38c1b51fbc6ef5ef5ce2427a05d534224a6126c6beb6b',
    'acquired/demozoo.body': 'f92ca1e7b22a700dd2eb9cdbd2d7ef108e45ad0e683698c9056db3ae5bcbebab',
    'acquired/original-release.body': '7a895ee1723a550002f70d57c386c807d74ab2e059dddc3b29658cc707832894',
    'acquired/release-page.body': '2c509bb8475752b23528b83363e081d972ca794ebd58f65da19f32bb3e9b63e7',
    'acquired/original-source.body': 'ae83489bef116bcfe5b018e6446dfdac0e91c39893c3c08946c4421fa0189d82',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def save(name, value):
    path = OUT / name
    path.write_text(json.dumps(value, indent=2) + '\n')
    return artifact(path)


def acquisition():
    rows = json.loads((BASE / 'acquisitions.json').read_text())
    assert len(rows) == 6
    for row in rows:
        data = (ROOT / row['path']).read_bytes()
        assert len(data) == row['bytes'] and sha(data) == row['sha256']
        assert row['url'].startswith(('https://www.elder0010.com/', 'https://csdb.dk/',
                                      'https://api.github.com/', 'https://demozoo.org/'))
    author = (BASE / 'acquired/author.body').read_text()
    release = (BASE / 'acquired/release-page.body').read_text()
    assert '108322' in author and '87813' in author
    assert '105505/Spires_-_Onslaught.zip' in release and '106229/spires_source.zip' in release
    repos = json.loads((BASE / 'acquired/github-repositories.body').read_text())
    assert len(repos) == 10
    return dict(records=rows, record_file=artifact(BASE / 'acquisitions.json'),
                author_page='https://www.elder0010.com/projects/spires/',
                release_page='https://csdb.dk/release/?id=108322',
                source_url='https://csdb.dk/getinternalfile.php/106229/spires_source.zip',
                release_url='https://csdb.dk/getinternalfile.php/105505/Spires_-_Onslaught.zip',
                source_link_present_on_author_linked_release=True,
                public_repositories=[row['full_name'] for row in repos],
                retained_HTTP_failures=[row for row in rows if row['status'] != 200])


def unpack(archive, directory):
    rows = []
    with zipfile.ZipFile(archive) as container:
        for item in container.infolist():
            name = PurePosixPath(item.filename.replace('\\', '/'))
            assert not name.is_absolute() and '..' not in name.parts
            assert item.file_size <= 2_000_000 and stat.S_IFMT(item.external_attr >> 16) != stat.S_IFLNK
            if item.is_dir():
                continue
            data = container.read(item)
            row = dict(name=item.filename, bytes=len(data), sha256=sha(data), compressed_bytes=item.compress_size,
                       CRC32=f'{item.CRC:08x}', retained_as_metadata_only='__MACOSX' in name.parts or '.DS_Store' in name.parts)
            if not row['retained_as_metadata_only']:
                target = directory.joinpath(*name.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
                row['file'] = artifact(target)
            rows.append(row)
    return dict(archive=artifact(archive), members=rows,
                extracted_files=sum(not row['retained_as_metadata_only'] for row in rows),
                downloaded_host_programs_executed=[])


def disk_files(path):
    data = path.read_bytes()
    assert len(data) == 174848
    sectors = [21 if track <= 17 else 19 if track <= 24 else 18 if track <= 30 else 17 for track in range(1, 36)]
    def block(track, sector):
        assert 1 <= track <= 35 and 0 <= sector < sectors[track - 1]
        first = (sum(sectors[:track - 1]) + sector) * 256
        return data[first:first + 256]
    track, sector, seen, entries = 18, 1, set(), []
    while track:
        assert (track, sector) not in seen
        seen.add((track, sector))
        page = block(track, sector)
        for first in range(0, 256, 32):
            row = page[first:first + 32]
            if not row[2]:
                continue
            current, part, visited, payload = row[3], row[4], [], bytearray()
            while current:
                assert (current, part) not in visited
                visited.append((current, part))
                item = block(current, part)
                payload.extend(item[2:] if item[0] else item[2:item[1] + 1])
                current, part = item[:2]
            entry = dict(ordinal=len(entries), filename_PETSCII=list(row[5:21]),
                         filename_latin1=row[5:21].rstrip(b'\xa0').decode('latin1'),
                         type=row[2], closed=bool(row[2] & 128), type_low=row[2] & 7,
                         declared_blocks=int.from_bytes(row[30:32], 'little'), sectors=[list(pair) for pair in visited])
            if payload:
                target = BASE / 'dos-files' / f'{len(entries):02d}.prg'
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(payload)
                entry.update(file=artifact(target), literal_load_address=int.from_bytes(payload[:2], 'little'))
                basic = re.search(rb'\x9e([0-9]+)\x00', payload[:32])
                entry['literal_BASIC_SYS'] = int(basic[1]) if basic else None
            entries.append(entry)
        track, sector = page[:2]
    files = [row for row in entries if row['type_low'] == 2 and 'file' in row]
    assert len(files) == 2 and [row['file']['bytes'] for row in files] == [12427, 6682]
    assert all(row['literal_load_address'] == 0x0801 and row['literal_BASIC_SYS'] == 2061 for row in files)
    return dict(disk=artifact(path), directory=entries, nonempty_PRG_files=files,
                scope='DOS chains and literal load/SYS fields only. No packed payload is decoded or executed.')


def clean_source(text):
    text = re.sub(r'/\*.*?\*/', lambda match: '\n' * match[0].count('\n'), text, flags=re.S)
    return '\n'.join(line.split('//', 1)[0] for line in text.splitlines())


def imports():
    pending, seen, rows = ['spires.asm'], set(), []
    while pending:
        name = pending.pop(0)
        if name in seen:
            continue
        seen.add(name)
        text = clean_source((SOURCE / name).read_text(encoding='latin1'))
        for match in re.finditer(r'\.import\s+(source|binary|c64)\s+"([^"\n]+)"', text):
            kind, target = match.groups()
            relative = (Path(name).parent / target.replace('\\', '/')).as_posix()
            path = SOURCE / relative
            row = dict(importer=name, line=1 + text[:match.start()].count('\n'), kind=kind,
                       target=relative, present=path.is_file())
            if path.is_file():
                row['file'] = artifact(path)
                if kind == 'source':
                    pending.append(relative)
            rows.append(row)
    return dict(reachable_source_units=sorted(seen), imports=rows,
                missing=[row for row in rows if not row['present']], source_build_attempted=False)


def fpp():
    path = SOURCE / 'fppinc.asm'
    text = path.read_text(encoding='latin1')
    assert re.search(r'fstraster\s+equ\s+\$3c', text)
    assert re.search(r'lda #\$fe\s+sta \$d015', text)
    macro = text.split('mac wait46bg', 1)[1].split('endm', 1)[0]
    assert re.findall(r'sta base\+scnpage\+\$03f([9a-f])', macro) == list('9abcdef')
    assert macro.index('sty $d017') < macro.index('stx $d017') < macro.index('sta base+scnpage+$03ff')
    calls = [int(value) for value in re.findall(r'^\s*wait46bg\s+(\d+)\s*$', text, re.M)]
    assert calls == list(range(1, 131))
    formula, recurrence, known = bytearray(4096), bytearray(4096), bytearray(4096)
    rows = []
    for width in range(1, 97):
        slab, slot = divmod(width - 1, 32)
        first = slot * 64 + slab * 21
        expected = bytes(sum((((8 * byte + bit) // width) & 1) << (7 - bit) for bit in range(8)) for byte in range(21))
        # A second source-derived model uses the sentinel-ROL and toggling run
        # counter, rather than the closed form above. It is not a CPU emulator.
        remaining, pixel, generated = width, 0, bytearray()
        for _ in range(21):
            accumulator = 1
            while True:
                sentinel_out = bool(accumulator & 128)
                accumulator = ((accumulator << 1) | pixel) & 255
                remaining -= 1
                if remaining == 0:
                    pixel ^= 1
                    remaining = width
                if sentinel_out:
                    break
            generated.append(accumulator)
        assert bytes(generated) == expected
        for shade in (0, 1):
            offset = shade * 2048 + first
            formula[offset:offset + 21] = bytes(value ^ (255 if shade else 0) for value in expected)
            recurrence[offset:offset + 21] = bytes(value ^ (255 if shade else 0) for value in generated)
            known[offset:offset + 21] = bytes([1]) * 21
        rows.append(dict(stripe_width=width, slot=slot, slab=slab, first_byte_within_definition=slab * 21,
                         byte_count=21, source_Y_base=61 - 7 * slab))
    assert formula == recurrence and sum(known) == 4032
    assert all(not known[i] for i in range(63, 4096, 64))
    pixels = OUT / 'fpp-source-patterns.bin'
    mask = OUT / 'fpp-source-patterns.known'
    pixels.write_bytes(formula)
    mask.write_bytes(known)
    phases = []
    for value in range(256):
        a = value
        carry = (a >> 7) & 1
        a = (a << 1) & 255
        for _ in range(2):
            a, carry = ((a << 1) | carry) & 255, (a >> 7) & 1
        a &= 1
        a, carry = ((a << 1) | carry) & 255, (a >> 7) & 1
        assert a == (value >> 5) & 3 and carry == 0
    for label, end in (('sinusz1', 'sinusy'), ('sinusz2', '; CHARSET')):
        block = text.split('\n' + label + '\n', 1)[1].split('\n' + end, 1)[0]
        values = [int(value) for line in block.splitlines() if re.match(r'\s*dc\.b', line)
                  for value in re.findall(r'\d+', line.split('dc.b', 1)[1])]
        assert len(values) == 256 and min(values) >= 1 and max(values) <= 95
        phases += values
    return dict(source=artifact(path), used_sprites=list(range(1, 8)), D015=0xfe,
                initial_Y=[[61 - 7 * slab - sprite for sprite in range(7)] for slab in range(3)],
                Y_base_values=[61, 54, 47], macro_calls=calls, pointer_rows=131,
                pointer_slots=[0xacf9 + i for i in range(7)],
                macro_nominal_CPU_cycles=46, macro_bytes_if_assembled=35,
                macro_D017_order='STY $D017 with Y=0; six pointer writes; STX $D017 with X=FF; seventh pointer write.',
                D011_values=sorted({0x18 | ((line + 61) & 7) for line in calls}),
                charset_address=0xa800, screen_address=0xac00, D018=0xba,
                prepared_slots_per_complement_bank=32, complement_banks=2,
                stripe_variants=96, stripe_bits_per_variant=168, source_generated_bytes=4032,
                allocated_pattern_bytes=4096, unused_final_bytes=64,
                patterns=artifact(pixels), known_mask=artifact(mask), variants=rows,
                independently_compared_source_math_bytes=4032,
                source_runtime_z_values=512, runtime_z_min=min(phases), runtime_z_max=max(phases),
                runtime_slot_formula='z &31', runtime_slab_formula='z >>5', actual_generated_stripe_width='z+1',
                intended_triplet_offsets=[[3 * sprite + 21 * slab for sprite in range(7)] for slab in range(3)],
                scope='Source arithmetic and packing only. Unwritten byte63 per definition is unknown; zero placeholders are masked out. Held MCBASE phase and actual display timing require native evidence.')


def tech():
    source_path = SOURCE / 'spires.asm'
    text = clean_source(source_path.read_text(encoding='latin1'))
    lut_path = SOURCE / 'tech_chars/lut.raw'
    lut = lut_path.read_bytes()
    assert len(lut) == 1024
    sets = [[(SOURCE / f'tech_chars/chs{bank}{phase}.raw').read_bytes() for phase in range(5)] for bank in range(2)]
    addresses = [[0x4000, 0x4800, 0x6000, 0x6800, 0x7000], [0xc000, 0xc800, 0xe000, 0xe800, 0xf000]]
    assets = []
    for bank in range(2):
        for phase in range(5):
            path = SOURCE / f'tech_chars/chs{bank}{phase}.raw'
            assert len(sets[bank][phase]) == 2048
            assert sets[bank][phase] == (SOURCE / f'techer tool/chs{bank}{phase}').read_bytes()
            declaration = rf'\.pc\s*=\s*\${addresses[bank][phase]:x}\s+"[^"\n]*"\s*(?:\w+:\s*)?\.import binary "tech_chars/chs{bank}{phase}\.raw"'
            assert re.search(declaration, text, re.I), path
            assets.append(dict(bank=bank, phase=phase, source_address=addresses[bank][phase], **artifact(path)))
    tables = {}
    for name in ('andata_d016', 'andata_d018'):
        body = text.split('.macro ' + name + '(){', 1)[1].split('}', 1)[0]
        tables[name] = bytes(int(value, 16) for value in re.findall(r'\$([0-9a-fA-F]+)', body))
        assert len(tables[name]) == 256
    phase_select = {0xe0: 0, 0xe2: 1, 0xe8: 2, 0xea: 3, 0xec: 4}
    displacement = [8 * phase_select[d018] + (d016 & 7) for d016, d018 in zip(tables['andata_d016'], tables['andata_d018'])]
    assert set(displacement) == set(range(40))
    assert max(abs(a - b) for a, b in zip(displacement, displacement[1:])) == 1
    assert set(tables['andata_d016']) == set(range(0xd8, 0xe0))
    for d018, phase in phase_select.items():
        for bank in range(2):
            base = 0x4000 if bank == 0 else 0xc000
            assert base + ((d018 & 14) << 10) == addresses[bank][phase]
            assert base + ((d018 >> 4) * 1024) == (0x7800 if bank == 0 else 0xf800)
    assert 'cmp #19' in text and 'cmp #25' in text and 'sty $dd00' in text
    def image(phase, top_only=False, screen=lut):
        return bytes(sets[0 if top_only or line < 152 else 1][phase][screen[(line // 8) * 40 + cell] * 8 + line % 8]
                     for line in range(200) for cell in range(40))
    base = image(0)
    proofs = []
    for phase in range(5):
        actual = image(phase)
        expected = bytes(base[line * 40 + cell - phase] if cell >= phase else 0
                         for line in range(200) for cell in range(40))
        assert len(actual) == 8000 and actual == expected
        path = OUT / f'tech-phase-{phase}-glyph-rows.bin'
        path.write_bytes(actual)
        wrong_bank = sum(a != b for a, b in zip(actual, image(phase, top_only=True)))
        wrong_shift = sum(a != b for a, b in zip(actual, base))
        assert wrong_bank and (wrong_shift or phase == 0)
        proofs.append(dict(phase=phase, shifted_physical_pixels=8 * phase, glyph_row_bytes=8000,
                           difference_count=0, reconstructed=artifact(path),
                           reuse_top_charset_for_bottom_control_differences=wrong_bank,
                           omit_coarse_shift_control_differences=wrong_shift))
    tool_lut = (SOURCE / 'techer tool/lut').read_bytes()
    assert len(tool_lut) == 1024
    lut_changes = [i for i, (a, b) in enumerate(zip(lut, tool_lut)) if a != b]
    assert len(lut_changes) == 817
    tables_path = OUT / 'tech-D016-D018-tables.bin'
    tables_path.write_bytes(tables['andata_d016'] + tables['andata_d018'])
    return dict(source=artifact(source_path), charset_assets=assets, charset_bytes=20480,
                common_screen_asset=artifact(lut_path), visible_matrix_cells=1000,
                source_screen_addresses=[0x7800, 0xf800], physical_matrix_copies_share_same_import=True,
                source_vertical_bank_split=dict(top_character_rows=19, bottom_character_rows=6,
                                               top_pixel_rows=152, bottom_pixel_rows=48),
                actual_horizontal_phases=5, coarse_physical_shifts=[0, 8, 16, 24, 32],
                D018_to_phase={f'{key:02x}': value for key, value in phase_select.items()},
                D016_values=list(range(0xd8, 0xe0)), fine_physical_shifts=list(range(8)),
                full_displacement_values=displacement, distinct_displacements=40,
                maximum_adjacent_table_displacement_change=1, tables=artifact(tables_path),
                reconstructed_full_images=proofs, independently_compared_glyph_row_bytes=40000,
                padding_or_foreground_palette_rendered=False,
                tool_folder_charset_bytes_equal=20480,
                tool_folder_LUT=artifact(SOURCE / 'techer tool/lut'),
                rejected_identical_tool_LUT_assumption=dict(changed_bytes=817, changed_offsets=lut_changes,
                    interpretation='Use the published demo LUT. The tool-folder LUT is a different input and is not silently substituted.'),
                scope='Exact prepared-asset translations and register-table arithmetic, not native output or a rerun of the unavailable generator source.')


def tool():
    path = SOURCE / 'techer tool/techer'
    data = path.read_bytes()
    header = struct.unpack_from('<IiiIIIII', data)
    assert header[0] == 0xfeedfacf and header[1] == 0x01000007
    usage = [item.decode('ascii') for item in re.findall(rb'[ -~]{5,}', data)
             if item.startswith((b' techer <', b' - org', b' - dst', b'Looking for blank', b'Rebuilding screen', b'Building scroll'))]
    assert usage and not list(SOURCE.rglob('*.c')) and not list(SOURCE.rglob('*.cpp'))
    return dict(file=artifact(path), format='Mach-O64', CPU='x86-64', header_fields=list(header),
                embedded_usage_strings=usage, custom_generator_source_present=False,
                executed=False, scope='Opaque executable metadata and strings only. No binary or script is run.')


def main():
    for relative, digest in PINS.items():
        assert sha((BASE / relative).read_bytes()) == digest, relative
    OUT.mkdir(parents=True, exist_ok=True)
    provenance = acquisition()
    release = unpack(BASE / 'acquired/original-release.body', BASE / 'release')
    source = unpack(BASE / 'acquired/original-source.body', SOURCE)
    original_disk = BASE / 'release/Spires_-_Onslaught.d64'
    source_disk = SOURCE / 'spires-onslaught.d64'
    assert original_disk.read_bytes() == source_disk.read_bytes()
    files = disk_files(original_disk)
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()), acquisitions=provenance,
        original_release=release, original_source_archive=source,
        source_bundled_disk=dict(**artifact(source_disk), exact_original_release_disk=True),
        original_DOS=files, source_import_closure=imports(), FPP_source_math=fpp(),
        TechTech_asset_and_table_proof=tech(), generator_tool_inventory=tool(),
        original_6502_or_host_programs_executed=[], assembler_or_native_VICE_run=False,
        source_rebuilt=False, original_packed_payload_decoded=False,
        original_executable_equals_source_build_proven=False, native_sprite_or_text_pixels_proven=False,
        limits=[
            'The source ZIP includes the exact original disk, but that identity is not equality between a newly assembled source build and the packed original executable.',
            'Active imports are missing from the main source closure. The custom charset generator is supplied as an opaque host executable without C/C++ source and is never executed.',
            'FPP stripe packing is exhaustively checked with two independent source-level mathematical descriptions; actual generated runtime RAM and held sprite counter phases are not observed.',
            'TechTech checks use the published demo charset and screen assets. The different tool-folder LUT is retained as a rejected substitution, not called a successful generator round trip.',
            'Nominal macro CPU cycles exclude VIC-II stalls, IRQ entry, branches elsewhere and runtime scheduling. No native raster deadline or demo FPS is measured.',
            'Prepared glyph-row bytes and physical translations are not native VIC palette output. Runtime color RAM, fine-scroll/bank timing and border behavior require a native witness.'])
    result['pass'] = result.pop('pass_')
    receipt = save('spires-proof.json', result)
    (OUT / 'inspect.checked.py').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(pass_=True, original_source_disk_exact=True,
        FPP_source_math_bytes=4032, TechTech_asset_bytes=20480, translated_glyph_row_bytes=40000,
        physical_coarse_shifts=[0, 8, 16, 24, 32], fine_combined_positions=40,
        missing_main_imports=len(result['source_import_closure']['missing']), receipt=receipt), indent=2))


if __name__ == '__main__':
    main()
