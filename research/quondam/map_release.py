#!/usr/bin/env python3
"""Map previously depacked original Quondam bytes; no CPU/emulator execution."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import shutil

REPO = Path(__file__).resolve().parents[2]
PRIOR = REPO/"build/research/frontier-followup"
OUT = REPO/"build/research/quondam"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    names = ["quondam-tunneling.prg", "quondam-unpacked-ram.bin", "quondam-depack.json",
             "quondam-window-proof.json", "quondam-init.txt", "quondam-renderer.txt"]
    reused = []
    for name in names:
        blob = (PRIOR/name).read_bytes()
        if (OUT/name).exists():
            assert (OUT/name).read_bytes() == blob
        else:
            shutil.copy2(PRIOR/name, OUT/name)
        reused.append({"file": name, "source": str((PRIOR/name).relative_to(REPO)),
                       "bytes": len(blob), "sha256": digest(blob)})
    program = (OUT/names[0]).read_bytes()
    raw = (OUT/names[1]).read_bytes()
    assert digest(program) == "e86e4bcf40e859f4ec3fcc83a86f8f0c172b6efa0a38d8dc199a85717fddc17c"
    assert digest(raw) == "8d1b7ea523dc2fbcb7c9ddc9b335cd451f87e0659b4e380b52334c350998e3db"

    labels = {
        "basic_sys_initial_and_depacked_entry": 0x080D,
        "sfx_final_jump_template_in_original_file": 0x8B65,
        "sfx_final_jump_relocated_runtime_pc": 0x01BD,
        "intro_natural_jump_to_tunnel": 0x09FF,
        "tunnel_initialization_entry": 0x9000,
        "asset_initialization": 0x902C,
        "color_ram_initialization": 0x90C9,
        "tunnel_initialization_complete_jump": 0x9029,
        "per_frame_irq": 0x9129,
        "top_sprite_irq": 0x9247,
        "viewport_preparation_irq": 0x92B0,
        "first_four_line_irq": 0x9300,
        "window_begin_before_d011": 0x9320,
        "window_after_both_patched_stores": 0x932D,
        "second_four_line_irq": 0x935C,
        "prepare_next_store_window": 0x939B,
        "foreground_wait_before_viewport": 0x93E9,
        "foreground_after_viewport_flag_before_line56_wait": 0x93ED,
        "foreground_wait_line228": 0x9595,
        "sprite_shift_worker": 0x961C,
        "d018_table": 0x966E,
        "dd02_table": 0x9680,
        "screen_page_table": 0x9692,
        "horizontal_motion_table": 0x9896,
        "vertical_motion_table": 0x9796,
    }
    expected = {0x01BD: bytes.fromhex("4c 0d 08"),
                0x080D: bytes.fromhex("a9 7f 8d 0d dc 78"), 0x09FF: bytes.fromhex("4c 00 90"),
                0x9000: bytes.fromhex("a9 0b 8d 11 d0 20 2c 90"),
                0x939B: bytes.fromhex("e6 11 a5 11 4a b0 1d")}
    for address, signature in expected.items():
        assert raw[address:address+len(signature)] == signature
    regions = [("intro_code", 0x080D, 0x0A00), ("tunnel_code_and_tables", 0x9000, 0x9696),
               ("smc_preparer", 0x939B, 0x93E9)]
    snapshots = []
    for name, start, end in regions:
        data = raw[start:end]
        filename = f"{name}-{start:04x}-{end:04x}.bin"
        (OUT/filename).write_bytes(data)
        snapshots.append({"file": filename, "start": start, "end_exclusive": end,
                          "bytes": len(data), "sha256": digest(data),
                          "native_compare_phase": "$9000 entry before initialization; later SMC changes are expected"})

    # Only a literal asset copy is needed to predict the selected glyph data.
    # This is not a reconstructed machine state: music, code SMC and IO remain out.
    prepared = bytearray(raw)
    prepared[0x2800:0x3000] = raw[0x7800:0x8000]
    table_rows = []
    selector_counts = Counter()
    for index, (d018, dd02) in enumerate(zip(raw[0x966E:0x9680], raw[0x9680:0x9692])):
        bank = (dd02&3)*0x4000
        screen = bank + ((d018>>4)&15)*0x400
        charset = bank + ((d018>>1)&7)*0x800
        data = prepared[charset:charset+0x800]
        counts = Counter((byte>>shift)&3 for byte in data for shift in (6,4,2,0))
        selector_counts.update(counts)
        sample = next((j for j, byte in enumerate(data) if len({(byte>>s)&3 for s in (6,4,2,0)}) == 4), None)
        table_rows.append({"index": index, "d018": d018, "dd02": dd02,
                           "expected_vic_bank": bank, "screen": screen, "pointer_table": screen+0x3F8,
                           "charset": charset, "prepared_charset_sha256": digest(data),
                           "all_glyph_selector_counts": dict(counts),
                           "four_selector_sample_address": charset+sample if sample is not None else None,
                           "four_selector_sample_byte": data[sample] if sample is not None else None})

    helper = json.loads((OUT/"quondam-window-proof.json").read_text())
    palettes = []
    for phase in (1, 3):
        case = helper["cases"][phase]
        assert case["phase"] == phase and case["sta"] == "d023" and case["stx"] == "d022"
        palette = [14, case["ldx"], case["lda"], 0]
        output_counts = Counter()
        for selector, count in selector_counts.items():
            output_counts[palette[selector]] += count
        palettes.append({"helper_phase": phase, "background_assumption": "viewport D021=$0E from $92C7/$92C9",
                         "color_ram_assumption": "$08 from original $90E7..$90F4 initialization",
                         "selector_palette_indices": palette,
                         "all_selected_asset_pixel_counts": dict(output_counts)})
    interpretations = []
    for value in range(256):
        selectors = [(value>>shift)&3 for shift in (6,4,2,0)]
        interpretations.append({"byte": value, "selectors": selectors,
                                "phase1_palette_indices": [palettes[0]["selector_palette_indices"][s] for s in selectors],
                                "phase3_palette_indices": [palettes[1]["selector_palette_indices"][s] for s in selectors]})

    result = {"scope": "Static original code/data mapping and finite pixel interpretation; no new CPU/VICE execution",
              "program_sha256": digest(program), "unpacked_ram_sha256": digest(raw),
              "reused_artifacts": reused,
              "labels": {name: {"address": address, "hex": f"${address:04X}"} for name,address in labels.items()},
              "preinitialization_regions": snapshots, "memory_selection_table": table_rows,
              "bank_derivation_assumption": "Original DD00 latch=0; low DD02 bits select outputs0 versus pulled-up inputs; confirm actual CIA2 pins natively",
              "charset_asset_scope": "All 256 glyphs per selected charset after literal7800->2800 copy; counts do not prove every glyph is fetched onscreen",
              "script_sha256": digest(Path(__file__).read_bytes())}
    (OUT/"release-map.json").write_text(json.dumps(result,indent=2)+"\n")
    (OUT/"pixel-interpretation.json").write_text(json.dumps({"scope": "Character pixels only; no VIC fetch/raster/sprite reconstruction",
        "palette_states_from_original_helper_receipt": palettes,
        "all_selected_asset_selector_counts": dict(selector_counts),
        "all_byte_values": interpretations},indent=2)+"\n")
    print(json.dumps({"memory_selection_entries": len(table_rows), "byte_interpretations":len(interpretations),
                      "selector_counts":dict(selector_counts), "palette_states":palettes},indent=2))


if __name__ == "__main__":
    main()
