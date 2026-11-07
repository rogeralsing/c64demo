#!/usr/bin/env python3
"""Pin the current original Colors CSDb archive; inspect members only.

No C64 code, emulator, depacker or downloaded host program is executed. Raw
pages, archive and members stay below the repository's ignored build directory.
"""

import hashlib
import json
import re
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from html import unescape
from pathlib import Path, PurePosixPath


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/research/colors"
SOURCES = [
    ("release.html", "https://csdb.dk/release/?id=262141"),
    ("production-notes.html", "https://csdb.dk/release/?id=262141&show=notes"),
    ("Colors [Lethargy].zip", "https://csdb.dk/getinternalfile.php/280610/Colors%20%5BLethargy%5D.zip"),
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fetch(name, url):
    requested = datetime.now(timezone.utc).isoformat()
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 C64 original-release research"})
    try:
        response = urllib.request.urlopen(request, timeout=30)
    except urllib.error.HTTPError as error:
        response = error
    with response:
        data = response.read(16_000_001)
        assert len(data) <= 16_000_000
        receipt = {"requested_url": url, "final_url": response.geturl(), "requested_utc": requested,
                   "http_status": response.status, "response_headers": {
                       key: response.headers[key] for key in ("Content-Type", "Content-Length", "ETag", "Last-Modified")
                       if key in response.headers}}
    success = 200 <= receipt["http_status"] < 300
    path = OUTPUT / (name if success else name + ".http-error")
    if name.endswith(".zip") and success and path.exists():
        assert path.read_bytes() == data, "Current upstream archive changed; preserve prior pinned bytes and inspect version separately"
    path.write_bytes(data)
    receipt.update({"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": digest(data), "success": success})
    return receipt


def d64_geometry(size):
    if size in (174848, 175531):
        return {"tracks": 35, "sectors": 683, "sector_data_bytes": 174848,
                "error_info_bytes": size - 174848}
    if size in (196608, 197376):
        return {"tracks": 40, "sectors": 768, "sector_data_bytes": 196608,
                "error_info_bytes": size - 196608}
    return {"recognized_geometry": False, "file_bytes": size}


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    acquisitions = [fetch(name, url) for name, url in SOURCES]
    archive = OUTPUT / SOURCES[-1][0]
    members = []
    assert acquisitions[-1]["success"] and zipfile.is_zipfile(archive)
    extracted = OUTPUT / "extracted"
    extracted.mkdir(exist_ok=True)
    with zipfile.ZipFile(archive) as zipped:
        assert len(zipped.infolist()) <= 200
        assert sum(info.file_size for info in zipped.infolist()) <= 32_000_000
        paths = set()
        for info in zipped.infolist():
            member = PurePosixPath(info.filename)
            assert not member.is_absolute() and ".." not in member.parts and "\\" not in info.filename
            assert info.filename not in paths
            paths.add(info.filename)
            if info.is_dir():
                continue
            raw = zipped.read(info)
            target = extracted.joinpath(*member.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            assert not target.exists() or target.read_bytes() == raw
            target.write_bytes(raw)
            row = {"archive_name": info.filename, "path": str(target.relative_to(ROOT)),
                   "bytes": len(raw), "sha256": digest(raw), "zip_crc32": f"{info.CRC:08x}"}
            if member.suffix.lower() == ".d64":
                row["d64_geometry"] = d64_geometry(len(raw))
            if member.suffix.lower() in (".txt", ".nfo", ".md", ".asm", ".s", ".c", ".h") or member.name.lower().startswith(("readme", "license", "copying")):
                row["possible_document_or_source"] = True
            members.append(row)
    release_text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", (OUTPUT / "release.html").read_text())))
    notes_text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", (OUTPUT / "production-notes.html").read_text())))
    fix = re.search(r"User Comment Submitted by Vincenzo on 7 June 2026 (.*?)(?=User Comment Submitted by |Search CSDb)", release_text)
    result = {"pass": True, "script_sha256": digest(Path(__file__).read_bytes()),
              "release_id": 262141, "original_download_file_id": 280610,
              "acquisitions": acquisitions, "members": members,
              "source_material": {
                  "included_document_or_source_members": [row["archive_name"] for row in members if row.get("possible_document_or_source")],
                  "retrieved_notes_route_has_production_info_heading": "Production Info" in notes_text,
                  "fix_notice": {"found": fix is not None, "page": "build/research/colors/release.html",
                                 "submitter": "Vincenzo", "date": "7 June 2026",
                                 "text": fix.group(1).strip() if fix else None,
                                 "scope": "Member comment about a reupload; neither historical ZIP bytes nor the exact side-order correction are independently compared here"}},
              "version_scope": "Actual current CSDb original route retrieved now; no equality to older mirrors or initial party pack is assumed",
              "scope": "Acquisition, ZIP member integrity and D64 geometry/identity only; no C64/CPU/drive/depacker/emulator execution or display/timing assertion"}
    (OUTPUT / "acquisition.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
