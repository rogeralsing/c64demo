#!/usr/bin/env python3
"""Pinned no-side-effect VIC monitor readback contract and finite value rules.

No native wire is treated as input to the value helpers. A future custody
case must separately prove sidefxOFF, bank selection, phase and raw framing.
"""
import argparse
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
BASE = ROOT / 'build/research/the-hat/raster-hardware-analysis'
ARCHIVE = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
ARCHIVE_SHA = '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'
HARDWARE = ROOT / 'research/the-hat/raster_hardware.py'
HARDWARE_SHA = 'f9d15a6d26b877f63591b3c1ff7e31d3cf9430165783c89cb53b35ea6e32a12f'
_hardware = None


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def hardware():
    global _hardware
    if _hardware is None:
        assert sha(HARDWARE.read_bytes()) == HARDWARE_SHA
        spec = importlib.util.spec_from_file_location('hat_observer_frozen_hardware', HARDWARE)
        _hardware = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(_hardware)
    return _hardware


def model_readback(registers, address, raster_line=None):
    """Return (expected visible byte, comparison mask) from model state only.

An unbound raster input masks D011's live bit7 and omits D012 entirely.
Never feed a VIC dump byte to this function as a modeled register value.
Dynamic IRQ/lightpen/collision and unsupported context classes reject.
"""
    assert len(registers) == 64 and all(0 <= value < 256 for value in registers)
    assert 0xd000 <= address < 0xd400
    index = address & 63
    if index == 0x11 and raster_line is None:
        return registers[index] & 127, 127
    if index == 0x12 and raster_line is None:
        return 0, 0
    if 0x20 <= index <= 0x2e:
        return registers[index] | 0xf0, 255
    if index >= 0x2f:
        return 255, 255
    return hardware().vic_register_read(registers, address, raster_line), 255


ANCHORS = {
    'monitor/mon_parse.y': ['mon_memory_display(default_radix, $2[0], $2[1], DF_PETSCII);'],
    'monitor/mon_memory.c': ['v = mon_get_mem_val(mem, (uint16_t)ADDR_LIMIT(addr + i));'],
    'monitor/monitor.c': ['if ((sidefx == 0) && (mon_interfaces[mem]->mem_bank_peek != NULL))',
        'return mon_interfaces[mem]->mem_bank_peek(bank, mem_addr, mon_interfaces[mem]->context);',
        'return mon_get_mem_val_ex(mem, mon_interfaces[mem]->current_bank, mem_addr);'],
    'mainc64cpu.c': ['maincpu_monitor_interface->mem_bank_peek = mem_bank_peek;'],
    'c64/c64mem.c': ['"io",', 'static const int banknums[] = { 0, 0, 1, 2, 3, 4, -1 };',
        'uint8_t mem_bank_peek(int bank, uint16_t addr, void *context)',
        'case 3: /* io */', 'return peek_bank_io(addr);', 'return c64io_d000_peek(addr);'],
    'c64/c64io.c': ['/* peek from I/O area with no side-effects */',
        'return current->device->peek((uint16_t)(addr & current->device->address_mask));',
        'return io_peek(&c64io_d000_head, addr);'],
    'c64/c64.c': ['static io_source_t vicii_d000_device = {', 'vicii_peek,', 'IO_PRIO_HIGH,'],
    'viciisc/vicii-mem.c': ['uint8_t vicii_peek(uint16_t addr)',
        'return (vicii.regs[addr] & 0x7f) | ((read_raster_y () & 0x100) >> 1);',
        'return read_raster_y() & 0xff;', 'return vicii.sprite_sprite_collisions;',
        'return vicii.sprite_background_collisions;', 'return vicii.regs[addr] | unused_bits_in_registers[addr];'],
}


def primary_sources():
    assert sha(ARCHIVE.read_bytes()) == ARCHIVE_SHA
    rows, texts, excerpts = [], {}, []
    with tarfile.open(ARCHIVE) as archive:
        for name, needles in ANCHORS.items():
            member = 'vice-3.10/src/' + name
            raw = archive.extractfile(member).read(); text = raw.decode(); texts[name] = text
            lines, anchors = text.splitlines(), []
            for needle in needles:
                found = [i for i, line in enumerate(lines) if needle in line]
                assert found, (member, needle)
                anchors.append(dict(needle=needle, lines=[i+1 for i in found]))
                for i in found:
                    excerpts.append(dict(member=member, first_line=max(1, i-2),
                        anchor_line=i+1, lines=lines[max(0, i-3):i+4]))
            rows.append(dict(member=member, bytes=len(raw), sha256=sha(raw), anchors=anchors))
    source = texts['viciisc/vicii-mem.c']
    table = source[source.index('static const uint8_t unused_bits_in_registers'):source.index('/* FIXME plus60k')]
    table = re.sub(r'/\*.*?\*/', '', table, flags=re.S)
    mask = [int(value, 16) for value in re.findall(r'0x([0-9a-f]+)', table[table.index('{'):])]
    expected = [0]*32 + [0xf0]*15 + [0xff]*17
    expected[0x16], expected[0x18], expected[0x19], expected[0x1a] = 0xc0, 1, 0x70, 0xf0
    assert mask == expected and len(mask) == 64
    peek = source[source.index('uint8_t vicii_peek('):source.index('void vicii_init_colorram(')]
    assert 'clear_collisions' not in peek and not re.search(r'vicii\.[a-z_]+(?:\[[^]]+\])?\s*=(?!=)', peek)
    assert 'd019_store' not in peek and 'd019_read' not in peek and 'd01e_read' not in peek
    device = texts['c64/c64.c']
    device = device[device.index('static io_source_t vicii_d000_device'):device.index('static io_source_t vicii_d100_device')]
    assert '0xd000, 0xd0ff, 0x3f' in device and 'vicii_peek,' in device
    return dict(archive=meta(ARCHIVE), files=rows, VIC_unused_read_masks=mask,
        VIC_peek_has_no_device_state_assignment=True,
        no_D01E_D01F_clear_or_CIA_ICR_read_in_VIC_dump=True,
        direct_VIC_device_has_nonnull_peek=True,
        source_scope='The guarded computer-space sidefxOFF/bankIO path uses explicit VIC peek. Conditional alternatives and other I/O devices are not assumed to be side-effect-free.'), excerpts


