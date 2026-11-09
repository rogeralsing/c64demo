#!/usr/bin/env python3
"""Pinned x64sc register rules and bounded VIC-II1.3 draw-tail decoding.

Pure finite data transformations and snapshot parsing only. No CPU execution,
instruction dispatcher, cycle interpreter, native process or hardware renderer.
"""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tarfile
import traceback

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/the-hat'
ARCHIVE = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
ARCHIVE_SHA = '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'
READER = ROOT / 'research/quondam/snapshot_state.py'
READER_SHA = 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a'
NATIVE_PROOF = BASE / 'upscroll-native-analysis/accepted-01/upscroll-native-proof.json'
NATIVE_SHA = '54f255845253703f876a2cc7915ef008d9f9dd479feb991fb898c4f9f6d28071'
CORE_END, DRAW_END, RASTER_HEADER_END, PAYLOAD_BYTES = 1881, 2055, 2071, 123415
_reader = None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def frozen_reader():
    global _reader
    assert sha(READER.read_bytes()) == READER_SHA
    if _reader is None:
        spec = importlib.util.spec_from_file_location('hat_hardware_frozen_snapshot', READER)
        _reader = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_reader)
    return _reader


# name, width, count, exact expression in the pinned snapshot writer.
DRAW_FIELDS = [
    *[(name, 1, 1, name) for name in (
        'gbuf_pipe0_reg', 'cbuf_pipe0_reg', 'vbuf_pipe0_reg',
        'gbuf_pipe1_reg', 'cbuf_pipe1_reg', 'vbuf_pipe1_reg',
        'xscroll_pipe', 'vmode11_pipe', 'vmode16_pipe', 'vmode16_pipe2',
        'gbuf_reg', 'gbuf_mc_flop', 'gbuf_pixel_reg', 'cbuf_reg', 'vbuf_reg', 'dmli')],
    ('sprite_x_pipe', 4, 8, '(uint32_t)sprite_x_pipe[i]'),
    *[(name, 1, 1, name) for name in (
        'sprite_pri_bits', 'sprite_mc_bits', 'sprite_expx_bits',
        'sprite_pending_bits', 'sprite_active_bits', 'sprite_halt_bits')],
    ('sbuf_reg', 4, 8, 'sbuf_reg[i]'),
    ('sbuf_pixel_reg', 1, 8, 'sbuf_pixel_reg, 8'),
    ('sbuf_expx_flops', 1, 1, 'sbuf_expx_flops'),
    ('sbuf_mc_flops', 1, 1, 'sbuf_mc_flops'),
    ('border_state', 1, 1, '(uint8_t)border_state'),
    ('render_buffer', 1, 8, 'render_buffer, 8'),
    ('pri_buffer', 1, 8, 'pri_buffer, 8'),
    ('pixel_buffer', 1, 8, 'pixel_buffer, 8'),
    ('cregs', 1, 0x2f, 'cregs, 0x2f'),
    ('last_color_reg', 1, 1, 'last_color_reg'),
    ('last_color_value', 1, 1, 'last_color_value'),
    ('cycle_flags_pipe', 4, 1, '(uint32_t)cycle_flags_pipe'),
]
assert sum(width * count for _, width, count, _ in DRAW_FIELDS) == DRAW_END - CORE_END == 174


