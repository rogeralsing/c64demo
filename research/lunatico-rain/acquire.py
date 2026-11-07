#!/usr/bin/env python3
"""Archive the primary rain/release pages and pin the previously fetched ZIP."""

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/research/lunatico-rain"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    files = []
    for name, url in (("author-rain.html", "https://www.linusakesson.net/scene/lunatico/rain.php"),
                      ("author-release.html", "https://www.linusakesson.net/scene/lunatico/index.php")):
        requested = datetime.now(timezone.utc).isoformat()
        with urllib.request.urlopen(url, timeout=30) as response:
            raw = response.read(1_000_001)
            assert len(raw) <= 1_000_000
            entry = {"url": url, "final_url": response.geturl(), "status": response.status,
                     "retrieved_utc": requested, "content_type": response.headers.get("Content-Type")}
        target = OUTPUT / name
        target.write_bytes(raw)
        entry.update({"path": str(target.relative_to(ROOT)), "bytes": len(raw), "sha256": digest(raw)})
        files.append(entry)
    prior = ROOT / "build/research/frontier-followup/prior-transcript-status.json"
    prior_entries = json.loads(prior.read_text())
    caption = next(row for row in prior_entries if row["video_id"] == "F2TkzDaa8A4")
    # The prior signed URL is ephemeral; the source file keeps its full record.
    prior_summary = {key: caption[key] for key in ("video_id", "tracks", "bytes", "sha256", "status")}
    archive = ROOT / "build/research/frontier-followup/lunatico.zip"
    assert archive.stat().st_size == 272533
    assert digest(archive.read_bytes()) == "1e22a02eeef77d98a8c348b03cbb808b489b3cf842d14db25dbf72f79eb9e6c0"
    result = {"pass": True, "script_sha256": digest(Path(__file__).read_bytes()), "files": files,
              "reused_zip": {"path": str(archive.relative_to(ROOT)), "bytes": archive.stat().st_size,
                             "sha256": digest(archive.read_bytes()), "original_url": "https://hd0.linusakesson.net/files/lft-lunatico.zip"},
              "prior_caption_attempt": {"source_path": str(prior.relative_to(ROOT)), "source_sha256": digest(prior.read_bytes()),
                                        "summary": prior_summary},
              "scope": "Public author HTML and identity of reused original ZIP; no remote video or audio downloaded"}
    (OUTPUT / "acquisition.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
