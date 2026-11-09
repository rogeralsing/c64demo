#!/usr/bin/env python3
"""Source-only four-bit ColorRAM adapter around the frozen Sparkle decoder.

Only device ColorRAM low bits are modelled. Unknown read high bits remain
explicitly partial and may reach only a sink whose required bits are known.
No native RAM or device state seeds prediction; no CPU code is executed.
"""
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
BASE = ROOT / 'build/research/aloft-decode-20261109/color-analysis'
MODEL = ROOT / 'research/aloft-decode-20261109/depacker.py'
MODEL_SHA = '180b2835ea06f7f7ae4d15d765eb3c64c9518f8d03fc6ee350d33ce9eccef036'
EXPORT = ROOT / 'build/research/aloft-decode-20261109/block-analysis/all-side1-accepted-01'
EXPORT_PROOF = EXPORT / 'all-side1-proof.json'
EXPORT_SHA = '093a3f02ef4e05987d93f9d8f58199623dab47c9502b9aee804072f0bd9bb2eb'
PLAN = EXPORT / 'side1-slot000-plan.json'
PLAN_SHA = '6f2dcbc22c112f4c902ca0fd1d6e9e9f6d07126fa7a3a0fd91559491eab5914e'
VICE = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
VICE_SHA = '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1'
PRIOR = ROOT / 'build/research/aloft-decode-20261109/stream-analysis/all-side1-exploration-01/all-side1-exploration.json'
PRIOR_SHA = 'ffc37070df52d17beb032e521a51b3c6fc42b068ab170f471fdf5a8871a11409'
RESIDENT_ASM = ROOT / 'build/research/aloft-20261109/loader-analysis/catalog-source-02/resources__sl.asm'
RESIDENT_ASM_SHA = '46b28b74e9d2528b808e0c3fd0df08ef0ce7537d4a143527932bee46d9dcab60'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def record(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def load_decoder():
    assert record(MODEL)['sha256'] == MODEL_SHA
    spec = importlib.util.spec_from_file_location('unchanged_sparkle_token_decoder', MODEL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FROZEN = load_decoder()


class PartialByte:
    """Bit values only where mask=1; absent high bits are not numeric zero."""
    def __init__(self, value_bits, known_mask):
        assert 0 <= value_bits <= 255 and 0 <= known_mask <= 255
        assert value_bits & (~known_mask & 255) == 0
        self.value_bits, self.known_mask = value_bits, known_mask

    def description(self):
        return dict(value_bits=self.value_bits, known_mask=self.known_mask,
            unknown_mask=(~self.known_mask & 255), full_byte_value_not_asserted=self.known_mask != 255)


def bits(value):
    if isinstance(value, PartialByte):
        return value.value_bits, value.known_mask
    assert isinstance(value, int) and 0 <= value <= 255
    return value, 255


class ColorMemory(FROZEN.Memory):
    def __init__(self):
        super().__init__()
        self.color_low = bytearray(1024)
        self.color_known_mask = bytearray(1024)
        self.color_origin = [None] * 1024
        self.color_reads = []

    def read(self, address, io_mode, context):
        address &= 65535
        if io_mode == 0x35 and 0xd800 <= address <= 0xdbff:
            cell = address & 1023
            known = self.color_known_mask[cell]
            if known != 15:
                raise FROZEN.DecodeStop('Unknown device ColorRAM low bits; no native/default substitution',
                    address=address,cell=cell,required_mask=15,known_mask=known,**context)
            value = PartialByte(self.color_low[cell] & 15, 15)
            origin = dict(kind='device-ColorRAM-partial-read',cell=cell,
                low_bit_origin=self.color_origin[cell],unknown_high_source='VICphi1 bus, not evaluated')
            self.color_reads.append(dict(address=address,cell=cell,**value.description(),origin=origin,**context))
            return value, origin
        return super().read(address, io_mode, context)

    def write(self, address, value, io_mode, context, source):
        address &= 65535
        value_bits, known_mask = bits(value)
        if io_mode == 0x35 and 0xd800 <= address <= 0xdbff:
            if known_mask & 15 != 15:
                raise FROZEN.DecodeStop('ColorRAM sink lacks required low bits',address=address,
                    required_mask=15,known_mask=known_mask,**context)
            cell = address & 1023
            self.color_low[cell] = value_bits & 15
            self.color_known_mask[cell] = 15
            bus = dict(value_bits=value_bits, known_mask=known_mask, unknown_mask=(~known_mask & 255),
                full_byte_value_not_asserted=known_mask != 255)
            entry = dict(address=address,cell=cell,io_mode=io_mode,bus=bus,
                device_stored_low=value_bits & 15,device_required_mask=15,source=source,**context)
            self.io_writes.append(entry)
            self.color_origin[cell] = dict(IO_write_index=len(self.io_writes)-1,**context)
            return
        if known_mask != 255:
            raise FROZEN.DecodeStop('Partial ColorRAM byte cannot feed full RAM or unsupported I/O sink',
                address=address,required_mask=255,known_mask=known_mask,value_bits=value_bits,**context)
        # Other I/O full-byte bus writes remain records only, as in the frozen
        # model. No unrelated device is simulated; its reads still fail closed.
        super().write(address,value_bits,io_mode,context,source)


def primary(output):
    assert record(VICE)['sha256'] == VICE_SHA
    entries=[]
    with tarfile.open(VICE) as archive:
        for member,ranges in {
            'vice-3.10/src/c64/c64memsc.c':[(597,605)],
            'vice-3.10/src/c64/c64meminit.c':[(179,190)],
        }.items():
            raw=archive.extractfile(member).read();lines=raw.decode().splitlines(keepends=True)
            for first,last in ranges:
                text=''.join(lines[first-1:last]);entries.append(dict(member=member,member_sha256=sha(raw),
                    first_line=first,last_line=last,text=text,fragment_sha256=sha(text.encode())))
    assert 'value & 0xf' in entries[0]['text'] and 'vicii_read_phi1() & 0xf0' in entries[0]['text']
    write(output/'primary-ColorRAM-source.json',dict(archive=record(VICE),anchors=entries,
        write_rule='device_low=value&0x0F',read_rule='device_low | (VICphi1&0xF0)',
        high_nibble_is_unbound_external_bus_state=True,
        partial_copy_control_note='Frozen resident copies LDA/STA/DEY/BNE; DEY supplies loop flags. The paired-nibble cache uses only the marker sign bit, forced by known control carry before prior A is discarded. No partial payload byte is interpreted as a token/length.'))
    assert record(RESIDENT_ASM)['sha256'] == RESIDENT_ASM_SHA
    asm=RESIDENT_ASM.read_text().splitlines(keepends=True)
    ranges=[(507,522,'literal A replacement and descending copy'),
        (528,553,'match-tag A replacement and descending copy'),
        (559,575,'known bitstream decisions and refill A replacement'),
        (581,601,'paired-nibble cache sign marker and later A replacement')]
    resident=[]
    for first,last,role in ranges:
        text=''.join(asm[first-1:last]);resident.append(dict(first_line=first,last_line=last,
            role=role,text=text,fragment_sha256=sha(text.encode())))
    assert 'dey' in resident[0]['text'] and 'bne LitCopy' in resident[0]['text']
    assert 'dey' in resident[1]['text'] and 'bne MatchCopy' in resident[1]['text']
    assert 'lda Buffer,x' in resident[1]['text'] and 'tya' in resident[0]['text']
    assert 'bcc ShortLit' in resident[2]['text'] and 'rol' in resident[2]['text']
    assert 'SkipML:' in resident[3]['text'] and 'ror' in resident[3]['text']
    assert 'sta MidLitSeq+1' in resident[3]['text'] and 'bpl SkipML' in resident[3]['text']
    write(output/'partial-copy-control-source.json',dict(resident_source=record(RESIDENT_ASM),
        unchanged_decoder=record(MODEL),anchors=resident,
        abstraction_argument=[
            'A partial payload value is used only by LDA/STA inside the copy loop. DEY sets N/Z from the known Y counter before BNE; payload N/Z cannot decide loop continuation.',
            'A following match replaces A with the full packet tag before ANC/classification. A single literal replaces A with TYA from known Y=0. A bit refill replaces A with a full packet byte.',
            'The pending-nibble shortcut may ROR the previous partial A. Entry to the multi-literal path has known C=1, so the stored cache marker always has bit7=1, independent of every old A bit.',
            'Only that marker sign is consumed at the next LDY-immediate/BPL: the negative path replaces Y and A from a full packet nibble byte. Other unknown marker bits are never used as a length.',
            'After saving the marker, TYA/ANC0F replaces A with the known cached nibble before destination arithmetic. The frozen cache abstraction None-or-known-nibble preserves exactly these control dependencies.',
        ],
        assumptions=['Packet/control inputs are full known bytes; partial writes to RAM/buffer/resident control are rejected before such values can become tokens.',
            'No arbitrary CPU/application execution is modelled. This argument covers the guarded resident compressed-copy paths only.']))


def finite_checks(output):
    domain=[]
    for low in range(16):
        for high in range(16):
            concrete = low | (high << 4)
            assert concrete & 15 == low
            domain.append(dict(low=low,possible_high=high,possible_full_read=concrete,
                abstract_value_bits=low,abstract_known_mask=15,ColorRAM_sink_result=concrete & 15))
    m=ColorMemory();context=dict(bundle=-1,packet=-1,token=-1,cursor=-1)
    failures=[]
    try:m.read(0xd800,0x35,context)
    except FROZEN.DecodeStop as error:failures.append(error.diagnostic)
    else:raise AssertionError('Unknown initial device color was accepted')
    m.write(0xd800,0xab,0x35,context,dict(kind='explicit synthetic full-byte source'))
    assert m.color_low[0]==11 and m.color_known_mask[0]==15 and not m.known[0xd800]
    value,origin=m.read(0xd800,0x35,context)
    assert isinstance(value,PartialByte) and value.value_bits==11 and value.known_mask==15
    m.write(0xd801,value,0x35,context,origin)
    assert m.color_low[1]==11 and m.io_writes[-1]['bus']['known_mask']==15 and 'value' not in m.io_writes[-1]
    for address in [0x8000,0xd020]:
        try:m.write(address,value,0x35,context,origin)
        except FROZEN.DecodeStop as error:failures.append(error.diagnostic)
        else:raise AssertionError('A partial byte reached a full/unsupported sink')
    m.write(0xd800,0x42,0x34,context,dict(kind='explicit synthetic underlying RAM source'))
    assert m.read(0xd800,0x34,context)[0]==0x42 and m.read(0xd800,0x35,context)[0].value_bits==11
    write(output/'partial-bit-contract.json',dict(pass_=True,all256_concrete_high_low_pairs=domain,
        initial_unknown_read_rejected=True,partial_full_RAM_and_other_IO_sinks_rejected=True,
        device_low_separate_from_underlying_RAM=True,explicit_failures=failures,
        forced_cache_marker_domain=[dict(prior_A=a,known_carry=1,ROR_marker=128 | (a >> 1),
            marker_sign_known_one=True,next_BPL_taken=False)for a in range(256)],
        synthetic_contract_checks_are_not_native_oracles=True))


def run(output):
    output.relative_to(BASE);output.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).read_bytes();(output/'color_memory.checked.py').write_bytes(source)
    (output/'depacker.checked.py').write_bytes(MODEL.read_bytes())
    primary(output);finite_checks(output)
    assert record(EXPORT_PROOF)['sha256']==EXPORT_SHA and record(PLAN)['sha256']==PLAN_SHA
    export=json.loads(EXPORT_PROOF.read_text());assert export['pass_']
    for item in export['inputs']:assert record(ROOT/item['path'])==item
    for item in export['outputs']:
        raw=(EXPORT/item['name']).read_bytes();assert len(raw)==item['bytes'] and sha(raw)==item['sha256']
    assert record(PRIOR)['sha256']==PRIOR_SHA
    prior=json.loads(PRIOR.read_text())
    provider=FROZEN.PlanProvider(PLAN);memory=ColorMemory();decoder=FROZEN.Decoder(provider,memory=memory)
    completed=[];stop=None;last_write=0;prior_equal=[]
    try:
        for index in range(128):
            result=decoder.decode_bundle();assert result['bundle']==index
            delta=bytearray(65536)
            for item in memory.writes[result['first_RAM_write']:result['end_RAM_write']]:delta[item['address']]=1
            values={'memory':memory.data,'known-mask':memory.known,'cumulative-write-mask':memory.output_mask,
                'delta-write-mask':delta,'ColorRAM-low-bits':memory.color_low,'ColorRAM-known-mask':memory.color_known_mask}
            files=[]
            for suffix,raw in values.items():
                name=f'bundle{index:03d}-{suffix}.bin';(output/name).write_bytes(raw)
                files.append(dict(name=name,bytes=len(raw),sha256=sha(raw)))
            # These old source-only outputs are comparison targets after each
            # new prediction, never initial RAM or device inputs.
            if index < 22:
                previous=prior['completed_bundles'][index]
                old={Path(row['path']).name:row for row in previous['files']}
                for suffix in ['memory','known-mask','cumulative-write-mask','delta-write-mask']:
                    row=old[f'bundle{index:03d}-{suffix}.bin'];path=ROOT/row['path'];assert record(path)==row
                    assert bytes(values[suffix])==path.read_bytes()
                prior_equal.append(index)
            completed.append(dict(**result,known_RAM_bytes=sum(memory.known),
                known_device_ColorRAM_cells=sum(mask==15 for mask in memory.color_known_mask),files=files))
            last_write=len(memory.writes)
        stop=dict(reason='Explicit128bundle exploration limit reached; not a source-end claim')
    except FROZEN.DecodeStop as error:
        stop=error.diagnostic
    except Exception as error:
        stop=dict(reason='Unexpected adapter/job exception',error=repr(error),traceback=traceback.format_exc())
    finally:
        for suffix,raw in [('memory',memory.data),('known-mask',memory.known),('cumulative-write-mask',memory.output_mask),
            ('ColorRAM-low-bits',memory.color_low),('ColorRAM-known-mask',memory.color_known_mask)]:
            (output/('partial-final-'+suffix+'.bin')).write_bytes(raw)
        write(output/'typed-tokens.json',decoder.events)
        write(output/'IO-write-events.json',memory.io_writes)
        write(output/'partial-ColorRAM-read-events.json',memory.color_reads)
        digest=hashlib.sha256()
        for item in memory.writes:digest.update(json.dumps(item,sort_keys=True,separators=(',',':')).encode()+b'\n')
        outputs=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes()))for p in sorted(output.iterdir())if p.is_file()]
        proof=dict(pass_=stop is not None and stop['reason']!='Unexpected adapter/job exception',
            scope='Source-only device-low-bit extension around unchanged token decoder; bounded stopped exploration, not a native-output proof.',
            producer=record(Path(__file__)),frozen_decoder=record(MODEL),
            inputs=[record(EXPORT_PROOF),record(PLAN),record(VICE),record(PRIOR),record(RESIDENT_ASM)],
            all_initial_RAM_and_device_low_bits_unknown=True,native_values_never_inputs=True,
            completed_bundle_count=len(completed),completed_bundles=completed,partial_bundle=decoder.bundle_number,
            packets_consumed=provider.position,stop=stop,
            total_RAM_write_operations=len(memory.writes),partial_RAM_writes_since_last_complete=len(memory.writes)-last_write,
            IO_bus_write_operations=len(memory.io_writes),partial_ColorRAM_read_operations=len(memory.color_reads),
            partial_bus_write_operations=sum(item.get('bus',{}).get('known_mask',255)!=255 for item in memory.io_writes),
            known_device_ColorRAM_cells=sum(mask==15 for mask in memory.color_known_mask),
            frozen_RAM_only_prefix_predictions_equal=prior_equal,full_RAM_write_ledger_canonical_SHA256=digest.hexdigest(),
            outputs=outputs,limits=['No CPU/native/drive/emulator/build/socket/downloaded host execution.',
                'ColorRAM high read bits stay UNKNOWN, no zero/constant/native high nibble.',
                'Only a ColorRAM sink may discard those unknown high bits. Full RAM and unsupported I/O partial consumers stop.',
                'Other device reads and unknown low ColorRAM bits stop; full unrelated I/O bus writes are records only, not device simulations.',
                'Canonical packet order, no intervening application execution or memory/device mutation is simulated.',
                'Per-bundle source states here remain software-only predictions until separately associated with native generations.',
                'No full-side completion, resource count, named effect, pixels, transfer waveform, timing or native-verified claim is inferred.'])
        write(output/'color-stream-proof.json',proof)
        print(json.dumps(dict(proof=record(output/'color-stream-proof.json'),completed=len(completed),
            packets=provider.position,known_colors=proof['known_device_ColorRAM_cells'],stop=stop)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True,type=Path)
    run(parser.parse_args().output.resolve())
