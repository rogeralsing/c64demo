#!/usr/bin/env python3
"""Independently predict two visible Dragonbond bitmap/sprite bands.

The oracle directly samples the original bitmap and logical old/new sprite
images. It does not replay VICE's pixel shifter or execute C64 instructions.
"""
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/dragonbond'
OUT = BASE / 'scanout-analysis'
PINS = {
    'research/anomaly/scanout.py': 'c5e63a07f3060614710518aaf9b9e6c9365c297619af4e19719a4b5f8b62198f',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'build/research/dragonbond/native-analysis/native-evidence.json': 'f6be9f8c2e9acf40199743fe49f74c03137ca0d83935a2c4caea0b65721113e1',
    'build/research/dragonbond/original-analysis/native-handover.json': '450f867d9bfbfcb492aeec4fdbeb8252b604d2e6bbf4576143788d9626698c25',
    'build/research/dragonbond/native-01/scene-41-entry.vsf': '96f34d4beaec41de6f997aac42f8dcbc5e758fe3564c11c6c323c6a954bc1a3e',
    'build/research/dragonbond/native-02/picture-field-01-end.vsf': 'e3dc53d004163fece9bec0804dfb91790f1b7890ac0054d22cdf5e8973e7b593',
    'build/research/dragonbond/native-02/bank80-after-intermediate.vsf': '60a0050ec79eff0a6d96c4f6b3b812ea024e7022ae6b57d23d2b4b8034471dac',
    'build/research/dragonbond/native-02/monitor.log': '46ac61cf21f3d56b908eddd6cf7034c56c677eb2810a25fdff2adc48f78eb7d2',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
}
ROWS = list(range(126, 144)) + list(range(148, 157))


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def helpers():
    for name, digest in PINS.items():
        assert sha((ROOT / name).read_bytes()) == digest, name
    spec = importlib.util.spec_from_file_location('frozen_dragon_raster', ROOT / 'research/anomaly/scanout.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module, module.reader()


def rules():
    archive = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    guards = {
        'vicii-draw-cycle.c': ['COL_D021, COL_VBUF_H, COL_VBUF_L, COL_CBUF,',
                               'for (s = 7; s >= 0; --s)',
                               'if (!(pixel_pri && spri))',
                               'render_buffer[i] = COL_D027 + as;',
                               'cregs[last_color_reg] = last_color_value;',
                               'last_color_reg = vicii.last_color_reg;'],
        'vicii-fetch.c': ['a = (vicii.vc << 3) | vicii.rc;',
                           'a |= (vicii.regs[0x18] & 0x8) << 10;'],
        'vicii-draw.c': ['#define DBUF_OFFSET (17 * 8 - vicii.screen_leftborderwidth)'],
    }
    result = []
    with tarfile.open(archive, 'r:gz') as tar:
        for name, needles in guards.items():
            member = 'vice-3.10/src/viciisc/' + name
            data = tar.extractfile(member).read()
            assert all(text in data.decode() for text in needles), name
            path = OUT / 'source' / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            result.append(dict(member=member, **artifact(path)))
    return dict(archive=artifact(archive), files=result,
                url='https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/')


def line_model(ram, color_ram, regs, line, variant='correct'):
    pixels = bytearray([regs[0x20] & 15] * 384)
    row, fine = divmod(line - 51, 8)
    for cell in range(40):
        attribute = ram[0x4000 + row * 40 + cell]
        bits = ram[0x6000 + row * 320 + cell * 8 + fine]
        colors = [regs[0x21] & 15, attribute >> 4, attribute & 15,
                  color_ram[row * 40 + cell] & 15]
        for bit in range(8):
            code = (bits >> (6 - (bit // 2) * 2)) & 3
            color = colors[code]
            if variant == 'hires_bitmap':
                color = attribute >> 4 if bits & (128 >> bit) else attribute & 15
            pixels[32 + cell * 8 + bit] = color
    if variant == 'no_sprites':
        return bytes(pixels)
    # Logical image rows are independent of the intermediate-image operands.
    # Y=124 displays the old image from125; Y=145 displays the successor from146.
    first, origin = (0x2d, 125) if line < 146 else (0x3d, 146)
    if variant == 'early_successor' and 139 <= line <= 143:
        first = 0x3d
    order = range(8) if variant == 'reverse_priority' else range(7, -1, -1)
    for sprite in order:
        x = regs[2*sprite] + (256 if regs[0x10] & (1 << sprite) else 0) + 8
        address = 0x4000 + (first + sprite) * 64 + (line - origin) * 3
        bits = int.from_bytes(ram[address:address+3], 'big')
        for bit in range(24):
            target = x + bit
            if 32 <= target < 352 and bits & (1 << (23-bit)):
                pixels[target] = regs[0x27+sprite] & 15
    return bytes(pixels)


def main():
    frozen, native = helpers()
    OUT.mkdir(parents=True, exist_ok=True)
    owner = json.loads((BASE / 'native-analysis/native-evidence.json').read_text())
    handover = json.loads((BASE / 'original-analysis/native-handover.json').read_text())
    assert owner['pass'] and handover['pass']
    pre_path = BASE / 'native-02/picture-field-01-end.vsf'
    post_path = BASE / 'native-02/bank80-after-intermediate.vsf'
    original_path = BASE / 'native-01/scene-41-entry.vsf'
    pre, post = native.read_snapshot(pre_path), native.read_snapshot(post_path)
    ram, after = native.module_payload(pre_path, 'C64MEM')[4:65540], native.module_payload(post_path, 'C64MEM')[4:65540]
    original = native.module_payload(original_path, 'C64MEM')[4:65540]
    _, meta, raster = frozen.draw_state(native.module_payload(post_path, 'VIC-II'))
    assert meta['current_line'] == post['vicii']['raster_line'] == 242
    assert (pre['vicii']['raster_line'], pre['vicii']['raster_cycle']) == (78, 11)
    pre_clock = int.from_bytes(native.module_payload(pre_path, 'MAINCPU')[:8], 'little')
    post_clock = int.from_bytes(native.module_payload(post_path, 'MAINCPU')[:8], 'little')
    field_clock = pre_clock - 78*63 - 11
    assert (pre_clock, post_clock) == (149017061, 149027395)
    assert field_clock == post_clock - 242*63 - 13 == 149012136
    assert pre['vicii']['vborder'] == 0
    assert (pre['vicii']['vcbase'], pre['vicii']['rc']) == (120, 3)
    color_ram = pre['vicii']['color_ram']
    assert color_ram == post['vicii']['color_ram']
    domains = [(0x4000, 0x43e8), (0x6000, 0x8000)]
    domains += [(0x4000 + pointer*64, 0x4000 + pointer*64 + 63)
                for pointer in range(0x2d, 0x45)]
    for first, end in domains:
        assert ram[first:end] == after[first:end] == original[first:end], (first, end)
    for sprite in range(8):
        old, middle, new = [ram[0x4000+(pointer+sprite)*64:0x4000+(pointer+sprite)*64+63]
                            for pointer in (0x2d, 0x35, 0x3d)]
        assert middle[:33] == new[:33] and middle[33:] == old[33:]
    events = []
    for match in frozen.TRACE.finditer((BASE / 'native-02/monitor.log').read_text()):
        event = {key: (value if key == 'kind' else int(value, 16 if key in ('pc', 'target', 'a', 'x', 'y', 'sp') else 10))
                 for key, value in match.groupdict().items()}
        if 149017061 <= event['clock'] <= 149027395:
            events.append(event)
    assert events and events[0]['line'] == 78
    fields, predicted = [], {name: bytearray() for name in ('correct', 'no_sprites', 'reverse_priority', 'hires_bitmap', 'early_successor')}
    actual = bytearray()
    for line in ROWS:
        regs = list(pre['vicii']['regs'])
        cia_pra, cia_ddra = pre['cia']['CIA2']['pra'], pre['cia']['CIA2']['ddra']
        live_stores = []
        for event in events:
            if event['line'] > line:
                break
            target = event['target']
            if target in (0xdd00, 0xdd02):
                source = {0x8d: 'a', 0x8e: 'x', 0x8c: 'y'}[ram[event['pc']]]
                if target == 0xdd00:
                    cia_pra = event[source]
                else:
                    cia_ddra = event[source]
                continue
            if not 0xd000 <= target <= 0xd02e:
                continue
            opcode = ram[event['pc']]
            source = {0x8d: 'a', 0x8e: 'x', 0x8c: 'y'}.get(opcode)
            if source:
                regs[target-0xd000] = event[source]
                if event['line'] == line:
                    live_stores.append(event)
            else:
                assert target == 0xd019  # Original DEC acknowledges the IRQ.
        assert (regs[0x11], regs[0x16], regs[0x18]) == (0x3b, 0xd8, 9)
        pins = (cia_pra & cia_ddra) | (3 & ~cia_ddra)
        assert ((~pins) & 3)*0x4000 == 0x4000
        assert (cia_pra, cia_ddra) == (0xc2, 0x3f)
        assert (regs[0x15], regs[0x17], regs[0x1b], regs[0x1c], regs[0x1d]) == (255, 0, 0, 0, 0)
        assert regs[0x20] == 0
        # The selected bands avoid same-pixel X/color changes. New Y and
        # pointer publication are intentional; the old/new halves are checked
        # separately above and in the frozen native handover proof.
        for event in live_stores:
            if event['target'] in list(range(0xd000, 0xd010, 2)) + [0xd010, 0xd016, 0xd01b, 0xd01c, 0xd01d, 0xd020, 0xd021]:
                raise AssertionError(('Selected row changes geometry/mode', line, event))
            if 0xd027 <= event['target'] <= 0xd02e:
                sprite = event['target'] - 0xd027
                x = regs[2*sprite] + (256 if regs[0x10] & (1 << sprite) else 0) + 8
                pointer, origin = (0x2d, 125) if line < 146 else (0x3d, 146)
                address = 0x4000+(pointer+sprite)*64+(line-origin)*3
                bits = int.from_bytes(ram[address:address+3], 'big')
                active = [bit for bit in range(24) if bits & (1 << (23-bit))]
                # Transparent leading pixels consume no sprite color. Require
                # two complete draw cycles before the first nontransparent bit.
                assert not active or 8*(event['cycle']+2) < 104+x+active[0], (line, event, x, active)
        for name in predicted:
            predicted[name].extend(line_model(ram, color_ram, regs, line, name))
        actual.extend(raster[line*384:(line+1)*384])
        fields.append(dict(line=line, sprite_pointers_logical=list(range(0x2d if line < 146 else 0x3d,
                                                                        (0x2d if line < 146 else 0x3d)+8)),
                           sprite_row=line-(125 if line < 146 else 146), colors=regs[0x27:0x2f],
                           CIA2_pra=cia_pra, CIA2_ddra=cia_ddra,
                           same_line_stores=live_stores))
    assert predicted['correct'] == actual
    controls = {}
    for name, data in predicted.items():
        (OUT / f'{name}.bin').write_bytes(data)
        if name != 'correct':
            differences = [dict(line=ROWS[i//384], x=i%384, expected=actual[i], alternative=value)
                           for i, value in enumerate(data) if value != actual[i]]
            if name != 'reverse_priority':
                assert differences, name
            file = OUT / f'{name}-differences.json'
            file.write_text(json.dumps(differences, indent=2)+'\n')
            controls[name] = dict(different_indices=len(differences), discriminating=bool(differences),
                                  evidence=artifact(file))
            if not differences:
                controls[name]['limit'] = 'Inconclusive: this selected image does not distinguish sprite priority order.'
    (OUT / 'actual.bin').write_bytes(actual)
    # First-field DMA snapshots were deliberately not used as visible proof:
    # DEN is clear and these same selected raster rows are completely black.
    early = BASE / 'native-02/before-next-intermediate.vsf'
    early_entry = [row for session in owner['sessions'] for row in session['checkpoints']
                   if row['stem'] == 'before-next-intermediate']
    assert len(early_entry) == 1 and artifact(early) == early_entry[0]['snapshot']
    early_state = native.read_snapshot(early)
    _, early_meta, early_raster = frozen.draw_state(native.module_payload(early, 'VIC-II'))
    assert early_state['vicii']['regs'][0x11] == 0x2b and early_meta['current_line'] == 158
    assert early_state['vicii']['vborder'] == 1
    assert not any(early_raster[line*384+x] for line in ROWS for x in range(384))
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()),
                  inputs=[artifact(ROOT/name) for name in PINS], source_rules=rules(),
                  pre=artifact(pre_path), post=artifact(post_path), original=artifact(original_path),
                  field_base_clock=field_clock,
                  lines=ROWS, pixels=len(actual), differences=0,
                  nonzero_indices=sum(value != 0 for value in actual), palette_histogram=dict(Counter(actual)),
                  reference_sha256=sha(predicted['correct']), actual_sha256=sha(actual),
                  original_RAM_domains_equal_at_endpoints=[list(pair) for pair in domains],
                  row_history=fields, negative_controls=controls,
                  first_field_visibility_boundary=dict(snapshot=artifact(early), D011=0x2b, vertical_border_closed=True,
                                                        selected_rows_all_black=True,
                                                        scope='DMA data proof remains valid; these first-field rows are not visible-picture proof.'),
                  scope='Two disjoint visible second-field bands126..143 and148..156; original multicolor bitmap plus eight hires sprite overlays.',
                  limits=['Only27 selected rows; rows144..147 contain timing-sensitive position/color changes and are excluded.',
                          'Direct logical-image composition predicts output; it does not replay every VIC fetch or bus phase.',
                          'RAM domain equality is an endpoint check, not a continuous no-transient-write trace.',
                          'No complete-picture, whole-demo timing, physical-hardware or general alpha-blending claim.'])
    result['pass'] = result.pop('pass_')
    (OUT / 'scanout-proof.json').write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({key: result[key] for key in ('pass', 'pixels', 'differences', 'nonzero_indices', 'scope')}, indent=2))


if __name__ == '__main__':
    main()
