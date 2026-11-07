#!/usr/bin/env python3
"""Check retained primary sources and finite-bob asset algebra; no CPU/native run.

--fetch-missing can reacquire missing response bodies using the retained,
hash-pinned acquisition indexes. Changed remote bytes fail the original pins.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib.request import Request, urlopen

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/research/frontier-2026/primary-notes"
COMMIT = "965807c511e2025b5c5e1ffb2a6235a4efd6ae5b"
TREE = "2a9bc04218fb7c60d744e8eb1b86ca4cda044eca"
INDEX_PINS = {
    "initial-acquisition.json": "b3efb5f22b42c95f44e65a40bf807c316d70e2ec2b674c651c53419ff35bfa37",
    "caption-acquisition.json": "a8a1d1a598bb13df7d994c11d3c3a83abce4facfdf11abc87c5839dde6c64863",
    "finite-bobs-acquisition.json": "901c34565371b095a37acc98e17b2789021c5c1d3664ed0cfd879f3df522e501",
    "finite-extra-acquisition.json": "993111523edf7d81bc16c372caf378177aac904efe72aa3009e7a1de8c29a2cb",
}
REUSED_PINS = {
    "build/research/sprite-interleave/tree.json": "8aaa841e2757475affb5dcddff1cd42892a695ab3574ea8284d0d2539a5191ce",
    "build/research/sprite-interleave/commit.json": "392f3b3bbda603e5efb665f9896eceb04d31f1dae578c7f35666b141f017dff9",
}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def artifact(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}


class Article(HTMLParser):
    def __init__(self):
        super().__init__()
        self.pre = False
        self.blocks = []
        self.current = []

    def handle_starttag(self, tag, attrs):
        if tag == "pre":
            self.pre = True
            self.current = []

    def handle_endtag(self, tag):
        if tag == "pre":
            self.blocks.append("".join(self.current))
            self.pre = False

    def handle_data(self, data):
        if self.pre:
            self.current.append(data)


def sources(fetch_missing: bool) -> dict:
    responses = {}
    indexes = []
    for name, expected in INDEX_PINS.items():
        path = OUT / name
        assert sha(path.read_bytes()) == expected, name
        indexes.append(artifact(path))
        for key, row in json.loads(path.read_text()).items():
            if "error" in row:
                responses[key] = row
                continue
            dest = ROOT / row["path"]
            if not dest.exists() and fetch_missing:
                with urlopen(Request(row["url"], headers={"User-Agent": "Mozilla/5.0 C64Research/1.0"}), timeout=35) as response:
                    data = response.read()
                assert sha(data) == row["sha256"], key + ": remote response changed"
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
            assert artifact(dest)["sha256"] == row["sha256"], key
            assert dest.stat().st_size == row["bytes"], key
            responses[key] = row
    deps = []
    for name, expected in REUSED_PINS.items():
        path = ROOT / name
        assert sha(path.read_bytes()) == expected, name
        deps.append(artifact(path))
    tree = json.loads((ROOT / next(iter(REUSED_PINS))).read_text())
    commit = json.loads((ROOT / "build/research/sprite-interleave/commit.json").read_text())
    assert tree["sha"] == TREE and not tree["truncated"]
    assert commit["sha"] == COMMIT and commit["commit"]["tree"]["sha"] == TREE
    entries = {entry["path"]: entry for entry in tree["tree"]}
    blobs = []
    for key, row in responses.items():
        if not key.startswith("NoBounds/"):
            continue
        data = (ROOT / row["path"]).read_bytes()
        git_sha = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        assert entries[key]["sha"] == git_sha and entries[key]["size"] == len(data), key
        blobs.append({"repository_path": key, "git_blob": git_sha, **artifact(ROOT / row["path"])})
    return {"indexes": indexes, "responses": responses, "reused_inputs": deps, "commit": COMMIT, "tree": TREE, "git_blobs": blobs}


def primary_text() -> dict:
    body = (OUT / "rodents-youtube.body").read_text()
    start = body.index("ytInitialPlayerResponse =") + len("ytInitialPlayerResponse =")
    player, _ = json.JSONDecoder().raw_decode(body[start:].lstrip())
    details = player["videoDetails"]
    assert details["videoId"] == "uZ1atMUOUMU" and details["author"] == "lftkryo"
    tracks = player["captions"]["playerCaptionsTracklistRenderer"]["captionTracks"]
    assert len(tracks) == 1 and tracks[0]["languageCode"] == "en" and tracks[0]["kind"] == "asr"
    names = ["rodents-caption-en", "rodents-caption-asr", "rodents-caption-signed", "rodents-caption-json", "rodents-caption-no-variant"]
    assert all((OUT / (name + ".body")).read_bytes() == b"" for name in names)
    parser = Article()
    parser.feed((OUT / "finite-bobs-article-canonical.body").read_text())
    function = "void InfiniteBobs_ConvertBobToASM"
    code = (OUT / "source/NoBounds/Parts/InfiniteBobs/InfiniteBobs.cpp").read_text()
    start = code.index(function)
    end = code.index("\n}", start) + 2
    matching = [block for block in parser.blocks if function in block]
    assert len(matching) == 1
    assert re.sub(r"\s+", "", matching[0]) == re.sub(r"\s+", "", code[start:end])
    return {"rodents_video": details["title"], "advertised_track": {key: tracks[0][key] for key in ["languageCode", "kind", "vssId"]}, "caption_empty_routes": names, "transcript_recovered": False, "article_generator_matches_repository_ignoring_whitespace": True}


def finite_bobs() -> dict:
    base = OUT / "source/NoBounds"
    background = Image.open(base / "Parts/InfiniteBobs/Data/pic512x448.png").convert("RGB")
    bob = Image.open(base / "Parts/InfiniteBobs/Data/bob.png").convert("RGB")
    assert background.size == (512, 448) and bob.size == (18, 15)
    bg = background.load()
    bp = bob.load()
    bg_palette = {(62, 49, 162): 0, (124, 112, 218): 1, (0, 0, 0): 3}
    bob_palette = {(255, 255, 255): 2, (128, 128, 128): 1, (0, 0, 0): 3}
    transparent = (255, 0, 234)
    assert {bg[x, y] for y in range(448) for x in range(512)} == set(bg_palette)
    assert {bp[x, y] for y in range(15) for x in range(18)} == set(bob_palette) | {transparent}
    assert all(bg[x, y] == bg[511 - x, y] for y in range(448) for x in range(256))
    assert all(bg[x, y] == bg[x + 1, y] for y in range(448) for x in range(0, 512, 2))
    assert all(bp[x, y] == bp[x + 1, y] for y in range(15) for x in range(0, 18, 2))

    # File-format implementation, independently checked below against the full image.
    packed = bytearray()
    for row in range(56):
        for column in range(32):
            for py in range(8):
                packed.append(sum(bg_palette[bg[column * 8 + px, row * 8 + py]] << (6 - px) for px in [0, 2, 4, 6]))
    supplied = (base / "Link/InfiniteBobs/ImageData.bin").read_bytes()
    assert packed == supplied
    restored = bytearray(28672)
    wrong_bit_reverse = bytearray(28672)
    for row in range(56):
        row_base = (row // 4) * 2048 + (row % 4) * 512
        for offset in range(256):
            value = supplied[row * 256 + offset]
            reverse_pairs = sum(((value >> (pair * 2)) & 3) << (6 - pair * 2) for pair in range(4))
            restored[row_base + offset] = value
            restored[row_base + 256 + (offset ^ 0xF8)] = reverse_pairs
            wrong_bit_reverse[row_base + offset] = value
            wrong_bit_reverse[row_base + 256 + (offset ^ 0xF8)] = int(f"{value:08b}"[::-1], 2)
    reference = bytearray(28672)
    for y in range(448):
        for x in range(0, 512, 8):
            address = (y // 32) * 2048 + ((y % 32) // 8) * 512 + (x // 8) * 8 + (y % 8)
            reference[address] = sum(bg_palette[bg[x + px, y]] << (6 - px) for px in [0, 2, 4, 6])
    assert restored == reference
    reverse_errors = sum(a != b for a, b in zip(wrong_bit_reverse, reference))
    assert reverse_errors > 0

    # Literal source mask/data construction versus a per-pixel ownership oracle.
    comparisons = 0
    wrong_or = 0
    shapes = Counter()
    for shift in [0, 2, 4, 6]:
        for column in range(3):
            for y in range(15):
                mask = data = 0
                for px in [0, 2, 4, 6]:
                    sx = column * 8 + px - shift
                    if sx < 0 or sx >= 18 or bp[sx, y] == transparent:
                        mask |= 3 << (6 - px)
                    else:
                        data |= bob_palette[bp[sx, y]] << (6 - px)
                shapes["transparent" if mask == 255 else "opaque" if mask == 0 else "masked"] += 1
                for old in range(256):
                    actual = (old & mask) | data
                    expected = 0
                    for lane in range(4):
                        sx = column * 8 + lane * 2 - shift
                        value = (old >> (6 - 2 * lane)) & 3
                        if 0 <= sx < 18 and bp[sx, y] != transparent:
                            value = bob_palette[bp[sx, y]]
                        expected = expected * 4 + value
                    assert actual == expected
                    wrong_or += (old | data) != expected
                    comparisons += 1
    assert wrong_or > 0
    return {"background_dimensions": list(background.size), "bob_dimensions": list(bob.size), "half_image_bytes_exact": len(packed), "full_charset_bytes_exact": len(restored), "full_charset_sha256": sha(restored), "mirrored_source_image": True, "bob_sites": dict(shapes), "mask_pixel_comparisons": comparisons, "negative_controls": {"reverse_all_bits_instead_of_pairs_wrong_bytes": reverse_errors, "OR_without_coverage_mask_wrong_cases": wrong_or}, "scope": "Host asset/format algebra only; no C++ execution, assembly, CPU, raster or native acceptance."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fetch-missing", action="store_true")
    args = parser.parse_args()
    report = {"pass": True, "script": artifact(Path(__file__).resolve()), "sources": sources(args.fetch_missing), "primary_text": primary_text(), "finite_bobs": finite_bobs()}
    dest = OUT / "primary-notes-proof.json"
    dest.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({"pass": report["pass"], "receipt": str(dest.relative_to(ROOT)), "git_blobs": len(report["sources"]["git_blobs"]), "finite_bobs": report["finite_bobs"]}, indent=2))


if __name__ == "__main__":
    main()
