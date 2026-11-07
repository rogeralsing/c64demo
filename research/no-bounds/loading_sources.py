#!/usr/bin/env python3
"""Archive the No Bounds loading article and its pinned original source files.

Only public source bytes are acquired and checked. No downloaded code,
assembler, CPU, loader, emulator or process-control action is run.
"""

import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "build/research/no-bounds"
COMMIT = "965807c511e2025b5c5e1ffb2a6235a4efd6ae5b"
TREE = "2a9bc04218fb7c60d744e8eb1b86ca4cda044eca"
ARTICLE = "https://c64demo.com/seamless-loading-nobounds/"
FILES = (
    "NoBounds/Main/Main-CommonMacros.asm",
    "NoBounds/Main/Main-BaseCode.asm",
    "NoBounds/Main/Main-CommonDefines.asm",
    "NoBounds/Main/Main-CommonMemory.asm",
    "NoBounds/Main/Sparkle/NoBoundsA.sls",
    "NoBounds/Parts/NoBounds/DISK-NoBounds.asm",
    "NoBounds/Parts/NoBounds/NoBounds.asm",
    "NoBounds/Parts/NoBounds/NoBounds.cpp",
    "NoBounds/Parts/NoBounds/FadeFromNoBounds.asm",
    "NoBounds/Link/NoBounds/StreamData.sls",
    "NoBounds/Parts/RotatingGP/DISK-RotatingGP.asm",
    "NoBounds/Parts/RotatingGP/FadeToNoBounds.asm",
    "NoBounds/Parts/PlasmaVector/DISK-PlasmaVector.asm",
)


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}


def fetch(pair):
    name, url = pair
    with urllib.request.urlopen(url, timeout=20) as response:
        body = response.read(2_000_001)
        assert len(body) <= 2_000_000
        path = BASE / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_bytes() != body:
            prior = path.with_name(path.name + ".previous-" + sha(path.read_bytes())[:16])
            if not prior.exists():
                prior.write_bytes(path.read_bytes())
        path.write_bytes(body)
        return {"url": url, "final_url": response.url,
                "utc": datetime.now(timezone.utc).isoformat(), "artifact": record(path)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--fetch-new", action="store_true", help="Keep acquired bodies and fetch newly listed routes only.")
    args = parser.parse_args()
    BASE.mkdir(parents=True, exist_ok=True)
    tree_path = ROOT / "build/research/sprite-interleave/tree.json"
    tree = json.loads(tree_path.read_text())
    assert tree["sha"] == TREE and not tree["truncated"]
    entries = {item["path"]: item for item in tree["tree"]}
    routes = [("article.html", ARTICLE)] + [
        (path, f"https://raw.githubusercontent.com/RobertTroughton/C64Demo-PublicReleases/{COMMIT}/{path}")
        for path in FILES]
    ledger = BASE / "loading-acquisitions.json"
    if args.fetch or args.fetch_new:
        existing = {item["url"]: item for item in json.loads(ledger.read_text())} if ledger.exists() else {}
        pending = [pair for pair in routes if args.fetch or pair[1] not in existing]
        with ThreadPoolExecutor(max_workers=4) as pool:
            existing.update({item["url"]: item for item in pool.map(fetch, pending)})
        acquisitions = [existing[url] for _, url in routes]
        ledger.write_text(json.dumps(acquisitions, indent=2) + "\n")
    else:
        acquisitions = json.loads(ledger.read_text())
    assert [item["url"] for item in acquisitions] == [url for _, url in routes]
    for item in acquisitions:
        path = ROOT / item["artifact"]["path"]
        assert record(path) == item["artifact"]
    sources = []
    for path in FILES:
        body = (BASE / path).read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(body)).encode() + b"\0" + body).hexdigest()
        assert entries[path]["type"] == "blob"
        assert len(body) == entries[path]["size"] and blob == entries[path]["sha"]
        sources.append({"repository_path": path, "git_blob": blob, "artifact": record(BASE / path)})
    proof = {"pass": True, "scope": "Original article and pinned source identity only; no build, disk payload, native timing or hardware proof.",
             "commit": COMMIT, "tree": record(tree_path), "article": record(BASE / "article.html"),
             "script": record(Path(__file__).resolve()), "acquisitions": record(ledger), "sources": sources}
    output = BASE / "loading-source-proof.json"
    output.write_text(json.dumps(proof, indent=2) + "\n")
    print(json.dumps({"pass": True, "source_files": len(sources), "proof": record(output)}, indent=2))


if __name__ == "__main__":
    main()
