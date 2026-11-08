#!/usr/bin/env python3
"""Passively bind the retained SDK/tool archives, extracted caches and executions."""

import argparse
import hashlib
import json
from pathlib import Path
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/3dvibe64-native'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def pin(path):
    path = Path(path).resolve()
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=digest(data))


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    powershell = BASE / 'acquired/powershell-7.6.9-osx-arm64.tar.gz'
    tass = BASE / 'acquired/64tass-1.60.3243-src.zip'
    sdk = ROOT / 'build/research/3dvibe64/3Dvibe64_1.15.1_source.zip'
    assert pin(powershell)['sha256'] == 'a1c7e98ac403da4be5ba75c1c5855af272de7787a91d478c4267466fe58fc1af'
    assert pin(tass)['sha256'] == '9d83be3d23a2c55e085b7c7a7856c2f96080447ea120a6a8c21a217ed76427f0'
    assert pin(sdk)['sha256'] == '1ba034569a0beff013800322bc6c8f1134894ab6e13eb3bb2bb055482a668cbc'
    release = json.loads((BASE / 'acquired/powershell-release.json').read_text())
    assert release['tag_name'] == 'v7.6.9' and not release['prerelease']
    asset = next(x for x in release['assets'] if x['name'] == powershell.name)
    assert asset['digest'] == 'sha256:' + pin(powershell)['sha256']
    checksum_text = (BASE / 'acquired/hashes.sha256').read_text(encoding='utf-16')
    expected_line = pin(powershell)['sha256'] + ' *' + powershell.name
    assert expected_line in checksum_text.splitlines()

    cache_index = []
    archive_counts = []
    ps_root = BASE / 'tools/powershell-7.6.9'
    with tarfile.open(powershell) as archive:
        members = archive.getmembers()
        for member in members:
            if member.isfile():
                original = archive.extractfile(member).read()
                path = ps_root / member.name
                assert path.read_bytes() == original, member.name
                cache_index.append(pin(path))
        archive_counts.append(dict(kind='PowerShell', members=len(members),
                                   regular_files=sum(x.isfile() for x in members)))
    for kind, source, target in [('64tass', tass, BASE / 'tools/64tass-source'),
                                 ('SDK', sdk, BASE / 'sdk')]:
        with zipfile.ZipFile(source) as archive:
            members = archive.infolist()
            for member in members:
                if not member.is_dir():
                    path = target / member.filename
                    assert path.read_bytes() == archive.read(member), member.filename
                    cache_index.append(pin(path))
            archive_counts.append(dict(kind=kind, members=len(members),
                                       regular_files=sum(not x.is_dir() for x in members)))
    cache_index.sort(key=lambda x: x['path'])
    write(args.output / 'archive-member-index.json', cache_index)

    executables = [ps_root / 'pwsh',
                   BASE / 'tools/64tass-source/64tass-1.60.3243-src/64tass']
    runs = []
    for name in ['tool-steps/assemble-64tass', 'tool-steps/powershell-parse',
                 'build-01', 'symbols-01']:
        directory = BASE / name
        result = json.loads((directory / 'result.json').read_text())
        command = json.loads((directory / 'command.json').read_text())
        assert result['exit_code'] == 0 and not result['shell']
        assert result['command'] == command['command']
        for stream in ['stdout', 'stderr']:
            data = (directory / (stream + '.bin')).read_bytes()
            assert result[stream] == dict(bytes=len(data), sha256=digest(data))
        runs.append(dict(name=name, command=command,
                         files=[pin(directory / f) for f in ['command.json', 'result.json',
                                                            'stdout.bin', 'stderr.bin']]))
    parse = json.loads((BASE / 'tool-steps/powershell-parse/stdout.bin').read_text())
    assert parse['powershellVersion'] == '7.6.9' and parse['parseErrors'] == []
    assert parse['builderSha256'] == pin(BASE / 'sdk/work/build-3Dvibe64.ps1')['sha256']
    delta = json.loads((BASE / 'build-01/sdk-delta.json').read_text())
    assert delta['changed'] == [] and delta['removed'] == []
    assert delta['added'] == ['work/3Dvibe64.asm', 'work/3Dvibe64.prg', 'work/build/3Dvibe64.prg']
    products = BASE / 'build-01/products'
    assert (products / '3Dvibe64.prg').read_bytes() == (BASE / 'symbols-01/3Dvibe64.prg').read_bytes()
    assert (products / '3Dvibe64.prg').read_bytes() == (BASE / 'sdk/work/build/3Dvibe64.prg').read_bytes()
    index_pin = pin(args.output / 'archive-member-index.json')
    index_pin['name'] = 'archive-member-index.json'
    del index_pin['path']
    proof = dict(schema=1, producer=pin(Path(__file__)),
                 acquisition=[pin(x) for x in sorted((BASE / 'acquired').iterdir()) if x.is_file()],
                 sdk_archive=pin(sdk), archive_counts=archive_counts,
                 archive_member_index=index_pin,
                 executables=[pin(x) for x in executables], runs=runs,
                 builder_ast=parse, sdk_delta=pin(BASE / 'build-01/sdk-delta.json'),
                 products=[pin(products / x) for x in ['3Dvibe64.asm', '3Dvibe64.prg']],
                 limitations=[
                     'PowerShell matched the official API digest and published UTF-16 checksum list.',
                     '64tass source has a retrieval custody hash; no separate publisher checksum was obtained.',
                     'Extracted archive members are checked byte-for-byte; generated build files are separate.',
                     'This passive producer executes no upstream code, compiler or emulator.',
                     'Historical execution receipts are observations, not a sandbox guarantee or physical-hardware result.'
                 ])
    write(args.output / 'toolchain-proof.json', proof)
    print(json.dumps(dict(accepted=True, archive_counts=archive_counts,
                          checked_archive_files=len(cache_index),
                          proof=pin(args.output / 'toolchain-proof.json')), indent=2))


if __name__ == '__main__':
    main()
