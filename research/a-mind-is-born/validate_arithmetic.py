#!/usr/bin/env python3
"""Bounded original-CPU checks of lft's LFSR, IRQ music and visual arithmetic.

Flat RAM with explicit timer/envelope input fixtures. No SID/VIC/CIA/ROM model,
interrupt scheduling, sound synthesis, rendered frame, or native timing claim.
"""

import hashlib
import importlib.metadata
import json
from collections import Counter
from pathlib import Path

from py65.devices.mpu6502 import MPU


ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "build/research/a-mind-is-born"
PRG_SHA = "7da29c8eed5acc39c5a1d3f0d40f5057c516cb6d2a04a18b15d71e6f8903f1f5"


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Cpu(MPU):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.instruct, self.cycletime = list(self.instruct), list(self.cycletime)
        for opcode, method, cycles in [(0xA7, self.lax_zp, 3), (0xB7, self.lax_zpy, 4),
                                       (0xAB, self.lax_zero, 2), (0x4B, self.alr, 2),
                                       (0x47, self.sre_zp, 5), (0xCB, self.axs, 2)]:
            self.instruct[opcode], self.cycletime[opcode] = method, cycles

    @staticmethod
    def lax_zp(c):
        c.a = c.x = c.memory[c.memory[c.pc]]
        c.FlagsNZ(c.a)
        c.pc += 1

    @staticmethod
    def lax_zpy(c):
        c.a = c.x = c.memory[(c.memory[c.pc] + c.y) & 255]
        c.FlagsNZ(c.a)
        c.pc += 1

    @staticmethod
    def lax_zero(c):
        # The otherwise model-dependent immediate LAX is asserted only with
        # operand0, where its result is necessarily0; no generic magic value.
        assert c.memory[c.pc] == 0
        c.a = c.x = 0
        c.FlagsNZ(0)
        c.pc += 1

    @staticmethod
    def alr(c):
        value = c.a & c.memory[c.pc]
        c.p = (c.p & ~c.CARRY) | (value & 1)
        c.a = value >> 1
        c.FlagsNZ(c.a)
        c.pc += 1

    @staticmethod
    def sre_zp(c):
        address = c.memory[c.pc]
        value = c.memory[address]
        c.memory[address] = value >> 1
        c.p = (c.p & ~c.CARRY) | (value & 1)
        c.a ^= value >> 1
        c.FlagsNZ(c.a)
        c.pc += 1

    @staticmethod
    def axs(c):
        value, operand = c.a & c.x, c.memory[c.pc]
        c.x = (value - operand) & 255
        c.p = (c.p & ~c.CARRY) | int(value >= operand)
        c.FlagsNZ(c.x)
        c.pc += 1


def image(blob):
    memory = bytearray(65536)
    memory[0x0801:0x08FF] = blob[2:]
    memory[3:255] = blob[4:]
    memory[0:3] = bytes((0x2F, 0x37, 0x77))
    memory[255] = 0xA5
    return memory


def run_to(cpu, target, limit=10000):
    count = 0
    while cpu.pc != target:
        assert count < limit and cpu.instruct[cpu.memory[cpu.pc]].__name__ != "inst_not_implemented"
        cpu.step()
        count += 1
    return count


def relocation_proof(blob):
    memory = bytearray(65536)
    memory[0x0801:0x08FF] = blob[2:]
    memory[0x08FF] = 0xA5
    memory[:3] = bytes((0x2F, 0x37, 0x77))
    memory[0x0314:0x0316] = bytes((0x31, 0xEA))
    cpu = Cpu(memory=memory, pc=0x08BC)
    instructions = run_to(cpu, 0x00CC)
    assert memory[3:255] == blob[4:] and memory[255] == 0xA5
    assert memory[:3] == bytes((0x2F, 0x37, 0x77))
    assert memory[0x0314:0x0316] == bytes((0x31, 0))
    return {"pass": True, "entry_after_ROM_clear": 0x08BC,
            "original_instructions": instructions, "payload_bytes_copied": 252,
            "extra_byte_read": 0x08FF, "extra_byte_destination": 255,
            "scope": "Copy-loop only; existing IRQ-vector low31 supplied, BASIC/ROM clear not executed"}


def next_lfsr(state):
    return (state >> 1) ^ (0xB8 if state & 1 else 0)


