#!/usr/bin/env python3
"""Compare Tower Power's offline decoder with its original 6502 depacker.

This executes original C64 instructions in py65 with one mocked disk-block
receive boundary at $c18f. It is NOT native disk, IEC, drive, VIC, or VICE proof.
The original raw-byte reader ($c139) and LSB-bit reader ($c156) execute unchanged.

Value: CPU-produced destination/value events independently check the Python
translation's bit order, eager refill, dispatch, length and back-reference logic.
The translation cannot independently establish those properties by decoding its
own outputs. No production seam or renderer change is required.
"""

import argparse
import hashlib
import importlib.metadata
import importlib.util
import json
from pathlib import Path

from py65.devices.mpu6502 import MPU


REPOSITORY = Path(__file__).resolve().parents[2]
ENTRY = 0xC023
END_RETURN = 0xC09A
RAW_LOAD = 0xC151
OUTPUT_STORE = 0xC12E
MATCH_LOAD = 0xC0B1
BLOCK_RECEIVE = 0xC18F
STOP = 0x02FF
BLOCK_SIZE = 254


def digest(data):
    return hashlib.sha256(data).hexdigest()


def artifact(path):
    path = Path(path)
    return path if path.is_absolute() else REPOSITORY / path


def ranges(bitmap):
    result = []
    start = None
    for address, value in enumerate([*bitmap, 0]):
        if value and start is None:
            start = address
        if not value and start is not None:
            result.append([start, address])
            start = None
    return result


class ObservedMemory:
    """Flat RAM plus observation of actual CPU stores at the output instruction."""

    def __init__(self, initial):
        self.ram = bytearray(initial)
        self.pc = None
        self.output = bytearray(65536)
        self.written = bytearray(65536)
        self.trace = bytearray()
        self.other_writes = set()

    def __getitem__(self, address):
        return self.ram[address]

    def __setitem__(self, address, value):
        self.ram[address] = value
        if self.pc == OUTPUT_STORE:
            self.trace.extend((address & 255, address >> 8, value))
            self.output[address] = value
            self.written[address] = 1
        else:
            self.other_writes.add(address)


class CpuDecoder:
    def __init__(self, blob, initial, max_steps):
        self.blob = blob
        self.memory = ObservedMemory(initial)
        self.cpu = MPU(memory=self.memory, pc=ENTRY)
        self.cpu.p = self.cpu.UNUSED | self.cpu.INTERRUPT  # binary arithmetic
        self.cpu.sp = 255
        self.cpu.stPushWord(STOP - 1)
        self.memory.other_writes.clear()
        self.block_start = 0
        self.block_refills = 0
        self.raw_offsets = []
        self.back_reference_reads = 0
        self.max_steps = max_steps
        self.steps = 0
        self.last_pc = None
        self.refill_carries = set()
        self.fill_block()

    def fill_block(self):
        payload = self.blob[self.block_start:self.block_start + BLOCK_SIZE]
        if not payload:
            raise EOFError(f"Block receive after encoded file at {self.block_start}")
        # The first block includes the two opaque file-prefix bytes. The original
        # entry's X=4 skips those two bytes; no load-address meaning is assumed.
        self.memory.ram[0xC302:0xC400] = payload.ljust(BLOCK_SIZE, b"\x00")

    def receive_mock(self):
        """Only replace external block receive, inside C139's PHP/PLP wrapper.

        Preserve A/X/Y/P; perform the RTS stack effect. C139 restores Y and
        sets X=2 after returning, so these preserved registers are sufficient.
        The CPU, not this hook, executes that restoration and every raw load.
        """
        cpu = self.cpu
        before = (cpu.a, cpu.x, cpu.y, cpu.p, cpu.sp)
        self.refill_carries.add(cpu.p & cpu.CARRY)
        self.block_start += BLOCK_SIZE
        self.fill_block()
        self.block_refills += 1
        cpu.pc = (cpu.stPopWord() + 1) & 65535
        assert (cpu.a, cpu.x, cpu.y, cpu.p) == before[:4]
        assert cpu.sp == (before[4] + 2) & 255
        assert cpu.pc == 0xC147, "Unexpected caller of mocked block receive"

    def run(self):
        cpu, memory = self.cpu, self.memory
        while cpu.pc != STOP:
            if self.steps >= self.max_steps:
                raise RuntimeError(f"Instruction limit at ${cpu.pc:04x}")
            if cpu.pc == BLOCK_RECEIVE:
                self.receive_mock()
                continue
            if not ENTRY <= cpu.pc <= 0xC177:
                raise RuntimeError(f"Unexpected original-code execution at ${cpu.pc:04x}")
            pc = cpu.pc
            memory.pc = pc
            if pc == RAW_LOAD:
                assert 2 <= cpu.x <= 255
                offset = self.block_start + cpu.x - 2
                if not 2 <= offset < len(self.blob):
                    raise EOFError(f"Original raw reader reads file offset {offset}")
                self.raw_offsets.append(offset)
                assert memory.ram[0xC300 + cpu.x] == self.blob[offset]
            if pc == MATCH_LOAD:
                source = ((memory.ram[0xFB] | memory.ram[0xFC] << 8) + cpu.y) & 65535
                if not memory.written[source]:
                    raise RuntimeError(f"Original CPU reads an unwritten back-reference at ${source:04x}")
                self.back_reference_reads += 1
            self.last_pc = pc
            cpu.step()
            self.steps += 1
        assert self.last_pc == END_RETURN and cpu.sp == 255
        assert self.raw_offsets == list(range(2, len(self.blob))), "Encoded bytes not consumed exactly once"
        return self


