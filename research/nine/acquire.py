#!/usr/bin/env python3
"""Archive Nine's author pages and PRG; inspect only the static file header.

Standard library only. No downloaded code, CPU routine, emulator, assembler or
production renderer is executed. Raw author files remain ignored artifacts.
"""

import hashlib
import json
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/research/nine"
SOURCES = [
    ("author-release.html", "https://www.linusakesson.net/scene/nine/"),
    ("author-explanation.html", "https://www.linusakesson.net/scene/nine/explanation.php"),
    ("lft-nine.prg", "https://hd0.linusakesson.net/files/lft-nine.prg"),
]


def digest(data):
    return hashlib.sha256(data).hexdigest()


def basic_header(blob):
    assert len(blob) >= 2
    load = int.from_bytes(blob[:2], "little")
    payload = blob[2:]
    result = {"load_address": load, "file_bytes": len(blob),
              "payload_bytes": len(payload),
              "loaded_end_exclusive": load + len(payload),
              "first_payload_bytes_hex": payload[:32].hex(" ")}
    if load != 0x0801 or len(payload) < 5:
        result["basic_stub"] = {"scope": "Not a conventional0801 BASIC header; no further interpretation"}
        return result
    end = payload.find(b"\0", 4, min(len(payload), 260))
    assert end >= 0, "First BASIC line is not terminated within bounded header"
    body = payload[4:end]
    sys_match = re.search(rb"\x9e\s*([0-9]+)", body)
    result["basic_stub"] = {
        "next_line_pointer": int.from_bytes(payload[:2], "little"),
        "line_number": int.from_bytes(payload[2:4], "little"),
        "body_hex": body.hex(" "),
        "body_display": "".join("SYS" if value == 0x9E else chr(value)
                                if 32 <= value <= 126 else f"<{value:02X}>" for value in body),
        "line_terminator_address": load + end,
        "literal_following_bytes_hex": payload[end + 1:end + 5].hex(" "),
        "literal_SYS_decimal": int(sys_match.group(1)) if sys_match else None,
        "scope": "First tokenized line only; no BASIC/ROM execution or validation of control flow",
    }
    return result


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    files = []
    prg = None
    for name, url in SOURCES:
        requested_at = datetime.now(timezone.utc).isoformat()
        request = urllib.request.Request(url, headers={"User-Agent": "C64 research archive (static retrieval)"})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
            metadata = {"requested_url": url, "final_url": response.geturl(),
                        "retrieved_utc": requested_at, "http_status": response.status,
                        "response_headers": {key: response.headers[key]
                                             for key in ("Content-Type", "Content-Length", "ETag", "Last-Modified")
                                             if key in response.headers}}
        path = OUTPUT / name
        path.write_bytes(data)
        metadata.update({"path": str(path.relative_to(ROOT)), "bytes": len(data),
                         "sha256": digest(data)})
        files.append(metadata)
        if name.endswith(".prg"):
            prg = data
    assert prg is not None
    result = {"pass": True, "script_sha256": digest(Path(__file__).read_bytes()),
              "files": files, "prg_header": basic_header(prg),
              "scope": "Acquisition and bounded static byte-header inspection only; no CPU/VICE/disassembly or downloaded-code execution"}
    (OUTPUT / "acquisition.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
