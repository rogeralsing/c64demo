#!/usr/bin/env python3
"""Predict a bounded sprites-4..7 priority candidate from closed native-07.

This is host arithmetic and direct sprite-pair indexing, not native execution,
an original CPU model, a future whole-scene image or a timing measurement.
"""

import copy
import hashlib
import importlib.util
import itertools
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/anomaly'
OUT = BASE / 'overlap-plan'
PINS = {
    'research/anomaly/upper_scanout.py': '70a71b45b4c469182d6b5c5c8841fd20741fe0638ba90d5979f89abbc5d3667a',
    'build/research/anomaly/native-upper-fetch-analysis/native-upper-fetch-proof.json': '9e49c34e002474b9df311aca423519833cdf5118e39327f64d036a0e35bb09e2',
    'build/research/anomaly/arcade-source-proof.json': '30e681b44b72f7a610bd8b151762813c591ad7339b153ca8ce8d18117e61e729',
    'build/research/anomaly/native-07/upper-complete.vsf': '2560606a79af78009553dfcfef19d678e5d8eeddc46215aa81c2d4c56eda2474',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    data = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(data), sha256=sha(data))


def checked(item):
    data = (ROOT / item['path']).read_bytes()
    assert len(data) == item['bytes'] and sha(data) == item['sha256'], item['path']
    return data


def save(name, value):
    path = OUT / name
    path.write_text(json.dumps(value, indent=2) + '\n')
    return artifact(path)


def advance(state, mask, wave):
    """Evaluate only the original four constant-speed source branches."""
    state = copy.deepcopy(state)
    events = []
    for sprite in state:
        number = sprite['sprite']
        difference = sprite['low_x'] - sprite['speed']
        borrowed = bool(sprite['phase'] and difference < 0)
        writes = []
        if sprite['phase']:
            writes.append(difference & 255)
            if borrowed:
                writes.append((difference + 12) & 255)
                sprite['phase'] = 0
                mask &= ~(1 << number)
        wrapped = False
        if not sprite['phase'] or borrowed:
            writes.append(difference & 255)
            if writes[-1] < 6:
                wrapped = True
                writes.append(96)
                sprite['phase'] = 96
                mask |= 1 << number
                sprite['y'] = wave[sprite['wave_index']]
                sprite['wave_index'] = (sprite['wave_index'] + 1) & 255
        sprite['low_x'] = writes[-1]
        events.append(dict(sprite=number, low_x_writes=writes, borrowed=borrowed, wrapped=wrapped))
    return state, mask, events


def bounds(sprite, mask):
    left = sprite['low_x'] + (256 if mask & (1 << sprite['sprite']) else 0) + 8
    top = sprite['y'] + 1
    rectangle = (max(39, left), max(51, top), min(343, left + 48), min(155, top + 21))
    return rectangle if rectangle[0] < rectangle[2] and rectangle[1] < rectangle[3] else None


def overlaps(state, mask, art, palettes):
    boxes = {row['sprite']: bounds(row, mask) for row in state}
    pairs = []
    for first, last in itertools.combinations(range(4, 8), 2):
        a, b = boxes[first], boxes[last]
        if a and b and max(a[0], b[0]) < min(a[2], b[2]) and max(a[1], b[1]) < min(a[3], b[3]):
            pairs.append([first, last])
    if not pairs:
        return boxes, pairs, 0, []
    layers = {}
    for sprite in state:
        number = sprite['sprite']
        if boxes[number] is None:
            continue
        left = sprite['low_x'] + (256 if mask & (1 << number) else 0) + 8
        for row in range(21):
            line = sprite['y'] + row + 1
            if not 51 <= line < 155:
                continue
            data = int.from_bytes(art[number][row * 3:row * 3 + 3], 'big')
            for pair in range(12):
                selector = (data >> (22 - 2 * pair)) & 3
                if not selector:
                    continue
                for repeat in range(4):
                    x = left + pair * 4 + repeat
                    if 39 <= x < 343:
                        layers.setdefault((line, x), []).append(dict(sprite=number, row=row,
                            pair=pair, selector=selector, color=palettes[number][selector]))
    covered = [(point, rows) for point, rows in sorted(layers.items()) if len(rows) > 1]
    differing = [dict(line=point[0], x=point[1], layers=rows,
                      normal_sprite=rows[0]['sprite'], normal_color=rows[0]['color'],
                      reversed_sprite=rows[-1]['sprite'], reversed_color=rows[-1]['color'])
                 for point, rows in covered if rows[0]['color'] != rows[-1]['color']]
    return boxes, pairs, len(covered), differing