def decode_vicii_tail(payload, version, old_core, border_mode=None):
    """Decode the exact retained PAL/normal-width C64SC1.3 layout, reject others.

An optional border_mode is a declared external resource value. The caller
must bind it to an actual resource query; a VSF does not serialize that query.
"""
    assert version == [1, 3] and len(payload) == PAYLOAD_BYTES
    assert old_core['core_bytes_parsed'] == CORE_END and old_core['model'] == 1
    assert old_core['opaque_draw_raster_tail_bytes'] == len(payload) - CORE_END
    assert old_core['opaque_draw_raster_tail_sha256'] == sha(payload[CORE_END:])
    assert border_mode in (None, 0), 'Only declared PAL normal-border geometry is supported'
    offset, draw, layout = CORE_END, {}, {}
    for name, width, count, _ in DRAW_FIELDS:
        first = offset
        values = [int.from_bytes(payload[offset + width*i:offset + width*(i+1)], 'little') for i in range(count)]
        offset += width * count
        draw[name] = values[0] if count == 1 else values
        layout[name] = dict(payload_offset=first, tail_offset=first - CORE_END, bytes=width * count, element_bytes=width, count=count)
    assert offset == DRAW_END
    header = {}
    for name in ('current_line', 'width', 'height', 'pitch'):
        header[name] = int.from_bytes(payload[offset:offset+4], 'little')
        offset += 4
    assert offset == RASTER_HEADER_END
    assert (header['width'], header['height'], header['pitch']) == (384, 312, 384)
    assert 0 <= header['current_line'] < 312
    padded = payload[offset:]
    padded_size, unpadded_offset = header['width'] * (header['height'] + 4), header['width'] * 2
    assert len(padded) == padded_size == 121344
    pixels = padded[unpadded_offset:unpadded_offset + header['width'] * header['height']]
    assert len(pixels) == 119808
    # Encode every decoded field back independently of the sequential reader.
    rebuilt = bytearray(DRAW_END - CORE_END)
    for name, width, count, _ in DRAW_FIELDS:
        values = [draw[name]] if count == 1 else draw[name]
        start = layout[name]['tail_offset']
        for i, value in enumerate(values):
            rebuilt[start + width*i:start + width*(i+1)] = value.to_bytes(width, 'little')
    assert rebuilt == payload[CORE_END:DRAW_END]
    normal = dict(border_mode=0, PAL_model=1, model_name='MOS8565', left_border=32, right_border=32,
        viewport_first_line=16, viewport_last_line=287, viewport_width=384, viewport_height=272,
        line_dbuf_copy_offset=17*8-32, framebuffer_graphics_x=32, framebuffer_graphics_y=51,
        framebuffer_origin='Unpadded allocation pixel(0,0); row number is raster.current_line, not cropped-screen row',
        snapshot_serializes_border_resource=False, external_resource_value_declared=border_mode is not None,
        applicable_only_if_actual_border_resource_is_zero=True)
    return dict(draw_pipeline=dict(values=draw, field_layout=layout, payload_range=[CORE_END, DRAW_END],
                    bytes=174, sha256=sha(payload[CORE_END:DRAW_END]), exact_reencode_equal=True),
        raster_store=dict(**header, header_payload_range=[DRAW_END, RASTER_HEADER_END],
            padded_payload_range=[RASTER_HEADER_END, PAYLOAD_BYTES], padded_bytes=len(padded),
            padded_sha256=sha(padded), top_padding_rows=2, bottom_padding_rows=2,
            unpadded_offset_in_padded=unpadded_offset, unpadded_payload_offset=RASTER_HEADER_END+unpadded_offset,
            unpadded_bytes=len(pixels), unpadded_sha256=sha(pixels), normal_PAL_geometry_contract=normal,
            lifetime='Line dbuf is accumulated during the beam, then committed at line end only for displayed viewport rows. Other rows may be old/initial. The currently accumulating line is not a newly committed canvas row.',
            full_current_field_or_pixel_model_claim=False),
        parsed_payload_end=PAYLOAD_BYTES, remaining_opaque_bytes=0,
        scope='Snapshot schema/data decoding; no pixels or internal pipelines are advanced by this reader.')


def read_extended_snapshot(path, border_mode=None):
    """Keep every frozen core field unchanged and add independently decoded tail."""
    reader = frozen_reader()
    original = reader.read_snapshot(path)
    core_hash = sha(canonical(original))
    payload = reader.module_payload(path, 'VIC-II')
    extension = decode_vicii_tail(payload, original['modules']['VIC-II']['version'], original['vicii'], border_mode)
    result = dict(original)
    result['raster_hardware_extension'] = extension
    result['frozen_core_canonical_sha256'] = core_hash
    assert {key: result[key] for key in original} == original
    return result


