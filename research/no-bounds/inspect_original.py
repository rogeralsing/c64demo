#!/usr/bin/env python3
"""Bind original No Bounds disks to published SpriteFPP code/data offline.

Python standard library only. No downloaded host tool, C64/drive CPU, emulator,
ROM or hardware runs. The reused decoder is accepted only after exact boot and
1536-byte drive-image binding to its previously audited Sparkle data semantics.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "build/research/no-bounds/original"
OUT = ROOT / "build/research/no-bounds/original-analysis"
CACHE = ROOT / "build/research/frontier-geometry-20261108"
COMMIT = "965807c511e2025b5c5e1ffb2a6235a4efd6ae5b"
ZIP_SHA = "d847bdf0c64ff9568854096596f5d9c4167023dd9270f6cde26365896fea8b1c"
DISK_SHAS = ("f603e03f94ed4df416584419a696e1832b0710308de8faf2d0179b0a7725fe70",
             "c26dd9428f1ef2737921c2f153b63e1453d51706d886b044e4151cbdf83997f7")
SUPPLIED_SHA = "7aba9b129119ec31aa31d06e663ebaca0bf221247c71af532f3b529c4a359e1a"
DECODER_SHA = "1ce2fc8725d7f6f693931ae527de34f1abd175451ef6a66c43d14ce6cfbe87bb"
DOMAINS = (("atlas", 0x4000, 4352), ("frame_rows", 0xAB00, 5824),
           ("frame_tables", 0xC200, 224), ("pointer_kernel", 0x802A, 4389),
           ("kernel_prefix", 0x8026, 4))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path):
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}


def dependency():
    path = ROOT / "research/anomaly/inspect_boot.py"
    assert sha(path.read_bytes()) == DECODER_SHA, "Audited decoder changed"
    sys.dont_write_bytecode = True
    spec = importlib.util.spec_from_file_location("no_bounds_byte_bound_sparkle_decoder", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def acquisitions():
    result = []
    for name in ("acquisitions.json", "pinned-source-acquisitions.json"):
        path = BASE / name
        rows = json.loads(path.read_text())
        for row in rows:
            body = ROOT / row["path"] if "path" in row else BASE / row["name"]
            data = body.read_bytes()
            assert row["status"] == 200 and row["headers"]
            assert len(data) == row["bytes"] and sha(data) == row["sha256"]
            result.append({"ledger": str(path.relative_to(ROOT)), "url": row["url"],
                           "final_url": row["final_url"], **record(body)})
    page = (BASE / "release-232957.html").read_text()
    author = (BASE / "elder-no-bounds.html").read_text()
    assert "https://csdb.dk/release/?id=232957" in author
    assert "getinternalfile.php/246029/NoBounds-GP.zip" in page
    return result


def source_identity():
    tree_path = CACHE / "tree.json"
    tree = json.loads(tree_path.read_text())
    assert not tree["truncated"] and tree["sha"] == "2a9bc04218fb7c60d744e8eb1b86ca4cda044eca"
    entries = {x["path"]: x for x in tree["tree"]}
    rows = []
    for path in sorted((BASE / "pinned-source").rglob("*")):
        if path.is_file():
            name = str(path.relative_to(BASE / "pinned-source"))
            data = path.read_bytes()
            blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            assert entries[name]["size"] == len(data) and entries[name]["sha"] == blob
            rows.append({"source_path": name, "git_blob": blob, **record(path)})
    for name in ("NoBounds/Main/Sparkle/NoBoundsA.sls", "NoBounds/Link/NoBounds/StreamData.sls"):
        path = ROOT / "build/research/no-bounds" / name
        data = path.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        assert blob == entries[name]["sha"] and len(data) == entries[name]["size"]
        rows.append({"source_path": name, "git_blob": blob, **record(path)})
    return {"commit": COMMIT, "tree": record(tree_path), "files": rows}


def manifest_groups(path):
    groups, current = [], []
    for raw in path.read_text().splitlines() + [""]:
        line = raw.split("#", 1)[0].strip()
        if not line:
            if not raw.strip() and current:
                groups.append(current)
                current = []
            continue
        match = re.match(r"(File|Mem|Script):\s*(.*)", line, re.I)
        if not match:
            continue
        if match[1].lower() == "script":
            assert not current
            assert match[2].replace("\\", "/") == "../../Link/NoBounds/StreamData.sls"
            groups.extend(manifest_groups(ROOT / "build/research/no-bounds/NoBounds/Link/NoBounds/StreamData.sls"))
        else:
            current.append({"kind": match[1], "fields": match[2].split()})
    return groups


def bind_drive(module, disk):
    path = module.SOURCE / "Resources/SD.prg"
    blob = path.read_bytes()
    assert int.from_bytes(blob[:2], "little") == 0x2300 and len(blob) == 1337
    canonical = bytearray(1536)
    canonical[:len(blob) - 2] = blob[2:]
    transformed = bytes(module.transform(canonical[768 + (-i & 255)]) for i in range(256))
    canonical[768:1024], canonical[1024:1280], canonical[1280:1536] = canonical[1024:1280], canonical[1280:1536], transformed
    original = b"".join(module.sector(disk, 18, s) for s in range(11, 17))
    before = [{"offset": i, "canonical": a, "original": b} for i, (a, b) in enumerate(zip(canonical, original)) if a != b]
    bam = module.sector(disk, 18, 0)
    canonical[0x1B:0x1E] = bytes(module.transform(bam[i]) for i in (0xF8, 0xF7, 0xF6))
    canonical[0x5B:0x5E], canonical[0x5F] = bytes.fromhex("23 01 05"), 0x23
    for offset, position in ((0x360, 0xFE), (0x361, 0xFD), (0x362, 0xFC), (0x363, 0xFB), (0x364, 0xFA)):
        canonical[offset] = module.transform(bam[position])
    assert canonical == original, "Original drive variant is not byte-bound; decoder reuse forbidden"
    return {"canonical": record(path), "original_sectors": [[18, s] for s in range(11, 17)],
            "bytes": len(original), "original_sha256": sha(original), "differences_before_config": before,
            "all_bytes_equal_after_documented_config": True, "product_id": list(canonical[0x1B:0x1E]),
            "drive_version_bcd": original[0x5B:0x5E].hex(),
            "normalization": "Same byte-bound SD ChkLastBlock rule as audited decoder: transitional buffer byte1 becomes0 before C64 delivery"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    acquired, sources = acquisitions(), source_identity()
    archive = BASE / "NoBounds-GP.zip"
    assert len(archive.read_bytes()) == 312201 and sha(archive.read_bytes()) == ZIP_SHA
    disks, members = [], []
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.namelist() == ["NoBounds-GP-Side1.d64", "NoBounds-GP-Side2.d64"]
        for index, name in enumerate(zipped.namelist()):
            data = zipped.read(name)
            assert len(data) == 174848 and sha(data) == DISK_SHAS[index]
            path = BASE / "zip-members" / name
            assert path.read_bytes() == data
            source_disk = BASE / "pinned-source/NoBounds/D64" / name
            assert source_disk.read_bytes() == data
            disks.append(data)
            members.append({"name": name, **record(path), "published_repository_disk_identical": True})
    module = dependency()
    primary = module.verify_primary_sources()
    canonical_loader = (module.SOURCE / "Resources/Loader.prg").read_bytes()
    disk_reports = []
    for side, disk in enumerate(disks, 1):
        entries = module.directory(disk)
        boot, chain = module.linked(disk, 18, 7)
        assert len(boot) == 834 and sha(boot) == "40cd90f462434ea395d1c03e09d5cb6336186ab2229e4889c4d3abb48a2816ea"
        path = out / f"side{side}-boot.prg"
        path.write_bytes(boot)
        differences = [{"file_offset": i, "canonical": a, "original": b} for i, (a, b) in enumerate(zip(canonical_loader, boot)) if a != b]
        assert [d["file_offset"] for d in differences] == [261, 264]
        assert (((boot[261] << 8) | boot[264]) + 1) == 0xFF40
        drive = bind_drive(module, disk)
        bam = module.sector(disk, 18, 0)
        interleaves = [(-module.transform(bam[p])) & 255 for p in (0xFA, 0xFC, 0xFD, 0xFE)]
        order = module.physical_order(interleaves)
        internal = module.internal_directory(disk, order)
        unique = []
        for row in internal:
            if (row["block_index"], row["bit_pointer"]) not in [(x["block_index"], x["bit_pointer"]) for x in unique]:
                unique.append(row)
        for track, sector in sorted({(x["track"], x["sector"]) for x in entries if x["type"] & 7 == 2} - {(18, 7)}):
            body, _ = module.linked(disk, track, sector)
            (out / f"side{side}-secondary-chain-{track}-{sector}.prg").write_bytes(body)
        disk_reports.append({"side": side, "DOS_entries": entries, "boot": record(path), "boot_chain": chain,
                             "canonical_loader": record(module.SOURCE / "Resources/Loader.prg"),
                             "boot_differences": differences, "configured_RTS_entry": 0xFF40,
                             "drive": drive, "interleaves": interleaves, "internal_directory": internal,
                             "unique_bundles": unique,
                             "resident": {"source_file_defined_range_exclusive": [0x09A5, 0x0B41],
                                 "destination_file_defined_range_exclusive": [0x0160, 0x02FC],
                                 "copy_loop_bytes": 416, "file_defined_bytes": 412,
                                 "source_tail_outside_boot": [0x0B41, 0x0B45],
                                 "limit": "Four copied bytes outside the DOS-loaded PRG are not synthesized"}})
    groups = manifest_groups(ROOT / "build/research/no-bounds/NoBounds/Main/Sparkle/NoBoundsA.sls")
    target_groups = [(i, group) for i, group in enumerate(groups)
                     if any("SpriteFPP\\DISK-SpriteFPP.prg" in row["fields"][0] for row in group)]
    assert len(groups) == 45 and len(target_groups) == 1 and target_groups[0][0] == 31
    target_index, manifest = target_groups[0]
    assert len(disk_reports[0]["unique_bundles"]) == len(groups) + 1
    entry = disk_reports[0]["internal_directory"][target_index]
    decoder = module.Decoder(disks[0], module.physical_order(disk_reports[0]["interleaves"]),
                             {x["block_index"] for x in disk_reports[0]["unique_bundles"]})
    target = decoder.decode(entry)
    assert target["written_ranges"] == [[0x088F, 0x08C1], [0x4003, 0x5103], [0x8000, 0xA440], [0xAB00, 0xC4B3]]
    (out / "side1-bundle031.ram").write_bytes(decoder.memory)
    (out / "side1-bundle031.known").write_bytes(decoder.known)
    target["RAM"], target["known_mask"] = record(out / "side1-bundle031.ram"), record(out / "side1-bundle031.known")
    production = BASE / "pinned-source/NoBounds/Link/SpriteFPP/SpriteFPP.prg"
    prod, load = production.read_bytes(), 0x4003
    assert len(prod) == 33970 and int.from_bytes(prod[:2], "little") == load
    sections = []
    for address, offset, length in ((0x4003, 2, 0x1100), (0x8000, 0x3FFF, 0x2440), (0xAB00, 0x6AFF, len(prod) - 0x6AFF)):
        assert all(decoder.known[address:address + length])
        assert decoder.memory[address:address + length] == prod[offset:offset + length]
        sections.append({"address": address, "file_offset": offset, "bytes": length, "exact": True,
                         "sha256": sha(prod[offset:offset + length])})
    driver = BASE / "pinned-source/NoBounds/Link/SpriteFPP/DISK-SpriteFPP.prg"
    d = driver.read_bytes()
    assert int.from_bytes(d[:2], "little") == 0x088F and decoder.memory[0x088F:0x08C1] == d[2:]
    supplied_path = CACHE / "NoBounds/Parts/SpriteFPP/SpriteFpp.prg"
    supplied = supplied_path.read_bytes()
    assert len(supplied) == 48386 and sha(supplied) == SUPPLIED_SHA
    supplied_memory = bytearray(65536)
    supplied_load = int.from_bytes(supplied[:2], "little")
    supplied_memory[supplied_load:supplied_load + len(supplied) - 2] = supplied[2:]
    checks = []
    for name, start, length in DOMAINS:
        defined = [a for a in range(start, start + length) if decoder.known[a]]
        unknown = [a for a in range(start, start + length) if not decoder.known[a]]
        differences = [{"address": a, "original": decoder.memory[a], "supplied": supplied_memory[a]}
                       for a in defined if decoder.memory[a] != supplied_memory[a]]
        assert not differences
        checks.append({"domain": name, "start": start, "bytes_requested": length,
                       "file_defined_exact_bytes": len(defined), "unknown_addresses": unknown,
                       "differences": differences, "file_defined_sha256": sha(bytes(decoder.memory[a] for a in defined))})
    assert sum(x["bytes_requested"] for x in checks) == 14793
    assert sum(x["file_defined_exact_bytes"] for x in checks) == 14790
    assert [a for row in checks for a in row["unknown_addresses"]] == [0x4000, 0x4001, 0x4002]
    loaded_variant_differences = [{"address": a, "production": decoder.memory[a], "supplied": supplied_memory[a]}
        for start, end in target["written_ranges"][1:] for a in range(start, end) if decoder.memory[a] != supplied_memory[a]]
    test_disk = BASE / "pinned-source/NoBounds/D64/SpriteFPP.d64"
    assert test_disk.read_bytes() not in disks
    result = {"pass": True, "script": record(Path(__file__).resolve()), "acquisitions": acquired,
        "source_identity": sources, "original_zip": {**record(archive), "csdb_release_id": 232957,
            "csdb_internal_file_id": 246029, "download_link_id": 286167}, "members": members,
        "source_test_disk": {**record(test_disk), "original_release_disk": False,
                             "manifest": record(BASE / "pinned-source/NoBounds/Parts/SpriteFPP/SpriteFPP.sls"),
                             "product_id": "9F33 versus original9F32"},
        "byte_bound_decoder": {"script": record(ROOT / "research/anomaly/inspect_boot.py"),
                               "primary_sources": primary, "family": "Matching Sparkle2.3 SL/SD data semantics",
                               "limit": "Exact loader/drive images do not establish a unique host builder executable"},
        "disks": disk_reports, "manifest_groups": groups, "target_manifest_group": manifest,
        "target_bundle": target, "production_Link": {**record(production), "sections": sections,
            "total_original_loaded_part_bytes_exact": sum(row["bytes"] for row in sections), "driver": record(driver),
            "driver_exact": True, "supplied_standalone_is_not_full_production_variant": True,
            "loaded_variant_differences": loaded_variant_differences},
        "supplied_Parts_PRG": record(supplied_path), "known_geometry_domains": checks,
        "requested_domain_bytes": 14793, "file_defined_exact_domain_bytes": 14790,
        "unloaded_domain_bytes": [0x4000, 0x4001, 0x4002],
        "natural_native_anchors": {"basic_SYS_entry": 0x0810, "post_resident_copy": 0x08B5,
            "loader_first_RTS_entry": 0xFF40, "resident_LoadNext": 0x0200,
            "target_bundle": 31, "target_DISK_entry": 0x0890, "target_init_call": 0x08A4,
            "target_init": 0xC300, "target_init_return": 0x08A7, "target_preload_call": 0x08A7},
        "limits": ["Offline data decoding only; no CPU, native/VICE, IEC/1541 or VIC scanout execution",
            "Bundle31 starts with unknown RAM; every accepted back-reference reads only bytes defined within it",
            "RAM dump zeroes at unknown addresses are placeholders, not fabricated original C64 prestate",
            "4000..4002 are outside the loaded original section; no zero-value or runtime-persistence assertion is made",
            "Standalone-versus-production differences are retained as build-variant differences, not runtime patches",
            "Other bundles may require resident-memory references; no unsupported state was invented to decode them",
            "No rebuild of published source or execution of downloaded host executables"]}
    path = out / "original-binding.json"
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"pass": True, "original_side1_bundle": 31, "loaded_part_bytes_exact": 20211,
                      "geometry_bytes_exact": 14790, "geometry_bytes_unloaded": 3,
                      "known_geometry_mismatches": 0, "receipt": record(path)}, indent=2))


if __name__ == "__main__":
    main()
