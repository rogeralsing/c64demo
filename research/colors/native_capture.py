#!/usr/bin/env python3
"""Read existing Colors native captures; no CPU, emulator or monitor actions.

Known byte oracles cover the loaded original boot and its pristine resident.
The first $8000 image is an observed handoff, not an independent depack oracle.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/colors'
spec = importlib.util.spec_from_file_location('colors_nine_readers', ROOT/'research/nine/native_capture.py')
readers = importlib.util.module_from_spec(spec)
spec.loader.exec_module(readers)
contexts, physical_ram, comparison, sha = readers.contexts, readers.physical_ram, readers.comparison, readers.sha
sys.path.insert(0,str(ROOT/'research/quondam'))
from snapshot_state import read_snapshot, module_payload

BOOT_PROOF_SHA = 'aa56bdc1b24b4365ab8f72b767a124c2b6b013b2790200fa4ef864b7a186b0dc'
LOADER_PROOF_SHA = 'feef4880f2521bf82046729b1db524c92f09cf006cc6f022febfffc9221ccb0f'
BOOT_SHA = '6c83458c3ab427c4d3a11abe50ffbfcb6d8922f99da864b4a54cac412f967f3b'
DISK_SHA = '94bde11ed515f6312fbd77efff9f1fe5c2cdbf25587f0eabada566e0430b1ad6'
RESIDENT_SHA = 'b09c13f9f60a28aa87cf1b157b4035df325eb60bf6d79fe8f176cf7aa606db48'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--capture',type=Path,default=BASE/'native-01')
    parser.add_argument('--output',type=Path,default=BASE/'native-analysis')
    parser.add_argument('--allow-live',action='store_true')
    args=parser.parse_args()
    directory,output=args.capture.resolve(),args.output.resolve()
    session=json.loads((directory/'session.json').read_text())
    assert args.allow_live or session.get('closed_utc'),'Final receipt requires owner-closed session'
    assert sha((BASE/'binary/boot-proof.json').read_bytes())==BOOT_PROOF_SHA
    assert sha((BASE/'binary/loader-identification.json').read_bytes())==LOADER_PROOF_SHA
    disk=BASE/'extracted/Colors [Lethargy] 1.d64'
    assert sha(disk.read_bytes())==DISK_SHA
    assert Path(session['program']).resolve()==disk.resolve(),'Expected original side1 D64 cold boot'
    blob=(BASE/'binary/side1-boot.prg').read_bytes()
    assert len(blob)==849 and sha(blob)==BOOT_SHA
    boot=bytearray(65536); boot[0x801:0xb50]=blob[2:]
    resident=bytearray(65536); resident[0x160:0x300]=boot[0x9b0:0xb50]
    assert sha(resident[0x160:0x300])==RESIDENT_SHA
    transcript=(directory/'monitor.log').read_text(errors='replace')
    events=contexts(transcript)
    snapshots,pending={},[]
    for event in events:
        if event['command']!='dump':continue
        path=directory/event['filename']
        if args.allow_live and not path.exists():pending.append(event);continue
        state=read_snapshot(path)
        assert state['modules']['MAINCPU']['version']==[1,4]
        cpu=module_payload(path,'MAINCPU')
        assert int.from_bytes(cpu[:8],'little')==event['registers']['clock']
        assert int.from_bytes(cpu[12:14],'little')==event['registers']['pc']
        key=event['registers']['pc'],event['registers']['clock']
        snapshots.setdefault(key,[]).append((path,state,event['transcript_line']))
    records,images=[],[]
    for event in events:
        if event['command'] not in ('bsave','screenshot','scrsh'):continue
        path=directory/event['filename']; register=event['registers']
        key=register['pc'],register['clock']
        if args.allow_live and (not path.exists() or key not in snapshots):pending.append(event);continue
        assert key in snapshots,('No same-stop VSF',path)
        choices=snapshots[key]
        named=[s for s in choices if s[0].stem==path.stem.removeprefix('ram-')]
        if len(named)==1:snapshot,state,_=named[0]
        elif len(choices)==1:snapshot,state,_=choices[0]
        else:
            assert event['command']!='bsave',('Ambiguous RAM/VSF pair',path)
            choices=sorted(choices,key=lambda s:abs(s[2]-event['transcript_line']))
            assert abs(choices[0][2]-event['transcript_line'])!=abs(choices[1][2]-event['transcript_line'])
            snapshot,state,_=choices[0]
        if event['command']!='bsave':
            images.append(dict(file=str(path.relative_to(ROOT)),sha256=sha(path.read_bytes()),registers=register,
                               snapshot=str(snapshot.relative_to(ROOT)),scope='Native output observation; no independent pixel oracle'))
            continue
        assert event['bank']=='ram' and event['first']==0 and event['end_inclusive']==65535
        actual=path.read_bytes(); assert len(actual)==65536
        checks=[comparison(actual,physical_ram(snapshot),0,65536,'All native raw RAM versus same-stop VSF RAM')]
        observations=[]; pc=register['pc']; stage='later_observation'; established=False
        detail={}
        if pc==0x810:
            stage,established='original_basic_SYS_entry',True
            assert actual[0x810:0x81f]==bytes.fromhex('a9 ff 85 fc a2 04 a9 08 85 ba a5 ba 20 0c ed')
            checks.append(comparison(actual,boot,0x801,0xb50,'All 847 original loaded boot bytes before first instruction'))
        elif pc==0x8c7:
            stage,established='resident_before_video_standard_patch',True
            assert actual[0x8b3:0x8c7]==boot[0x8b3:0x8c7]
            checks.append(comparison(actual,resident,0x160,0x300,'All 416 literal resident-copy bytes'))
            checks.append(comparison(actual,boot,0x9b0,0xb50,'All 416 original resident-source bytes'))
        elif pc==0x8000:
            stage='first_configured_handoff_observation'
            observations.append(dict(first_image_signature=actual[0x8000:0x8040].hex(' '),
                image_has_independent_byte_oracle=False,
                scope='Observed original side1 configured return; no offline packed-bundle/image equality is inferred'))
            observations.append(comparison(actual,resident,0x160,0x300,'All later resident differences retained; no mutable mask'))
        elif pc==0x8e4e:
            assert actual[pc:pc+17]==bytes.fromhex('48 8a 48 98 48 20 45 80 20 52 80 20 72 80 20 42 84')
            stage='field_before_next_phase_update'
            detail=dict(phase=actual[0x8046],D018=state['vicii']['regs'][0x18],
                        CIA2_PRA=state['cia']['CIA2']['pra'],CIA2_DDRA=state['cia']['CIA2']['ddra'],
                        sprite_colors=state['vicii']['regs'][0x27:0x2f],
                        sprite_pointer_tables=[dict(first=base,bytes=list(actual[base:base+8]))
                                               for base in (0x27f8,0x67f8,0xa7f8,0xe7f8)],
                        interpretation='State belongs to the completed previous beam; this handler has not advanced $8046 yet. No pixel oracle here.')
        records.append(dict(file=str(path.relative_to(ROOT)),sha256=sha(actual),registers=register,
            snapshot=str(snapshot.relative_to(ROOT)),snapshot_sha256=state['file_sha256'],
            stage=stage,established_checkpoint=established,checks=checks,observations=observations,detail=detail,
            exact=all(c['exact'] for c in checks),vic_raster=[state['vicii']['raster_line'],state['vicii']['raster_cycle']],
            vic_registers=state['vicii']['regs']))
    required={'original_basic_SYS_entry','resident_before_video_standard_patch','first_configured_handoff_observation'}
    missing=sorted(required-{r['stage'] for r in records})
    fields=[r for r in records if r['stage']=='field_before_next_phase_update' and 'stable-field-' in r['file']]
    cadence=[]
    for previous,current in zip(fields,fields[1:]):
        a,b=previous['registers'],current['registers']
        elapsed=b['clock']-a['clock']
        phase_advance=current['detail']['phase']==(previous['detail']['phase']+1)%3
        jitter=(b['raster_line']-a['raster_line'])*63+b['raster_cycle']-a['raster_cycle']
        exact=phase_advance and elapsed-jitter==19656
        cadence.append(dict(first=previous['file'],second=current['file'],elapsed_clocks=elapsed,
                            raster_position_delta_clocks=jitter,frame_clocks=elapsed-jitter,
                            phase_advance_modulo3=phase_advance,exact=exact,
                            scope='These consecutive named stable-field captures only; no whole-demo cadence or full-image period claim'))
    result=dict(provisional=bool(args.allow_live),session_closed=bool(session.get('closed_utc')),session=session,
        disk_sha256=DISK_SHA,boot_sha256=BOOT_SHA,resident_sha256=RESIDENT_SHA,
        boot_proof_sha256=BOOT_PROOF_SHA,loader_proof_sha256=LOADER_PROOF_SHA,
        script_sha256=sha(Path(__file__).read_bytes()),transcript_sha256=sha(transcript.encode()),
        reader_sha256={name:sha((ROOT/name).read_bytes()) for name in
                      ('research/nine/native_capture.py','research/quondam/snapshot_state.py')},
        checkpoints=records,screenshots=images,raw_RAM_VSF_pair_count=len(records),screenshot_count=len(images),
        pending_capture_events=pending,missing_required_stages=missing,
        stable_field_cadence=cadence,
        all_RAM_VSF_pairs_exact=all(r['checks'][0]['exact'] for r in records),
        established_byte_contracts_exact=all(r['exact'] for r in records if r['established_checkpoint']),
        complete=not missing and not pending,
        scope='Passive original boot/resident byte checks, observed first handoff and bounded stable-field phase cadence; no independent full-image oracle, complete display model, whole-demo timing or analog-color claim')
    result['pass']=(result['all_RAM_VSF_pairs_exact'] and result['established_byte_contracts_exact']
                    and all(c['exact'] for c in cadence) and (args.allow_live or result['complete']))
    output.mkdir(parents=True,exist_ok=True)
    path=output/('native-evidence-provisional.json' if args.allow_live else 'native-evidence.json')
    path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ('pass','provisional','complete','missing_required_stages')},indent=2))
    assert result['pass'],f'Preserved failure details in {path}'


if __name__=='__main__':main()
