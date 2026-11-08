#!/usr/bin/env python3
"""Read-only source/asset checks for the November frontier follow-up.

No downloaded Python, assembler, executable, disk program, or CPU routine runs.
"""
import hashlib
import json
import pathlib
import re
import zipfile

from PIL import Image, ImageOps

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = ROOT / "build" / "research" / "frontier-20261108"


def sha(data):
    return hashlib.sha256(data).hexdigest()


def disk_directory(data):
    assert len(data) == 174848
    sectors = [0] + [21] * 17 + [19] * 7 + [18] * 6 + [17] * 5

    def sector(track, number):
        assert 1 <= track <= 35 and 0 <= number < sectors[track]
        offset = (sum(sectors[1:track]) + number) * 256
        return data[offset:offset + 256]

    result, seen = [], set()
    track, number = 18, 1
    while track:
        assert (track, number) not in seen
        seen.add((track, number))
        block = sector(track, number)
        for offset in range(2, 256, 32):
            item = block[offset:offset + 30]
            if not item[0]:
                continue
            result.append(dict(type=item[0], start=[item[1], item[2]],
                               petscii_name=item[3:19].hex(),
                               ascii_name=item[3:19].rstrip(b"\xa0").decode("ascii", "replace"),
                               declared_blocks=int.from_bytes(item[28:30], "little")))
        track, number = block[:2]
    return result


def disk_file(data, track, number):
    sectors = [0] + [21] * 17 + [19] * 7 + [18] * 6 + [17] * 5
    payload, seen = bytearray(), set()
    while track:
        assert (track, number) not in seen
        seen.add((track, number))
        assert 1 <= track <= 35 and 0 <= number < sectors[track]
        offset = (sum(sectors[1:track]) + number) * 256
        block = data[offset:offset + 256]
        if block[0]:
            payload.extend(block[2:])
        else:
            assert 1 <= block[1] <= 255
            payload.extend(block[2:block[1] + 1])
        track, number = block[:2]
    return bytes(payload)


records = json.loads((BASE / "acquisitions.json").read_text())
for record in records:
    data = (BASE / record["name"]).read_bytes()
    assert len(data) == record["bytes"] and sha(data) == record["sha256"], record["name"]

bindings = {
    "tusari-main.a": "FLDParalax.a",
    "tusari-FLDParalaxNMISparse.a": "FLDParalaxNMISparse.a",
    "tusari-Sprites_Macros.a": "Sprites_Macros.a",
    "tusari-IRQSparse.a": "IRQSparse.a",
    "tusari-IRQSparse2.a": "IRQSparse2.a",
    "tusari-Data.a": "Data.a",
    "tusari-BuildIt.bat": "BuildIt.bat",
    "tusari-config.a": "_config.a",
    "tusari-v4.prg": "Tusari2TheRiver_V4.prg",
    "tusari-v3-repo.prg": "Tusari2TheRiver_V3.prg",
    "tusari-game.spd": "data/game.spd",
}
git_bindings = []
for tree_name in ("tusari-tree.json", "tusari-v4-tree.json"):
    tree = json.loads((BASE / tree_name).read_text())
    assert tree["truncated"] is False
    entries = {entry["path"]: entry for entry in tree["tree"]}
    for local, relative in bindings.items():
        data = (BASE / local).read_bytes()
        digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        assert digest == entries["Tusari2/FLDParalax/" + relative]["sha"], (tree_name, local)
        git_bindings.append(dict(tree=tree_name, local=local, path=relative, blob=digest))

assert (BASE / "dragonbond.d64").read_bytes() == (BASE / "dragonbond-csdb.d64").read_bytes()
assert (BASE / "dragonbond-making-of.pdf").read_bytes() == (BASE / "dragonbond-csdb.pdf").read_bytes()
assert (BASE / "tusari-v3-repo.prg").read_bytes() == (BASE / "tusari-v3-csdb.prg").read_bytes()