def lfsr_proof(blob):
    memory = image(blob)
    cpu = Cpu(memory=memory)
    instructions = 0
    for state in range(256):
        for carry in range(2):
            memory[0x14] = state
            cpu.pc, cpu.p = 0x8F, 0x20 | carry
            instructions += run_to(cpu, 0x9E)
            wanted = next_lfsr(state)
            assert memory[0x14] == wanted
            assert cpu.x == (wanted & 7)
            assert memory[0x12] == memory[0xF7 + (wanted & 7)]
    periods = []
    for seed in range(1, 256):
        state, seen = seed, set()
        while state not in seen:
            seen.add(state)
            state = next_lfsr(state)
        assert state == seed and len(seen) == 255 and 0 not in seen
        periods.append(len(seen))
    state, histogram = 1, Counter()
    for _ in range(255):
        state = next_lfsr(state)
        histogram[state & 7] += 1
    assert histogram == Counter({0: 31, **{i: 32 for i in range(1, 8)}})
    assert next_lfsr(0) == 0
    return {"pass": True, "original_CPU_cases": 512, "original_instructions": instructions,
            "recurrence": "s'=(s>>1) XOR(B8 if s&1 else0); index=s'&7",
            "nonzero_seeds_checked": len(periods), "period_for_each_nonzero_seed": 255,
            "zero_is_absorbing": True, "note_index_histogram_one_cycle": dict(histogram)}


def music_reference(memory):
    low = (memory[0x13] + 2) & 255
    memory[0x13] = low
    if low == 0:
        memory[0x20] += 1
    memory[0x1C] = 0x61
    bar = memory[0x20]
    if bar >= 64:
        return None
    if bar == 63:
        memory[0x22] = memory[0xD7] = 0x6D
    phase, script = low & 0x30, None
    if phase == 0:
        memory[0x1C] = 0x60
    if bar == 0x2F or phase == 0x10:
        high = 0
    else:
        index = 2 if bar < 0x2F else bar & 3
        bass = memory[0xF3 + index]
        memory[0x0A] = bass
        high = bass & 3
        if phase == 0:
            offset = 2 * (bar >> 3)
            target, value = memory[0x21 + offset], memory[0x22 + offset]
            memory[target] = value
            script = (target, value)
            step = (low & 0x0E) >> 1
            memory[0xCC] = 8 + step
            high = 7 - step
    memory[0x0B] = high
    note = None
    if low & 15 == 0:
        memory[0x14] = next_lfsr(memory[0x14])
        note = memory[0x14] & 7
        memory[0x12] = memory[0xF7 + note]
    writes = [(0xD01C + y, memory[0x0D + y]) for y in range(8, -1, -1)]
    writes += [(0xD3FF + y, memory[9 + y]) for y in range(25, 0, -1)]
    return bar, note, script, writes


class MusicRam:
    def __init__(self, data):
        self.data = data
        self.writes = []

    def __getitem__(self, address):
        return self.data[address]

    def __setitem__(self, address, value):
        self.data[address] = value
        if 0xD000 <= address < 0xE000:
            self.writes.append((address, value))


def music_proof(blob):
    data, reference = image(blob), image(blob)
    data[0xD011] = 0x50
    ram = MusicRam(data)
    cpu = Cpu(memory=ram)
    instructions = normal_ticks = 0
    counts, scripts, bass_notes = Counter(), Counter(), Counter()
    for tick in range(1, 8193):
        wanted = music_reference(reference)
        cpu.pc, cpu.p = 0x31, 0x20 | (tick & 1)
        ram.writes.clear()
        count = 0
        while cpu.pc not in (0xEA7E, 0x48):
            assert count < 500
            cpu.step()
            count += 1
        instructions += count
        assert data[:256] == reference[:256], tick
        if wanted is None:
            assert tick == 8192 and cpu.pc == 0x48
            assert data[0x20] == 64 and data[0x13] == 0
            assert data[0xD011] == 0x28
            break
        bar, note, script, writes = wanted
        assert cpu.pc == 0xEA7E and ram.writes == writes, tick
        normal_ticks += 1
        if note is not None:
            counts[note] += 1
        if script is not None:
            scripts[f"{script[0]:02x}:{script[1]:02x}"] += 1
        bass_notes[f"{data[0x0B]:02x}{data[0x0A]:02x}"] += 1
    assert sum(counts.values()) == 1023
    return {"pass": True, "interrupt_calls_including_end": 8192,
            "normal_calls_returning_to_Kernal": normal_ticks,
            "original_instructions": instructions,
            "literal_SID_writes_compared": normal_ticks * 25,
            "literal_VIC_writes_compared": normal_ticks * 9,
            "melody_updates": sum(counts.values()), "song_note_index_histogram": dict(counts),
            "script_write_counts": dict(scripts), "voice1_frequency_word_counts": dict(bass_notes),
            "end_stop_before_reset_jump": 0x48,
            "scope": "No main-loop interleaving, incoming carry varied; literal writes including read-only VIC targets, not chip state/sound; ROM prologue/tail/reset omitted"}


