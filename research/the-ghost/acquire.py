#!/usr/bin/env python3
"""Archive original CSDb routes, including failed HTTP responses; no execution."""

import hashlib
import json
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/research/the-ghost"
SOURCES = [
    ("release.html", "https://csdb.dk/release/?id=239394"),
    ("author-notes.html", "https://csdb.dk/release/?id=239394&show=notes"),
    ("the_ghost-flt_and_gp.zip", "https://csdb.dk/getinternalfile.php/253352/the_ghost-flt_and_gp.zip"),
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def retrieve(name, url):
    metadata = {"requested_url": url, "retrieved_utc": datetime.now(timezone.utc).isoformat()}
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 C64 static research archive"})
    try:
        response = urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    except urllib.error.URLError as error:
        metadata.update({"success": False, "error": str(error)})
        return metadata
    with response:
        raw = response.read(8_000_001)
        assert len(raw) <= 8_000_000
        metadata.update({"final_url": response.geturl(), "status": response.status,
                         "success": 200 <= response.status < 300,
                         "response_headers": {key: response.headers[key] for key in
                                              ("Content-Type", "Content-Length", "ETag", "Last-Modified")
                                              if key in response.headers}})
    target = OUTPUT / (name if metadata["success"] else name + ".http-error")
    target.write_bytes(raw)
    metadata.update({"bytes": len(raw), "sha256": digest(raw), "path": str(target.relative_to(ROOT))})
    return metadata


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    files = [retrieve(name, url) for name, url in SOURCES]
    archive = OUTPUT / "the_ghost-flt_and_gp.zip"
    members = []
    if files[-1].get("success") and zipfile.is_zipfile(archive):
        with zipfile.ZipFile(archive) as zipped:
            assert sum(info.file_size for info in zipped.infolist()) < 8_000_000
            output = OUTPUT / "extracted"
            output.mkdir(exist_ok=True)
            for info in zipped.infolist():
                if info.is_dir():
                    continue
                name = Path(info.filename).name
                assert name
                raw = zipped.read(info)
                target = output / name
                assert not target.exists() or target.read_bytes() == raw, name
                target.write_bytes(raw)
                members.append({"archive_name": info.filename, "path": str(target.relative_to(ROOT)),
                                "bytes": len(raw), "sha256": digest(raw)})
    receipt = {"script_sha256": digest(Path(__file__).read_bytes()), "files": files,
               "zip_members": members, "archive_is_zip": archive.exists() and zipfile.is_zipfile(archive),
               "scope": "Original CSDb release route acquisition only; no program or loader executed"}
    (OUTPUT / "acquisition.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
