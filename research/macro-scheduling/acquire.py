#!/usr/bin/env python3
"""Archive Trident's pinned scheduling example and original talk slides.

The PPTX is inspected as an unchanged ZIP/XML source. Extracted text is a
research aid, not a rendered-slide or spoken-video transcript.
"""

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/research/macro-scheduling"
COMMIT = "80d1027742815e55cda13a80cb4826744dd75c83"
FILES = ("anonymous-irq-handlers-example.s", "trident - fjälldata 2025 slides.pptx")


def sha(data):
    return hashlib.sha256(data).hexdigest()


def fetch(url, limit):
    request = urllib.request.Request(url, headers={"User-Agent": "C64 source research"})
    with urllib.request.urlopen(request, timeout=30) as response:
        data = response.read(limit + 1)
        assert len(data) <= limit, "Download exceeds the explicit archive bound"
        return data, dict(requested_url=url, final_url=response.geturl(),
                          http_status=response.status,
                          fetched_utc=datetime.now(timezone.utc).isoformat())


def extract_slides(path):
    ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main",
          "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
          "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships"}
    records = []
    with zipfile.ZipFile(path) as archive:
        rels = ET.fromstring(archive.read("ppt/_rels/presentation.xml.rels"))
        targets = {item.attrib["Id"]: item.attrib["Target"] for item in rels}
        presentation = ET.fromstring(archive.read("ppt/presentation.xml"))
        for number, item in enumerate(presentation.findall("p:sldIdLst/p:sldId", ns), 1):
            target = targets[item.attrib[f"{{{ns['r']}}}id"]]
            member = "ppt/" + target
            slide = ET.fromstring(archive.read(member))
            paragraphs = ["".join(t.text or "" for t in paragraph.findall(".//a:t", ns))
                          for paragraph in slide.findall(".//a:p", ns)]
            records.append(dict(number=number, member=member, paragraphs=paragraphs,
                                embedded_picture_count=len(slide.findall(".//p:pic", ns)),
                                xml_sha256=sha(archive.read(member))))
    (OUT / "slides-text.json").write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n")
    (OUT / "slides-text.txt").write_text("\n\n".join(
        f"SLIDE {record['number']}\n" + "\n".join(record["paragraphs"])
        for record in records) + "\n")
    return records


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw_tree, tree_meta = fetch(f"https://api.github.com/repos/trident64/c64/git/trees/{COMMIT}?recursive=1", 1_000_000)
    (OUT / "git-tree.json").write_bytes(raw_tree)
    tree = json.loads(raw_tree)
    assert not tree["truncated"]
    entries = {item["path"]: item for item in tree["tree"]}
    records = []
    for name in FILES:
        expected = entries[name]
        assert expected["type"] == "blob"
        url = f"https://raw.githubusercontent.com/trident64/c64/{COMMIT}/" + urllib.parse.quote(name)
        data, record = fetch(url, 20_000_000)
        blob = hashlib.sha1(f"blob {len(data)}\0".encode() + data).hexdigest()
        assert blob == expected["sha"] and len(data) == expected["size"]
        (OUT / name).write_bytes(data)
        record.update(path=str((OUT / name).relative_to(ROOT)), bytes=len(data),
                      sha256=sha(data), git_blob_sha1=blob)
        records.append(record)
    slides = extract_slides(OUT / FILES[1])
    receipt = dict(pass_=True, commit=COMMIT, tree_request=tree_meta,
                   tree_sha256=sha(raw_tree), files=records, slides=len(slides),
                   script_sha256=sha(Path(__file__).read_bytes()),
                   scope="Unchanged primary source and ordered XML text; no source execution, slide rendering or spoken transcript")
    receipt["pass"] = receipt.pop("pass_")
    (OUT / "acquisition.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(dict(pass_=True, slides=len(slides), files=records), indent=2))


if __name__ == "__main__":
    main()
