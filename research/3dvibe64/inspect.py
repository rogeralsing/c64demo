#!/usr/bin/env python3
"""Independent passive arithmetic checks of pinned 3Dvibe64 source/data.

Upstream source attribution: 3Dvibe64, librologica.digital (2026), distributed
under PolyForm Noncommercial 1.0.0. This program never imports, evaluates, runs,
assembles or builds upstream code. Only our own parsers and arithmetic run.
"""
import hashlib
import json
from pathlib import Path
import re
import tarfile
import zipfile

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/research/3dvibe64"
COMMIT = "b19df459b7efe50d514b59fe876c0bc7c326c5b4"
FETCHED = {
    "article.html": ("https://www.retromind.it/blog/3dvibe64-gouraud-textures-and-raycasting-in-commodores-8-bit-world/",
                     "ae042a4686db5ce71daae8bd3d9f5191863e47f684e6b0aa63606edbf88dca51"),
    "commit.json": ("https://api.github.com/repos/Librologica/3Dvibe64/commits/main",
                    "d6d3ed84a9daacf8ce1368dbc7f306c36a88c3ef166ef9b116541829fc7ff1bd"),
    "tree.json": ("https://api.github.com/repos/Librologica/3Dvibe64/git/trees/main?recursive=1",
                  "c343c2b22c91d94bf00e503c2d2232141bda746625e58bf4310e138b1012c2e4"),
    "releases.json": ("https://api.github.com/repos/Librologica/3Dvibe64/releases?per_page=10",
                      "3422fd75d881d5dcb082651b30e37384fbf6382162c4a0e440ab10c9ee6c8777"),
    "upstream.tar.gz": (f"https://codeload.github.com/Librologica/3Dvibe64/tar.gz/{COMMIT}",
                        "fbccc522110b1fe4beb85ba1378183f70b5d8fc76227c2482306cd5354b4c998"),
    "3Dvibe64_1.15.1_source.zip": ("https://github.com/Librologica/3Dvibe64/releases/download/v1.15.1/3Dvibe64_1.15.1_source.zip",
                                 "1ba034569a0beff013800322bc6c8f1134894ab6e13eb3bb2bb055482a668cbc"),
    "SHA256SUMS.txt": ("https://github.com/Librologica/3Dvibe64/releases/download/v1.15.1/SHA256SUMS.txt",
                       "4b3862d59d24a719c20aa83d1f21c43ec66a4892da6fa997f4f630127090ec00"),
}
MEMBERS = [
    "README.md", "README.en.md", "GOURAUD-MODE6-REPORT.md", "MODE7.en.md",
    "TEXTURE-GUIDE.en.md", "QUALIFICATION-1.15.1.en.md", "RELEASE.json",
    "EXTERNAL-INPUTS.en.md", "LICENSE", "LICENSE-DOCUMENTATION.md",
    "work/build-3Dvibe64.ps1", "work/mode7-kernel.asm", "work/mode7-gouraud.asm",
    "work/mode7-lighting.asm", "work/legacy_gouraud_coherent.py",
    "work/legacy_gouraud_material.py", "work/mode7.py", "work/mode7_lighting.py",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def read_sources():
    receipt = []
    for name, (url, pin) in FETCHED.items():
        r = record(OUT / name)
        assert r["sha256"] == pin, name
        receipt.append(dict(r, original_url=url, observed_http_status=200,
                            acquisition_date="2026-11-08", replay_uses_retained_bytes=True))
    commit = json.loads((OUT / "commit.json").read_text())
    tree = json.loads((OUT / "tree.json").read_text())
    releases = json.loads((OUT / "releases.json").read_text())
    assert commit["sha"] == COMMIT and tree["sha"] == COMMIT
    assert not tree["truncated"] and releases[0]["tag_name"] == "v1.15.1"
    zip_pin = FETCHED["3Dvibe64_1.15.1_source.zip"][1]
    assert zip_pin in (OUT / "SHA256SUMS.txt").read_text()
    sources, member_records = {}, []
    tree_entries = {entry["path"]: entry for entry in tree["tree"]}
    with tarfile.open(OUT / "upstream.tar.gz") as archive, zipfile.ZipFile(OUT / "3Dvibe64_1.15.1_source.zip") as release:
        prefix = archive.getnames()[0]
        assert prefix == "3Dvibe64-" + COMMIT
        names = release.namelist()
        assert not any(n.lower().endswith(".prg") for n in names)
        assert not any(n.startswith(("examples/", "validation/")) for n in names)
        for name in MEMBERS:
            data = archive.extractfile(prefix + "/" + name).read()
            git_blob = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
            assert tree_entries[name]["sha"] == git_blob
            assert release.read(name) == data, f"Selected release/source member differs: {name}"
            assert (OUT / "source" / name).read_bytes() == data
            sources[name] = data.decode("utf-8-sig")
            member_records.append(dict(record(OUT / "source" / name),
                                       archive_member=prefix + "/" + name,
                                       release_zip_member=name, release_bytes_equal=True,
                                       source_url=f"https://github.com/Librologica/3Dvibe64/blob/{COMMIT}/{name}"))
    return sources, receipt, member_records, len(names)


def byte_array(source, label):
    match = re.search(r"(?m)^" + re.escape(label) + r": \.byte ([^\n]+)$", source)
    assert match, label
    return [int(v[1:], 16) if v.startswith("$") else int(v) for v in match[1].split(",")]


def check_bayer(source):
    host = re.search(r"\$gouraudBayer = @\(([0-9,]+)\)", source)
    assert host
    matrix = [int(v) for v in host[1].split(",")]
    embedded = byte_array(source, "gouraud_bayer4x4")
    # Canonical recursive Bayer construction, independent of the stored array.
    seed = [[0, 2], [3, 1]]
    recursive = [4 * seed[y % 2][x % 2] + seed[y // 2][x // 2]
                 for y in range(4) for x in range(4)]
    assert matrix == embedded == recursive and sorted(matrix) == list(range(16))
    for literal in ["$slot = if ($threshold -lt $shade) { 2 } else { 1 }",
                    "$slot = if ($threshold -lt ($shade - 16)) { 3 } else { 2 }",
                    "$Mode6ByteSpanKernelFlag = $Mode6GouraudFlag",
                    "lda yrow\n and #$03", "gdsb_lut_phase0:", "gdsb_lut_phase3:"]:
        assert literal in source
    masks = byte_array(source, "gouraud_pair_11")
    clears = byte_array(source, "gouraud_pair_clear")
    assert masks == [192, 48, 12, 3] and clears == [255 ^ m for m in masks]
    assert sum(masks) == 255 and all(not (a & b) for i, a in enumerate(masks) for b in masks[i + 1:])
    unpacked, packed, counts = [], [], []
    slots = []
    masked_cases = 0
    for shade in range(33):
        codes = [1 + int(shade > t) + int(shade > t + 16) for t in matrix]
        expected_counts = ({1: 16 - shade, 2: shade, 3: 0} if shade <= 16
                           else {1: 0, 2: 32 - shade, 3: shade - 16})
        assert {n: codes.count(n) for n in (1, 2, 3)} == expected_counts
        slots.append(codes)
        counts.append(dict(shade=shade, counts=expected_counts))
    assert len({tuple(row) for row in slots}) == 33
    for y in range(4):
        row = []
        for shade in range(33):
            fields = []
            for x in range(4):
                threshold = matrix[y * 4 + x]
                # Literal branch rule manually ported from the host source.
                slot = (2 if threshold < shade else 1) if shade <= 16 else (3 if threshold < shade - 16 else 2)
                assert slot == slots[shade][y * 4 + x]
                field = slot << (6 - 2 * x)
                fields.append(field)
                unpacked.append(field)
                for old in range(256):
                    # Actual partial-byte AND/OR masks versus independently
                    # decoding/replacing one 2-bit field and repacking it.
                    translated = (old & clears[x]) | (field & masks[x])
                    old_codes = [(old >> (6 - 2 * i)) & 3 for i in range(4)]
                    old_codes[x] = slot
                    reference = sum(v << (6 - 2 * i) for i, v in enumerate(old_codes))
                    assert translated == reference
                    masked_cases += 1
            byte = fields[0] | fields[1] | fields[2] | fields[3]
            assert [(byte >> (6 - 2 * x)) & 3 for x in range(4)] == slots[shade][y * 4:y * 4 + 4]
            row.append(byte)
            packed.append(byte)
        assert row == sorted(row)
    assert len(packed) == 132 and len(unpacked) == 528 and masked_cases == 135168
    assert packed[0] == 0x55 and packed[16] == 0xaa and packed[32] == 0xff
    # Uniform-span classifier: same endpoint byte means every intermediate
    # integer shade has that byte. DDA monotonicity then permits bulk fill.
    equal_pairs, interior_checks = 0, 0
    for y in range(4):
        row = packed[y * 33:(y + 1) * 33]
        for a in range(33):
            for b in range(33):
                if row[a] == row[b]:
                    equal_pairs += 1
                    for s in range(min(a, b), max(a, b) + 1):
                        assert row[s] == row[a]
                        interior_checks += 1
    for label in ["gdsb_uniform_first:", "gdsb_uniform_last:", "gouraud_draw_uniform_span:"]:
        assert label in source
    return dict(matrix=matrix, shade_levels=33, tile_samples=528,
                unique_tiles=33, shade_slot_counts=counts, masked_old_byte_cases=masked_cases,
                packed_bytes=132, scalar_layout_bytes=528,
                uniform_endpoint_pairs=equal_pairs, uniform_interior_checks=interior_checks,
                pixel_unit="logical multicolor pixels; standard renderer duplicates physical rows",
                phase_anchor="screen x mod4 / logical y mod4; no rotating phase"), bytes(packed), bytes(unpacked)


def check_dda(source):
    for literal in ["gouraud_advance_scan_pixel:", "adc gouraud_scan_delta",
                    "cmp gouraud_scan_span", "sbc gouraud_scan_span",
                    "adc gouraud_scan_dir"]:
        assert literal in source
    samples = spans = max_accumulator = 0
    digest = hashlib.sha256()
    for span in range(1, 160):
        for start in range(33):
            for end in range(33):
                delta, direction = abs(end - start), 1 if end >= start else -1
                error, shade, values = 0, start, bytearray()
                for k in range(span + 1):
                    # Closed-form rational interpolation, independent of the
                    # repeated subtraction in the pinned 6510 source.
                    assert shade == start + direction * ((k * delta) // span)
                    assert 0 <= shade <= 32 and 0 <= error < span
                    values.append(shade)
                    if k != span:
                        error += delta
                        max_accumulator = max(max_accumulator, error)
                        assert error < 256  # No omitted 8-bit carry in this domain.
                        while error >= span:
                            error -= span
                            shade += direction
                assert values[-1] == end
                digest.update(values)
                samples += len(values)
                spans += 1
    assert spans == 173151 and samples == 14025231
    return dict(span_extents=[1, 159], endpoint_domain=[0, 32], spans=spans,
                samples=samples, sample_stream_sha256=digest.hexdigest(),
                maximum_pre_reduction_error=max_accumulator, mismatches=0,
                scope="manually translated scalar integer DDA for nonzero normal-width spans; not instruction execution or full geometry")


def check_lighting(source):
    for literal in ["($dotHi * $gouraudIntensity * 32.0) / 240.0",
                    "lda gouraud_normal_x,y", "lda gouraud_normal_y,y", "lda gouraud_normal_z,y",
                    "sbc gouraud_center_dot_hi,y", "lda gouraud_level_ptr_lo,x",
                    "lda gouraud_shade_value,y", "cmp #$05"]:
        assert literal in source
    levels = []
    for intensity in range(11):
        row = []
        for dot_hi in range(64):
            # 32/240=2/15. Denominator15 excludes half-integer ties, so nearest
            # integer is exact here without assuming a floating-point tie rule.
            numerator = dot_hi * intensity * 2
            exact = min(32, (numerator + 7) // 15)
            host_translation = min(32, max(0, round(dot_hi * intensity * 32.0 / 240.0)))
            assert exact == host_translation
            row.append(exact)
        assert row == sorted(row)
        levels.extend(row)
    assert len(levels) == 704 and set(levels) == set(range(33))
    slew_cases = 0
    for old in list(range(33)) + [255]:
        for target in range(33):
            # Two formulations of the source's temporal +/-4 clamp.
            translated = target if old == 255 or abs(target - old) < 5 else old + (4 if target > old else -4)
            reference = target if old == 255 else old + max(-4, min(4, target - old))
            assert translated == reference and 0 <= translated <= 32
            slew_cases += 1
    return dict(level_table_entries=704, intensity_domain=[0, 10], dot_high_domain=[0, 63],
                mismatches=0, temporal_slew_cases=slew_cases, maximum_later_tick_level_change=4,
                scope="quantized light lookup and slew arithmetic; no complete normal/light/transform or scene proof"), bytes(levels)


def check_texture(sources):
    kernel = sources["work/mode7-kernel.asm"]
    host = sources["work/mode7.py"]
    assert "tex.get('width') != 16 or tex.get('height') != 16" in host
    assert "p not in (1, 2, 3)" in host
    assert "lda m7_v\n and #$f0\n sta m7_index\n lda m7_u\n lsr\n lsr\n lsr\n lsr\n ora m7_index" in kernel
    assert "lda m7_texture_0,y" in kernel
    histogram = [0] * 256
    for u in range(256):
        for v in range(256):
            source_index = (v & 240) | (u >> 4)
            reference_index = (v // 16) * 16 + (u // 16)
            assert source_index == reference_index and 0 <= source_index < 256
            histogram[source_index] += 1
    assert histogram == [256] * 256
    return dict(uv_byte_pairs=65536, mismatches=0, texture_dimensions=[16, 16],
                texture_page_bytes=256, uv_format="unsigned Q4.4",
                index_formula="16*floor(V/16)+floor(U/16)", texel_input_multiplicities=histogram,
                scope="default unlit affine address sampler only; no supplied texture, generated placement, projective or lit compositor proof")


def main():
    sources, fetched, members, zip_entries = read_sources()
    source = sources["work/build-3Dvibe64.ps1"]
    bayer, packed, unpacked = check_bayer(source)
    dda = check_dda(source)
    lighting, levels = check_lighting(source)
    texture = check_texture(sources)
    artifacts = []
    for name, data in [("bayer-packed.bin", packed), ("bayer-scalar-layout.bin", unpacked), ("light-levels.bin", levels)]:
        path = OUT / name
        path.write_bytes(data)
        artifacts.append(record(path))
    proof = dict(upstream_commit=COMMIT, upstream_committer_date="2026-10-30T06:29:46Z",
                 article_date="2026-10-01", latest_release="v1.15.1",
                 release_zip_entries=zip_entries, selected_release_equal_members=len(members),
                 observed_source_only_release_no_prgs=True, fetched=fetched, source_members=members,
                 method="our source-data parsers and independent arithmetic; no upstream imports/eval/build/native execution",
                 bayer=bayer, dda=dda, lighting=lighting, texture=texture, derived_tables=artifacts,
                 limitations=["No bundled Mode6/7 demo PRG, scene/artwork input or original native capture bound by this audit; engine font/templates remain",
                              "No full host generator, optional source rewrite, assembler, runtime or framebuffer acceptance",
                              "No PAL/NTSC timing, stock/accelerated speed, FPS or physical-hardware result",
                              "Bayer checks prove bit codes/densities, not palette luminance, material ownership or visual quality",
                              "DDA extent1..159 and shade0..32 only; clipping/edge setup and optional coherent path not executed",
                              "Texture proof is Q4.4 page indexing, not perspective correction or complete rendered sampling"])
    path = OUT / "proof.json"
    path.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps(dict(proof=record(path), upstream_commit=COMMIT,
                          bayer_levels=bayer["unique_tiles"], masked_cases=bayer["masked_old_byte_cases"],
                          uniform_endpoint_pairs=bayer["uniform_endpoint_pairs"], dda_samples=dda["samples"],
                          light_entries=lighting["level_table_entries"], uv_pairs=texture["uv_byte_pairs"],
                          mismatches=0, native_execution=False), indent=2))


if __name__ == "__main__":
    main()
