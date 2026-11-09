#!/usr/bin/env python3
"""Retain primary reading and an author-linked C64 data file; never execute it."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-pixels-20261109/reading-analysis'
URLS = {
    'bauer': 'https://www.cebix.net/VIC-Article.txt',
    'perpetual': 'https://linusakesson.net/scene/perpetual-fragility/index.php',
    'perpetual-prg': 'https://hd0.linusakesson.net/files/lft-perpetual-fragility.prg',
}


def request(item):
    name, url = item
    row = dict(name=name, url=url, started_utc=datetime.now(timezone.utc).isoformat(),
               certificate_verification_disabled=False)
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'C64-rendering-research/1.0'})
        with urllib.request.urlopen(req, timeout=20) as response:
            body = response.read()
            row.update(status=response.status, final_url=response.url,
                       headers=dict(response.headers.items()))
    except urllib.error.HTTPError as error:
        body = error.read()
        row.update(status=error.code, final_url=error.url, headers=dict(error.headers.items()))
    except Exception as error:
        body = None
        row.update(status=None, exception_type=type(error).__name__, exception=str(error))
    row['ended_utc'] = datetime.now(timezone.utc).isoformat()
    return row, body


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to(BASE)
    assert not out.exists()
    out.mkdir(parents=True)
    (out / 'primary_acquire.checked.py').write_bytes(Path(__file__).read_bytes())
    rows = []
    with ThreadPoolExecutor(max_workers=3) as executor:
        for row, body in executor.map(request, URLS.items()):
            if body is not None:
                path = out / (row['name'] + ('.prg' if row['name'].endswith('-prg') else '.body'))
                path.write_bytes(body)
                row['body'] = dict(path=str(path.relative_to(ROOT)), bytes=len(body),
                                   sha256=hashlib.sha256(body).hexdigest())
            rows.append(row)
    result = dict(scope='Raw primary HTTP acquisition; no downloaded code execution.',
                  requests=rows, no_certificate_bypass=True)
    (out / 'http-retention.json').write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps([{k: row.get(k) for k in ('name', 'status', 'body', 'exception')} for row in rows]))


if __name__ == '__main__':
    main()
