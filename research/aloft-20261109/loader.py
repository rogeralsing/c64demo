#!/usr/bin/env python3
"""Passive original-Aloft bootstrap/resident identification; no CPU execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DISK = ROOT / 'build/research/aloft-20261109/disk-analysis/accepted-01'
SOURCE = ROOT / 'build/research/colors/binary/source'
PIN = {
    'disk-proof.json': '113eadc069fbf46bb1011d7c9373d175f4c3536950f7a7ee173f471b8f1eef84',
    'bootstrap': '7e283e390a10c2b7784ac1885081234c21a754d161e938babd504a13da2ee2e5',
    'loader-v3.4.260405.cpp': '6b60719200fe199b0bb36b2b836e4d4aa09d574f3e50704baca38a64624617f1',
    'sl-v3.4.260405.asm': '223deb8c52b2aad69f8e5d4ba4573c196b0685f1a595f8e655f35c29d7777c02',
    'sparkle-acquisition.json': 'a5ebba5e352c8dcfebe5699d4e7b8d0c59cad19bcb181c9ee4c4912e5c96bf0b',
}
RESIDENT_SHA = 'b09c13f9f60a28aa87cf1b157b4035df325eb60bf6d79fe8f176cf7aa606db48'
COMMIT = '41d6963b8334dd5f0046ff0dfccb29ef7d9ad0fb'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def meta(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}


def read_pinned(path, digest):
    data = path.read_bytes()
    assert sha(data) == digest, str(path)
    return data


def jbytes(value):
    return (json.dumps(value, indent=2, sort_keys=True) + '\n').encode()


def span(prg, address, length):
    base = int.from_bytes(prg[:2], 'little')
    offset = 2 + address - base
    assert offset >= 2 and offset + length <= len(prg)
    return prg[offset:offset + length]


def guard(prg, address, expected):
    expected = bytes.fromhex(expected)
    assert span(prg, address, len(expected)) == expected, hex(address)
    return {'PC': address, 'bytes_hex': expected.hex()}


def install_copy(prg):
    """Evaluate the two explicitly guarded 256-byte indexed copies as data."""
    payload = prg[2:]
    hits = []
    for offset in range(len(payload) - 14):
        b = payload[offset:offset + 15]
        if (b[0] == 0xBD and b[3:7] == bytes.fromhex('9d6001bd')
                and b[9:] == bytes.fromhex('9d0002e8d0f1')):
            hits.append((int.from_bytes(prg[:2], 'little') + offset, b))
    assert len(hits) == 1
    pc, code = hits[0]
    assert span(prg, pc - 5, 5) == bytes.fromhex('a2008e00dd')
    source1 = int.from_bytes(code[1:3], 'little')
    source2 = int.from_bytes(code[7:9], 'little')
    assert source2 - source1 == 0xA0
    memory = {}
    writes = []
    duplicates = 0
    for x in range(256):
        for source, dest in [(source1 + x, 0x160 + x), (source2 + x, 0x200 + x)]:
            value = span(prg, source, 1)[0]
            if dest in memory:
                assert memory[dest] == value
                duplicates += 1
            memory[dest] = value
            writes.append({'source': source, 'destination': dest, 'value': value})
    assert len(memory) == 416 and duplicates == 96
    assert set(memory) == set(range(0x160, 0x300))
    result = bytes(memory[a] for a in range(0x160, 0x300))
    assert result == span(prg, source1, 416)
    return result, {
        'copy_loop_PC': pc, 'copy_loop_hex': code.hex(),
        'initial_X': 0, 'X_values': 256, 'logical_copy_writes': len(writes),
        'source1': source1, 'source2': source2, 'destination1': 0x160, 'destination2': 0x200,
        'identical_duplicate_destinations': duplicates, 'unique_installed_bytes': 416,
        'installed_start': 0x160, 'installed_end_exclusive': 0x300,
        'source_end_exclusive': source2 + 256,
        'all_source_bytes_inside_loaded_PRG': True,
        'resident_sha256': sha(result),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to(ROOT / 'build/research/aloft-20261109/loader-analysis')
    out.mkdir(parents=True, exist_ok=False)

    disk_path = DISK / 'disk-proof.json'
    disk = json.loads(read_pinned(disk_path, PIN['disk-proof.json']))
    assert disk['pass_'] and disk['all_three_bootstrap_PRGs_identical']
    boot_paths = [DISK / f'bootstrap-side{i}.prg' for i in range(1, 4)]
    boots = [read_pinned(p, PIN['bootstrap']) for p in boot_paths]
    boot = boots[0]
    assert len(boot) == 832 and len(set(boots)) == 1
    assert boot[:2] == bytes.fromhex('0108')
    assert span(boot, 0x801, 13) == bytes.fromhex('0b080a009e3230363400000000')
    cpp_path = SOURCE / 'loader-v3.4.260405.cpp'
    asm_path = SOURCE / 'sl-v3.4.260405.asm'
    acquisition_path = SOURCE / 'sparkle-acquisition.json'
    cpp = read_pinned(cpp_path, PIN[cpp_path.name]).decode()
    asm = read_pinned(asm_path, PIN[asm_path.name]).decode()
    acquisition = json.loads(read_pinned(acquisition_path, PIN[acquisition_path.name]))
    assert acquisition['commit'] == COMMIT and acquisition['tag'] == 'v3.4.260405'
    for record in acquisition['records']:
        assert record['http_status'] == 200 and COMMIT in record['url']
        assert record['sha256'] == PIN[Path(record['path']).name]
    array = re.search(r'unsigned char loader\[loader_size\] = \{(.*?)\};', cpp, re.S)
    assert array and 'const int loader_size = 849;' in cpp
    canonical = bytes(int(v, 16) for v in re.findall(r'0x([\da-fA-F]{2})', array[1]))
    assert len(canonical) == 849
    assert sha(canonical) == 'c3af3c519034fb5fe8dfa4cc7749b8e55922f599de5caf6d6ef3158568ff87d0'
    actual_resident, actual_map = install_copy(boot)
    canonical_resident, canonical_map = install_copy(canonical)
    assert actual_resident == canonical_resident and sha(actual_resident) == RESIDENT_SHA
    assert actual_map['copy_loop_PC'] == 0x8A6
    assert actual_map['source1'] == 0x99F and actual_map['source2'] == 0xA3F
    assert actual_map['source_end_exclusive'] == 0xB3F

    guards = [
        guard(boot, 0x810, 'a9ff85fca204a90885baa5ba200ceda96f20b9ed'),
        guard(boot, 0x894, '78a9358501a25f9aa93c8d02dd'),
        guard(boot, 0x8B5, 'ad12d0cd12d0f0fb30f6c920b02c'),
        guard(boot, 0x8C3, 'a9408dc201a9dc8dc301a2029db5019dcf019ddc01a9f8cad0f2a9b98db501a9198dc1018dcf01a9398ddc01'),
        guard(boot, 0x8EF, 'a9f82c00dd30fb8d00dda9fd48a9ff484c9f01'),
    ]
    pushed = (span(boot, 0x8FA, 1)[0] << 8) | span(boot, 0x8FD, 1)[0]
    assert pushed == 0xFDFF
    handoff = (pushed + 1) & 0xFFFF
    assert handoff == 0xFE00

    roles = [
        ('Sparkle_IRQ', 0x160, '488a489848a50148200502ee19d0200902', 263, 285),
        ('Sparkle_SendCmd', 0x17A, '8504200502a2188e00dd2c00dd30fb', 289, 309),
        ('Sparkle_LoadA', 0x19C, '207a01', 313, 314),
        ('Sparkle_LoadFetched', 0x19F, '200502a200a0088c00dd2c00dd70fb', 318, 329),
        ('Set01', 0x205, 'a9358501', 397, 398),
        ('Done', 0x209, '60', 399, 399),
        ('Sparkle_LoadNext', 0x21C, 'a2ff8edd02e8bd0003d005aeff03d0f68504', 426, 435),
    ]
    roles_output = []
    for label, pc, code, first, last in roles:
        expected = bytes.fromhex(code)
        assert actual_resident[pc - 0x160:pc - 0x160 + len(expected)] == expected
        assert label + ':' in '\n'.join(asm.splitlines()[first - 1:last])
        roles_output.append({'label': label, 'PC': pc, 'bytes_hex': code,
                             'primary_asm_lines': [first, last]})
    for token in ['.pseudopc $0160', '.label ZPDst', '.label Bits', '.const Buffer',
                  'BLOCK STRUCTURE FOR DEPACKER', 'NextFile:', 'LitCopy:', 'MatchCopy:']:
        assert token in asm

    provenance = {
        'original_copy': actual_map, 'primary_reference_copy': canonical_map,
        'byte_identical_resident_bytes': 416, 'mismatches': 0,
        'whole_bootstrap_identical_to_primary_reference': boot == canonical,
        'original_bootstrap_bytes': len(boot), 'reference_bootstrap_bytes': len(canonical),
        'primary_reference_PRG_sha256': sha(canonical),
        'original_guards': guards, 'resident_roles': roles_output,
        'first_return_address_pushed': pushed, 'natural_RTS_destination': handoff,
        'primary_format_contract_lines': {
            'receive_and_block_layout': [335, 424], 'file_header_and_memory_config': [437, 459],
            'match_classes_and_end_tags': [465, 481], 'backward_literal_copy': [510, 530],
            'backward_match_copy': [536, 561],
        },
        'next_native_checkpoints': [
            {'PC': 0x810, 'meaning': 'original BASIC SYS entry, before installer'},
            {'PC': 0x8B5, 'meaning': 'copy completed, before PAL/NTSC receiver patches'},
            {'PC': 0x19F, 'meaning': 'original first LoadFetched handoff'},
            {'PC': handoff, 'meaning': 'configured initial RTS destination, not an effect identity'},
        ],
    }
    (out / 'resident-0160.bin').write_bytes(actual_resident)
    (out / 'loader-contract.json').write_bytes(jbytes(provenance))
    (out / 'loader.checked.py').write_bytes(Path(__file__).read_bytes())
    outputs = [{'name': p.name, 'bytes': p.stat().st_size, 'sha256': sha(p.read_bytes())}
               for p in sorted(out.iterdir())]
    proof = {
        'pass_': True,
        'scope': 'Original Aloft installer static data copies and exact primary Sparkle resident identity',
        'producer': meta(Path(__file__).resolve()),
        'inputs': [meta(disk_path), *[meta(p) for p in boot_paths], meta(cpp_path), meta(asm_path), meta(acquisition_path)],
        'primary_commit': COMMIT, 'primary_tag': acquisition['tag'],
        'source_URLs': [r['url'] for r in acquisition['records']],
        'contract': provenance,
        'outputs': outputs,
        'limits': [
            'No CPU, assembler, emulator, native process, upstream script or host tool executed.',
            'Shared resident bytes do not establish Aloft host-tool version/build date; the reference tag postdates the February release.',
            'Copy result is pre-PAL/NTSC and pre-depacker self-modification, not a claim of unchanged later RAM.',
            'No disk block/bundle mapping, drive implementation, first payload or named layered-pattern effect has been decoded here.',
            'The initial configured RTS destination is conditional on a successful original first loader call, not native execution evidence.',
        ],
    }
    (out / 'loader-proof.json').write_bytes(jbytes(proof))
    print(json.dumps({'pass_': True, 'resident_bytes': 416, 'resident_sha256': sha(actual_resident),
                      'proof': str(out / 'loader-proof.json')}))


if __name__ == '__main__':
    main()
