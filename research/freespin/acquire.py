#!/usr/bin/env python3
"""Pin public author pages, published loader text, and exact Freespin D64.

Downloads data only. Does not launch a downloaded program or an emulator.
"""

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
OUTPUT = REPOSITORY / "build/research/freespin"
BASE = "https://www.quiss.org/freespin/"


class PreText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.active = False
        self.blocks = []
        self.current = []

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            self.active = True
            self.current = []

    def handle_endtag(self, tag):
        if tag == "pre" and self.active:
            self.blocks.append("".join(self.current))
            self.active = False

    def handle_data(self, data):
        if self.active:
            self.current.append(data)


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in ("index.html", "raster.html", "music.html", "loading.html", "loader.html", "recording.html", "freespin.d64"):
        url = BASE if name == "index.html" else BASE + name
        request = urllib.request.Request(url, headers={"User-Agent": "C64-research/1.0"})
        with urllib.request.urlopen(request, timeout=30) as response:
            data = response.read()
            final_url = response.url
        (OUTPUT / name).write_bytes(data)
        row = {"url": url, "final_url": final_url, "file": name, "bytes": len(data),
               "sha256": hashlib.sha256(data).hexdigest()}
        if name.endswith(".html"):
            parser = PreText()
            parser.feed(data.decode("utf-8"))
            for index, block in enumerate(parser.blocks):
                target = "loader-published.asm" if name == "loader.html" and index == 0 else name.removesuffix(".html") + f"-pre{index}.txt"
                (OUTPUT / target).write_text(block)
            row["pre_blocks"] = len(parser.blocks)
        rows.append(row)
    disk = (OUTPUT / "freespin.d64").read_bytes()
    assert len(disk) == 174848
    assert hashlib.sha256(disk).hexdigest() == "7798f74046ee767a2e05e4e05c12e7b7453640c579ebc3d5daed20ce019f890c"
    receipt = {"retrieved_utc": datetime.now(timezone.utc).isoformat(), "scope": "Author-published source/page snapshots and D64; no full effect Git repository claimed", "downloads": rows}
    (OUTPUT / "downloads.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