zip_members = []
with zipfile.ZipFile(BASE / "viva.zip") as archive:
    for member in archive.infolist():
        assert "/" not in member.filename and "\\" not in member.filename
        data = archive.read(member)
        (BASE / member.filename).write_bytes(data)
        zip_members.append(dict(name=member.filename, bytes=len(data), sha256=sha(data)))

original_side2 = (BASE / "Viva_Las_Vegas-CD_s2.d64").read_bytes()
fixed_side2 = (BASE / "viva-side2-fixed.d64").read_bytes()
side2_differences = [i for i, (a, b) in enumerate(zip(original_side2, fixed_side2)) if a != b]

# Source-bound sprite frame: bank $4000, !bin origin $5000 => frame 64.
# Data.a skips the SpritePad header plus the first 64 frames at $1009.
source = (BASE / "tusari-main.a").read_text()
irq = (BASE / "tusari-IRQSparse2.a").read_text()
data_source = (BASE / "tusari-Data.a").read_text()
assert 'GameSprites\n!bin "data/game.spd",(255-64)*$40,$1009' in data_source
assert "lda #144\n\tsta GameScreen2 + SPRITEFRAMESCROFF + 2" in source
assert "sta VIC2SpriteDoubleWidth" in source and "Forces the \"bullet\" sprite to be multicolour" in source
sprite_offset = 0x1009 + (144 - 64) * 64
sprite = (BASE / "tusari-game.spd").read_bytes()[sprite_offset:sprite_offset + 64]
nonzero_rows = [row for row in range(21) if any(sprite[row * 3:row * 3 + 3])]
assert nonzero_rows == [2, 3, 4, 10, 11, 12, 18, 19, 20]
pattern = sprite[2 * 3:5 * 3]
assert pattern == sprite[10 * 3:13 * 3] == sprite[18 * 3:21 * 3]
assert sprite[-1] == 0x8c  # 64th byte is outside the 63 displayed pixel bytes.

entries = re.findall(r"^IRQBulletRow(\d+)\s+\+MIRQBulletRow\s+(\d+)\s*,\s*(\w+)\s*,\s*(\d+)\s*,\s*(\d+)", irq, re.M)
assert len(entries) == 23
schedule = []
for i, (label, row, successor, last, update_y) in enumerate(entries):
    assert int(label) == int(row) == i
    assert int(last) == (i == 22)
    assert int(update_y) == (i % 3 == 2)
    assert successor == ("0" if i == 22 else f"IRQBulletRow{i + 1}")
    schedule.append(dict(row=i, irq_line=67 + i * 8,
                         next_sprite_y=67 + (i + 1) * 8 if int(update_y) else None))

# Exhaust the original ASL/STA/BCC/ORA-or-AND sequence's numeric contract.
# This is instruction-semantics arithmetic, not timing or assembled-code execution.
assert "lda BulletSprite_XPos + .row\n\tasl\n\tsta VIC2Sprite2X\n\tbcc .noMSB1" in irq
assert "ora #%100" in irq and "and #%11111011" in irq
for position in range(256):
    shifted, carry = (position << 1) & 255, position >> 7
    for shared_register in range(256):
        result = shared_register | 4 if carry else shared_register & 251
        assert shifted + (256 if result & 4 else 0) == 2 * position
        assert (result & 251) == (shared_register & 251)

# These PNGs are author's web illustrations, not C64 bitmap/RAM captures.
images = {key: Image.open(BASE / name).convert("RGBA") for key, name in
          (("quarter", "viva-mirror-final.png"), ("half", "viva-m1.png"), ("full", "viva-m2.png"))}
quarter, half, full = images["quarter"], images["half"], images["full"]
assert quarter.size == (320, 512) and half.size == (640, 512) and full.size == (640, 1024)
assert all(quarter.getpixel((x, y)) == quarter.getpixel((x + 1, y))
           for y in range(512) for x in range(0, 320, 2))