def framebuffer_bytes(path):
    """Return retained unpadded byte pixels, without claiming their generation."""
    reader = frozen_reader()
    original = reader.read_snapshot(path)
    payload = reader.module_payload(path, 'VIC-II')
    extension = decode_vicii_tail(payload, original['modules']['VIC-II']['version'], original['vicii'])
    raster = extension['raster_store']
    first = raster['unpadded_payload_offset']
    return payload[first:first + raster['unpadded_bytes']]


def d016_rmw(stored, delta):
    assert 0 <= stored < 256 and delta in (-1, 1)
    read_value = stored | 0xc0
    return read_value, (read_value + delta) & 255


def vic_register_read(registers, address, raster_line=None):
    """Source-used CPU I/O reads only; caller must establish actual I/O mapping.

This is an immediate read rule, not a CPU read-cycle or VIC pipeline model.
Dynamic light-pen/collision/IRQ reads are deliberately unsupported.
"""
    assert len(registers) == 64 and all(0 <= value < 256 for value in registers)
    assert 0xd000 <= address < 0xd400
    index = address & 63
    if index in (0x11, 0x12):
        assert raster_line is not None and 0 <= raster_line < 312
        if index == 0x11:
            return (registers[index] & 0x7f) | ((raster_line & 0x100) >> 1)
        return raster_line & 255
    if index == 0x16:
        return registers[index] | 0xc0
    if index == 0x18:
        return registers[index] | 1
    assert index in (*range(0x11), 0x15, 0x17, 0x1b, 0x1c, 0x1d), ('Unsupported dynamic/read register', hex(address))
    return registers[index]


def sax_store_value(a, x):
    assert 0 <= a < 256 and 0 <= x < 256
    return a & x


def vic_register_write(registers, address, raw_value):
    """Return logical register storage for the source-used stable store classes.

Keep raw_value separately for CPU store-event comparison. This does not
advance cached sprite X, DMA, ysmooth, IRQ, border or color pipeline state.
"""
    assert len(registers) == 64 and all(0 <= value < 256 for value in registers)
    assert 0xd000 <= address < 0xd400 and 0 <= raw_value < 256
    index = address & 63
    assert index in (*range(0x13), 0x15, 0x16, 0x17, 0x18, 0x1b, 0x1c, 0x1d, *range(0x20, 0x2f)), ('Unsupported side-effect store class', hex(address))
    result = list(registers)
    result[index] = raw_value & 15 if 0x20 <= index <= 0x2e else raw_value
    return result


def sprite_x_rmw(low, highmask, sprite, delta):
    assert 0 <= low < 256 and 0 <= highmask < 256 and 0 <= sprite < 8 and delta in (-1, 1)
    changed = (low + delta) & 255
    return changed, changed | (256 if highmask & (1 << sprite) else 0)


def nominal_pointer_address(bank, d018, sprite):
    assert bank in (0, 0x4000, 0x8000, 0xc000) and 0 <= d018 < 256 and 0 <= sprite < 8
    return bank + ((d018 & 0xf0) << 6) + 0x3f8 + sprite


def nominal_screen_character_bases(bank, d018):
    assert bank in (0, 0x4000, 0x8000, 0xc000) and 0 <= d018 < 256
    return bank + ((d018 & 0xf0) << 6), bank + ((d018 & 0x0e) << 10)


def sprite_dma_start(enabled, y, raster_line, dma, mcbase, exp_flop):
    """One declared check_sprite_dma event; not a raster-cycle scheduler."""
    assert enabled in (0, 1) and dma in (0, 1) and 0 <= y < 256
    assert 0 <= raster_line < 312 and 0 <= mcbase < 64 and exp_flop in (0, 1)
    if enabled and y == (raster_line & 255) and not dma:
        return 1, 0, 1
    return dma, mcbase, exp_flop


def border_top_event(d011, raster_line, vborder, set_vborder):
    """Only the named top-comparison event; do not advance time/later checks."""
    top = 0x33 if d011 & 8 else 0x37
    return (0, 0) if raster_line == top and d011 & 0x10 else (vborder, set_vborder)


