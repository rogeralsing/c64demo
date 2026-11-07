#!/usr/bin/env python3
"""Re-encode the released D64 sectors to GCR and reconstruct Freespin parts.

Pure offline data translation. Uses the released loader's literal ADC constants
and carry chain, independently checked by validate_decoder.py. No disk timing,
drive emulation, downloaded host-code execution, or VICE process.
"""

import hashlib
import json
from collections import Counter
from functools import reduce
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
ROOT = REPOSITORY / "build/research/freespin"
GCR = (0x0A, 0x0B, 0x12, 0x13, 0x0E, 0x0F, 0x16, 0x17,
       0x09, 0x19, 0x1A, 0x1B, 0x0D, 0x1D, 0x1E, 0x15)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def track_size(track):
    return 21 if track <= 17 else 19 if track <= 24 else 18 if track <= 30 else 17


def sector(disk, track, number):
    assert 1 <= track <= 35 and 0 <= number < track_size(track)
    offset = (sum(track_size(t) for t in range(1, track)) + number) * 256
    return disk[offset:offset + 256]


def gcr_body(data):
    logical = bytes((7,)) + data + bytes((reduce(int.__xor__, data), 0, 0))
    encoded = 0
    for value in logical:
        encoded = (encoded << 10) | (GCR[value >> 4] << 5) | GCR[value & 15]
    return encoded.to_bytes(325, "big")


def adc(a, b, carry):
    total = a + b + carry
    return total & 255, int(total > 255)


def decode_payload(raw, constants):
    """Original read_block arithmetic; payload writes descend from dst+207."""
    c0, c1, c2, c3 = constants
    result = bytearray(208)
    carry, y = 0, 208
    events = []
    for index in range(7, 319, 3):
        a, carry = adc(raw[index], c1, carry)
        p1 = a
        p2, carry = adc(a, c3, carry)
        y -= 1
        a, carry = adc(c0, raw[index + 1], carry)
        result[y] = a ^ p1
        events.append((y, result[y]))
        a, carry = adc(raw[index + 2], c2, carry)
        y -= 1
        result[y] = a ^ p2
        events.append((y, result[y]))
    assert y == 0
    return bytes(result), events, carry


def xor_coverage():
    pairs = set()
    for a in GCR:
        for b in GCR:
            for c in GCR:
                for d in GCR:
                    bits = (a << 15) | (b << 10) | (c << 5) | d
                    pairs.add((bits >> 12, (bits >> 4) & 255))
    counts = Counter(a ^ b for a, b in pairs)
    assert len(pairs) == 8192 and set(counts) == set(range(256))
    return {"valid_raw_byte_pairs": len(pairs), "decoded_values": len(counts),
            "minimum_encodings_per_value": min(counts.values()), "maximum_encodings_per_value": max(counts.values()),
            "scope": "All standard GCR nibble quadruples, first sixteen encoded bits; full set, not a selected subset"}


def extract_bootstrap(disk):
    track, number = 18, 1
    files = []
    while track:
        data = sector(disk, track, number)
        for entry in range(8):
            offset = entry * 32
            if data[offset + 2] & 7 != 2:
                continue
            name = data[offset + 5:offset + 21].rstrip(bytes((160,))).decode("ascii", errors="replace")
            current, part_sector = data[offset + 3:offset + 5]
            payload, chain, seen = bytearray(), [], set()
            while current:
                assert (current, part_sector) not in seen
                seen.add((current, part_sector))
                chain.append([current, part_sector])
                block = sector(disk, current, part_sector)
                current, part_sector = block[:2]
                payload.extend(block[2:] if current else block[2:part_sector + 1])
            target = ROOT / "bootstrap.prg"
            target.write_bytes(payload)
            files.append({"name": name, "sector_chain": chain, "bytes": len(payload),
                          "sha256": digest(payload), "prg_load": int.from_bytes(payload[:2], "little")})
        track, number = data[:2]
    return files


