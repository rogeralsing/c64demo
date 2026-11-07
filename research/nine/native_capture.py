#!/usr/bin/env python3
"""Compare existing original Nine RAM/VSF captures with established byte proofs.

No process, emulator, CPU interpretation or hardware mock is started. Unknown
later display states are observations, not silently accepted initializers.
"""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/nine'
BINARY = BASE/'binary'
sys.path.insert(0,str(ROOT/'research/quondam'))
from snapshot_state import read_snapshot, module_payload

PRG_SHA = 'a257fa0436bc0d97fbeaa906c55489786a26ee6a9213aa3fd0d8e21f9612d839'
PAYLOAD_SHA = 'ef45ab609f139bb03befcf20ab3253e2bb30debbc4cbd789350607c1c9d54004'
PROOF_SHA = '2a68b45ae9a6c4e0de061a7233b46a131420070f5d6fe586157bd945f10558cc'
UNPACKED_SIGNATURE = bytes.fromhex('a9 7f 8d 0d dc a2 02 b5 00 9d 00 fe')
ENTRY_SIGNATURE = bytes.fromhex('20 17 80 20 77 82 a9 bf')
REGISTER = re.compile(
    r'^\.;([0-9a-f]{4})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+'
    r'([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([01]{8})\s+(\d+)\s+(\d+)\s+(\d+)',re.I)


def sha(blob):
    return hashlib.sha256(blob).hexdigest()


def contexts(text):
    current, bank, result = None,'cpu',[]
    for number,line in enumerate(text.splitlines(),1):
        text=line.strip()
        if text=='x': current=None
        if text.startswith('bank '): bank=text.split()[1]
        match=REGISTER.match(text)
        if match:
            values=match.groups()
            current=dict(zip(('pc','a','x','y','sp','port00','port01'),(int(v,16) for v in values[:7])))
            current.update(flags=int(values[7],2),raster_line=int(values[8]),
                           raster_cycle=int(values[9]),clock=int(values[10]))
        match=re.match(r'(bsave|dump|screenshot|scrsh) "([^"]+)"',text)
        if match:
            assert current is not None,('Capture lacks register observation',number)
            event=dict(filename=Path(match[2]).name,command=match[1],
                       bank=bank,transcript_line=number,registers=deepcopy(current))
            if match[1]=='bsave':
                args=text[match.end():].split()
                assert len(args)==3,('Expected explicit bsave device/start/end',number)
                event.update(device=int(args[0],16),first=int(args[1],16),end_inclusive=int(args[2],16))
            result.append(event)
    return result


def physical_ram(path):
    state=read_snapshot(path); meta=state['modules']['C64MEM']
    assert meta['version']==[0,1] and meta['payload_size']==65555
    return module_payload(path,'C64MEM')[4:65540]


def comparison(actual,expected,first,end,label):
    assert len(actual)==len(expected)==65536 and 0<=first<=end<=65536
    differences=[dict(address=a,expected=expected[a],actual=actual[a])
                 for a in range(first,end) if expected[a]!=actual[a]]
    return dict(label=label,first=first,end_exclusive=end,bytes=end-first,
                matched_bytes=end-first-len(differences),exact=not differences,
                sha256=sha(actual[first:end]),differences=differences)


def initial_zp():
    # Literal $8017..$8079 initialization plus generator's final pointer.
    result=bytearray(65536)
    values={2:255,3:255,6:6,0x22:0x3d,0x24:0,0x25:0x48,
            0x35:0x40,0x37:0x40,0x39:0xc0,0x3b:0x40,0x3f:0x7f,
            0x40:0xa0,0x41:0x3a,0x5b:0xc0}
    for a,v in values.items(): result[a]=v
    result[0x77:0x80]=bytes(range(9))
    return result


def rom_copy(path,actual,external=None):
    state=read_snapshot(path)
    if 'C64ROM' not in state['modules']:
        if external is not None:
            expected=bytearray(65536); expected[0x4400:0x4700]=external['data']
            result=comparison(actual,expected,0x4400,0x4700,'Native bank-rom D800..DAFF character-ROM copy')
            result.update(checked=True,source_file=external['file'],source_sha256=sha(external['data']),
                          source_bank='rom',source_range=[0xd800,0xdb00])
            return result
        return dict(checked=False,destination=[0x4400,0x4700],bytes=768,
                    reason='Snapshot omits ROMs; underlying $d800 RAM is not character ROM. No zero substitute is used.')
    meta=state['modules']['C64ROM']
    assert meta['version']==[0,0] and meta['payload_size']==20480
    # c64memsnapshot.c: KERNAL8192 + BASIC8192 + CHARGEN4096.
    payload=module_payload(path,'C64ROM')
    expected=bytearray(65536); expected[0x4400:0x4700]=payload[0x4800:0x4b00]
    result=comparison(actual,expected,0x4400,0x4700,'Authentic character-ROM copy D800..DAFF')
    result.update(checked=True,rom_module_version=[0,0],rom_module_sha256=sha(payload),
                  rom_payload_slice=[0x4800,0x4b00],chargen_sha256=sha(payload[0x4000:0x5000]))
    return result