def finite_rules():
    d016 = []
    for stored in range(256):
        for delta in (-1, 1):
            dummy, final = d016_rmw(stored, delta)
            assert dummy & 0xc0 == 0xc0 and final & 63 == ((stored & 63) + delta) & 63
            d016.append(dict(stored=stored, delta=delta, read_and_dummy_write=dummy, final_write=final))
    assert d016_rmw(0x88, -1) == (0xc8, 0xc7)
    assert d016_rmw(0x88, 1) == (0xc8, 0xc9)
    digest, count = hashlib.sha256(), 0
    for sprite in range(8):
        for mask in range(256):
            for low in range(256):
                for delta in (-1, 1):
                    final_low, final_x = sprite_x_rmw(low, mask, sprite, delta)
                    assert final_x >> 8 == bool(mask & (1 << sprite))
                    assert final_x & 255 == final_low
                    digest.update(bytes((sprite, mask, low, delta & 255, final_low, final_x >> 8)))
                    count += 1
    assert count == 1048576
    pointers = []
    for bank in (0, 0x4000, 0x8000, 0xc000):
        for d018 in range(256):
            for sprite in range(8):
                address = nominal_pointer_address(bank, d018, sprite)
                independent = bank + (d018 >> 4) * 1024 + 1016 + sprite
                assert address == independent
                pointers.append([bank, d018, sprite, address])
    sax_digest = hashlib.sha256()
    for a in range(256):
        for x in range(256):
            value = sax_store_value(a, x)
            assert all((value >> bit & 1) == ((a >> bit & 1) and (x >> bit & 1)) for bit in range(8))
            sax_digest.update(bytes((a, x, value)))
    assert 0xf0 & 0x88 == 0x80
    read_digest = hashlib.sha256()
    write_digest = hashlib.sha256()
    for stored in range(256):
        registers = [stored] * 64
        for line in range(312):
            high_read = vic_register_read(registers, 0xd011, line)
            low_read = vic_register_read(registers, 0xd112, line)
            assert high_read == vic_register_read(registers, 0xd111, line)
            assert high_read & 127 == stored & 127 and high_read >> 7 == line >> 8
            assert low_read == line & 255
            read_digest.update(bytes((stored, line & 255, line >> 8, high_read, low_read)))
        assert vic_register_read(registers, 0xd016) == stored | 0xc0
        assert vic_register_read(registers, 0xd118) == stored | 1
        for index in (*range(0x13), 0x15, 0x16, 0x17, 0x18, 0x1b, 0x1c, 0x1d, *range(0x20, 0x2f)):
            for mirror in range(16):
                address = 0xd000 + 64*mirror + index
                changed = vic_register_write([0]*64, address, stored)
                expected = stored & 15 if 0x20 <= index <= 0x2e else stored
                assert changed[index] == expected and all(v == 0 for i, v in enumerate(changed) if i != index)
                write_digest.update(bytes((stored, index, mirror, expected)))
    dma_digest, dma_count = hashlib.sha256(), 0
    for enabled in (0, 1):
        for dma in (0, 1):
            for y in range(256):
                for line in range(312):
                    for mcbase, flop in ((0, 1), (42, 0)):
                        result = sprite_dma_start(enabled, y, line, dma, mcbase, flop)
                        start = bool(enabled and not dma and y == line % 256)
                        assert result == ((1, 0, 1) if start else (dma, mcbase, flop))
                        dma_digest.update(bytes((enabled, dma, y, line & 255, line >> 8, mcbase, flop, *result)))
                        dma_count += 1
    assert dma_count == 638976
    top_digest, top_count = hashlib.sha256(), 0
    for rsel in (0, 8):
        for den in (0, 16):
            for line in range(312):
                for old_v in (0, 1):
                    for old_set in (0, 1):
                        actual = border_top_event(rsel | den, line, old_v, old_set)
                        if not den:
                            assert actual == (old_v, old_set)
                        top_digest.update(bytes((rsel, den, line & 255, line >> 8, old_v, old_set, *actual)))
                        top_count += 1
    aliases = [[address, address & 63] for address in range(0xd000, 0xd400)]
    assert dict(aliases)[0xd111] == 0x11 and dict(aliases)[0xd112] == 0x12 and dict(aliases)[0xd118] == 0x18
    return dict(d016=d016,
        certificates=dict(sprite_x=dict(cases=count, sha256=digest.hexdigest(), preserves_D010_bit=True,
                example_256_minus1_with_highbit_still_set=511),
            pointer_addresses=dict(cases=len(pointers), canonical_sha256=sha(canonical(pointers)),
                bank4000_screen4000_pointers=[nominal_pointer_address(0x4000, 0, i) for i in range(8)],
                bank4000_screen4400_pointers=[nominal_pointer_address(0x4000, 0x10, i) for i in range(8)],
                nominal_only='Actual fetch also applies phi-specific bank, address masks/offsets and possible character-ROM/cartridge mapping.'),
            SAX=dict(cases=65536, ordered_byte_triplets_sha256=sax_digest.hexdigest(), A_F0_X_88=0x80,
                scope='One stable NMOS6510 A&X store; no dummy RMW store or register/flag change is modeled.'),
            software_raster_reads=dict(cases=256*312, ordered_byte_records_sha256=read_digest.hexdigest(),
                D011_uses_actual_raster_bit8=True, D112_uses_actual_raster_low=True,
                no_stored_compare_byte_substitution=True),
            logical_register_writes=dict(cases=256*(19+7+15)*16,
                ordered_byte_records_sha256=write_digest.hexdigest(),
                D018_written_bit0_retained=True, color_storage_low_nibble_only=True,
                no_pipeline_or_cached_sprite_X_advance=True),
            DMA_start=dict(cases=dma_count, ordered_byte_records_sha256=dma_digest.hexdigest(),
                scope='Finite source predicate at one declared DMA check, not timing or a DMA row renderer.'),
            border_top=dict(cases=top_count, ordered_byte_records_sha256=top_digest.hexdigest(),
                DEN_clear_does_not_immediately_clear_or_set_border=True),
            VIC_aliases=dict(cases=len(aliases), canonical_sha256=sha(canonical(aliases)),
                D111=0x11, D112=0x12, D118=0x18)))


