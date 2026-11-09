#!/usr/bin/env python3
"""Strict typed Sparkle backward token decoder, using source packets only.

This is a compressed-format reader, not a CPU interpreter. It evaluates
literal/match/header/tag operations only. Native expected RAM is never input.
Unknown RAM and unmodelled I/O/control-memory dependencies stop explicitly.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import traceback

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-decode-20261109/stream-analysis'
OLD = ROOT / 'build/research/aloft-20261109'
PRIMARY = OLD / 'loader-analysis/catalog-source-02'
SOURCE_PINS = {
    'resources__sl.asm': '46b28b74e9d2528b808e0c3fd0df08ef0ce7537d4a143527932bee46d9dcab60',
    'loader.cpp': '78649471dfd302500e0c0b8053869043879d87e0566a450f2eb2e7b041e1162d',
    'packer.cpp': 'bb60128abbe2c5af5f3a1965f7ea66a5f4ef3bcb2523b2a8324758555bb32a6a',
}
TRANSPORT_RECEIPTS = {
    'accepted-01/block-proof.json': '768a37475c5e8e07c73fc8e0ab64c5ef80eea508212e462a3e8b58b8033e6ec3',
    'sequential-prefix-accepted-01/prefix-export-proof.json': 'ac3b5f1f0f2731a51d1a6bbbfaf658869b588d842088ce0c130256d501d63e61',
}
RESIDENT_SHA = 'b09c13f9f60a28aa87cf1b157b4035df325eb60bf6d79fe8f176cf7aa606db48'
BOOT_SHA = '7e283e390a10c2b7784ac1885081234c21a754d161e938babd504a13da2ee2e5'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


class DecodeStop(Exception):
    def __init__(self, reason, **context):
        self.diagnostic = dict(reason=reason, **context)
        super().__init__(json.dumps(self.diagnostic, sort_keys=True))


class Memory:
    """Physical RAM values known from transport or earlier decoded writes only."""
    def __init__(self):
        self.data = bytearray(65536)
        self.known = bytearray(65536)
        self.output_mask = bytearray(65536)
        self.origin = [None] * 65536
        self.writes = []
        self.io_writes = []

    def packet(self, raw, origin):
        assert len(raw) == 256
        for index, value in enumerate(raw):
            address = 0x300 + index
            self.data[address] = value
            self.known[address] = 1
            self.output_mask[address] = 0
            self.origin[address] = dict(kind='received-packet', index=index, **origin)

    def metadata(self, address, value, origin):
        assert address in (0x300,0x3ff) and 0 <= value <= 255
        self.data[address],self.known[address] = value,1
        self.origin[address] = dict(kind='resident-format-buffer-metadata', **origin)

    def read(self, address, io_mode, context):
        address &= 65535
        if address in (0,1):
            raise DecodeStop('CPU port read needs explicit hardware context', address=address, **context)
        if io_mode == 0x35 and 0xd000 <= address <= 0xdfff:
            raise DecodeStop('I/O-visible match/literal read needs device provenance', address=address, **context)
        if not self.known[address]:
            raise DecodeStop('Unknown RAM read; no zero/native-oracle substitution', address=address, **context)
        return self.data[address],self.origin[address]

    def write(self, address, value, io_mode, context, source):
        address &= 65535
        assert 0 <= value <= 255
        if 0 <= address <= 4 or 0x160 <= address < 0x300:
            raise DecodeStop('Decoded output aliases active CPU-port/loader control state', address=address, **context)
        record = dict(address=address,value=value,io_mode=io_mode,source=source,**context)
        if io_mode == 0x35 and 0xd000 <= address <= 0xdfff:
            # Raw bus value only: no I/O-device readback or physical RAM claim.
            self.io_writes.append(record)
            return
        self.data[address] = value
        self.known[address] = self.output_mask[address] = 1
        self.origin[address] = dict(kind='decoded-output',write_index=len(self.writes))
        self.writes.append(record)


class PlanProvider:
    """Immutable packet files; canonical order/provenance belongs to transport."""
    def __init__(self, path):
        self.path = path.resolve()
        self.plan = json.loads(path.read_text())
        if self.plan.get('schema') != 'sparkle-received-packets-v1':
            raise DecodeStop('Unsupported packet plan schema', schema=self.plan.get('schema'))
        self.rows = self.plan['packets']
        self.position = 0
        self.used = []

    def next_packet(self):
        if self.position >= len(self.rows):
            raise DecodeStop('Original source packet plan exhausted', packets_consumed=self.position)
        row = self.rows[self.position]
        path = Path(row['path'])
        if not path.is_absolute():
            path = self.path.parent / path
        raw = path.read_bytes()
        if len(raw) != 256 or row.get('bytes') != 256 or sha(raw) != row['sha256']:
            raise DecodeStop('Changed source packet file', position=self.position,path=str(path))
        result = dict(received=raw,source=dict(row.get('source',{}),plan_position=self.position,
            packet_artifact=artifact(path)))
        self.used.append(dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw),source=result['source']))
        self.position += 1
        return result


class Decoder:
    def __init__(self, provider, memory=None, token_limit=1000000):
        self.provider = provider
        self.memory = memory if memory is not None else Memory()
        self.packet_number = -1
        self.packet_source = None
        self.x = self.bits = 0
        self.nibble_cache = None
        self.destination = None
        self.io_mode = 0x35
        self.events = []
        self.bundles = []
        self.byte_reads = []
        self.bit_reads = []
        self.token_limit = token_limit
        self.bundle_number = -1

    def context(self):
        return dict(bundle=self.bundle_number,packet=self.packet_number,token=len(self.events),cursor=self.x)

    def event(self, kind, **data):
        if len(self.events) >= self.token_limit:
            raise DecodeStop('Explicit typed-token bound reached', limit=self.token_limit,**self.context())
        self.events.append(dict(kind=kind,**self.context(),**data))
        return self.events[-1]

    def at(self, index):
        assert 0 <= index < 256
        return self.memory.read(0x300 + index,0x34,self.context())[0]

    def byte(self, role):
        index = self.x
        value = self.at(index)
        self.x = (self.x - 1) & 255
        self.byte_reads.append(dict(role=role,index=index,value=value,**self.context()))
        return value

    def initial_bits(self):
        # LoadNext starts X=0; a zero Buffer0 redirects to saved LastX/BPtr.
        self.nibble_cache = None
        self.x = 0
        first = self.at(0)
        if first == 0:
            self.x = self.at(255)
            first = self.at(self.x)
        if first == 0:
            raise DecodeStop('No nonzero initial bitstream/sentinel', **self.context())
        self.bits = first
        self.x = (self.x - 1) & 255
        self.event('bitstream-start',initial_bits=first,first_header_cursor=self.x)

    def receive(self):
        packet = self.provider.next_packet()
        raw = packet['received']
        if not isinstance(raw,bytes) or len(raw) != 256:
            raise DecodeStop('Provider did not supply exact received256bytes')
        self.packet_number += 1
        self.packet_source = packet['source']
        self.memory.packet(raw,dict(packet=self.packet_number,source=packet['source']))
        self.event('receive-packet',received_sha256=sha(raw),source=packet['source'])
        self.initial_bits()

    def bit(self, role):
        before = self.bits
        carry = before >> 7
        self.bits = (before << 1) & 255
        refilled = False
        if self.bits == 0:
            if carry != 1:
                raise DecodeStop('Invalid exhausted bitstream sentinel', bits_before=before,**self.context())
            value = self.byte('bitstream-refill')
            carry = value >> 7
            self.bits = ((value << 1) | 1) & 255
            refilled = True
        self.bit_reads.append(dict(role=role,value=carry,bits_before=before,bits_after=self.bits,
            refilled=refilled,**self.context()))
        return carry

    def nibble(self):
        if self.nibble_cache is None:
            pair = self.byte('paired-literal-length-nibbles')
            self.nibble_cache = pair >> 4
            return pair & 15
        result,self.nibble_cache = self.nibble_cache,None
        return result

    def header(self, reason):
        low = self.byte('destination-low')
        high = self.byte('destination-high-or-IO-flag')
        self.io_mode = 0x35
        flag = high == 0
        if flag:
            high = self.byte('destination-high-after-zero-flag')
            if high:
                self.io_mode = 0x34
        self.destination = low | (high << 8)
        self.memory.metadata(0x300,0,self.context())
        self.event('destination-header',reason=reason,destination=self.destination,io_mode=self.io_mode,
            encoded_zero_flag=flag,first_literal_has_no_type_bit=True)

    @staticmethod
    def descending_y(count):
        assert 1 <= count <= 256
        if count == 256:
            return [0] + list(range(255,0,-1))
        return range(count,0,-1)

    def literals(self):
        if self.bit('literal-length-selector') == 0:
            length,kind = 1,'one'
        else:
            value = self.nibble()
            if value:
                length,kind = value + 1,'paired-nibble'
            else:
                length,kind = self.byte('long-literal-length-minus-one') + 1,'long'
        before = self.destination
        self.destination = (self.destination - length) & 65535
        self.x = (self.x - length) & 255
        source_base = 0x300 + self.x
        canonical = length <= 251 and (kind != 'long' or length >= 17)
        event = self.event('literal',length=length,length_class=kind,destination_before=before,
            destination_after=self.destination,literal_source_base=source_base,writer_canonical=canonical)
        context = dict(self.context(),token=event['token'])
        for y in self.descending_y(length):
            src = (source_base + y) & 65535
            dst = (self.destination + y) & 65535
            value,origin = self.memory.read(src,self.io_mode,context)
            self.memory.write(dst,value,self.io_mode,context,dict(kind='literal',address=src,origin=origin,y=y))

    def match(self):
        tag = self.byte('match-tag')
        if tag & 3:
            length = (tag & 3) + 1
            stored_distance = tag >> 2
            kind = 'short'
        else:
            if tag == 0:
                self.event('end-block',tag=tag)
                return 'block'
            if tag == 0x80:
                self.event('end-file',tag=tag)
                return 'file'
            high = self.byte('far-distance-high') if tag < 128 else 0
            length = (tag & 0x7c) >> 2
            kind = 'far-mid' if tag < 128 else 'near-mid'
            if length == 1:
                length = self.byte('long-match-length-or-bundle-end')
                kind = 'far-long' if tag < 128 else 'near-long'
                if length == 0:
                    self.memory.metadata(0x3ff,self.x,self.context())
                    self.io_mode = 0x35
                    self.event('end-bundle',tag=tag,saved_LastX=self.x)
                    return 'bundle'
            if length == 0:
                raise DecodeStop('Unrecognized zero-length match class',tag=tag,**self.context())
            stored_distance = (high << 8) | self.byte('match-distance-low')
        distance = stored_distance + 1
        before = self.destination
        self.destination = (self.destination - length) & 65535
        source_base = (self.destination + distance) & 65535
        event = self.event('match',tag=tag,match_class=kind,length=length,distance=distance,
            destination_before=before,destination_after=self.destination,source_base=source_base,
            address_wraps_16bits=True,overlapping_reads_use_current_decoded_RAM=True)
        context = dict(self.context(),token=event['token'])
        for y in self.descending_y(length):
            src,dst = (source_base + y) & 65535,(self.destination + y) & 65535
            value,origin = self.memory.read(src,self.io_mode,context)
            self.memory.write(dst,value,self.io_mode,context,dict(kind='match',address=src,origin=origin,y=y))
        return 'continue'

    def decode_bundle(self):
        self.bundle_number += 1
        start_events,start_writes,start_io = len(self.events),len(self.memory.writes),len(self.memory.io_writes)
        if self.packet_number < 0:
            self.receive()
        else:
            self.initial_bits()
        self.header('bundle-start')
        state = 'literal'
        while True:
            if len(self.events) >= self.token_limit:
                raise DecodeStop('Explicit typed-token bound reached',limit=self.token_limit,**self.context())
            if state == 'choose':
                state = 'match' if self.bit('literal-or-match') else 'literal'
            if state == 'literal':
                self.literals()
                state = 'match'  # Source/packer guarantee: literal followed by match.
                continue
            result = self.match()
            if result == 'bundle':
                record = dict(bundle=self.bundle_number,first_event=start_events,end_event=len(self.events),
                    first_RAM_write=start_writes,end_RAM_write=len(self.memory.writes),
                    RAM_writes=len(self.memory.writes)-start_writes,IO_writes=len(self.memory.io_writes)-start_io,
                    packet_at_return=self.packet_number,saved_LastX=self.x)
                self.bundles.append(record)
                return record
            if result == 'block':
                self.receive()
                self.header('new-block')
                state = 'literal'
            elif result == 'file':
                self.header('next-file-in-current-block')
                state = 'literal'
            else:
                state = 'choose'


def source_contract(output):
    inputs=[]
    for name,pin in SOURCE_PINS.items():
        path=PRIMARY/name
        assert artifact(path)['sha256']==pin
        inputs.append(artifact(path))
    cpp=(PRIMARY/'loader.cpp').read_text()
    array=re.search(r'unsigned char loader\[loader_size\] = \{(.*?)\};',cpp,re.S)
    assert array and 'const int loader_size = 832;'in cpp
    reference=bytes(int(x,16)for x in re.findall(r'0x([0-9a-fA-F]{2})',array[1]))
    assert len(reference)==832 and sha(reference)=='0916330e9e7075a446559665572b94a875a8ff0f72472c3d25afc96659c789fa'
    boot=OLD/'disk-analysis/accepted-01/bootstrap-side1.prg'
    assert artifact(boot)['sha256']==BOOT_SHA
    original=boot.read_bytes()
    assert original[-416:]==reference[-416:] and sha(reference[-416:])==RESIDENT_SHA
    (output/'resident-source-0160.bin').write_bytes(reference[-416:])
    asm=(PRIMARY/'resources__sl.asm').read_text();lines=asm.splitlines(keepends=True)
    anchors=[]
    for first,last,role in [(8,16,'workspace and buffer'),(363,450,'block/file/bundle transitions and headers'),
        (452,494,'match tags and offset/length semantics'),(496,553,'literal/match backward copy'),
        (555,611,'sentinel bits and paired-nibble lengths')]:
        text=''.join(lines[first-1:last]);anchors.append(dict(first_line=first,last_line=last,role=role,
            text=text,sha256=sha(text.encode())))
    write_json(output/'grammar-source-anchors.json',dict(source=inputs[0],resident_sha256=RESIDENT_SHA,
        original_bootstrap=artifact(boot),primary_reference=inputs[1],full416_original_resident_equal=True,
        whole832_bootstrap_equal=reference==original,anchors=anchors))
    packer=(PRIMARY/'packer.cpp').read_text().splitlines(keepends=True)
    write_json(output/'writer-format-anchors.json',dict(source=inputs[2],anchors=[
        dict(first_line=first,last_line=last,role=role,text=''.join(packer[first-1:last]))
        for first,last,role in [(152,237,'buffer/sentinel/paired-nibble construction'),
            (241,310,'literal selectors and byte sequence'),(322,403,'five match-tag constructions')]]))
    return inputs+[artifact(boot)]


def transport_contract(plan):
    """Require a frozen original-byte transport receipt, not arbitrary JSON."""
    block_base=ROOT/'build/research/aloft-decode-20261109/block-analysis'
    candidates=[(block_base/name,pin)for name,pin in TRANSPORT_RECEIPTS.items()
        if plan.parent==(block_base/name).parent]
    if len(candidates)!=1:
        raise DecodeStop('Packet plan is outside the frozen original-source transport receipts',path=str(plan))
    path,pin=candidates[0]
    if artifact(path)['sha256']!=pin:
        raise DecodeStop('Changed frozen transport receipt',path=str(path))
    proof=json.loads(path.read_text())
    assert proof['pass_']
    for record in proof['inputs']:
        assert artifact(ROOT/record['path'])==record
    outputs={record['name']:record for record in proof['outputs']}
    assert plan.name in outputs
    for record in outputs.values():
        target=path.parent/record['name']
        raw=target.read_bytes()
        assert len(raw)==record['bytes'] and sha(raw)==record['sha256']
    return artifact(path)


def export_state(output,decoder):
    (output/'predicted-memory.bin').write_bytes(decoder.memory.data)
    (output/'known-memory-mask.bin').write_bytes(decoder.memory.known)
    (output/'decoded-RAM-write-mask.bin').write_bytes(decoder.memory.output_mask)
    write_json(output/'typed-tokens.json',decoder.events)
    write_json(output/'decoded-RAM-writes.json',decoder.memory.writes)
    write_json(output/'decoded-IO-writes.json',decoder.memory.io_writes)
    write_json(output/'byte-and-bit-reads.json',dict(bytes=decoder.byte_reads,bits=decoder.bit_reads))


def run(plan,output,bundle_count):
    output.relative_to(BASE)
    output.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).read_bytes();(output/'depacker.checked.py').write_bytes(source)
    provider=decoder=None
    try:
        inputs=source_contract(output)
        transport_receipt=transport_contract(plan)
        provider=PlanProvider(plan)
        decoder=Decoder(provider)
        for _ in range(bundle_count):decoder.decode_bundle()
        export_state(output,decoder)
        write_json(output/'source-packets-used.json',dict(plan=artifact(plan),metadata=provider.plan,
            packets_used=provider.used,delivery_order_is_declared_transport_input_not_native_trace=True))
        outputs=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes()))for p in sorted(output.iterdir())if p.is_file()]
        proof=dict(pass_=True,scope='Exact-resident typed backward compressed-format decode from original source packets; UNKNOWN RAM start.',
            producer=artifact(Path(__file__)),inputs=inputs+[transport_receipt,artifact(plan)],bundles=decoder.bundles,
            received_packets=len(provider.used),tokens=len(decoder.events),token_classes=dict(Counter(e['kind']for e in decoder.events)),
            known_RAM_bytes=sum(decoder.memory.known),decoded_RAM_unique_bytes=sum(decoder.memory.output_mask),
            decoded_RAM_writes=len(decoder.memory.writes),decoded_IO_bus_writes=len(decoder.memory.io_writes),
            initial_RAM_is_unknown=True,native_expected_RAM_or_pixels_are_never_inputs=True,outputs=outputs,
            limits=['No CPU/drive/emulator/native process/build/socket/downloaded host execution.',
                'Delivery order is the declared source-transport order, not a native rotational trace or all-order equivalence proof.',
                'Only known RAM reads are accepted; unknown prior assets, I/O reads and active CPU/loader-control aliasing stop with exact context.',
                'Raw I/O writes are recorded separately; device state/readback and physical RAM under visible I/O are not fabricated.',
                'Packet Buffer0300..03FF metadata is format state, kept distinct from decoded-output RAM masks.',
                'Sequential bundles retain source-decoded format memory; external application mutations between calls are not simulated or supplied from native RAM.',
                'No native slot association, execution entry, named effect, pixels, schedule, physical IEC transfer or timing result is inferred.'])
        write_json(output/'stream-proof.json',proof)
        print(json.dumps(dict(pass_=True,proof=artifact(output/'stream-proof.json'),bundles=len(decoder.bundles),
            packets=len(provider.used),RAM_unique=sum(decoder.memory.output_mask))))
    except Exception as error:
        if decoder is not None:export_state(output,decoder)
        write_json(output/'failure.json',dict(pass_=False,error=repr(error),diagnostic=error.diagnostic if isinstance(error,DecodeStop)else None,
            traceback=traceback.format_exc(),producer_sha256=sha(source),plan=artifact(plan),
            packets_used=provider.used if provider else [],native_expected_RAM_never_input=True))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packets',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    parser.add_argument('--bundles',type=int,default=1)
    args=parser.parse_args()
    assert args.bundles>0
    run(args.packets.resolve(),args.output.resolve(),args.bundles)
