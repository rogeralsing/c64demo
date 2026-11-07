#!/usr/bin/env python3
"""Extract author arrays and conventional D64 files; never execute host binaries."""
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / 'build/research/frontier/Mufflon1.0-source+GUI+Bonus/Mufflon1.0-source+Bonus'
OUT = ROOT / 'build/research/nufli'


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def arrays():
    text = (PACKAGE / 'mufflon-source+GUI/mufflon.h').read_text()
    text = re.sub(r'/\*.*?\*/', '', text, flags=re.S)
    result = {}
    names = ('nuifli_displayer_code1', 'nuifli_displayer_code2',
             'nuifli_displayer_code3', 'nuifli_scram', 'nuifli_spram',
             'flibug_hires_spram', 'flibug_multi_spram', 'nuifli_sprite_pointers')
    for name in names:
        body = re.search(r'\b' + name + r'\s*\[[^=]*=\s*\{(.*?)\};', text, re.S).group(1)
        result[name] = [int(x, 0) for x in re.findall(r'0x[0-9a-fA-F]+|\b\d+\b', body)]
    return result


def sectors(track):
    assert 1 <= track <= 35
    return 21 if track <= 17 else 19 if track <= 24 else 18 if track <= 30 else 17


def sector(disk, track, number):
    assert 0 <= number < sectors(track)
    offset = (sum(sectors(t) for t in range(1, track)) + number) * 256
    return disk[offset:offset+256]


def files(disk):
    track, number = 18, 1
    visited = set()
    while track:
        assert (track, number) not in visited
        visited.add((track, number))
        block = sector(disk, track, number)
        for offset in range(0, 256, 32):
            entry = block[offset:offset+32]
            if not entry[2]:
                continue
            name = bytes(entry[5:21]).rstrip(b'\xa0').decode('latin1')
            t, s = entry[3:5]
            data, chain = bytearray(), []
            while t:
                assert (t, s) not in chain
                chain.append((t, s))
                piece = sector(disk, t, s)
                nt, ns = piece[:2]
                data.extend(piece[2:] if nt else piece[2:ns+1])
                t, s = nt, ns
            yield name, entry[2], bytes(data), chain
        track, number = block[:2]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    archive = ROOT / 'build/research/frontier/Mufflon1.0-source+GUI+Bonus.zip'
    assert sha(archive.read_bytes()) == 'c610bc91ec7f60bd7c19c19fe0ecc4e97288a26b12e65febad3827da1f4d4adf'
    # Prove these pre-extracted files actually belong to the pinned archive.
    with zipfile.ZipFile(archive) as package:
        for path in (PACKAGE/'mufflon-source+GUI/mufflon.c',
                     PACKAGE/'mufflon-source+GUI/mufflon.h', PACKAGE/'Mufflon-README.txt',
                     *sorted((PACKAGE/'Examplepictures').glob('*.d64'))):
            suffix = str(path.relative_to(PACKAGE))
            names = [name for name in package.namelist() if name.endswith('/'+suffix)]
            assert len(names) == 1 and package.read(names[0]) == path.read_bytes(), suffix
    tables = arrays()
    (OUT / 'source-arrays.json').write_text(json.dumps(tables, indent=2) + '\n')
    memory = bytearray(65536)
    code_receipts = []
    for n, address in ((1, 0x3000), (2, 0x3300), (3, 0x3fc0)):
        data = bytes(tables[f'nuifli_displayer_code{n}'])
        memory[address:address+len(data)] = data
        (OUT / f'displayer-{address:04x}.bin').write_bytes(data)
        code_receipts.append(dict(address=address, size=len(data), sha256=sha(data)))
    sys.path.insert(0, str(ROOT / 'research/tower-power'))
    from static_loader import decode
    disassembly = []
    for lo, hi in ((0x3000, 0x31f5), (0x33b0, 0x33d6)):
        pc = lo
        while pc < hi:
            item = decode(memory, pc)
            disassembly.append(f"{pc:04x}: {item['bytes']:8s} {item['mnemonic']} {item['text']}")
            pc = item['next']
    (OUT / 'displayer.txt').write_text('\n'.join(disassembly) + '\n')
    index = []
    for diskpath in sorted((PACKAGE / 'Examplepictures').glob('*.d64')):
        directory = OUT / diskpath.stem
        directory.mkdir(exist_ok=True)
        for i, (name, kind, blob, chain) in enumerate(files(diskpath.read_bytes())):
            safe = re.sub(r'[^a-zA-Z0-9._-]', '_', name)
            target = directory / f'{i:02d}-{safe}.prg'
            target.write_bytes(blob)
            load = int.from_bytes(blob[:2], 'little')
            matches = []
            for block in code_receipts:
                a, size = block['address'], block['size']
                actual = blob[a-load+2:a-load+2+size] if load <= a else b''
                matches.append(actual == memory[a:a+size])
            index.append(dict(disk=str(diskpath.relative_to(ROOT)), name=name,
                              type=kind, path=str(target.relative_to(ROOT)),
                              bytes=len(blob), sha256=sha(blob), load_address=load,
                              chain=chain, embedded_code_matches=matches))
    receipt = dict(archive=dict(path='build/research/frontier/Mufflon1.0-source+GUI+Bonus.zip',
                  url='https://csdb.dk/getinternalfile.php/180585/Mufflon1.0-source+GUI+Bonus.zip',
                  sha256=sha(archive.read_bytes()), extracted_sources_and_disks_match=True),
                  sources={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in
                           [PACKAGE / 'mufflon-source+GUI/mufflon.c',
                            PACKAGE / 'mufflon-source+GUI/mufflon.h', PACKAGE / 'Mufflon-README.txt']},
                  code=code_receipts, files=index)
    (OUT / 'extraction.json').write_text(json.dumps(receipt, indent=2) + '\n')
    for f in index:
        print(f"{f['name']!r}: {f['bytes']} bytes, ${f['load_address']:04x}, code {f['embedded_code_matches']}")


if __name__ == '__main__':
    main()
