#!/usr/bin/env python3
"""Assemble an unchanged author example and check bounded scheduling behavior.

This models official 6502 instructions, RAM, and explicit register fixtures.
It does not model VIC timing, IRQ recognition latency, DMA, or RMW bus writes.
"""

from collections import Counter
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import re
import subprocess

from py65.devices.mpu6502 import MPU


ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/research/macro-scheduling"
SOURCE = OUT / "anonymous-irq-handlers-example.s"
SOURCE_SHA = "caa3e48260562636ae1d47c6c3ba18b079b42948666253f41a8ff00dc49b0cee"


def sha(data):
    return hashlib.sha256(data).hexdigest()


class Memory:
    def __init__(self, blob):
        self.data = bytearray(65536)
        base = int.from_bytes(blob[:2], "little")
        self.data[base:base + len(blob) - 2] = blob[2:]
        self.io = {0xD011: 0x9B, 0xD019: 1}
        self.events = []

    def __getitem__(self, address):
        return self.io.get(address, 0) if 0xD000 <= address <= 0xDFFF else self.data[address]

    def __setitem__(self, address, value):
        if 0xD000 <= address <= 0xDFFF:
            self.events.append((address, value))
            self.io[address] = value
        else:
            self.data[address] = value


def assemble():
    assert sha(SOURCE.read_bytes()) == SOURCE_SHA
    java = os.environ.get("JAVA", "/opt/homebrew/opt/openjdk/bin/java")
    jar = Path(os.environ.get("KICKASS_JAR", Path.home() / ".local/share/c64-tools/KickAssembler/KickAss.jar"))
    target = OUT / "example.prg"
    command = [java, "-jar", str(jar), str(SOURCE), "-o", str(target), "-symbolfile"]
    result = subprocess.run(command, cwd=OUT, check=True, capture_output=True, text=True)
    log = result.stdout + result.stderr
    (OUT / "assembly.log").write_text(log)
    symbols = {name: int(address, 16) for name, address in
               re.findall(r"\.label (\w+)=\$([0-9a-f]+)", SOURCE.with_suffix(".sym").read_text())}
    assert symbols == {"sequence": 0x08CA, "pt": 0x090C, "again": 0x08CD,
                       "start": 0x0810, "irq": 0x083F}
    assert sha(SOURCE.read_bytes()) == SOURCE_SHA
    return target.read_bytes(), symbols, dict(command=command, source_modified=False,
                                             source_sha256=SOURCE_SHA,
                                             jar_sha256=sha(jar.read_bytes()),
                                             PRG_bytes=target.stat().st_size,
                                             PRG_sha256=sha(target.read_bytes()))


def sequence_proof(blob, symbols):
    memory = Memory(blob)
    # The original sequence remains unchanged. A separate JSR harness supplies
    # a caller and a bounded return checkpoint outside its loaded address range.
    memory.data[0xC000:0xC004] = bytes((0x20, symbols["sequence"] & 255,
                                     symbols["sequence"] >> 8, 0x00))
    expected = bytearray(memory.data)
    cpu = MPU(memory=memory, pc=0xC000)
    cpu.sp = 0xFD
    cpu.p = 0x20
    phase = count = 0
    phase_entry = True
    cycles = Counter()
    colors = []
    instruction_count = 0
    for invocation in range(1, 1002):
        expected[0x1FD], expected[0x1FC] = 0xC0, 0x02
        switched = count == 100
        expected_events = []
        if switched:
            color = 5 if phase == 0 else 6
            expected_events.append((0xD021, color))
            colors.append(dict(invocation=invocation, color=color))
            phase ^= 1
            phase_entry = True
            count = 0
        nominal_cycles = (60 if phase == 1 else 63) if switched else (47 if phase_entry else 29)
        count += 1
        continuation = (0x08DC, 0x08FA)[phase]
        counter_address = continuation + 1
        expected[counter_address] = count
        expected[0x090C:0x090E] = continuation.to_bytes(2, "little")
        memory.events.clear()
        cpu.pc = 0xC000
        first_cycle = cpu.processorCycles
        for steps in range(1, 100):
            cpu.step()
            instruction_count += 1
            if cpu.pc == 0xC003:
                break
        else:
            raise AssertionError("Original sequence failed to return within 99 instructions")
        assert cpu.sp == 0xFD
        assert memory.data == expected, f"All-RAM sequence mismatch at invocation {invocation}"
        assert memory.events == expected_events
        observed = cpu.processorCycles - first_cycle
        assert observed == nominal_cycles, (invocation, observed, nominal_cycles)
        cycles[observed] += 1
        phase_entry = False
    assert colors == [dict(invocation=101 + 100 * i, color=5 + i % 2) for i in range(10)]
    return dict(pass_=True, calls=1001, instructions=instruction_count,
                physical_RAM_bytes_compared_per_call=65536,
                background_writes=colors,
                nominal_CPU_cycles_including_JSR=dict(sorted(cycles.items())),
                continuation_addresses=[0x08DC, 0x08FA],
                counter_immediate_addresses=[0x08DD, 0x08FB],
                pointer_address=0x090C, caller_stack_pointer=0xFD,
                RAM_final_sha256=sha(memory.data),
                scope="Original source's repeatable two-phase wait; all RAM and literal IO writes match an independent counter model")