def font_proof(blob):
    memory = image(blob)
    cpu = Cpu(memory=memory)
    cases = 0
    for op1 in (0xA0, 0x24, 0x29):
        memory[0xD5] = op1
        for op2 in (0x0D, 0x6D):
            memory[0xD7] = op2
            for timer in range(256):
                memory[0xDC04] = timer
                for envelope in range(256):
                    memory[0xD41C] = envelope
                    for carry in range(2):
                        cpu.pc, cpu.p, cpu.sp, cpu.y = 0xD2, 0x20 | carry, 0x80, 0x77
                        run_to(cpu, 0xDD)
                        value = timer & 0xC3 if op1 == 0x29 else timer
                        value = value | envelope if op2 == 0x0D else (value + envelope + carry) & 255
                        assert memory[0x0180] == value and cpu.sp == 0x7F
                        assert cpu.a == (value & 4) >> 1 and not cpu.p & cpu.CARRY
                        cases += 1
    return {"pass": True, "cases": cases,
            "domain": "All256 timer×256 envelope×2 incoming carries×3 first opcodes×2 envelope opcodes",
            "stack_byte": 0x0180,
            "scope": "Controlled register-read values; no actual envelope/timer waveform, stack IRQ interference or displayed image"}


def neighbour_proof(blob):
    memory = image(blob)
    cpu = Cpu(memory=memory)
    cases, wraps = 0, 0
    for seed in (0, 2):
        for left in range(256):
            for right in range(256):
                low, high = (left * 73 + right * 37 + seed) & 255, 8 + ((left ^ right) & 7)
                bar, opcode = (left + 3 * right + seed) & 63, (0xA0, 0x24, 0x29)[(left ^ right ^ seed) % 3]
                pointer, following = high * 256 + low, high * 256 + ((low + 1) & 255)
                memory[0xCB:0xCD] = bytes((low, high))
                memory[0x20], memory[0xD5] = bar, opcode
                memory[pointer + 0x30], memory[following + 0x30] = left, right
                cpu.pc, cpu.p, cpu.a = 0xDD, 0x20, seed
                run_to(cpu, 0xD2)
                first = seed + left
                second = (first & 255) + right + (first >> 8)
                value = ((second & 255) >> 1) | ((second >> 8) << 7) | bar | opcode
                assert memory[following + 0x58] == value
                assert memory[0xCB:0xCD] == bytes(((low + 1) & 255, high))
                assert cpu.p & cpu.CARRY == (second & 1)
                assert value & 0x20 and 32 <= value & 63 <= 63
                cases += 1
                wraps += low == 255
    return {"pass": True, "cases": cases, "low_pointer_wrap_cases": wraps,
            "domain": "All256×256 neighbour bytes for both possible random seeds; deterministic variation across pointer pages08..0F, lowbyte, bar0..63 and three opcode masks",
            "guarantees": "Stored value nonzero; glyph index32..63 lies in stack-backed font; final carry is second addition lowbit",
            "scope": "One uninterrupted main-loop update, not asynchronous IRQ/pointer races or full visual cadence"}


def main():
    blob = (ROOT / "build/research/frontier/a_mind_is_born.prg").read_bytes()
    assert len(blob) == 256 and sha(blob) == PRG_SHA
    result = {"pass": True, "script_sha256": sha(Path(__file__).read_bytes()),
              "prg_sha256": sha(blob), "py65_version": importlib.metadata.version("py65"),
              "CPU_extensions": "A7/B7 LAX, AB LAXimmediate restricted tooperand0, 4B ALR, 47 SRE, CB AXS",
              "relocation": relocation_proof(blob), "LFSR": lfsr_proof(blob),
              "music": music_proof(blob), "font": font_proof(blob),
              "neighbours": neighbour_proof(blob),
              "scope": "OriginalCPU arithmetic in flatRAM; explicit external read fixtures, noVIC/SID/CIA/ROM/interrupt timing/native rendering"}
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "arithmetic-proof.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
