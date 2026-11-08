#!/usr/bin/env python3
"""Record one explicit host build/tool command in a new evidence directory.

The command uses an argument array, never a shell. This helper is not used to
own VICE; native captures retain the separate cancellable observer contract.
"""

import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def utc():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cwd', type=Path, required=True)
    parser.add_argument('--env', action='append', default=[])
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if not command:
        parser.error('An explicit command is required after --')
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    overrides = dict(value.split('=', 1) for value in args.env)
    receipt = dict(command=command, cwd=str(args.cwd.resolve()), environment_overrides=overrides,
                   started_utc=utc(), shell=False)
    (output / 'command.json').write_text(json.dumps(receipt, indent=2) + '\n')
    with (output / 'stdout.bin').open('wb') as stdout, (output / 'stderr.bin').open('wb') as stderr:
        process = subprocess.Popen(command, cwd=args.cwd.resolve(), env={**os.environ, **overrides},
                                   stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr)
        receipt['pid'] = process.pid
        receipt['exit_code'] = process.wait()
    receipt['finished_utc'] = utc()
    for stream in ('stdout', 'stderr'):
        data = (output / (stream + '.bin')).read_bytes()
        receipt[stream] = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    (output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))
    sys.exit(receipt['exit_code'])


if __name__ == '__main__':
    main()
