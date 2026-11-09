#!/usr/bin/env python3
"""Typed original Sparkle disk-to-packet transport; no CPU or timing model."""
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import tarfile

ROOT = Path(__file__).resolve().parents[2]
OLD = ROOT / 'build/research/aloft-20261109'
BASE = ROOT / 'build/research/aloft-decode-20261109/block-analysis'
SOURCE = OLD / 'loader-analysis/catalog-source-02'
CATALOG_SOURCE = ROOT / 'research/aloft-20261109/catalog.py'
CATALOG_SHA = 'd7a0785fec84a3bfdd3d7eec1dadc16b40540dcaceaf0101bca4dee5ba4fd497'
CATALOG_PROOF = OLD / 'loader-analysis/catalog-accepted-01/catalog-proof.json'
CATALOG_PROOF_SHA = 'a8109b96af82701bf61af84e7b054e8fff8048b1efcfefe52c631e54ee88f2b4'
DISK_PROOF = OLD / 'disk-analysis/accepted-01/disk-proof.json'
DISK_PROOF_SHA = '113eadc069fbf46bb1011d7c9373d175f4c3536950f7a7ee173f471b8f1eef84'
SOURCE_PINS = {
    'sd.cpp': '0e28b8eb743494fab9ad6f914f047d05f4b729c4cc000820267172951ef06537',
    'resources__sd.asm': '7d6b673ff21f6efef523e04d9fb46a53eb05852d4a7182109365d33af684510a',
    'resources__sl.asm': '46b28b74e9d2528b808e0c3fd0df08ef0ce7537d4a143527932bee46d9dcab60',
    'packer.cpp': 'bb60128abbe2c5af5f3a1965f7ea66a5f4ef3bcb2523b2a8324758555bb32a6a',
}
VICE_ARCHIVE = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
VICE_SHA = '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'
VICE_MEMBERS = {
    'gcr.c': 'vice-3.10/src/gcr.c',
    'c64cia2.c': 'vice-3.10/src/c64/c64cia2.c',
    'via1d1541.c': 'vice-3.10/src/drive/iec/via1d1541.c',
    'c64iec.c': 'vice-3.10/src/c64/c64iec.c',
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def meta(path):
    data = path.read_bytes()
    return {'path': str(path.relative_to(ROOT)), 'bytes': len(data), 'sha256': sha(data)}


def pinned(path, expected):
    data = path.read_bytes()
    assert sha(data) == expected, str(path)
    return data


def encode(value):
    return (json.dumps(value, sort_keys=True, indent=2) + '\n').encode()


def catalog_module():
    pinned(CATALOG_SOURCE, CATALOG_SHA)
    spec = importlib.util.spec_from_file_location('frozen_aloft_catalog', CATALOG_SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def cia_input(c64_written, drive_written):
    """Settled IEC pins for these source-used writes, not a bus time model.

    One active 1541, configured DDRA=$3C. Formula follows the pinned VICE
    c64iec/via1d1541 port equations; only high input bits are consumed.
    """
    cpu_data = (~c64_written) & 255
    cpu_bus = ((cpu_data << 2) & 0xC0) | ((cpu_data << 1) & 0x10)
    drive_data = (~drive_written) & 255
    drive_bus = ((drive_data << 3) & 0x40) | (
        (drive_data << 6) & (((~drive_data) ^ cpu_bus) << 3) & 0x80)
    return cpu_bus & drive_bus & 0xC0


def transfer_byte(drive_value):
    """Four typed source transfer phases composed with the C64 receiver."""
    assert 0 <= drive_value < 256
    # Source W1/W2/W3/W4 expressions after SAX/ASL+ORA/ROR+ALR/LSR+ALR.
    writes = [drive_value & 0xEF, ((drive_value << 1) | 0x10) & 255,
              (drive_value & 0xF0) >> 1, (drive_value & 0xC0) >> 3]
    reads = [cia_input(cpu, drv) for cpu, drv in zip([0x00, 0x08, 0xC0, 0x08], writes)]
    # Read1 and Read2/3 are combined then shifted twice at each source stage;
    # Read4 is masked by C0 before the saved low six bits are ORed back.
    result = ((reads[0] >> 6) | (reads[1] >> 4) | (reads[2] >> 2) | reads[3]) & 255
    return result, writes, reads


def gcr_lane_values(value, gcr, sd):
    """Four high-level table expressions from source GCR loop A/B..G/H.

    The standard encoded nibbles are inputs. No CPU instruction is stepped;
    all four lanes independently use their original concrete lookup tables.
    """
    high, low = gcr[value >> 4], gcr[value & 15]
    zp = sd[0x400:0x500]
    # A/B: SBC from the source constant7, its two ALR masks and split indices.
    y_ab = ((7 - ((high << 3) | (low >> 2))) & 0xF8) >> 1
    x_ab = ((low & 3) << 5) | (7 - (low >> 2))
    ab = sd[0x12 + y_ab] ^ sd[x_ab]
    cd = zp[high << 1] ^ sd[1 + (low << 3)]
    ef = (zp[high >> 1] + zp[1 + ((high & 1) << 6) + (low << 1)]) & 255
    gh = sd[0x100 + (high >> 3) + ((high & 7) << 4)] ^ sd[0x1E + low]
    return [ab, cd, ef, gh]


class DiskStream:
    """Canonical source-valid packet provider, independent of native RAM.

    Ascending writer order is selected explicitly. Normal packets can arrive
    out of order in the real drive; no equality across all orders is asserted.
    Indexed first packets are forced first, and transition packets are last
    in their current transfer group. Packet requests continue only on demand.
    """
    def __init__(self, d64, slot, side=1):
        self.cat = catalog_module()
        self.data = bytes(d64)
        assert len(self.data) == 174848 and 0 <= slot < 128 and 1 <= side <= 3
        self.side, self.slot = side, slot
        bam = self.cat.sector(self.data, 18, 0)
        interleaves = [(-self.cat.transform(bam[i])) & 255 for i in [0xFA, 0xFC, 0xFD, 0xFE]]
        self.table = self.cat.calc_tabs(interleaves)
        directory = b''.join(self.cat.reverse_sector(self.cat.sector(self.data, 18, s)) for s in [17, 18])
        entry = directory[slot * 4:slot * 4 + 4]
        track, start, remaining = [self.cat.transform(v) for v in entry[:3]]
        assert track & 0xC0 == 0, 'plugin transport is outside this compressed-packet contract'
        hits = [r for r in self.table if (r['track'], r['start_sector_on_track'],
                r['remaining_sectors_on_track']) == (track, start, remaining)]
        assert len(hits) == 1
        self.first_ordinal = hits[0]['block_ordinal']
        self.ordinal = self.first_ordinal
        self.pointer = entry[3]
        self.sequence = 0
        self.terminal = None
        self.exhausted = False
        self.history = []

    def next_packet(self):
        if self.exhausted or self.ordinal >= len(self.table):
            raise StopIteration('No further source-derived compressed packet available')
        row = self.table[self.ordinal]
        raw_sector = self.cat.sector(self.data, row['track'], row['sector'])
        packet = bytearray(self.cat.reverse_sector(raw_sector))
        first = self.sequence == 0
        transition = first or self.ordinal == self.terminal
        patches = []
        next_count = None
        if transition:
            # Raw logical byte1 was host-EOR encoded. GCR f() makes it the
            # numeric drive NBC; the 7F drive replacement transfers as zero.
            next_count = self.cat.transform(packet[1])
            patches.append({'offset': 1, 'raw_received_value': packet[1], 'received_value': 0,
                            'meaning': 'drive saves NBC, replaces count by drive7F→C64zero'})
            packet[1] = 0
        if first:
            patches.extend([
                {'offset': 0, 'raw_received_value': packet[0], 'received_value': 0,
                 'meaning': 'indexed entry forces Buffer0 fallback'},
                {'offset': 255, 'raw_received_value': packet[255], 'received_value': self.pointer,
                 'meaning': 'directory raw pointer→GCRf(BPtr)→driveFF→wiref→raw pointer'},
            ])
            packet[0], packet[255] = 0, self.pointer
        source = {
            'side': self.side, 'indexed_slot': self.slot, 'packet_sequence': self.sequence,
            'track': row['track'], 'sector': row['sector'], 'writer_block_ordinal': self.ordinal,
            'raw_sector_sha256': sha(raw_sector),
            'raw_logical_packet_sha256': sha(self.cat.reverse_sector(raw_sector)),
            'delivery_order': 'chosen ascending source writer ordinal; real rotational order unresolved',
            'indexed_first': first, 'count_transition': transition, 'saved_next_block_count_NBC': next_count,
            'patches': patches,
            'raw_disk_offset_for_received_index': 'sector_start + ((-received_index) & 255)',
        }
        if transition:
            self.terminal = self.ordinal + next_count if next_count else None
            source['next_transition_writer_ordinal'] = self.terminal
            self.exhausted = next_count == 0
        self.sequence += 1
        self.ordinal += 1
        self.history.append(source)
        return {'received': bytes(packet), 'source': source}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to(BASE) and not out.exists()
    out.mkdir(parents=True)
    catalog_proof = json.loads(pinned(CATALOG_PROOF, CATALOG_PROOF_SHA))
    disk_proof = json.loads(pinned(DISK_PROOF, DISK_PROOF_SHA))
    assert catalog_proof['pass_'] and disk_proof['pass_']
    texts = {name: pinned(SOURCE / name, digest).decode() for name, digest in SOURCE_PINS.items()}
    cat = catalog_module()
    sd = cat.array(texts['sd.cpp'], 'sd')
    assert len(sd) == 1427
    pinned(VICE_ARCHIVE, VICE_SHA)
    source_dir = BASE / 'source-01'
    members = json.loads((source_dir / 'source-members.json').read_bytes())
    assert {r['name']: r['member'] for r in members} == VICE_MEMBERS
    with tarfile.open(VICE_ARCHIVE) as archive:
        for r in members:
            data = (source_dir / r['name']).read_bytes()
            assert len(data) == r['bytes'] and sha(data) == r['sha256']
            assert archive.extractfile(r['member']).read() == data
    via = (source_dir / 'via1d1541.c').read_text()
    iec = (source_dir / 'c64iec.c').read_text()
    cia = (source_dir / 'c64cia2.c').read_text()
    assert '*drive_data = ~byte;' in via
    assert '((uint32_t)(~(*drive_data) ^ iecbus->cpu_bus) << 3) & 0x80' in via
    assert 'iecbus.cpu_bus = (((data << 2) & 0x80) | ((data << 2) & 0x40) | ((data << 1) & 0x10));' in iec
    assert 'tmp = (uint8_t)~byte;' in cia
    assert 'value = ((cia_context->c_cia[CIA_PRA] | ~(cia_context->c_cia[CIA_DDRA])) & 0x3f);' in cia
    gcr_text = (source_dir / 'gcr.c').read_text()
    gcr_array = re.search(r'GCR_conv_data\[16\]\s*=\s*\{(.*?)\};', gcr_text, re.S)
    assert gcr_array
    gcr = [int(v, 16) for v in re.findall(r'0x([0-9a-fA-F]+)', gcr_array[1])]
    assert len(gcr) == 16
    sd_text, sl_text = texts['resources__sd.asm'], texts['resources__sl.asm']
    for clause in ['sta (ZP0101),y', 'sta (ZP0100),y', 'sta (ZP01ff),y',
                   'lda BPtr', 'sta NBC', 'inc ScndBuff', 'dec BlockCtr', 'lda NBC']:
        assert clause in sd_text
    assert 'Data Code - SP = $00 here' in sd_text
    for clause in ['sta Buffer,x', 'sta LastBits+1', 'ora $dd00', 'and $dd00']:
        assert clause in sl_text
    finite = []
    for v in range(256):
        transformed = cat.transform(v)
        lanes = gcr_lane_values(v, gcr, sd)
        assert lanes == [transformed] * 4
        received, writes, reads = transfer_byte(transformed)
        assert received == v
        assert transfer_byte(v)[0] == transformed
        finite.append({'disk_byte': v, 'four_GCR_lanes': lanes, 'drive_value': transformed,
                       'four_drive_port_writes': writes, 'four_CIA_high_inputs': reads,
                       'received_byte': received})
    (out / 'byte-transport-domain.json').write_bytes(encode(finite))
    plans = []
    # A bounded export: initial index0 and source-bound indexed slot5. Slot5's
    # source counter is70, so its first transfer group contains71 packets.
    for slot in [0, 5]:
        dpath = OLD / 'disk-analysis/accepted-01/Aloft-Side1.d64'
        data = dpath.read_bytes()
        disk_meta = next(r for r in disk_proof['outputs'] if r['name'] == dpath.name)
        assert sha(data) == disk_meta['sha256']
        provider = DiskStream(data, slot)
        packet_rows = []
        first_terminal = None
        while first_terminal is None or provider.ordinal <= first_terminal:
            result = provider.next_packet()
            if first_terminal is None:
                first_terminal = provider.terminal
                assert first_terminal is not None
            name = f'side1-slot{slot:03d}-packet{len(packet_rows):03d}.bin'
            (out / name).write_bytes(result['received'])
            packet_rows.append({'path': name, 'bytes': 256, 'sha256': sha(result['received']),
                                'source': result['source']})
        plan = {
            'schema': 'sparkle-received-packets-v1', 'side': 1, 'indexed_slot': slot,
            'D64': meta(dpath), 'packets': packet_rows,
            'scope': 'indexed first packet through first following count-transition packet',
            'delivery_order': 'canonical writer ordinal; actual rotational order unresolved',
            'first_transition_ordinal': first_terminal,
            'next_transition_ordinal': provider.terminal,
            'limits': ['No resource end or token decoding is inferred from packet count.',
                       'No native packet bytes are inputs or validation oracles in this static proof.',
                       'Alternative legal packet orders are not asserted output-equivalent.'],
        }
        plan_name = f'side1-slot{slot:03d}-plan.json'
        (out / plan_name).write_bytes(encode(plan))
        plans.append({'name': plan_name, 'packets': len(packet_rows),
                      'first_transition_ordinal': first_terminal,
                      'last_packet_sha256': packet_rows[-1]['sha256']})
    assert [r['packets'] for r in plans] == [2, 71]
    (out / 'disk_stream.checked.py').write_bytes(Path(__file__).read_bytes())
    proof = {
        'pass_': True, 'scope': 'Source-derived disk bytes→canonical deposited C64 packets; no token/CPU/timing execution',
        'producer': meta(Path(__file__).resolve()),
        'inputs': [meta(CATALOG_SOURCE), meta(CATALOG_PROOF), meta(DISK_PROOF), meta(VICE_ARCHIVE),
                   *[meta(SOURCE / name) for name in SOURCE_PINS],
                   *[meta(source_dir / r['name']) for r in members], meta(source_dir / 'source-members.json')],
        'source_contract': {
            'writer_byte_permutation_packer_lines': [99, 127],
            'directory_random_entry_drive_lines': [907, 963],
            'count_and_indexed_packet_patches_drive_lines': [832, 857],
            'secondary_buffer_and_count_update_drive_lines': [1186, 1225],
            'four_transfer_phases_drive_lines': [1117, 1154],
            'four_receiver_phases_resident_lines': [327, 355],
            'GCR_data_stack_entry_drive_lines': [519, 563],
            'GCR_table_decode_drive_lines': [1381, 1455],
            'official_GCR_conversion_lines': [51, 84],
            'official_CIA_input_lines': [200, 214],
            'official_CIA_output_inversion_lines': [151, 163],
            'official_IEC_CPU_bus_lines': [121, 124],
            'official_VIA_output_lines': [212, 242],
            'actual_rotational_order': 'not derivable uniquely from disk alone; OOO fetch is deliberate',
        },
        'finite_domain': {'bytes': 256, 'GCR_lanes_checked': 1024,
                          'all_raw_bytes_roundtrip': True, 'transfer_f_involution': True},
        'plans': plans,
        'outputs': [{'name': f.name, 'bytes': f.stat().st_size, 'sha256': sha(f.read_bytes())}
                    for f in sorted(out.iterdir())],
        'limits': [
            'Only the two declared indexed starts and their first transfer groups are exported, not all resources.',
            'The real drive can transfer ordinary wanted sectors out of order; canonical ascending order is explicit.',
            'Token match dependencies must be checked by the separate decoder; no all-order equivalence is asserted.',
            'Indexed first and terminal packets clear count byte1; ordinary packet byte1 is data and remains unchanged.',
            'Native RAM, decompressed resources and received-packet captures never seed this model.',
            'VIA/CIA equations describe successful settled handshakes for one active1541 and source DDRA3C; no cycle or analog electrical model.',
        ],
    }
    (out / 'block-proof.json').write_bytes(encode(proof))
    print(json.dumps({'pass_': True, 'packets': 73, 'finite_GCR_cases': 1024,
                      'proof': str(out / 'block-proof.json')}))


if __name__ == '__main__':
    main()