expected_half = Image.new("RGBA", half.size)
expected_half.paste(quarter, (0, 0))
expected_half.paste(ImageOps.mirror(quarter), (320, 0))
expected_full = Image.new("RGBA", full.size)
expected_full.paste(expected_half, (0, 0))
expected_full.paste(ImageOps.flip(expected_half), (0, 512))
assert half.tobytes() == expected_half.tobytes()
assert full.tobytes() == expected_full.tobytes()

result = dict(
    checked_acquisitions=len(records), git_bindings=git_bindings,
    tusari=dict(version_commit="7cea879b93f66231c1cc3c5bd782c14b71e24d7a",
                sprite_frame=144, sprite_source_offset=sprite_offset,
                sprite_bytes_hex=sprite.hex(), pixel_bytes_sha256=sha(sprite[:63]),
                pattern_hex=pattern.hex(), nonzero_rows=nonzero_rows,
                irq_schedule=schedule, x_encoding_cases=256 * 256,
                source_build_not_run=True, native_not_run=True),
    viva=dict(zip_members=zip_members, fixed_side2_different_bytes=len(side2_differences),
              fixed_side2_difference_offsets=side2_differences,
              image_sizes={key: value.size for key, value in images.items()},
              horizontal_pair_samples_checked=160 * 512,
              mirrored_rgba_pixels_checked=640 * 512 + 640 * 1024,
              original_program_pixels_not_checked=True),
    disks={name: disk_directory((BASE / name).read_bytes()) for name in
           ("dragonbond.d64", "mode-coder.d64", "Viva_Las_Vegas-CD_s1.d64", "Viva_Las_Vegas-CD_s2.d64", "viva-side2-fixed.d64")},
    excluded_route=dict(name="dragonbond-release.html", reason="Unrelated guessed CSDb ID 262297; replaced by event-linked 262185; never used as artifact authority"),
)
dragon_data = (BASE / "dragonbond.d64").read_bytes()
dragon_files = []
for track, number, name in ((18, 2, "dragonbond-boot.prg"),
                            (24, 16, "dragonbond-making-of-disk.prg"),
                            (24, 3, "dragonbond-shadows-prologue.prg")):
    payload = disk_file(dragon_data, track, number)
    (BASE / name).write_bytes(payload)
    dragon_files.append(dict(name=name, start=[track, number], bytes=len(payload),
                             sha256=sha(payload), load_address=int.from_bytes(payload[:2], "little")))
result["dragonbond_extracted_chains"] = dragon_files


def file_identity(path):
    data = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(data), sha256=sha(data))


result["producer"] = file_identity(pathlib.Path(__file__).resolve())
result["pre_tracked_checkpoint"] = [
    file_identity(BASE / "pre-tracked-producer" / name)
    for name in ("analyze.py", "findings.json")
]
assert result["pre_tracked_checkpoint"][0]["sha256"] == "0ca754b23182c67679a4975db5060370fa24b8f0ce411e2b11f648b662842b0a"
assert result["pre_tracked_checkpoint"][1]["sha256"] == "b788f534b6020f305cb03ccf03e55e82abb2d14c321287fbfd5118bba6718886"
previous_result = json.loads((BASE / "pre-tracked-producer" / "findings.json").read_text())
checked_result = {key: value for key, value in result.items() if key not in ("producer", "pre_tracked_checkpoint")}
assert json.loads(json.dumps(checked_result)) == previous_result
(BASE / "findings.json").write_text(json.dumps(result, indent=2) + "\n")
print(json.dumps(dict(acquisitions=len(records), git_bindings=len(git_bindings),
                      sprite_rows=nonzero_rows, irq_entries=len(schedule),
                      x_encoding_cases=65536, mirrored_rgba_pixels=983040,
                      fixed_side2_changed_bytes=len(side2_differences)), indent=2))