def main():
    disk = (ROOT / "freespin.d64").read_bytes()
    assert len(disk) == 174848 and digest(disk) == "7798f74046ee767a2e05e4e05c12e7b7453640c579ebc3d5daed20ce019f890c"
    released = sector(disk, 18, 18)[2:]
    assert len(released) == 254
    assert released[:18] == bytes.fromhex("a9 64 8d 00 1c a9 6f 8d 02 1c 8d 0c 1c a9 41 8d 0b 1c")
    assert released[-3:] == bytes(3)
    published = (ROOT / "loader-published-20000.prg").read_bytes()
    assert published[:2] == bytes((2, 7)) and len(published) == 246
    published = published[2:]
    split = 0x7C1 - 0x702
    assert released[:split] == published[:split]
    assert released[split:split + 7] == bytes.fromhex("e9 33 b0 fc 88 d0 f9")
    assert released[split + 7:-3] == published[split:]
    assert released[0x733 - 0x702] == 0x4E and released[0x735 - 0x702] == 0x1E
    constants = [released[address - 0x702] for address in (0x78C, 0x77F, 0x79B, 0x783)]
    assert constants == [80, 133, 102, 68]
    (ROOT / "loader-release.bin").write_bytes(released)
    parts = ROOT / "parts"
    parts.mkdir(exist_ok=True)
    records, all_blocks = [], []
    # Tracks 1..17 have a coherent next-loader prefix under these released
    # constants. Other custom-looking tracks are not promoted to decoded code.
    for track in range(1, 18):
        blocks = {}
        for number in range(track_size(track)):
            data = sector(disk, track, number)
            raw = gcr_body(data)
            assert raw[0] == 0x55
            identity = raw[1] ^ raw[2]
            destination = ((raw[3] ^ raw[4]) << 8) | (raw[5] ^ raw[6])
            assert 1 <= identity <= 9 and destination == 0x10 + (identity - 1) * 208
            decoded, _, _ = decode_payload(raw, constants)
            if identity in blocks:
                assert blocks[identity]["decoded"] == decoded, (track, number, identity)
                assert blocks[identity]["raw"] == raw, "Redundant sector copies must be byte-identical here"
                blocks[identity]["copies"].append(number)
            else:
                blocks[identity] = {"decoded": decoded, "raw": raw, "destination": destination, "copies": [number]}
        assert set(blocks) == set(range(1, 10))
        memory, known = bytearray(2048), bytearray(2048)
        memory[0x702:] = released
        known[0x702:] = bytes((1,)) * 254
        for identity, block in sorted(blocks.items()):
            prefix = f"track{track:02}-block{identity}"
            (parts / (prefix + ".gcr.bin")).write_bytes(block["raw"])
            (parts / (prefix + ".decoded.bin")).write_bytes(block["decoded"])
            destination = block["destination"]
            memory[destination:destination + 208] = block["decoded"]
            known[destination:destination + 208] = bytes((1,)) * 208
            all_blocks.append({"track": track, "block": identity, "destination": destination,
                               "copies": block["copies"], "raw_sha256": digest(block["raw"]),
                               "decoded_sha256": digest(block["decoded"]), "prefix": "parts/" + prefix})
        # Every reconstructed part preserves this independently identified
        # released loader prefix, apart from its deliberately new motor value.
        changed = [i for i in range(94) if memory[0x702 + i] != released[i]]
        assert set(changed) <= {1}, (track, changed)
        entry = int.from_bytes(memory[0x700:0x702], "little")
        assert 0x10 <= entry < 0x702, (track, hex(entry))
        (parts / f"track{track:02}.memory.bin").write_bytes(memory)
        (parts / f"track{track:02}.known.bin").write_bytes(known)
        records.append({"track": track, "entry": entry, "memory_sha256": digest(memory),
                        "effect_data_sha256": digest(memory[0x10:0x700]),
                        "loader_next_1c00": memory[0x703], "overwritten_loader_prefix_bytes": 94,
                        "prefix_except_motor_matches_release": True,
                        "sector_copies_per_block": {str(i): len(blocks[i]["copies"]) for i in sorted(blocks)}})
    report = {"pass": True, "scope": "Offline D64-to-GCR data reconstruction; no drive timing or native execution",
              "script_sha256": digest(Path(__file__).read_bytes()), "disk_sha256": digest(disk),
              "loader_source_published_sha256": digest((ROOT / "loader-published.asm").read_bytes()),
              "loader_release_sha256": digest(released), "loader_release_track_sector": [18, 18],
              "loader_release_capacity_bytes": 254, "loader_release_executable_bytes": 251,
              "loader_published_executable_bytes": 244, "release_extra_delay": "e9 33 b0 fc 88 d0 f9",
              "frame_cycles_from_released_timer_immediates": 20000,
              "decoder_constants_c0_c1_c2_c3": constants, "payload_write_range_end_exclusive": [0x10, 0x760],
              "xor_2to1_coverage": xor_coverage(), "bootstrap_files": extract_bootstrap(disk),
              "tracks_reconstructed": len(records), "unique_blocks": len(all_blocks),
              "physical_sector_copies": sum(len(block["copies"]) for block in all_blocks),
              "all_redundant_sector_copies_byte_identical": True,
              "decoded_unique_output_bytes": 208 * len(all_blocks), "tracks": records, "blocks": all_blocks,
              "limitations": ["No physical GCR sync/header/rotation/IEC validation",
                              "Payload arithmetic awaits independent original-CPU validation",
                              "Secondary custom-looking tracks19..34 not identified under this loader state",
                              "No effect framebuffer, analog video, mechanics or complete performance proof"]}
    (ROOT / "decoded-index.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({key: value for key, value in report.items() if key not in ("tracks", "blocks", "bootstrap_files")}, indent=2))


if __name__ == "__main__":
    main()
