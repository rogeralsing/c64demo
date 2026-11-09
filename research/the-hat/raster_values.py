#!/usr/bin/env python3
"""Passive typed-macro values for four closed original Hat raster paths.

Only guarded source macros are lowered into semantic stages. No opcode is
fetched or dispatched at runtime, no CPU timing/stack is simulated, and
expected native stores are never prediction inputs.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import traceback

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/the-hat'
SOURCE_PROOF = BASE / 'raster-source-analysis/accepted-02/raster-source-proof.json'
SOURCE_PROOF_SHA = '6c3e831d481b58ca3d297cd13d2f21a95256a1edeb806cc46c4b5ce60d8491cb'
CASE_PROOF = BASE/'raster-case-analysis/accepted-01/raster-case-proof.json'
CASE_PROOF_SHA = '44f64e23252ed23db79c7ac5a56ffa326ba0d9e863a85f6902aa628e84c92f24'
HARDWARE_SOURCE_SHA = 'f9d15a6d26b877f63591b3c1ff7e31d3cf9430165783c89cb53b35ea6e32a12f'
HARDWARE_PROOF = BASE/'raster-hardware-analysis/accepted-02/raster-hardware-proof.json'
HARDWARE_PROOF_SHA = '1152358f2e24f596192758f5e2b9af5543556b35c63e6474ed8b08dac2de01fb'
OBSERVER_PROOF = BASE/'raster-hardware-analysis/observer-accepted-01/observer-contract-proof.json'
OBSERVER_PROOF_SHA = 'bc4387e8c5bf8909e9db6b3f174a691997ebbfaf8035d3553cad67aa5f7e9da9'
OBSERVER_SOURCE_SHA = '0baff66ac8ebc6cda8b439aa6435c00891e9bd6e2d026a06d5625356d71dfe71'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw=path.read_bytes()
    return dict(path=str(path.resolve().relative_to(ROOT)),bytes=len(raw),sha256=sha(raw))


def output_meta(path):
    raw=path.read_bytes()
    return dict(name=path.name,bytes=len(raw),sha256=sha(raw))


def checked_record(record):
    path=ROOT/record['path']
    assert meta(path)==record,record['path']
    return path.read_bytes()


def pinned_proof(path,pin):
    assert sha(path.read_bytes())==pin,path
    proof=json.loads(path.read_text())
    assert proof['pass_']
    for record in proof['outputs']:
        raw=(path.parent/record['name']).read_bytes()
        assert len(raw)==record['bytes'] and sha(raw)==record['sha256']
    return proof


def pure_module(path,pin,name):
    assert sha(path.read_bytes())==pin,path
    spec=importlib.util.spec_from_file_location(name,path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_bundle():
    assert sha(SOURCE_PROOF.read_bytes()) == SOURCE_PROOF_SHA
    proof = json.loads(SOURCE_PROOF.read_text())
    assert proof['pass_']
    for record in proof['inputs']:
        path = ROOT/record['path']
        raw = path.read_bytes()
        assert len(raw)==record['bytes'] and sha(raw)==record['sha256']
    for record in proof['outputs']:
        path = SOURCE_PROOF.parent / record['name']
        raw = path.read_bytes()
        assert len(raw) == record['bytes'] and sha(raw) == record['sha256']
    return json.loads((SOURCE_PROOF.parent/'raster-blocks.json').read_text())


def semantic_stages(macro):
    """Lower a closed source idiom and verify every original byte/PC.

    Recognition is by the high-level kind. Encodings only guard each known
    stage; they are not decoded or executed by the value consumer.
    """
    pc, encoded, stages = macro['first'], bytearray(), []

    def add(kind, data, **fields):
        nonlocal pc
        stages.append(dict(kind=kind, pc=pc, **fields))
        encoded.extend(data)
        pc += len(data)

    def word(opcode, address):
        return bytes((opcode,address&255,address>>8))

    def writes(rows, opcode, value):
        for row in rows:
            assert row['pc'] == pc
            add('write',word(opcode,row['address']),address=row['address'],value=value,
                operation={0x8d:'STA',0x8c:'STY',0x8e:'STX'}[opcode])

    kind = macro['kind']
    if kind in ('copy_and_write_group','add_and_write_group','retain_value_for_later_writes'):
        value = macro['input']
        if 'literal' in value:
            data = bytes((0xa9,value['literal']))
        elif 'read8' in value:
            read = value['read8']
            address = read.get('address',read.get('canonical'))
            data = word(0xad,address)
        else:
            assert 'table' in value
            data = word(0xb9,value['table'])
        add('load_value',data,input=value,result=macro['result'])
        if kind == 'add_and_write_group':
            add('add',bytes((0x69,macro['addend'])),addend=macro['addend'],
                incoming_carry=macro['carry_in'],result=macro['result'])
            if macro['clear_carry_after_sum']:
                add('clear_carry',b'\x18')
        writes(macro['writes'],0x8d,dict(result=macro['result']))
    elif kind == 'write_previous_value':
        writes(macro['writes'],0x8d,macro['value'])
    elif kind == 'sample_live_raster_low':
        add('sample_raster',word(0xac,macro['source_address']),
            source_address=macro['source_address'],sample=macro['sample'])
    elif kind == 'literal_lookup_index_and_write':
        add('set_Y',bytes((0xa0,macro['value'])),value=macro['value'])
        writes(macro['writes'],0x8c,dict(register='Y'))
    elif kind == 'advance_sampled_lookup_index':
        add('advance_Y',b'\xc8',expected_index=macro['index'])
    elif kind == 'clear_sum_carry':
        add('clear_carry',b'\x18')
    elif kind == 'set_fixed_X':
        add('set_X',bytes((0xa2,macro['value'])),value=macro['value'])
    elif kind == 'coordinate_and_border_write_train':
        for step in macro['ordered_steps']:
            assert step['pc'] == pc
            if step['operation'] == 'literal_write':
                assert step['value'] == 0x88
                add('write',word(0x8e,step['address']),address=step['address'],
                    value=dict(register='X'),operation='STX')
            else:
                assert step['operation']=='RMW' and step['delta'] in (-1,1)
                add('RMW',word(0xce if step['delta']==-1 else 0xee,step['address']),
                    address=step['address'],delta=step['delta'])
    elif kind == 'mask_write_D011_mirror':
        add('SAX_write',word(0x8f,macro['address']),address=macro['address'],
            expected_A=macro['source_literal'],expected_X=0x88)
    elif kind == 'padding':
        for padding in macro['instructions']:
            assert padding['pc'] == pc
            data = bytes.fromhex(padding['hex'])
            assert data in (b'\xea',b'\x04\x80')
            add('padding',data)
    elif kind == 'external_delay_call':
        assert macro['target'] in (0x019f,0x01a0,0x01a4)
        add('preserving_delay_call',word(0x20,macro['target']),target=macro['target'])
    elif kind == 'normal_flow_edge':
        add('normal_flow_edge',word(0x4c,macro['initial_target']))
    else:
        raise AssertionError(('unknown guarded macro',kind))
    assert pc == macro['end_exclusive']
    assert bytes(encoded).hex().upper() == macro['hex']
    return stages


def lowered_blocks(bundle):
    result = {}
    for block in bundle['blocks']:
        stages = [s for macro in block['macros'] for s in semantic_stages(macro)]
        assert stages[0]['pc'] == block['first']
        assert len(stages) == block['instruction_sites']
        result[block['first']] = dict(block=block,stages=stages)
    # The ten-byte selector has no writes. Both paths immediately replace its
    # dead A/flags before any value-producing source write; pointer bit3 alone
    # chooses the source prologue. Carry is explicitly cleared in each prologue.
    assert sum(len(b['stages']) for b in result.values())+4 == 6525
    return result


def predict(entry_ram, entry_regs, entry_cpu, raster_reads, cutoff_pc, hardware):
    """Predict one bounded path using live reads/cutoff as external inputs.

    raster_reads rows have source_pc, value and optional custody metadata.
    hardware supplies guarded logical vic_register_read/store functions.
    No expected native stores, counts or ending values are accepted here.
    """
    assert len(entry_ram)==65536 and len(entry_regs)==64
    assert not entry_cpu['flags'] & 8, 'Binary ADC requires decimal flag clear.'
    assert entry_cpu['port01']&7==5, (
        'CPU mapping requires HIRAM clear for Fxxx tables/Axxx code, with VIC I/O mapped.')
    assert entry_cpu['sp']==0x59, 'This case binds the original saved-stack generation.'
    bundle = source_bundle()
    blocks = lowered_blocks(bundle)
    all_pcs = {s['pc'] for b in blocks.values() for s in b['stages']}
    assert cutoff_pc in all_pcs, 'This bounded case requires cutoff at a guarded raster instruction boundary.'
    ram, regs = bytearray(entry_ram), list(entry_regs)
    original = (BASE/'dali-analysis/neighbor-probe-02/accepted-01/b08.bin').read_bytes()
    mutable = {0x8976,0x8977,0xacff,0xad00}
    assert all(ram[pc]==original[pc-0x4000] for pc in range(0x8516,0xc7ba)
               if pc not in mutable), 'Wrong source generation outside declared JMP operands.'
    b9 = (BASE/'dali-analysis/neighbor-probe-02/accepted-01/b09.bin').read_bytes()
    assert ram[0xf400:0xf800]==b9[0x1400:0x1800], 'This case binds original dispatch-table generation.'
    assert bytes(ram[0x019f:0x01ac]) == bytes.fromhex('60209F016020A0016020A40160')
    state = dict(A=entry_cpu['a'],X=entry_cpu['x'],Y=entry_cpu['y'],C=entry_cpu['flags']&1)
    variant = 1 if ram[0x43f8]&8 else 0
    state['A'] = ram[0x43f8]&8  # Explicit selector result before the chosen prefix.
    next_block = 0xa8aa if variant else 0x8520
    read_index, events, iterations = 0, [], []
    # No expected output count or path length supplies this bound.
    maximum_iterations = len(raster_reads)+3
    touched_regs, touched_ram = set(), set()

    def canonical(address):
        return address & 0x3f

    def read_byte(description):
        if description['kind']=='sprite_pointer_RAM':
            return ram[description['address']]
        return hardware.vic_register_read(regs,description['canonical'])

    def index_value(description, samples):
        if 'literal' in description:
            return description['literal']
        return (samples[description['sample']]+description['offset'])&255

    def carry_value(description, carries, entry_carry):
        if 'literal' in description:
            return description['literal']
        if 'entry_carry' in description:
            return entry_carry
        return carries[description['sum_carry_of']]

    def do_write(pc,address,value,operation,software_read=None):
        assert 0<=value<256
        if 0xd000<=address<=0xd3ff:
            reg = canonical(address)
            regs[:] = hardware.vic_register_write(regs,address,value)
            touched_regs.add(reg)
        else:
            assert (0x43f8<=address<=0x43ff or 0x47f8<=address<=0x47ff or
                    address in (0x8976,0x8977,0xacff,0xad00))
            ram[address] = value
            touched_ram.add(address)
        row = dict(pc=pc,address=address,value=value,operation=operation,
                   registers_after=bytes(regs).hex(),CPU_values_after=dict(state))
        if software_read is not None:
            row['software_visible_read'] = software_read
            row['software_visible_after'] = hardware.vic_register_read(regs,address)
        events.append(row)

    for iteration in range(maximum_iterations):
        item = blocks[next_block]
        block = item['block']
        assert block['variant']==variant
        samples, values, carries = {}, {}, {}
        entry_carry = state['C']
        pass_record = dict(block=next_block,read_first=read_index,write_first=len(events))
        iterations.append(pass_record)
        for stage in item['stages']:
            pc = stage['pc']
            if pc==cutoff_pc and read_index==len(raster_reads):
                pass_record.update(read_end=read_index,write_end=len(events),cutoff_inside_block=True)
                return dict(variant=variant,cutoff_pc=cutoff_pc,all_live_reads_consumed=True,
                            consumed_live_reads=read_index,final_cpu_values=state,
                            writes=events,iterations=iterations,
                            final_regs=regs,final_ram=bytes(ram),
                            touched_registers=sorted(touched_regs),touched_RAM=sorted(touched_ram))
            kind = stage['kind']
            if kind=='load_value':
                value = stage['input']
                if 'literal' in value:
                    byte = value['literal']
                elif 'read8' in value:
                    byte = read_byte(value['read8'])
                else:
                    y = index_value(value['index'],samples)
                    assert y==state['Y']
                    byte = ram[value['table']+y]
                state['A'] = values[stage['result']] = byte
            elif kind=='add':
                expected_C = carry_value(stage['incoming_carry'],carries,entry_carry)
                assert state['C']==expected_C
                total = state['A']+stage['addend']+state['C']
                state['A'],state['C'] = total&255,total>>8
                values[stage['result']] = state['A']
                carries[stage['result']] = state['C']
            elif kind=='clear_carry':
                state['C'] = 0
            elif kind=='write':
                expression = stage['value']
                value = state[expression['register']] if 'register' in expression else values[expression['result']]
                if 'result' in expression:
                    assert value==state['A']
                do_write(pc,stage['address'],value,stage['operation'])
            elif kind=='sample_raster':
                assert read_index<len(raster_reads), ('missing live read',hex(pc))
                record = raster_reads[read_index]
                assert record['source_pc']==pc,(read_index,hex(pc),record)
                value = record['value']
                assert 0<=value<256
                state['Y'] = samples[stage['sample']] = value
                read_index += 1
            elif kind=='set_Y':
                state['Y'] = stage['value']
            elif kind=='advance_Y':
                state['Y'] = (state['Y']+1)&255
                assert state['Y']==index_value(stage['expected_index'],samples)
            elif kind=='set_X':
                state['X'] = stage['value']
            elif kind=='RMW':
                old = hardware.vic_register_read(regs,stage['address'])
                do_write(pc,stage['address'],(old+stage['delta'])&255,
                         'DEC' if stage['delta']==-1 else 'INC',old)
            elif kind=='SAX_write':
                assert state['A']==stage['expected_A'] and state['X']==stage['expected_X']
                do_write(pc,stage['address'],state['A']&state['X'],'SAX')
            elif kind in ('padding','preserving_delay_call','normal_flow_edge'):
                pass
            else:
                raise AssertionError(kind)
        pass_record.update(read_end=read_index,write_end=len(events),cutoff_inside_block=False)
        edge = block.get('normal_flow')
        if edge is None:
            next_block = 0xa8df if variant else 0x8556
        elif edge['kind']=='self_loop':
            next_block = edge['target']
        else:
            assert edge['kind']=='live_raster_table_dispatch'
            sample = block['raster_samples'][-1]['sample']
            y = samples[sample]
            next_block = ram[edge['low_table']+y] | ram[edge['high_table']+y]<<8
            operand = edge['jump_pc']+1
            assert next_block==ram[operand] | ram[operand+1]<<8
        assert next_block in blocks and blocks[next_block]['block']['variant']==variant
    raise AssertionError('No bounded cutoff after consuming the supplied live reads.')


def compare_prediction(prediction, store_hooks, cutoff_ram, cutoff_regs,
                       cutoff_cpu, visible_read, watch_ranges):
    """Oracle checks only; none of these arguments feed path prediction.

    visible_read(regs64, absolute_register_address, observed_raster_line)
    returns the expected byte and the independently guarded comparison mask.
    is the separately guarded monitor-observer rule. The observed beam only
    formats a dynamic readback, not source scheduling or branch selection.
    """
    # Coverage selection is the independently accepted checkpoint configuration,
    # not an address/count list recovered from the observed store sequence.
    writes = [w for w in prediction['writes']
              if any(first<=w['address']<=last for first,last in watch_ranges)]
    assert len(writes)==len(store_hooks)
    direct, rmw, visible_dumps, visible_checks, cpu_checks = 0,0,0,0,0
    observed_operations = {}
    # Source-used storage classes plus the preserved X-high byte.
    visible_indices = list(range(0x11))+[0x11,0x16,0x18]+list(range(0x27,0x2f))
    for ordinal,(model,hook) in enumerate(zip(writes,store_hooks)):
        assert hook['operation']=='store'
        assert model['pc']==hook['instruction_PC'],(ordinal,model['pc'],hook['instruction_PC'])
        assert model['address']==hook['monitored_address'],ordinal
        op = hook['instruction'].split()[0]
        assert model['operation']==op,ordinal
        observed_operations[op] = observed_operations.get(op,0)+1
        registers = hook['registers']
        for name,key in (('A','a'),('X','x'),('Y','y')):
            assert model['CPU_values_after'][name]==registers[key],(ordinal,name)
            cpu_checks += 1
        assert model['CPU_values_after']['C']==registers['flags']&1,(ordinal,'carry')
        cpu_checks += 1
        if op in ('STA','STX','STY','SAX'):
            actual = (registers[{'STA':'a','STX':'x','STY':'y'}[op]] if op!='SAX'
                      else registers['a']&registers['x'])
            assert model['value']==actual,(ordinal,op)
            direct += 1
        else:
            assert op in ('INC','DEC')
            expected_NZ = (model['value']&0x80) | (2 if model['value']==0 else 0)
            assert registers['flags']&0x82==expected_NZ,(ordinal,'RMW N/Z')
            rmw += 1
        if 'visible_IO_readback' in hook:
            view = hook['visible_IO_readback']['visible_bytes']
            assert len(view)==64
            after = list(bytes.fromhex(model['registers_after']))
            for index in visible_indices:
                expected,mask = visible_read(after,0xd000+index,registers['line'])
                assert expected&mask==view[index]&mask,(ordinal,'visible register',hex(index),expected,view[index],mask)
                visible_checks += 1
            visible_dumps += 1
    endpoint_registers = sorted(set(prediction['touched_registers'])|{0x10})
    for index in endpoint_registers:
        assert prediction['final_regs'][index]==cutoff_regs[index],('endpoint VIC',hex(index))
    tracked_RAM = list(range(0x43f8,0x4400))+list(range(0x47f8,0x4800))+[0x8976,0x8977,0xacff,0xad00]
    endpoint_RAM = []
    for address in tracked_RAM:
        value = prediction['final_ram'][address]
        assert value==cutoff_ram[address],('endpoint RAM',hex(address))
        endpoint_RAM.append(dict(address=address,value=value,
                                 written_by_model=address in prediction['touched_RAM']))
    for name,key in (('A','a'),('X','x'),('Y','y')):
        assert prediction['final_cpu_values'][name]==cutoff_cpu[key],('endpoint CPU',name)
    assert prediction['final_cpu_values']['C']==cutoff_cpu['flags']&1
    return dict(all_ordered_hook_PC_address_operations_equal=True,hook_count=len(writes),
                all_source_predicted_writes=len(prediction['writes']),
                unwatched_source_writes=len(prediction['writes'])-len(writes),
                oracle_watch_ranges=[list(r) for r in watch_ranges],
                operation_counts=observed_operations,CPU_value_component_checks=cpu_checks,
                direct_store_byte_checks=direct,RMW_NZ_checks=rmw,
                visible_IO_dumps=visible_dumps,visible_register_byte_checks=visible_checks,
                endpoint_VIC_registers=endpoint_registers,endpoint_RAM=endpoint_RAM,
                endpoint_A_X_Y_carry_equal=True,
                limits=['RMW raw intermediate bytes are predictions, not a separately captured data-bus trace.',
                        'Visible IO readbacks mask stored unused bits and D011 uses the observed query beam.',
                        'Only declared tracked RAM/VIC fields are compared; stack, DMA, caches, pixels and complete physical RAM evolution are not modeled.'])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output',type=Path,required=True)
    args = ap.parse_args()
    out=args.output.resolve()
    assert out.is_relative_to(BASE/'raster-value-analysis') and not out.exists()
    out.mkdir(parents=True)
    source=Path(__file__).resolve()
    (out/'raster_values.checked.py').write_bytes(source.read_bytes())
    try:
        case=pinned_proof(CASE_PROOF,CASE_PROOF_SHA)
        pinned_proof(HARDWARE_PROOF,HARDWARE_PROOF_SHA)
        pinned_proof(OBSERVER_PROOF,OBSERVER_PROOF_SHA)
        hardware_path=HARDWARE_PROOF.parent/'raster_hardware.checked.py'
        observer_path=OBSERVER_PROOF.parent/'observer_schema.checked.py'
        hardware=pure_module(hardware_path,HARDWARE_SOURCE_SHA,'hat_values_hardware')
        observer=pure_module(observer_path,OBSERVER_SOURCE_SHA,'hat_values_observer')
        # Bind the same pinned checked hardware dependency into the frozen
        # observer's lazy pure-helper slot. No source file/AST is changed.
        observer._hardware=hardware
        reads=json.loads((CASE_PROOF.parent/'raster-read-inputs.json').read_text())
        hooks=json.loads((CASE_PROOF.parent/'trace-hits.json').read_text())
        by_capture={row['stem']:row for row in case['captures']}
        by_reads={row['label']:row for row in reads['fields']}
        by_watch={row['label']:row for row in case['watched_lifetimes']['fields']}
        ranges=[(r['first'],r['last']) for r in case['watched_lifetimes']['required_ranges']
                if r['operation']=='store']
        fields=[]
        for field in case['bounded_machine_context']['fields']:
            label=field['label'];stages=field['stages']
            selector=stages['selector'];cutoff=stages['cutoff']
            begin_capture=by_capture[selector['stem']]
            end_capture=by_capture[cutoff['stem']]
            entry_ram=checked_record(begin_capture['ram'])
            target_ram=checked_record(end_capture['ram'])
            checked_record(begin_capture['snapshot']);checked_record(end_capture['snapshot'])
            stream=by_reads[label]
            low,high=selector['registers']['clock'],cutoff['registers']['clock']
            assert stream['selector_clock']==low and stream['cutoff_clock']==high
            samples=[dict(source_pc=r['instruction_PC'],value=r['loaded_Y'])
                     for r in stream['raster_read_samples']]
            # No target RAM/registers/store hooks are supplied to predict().
            prediction=predict(entry_ram,selector['VIC']['regs'],selector['registers'],
                               samples,field['stacked_interrupted_PC'],hardware)
            assert prediction['variant']==stream['variant']
            completed_sequence=by_capture[stages['completed']['stem']]['stop_sequence']
            oracle=[h for h in hooks if h['operation']=='store'
                    and low<=h['registers']['clock']<=high
                    and h['sequence']<=completed_sequence]
            comparisons=compare_prediction(prediction,oracle,target_ram,cutoff['VIC']['regs'],
                                           cutoff['registers'],observer.model_readback,ranges)
            expected_views=by_watch[label]['visible_IO_oracles_expected']
            assert comparisons['visible_IO_dumps']==(len(oracle) if expected_views else 0)
            paths=[]
            path=out/(label+'-source-writes.json')
            path.write_text(json.dumps(prediction['writes'],indent=2)+'\n');paths.append(path.name)
            path=out/(label+'-logical-registers-after.bin')
            path.write_bytes(bytes(prediction['final_regs']));paths.append(path.name)
            path=out/(label+'-pointers-and-operands-after.bin')
            path.write_bytes(bytes(r['value'] for r in comparisons['endpoint_RAM']));paths.append(path.name)
            fields.append(dict(label=label,variant=prediction['variant'],
                prediction_inputs=dict(selector_capture=selector['stem'],RAM=begin_capture['ram'],
                    snapshot=begin_capture['snapshot'],CPU=selector['registers'],
                    logical_VIC_registers=selector['VIC']['regs'],
                    live_read_count=len(samples),live_read_input_output=case['external_read_input_output'],
                    live_read_selection_label=label,cutoff_PC=field['stacked_interrupted_PC'],
                    observed_cutoff_clock_not_a_prediction=high),
                oracle_inputs=dict(cutoff_capture=cutoff['stem'],RAM=end_capture['ram'],
                    snapshot=end_capture['snapshot'],store_hooks=case['store_hook_oracle_output'],
                    clock_window_inclusive=[low,high],completed_stop_sequence=completed_sequence,
                    visible_IO_expected=expected_views),
                consumed_live_reads=prediction['consumed_live_reads'],
                all_live_reads_consumed_before_cutoff=True,
                iterations=prediction['iterations'],final_A_X_Y_carry=prediction['final_cpu_values'],
                comparisons=comparisons,outputs=paths))
        assert len(fields)==4
        outputs=[output_meta(p) for p in sorted(out.iterdir()) if p.is_file()]
        proof=dict(pass_=True,scope='Four bounded original Hat raster paths predicted from typed source macros plus explicit live raster reads and cutoff PCs; no CPU/timing/pixel model',
            producer=meta(source),inputs=[meta(p) for p in
                (SOURCE_PROOF,CASE_PROOF,HARDWARE_PROOF,OBSERVER_PROOF,hardware_path,observer_path)],
            observer_dependency='Frozen observer._hardware is explicitly bound to the identical frozen checked pure hardware module; no AST or source mutation.',
            fields=fields,
            helper_contract=dict(first=0x019f,end_exclusive=0x01ac,
                hex='60209F016020A0016020A40160',entry_SP=0x59,
                entry019F='RTS only',entry01A0='JSR019F then RTS',entry01A4='JSR01A0 then RTS',
                preserves=['A','X','Y','carry'],stack_and_elapsed_time_modeled=False),
            limits=['Live raster read values and the stacked cutoff PC are external control inputs; source clock scheduling and IRQ deadlines are not predicted.',
                'Entry RAM/VIC state and current table generations are declared inputs. Later snapshot fields and store/readback values are equality oracles only.',
                'Only accepted watched ranges select predicted writes for hook comparison; unwatched SMC writes remain predicted and endpoint-checked.',
                'Old windows lack IO readback. RMW raw intermediate bytes there are not separately observed; N/Z and final stored snapshots constrain them.',
                'New IO windows compare28 software-visible register bytes per hook using the observed query beam solely for dynamic readback formatting.',
                'Unused stored bits, physical dummy/final bus cycles, caches/DMA/shifters, all pixels and animation FPS are not proved.',
                'No native/process/build/CPU interpreter or downloaded host execution occurs.'],outputs=outputs)
        path=out/'raster-value-proof.json'
        path.write_text(json.dumps(proof,indent=2)+'\n')
        print(json.dumps(dict(pass_=True,receipt=output_meta(path),fields=[dict(label=f['label'],
            reads=f['consumed_live_reads'],hooks=f['comparisons']['hook_count'],
            visible_checks=f['comparisons']['visible_register_byte_checks']) for f in fields]),indent=2))
    except Exception as error:
        (out/'failure.json').write_text(json.dumps(dict(pass_=False,error_type=type(error).__name__,
            error=str(error),traceback=traceback.format_exc(),producer=meta(source),
            no_native_or_CPU_execution=True),indent=2)+'\n')
        raise


if __name__=='__main__':
    main()