def finite_values():
    model = hardware()
    digest, cases = hashlib.sha256(), 0
    for raw in range(256):
        for index in range(0x20, 0x2f):
            regs = model.vic_register_write([0]*64, 0xd000+index, raw)
            value, mask = model_readback(regs, 0xd000+index)
            assert (value, mask) == ((raw & 15) | 0xf0, 255)
            digest.update(bytes((raw, index, value, mask))); cases += 1
        regs = [raw]*64
        assert model_readback(regs, 0xd016) == (raw | 0xc0, 255)
        assert model_readback(regs, 0xd118) == (raw | 1, 255)
        assert model_readback(regs, 0xd111) == (raw & 127, 127)
        assert model_readback(regs, 0xd112) == (0, 0)
        for line in range(312):
            assert model_readback(regs, 0xd111, line) == ((raw & 127) | ((line & 256) >> 1), 255)
            assert model_readback(regs, 0xd112, line) == (line & 255, 255)
    rejected = []
    for index in (0x13, 0x14, 0x19, 0x1a, 0x1e, 0x1f):
        try:
            model_readback([0]*64, 0xd000+index)
        except AssertionError:
            rejected.append(index)
        else:
            raise AssertionError(('Unmodeled context was silently predicted', index))
    return dict(color_write_to_visible_cases=cases, ordered_color_quadruplets_sha256=digest.hexdigest(),
        D016_D018_and_unbound_raster_cases=256, bound_raster_pairs=256*312,
        rejected_context_registers=rejected,
        D016_stored_high2_bits_not_observable=True, D018_stored_bit0_not_observable=True,
        unbound_D011_compare_mask=127, unbound_D012_compare_mask=0,
        dump_bytes_are_oracle_only=True, no_native_dump_used_as_value_input=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to(BASE.resolve())
    out.mkdir(parents=True, exist_ok=False)
    checked = Path(__file__).read_bytes(); (out/'observer_schema.checked.py').write_bytes(checked)
    try:
        primary, excerpts = primary_sources()
        values = finite_values()
        raw = (json.dumps(excerpts, indent=2)+'\n').encode()
        (out/'observer-source-excerpts.json').write_bytes(raw)
        proof = dict(pass_=True, producer=meta(Path(__file__)), frozen_hardware=meta(HARDWARE),
            primary_sources=primary, finite_value_contract=values,
            required_case_bindings=['Computer monitor memoryspace', 'Explicit sidefxOFF with no intervening enable',
                'bankio selects bank3 and bankram is restored after the dump',
                'The standard VIC device has its registered peek callback; no memory hack remaps it',
                'No x/step/resume between composite register/dump commands; actual CPUclock equality separately checked',
                'Raw received bytes and per-hook Latin1 framing remain original, including PETSCII glyph bytes',
                'Every64byte dump remains a comparison oracle, never initial logical state, expected-store seed or model input'],
            scope='Primary source contract for monitor VIC peeking and model-to-visible value masks; no acceptance of a live or closed native readback window.',
            outputs=[dict(name='observer_schema.checked.py', bytes=len(checked), sha256=sha(checked)),
                dict(name='observer-source-excerpts.json', bytes=len(raw), sha256=sha(raw))],
            limits=['Source graph is conditional on declared observer mode/device registration; actual command phase and same-clock custody must be proved by its own closed native case.',
                'D011 bit7 and D012 are live beam values. Unknown beam context is masked/omitted, not copied from stored raster compare bytes.',
                'IRQ/lightpen/collision and unsupported context registers reject; full64byte dump availability does not imply prediction of all64bytes.',
                'Forced read bits hide some stored bits. A successful readback comparison cannot prove D018 writtenbit0 or D016 storedtop2bits.',
                'No CPU, VIC cycle, native process, emulator, snapshot restore, build, subprocess, socket, memory mutation or downloaded host program is executed.'])
        raw = (json.dumps(proof, indent=2)+'\n').encode(); (out/'observer-contract-proof.json').write_bytes(raw)
        print(json.dumps(dict(pass_=True, receipt_bytes=len(raw), receipt_sha256=sha(raw))))
    except Exception as error:
        (out/'failure.json').write_text(json.dumps(dict(pass_=False, error_type=type(error).__name__,
            error=str(error), traceback=traceback.format_exc(), producer=meta(Path(__file__))), indent=2)+'\n')
        raise


if __name__ == '__main__':
    main()
