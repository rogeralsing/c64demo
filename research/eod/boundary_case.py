#!/usr/bin/env python3
"""Passively accept the closed EOD natural visibility-boundary native case."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/eod'
CASE = BASE/'native-06'
REJECTED = BASE/'native-05'
DISK = BASE/'release/EdgeOfDisgrace_1a.d64'
# The native owner supplies these only after explicit terminal closure.
CASE_SHA = 'd328247aab0c1a8953189ea5acfe9aa1bd29a39d04cab5857814309b8f7cca37'
MANIFEST_SHA = 'f683b6f95db04b2ad862de322793595031eb63355c3adf7305156164630afe1c'
COMMANDS_SHA = '39e096b3e9eb2a79b57bd6fdbebd5cd0862c187c9bd08e806c1e234ca374781e'
REJECTED_SHA = 'b4474ba08c26de5edbebe9a984226734df937486d98190a00eb9a01d74555d79'
FILE_COUNT, TOTAL_BYTES, COMMAND_COUNT = 47, 5423132, 148
EXPECTED_STATES = {
    'sys': (0x080d, 6940182),
    'after52': (0x0709, 418809379),
    'p082-begin': (0x546a, 472466695),
    'p082-vertices': (0x5473, 472470418),
    'p082-visibility': (0x5476, 472472392),
    'p082-body': (0x17db, 472510952),
    'p082-prefix-before': (0x1a73, 472522767),
    'p082-filled': (0x1750, 472538208),
    'p082-cleared': (0x1753, 472545517),
    'p082-next-frame': (0x546a, 472545616),
    'p082-display-setup': (0x16bb, 472553166),
    'p082-display-mid': (0x5ba1, 472558117),
    'p082-display-complete': (0x5c9f, 472563791),
    'p028-begin': (0x546a, 476967903),
    'p028-vertices': (0x5473, 476971541),
    'p028-visibility': (0x5476, 476973486),
    'p028-body': (0x17db, 477010060),
    'p028-prefix-before': (0x1a73, 477023991),
    'p028-filled': (0x1750, 477039128),
    'p028-cleared': (0x1753, 477046479),
}
EXPECTED_WAITS = [{'utc': '2026-11-08T19:35:35.173086+00:00', 'kind': 'observation_timeout', 'status': 'partial', 'waiting': True, 'elapsed_seconds': 30.085, 'sequence': 12, 'id': 'natural-load52', 'command': 'x', 'internal': False, 'received_bytes': 0, 'action': 'Still pending; send interrupt or close. No retry or restart.'}]
EXPECTED_TRACE_HITS = [
    (86,12,0xd012,0x16bd,0x16c0,472553172),
    (86,12,0xd019,0x16c5,0x16c8,472553184),
    (92,12,0xd012,0x1732,0x1735,472562039),
    (92,12,0xd019,0x173a,0x173d,472562051),
]
PINS = {
    'research/eod/controller.py': '033bafb6ac6e97283175ac6713af0eef60cb7991b653ee1c98c47a1a4afa83c9',
    'research/eod/output_case.py': '1b5d654fd75c02c3c54abb28d40f8e58f9fe59afb1a6bf01cc74d56ec1213c1d',
    'research/eod/native_boot.py': 'f1c0c0eaa4be5380bec55b84b34461b43b0065689a0ab94342c411dffb53bb55',
    'research/verify_vice_live.py': 'f3ec454250bcbbc23bb32ad5845cfdc0f540fd3f594df2c55aac8a3dda82d05a',
    'research/vice_session_live.py': '4340d1b0394fa612f5e6a71edddcbc2daf947e59c4c3013ab3b850c886dc621c',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'build/research/eod/release/EdgeOfDisgrace_1a.d64': '0624697997c57209929fc36ff7121ec7c61760a88576edbf0768d63e77d28956',
    'build/research/eod/file-analysis/accepted-03/file-proof.json': 'fb8e819f854fd500acb34ea023508a9966f95914f38e1c6de0db77e3f2381db9',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-051.decoded.prg': 'e4899712681147b233a960d675aab369feebac4ba149073f1051d45f78b5312c',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-052.decoded.prg': '3adc5e1b6990cf41b3d93954de9d92bd3da62b4b562fc636cbd827cf94d67c04',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
}
TARGETS = (('p082',1,82),('p028',1,28))
STAGES = {'begin':0x546a,'vertices':0x5473,'visibility':0x5476,'body':0x17db,
          'prefix-before':0x1a73,'filled':0x1750,'cleared':0x1753}
TRACE_RANGES = ((0xd000,0xd02e),(0xdd00,0xdd03),(0x6c00,0x6fff),
                (0x7000,0x77ff),(0xd800,0xdbff))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw=path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw))


def load(name,relative):
    spec=importlib.util.spec_from_file_location(name,ROOT/relative)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def listing(path):
    return [dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
            for p in sorted(path.iterdir()) if p.is_file()]


def audit_wire():
    assert all(not s.startswith('PENDING') for s in (CASE_SHA,MANIFEST_SHA,COMMANDS_SHA,REJECTED_SHA)), 'Only accept owner-closed, pinned cases'
    assert FILE_COUNT and TOTAL_BYTES and COMMAND_COUNT and EXPECTED_STATES
    assert EXPECTED_WAITS is not None
    wire=load('eod_boundary_wire','research/verify_vice_live.py')
    wire.BASE,wire.CASE_PINS=BASE,{'native-06':CASE_SHA}
    source=(ROOT/'research/verify_vice_live.py').read_text()
    node=next(n for n in ast.parse(source).body if isinstance(n,ast.FunctionDef) and n.name=='audit_session')
    original=ast.get_source_segment(source,node)+'\n'
    old='assert session["startup_mode"] == "manual monitor load" and "-autostart" not in session["command"]'
    replacement=('assert session["startup_mode"] == "autostart"\n'
        '    assert session["program"] == '+repr(str(DISK))+'\n'
        '    for flag in ("-autostart", "-8"):\n'
        '        assert session["command"].count(flag) == 1\n'
        '        assert session["command"][session["command"].index(flag)+1] == '+repr(str(DISK)))
    assert original.count(old)==1
    adapted=original.replace(old,replacement)
    exec(compile(adapted,'<exact-EOD-side1a-boundary-startup>','exec'),wire.__dict__)
    case=wire.audit_session('native-06');responses=case['responses']
    assert not case['partial'] and not case['cancelled']
    assert sorted(responses)==list(range(1,COMMAND_COUNT+1))
    assert all(row['status']=='completed' for row in responses.values())
    assert all(row['purpose']=='ordinary' for row in case['requests'])
    commands=[responses[n]['command'] for n in range(1,COMMAND_COUNT+1)]
    assert sha(json.dumps(commands,separators=(',',':')).encode())==COMMANDS_SHA
    assert not any(e['kind'].startswith('interrupt_') for e in case['events'])
    assert not any(re.search(r'ERROR --|Syntax error|Unknown resource',r['response']) for r in responses.values())
    assert case['waits']==EXPECTED_WAITS
    assert all(responses[r['sequence']]['status']=='completed' for r in case['waits'])
    launch=case['session']['command']
    assert '-pal' in launch and launch[launch.index('-speed')+1]=='100'
    assert '+warp' in launch and '+autostart-warp' in launch
    assert '-drive8truedrive' in launch and launch[launch.index('-drive8type')+1]=='1541'
    path=BASE/'native-06-files-accepted.json'
    assert sha(path.read_bytes())==MANIFEST_SHA
    manifest=json.loads(path.read_text());files=listing(CASE)
    assert files==manifest['files'] and len(files)==manifest['file_count']==FILE_COUNT
    assert sum(r['bytes'] for r in files)==manifest['total_bytes']==TOTAL_BYTES
    assert sha(json.dumps(files,sort_keys=True,separators=(',',':')).encode())==CASE_SHA
    return wire,case,dict(original_function_sha256=sha(original.encode()),adapted_function_sha256=sha(adapted.encode()),
        exact_startup_replacement=replacement,no_event_filter_or_other_auditor_change=True)


def rejected_startup():
    files=listing(REJECTED)
    assert sha(json.dumps(files,sort_keys=True,separators=(',',':')).encode())==REJECTED_SHA
    session=json.loads((REJECTED/'session.json').read_text())
    events=[json.loads(s) for s in (REJECTED/'events.jsonl').read_text().splitlines()]
    assert session['observer_error']=="OSError(22, 'Invalid argument')"
    assert session['exit_code']==-15 and session['owned_process_reaped'] and session['closed_utc']
    assert [r['kind'] for r in events]==['owned_process_started','observer_error','owned_terminate_requested','closed']
    assert events[0]['pid']==events[2]['pid']==session['pid']
    assert events[0]['command']==session['command']
    assert events[1]['error']==session['observer_error']
    assert all(events[3][k]==v for k,v in session.items())
    assert all((REJECTED/name).read_bytes()==b'' for name in ('input.bin','sent.bin','received.bin','monitor.log'))
    assert not list(REJECTED.glob('*.vsf')) and not list(REJECTED.glob('*-ram.bin'))
    return dict(case='native-05',listing_sha256=REJECTED_SHA,files=[artifact(REJECTED/r['name']) for r in files],
        session=session,events=events,ordinary_commands=0,captures=0,
        retained_as_rejected_startup=True,not_an_emulation_or_shader_failure=True,
        cause_scope='Owner recorded no-TTY observer startup; retained journal directly proves OSError22 before any monitor command/capture. No retry or continuation of this case.')


def command_audit(case):
    grammar=[r'r',r'sidefx off',r'bank ram',r'help (?:break|trace|command)',r'warp(?: on| off)?',
        r'resourceget "Speed"',r'delete [0-9]+',r'break [0-9a-f]{4}',
        r'break exec 0000 ffff if \(RL == \$[0-9a-f]+\) && \(CY >= \$[0-9a-f]+\) && \(CY <= \$[0-9a-f]+\)',
        r'condition [0-9]+ if \(@ram:\$1767 == \$0a\) && \(@ram:\$5514 == \$01\) && \(@ram:\$5513 == \$[0-9a-f]{2}\)',
        r'trace store [0-9a-f]{4} [0-9a-f]{4}',r'command [0-9]+ "r"',r'x',
        r'bsave "'+re.escape(str(CASE))+r'/[a-z0-9-]+-ram\.bin" 0 0000 ffff',
        r'dump "'+re.escape(str(CASE))+r'/[a-z0-9-]+\.vsf"',
        r'screenshot "'+re.escape(str(CASE))+r'/[a-z0-9-]+\.png" 2']
    for row in case['responses'].values():
        assert any(re.fullmatch(pattern,row['command']) for pattern in grammar),row['command']
    return dict(all_commands_match_observation_grammar=True,manual_RAM_PC_register_write_or_restore_commands=0,
        pinned_ordered_commands_sha256=COMMANDS_SHA)


def states_and_continuations(memories,captures,helper):
    states={r['stem']:r['registers'] for r in captures}
    assert set(states)==set(EXPECTED_STATES)
    for stem,(pc,clock) in EXPECTED_STATES.items():
        assert (states[stem]['pc'],states[stem]['clock'])==(pc,clock),stem
    records=[]
    for name,phase,counter in TARGETS:
        stems={stage:name+'-'+stage for stage in STAGES}
        for stage,stem in stems.items():assert states[stem]['pc']==STAGES[stage]
        assert list(memories[stems['begin']][0x5513:0x5515])==[counter,phase]
        sp=states[stems['begin']]['sp']
        assert helper.continuation(memories[stems['begin']],sp)==0x17db
        assert all(states[stems[stage]]['sp']==sp for stage in ('vertices','visibility'))
        assert (states[stems['body']]['sp']-sp)&255==2
        before,filled,cleared=(stems[s] for s in ('prefix-before','filled','cleared'))
        assert helper.continuation(memories[before],states[before]['sp'])==0x1750
        assert (states[filled]['sp']-states[before]['sp'])&255==2
        assert states[filled]['sp']==states[cleared]['sp']
        records.append(dict(name=name,phase=phase,counter=counter,captures=stems,
            natural_saved_continuations_checked=True,
            consecutive_intervals=[dict(begin=stems[a],end=stems[b],cycles=states[stems[b]]['clock']-states[stems[a]]['clock']) for a,b in zip(STAGES,list(STAGES)[1:])]))
    return records


def mode_bindings(case,captures,helper):
    responses=case['responses'];queries=[];scopes=[]
    for row in responses.values():
        if row['command']=='warp':
            assert 'Warp mode is off.' in row['response'];queries.append(helper.response_reference(row))
        elif row['command']=='resourceget "Speed"':
            assert re.search(r'Speed\s*=\s*100',row['response']);queries.append(helper.response_reference(row))
    assert [responses[n]['command'] for n in (COMMAND_COUNT-1,COMMAND_COUNT)]==['warp','resourceget "Speed"']
    for capture in captures:
        if capture['stem'] in ('sys','after52'):continue
        register=capture['register_sequence']
        changed=max(n for n in responses if n<register and responses[n]['command'] in ('warp on','warp off'))
        assert responses[changed]['command']=='warp off'
        warp=max(n for n in responses if changed<n<register and responses[n]['command']=='warp')
        speed=max(n for n in responses if changed<n<register and responses[n]['command']=='resourceget "Speed"')
        scopes.append(dict(stem=capture['stem'],warp_off_sequence=changed,actual_warp_query_sequence=warp,actual_speed_query_sequence=speed))
    return dict(actual_query_responses=queries,capture_query_bindings=scopes,navigation_warp_declared=True,endpoint_queries_repeated=True)


def display_trace(case,captures,original,wire,helper):
    """Retain every configured monitor instruction hit with its attached r."""
    responses=case['responses'];capturemap={r['stem']:r for r in captures}
    names={stage:next(stem for stem in capturemap if stem.endswith('display-'+stage))
           for stage in ('setup','mid','complete')}
    setup,mid,complete=(capturemap[names[k]] for k in ('setup','mid','complete'))
    assert setup['registers']['pc']==0x16bb
    for capture,line,low,high in ((mid,130,31,35),(complete,220,35,45)):
        regs=capture['registers'];assert regs['line']==line and low<=regs['cycle']<=high
    assert setup['registers']['clock']//19656==mid['registers']['clock']//19656==complete['registers']['clock']//19656
    arming=[]
    for seq,row in sorted(responses.items()):
        if not setup['snapshot_sequence']<seq<mid['stop_sequence']:continue
        if not row['command'].startswith('trace store '):continue
        match=re.fullmatch(r'trace store ([0-9a-f]{4}) ([0-9a-f]{4})',row['command']);assert match
        first,last=int(match[1],16),int(match[2],16)
        number=re.search(r'TRACE: ([0-9]+)  C:\$'+match[1]+r'-\$'+match[2]+r'  \(Trace store\)',row['response']);assert number
        number=int(number[1]);context=responses[seq+1]
        assert context['command']==f'command {number} "r"'
        assert context['response'].startswith(f'Setting checkpoint {number} command to: r')
        arming.append(dict(number=number,first=first,last=last,setup=helper.response_reference(row),attached_r=helper.response_reference(context)))
    assert [(r['first'],r['last']) for r in arming]==list(TRACE_RANGES)
    watched={r['number']:r for r in arming}
    # Before completion, no trace can be deleted/rearmed or have its attachment
    # changed. Breakpoint changes for the two natural raster stops are distinct.
    for seq,row in responses.items():
        if not arming[-1]['attached_r']['sequence']<seq<=complete['stop_sequence']:continue
        assert not row['command'].startswith('trace ')
        if row['command'].startswith(('delete ','command ')):
            assert int(row['command'].split()[1]) not in watched
    hit_pattern=re.compile(r'#([0-9]+) \(Trace store ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+\n')
    instruction=re.compile(r'^\.C:([0-9a-f]{4})\s+([0-9A-F]{2}(?: [0-9A-F]{2}){0,2})\s+(.+?)\s+- A:([0-9A-F]{2}) X:([0-9A-F]{2}) Y:([0-9A-F]{2}) SP:([0-9a-f]{2}) ([NV\-BDIZC.]{8})\s+(\d+)\n',re.M)
    hits=[];windows=[]
    resumes=[row for seq,row in sorted(responses.items()) if setup['stop_sequence']<seq<=complete['stop_sequence'] and row['command']=='x']
    assert [r['sequence'] for r in resumes]==[mid['stop_sequence'],complete['stop_sequence']]
    for row in resumes:
        text=row['response'];assert text.isascii()
        matches=list(hit_pattern.finditer(text))
        assert text.count('(Trace store ')==len(matches)
        stop=re.search(r'^#[0-9]+ \(Stop on',text,re.M);assert stop
        windows.append(dict(response=helper.response_reference(row),instruction_hits=len(matches)))
        for index,match in enumerate(matches):
            end=matches[index+1].start() if index+1<len(matches) else stop.start()
            assert end>match.end()
            segment=text[match.end():end];ins=instruction.search(segment)
            assert ins and segment.count('Executing: r')==1
            regs=wire.registers(segment)
            number,address,line,cycle=int(match[1]),int(match[2],16),int(match[3]),int(match[4])
            assert number in watched and watched[number]['first']<=address<=watched[number]['last']
            pc=int(ins[1],16);raw=bytes.fromhex(ins[2])
            assert original[pc:pc+len(raw)]==raw
            assert regs['pc']==pc+len(raw)
            assert regs['clock']==int(ins[9]) and (regs['line'],regs['cycle'])==(line,cycle)
            assert [regs[k] for k in ('a','x','y','sp')]==[int(ins[k],16) for k in (4,5,6,7)]
            assert regs['port00']==0x2f
            hits.append(dict(sequence=row['sequence'],checkpoint=number,monitored_address=address,
                monitor_instruction_PC=pc,instruction_hex=raw.hex(),instruction=ins[3],
                attached_post_instruction_registers=regs,original_source_range=[pc,pc+len(raw)],
                received_first=row['received_first']+match.start(),received_end=row['received_first']+end,
                trace_block_bytes=end-match.start(),trace_block_sha256=sha(text[match.start():end].encode()),
                response=helper.response_reference(row),physical_bus_write_count_inferred=False))
    actual=[(h['sequence'],h['checkpoint'],h['monitored_address'],h['monitor_instruction_PC'],h['attached_post_instruction_registers']['pc'],h['attached_post_instruction_registers']['clock']) for h in hits]
    assert actual==EXPECTED_TRACE_HITS
    return dict(capture_names=names,arming=arming,raw_windows=windows,observed_instruction_hits=hits,
        instruction_hits=len(hits),no_unparsed_monitor_trace_hit=True,
        no_other_monitor_trace_hits_in_watched_ranges=True,
        RMW_limit='One monitored RMW instruction hit is not a one-physical-bus-write claim.',
        device_classification_scope='Actual attached CPU ports remain exposed per hit; graphics/device relevance and committed pixels belong to the independent display consumer.',
        trace_parser_scope='Literal trace headers may follow a monitor prompt prefix; all complete raw responses and byte ranges remain retained.')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve();out.relative_to((BASE/'boundary-case-analysis').resolve())
    assert not out.exists(),'Choose a fresh output directory'
    assert not CASE_SHA.startswith('PENDING'),'Only accept an owner-closed, pinned case'
    for name,pin in PINS.items():assert sha((ROOT/name).read_bytes())==pin,name
    wire,case,adapter=audit_wire()
    rejected=rejected_startup()
    controller=load('eod_boundary_capture_reader','research/eod/controller.py');controller.CASE=CASE
    reader=load('eod_boundary_snapshot','research/quondam/snapshot_state.py')
    memories,captures=controller.capture_pairs(reader,wire,case)
    helper=load('eod_boundary_frozen_helpers','research/eod/output_case.py');helper.CASE=CASE;helper.TARGETS=TARGETS
    original,original_inputs=helper.source_memory(controller)
    guards=helper.source_guards(memories,original)
    targets=states_and_continuations(memories,captures,helper)
    commands=command_audit(case);modes=mode_bindings(case,captures,helper)
    checkpoints=helper.checkpoint_bindings(case,captures)
    trace=display_trace(case,captures,original,wire,helper)
    payloads=[]
    for stem,name,length in (('sys','dos-001.raw.prg',874),('after52','trackmo-052.decoded.prg',13603)):
        path=BASE/'file-analysis/accepted-03/EdgeOfDisgrace_1a'/name
        start,data=controller.prg(path)
        assert len(data)==length and memories[stem][start:start+length]==data
        payloads.append(dict(capture=stem,source=artifact(path),start=start,bytes=length,all_equal=True))
    after52=next(r for r in captures if r['stem']=='after52')['registers']
    assert after52['a']==0 and after52['flags']&1 and not after52['flags']&8
    rejection_path=BASE/'native-05-startup-rejection.json'
    rejection=json.loads(rejection_path.read_text())
    assert rejection['pass_'] and not rejection['accepted_native_observation']
    assert rejection['session']==rejected['session'] and rejection['files']==rejected['files']
    boot=load('eod_boundary_port_sources','research/eod/native_boot.py');ports=boot.primary_port_sources()
    checked=Path(__file__).read_bytes()
    proof=dict(pass_=True,
        scope='Closed fresh original EOD natural p082/p028 stage and one p082 display-window custody; geometry, culling meaning, software/pixel predictions belong to separate consumers',
        producer=artifact(Path(__file__)),inputs=[artifact(ROOT/p) for p in PINS]+original_inputs+[artifact(rejection_path)],
        case_sha256=CASE_SHA,case_manifest=artifact(BASE/'native-06-files-accepted.json'),wire=wire.summary(case),adapter=adapter,
        command_audit=commands,waiting_notices=case['waits'],rejected_startup=rejected,captures=captures,
        primary_port_schema=ports,original_payloads=payloads,original_source_generation_guards=guards,
        phase_counter_targets=targets,actual_modes=modes,checkpoint_bindings=checkpoints,display_trace=trace,
        reused_frozen_helpers=['controller.capture_pairs unchanged','output_case.source_memory','output_case.source_guards','output_case.continuation','output_case.response_reference with CASE rebound','output_case.checkpoint_bindings with CASE/TARGETS rebound'],
        limits=['Original disk startup and natural predicates only; no RAM, register or PC mutation, restore, interrupt, retry or event filtering in accepted native06.',
            'Native05 remains a separate terminal/reaped startup rejection with no monitor commands or captures, not a shader result.',
            'The sole wire-auditor adaptation replaces the manual-load startup assertion in memory; the frozen controller capture parser remains unchanged.',
            'All trace hits retain attached port/readback context and exact raw blocks; no physical RMW bus-write count or addressed-device classification is inferred here.',
            'Finite source/checkpoint/state custody does not itself prove correct geometry, culling, visible artifacts, completed buffers, pixels, all poses, full312-line fields, delivered FPS, tearing-free publication or savings.',
            'No emulator, native process, socket, CPU interpreter, subprocess, build or downloaded host execution occurs in passive acceptance.'],
        outputs=[dict(name='boundary_case.checked.py',bytes=len(checked),sha256=sha(checked))])
    raw=(json.dumps(proof,indent=2)+'\n').encode()
    out.mkdir(parents=True)
    (out/'boundary_case.checked.py').write_bytes(checked)
    (out/'boundary-case-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,pairs=len(captures),receipt_bytes=len(raw),receipt_sha256=sha(raw),trace_instruction_hits=len(trace['observed_instruction_hits']))))


if __name__=='__main__':main()