ANCHORS = {
    'Makefile.am': ['x64sc_libs =', '$(c64sc_lib)'],
    'c64/Makefile.am': ['c64cpusc.c'],
    'c64/c64cpusc.c': ['#define SKIP_CYCLE 0', '#include "../mainc64cpu.c"'],
    'mainc64cpu.c': ['#include "6510dtvcore.c"', '(*_mem_write_tab_ptr_dummy[(addr) >> 8])'],
    '6510dtvcore.c': ['#define SET_ABS_RMW(old_value, new_value)', 'STORE_DUMMY(p2, old_value);',
        'STORE(p2, new_value);', 'new_value = (old_value - 1) & 0xff;',
        'new_value = (old_value + 1) & 0xff;', 'ST(reg_a_read & reg_x, SET_ABS, 3);',
        'monitor_check_watchpoints(LAST_OPCODE_ADDR, (uint16_t)reg_pc);'],
    'viciisc/vicii-mem.c': ['addr &= 0x3f;', 'value = vicii.regs[addr] | 0xc0;',
        'value = vicii.regs[addr] | 0x1;', 'return tmp & 0xff;',
        'return (vicii.regs[addr] & 0x7f) | ((tmp & 0x100) >> 1);',
        'vicii.sprite[n].x = (value | (vicii.regs[0x10] & (1 << n) ? 0x100 : 0));',
        'vicii.sprite[i].x = (vicii.regs[2 * i] | (value & b ? 0x100 : 0));',
        'vicii.regs[addr] = value;', 'vicii.ysmooth = value & 0x7;',
        'inline static void sprite_color_store(uint16_t addr, uint8_t value)',
        'value &= 0xf;', 'color_reg_store(addr, value);'],
    'viciisc/vicii-cycle.c': ['vicii.sprite[i].mcbase = 0;', 'vicii.sprite[i].exp_flop = 1;',
        'if ((enable & b) && (y == (vicii.raster_line & 0xff)) && !(vicii.sprite_dma & b))',
        'if (vicii.sprite[i].mcbase == 63)', 'vicii.sprite[i].exp_flop ^= 1;',
        'vicii.vborder = 0;', 'vicii.set_vborder = 1;', 'vicii.main_border = 0;',
        'vicii.reg11_delay = vicii.regs[0x11];', 'vicii_raster_draw_handler();'],
    'viciisc/vicii-fetch.c': ['return ((vicii.regs[0x18] & 0xf0) << 6) + offset;',
        'a |= (vicii.regs[0x18] & 0xe) << 10;',
        'vicii.sprite[i].pointer = fetch_phi1(v_fetch_addr(0x3f8 + i));',
        'sprdata = fetch_phi1((vicii.sprite[i].pointer << 6) + vicii.sprite[i].mc);',
        'addr = ((addr + vicii.vbank_phi1) & vicii.vaddr_mask_phi1) | vicii.vaddr_offset_phi1;'],
    'viciisc/vicii-snapshot.c': ['vicii_draw_cycle_snapshot_write(m)', 'raster_snapshot_write(m, &vicii.raster)'],
    'viciisc/vicii-draw-cycle.c': ['int vicii_draw_cycle_snapshot_write(snapshot_module_t *m)',
        'sprite_x_pipe[s] = vicii.sprite[s].x;', 'if (xpos == sprite_x_pipe[s])',
        'sprite_pending_bits = vicii.sprite_display_bits;', 'cycle_flags_pipe = vicii.cycle_flags;'],
    'viciisc/vicii-draw.c': ['#define DBUF_OFFSET (17 * 8 - vicii.screen_leftborderwidth)',
        'src = &(vicii.dbuf[DBUF_OFFSET + xs * 8]);', 'memcpy(dest, src, (xe - xs + 1) * 8);'],
    'viciisc/vicii.c': ['width = vicii.screen_leftborderwidth + VICII_SCREEN_XPIX + vicii.screen_rightborderwidth;',
        'vicii.screen_leftborderwidth, VICII_NO_BORDER_FIRST_DISPLAYED_LINE,', 'raster_line_emulate(&vicii.raster);'],
    'viciisc/viciitypes.h': ['#define VICII_25ROW_START_LINE    0x33', '#define VICII_25ROW_STOP_LINE     0xfb',
        '#define VICII_24ROW_START_LINE    0x37', '#define VICII_24ROW_STOP_LINE     0xf7'],
    'viciisc/vicii-timing.h': ['#define VICII_SCREEN_PAL_NORMAL_LEFTBORDERWIDTH      0x20',
        '#define VICII_SCREEN_PAL_NORMAL_RIGHTBORDERWIDTH     0x20',
        '#define VICII_PAL_NORMAL_FIRST_DISPLAYED_LINE        0x10',
        '#define VICII_PAL_NORMAL_LAST_DISPLAYED_LINE         0x11f'],
    'viciisc/vicii-timing.c': ['case VICII_NORMAL_BORDERS:', 'vicii.first_displayed_line = VICII_PAL_NORMAL_FIRST_DISPLAYED_LINE;'],
    'viciisc/vicii-chip-model.c': ['static const struct ViciiChipModel chip_model_mos8565 = {',
        '"MOS8565",', 'case VICII_MODEL_8565:', 'vicii_chip_model_set(&chip_model_mos8565);'],
    'vicii.h': ['#define VICII_NORMAL_BORDERS 0', '#define VICII_MODEL_8565    1'],
    'raster/raster-snapshot.c': ['SMW_DW(m, raster->current_line)', 'SMW_DW(m, draw_buffer->draw_buffer_pitch)',
        'SMW_BA(m, draw_buffer->draw_buffer_padded_allocations[0], padded_size)'],
    'raster/raster.c': ['*padded_size = fb_width * (fb_height + 4);', '*unpadded_offset = fb_width * 2;',
        'raster->draw_buffer_ptr =', ') + raster->current_line'],
    'raster/raster-line.c': ['raster->current_line >= raster->geometry->first_displayed_line',
        'raster->current_line <= raster->geometry->last_displayed_line', 'raster->current_line++;'],
    'c64/c64.c': ['0xd300, 0xd3ff, 0x3f,'],
    'c64/c64mem.c': ['/* enable watchpoints on dummy accesses */', '_mem_write_tab_ptr_dummy = mem_write_tab_watch;',
        'monitor_watch_push_store_addr(addr, e_comp_space);'],
    'monitor/monitor.c': ['int break_on_dummy_access = 0;', 'watch_store_array[watch_store_count[mem]][mem] = addr;',
        'mon_breakpoint_check_checkpoint(mem, addr, lastpc, e_store)'],
    'monitor/mon_breakpoint.c': ['1 | (break_on_dummy_access << 1)'],
    'monitor/mon_parse.y': ['CMD_DUMMY end_cmd', 'Checkpoints will %strigger on dummy accesses.'],
}


