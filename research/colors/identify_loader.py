#!/usr/bin/env python3
"""Compare original Colors boot PRGs with pinned primary Sparkle source text.

No source is compiled, no CPU is interpreted, and no hardware is contacted.
--fetch-source downloads only the two fixed author source files when requested.
"""
import argparse
import datetime
import json
from pathlib import Path
import re
import urllib.request

from inspect_boot import ROOT, BASE, BOOT_SHAS, sha

COMMIT = '41d6963b8334dd5f0046ff0dfccb29ef7d9ad0fb'
ARRAY_SHA = 'c3af3c519034fb5fe8dfa4cc7749b8e55922f599de5caf6d6ef3158568ff87d0'
SOURCES = [
    ('loader.cpp', 'loader-v3.4.260405.cpp', '6b60719200fe199b0bb36b2b836e4d4aa09d574f3e50704baca38a64624617f1'),
    ('resources/sl.asm', 'sl-v3.4.260405.asm', '223deb8c52b2aad69f8e5d4ba4573c196b0685f1a595f8e655f35c29d7777c02'),
]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=BASE/'binary')
    parser.add_argument('--fetch-source', action='store_true')
    args = parser.parse_args()
    source = args.output/'source'
    source.mkdir(parents=True, exist_ok=True)
    downloads = []
    for member, name, expected_sha in SOURCES:
        path = source/name
        url = f'https://raw.githubusercontent.com/spartaomg/SparkleCPP/{COMMIT}/{member}'
        if args.fetch_source:
            with urllib.request.urlopen(url, timeout=30) as response:
                blob, final, status = response.read(), response.url, response.status
            assert sha(blob) == expected_sha
            path.write_bytes(blob)
            downloads.append(dict(url=url, final_url=final, http_status=status,
                                  path=str(path.relative_to(ROOT)), bytes=len(blob), sha256=sha(blob),
                                  utc=datetime.datetime.now(datetime.timezone.utc).isoformat()))
        assert path.exists(), f'Missing pinned source; run with --fetch-source: {path}'
        assert sha(path.read_bytes()) == expected_sha
    if downloads:
        (source/'sparkle-acquisition.json').write_text(json.dumps(dict(commit=COMMIT, tag='v3.4.260405',
            records=downloads, scope='Primary author source text only; not compiled/executed'),indent=2)+'\n')
    text = (source/SOURCES[0][1]).read_text()
    body = re.search(r'unsigned char loader\[loader_size\]\s*=\s*\{([^}]+)\}', text, re.S).group(1)
    canonical = bytes(int(x,16) for x in re.findall(r'0x([0-9a-fA-F]{2})', body))
    assert len(canonical) == 849 and sha(canonical) == ARRAY_SHA
    records, resident_images = [], []
    for side, expected_sha in enumerate(BOOT_SHAS,1):
        path = args.output/f'side{side}-boot.prg'
        blob = path.read_bytes()
        assert sha(blob) == expected_sha
        different = [dict(file_offset=i, memory_address=0x801+i-2, canonical=a, release=b)
                     for i,(a,b) in enumerate(zip(canonical,blob)) if a!=b]
        assert [d['file_offset'] for d in different] == [269,272]
        entry = (((blob[269]<<8)|blob[272])+1)&65535
        assert entry == (0x8000,0x0005,0xc000)[side-1]
        memory = bytearray(65536)
        memory[0x801:0xb50] = blob[2:]
        assert memory[0x8b3:0x8c7] == bytes.fromhex('a2 00 8e 00 dd bd b0 09 9d 60 01 bd 50 0a 9d 00 02 e8 d0 f1')
        assert memory[0x911:0x914] == bytes.fromhex('4c 9f 01')
        installed = {}
        overlap = set()
        for x in range(256):
            for first,target in ((0x9b0,0x160),(0xa50,0x200)):
                address, value = target+x, memory[first+x]
                if address in installed:
                    assert installed[address] == value
                    overlap.add(address)
                installed[address] = value
        assert set(installed) == set(range(0x160,0x300)) and len(overlap)==96
        resident = bytes(installed[a] for a in range(0x160,0x300))
        assert resident == memory[0x9b0:0xb50]
        resident_images.append(resident)
        records.append(dict(side=side, boot_sha256=sha(blob), canonical_matched_bytes=847,
                            differences=different, configured_RTS_entry=entry,
                            resident_source=[0x9b0,0xb50], resident_destination=[0x160,0x300],
                            overlap_bytes_identical=96, resident_sha256=sha(resident)))
    assert resident_images[0] == resident_images[1] == resident_images[2]
    (args.output/'resident-reference.bin').write_bytes(resident_images[0])
    names = dict(Sparkle_IRQ=0x160, Sparkle_SendCmd=0x17a, Sparkle_LoadA=0x19c,
                 Sparkle_LoadFetched=0x19f, Set01=0x205, Done=0x209, Sparkle_LoadNext=0x21c)
    symbols = [dict(name=name, address=address, first_bytes=resident_images[0][address-0x160:address-0x160+12].hex(' '))
               for name,address in names.items()]
    result = dict(pass_=True, identification='Sparkle 3.4 loader matching v3.4.260405',
                  version_limit='Matching loader bytes persist in later builds; exact host tool build/date is not identified.',
                  primary_source_commit=COMMIT, primary_source_files=[dict(member=m, local=n, sha256=h) for m,n,h in SOURCES],
                  canonical_array_bytes=len(canonical), canonical_array_sha256=ARRAY_SHA,
                  script_sha256=sha(Path(__file__).read_bytes()), sides=records,
                  literal_copy_symbols=symbols, buffer=0x300, destination_ZP=[2,3], bits_ZP=4,
                  clean_post_copy_checkpoint=0x8c7, boot_loader_jump=0x911, boot_loader_entry=0x19f,
                  scope='Exact source-array comparison and literal copy arithmetic only. Resident symbols use the matching author assembly. No loader/drive/depacker/effect execution or native match is asserted.')
    result['pass'] = result.pop('pass_')
    (args.output/'loader-identification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(pass_=True, family=result['identification'], configured_entries=[r['configured_RTS_entry'] for r in records],
                         resident_bytes=len(resident_images[0]), resident_sha256=sha(resident_images[0])),indent=2))


if __name__ == '__main__':
    main()