def load_translation(path):
    spec = importlib.util.spec_from_file_location("tower_offline_decoder_under_review", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.Decoder


def translated_trace(decoder_class, blob):
    """Observe the existing translation without editing its implementation."""
    trace = bytearray()

    class ObservedDecoder(decoder_class):
        def put(self, value, known=True):
            trace.extend((self.destination & 255, self.destination >> 8, value))
            super().put(value, known)

    decoder = ObservedDecoder(blob)
    decoder.run()
    return decoder, trace


def first_difference(a, b):
    return next((i for i, (x, y) in enumerate(zip(a, b)) if x != y), min(len(a), len(b)))


def validate(row, initial, decoder_class, directory, max_steps):
    source = artifact(row["source"])
    blob = source.read_bytes()
    assert digest(blob) == row["source_sha256"], "Encoded input changed since static index"
    assert row["pass"] and row["unknown_output_bytes"] == 0
    cpu = CpuDecoder(blob, initial, max_steps).run()
    translated, trace = translated_trace(decoder_class, blob)
    original = cpu.memory
    if original.trace != trace:
        offset = first_difference(original.trace, trace)
        raise AssertionError(f"Chronological destination/value trace differs at byte {offset}, event {offset // 3}")
    assert original.output == translated.memory
    assert original.written == translated.written
    assert ranges(original.written) == row["ranges"]
    assert len(original.trace) // 3 == translated.total == row["output_bytes"]
    assert translated.pos == row["consumed"] == len(blob)
    assert digest(original.output) == row["memory_sha256"]
    prefix = artifact(row["output_prefix"])
    assert original.output == Path(str(prefix) + ".memory.bin").read_bytes()
    assert original.written == Path(str(prefix) + ".known.bin").read_bytes()
    # Only the original length routine's immediate addend may change here.
    for address in range(ENTRY, 0xC178):
        if address != 0xC11B:
            assert original.ram[address] == initial[address], f"Depacker changed at ${address:04x}"
    name = prefix.name
    (directory / (name + ".writes.bin")).write_bytes(original.trace)
    (directory / (name + ".output.bin")).write_bytes(original.output)
    (directory / (name + ".written.bin")).write_bytes(original.written)
    return {
        "source": str(source.relative_to(REPOSITORY)), "source_sha256": digest(blob),
        "pass": True, "encoded_bytes": len(blob), "raw_bytes_read": len(cpu.raw_offsets),
        "block_refills": cpu.block_refills, "refill_entry_carries_seen": sorted(cpu.refill_carries),
        "instructions_executed": cpu.steps, "back_reference_reads": cpu.back_reference_reads,
        "output_events": len(original.trace) // 3, "distinct_output_addresses": sum(original.written),
        "ranges": ranges(original.written), "output_sha256": digest(original.output),
        "chronological_writes_sha256": digest(original.trace),
        "chronological_trace_format": "repeated destination_lo,destination_hi,value",
        "static_artifacts_match": True, "offline_translation_events_match": True,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=REPOSITORY / "build/research/tower-power")
    parser.add_argument("--output", type=Path, help="Defaults to ROOT/cpu-validation")
    parser.add_argument("--limit", type=int, help="Diagnostic subset; receipt will not claim full inventory")
    parser.add_argument("--max-steps", type=int, default=5_000_000, help="Per-stream original instruction limit")
    args = parser.parse_args()
    root = args.root.resolve()
    directory = args.output or root / "cpu-validation"
    directory.mkdir(parents=True, exist_ok=True)
    loader_path = root / "static/loader-c000.bin"
    live_path = root / "live-01/ram-loader-init.bin"
    index_path = root / "static/unpacked-index.json"
    translation_path = Path(__file__).with_name("unpack_stream.py")
    loader, initial = loader_path.read_bytes(), bytearray(live_path.read_bytes())
    assert len(loader) == 1280 and len(initial) == 65536
    assert initial[0xC000:0xC500] == loader, "Static loader differs from original live RAM"
    items = json.loads(index_path.read_text())
    assert len(items) == 42
    decoder_class = load_translation(translation_path)
    results = []
    for row in items[:args.limit] if args.limit is not None else items:
        try:
            result = validate(row, initial, decoder_class, directory, args.max_steps)
        except Exception as exc:
            result = {"source": row["source"], "pass": False,
                      "error": f"{type(exc).__name__}: {exc}"}
        results.append(result)
        print(json.dumps({k: result[k] for k in ("source", "pass", "output_events", "error") if k in result}), flush=True)
    receipt = {
        "pass": all(row["pass"] for row in results), "full_inventory": len(results) == 42,
        "scope": "Original 6502 depacker execution with mocked C18F block input; not native disk or VICE proof",
        "py65_version": importlib.metadata.version("py65"),
        "validator_sha256": digest(Path(__file__).read_bytes()),
        "offline_decoder_sha256": digest(translation_path.read_bytes()),
        "loader_sha256": digest(loader), "live_ram_sha256": digest(live_path.read_bytes()),
        "index_sha256": digest(index_path.read_bytes()),
        "original_depacker_live_static_match": True,
        "cpu_entry": ENTRY, "original_return": END_RETURN,
        "mocked_entry": BLOCK_RECEIVE, "mock_return": 0xC147,
        "unmodified_raw_reader": 0xC139, "unmodified_bit_reader": 0xC156,
        "mock_contract": "254 raw file bytes to C302..C3FF; preserve A/X/Y/P; RTS stack effect only",
        "initial_prefix": "First two encoded file bytes remain opaque; original X=4 skips them",
        "comparison": "Every actual output store address/value in order, final output, output-address set, consumption",
        "streams_checked": len(results), "streams_expected": 42,
        "total_instructions": sum(row.get("instructions_executed", 0) for row in results),
        "total_output_events": sum(row.get("output_events", 0) for row in results),
        "limitations": ["No IEC/1541/disk-sector transport validation", "No interrupts, banking or C64 IO emulated",
                        "Output comparison is flat RAM, not hardware-visible rendering", "No timing-performance conclusion"],
        "streams": results,
    }
    (directory / "validation.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps({k: receipt[k] for k in ("pass", "full_inventory", "streams_checked", "total_instructions", "total_output_events")}))
    raise SystemExit(0 if receipt["pass"] else 1)


if __name__ == "__main__":
    main()
