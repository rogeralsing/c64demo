#!/usr/bin/env python3
"""Passive original-source contracts for the Lab ball publication path."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile
import traceback

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / "build/research/lab-polygons-20261109/display-source-analysis"
IMAGE20 = "build/research/the-lab/side2-analysis/depacked/20.ram.bin"
IMAGE22 = "build/research/the-lab/side2-analysis/depacked/22.ram.bin"
MASK20 = "build/research/the-lab/side2-analysis/depacked/20.written.bin"
DECODER = "research/tower-power/static_loader.py"
VICE = "build/research/quondam/hardware-source/vice-3.10.tar.gz"
PINS = {
    IMAGE20: "f866f5a03713f91979dc4ad8421f95b4a9da6b405faea55804112e9993e90ef8",
    IMAGE22: "e95132427dc660f13e611bcb886636374d4f86e533b22a3dd286dc59896b5229",
    MASK20: "69666deef45da83279aadf998f467010be230b6adc32f80e3c8e099f2247c95a",
    DECODER: "21da904962fa53ab7fa3c72caf0bc5a21fa4eb0a94f2be6155ef06a6994b4ce4",
    VICE: "8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1",
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load_decoder():
    spec = importlib.util.spec_from_file_location("lab_ball_static_decoder", ROOT / DECODER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def listing(decoder, image, first, end):
    rows = []
    pc = first
    while pc < end:
        row = decoder.decode(image, pc)
        rows.append(row)
        pc = row["next"]
    assert pc == end, (hex(first), hex(end), hex(pc))
    return rows


def guard(image, address, expected, role):
    raw = bytes.fromhex(expected)
    assert image[address:address + len(raw)] == raw, (hex(address), role)
    return dict(first=address, end_exclusive=address + len(raw), hex=expected,
                sha256=sha(raw), role=role)


def color_copy(image):
    """Recognize all original cells; no supplied shadow values are evaluated."""
    assert image[0x26b9:0x26bb] == bytes.fromhex("a000")
    pc = 0x26bb
    groups, cells = [], []
    while image[pc] != 0x60:
        assert image[pc] == 0x98
        reset = pc
        pc += 1
        group = []
        while image[pc] == 0xae:
            source = int.from_bytes(image[pc + 1:pc + 3], "little")
            destination = int.from_bytes(image[pc + 10:pc + 12], "little")
            assert image[pc + 3:pc + 6] == bytes.fromhex("f0048a")
            assert image[pc + 6] == 0x8c and int.from_bytes(image[pc + 7:pc + 9], "little") == source
            assert image[pc + 9] == 0x8d and 0xd800 <= destination < 0xdc00
            row, column = divmod(destination - 0xd800, 40)
            assert source == 0xc500 + 24 * column + row
            cell = dict(index=len(cells), first=pc, end_exclusive=pc + 12,
                        source=source, destination=destination, row=row, column=column,
                        branch_zero_target=pc + 9, store_PC=pc + 9,
                        conditional_clear_PC=pc + 6)
            cells.append(cell)
            group.append(cell)
            pc += 12
        assert group
        column = group[0]["column"]
        assert all(c["column"] == column for c in group)
        rows = [c["row"] for c in group]
        assert rows == list(range(rows[0], rows[-1] + 1))
        groups.append(dict(column=column, reset_A_PC=reset, first_row=rows[0],
                           last_row=rows[-1], count=len(group),
                           first_cell=group[0]["index"], end_cell=len(cells)))
    assert pc == 0x3d83 and len(cells) == 484 and len(groups) == 24
    assert [g["column"] for g in groups] == list(range(8, 32))
    assert len({c["source"] for c in cells}) == len({c["destination"] for c in cells}) == 484
    return dict(entry=0x26b9, return_PC=pc, end_exclusive=pc + 1,
                source_bytes=pc + 1 - 0x26b9, cells=cells, groups=groups,
                unconditional_color_stores=484,
                shadow_window=[0xc5c0, 0xc800],
                shadow_cells_not_visited=576 - 484,
                symbolic_cell="X=shadow; if X!=0: A=X and shadow=0; ColorRAM=A&15",
                column_initial_A=0, Y_is_forced_zero=True,
                source_formula="C500 + 24*screenColumn + screenRow",
                destination_formula="D800 + 40*screenRow + screenColumn",
                every_visited_shadow_zero_on_normal_return=True,
                outside_crop_not_written_by_this_function=True,
                instruction_count_formula="26 + 3*484 + 2*nonzeroShadowEvents",
                instruction_count_bounds=[1478, 2446],
                no_fixed_cycle_or_scanout_deadline_claim=True)


def screen_footprints(decoder, image, color):
    """Derive screen destinations only, not attribute byte semantics."""
    result = []
    color_offsets = {c["destination"] - 0xd800 for c in color["cells"]}
    for flag, entry, low, high, stop_low, stop_high, screen in [
        (1, 0x6ee8, 0x88d4, 0x88ec, 0x8904, 0x891c, 0xdc00),
        (0, 0x6f27, 0x8934, 0x894c, 0x8964, 0x897c, 0x6000),
    ]:
        calls, stores = [], []
        for column_index in range(23, -1, -1):
            first = image[low + column_index] | image[high + column_index] << 8
            stop = image[stop_low + column_index] | image[stop_high + column_index] << 8
            rows = listing(decoder, image, first, stop)
            assert not any(r["mnemonic"] in ("LDX", "INX", "DEX", "TAX", "TSX", "JSR", "JMP", "RTS", "RTI") for r in rows)
            selected = [r for r in rows if r["mnemonic"] == "STA" and r["mode"] == "wx"]
            assert selected
            for row in selected:
                target = row["operand"] + column_index
                offset = target - screen
                y, x = divmod(offset, 40)
                assert x == 8 + column_index and 0 <= y < 24
                stores.append(dict(instruction_PC=row["address"], X=column_index,
                                   destination=target, row=y, column=x))
            calls.append(dict(X=column_index, first=first, stop_patch_address=stop,
                              screen_stores=len(selected)))
        assert len(stores) == 484 and {s["destination"] - screen for s in stores} == color_offsets
        result.append(dict(old_flag43=flag, wrapper=entry, screen=screen,
                           column_iteration="23 down to0", calls=calls,
                           screen_store_sites_in_normal_full_wrapper=484, stores=stores,
                           footprint_equals_ColorRAM_crop=True,
                           scope="Destination/address footprint only; nibble/event arithmetic belongs to the separate attribute consumer."))
    return result


def selector(bank, d018):
    return dict(bank=bank, D018=d018, screen=bank + ((d018 >> 4) & 15) * 0x400,
                bitmap=bank + ((d018 >> 3) & 1) * 0x2000)


def contracts(image, script):
    guards = [
        guard(image, 0x2030, "a9100d16d08d16d0", "init sets multicolor bit while preserving other D016 bits"),
        guard(image, 0x20f6, "a93b8d11d0", "normal post-initialization bitmap mode D0113B"),
        guard(image, 0x2116, "c60120008ce601", "file22 call under DEC01/INC01"),
        guard(image, 0x216d, "488a489848a50148a9358501203204", "IRQ saves registers/port, maps IO35, external0432 call"),
        guard(image, 0x2185, "a544f025a54349018543aaf00d", "pending gate, selector toggle and branch"),
        guard(image, 0x2192, "a9028d00dda9808d18d04ca921", "new43=1: bank latch first, D018 second"),
        guard(image, 0x219f, "a9008d00dda9788d18d0", "new43=0: bank latch first, D018 second"),
        guard(image, 0x21a9, "20b926c64420e883ee19d068850168a868aa6840", "color copy before request decrement/tail/ack/port restore"),
        guard(image, 0x224e, "a544d0fca543f009200b2620e86e4c652220622620276fe644", "wait, backbuffer paths and queued request"),
        guard(image, 0x21bd, "a54bc54cf019b008654dc54c900cb008", "full render entry before scale/edge work"),
        guard(script, 0x8c00, "a926853e8540a990853f8541a9168548a9908549", "file22 stream9026 and palette9016"),
        guard(script, 0x8c40, "a901854a20bd21", "first file22 render call8C44"),
    ]
    assert image[0x9035:0x903b] == bytes.fromhex("51459d40e0c8")
    assert image[0x8ff3:0x8ffd] == bytes.fromhex("a9408d3890a9408d3990")
    assert (image[0x87fc] | image[0x8814] << 8) == 0x7a46
    assert (image[0x885c] | image[0x8874] << 8) == 0x7ec6
    cases = []
    for old, new, bitmap_call, attr_call, bank, d018, old_bank, old_d018 in [
        (0, 1, 0x2662, 0x6f27, 0x4000, 0x80, 0xc000, 0x78),
        (1, 0, 0x260b, 0x6ee8, 0xc000, 0x78, 0x4000, 0x80),
    ]:
        cases.append(dict(old_flag43=old, new_flag43=new,
                          bitmap_fill_wrapper=bitmap_call, screen_wrapper=attr_call,
                          before=selector(old_bank, old_d018),
                          after_DD00_before_D018=selector(bank, old_d018),
                          at21A9=selector(bank, d018),
                          ColorRAM_copy_has_not_started_at21A9=True))
    return dict(guards=guards, cases=cases,
                queue=dict(wait=0x224e, render_complete_before_request=0x2265,
                           queued=0x2267, flag=0x44, normal_values=[0, 1],
                           test=0x2185, post_bank_pre_color_copy=0x21a9,
                           post_color_copy_pre_decrement=0x21ac, cleared=0x21ae),
                full_render_entry=0x21bd, first_file22_render_call=0x8c44,
                first_file22_return=0x8c47, file20_script_call=0x2118, file20_script_return=0x211b,
                fixed_IRQ_compare_source=250, IRQ_entry=0x216d,
                generator=dict(template_PC=0x9035, template="51459d40e0c8",
                               first_generated_entry=0x7a46, first_bitmap_bank=0xe000,
                               second_generated_entry=0x7ec6, second_bitmap_bank=0x4000,
                               rows_per_bank=192, generated_bytes=2304,
                               target_formula="bank + 0x40 + 320*(row//8) + (row%8) + X"),
                preconditions=["VIC must be in normal multicolor bitmap mode (BMM1/ECM0/MCM1); bind actual modes, not init alone.",
                               "CIA2 effective bank pins must match writes; bind DDR/readback in native evidence.",
                               "CPU01=35 IRQ code requires inherited CPU DDR to drive mapping bits; renderer uses34.",
                               "Normal renderer waits44=0 before filling, then INC44 queues one request; IRQ decrements after copy.",
                               "Edge/attribute construction at221C precedes the224E wait. No universal no-race or pre-entry-zero claim follows from that wait alone.",
                               "External0432 and asynchronous hardware/callback behavior are not evaluated here."])


def primary_sources():
    selected = {
        "vice-3.10/src/c64/c64cia2.c": [(136, 154)],
        "vice-3.10/src/c64/c64gluelogic.c": [(86, 107)],
        "vice-3.10/src/viciisc/vicii-fetch.c": [(158, 181), (192, 200)],
        "vice-3.10/src/c64/c64mem.c": [(613, 624)],
    }
    rows = []
    with tarfile.open(ROOT / VICE) as archive:
        for name, ranges in selected.items():
            raw = archive.extractfile(name).read()
            lines = raw.decode().splitlines()
            rows.append(dict(member=name, bytes=len(raw), sha256=sha(raw),
                             excerpts=[dict(first_line=a, last_line=b,
                                            text="\n".join(lines[a - 1:b]))
                                       for a, b in ranges]))
    return dict(archive=artifact(ROOT / VICE), members=rows,
                limit="Address/control and cache contracts only, not a VIC/GLUE/timing execution model.")


def capture_plan():
    return [
        dict(pc=0x2118, role="file22 pre-call", expected_port="34 after DEC01", proves="Original file20 call and loaded file22 generation"),
        dict(pc=0x8c00, role="file22 script entry", proves="Before script setup and every edge/event change"),
        dict(pc=0x8c44, role="first full render pre-call", proves="Exact first call with stream9026 and4A=1"),
        dict(pc=0x21bd, role="full body entry", proves="Before scale/translation, edge and attribute work; do not use224E as full render start"),
        dict(pc=0x224e, role="presentation wait", proves="Separate previous-request wait/fill subset from full work"),
        dict(pc=0x2265, role="render done before INC44", proves="Completed backbuffer, not necessarily displayed frame"),
        dict(pc=0x2267, role="request queued", expected_flag44=1, proves="Normal0-to1 queued generation before edge erasure/input advance"),
        dict(pc=0x2185, role="IRQ publication gate", condition="RAM44==1 plus source guard", proves="After unknown0432 callback; before toggle"),
        dict(pc=0x2190, role="selector stored and X loaded", proves="New43 selected; DD00/D018 writes still ahead"),
        dict(pc=0x21a9, role="post-bank/pre-ColorRAM", proves="Both selects changed; global ColorRAM copy has not started"),
        dict(pc=0x26b9, role="ColorRAM entry", proves="Before all484 shadow loads/clears and ColorRAM stores"),
        dict(pc=0x3d83, role="ColorRAM pre-RTS", proves="Normal484-cell copy finished, before caller return"),
        dict(pc=0x21ac, role="post-copy/pre-DEC44", proves="Strong postcopy ColorRAM endpoint before font tail"),
        dict(pc=0x21ae, role="request cleared", expected_flag44=0, proves="Before83E8 may update speech glyph pixels in both bitmap banks"),
    ]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to(BASE.resolve())
    out.mkdir(parents=True, exist_ok=False)
    checked = Path(__file__).read_bytes()
    (out / "ball_display_source.checked.py").write_bytes(checked)
    try:
        for name, expected in PINS.items():
            assert sha((ROOT / name).read_bytes()) == expected, name
        image = (ROOT / IMAGE20).read_bytes()
        script = (ROOT / IMAGE22).read_bytes()
        mask = (ROOT / MASK20).read_bytes()
        assert len(image) == len(script) == len(mask) == 65536
        decoder = load_decoder()
        segments = [(0x2000, 0x2089), (0x2116, 0x21bd),
                    (0x21bd, 0x2285), (0x260b, 0x26b9),
                    (0x26b9, 0x3d84), (0x6ee8, 0x6f66),
                    (0x83e8, 0x8419)]
        listings = []
        for first, end in segments:
            assert all(mask[first:end]), (hex(first), hex(end), "not original depacker stores")
            listings.append(dict(first=first, end_exclusive=end,
                                 sha256=sha(image[first:end]),
                                 instructions=listing(decoder, image, first, end)))
        color = color_copy(image)
        screens = screen_footprints(decoder, image, color)
        protocol = contracts(image, script)
        primaries = primary_sources()
        plan = capture_plan()
        outputs = [dict(name="ball_display_source.checked.py", bytes=len(checked), sha256=sha(checked))]
        for name, value in [("source-listings.json", listings), ("color-copy-map.json", color),
                            ("screen-footprints.json", screens), ("capture-plan.json", plan),
                            ("primary-source-anchors.json", primaries)]:
            raw = (json.dumps(value, indent=2) + "\n").encode()
            (out / name).write_bytes(raw)
            outputs.append(dict(name=name, bytes=len(raw), sha256=sha(raw)))
        proof = dict(pass_=True, scope="Original file20/file22 display publication contracts; static source recognition only.",
                     producer=artifact(Path(__file__)), inputs=[artifact(ROOT / p) for p in PINS],
                     publication=protocol, ColorRAM=dict(entry=color["entry"], end_exclusive=color["end_exclusive"],
                         cells=484, groups=24, slots_in_shadow_window=576,
                         copied_cells_zero_after_normal_return=True,
                         immediate_zero_invariant_does_not_prove_later_entry_state=True),
                     screen_backbuffer_bindings=[{k: r[k] for k in ("old_flag43", "wrapper", "screen", "screen_store_sites_in_normal_full_wrapper", "footprint_equals_ColorRAM_crop")} for r in screens],
                     outputs=outputs, limits=[
                         "No CPU/native/process/socket/build or downloaded host code is executed. Only the pinned existing static instruction reader is imported.",
                         "No native rendered marker/bitmap/attribute/color output is an input to these source contracts.",
                         "Logical bank addresses require native DDR/effective-pin and CPU-port bindings; GLUE and VIC caches are separate timed state.",
                         "DD00 precedes D018;21A9 is before the ColorRAM copy, not an atomic completed publication proof.",
                         "The484-cell ColorRAM zero invariant is immediate on normal return; earlier edge/attribute work precedes224E wait, so no arbitrary asynchronous no-race theorem is claimed.",
                         "ColorRAM is shared and4bit;484 shaped cells are written, not the entire1024-byte device or all576 shadow slots.",
                         "Current input pointer may advance after2265. Track queued/rendered generation rather than infer displayed pose from later3E/3F alone.",
                         "No copied-value, full color/committed-pixel, deadline, animation/FPS or physical-hardware result is claimed."])
        raw = (json.dumps(proof, indent=2) + "\n").encode()
        (out / "display-source-proof.json").write_bytes(raw)
        print(json.dumps(dict(pass_=True, receipt_bytes=len(raw), receipt_sha256=sha(raw), ColorRAM_cells=484)))
    except Exception as error:
        (out / "failure.json").write_text(json.dumps(dict(pass_=False, error_type=type(error).__name__,
            error=str(error), traceback=traceback.format_exc(),
            no_CPU_or_native_execution=True), indent=2) + "\n")
        raise


if __name__ == "__main__":
    main()
