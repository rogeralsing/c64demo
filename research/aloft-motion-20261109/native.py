#!/usr/bin/env python3
"""Passive custody of a closed original Aloft motion-input case.

The owner alone controls native VICE. This reader stays fail-closed while the
case is live, reuses frozen strict wire/pair readers, and separates genuine
pre-motion inputs from late program-result oracles. No CPU execution occurs.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-motion-20261109'
ANALYSIS = BASE / 'native-analysis'
FROZEN_NATIVE = ROOT / 'research/aloft-execution-20261109/native.py'
FROZEN_NATIVE_SHA = '99bea080d4e2fa74f4c3656dfd6084af752e0747247c1ef67e7688c1ec92d967'
READER = ROOT / 'research/quondam/snapshot_state.py'
READER_SHA = 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a'
TABLE_PROOF = BASE / 'table-analysis/accepted-01/motion-table-proof.json'
TABLE_SHA = 'b1c79ce00b3fa4694786ec6be8786b7c949b0b176514d8fcceb533441379a0fa'
OBSERVER_PROOF = ROOT / 'build/research/aloft-pixels-20261109/display-analysis/source-route-01/store-route-proof.json'
OBSERVER_SHA = '2e7acf05f320399b27759d8811a0c0c074ba47511ac0466418740d65dfbf483a'
# Populated only from the owner's authoritative closed manifest/profile.
CLOSED_PROFILE = ANALYSIS / 'closed-profile-01.json'
CLOSED_PROFILE_SHA = '40abe07db2e914f82904956fd0722d7b85df61296f374c38ae75765a606b5c9b'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def pinned(path, digest):
    raw = path.read_bytes()
    assert sha(raw) == digest, str(path)
    return raw


def meta(path):
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=sha(raw))


def load(name, path, digest):
    pinned(path, digest)
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def closed_readers(profile):
    """No frozen source edit: parameterize the retained case's base directory."""
    assert profile['owner_closed'] is True
    assert profile['owned_process_reaped'] is True and profile['unified_handle_terminal'] is True
    frozen = load('aloft_motion_frozen_native_readers', FROZEN_NATIVE, FROZEN_NATIVE_SHA)
    frozen.BASE = BASE
    case_path, files = frozen.closed_inventory(profile)
    wire, case, startup_adapter = frozen.audit_wire(profile, case_path)
    reader = load('aloft_motion_snapshot_reader', READER, READER_SHA)
    memories, captures, pair_adapter = frozen.paired_captures(reader, wire, case, case_path)
    generations = frozen.checkpoint_generations(case)
    return frozen, reader, wire, case, memories, captures, generations, dict(
        files=files, startup_adapter=startup_adapter, pair_adapter=pair_adapter,
        parameterized_base=BASE.relative_to(ROOT).as_posix(),
        frozen_source_unchanged=True, raw_events_and_waits_unfiltered=True)


def checked_ref(ref):
    raw = pinned(ROOT / ref['path'], ref['sha256'])
    assert len(raw) == ref['bytes']
    return raw


def output_meta(path):
    raw = path.read_bytes()
    return dict(name=path.name, bytes=len(raw), sha256=sha(raw))


