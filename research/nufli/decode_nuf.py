#!/usr/bin/env python3
"""Decode Mufflon 1.0's logical static NUFLI planes, not VIC raster hardware.

Address formulas are reconstructed independently of the writer's 100-row
address tables, then checked against all of those tables. Palette timing uses
the writer's separate odd normal-sprite / even FLI-bug colour-grid convention.
"""
import json
from pathlib import Path

from PIL import Image

from extract import ROOT, OUT, PACKAGE, sha

PEPTO = ('000000 ffffff 68372b 70a4b2 6f3d86 588d43 352879 b8c76f '
         '6f4f25 433900 9a6759 444444 6c6c6c 9ad284 6c5eb5 959595').split()
RGB = [tuple(bytes.fromhex(c)) for c in PEPTO]


def bottom_index(i):
    j = i-64
    return (j+(j >= 20)) % 4


def screen(i):
    if i < 64:
        return (0x3c00, 0x3800, 0x3400, 0x3000, 0x2c28, 0x2828,
                0x2428, 0x2028)[i % 8]+(i//8)*80
    return bottom_index(i)*0x400+0x280+((i-64)//4)*40


def sprite(i):
    return 0x3e80-(i % 8)*0x400 if i < 64 else bottom_index(i)*0x400+0x100


def bug_hires(i):
    return 0x59c0-(i % 8)*0x40 if i < 64 else 0x1200+bottom_index(i)*0x40


def bug_multi(i):
    return 0x57c0-(i % 8)*0x40 if i < 64 else bottom_index(i)*0x40


def sprite_row(y):
    # Starts at byte5 and advances three bytes after each even image line.
    # The unusual wrap excludes byte63 (sprite pointer, never bitmap data).
    row = 5
    for previous in range(y):
        if previous % 2 == 0:
            row += 3
        if row > 63:
            row &= 63
        elif row == 63:
            row = 0
    return row


def normal_sbyte(x, y):
    lane_byte = (x-24)//16
    r = (sprite_row(y)+lane_byte % 3) & 63
    if lane_byte >= 15 and y < 128:
        return 0x5400+((y//2 % 8) ^ 7)*64+r
    return sprite(y//2)+lane_byte//3*64+r


def decode(blob):
    assert len(blob) == 23042 and blob[:2] == b'\x00\x20'
    data = blob[2:]
    bitmap = data[0x4000:0x5400]+data[0x1400:0x1f40]
    assert len(bitmap) == 8000
    rows = [[data[base+i] for base in (0x400, 0x480, 0x800, 0x880, 0xc00, 0xc80)]
            for i in range(101)]
    # Normal sprite colours are initially row0. Subsequent row i starts at
    # image y=2*i-1, unlike bitmap/bug pairs which start at y=2*i.
    normal = list(rows[0])
    assert all(v < 16 for v in normal)
    normal_rows = [normal.copy()]
    bug = {0x27:data[0x1ff7]&15, 0x25:data[0x1ff1]&15,
           0x26:data[0x1ff0]&15, 0x2e:data[0x1ff6]&15}
    bug_rows = [bug.copy()]
    controls = {}
    for i in range(1, 101):
        for lane, value in enumerate(rows[i]):
            kind = value >> 4
            if kind == 0:
                normal[lane] = value
            elif kind >= 3:
                controls[kind] = controls.get(kind, 0)+1
                if (0x20 | kind) in bug:
                    bug[0x20 | kind] = value & 15
        normal_rows.append(normal.copy())
        bug_rows.append(bug.copy())
    pixels, uncovered_bug = [], 0
    ownership = {'bitmap_ink':0, 'bitmap_paper':0,
                             'normal_sprite':0, 'bug_hires':0, 'bug_multi':0}
    for y in range(200):
        for x in range(320):
            byte = bitmap[(y//8)*320+(x//8)*8+y % 8]
            matrix = data[screen(y//2)+x//8]
            paper, ink = matrix & 15, matrix >> 4
            if x < 24 and y % 8 >= 2:
                # Mufflon's FLI-bug conversion models the fetched $ff ink.
                # Transparent fallback is not a general VIC bus simulation.
                ink = 15
            bit = (byte >> (7-x % 8)) & 1
            if bit:
                value, owner = ink, 'bitmap_ink'
            elif 24 <= x < 312 and data[normal_sbyte(x,y)] & (0x80 >> (((x-24)//2) % 8)):
                value, owner = normal_rows[(y+1)//2][(x-24)//48] & 15, 'normal_sprite'
            elif x < 24:
                row = (sprite_row(y)+x//8) & 63
                b = bug_rows[y//2]
                if data[bug_hires(y//2)+row] & (0x80 >> (x % 8)):
                    value, owner = b[0x27], 'bug_hires'
                else:
                    pair = data[bug_multi(y//2)+row] >> (6-(x % 8)//2*2) & 3
                    if pair:
                        value, owner = b[{1:0x25,2:0x2e,3:0x26}[pair]], 'bug_multi'
                    else:
                        value, owner = paper, 'bitmap_paper'
                        if y % 8 >= 2:
                            uncovered_bug += 1
            else:
                value, owner = paper, 'bitmap_paper'
            assert 0 <= value <= 15
            pixels.append(value)
            ownership[owner] += 1
    assert sum(ownership.values()) == 64000
    return bytes(pixels), ownership, controls, uncovered_bug


def main():
    tables = json.loads((OUT/'source-arrays.json').read_text())
    comparisons = 0
    for name, fn in (('nuifli_scram',screen), ('nuifli_spram',sprite),
                     ('flibug_hires_spram',bug_hires), ('flibug_multi_spram',bug_multi)):
        assert [fn(i) for i in range(100)] == tables[name]
        comparisons += 100
    # The bitmap's two blocks and every sprite read must remain in the file.
    source_names = {'SMOKING FISH.NUF':'Smoking-Fish-pepto.bmp',
                    'FORGOTTEN   .NUF':'Forgotten-pepto.bmp',
                    'WRONG WAY   .NUF':'Wrong-Way-pepto.bmp'}
    receipt = []
    for item in json.loads((OUT/'extraction.json').read_text())['files']:
        if item['load_address'] != 0x2000:
            continue
        blob = (ROOT/item['path']).read_bytes()
        assert sha(blob) == item['sha256']
        pixels, owners, controls, uncovered_bug = decode(blob)
        assert uncovered_bug == 0  # All bundled examples cover this undefined fallback.
        stem = Path(item['path']).stem
        image = Image.new('RGB',(320,200)); image.putdata([RGB[v] for v in pixels])
        path = OUT/f'{stem}-logical.png'; image.save(path)
        (OUT/f'{stem}-indices.bin').write_bytes(pixels)
        row = dict(name=item['name'], prg_sha256=sha(blob), output=str(path.relative_to(ROOT)),
                   indices_sha256=sha(pixels), ownership=owners, control_kinds=controls)
        row['uncovered_flibug_pixels_outside_afli_lines'] = uncovered_bug
        if item['name'] in source_names:
            source = PACKAGE/'Examplepictures/16 static Colors (NUFLI)'/source_names[item['name']]
            original = Image.open(source).convert('RGB')
            target = list(image.get_flattened_data()); src = list(original.get_flattened_data())
            row['source_bitmap'] = str(source.relative_to(ROOT))
            row['source_bitmap_sha256'] = sha(source.read_bytes())
            row['same_rgb_pixels'] = sum(a == b for a,b in zip(target,src))
            # Some bundled BMP shades differ from Mufflon's Pepto table by
            # one RGB unit. Compare nearest palette indices separately.
            src_indices = [min(range(16), key=lambda i:sum((a-b)**2 for a,b in zip(c,RGB[i])))
                           for c in src]
            row['same_nearest_palette_indices'] = sum(a == b for a,b in zip(pixels,src_indices))
            row['comparison_note'] = 'Input art is not a lossless output oracle; conversion may replace colours.'
        receipt.append(row)
    result = dict(pass_=True, script_sha256=sha(Path(__file__).read_bytes()),
                  independent_address_formula_entries_checked=comparisons, files=receipt,
                  scope='Intended logical composition under Mufflon1.0 constraints, not raster/VIC/border/NTSC proof')
    (OUT/'decode-validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__ == '__main__':
    main()