def main():
    for relative, digest in PINS.items():
        assert sha((ROOT / relative).read_bytes()) == digest, relative
    OUT.mkdir(parents=True, exist_ok=True)
    owner = json.loads((ROOT / 'build/research/anomaly/native-upper-fetch-analysis/native-upper-fetch-proof.json').read_text())
    assert owner['pass'] and owner['fifth_upper_field']['controls'][-1]['differences'] == 0
    seed = owner['final_continuation']
    ram = checked(seed['ram'])
    snapshot = ROOT / seed['snapshot']['path']
    checked(seed['snapshot'])
    spec = importlib.util.spec_from_file_location('overlap_frozen_upper', ROOT / 'research/anomaly/upper_scanout.py')
    upper = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(upper)
    _, reader = upper.readers()
    state = reader.read_snapshot(snapshot)
    assert ram == reader.module_payload(snapshot, 'C64MEM')[4:65540]
    vic = state['vicii']
    mask = ram[0xcb] & 0xf0
    sprites = [dict(sprite=s, low_x=vic['regs'][s * 2], y=vic['regs'][s * 2 + 1],
                    phase=ram[0xe8 + s], wave_index=ram[0xe0 + s - 2], speed=ram[0xf0 + s - 2])
               for s in range(4, 8)]
    initial = copy.deepcopy(sprites)
    wave = ram[0x39e9:0x3ae9]
    assert ram[0xca00:0xcb00] == ram[0x7400:0x7500]
    art = {s: ram[0xca00 + (s - 4) * 64:0xca00 + (s - 3) * 64] for s in range(4, 8)}
    palettes = {s: [None, vic['regs'][0x25], vic['regs'][0x27 + s], vic['regs'][0x26]] for s in range(4, 8)}
    assert [row['speed'] for row in sprites] == [8, 12, 12, 14]
    assert list(palettes.values()) == [[None, 1, 14, 3]] * 4
    author = json.loads((ROOT / 'build/research/anomaly/arcade-source-proof.json').read_text())
    selected = []
    for name in ('ArcadeScroller.asm', 'variables.asm', 'functions.asm', 'raster_irq.asm', 'scene_settings.asm'):
        item = next(item for item in author['sources'] if item['source_path'] == 'Parts/ArcadeScroller/' + name)
        checked(item)
        selected.append(item)
    scene_counter = int.from_bytes(ram[0xf0:0xf2], 'little')
    assert scene_counter == 124 and ram[0x3d89:0x3d8c] == bytes.fromhex('2c c2 66')
    inputs = save('inputs.json', dict(seed=seed, source_files=selected, upper_mask=mask, sprites=initial,
        scene_counter=scene_counter, wave_address=0x39e9, wave_bytes=list(wave),
        art_address=0xca00, mirrored_art_address=0x7400,
        sprite_art={s: dict(bytes=list(data), sha256=sha(data)) for s, data in art.items()}, palettes=palettes))
    search, transitions = [], []
    for updates in range(513):
        boxes, pairs, covered, different = overlaps(sprites, mask, art, palettes)
        search.append(dict(updates=updates, predicted_scene_counter=scene_counter + updates,
            mask_upper_bits=mask, sprites=copy.deepcopy(sprites), clipped_boxes=boxes,
            coarse_overlap_pairs=pairs, nontransparent_overlap_pixels=covered,
            priority_difference_pixels=len(different)))
        if different:
            candidate = search[-1]
            break
        sprites, mask, events = advance(sprites, mask, wave)
        transitions.append(dict(update=updates + 1, events=events))
    else:
        raise AssertionError('No distinguishing sprites-4..7 candidate in the declared 512-update search.')
    assert updates == 403 and mask == 0xf0
    assert [(point['line'], point['x'], point['normal_color'], point['reversed_color']) for point in different] == [
        (110, 318, 14, 1), (110, 319, 14, 1)]
    # Cross-check the predicted priority delta with the frozen compositor using
    # a declared artificial seed wall. The future wall itself is not predicted.
    template = next(row for row in owner['checkpoints'] if row['stem'] == 'fifth-field-pre')
    conditional = dict(ram=checked(template['ram']), state=reader.read_snapshot(ROOT / template['snapshot']['path']))
    for sprite in sprites:
        s = sprite['sprite']
        conditional['state']['vicii']['regs'][s * 2:s * 2 + 2] = [sprite['low_x'], sprite['y']]
    conditional['state']['vicii']['regs'][0x10] = mask
    normal, _, collisions = upper.compose(conditional)
    reverse, _, _ = upper.compose(conditional, 'reverse_sprite_priority')
    delta = upper.delta(normal, reverse)
    assert [(point['line'], point['x'], point['actual'], point['expected']) for point in delta] == [
        (110, 318, 14, 1), (110, 319, 14, 1)]
    counter = scene_counter + updates
    conditions = [(0xf0, counter & 255), (0xf1, counter >> 8)]
    conditions += [(0xe0 + row['sprite'] - 2, row['wave_index']) for row in sprites]
    command = 'break b400 if ' + ' && '.join(f'(@ram:${address:02x} == ${value:02x})' for address, value in conditions)
    search_artifact = save('search.json', search)
    transition_artifact = save('motion-transitions.json', transitions)
    candidate_artifact = save('candidate.json', dict(**candidate, priority_pixels=different,
        conditional_seed_wall_compositor_delta=delta, conditional_seed_wall_sprite_collisions=collisions))
    result = dict(pass_=True, script=artifact(Path(__file__).resolve()), inputs=inputs,
        pinned_inputs=[artifact(ROOT / relative) for relative in PINS], search=search_artifact,
        motion_transitions=transition_artifact, candidate=candidate_artifact,
        earliest_distinguishing_updates_among_sprites_4_through_7=updates,
        searched_update_indices=[0, updates], maximum_search_updates=512,
        predicted_scene_counter=counter, predicted_upper_mask_bits=mask,
        predicted_priority_differences=different,
        conditional_monitor_command=command,
        capture_plan=[
            'Use a fresh native directory and the unchanged native07/upper-complete.vsf as its explicit parent.',
            'Resume original code without PC/data/register writes. The proposed B400 condition uses only RAM counter/wave bytes.',
            'At the stop, verify actual VIC X/Y/high bits, upper bank/mode/pointers, sprite palettes and art. Do not treat RAM D00x bytes as live VIC registers.',
            'Check all eight actual sprites. Accept this priority witness only if sprites0..3 do not occlude line110 X318..319.',
            'At B400/line152 the candidate line110 is already committed. Read serialized palette indices and actual sprite latches; capture a later stop only if a wider strip is needed.',
            'Compose the newly captured wall and actual sprite state. The seed wall used by this host cross-check is not a future wall or native output.'],
        assumptions=[
            'One unchanged move_upper_sprites source update occurs per upper field; count403 is source motion updates, not measured timing.',
            'Sprites4..7 retain speeds8/12/12/14, the pinned Y-wave table and mirrored sprite art through the target.',
            'Upper sprites remain multicolor, horizontally expanded, enabled and in front of bitmap foreground, with palette1/14/3.',
            'The actual upper VIC bank may be4000 orC000 after wall publication; fetch actual bank/pointers instead of forcing the seed bank.',
            'Counter527 is below source high-byte4 sprite-fade enable and055E scene fade-out deadline; this bounds known fade triggers, not all possible program changes.'],
        pending_requirement='Native validation of all8 sprite coverage and all actual target state. Sprites2/3 use F0/F1 scene-counter aliases and moving foreground X; they were not simulated here.',
        earliest_scope='Only sprites4..7 under the declared constant-speed/source/art contract. No earliest whole-scene or all8-sprite claim.',
        native_observed=False, original_CPU_executed=False, future_whole_scene_image_predicted=False,
        native_priority_witness_complete=False, FPS_or_deadline_measurement=False)
    result['pass'] = result.pop('pass_')
    receipt = save('overlap-plan.json', result)
    print(json.dumps(dict(pass_=True, updates=updates, predicted_scene_counter=counter,
                         priority_difference_pixels=len(different), receipt=receipt,
                         pending_requirement=result['pending_requirement']), indent=2))


if __name__ == '__main__':
    main()
