#!/usr/bin/env python3
"""Archive pinned Trident examples; no downloaded program is executed.

The raw article, illustrations and source stay under ignored build/. Git blob
hashes are checked independently of HTTP headers before assembly is allowed.
"""

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/research/ghostbyte"
COMMIT = "80d1027742815e55cda13a80cb4826744dd75c83"
BASE = f"https://raw.githubusercontent.com/trident64/c64/{COMMIT}/unexpanded-border-scroll/"
FILES = {
    "README.md": "f15da29a1626a7cb1e22a1839485abcc7ee031dc",
    "ghostbyte.s": "007be2c41e616d3a446f30d4c7d89a583b418aac",
    "sprite.s": "2c21779d52eae151d8c09f8689d6a2e604b25e04",
    "abcd-gimp.png": "9b8ce28b3f766c4f0252c28ab40c066cea100d32",
    "multicolor-ghostbytes.png": "08cf7b8e3d4d9d1f23e0328d010b9cfe2a92816d",
    "multicolor-expanded-a.png": "12cdf9a88b26f1d707291a3d52c3b7243bc792e2",
    "multicolor-masked-a.png": "9bf03afbe95106a052445b8734bde02daf3ab39b",
}


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    files = []
    for name, expected in FILES.items():
        requested_utc = datetime.now(timezone.utc).isoformat()
        request = urllib.request.Request(BASE + name, headers={"User-Agent": "C64 static source research"})
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read(2_000_001)
            assert len(raw) <= 2_000_000
            metadata = {"requested_url": BASE + name, "final_url": response.geturl(),
                        "requested_utc": requested_utc, "http_status": response.status,
                        "response_headers": {key: response.headers[key] for key in
                                             ("Content-Type", "Content-Length", "ETag", "Last-Modified")
                                             if key in response.headers}}
        actual = hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()
        assert actual == expected, (name, expected, actual)
        (OUTPUT / name).write_bytes(raw)
        metadata.update({"path": str((OUTPUT / name).relative_to(ROOT)), "bytes": len(raw),
                         "sha256": digest(raw), "git_blob_sha1": actual})
        files.append(metadata)
    receipt = {"pass": True, "repository": "https://github.com/trident64/c64",
               "commit": COMMIT, "script_sha256": digest(Path(__file__).read_bytes()),
               "files": files, "scope": "Pinned article, two teaching sources and selected illustrations; no Orbit Untold/The Ghost/Nine binary is acquired or identified by this receipt"}
    (OUTPUT / "acquisition.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({"pass": True, "commit": COMMIT,
                      "files": [{k: item[k] for k in ("path", "bytes", "sha256", "git_blob_sha1")} for item in files]}, indent=2))


if __name__ == "__main__":
    main()