def emit(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def natural_bindings(frozen, case, generations, captures, memories):
    original = frozen.function_source('research/aloft-execution-20261109/native.py', 'natural_bindings')
    old, new = "if row['command'] == 'x']) == 18", "if row['command'] == 'x']) == 8"
    assert original.count(old) == 1
    adapted = original.replace(old, new)
    exec(compile(adapted, '<Aloft-motion-natural-pair-arity-only-adapter>', 'exec'), frozen.__dict__)
    bindings = frozen.natural_bindings(case, generations, captures, memories)
    return bindings, dict(original_function_sha256=sha(original.encode()),
                          adapted_function_sha256=sha(adapted.encode()), replacements=1,
                          exact_old_assertion=old, exact_replacement=new,
                          all_natural_stop_and_condition_checks_unchanged=True)


def command_audit(profile, frozen, case):
    rows = case['responses']
    assert sorted(rows) == list(range(1,85))
    assert all(r['status'] == 'completed' for r in rows.values())
    assert not case['waits'] and not case['partial'] and not case['cancelled']
    assert [n for n,r in rows.items() if r['internal']] == [1,2]
    permitted = re.compile(r'(?:r|x|bank ram|sidefx off|warp(?: on| off)?|dummy(?: on)?|resourceget "(?:Speed|VICIIModel|VICIIBorderMode|VICIIVSPBug)"|(?:enable|disable|delete) \d+|ignore \d+ \$[0-9a-f]+|command \d+ "r"|break(?: [0-9a-f]{4}(?: if [0-9a-z@$:() =&|!<>.]+)?)?|trace store [0-9a-f]{4} [0-9a-f]{4}|bsave "[^"\n]+" 0 0000 ffff|dump "[^"\n]+")',re.I)
    queries=[]
    bank=None
    for n,row in sorted(rows.items()):
        command,response=row['command'],row['response']
        assert permitted.fullmatch(command),(n,command)
        assert not re.search(r'ERROR --|Syntax error|Unknown resource',response)
        if command.startswith('bank '):bank=command[5:]
        if command.startswith('bsave '):assert bank=='ram'
        if command in ('warp','dummy') or command.startswith('resourceget '):
            queries.append(frozen.response_reference(case,row)|dict(response=response))
    assert rows[2]['command']=='sidefx off'
    assert [(n,r['command']) for n,r in rows.items() if r['command'] in ('warp on','warp off')]==[(18,'warp on'),(24,'warp off')]
    assert [(n,r['command']) for n,r in rows.items() if r['command'] in ('dummy on','dummy off')]==[(8,'dummy on')]
    assert rows[9]['response'].startswith('Checkpoints will trigger on dummy accesses.\n')
    for item in profile['final_resource_queries']:
        row=rows[item['sequence']]
        assert (row['command'],row['response'])==(item['command'],item['response'])
    assert [r['response'].split('\n')[0] for r in (rows[74],rows[75],rows[76],rows[77],rows[78],rows[79])]==[
        'Warp mode is off.','Speed=100','VICIIModel=1','VICIIBorderMode=0','VICIIVSPBug=0','Checkpoints will trigger on dummy accesses.']
    assert rows[84]['response'].startswith('No breakpoints are set\n')
    assert rows[55]['command']=='ignore 3 $3f' and rows[55]['response'].startswith('Will ignore the next 63 hits of checkpoint #3\n')
    launch=case['session']['command']
    assert '-pal' in launch and '-drive8truedrive' in launch and launch[launch.index('-drive8type')+1]=='1541'
    assert case['session']['exit_code']==-15 and case['session']['owned_process_reaped'] is True
    commands=[r['command'] for n,r in sorted(rows.items())]
    return dict(responses=84,public_commands=82,all_completed=True,interrupts=0,waits=[],errors=[],
                command_list_sha256=sha(json.dumps(commands,separators=(',',':')).encode()),
                queries=queries,later_selection=frozen.response_reference(case,rows[55]),
                later_index64_is_first_plus63_ignored_entries=True,
                no_payload_RAM_PC_write_restore_restart_or_disk_change_commands=True,
                final_all_checkpoints_deleted=True)


def source_generation(memories, captures):
    table=json.loads(pinned(TABLE_PROOF,TABLE_SHA))
    abi_ref=table['table_ABI']
    abi_path=TABLE_PROOF.parent/abi_ref['name']
    abi=json.loads(pinned(abi_path,abi_ref['sha256']))
    source_path=ROOT/'build/research/aloft-decode-20261109/color-analysis/accepted-01/bundle031-memory.bin'
    source=pinned(source_path,'95a344b261b1b28d229da9778df80bae06eff39470ff4515820ce4e1fa86869e')
    initialized_dispatcher=pinned(TABLE_PROOF.parent/abi['dispatcher_data']['name'],abi['dispatcher_data']['sha256'])
    phase_addresses=sorted({p[k] for p in abi['motion']['phases'] for k in ('X_operand','Y_operand','fade_in_operand','fade_out_operand')})
    rows=[]
    for capture in captures:
        stem=capture['stem']
        if stem=='sys':continue
        memory=memories[stem]
        for asset in abi['assets']:
            data=pinned(TABLE_PROOF.parent/asset['data']['name'],asset['data']['sha256'])
            assert memory[asset['base']:asset['end_exclusive']]==data
        for program in abi['programs']:
            data=pinned(TABLE_PROOF.parent/program['data']['name'],program['data']['sha256'])
            assert memory[program['base']:program['end_exclusive']]==data
        assert all(memory[a]==source[a] for a in range(0xf12f,0xf2c2) if a not in phase_addresses)
        assert memory[0xf133:0xf136]==bytes.fromhex('2000c0')
        assert memory[0xf136:0xf141]==source[0xf136:0xf141]
        assert memory[0xf11a:0xf11f]==source[0xf11a:0xf11f]
        assert all(memory[0x500+3*i]==0x20 and memory[0x501+3*i]==initialized_dispatcher[3*i+1] for i in range(200))
        assert memory[0x758]==0x60
        if stem=='body':
            assert memory[0x500:0x759]==initialized_dispatcher
            assert memory[0xf000:0xf02b]==source[0xf000:0xf02b]
        rows.append(dict(stem=stem,all2560_asset_bytes_equal_original=True,all7204_program_bytes_equal_source_initializer=True,
                         original_controller_code_range=[0xf12f,0xf2c2],explicit_mutable_operand_addresses=phase_addresses,
                         controller_code_equal_except_declared_inputs=True,all401_dispatcher_skeleton_bytes_equal=True,
                         initial601_dispatcher_compared=stem=='body'))
    return abi,dict(table_proof=meta(TABLE_PROOF),table_ABI=meta(abi_path),original_source=meta(source_path),
                    captures=rows,mutable_operands_recorded_not_normalized=True,
                    source_expected_table_and_program_bytes_used_for_generation_identity_only=True)


def phase_context(memory, context, abi):
    phases=[]
    for phase in abi['motion']['phases']:
        phases.append(dict(index=phase['index'],entry=phase['entry'],
                           X_operand=phase['X_operand'],Y_operand=phase['Y_operand'],
                           X=memory[phase['X_operand']],Y=memory[phase['Y_operand']],
                           fade_in_operand=phase['fade_in_operand'],fade_out_operand=phase['fade_out_operand'],
                           fade_in=memory[phase['fade_in_operand']],fade_out=memory[phase['fade_out_operand']]))
    return dict(active_controller=int.from_bytes(memory[0xf11b:0xf11d],'little'),
                controller_operand_bytes=list(memory[0xf11b:0xf11d]),ZP05=memory[5],ZP06=memory[6],
                phases=phases,palette_D020_D023=context['VIC']['regs'][0x20:0x24])


def field_ABIs(profile,frozen,case,points,captures,memories,context,hooks,abi):
    by_stem={x['stem']:x for x in captures}
    inputs,oracles,lifetimes=[],[],[]
    trace=next(p for p in points if p['id']==6 and p['created_sequence']==38)
    assert trace['kind']=='TRACE' and trace['operation']=='Trace store'
    assert (trace['first'],trace['last'])==(0x500,0x758)
    assert trace['setup']['command']=='trace store 0500 0758' and trace['attached_r_sequence']==39
    assert not any(u['command'].startswith('condition ') for u in trace['updates'])
    assert trace['deleted_sequence']==83
    assert len(hooks)==400 and {h['sequence'] for h in hooks}=={42,63}
    for field in profile['fields']:
        pre,post,wrapper=[by_stem[field['roles'][k]] for k in ('precall','postcall','postwrapper')]
        assert [x['registers']['pc'] for x in (pre,post,wrapper)]==[0xf133,0xf136,0xf11d]
        assert [x['stop_sequence'] for x in (pre,post,wrapper)]==[field['pre_run_sequence'],field['call_run_sequence'],field['wrapper_run_sequence']]
        assert trace['attached_r_sequence']<post['stop_sequence']
        if field['label']=='first':
            assert pre['snapshot_sequence']<trace['attached_r_sequence']
        assert frozen.enabled_at(trace,post['stop_sequence'])
        assert trace['deleted_sequence']>post['snapshot_sequence']
        assert not any(pre['snapshot_sequence']<u['sequence']<post['stop_sequence'] and u['command'].startswith('disable ') for u in trace['updates'])
        assert not any(pre['stop_sequence']<=n<=wrapper['snapshot_sequence'] and r['command'] in ('dummy on','dummy off','warp on','warp off') for n,r in case['responses'].items())
        reg=pre['registers'];memory=memories[pre['stem']]
        assert reg['flags']&4 and not reg['flags']&8
        assert reg['port00']==0x2e and reg['port01']==0x35
        assert (reg['x'],reg['y'])==(memory[0xf130],memory[0xf132])
        assert int.from_bytes(memory[0xf11b:0xf11d],'little')==0xf12f
        assert list(memory[0x100+reg['sp']+1:0x100+reg['sp']+3])==[0x1c,0xf1]
        assert [memories[x['stem']][5:7] for x in (pre,post,wrapper)]==[bytes([field['index'],2])]*3
        source_phase=phase_context(memory,context[pre['stem']],abi)
        inputs.append(dict(label=field['label'],invocation_index=field['index'],roles=field['roles'],input=dict(
            capture=pre,CPU=reg,C=reg['flags']&1,D=bool(reg['flags']&8),ports=pre['ports'],
            program_address=0xc000,phase_context=source_phase,
            caller_saved_return_address=0xf11c,
            program_source=abi['programs'][0]['data'],
            no_current_or_future_dispatcher_high_bytes_as_inputs=True)))
        actual=[h for h in hooks if h['sequence']==post['stop_sequence']]
        assert len(actual)==200
        for i,h in enumerate(actual):
            assert h['operation']=='store' and h['monitored_address']==0x502+3*i
            assert h['instruction_PC']==0xc006+9*i
            assert h['instruction_hex']==(bytes([0x8d])+ (0x502+3*i).to_bytes(2,'little')).hex()
            assert h['registers']['pc']==h['instruction_PC']+3
            assert h['registers']['sp']==reg['sp']-2
        endpoints=[]
        for role,capture in [('postcall',post),('postwrapper',wrapper)]:
            ram=memories[capture['stem']]
            endpoints.append(dict(role=role,capture=capture,CPU=capture['registers'],ports=capture['ports'],
                                  dispatcher_0500_bytes=list(ram[0x500:0x759]),
                                  phase_context=phase_context(ram,context[capture['stem']],abi)))
        oracles.append(dict(label=field['label'],roles=field['roles'],endpoints=endpoints,all200_store_hooks=actual,
                            source_store_values_from_actual_A_are_oracles_only=True))
        lifetimes.append(dict(label=field['label'],precall=pre['stem'],postcall=post['stem'],
                              watch=trace,start_after_capture=pre['snapshot_sequence'],through_capture=post['snapshot_sequence'],
                              attached_r_before_resume=True,unconditional_and_enabled_during_call=True,
                              dummy_on_and_unchanged=True,warp_off_and_unchanged=True,
                              actual_hook_count=200,elapsed_machine_cycles=post['registers']['clock']-reg['clock'],
                              hook_clocks_are_instruction_completion_not_bus_accesses=True))
    return inputs,oracles,lifetimes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    assert CLOSED_PROFILE is not None and CLOSED_PROFILE_SHA is not None, 'owner case closure/profile pins pending'
    profile = json.loads(pinned(CLOSED_PROFILE, CLOSED_PROFILE_SHA))
    assert profile['owner_closed'] is True
    out = (ROOT / args.output).resolve()
    out.relative_to(ANALYSIS)
    out.mkdir(parents=True, exist_ok=False)
    (out / 'native.checked.py').write_bytes(Path(__file__).read_bytes())
    pinned(TABLE_PROOF, TABLE_SHA)
    pinned(OBSERVER_PROOF, OBSERVER_SHA)
    frozen,reader,wire,case,memories,captures,points,adapters=closed_readers(profile)
    assert len(captures)==8
    owner=json.loads(checked_ref(profile['owner_closure']))
    assert owner['all_84_responses_completed'] is True
    assert all(owner[k]==0 for k in ('interrupts','timeouts','restarts','snapshot_restores','disk_changes','PC_or_RAM_mutations'))
    by_stem={x['stem']:x for x in captures}
    for expected in profile['pairs']:
        actual=by_stem[expected['stem']]
        assert (actual['save_sequence'],actual['snapshot_sequence'])==(expected['ram_sequence'],expected['snapshot_sequence'])
        assert (actual['ram'],actual['snapshot'])==(expected['ram'],expected['vsf'])
    bindings,natural_adapter=natural_bindings(frozen,case,points,captures,memories)
    adapters['natural_pair_count_adapter']=natural_adapter
    commands=command_audit(profile,frozen,case)
    assert {p['id'] for p in points}==set(range(1,7)) and all('deleted_sequence' in p for p in points)
    hooks=frozen.trace_hooks(case,wire,points,captures)
    context=frozen.machine_context(reader,memories,captures,ROOT/profile['case_relative'])
    abi,generation=source_generation(memories,captures)
    bootstrap=ROOT/'build/research/aloft-20261109/disk-analysis/accepted-01/bootstrap-side1.prg'
    boot=pinned(bootstrap,'7e283e390a10c2b7784ac1885081234c21a754d161e938babd504a13da2ee2e5')
    assert len(boot)==832 and boot[:2]==bytes.fromhex('0108')
    assert memories['sys'][0x801:0xb3f]==boot[2:] and by_stem['sys']['registers']['pc']==0x810
    inputs,oracles,lifetimes=field_ABIs(profile,frozen,case,points,captures,memories,context,hooks,abi)
    emit(out/'machine-context.json',dict(captures=context))
    emit(out/'independent-inputs.json',dict(motion_witnesses=inputs,table_proof=meta(TABLE_PROOF),
         no_post_state_or_store_values_as_model_inputs=True,dispatcher_high_bytes_not_exported_as_inputs=True))
    emit(out/'motion-oracles.json',dict(motion_witnesses=oracles,all_hooks=hooks,
         input_use_forbidden=True,all_raw_hits_retained=True,hook_clock_is_completion_not_electrical_bus_time=True))
    proof=dict(pass_=True,scope='Closed original Aloft motion-call custody and separated genuine inputs/result oracles; no runtime model, CPU or pixel execution.',
               producer=meta(Path(__file__).resolve()),profile=meta(CLOSED_PROFILE),
               inputs=[meta(FROZEN_NATIVE),meta(READER),meta(TABLE_PROOF),meta(OBSERVER_PROOF),meta(bootstrap),profile['owner_closure'],profile['manifest'],profile['freeze_source']],
               case_files=adapters.pop('files'),owner_closure=owner,session=case['session'],
               wire={k:dict(bytes=len(v),sha256=sha(v)) for k,v in case['wire'].items()},
               event_count=len(case['events']),reader_adapters=adapters,captures=captures,natural_stops=bindings,
               checkpoint_generations=points,command_audit=commands,source_generation=generation,
               observer_source_context=dict(proof=meta(OBSERVER_PROOF),compiled_source_route='c64cpusc/mainc64cpu/6510dtvcore plus c64memsc',
                    actual_dummy_mode_queries=[9,27,79],mode_unchanged_after_sequence8=True,
                    conditional_official_source_contract_not_capture_time_host_build_proof=True,
                    generic_core_timing_not_used=True),
               bootstrap_binding=dict(all830_SYS_payload_bytes_equal=True,SYS_PC=0x810,fresh08B5_pair=False),
               watched_windows=lifetimes,trace_hook_count=len(hooks),
               fields=[dict(label=x['label'],invocation_index=x['invocation_index'],roles=x['roles'],
                            genuine_C=x['input']['C'],genuine_D=x['input']['D'],
                            genuine_X=x['input']['CPU']['x'],genuine_Y=x['input']['CPU']['y']) for x in inputs],
               no_worker_native_process_socket_CPU_emulator_build_or_downloaded_host_execution=True,
               limits=['Source/table generation guards bind identities; no source-predicted target high bytes seed genuine inputs.',
                       'Only two calls of C000 (first of four source motion programs) were observed; later entry skips 63 checkpoint hits explicitly.',
                       'No full current resident-loader equality claim is inferred from this fresh SYS-only bootstrap pair.',
                       'Store hooks are instruction-completion observations; no electrical bus timestamp or universal raw bus-order claim.',
                       'Program/phase arithmetic, all intervening fields, pixels, physical timing, frame rate and named scene identity require separate proofs.'],
               outputs=[output_meta(p) for p in sorted(out.iterdir()) if p.is_file()])
    path=out/'native-proof.json';emit(path,proof);print(json.dumps(meta(path)))


if __name__ == '__main__':
    main()