def primary_sources():
    assert sha(ARCHIVE.read_bytes()) == ARCHIVE_SHA
    rows, excerpts, texts = [], [], {}
    with tarfile.open(ARCHIVE) as archive:
        for name, needles in ANCHORS.items():
            member = 'vice-3.10/src/' + name
            raw = archive.extractfile(member).read(); text = raw.decode(); texts[name] = text
            lines, matches = text.splitlines(), []
            for needle in needles:
                found = [i for i, line in enumerate(lines) if needle in line]
                assert found, (member, needle)
                matches.append(dict(needle=needle, lines=[i + 1 for i in found]))
                for i in found:
                    excerpts.append(dict(member=member, first_line=max(1, i-2),
                        lines=lines[max(0, i-3):i+4], anchor_line=i+1, needle=needle))
            rows.append(dict(member=member, bytes=len(raw), sha256=sha(raw), anchors=matches))
    text = texts['viciisc/vicii-draw-cycle.c']
    writer = text[text.index('int vicii_draw_cycle_snapshot_write('):text.index('int vicii_draw_cycle_snapshot_read(')]
    calls = re.findall(r'SMW_(B|DW|BA)\(m,\s*(.*?)\)\s*< 0', writer)
    expected = [('DW' if width == 4 else 'BA' if count > 1 else 'B', expression)
                for _, width, count, expression in DRAW_FIELDS]
    assert calls == expected, (calls, expected)
    assert writer.count('for (i = 0; i < 8; i++)') == 2
    block = re.search(r'chip_model_mos8565\s*=\s*\{(.*?)\};', texts['viciisc/vicii-chip-model.c'], re.S)
    assert block
    values = re.sub(r'/\*.*?\*/', '', block[1], flags=re.S)
    assert re.sub(r'\s+', '', values) == '"MOS8565",63,cycle_tab_pal,312,0,0,1'
    return dict(archive=meta(ARCHIVE), files=rows, exact_draw_writer_field_order_equal=True,
        exact_draw_writer_function_sha256=sha(writer.encode()),
        model8565=dict(enum=1, cycles_per_line=63, raster_lines=312, color_latency=0,
            cycle_table='cycle_tab_pal', old_light_pen_irq_mode=0, new_luminances=1)), excerpts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE / 'raster-hardware-analysis').resolve())
    out.mkdir(parents=True, exist_ok=False)
    checked = Path(__file__).read_bytes()
    (out / 'raster_hardware.checked.py').write_bytes(checked)
    try:
        assert sha(NATIVE_PROOF.read_bytes()) == NATIVE_SHA
        primary, excerpts = primary_sources()
        finite = finite_rules()
        native = json.loads(NATIVE_PROOF.read_text()); assert native['pass_']
        extended, bindings = {}, []
        for row in native['captures']:
            path = ROOT / row['snapshot']['path']
            assert meta(path) == row['snapshot']
            state = read_extended_snapshot(path)
            old = frozen_reader().read_snapshot(path)
            assert {key: state[key] for key in old} == old
            assert len(framebuffer_bytes(path)) == 119808
            extended[row['stem']] = state
            bindings.append(dict(stem=row['stem'], snapshot=meta(path),
                old_core_canonical_sha256=state['frozen_core_canonical_sha256'],
                all_old_fields_unchanged=True, parsed_payload_bytes=PAYLOAD_BYTES,
                draw_pipeline_sha256=state['raster_hardware_extension']['draw_pipeline']['sha256'],
                raster_buffer_sha256=state['raster_hardware_extension']['raster_store']['unpadded_sha256'],
                external_border_resource_value_supplied=False))
        outputs = []
        for name, value in [('primary-source-excerpts.json', excerpts), ('d016-finite-rmw.json', finite.pop('d016')),
                            ('extended-native02-snapshots.json', extended)]:
            raw = (json.dumps(value, indent=2) + '\n').encode()
            (out / name).write_bytes(raw)
            outputs.append(dict(name=name, bytes=len(raw), sha256=sha(raw)))
        outputs.append(dict(name='raster_hardware.checked.py', bytes=len(checked), sha256=sha(checked)))
        proof = dict(pass_=True, producer=meta(Path(__file__)), primary_sources=primary,
            frozen_reader=meta(READER), declared_native_context=meta(NATIVE_PROOF),
            finite_certificates=finite['certificates'], snapshot_bindings=bindings,
            schema=dict(VICII_version=[1, 3], model=1, model_name='MOS8565', payload_bytes=PAYLOAD_BYTES,
                frozen_core_range=[0, CORE_END], draw_pipeline_range=[CORE_END, DRAW_END],
                raster_header_range=[DRAW_END, RASTER_HEADER_END], padded_raster_range=[RASTER_HEADER_END, PAYLOAD_BYTES],
                unknown_variants_rejected=True, old_reader_unmodified=True),
            outputs=outputs,
            scope='Pinned x64sc register/address rules, finite word transformations and exact VICII1.3 retained draw/raster schema decoding. No machine/pixel/timing execution.',
            limits=[
                'Source-derived rules are bounded translations, not physical hardware experiments or a complete CPU/VIC interpreter.',
                'I/O aliases require actual I/O mapping. Nominal fetch addresses additionally depend on phi bank/address masks, cartridge and character-ROM state.',
                'Old core registers and new draw pipelines describe one instant. Pointer fetch latches, DMA byte counters, display/expansion flops, x pipelines and border/color pipelines cannot be replaced by final registers.',
                'One RMW instruction physically writes the read byte then changed byte under the x64sc source rules; monitor dummy coverage and deferred watch processing do not supply those two write timestamps.',
                'The decoded framebuffer is retained emulator output data, including old/initial out-of-viewport rows and padding. No row is declared current-generation merely because a snapshot exists or the beam wrapped.',
                'PAL normal viewport rows16..287 and left/right32 are conditional on actual border resource0 and captured model1(MOS8565); native02 did not query that resource, so the geometry remains an explicit source contract.',
                'No source edits to the frozen old reader, existing native proof, baseline docs/producers or existing artifacts; no native process, emulator, CPU interpreter, build, subprocess, socket or downloaded host execution.'
            ])
        raw = (json.dumps(proof, indent=2) + '\n').encode()
        (out / 'raster-hardware-proof.json').write_bytes(raw)
        print(json.dumps(dict(pass_=True, snapshots=len(bindings), receipt_bytes=len(raw), receipt_sha256=sha(raw))))
    except Exception as error:
        (out / 'failure.json').write_text(json.dumps(dict(pass_=False, error_type=type(error).__name__,
            error=str(error), traceback=traceback.format_exc(), producer=meta(Path(__file__))), indent=2) + '\n')
        raise


if __name__ == '__main__':
    main()