def initialized_reference(generated):
    result=bytearray(generated)
    # Exact original $823f page-clear increment, $8252..$826b copy-operand
    # advancement and $8271..$8275 idle-byte initialization, not exclusions.
    result[0x823b]=0xf0
    result[0x824a:0x824c]=(0x7800+9*64).to_bytes(2,'little')
    result[0x824d:0x824f]=(0xe883+9*192).to_bytes(2,'little')
    result[0x79ff]=0xff
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,default=BASE/'native-01')
    parser.add_argument('--output',type=Path,default=BASE/'native-analysis')
    args=parser.parse_args(); directory=args.capture.resolve(); output=args.output.resolve()
    session=json.loads((directory/'session.json').read_text())
    assert session.get('closed_utc'),'Analyze a completed closed session.'
    program=(BASE/'lft-nine.prg').read_bytes()
    assert len(program)==14356 and sha(program)==PRG_SHA
    proof_path=BINARY/'binary-proof.json'
    assert sha(proof_path.read_bytes())==PROOF_SHA
    proof=json.loads(proof_path.read_text()); assert proof['input_sha256']==PRG_SHA
    unpacked=(BINARY/'unpack-ram.bin').read_bytes()
    relocated=(BINARY/'relocated-ram.bin').read_bytes()
    generated=(BINARY/'generated-ram.bin').read_bytes()
    assert len(unpacked)==len(relocated)==len(generated)==65536
    assert sha(unpacked[0x801:0x7cbd])==PAYLOAD_SHA
    for block in proof['relocation']['blocks']:
        a,b=block['destination'],block['destination_end_exclusive']
        assert sha(relocated[a:b])==block['sha256']
    for family in proof['generator']['families']:
        assert sha(generated[family['first']:family['end_exclusive']])==family['sha256']
    events=contexts((directory/'monitor.log').read_text(errors='replace'))
    snapshots={}; external_rom=None; rom_captures=[]
    for event in events:
        if event['command']=='bsave' and event['bank']=='rom':
            assert (event['first'],event['end_inclusive'])==(0xd800,0xdaff)
            file=directory/event['filename']; data=file.read_bytes(); assert len(data)==768
            external_rom=dict(file=str(file.relative_to(ROOT)),data=data)
            rom_captures.append(dict(file=str(file.relative_to(ROOT)),sha256=sha(data),bytes=len(data),
                                     bank='rom',range=[0xd800,0xdb00],registers=event['registers']))
            continue
        if event['command']!='dump': continue
        file=directory/event['filename']; state=read_snapshot(file)
        clock=int.from_bytes(module_payload(file,'MAINCPU')[:8],'little')
        assert clock==event['registers']['clock']
        snapshots[(event['registers']['pc'],clock)]=(file,state)
    records,images=[],[]
    for event in events:
        file=directory/event['filename']; register=event['registers']; pc=register['pc']
        key=pc,register['clock']
        if event['command']=='bsave':
            if event['bank']=='rom': continue  # Explicit768-byte ROM source, recorded separately.
            actual=file.read_bytes()
            if len(actual)!=65536:
                raise AssertionError(('Expected full64KB physical RAM capture',file,len(actual)))
            assert event['bank']=='ram',('Raw RAM must be explicitly bank ram',file,event['bank'])
            assert key in snapshots,('No same-stop VSF',file)
            snapshot,state=snapshots[key]
            checks=[comparison(actual,physical_ram(snapshot),0,65536,'All native raw RAM versus same-stop VSF RAM')]
            stage,established='unclassified_display_observation',False
            if pc in (0x1b3,0x80d) and actual[0x80d:0x819]==UNPACKED_SIGNATURE:
                if pc==0x1b3: assert actual[pc:pc+3]==bytes.fromhex('4c0d08')
                stage,established='untouched_unpacked_SFX_output',True
                checks.append(comparison(actual,unpacked,0x801,0x7cbd,'All29884 unpacked payload bytes'))
            elif pc==0x80d:
                expected=bytearray(65536); expected[0x801:0x4013]=program[2:]
                stage,established='packed_original_entry',True
                checks.append(comparison(actual,expected,0x801,0x4013,'Original loaded PRG before SFX'))
            elif pc in (0x8000,0x8146,0x8003):
                assert actual[0x8000:0x8008]==ENTRY_SIGNATURE
                expected=relocated if pc==0x8000 else generated if pc==0x8146 else initialized_reference(generated)
                stage={0x8000:'original_effect_entry',0x8146:'generator_complete_before_display',
                       0x8003:'initializer_complete_before_music'}[pc]
                established=True
                for n,block in enumerate(proof['relocation']['blocks']):
                    checks.append(comparison(actual,expected,block['destination'],block['destination_end_exclusive'],f'Relocated block{n+1}'))
                if pc in (0x8146,0x8003):
                    for family in proof['generator']['families']:
                        checks.append(comparison(actual,generated,family['first'],family['end_exclusive'],f"Generated family${family['first']:04x}"))
                    table=bytearray(65536); table[0x4700:0x4800]=relocated[0xae52:0xaf52]
                    checks.append(comparison(actual,table,0x4700,0x4800,'Literal AE52..AF51 table copy'))
                    if pc==0x8146:
                        checks.append(comparison(actual,initial_zp(),2,256,'Explicit initializer ZP state, including final generator pointer'))
                    else:
                        pointers=bytearray(65536)
                        for address,value in proof['setup']['pointer_setup']['expected_pointer_writes']:
                            pointers[address]=value
                            checks.append(comparison(actual,pointers,address,address+1,f'Prepared sprite pointer${address:04x}'))
                        glyphs=bytearray(65536)
                        for copy in proof['setup']['image_copy_setup']['copies']:
                            a,b,n=copy['source'],copy['destination'],copy['bytes']
                            glyphs[b:b+n]=relocated[a:a+n]
                        checks.append(comparison(actual,glyphs,0xe800,0xf000,'Full eight cleared pages with nine63-byte image copies'))
                    rom=rom_copy(snapshot,actual,external_rom)
                    if rom['checked']: checks.append(rom)
                else: rom=None
            else:
                # Later code intentionally patches operands/assets. Retain all
                # changes to established destinations without declaring them
                # harmless or excluding broad mutable regions.
                for n,block in enumerate(proof['relocation']['blocks']):
                    checks.append(comparison(actual,relocated,block['destination'],block['destination_end_exclusive'],f'Later observation versus original block{n+1}'))
            row=dict(file=str(file.relative_to(ROOT)),sha256=sha(actual),registers=register,
                     stage=stage,established_checkpoint=established,checks=checks,
                     exact=all(c['exact'] for c in checks),
                     snapshot=str(snapshot.relative_to(ROOT)),snapshot_sha256=state['file_sha256'],
                     vic_raster=[state['vicii']['raster_line'],state['vicii']['raster_cycle']],
                     cia={name:{k:v[k] for k in ('pra','ddra','timer_a','timer_b','cra','crb')}
                          for name,v in state['cia'].items()})
            if pc in (0x8146,0x8003): row['character_rom_copy']=rom
            if pc==0x8003:
                row['exact_initializer_updates']=[dict(address=a,before=generated[a],expected=expected[a],
                                                       reason=('Eight-page clear advances destination highbyte' if a==0x823b else
                                                               'Literal idle-byte initialization' if a==0x79ff else
                                                               'Nine-copy source/destination operand advancement'))
                                                  for a in (0x823b,0x824a,0x824b,0x824d,0x824e,0x79ff)]
            if not established: row['interpretation']='Observed differences require consumer/timing analysis; no initializer-equivalence claim.'
            records.append(row)
        elif event['command'] in ('screenshot','scrsh'):
            assert key in snapshots,('Screenshot lacks same-stop VSF',file)
            image=Image.open(file)
            images.append(dict(file=str(file.relative_to(ROOT)),sha256=sha(file.read_bytes()),
                               pixels=list(image.size),registers=register,
                               snapshot=str(snapshots[key][0].relative_to(ROOT)),
                               interpretation='Original-program output observation; no independent full-image pixel oracle.'))
    assert any(r['stage']=='untouched_unpacked_SFX_output' for r in records),'Missing pre-wrapper capture'
    assert any(r['stage']=='original_effect_entry' for r in records),'Missing natural8000 entry'
    assert any(r['stage']=='generator_complete_before_display' for r in records),'Missing postgenerator8146'
    result=dict(program_sha256=PRG_SHA,payload_sha256=PAYLOAD_SHA,script_sha256=sha(Path(__file__).read_bytes()),
                reference_proof_sha256=PROOF_SHA,reference_ram_sha256={name:sha(data) for name,data in
                (('unpacked',unpacked),('relocated',relocated),('generated',generated))},
                snapshot_reader_sha256=sha((ROOT/'research/quondam/snapshot_state.py').read_bytes()),
                transcript_sha256=sha((directory/'monitor.log').read_bytes()),session=session,
                checkpoints=records,screenshots=images,character_rom_captures=rom_captures,
                established_checkpoints_exact=all(r['exact'] for r in records if r['established_checkpoint']),
                all_native_ram_snapshot_pairs_exact=all(r['checks'][0]['exact'] for r in records),
                scope='Original native SFX/wrapper/initializer captures versus established byte contracts. No skipped entry, supplied raster/ROM values, whole-image oracle or physical-VIC claim.')
    output.mkdir(parents=True,exist_ok=True)
    target=output/'native-evidence.json'; target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(established_checkpoints_exact=result['established_checkpoints_exact'],
                          all_native_ram_snapshot_pairs_exact=result['all_native_ram_snapshot_pairs_exact'],
                          stages=[r['stage'] for r in records],receipt=str(target.relative_to(ROOT))),indent=2))
    if not result['established_checkpoints_exact'] or not result['all_native_ram_snapshot_pairs_exact']:
        raise SystemExit(1)


if __name__=='__main__': main()