def irq_proof(blob, symbols):
    memory = Memory(blob)
    cpu = MPU(memory=memory, pc=symbols["start"])
    cpu.sp = 0xFD
    for startup_steps in range(1, 100):
        cpu.step()
        if cpu.pc == 0x083C:
            break
    else:
        raise AssertionError("Startup did not reach its original idle loop")
    assert memory.data[0xFFFE:0x10000] == symbols["irq"].to_bytes(2, "little")
    assert memory.io[0xD012] == 0 and memory.io[0xD011] == 0x1B
    assert memory.io[0xDC0D] == 0x7F and memory.io[0xD01A] == 1
    assert memory.data[1] == 0x35
    records = []
    for entry in range(16):
        memory.events.clear()
        memory.io[0xD019] = 1
        cpu.irq()
        handler = cpu.pc
        for steps in range(1, 200):
            cpu.step()
            if cpu.pc == 0x083C:
                break
        else:
            raise AssertionError("Original IRQ segment did not return")
        slot = entry % 4
        next_vector = int.from_bytes(memory.data[0xFFFE:0x10000], "little")
        expected_vector = (0x0861, 0x0883, 0x08A5, 0x083F)[slot]
        assert next_vector == expected_vector
        assert memory.events == [(0xD020, (14, 2, 3, 4)[slot]),
                                 (0xD012, (0x40, 0x80, 0xF8, 0)[slot]),
                                 (0xD011, 0x1B), (0xD019, 2)]
        assert cpu.sp == 0xFD and not cpu.p & cpu.INTERRUPT
        records.append(dict(entry=entry + 1, handler=handler,
                            next_handler=next_vector, IO_writes=memory.events.copy(),
                            instructions=steps))
    return dict(pass_=True, startup_instructions=startup_steps,
                synthetic_IRQ_entries=16, complete_handler_chains=4, entries=records,
                scope="Manually injected IRQs exercise original vector chaining/RTI; fixed IO bytes, no raster clock, DMA, acknowledgement bus or pixel model")


def main():
    blob, symbols, assembly = assemble()
    sequence = sequence_proof(blob, symbols)
    irq = irq_proof(blob, symbols)
    receipt = dict(pass_=True, script_sha256=sha(Path(__file__).read_bytes()),
                   py65_version=importlib.metadata.version("py65"), assembly=assembly,
                   sequence=sequence, IRQ=irq,
                   scope="Unchanged standalone teaching source; slides and released-demo implementations are separate evidence")
    receipt["pass"] = receipt.pop("pass_")
    (OUT / "proof.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(dict(pass_=True, assembly=assembly,
                         sequence_calls=sequence["calls"], IRQ_entries=irq["synthetic_IRQ_entries"],
                         nominal_cycles=sequence["nominal_CPU_cycles_including_JSR"]), indent=2))


if __name__ == "__main__":
    main()
