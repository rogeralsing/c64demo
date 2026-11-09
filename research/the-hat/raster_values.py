#!/usr/bin/env python3
"""Typed-macro value consumer; native03 acceptance is deliberately pending.

Only guarded source macros are lowered into semantic stages. No opcode is
fetched or dispatched at runtime, no CPU timing/stack is simulated, and
expected native stores are never prediction inputs.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/the-hat'
SOURCE_PROOF = BASE / 'raster-source-analysis/accepted-02/raster-source-proof.json'
SOURCE_PROOF_SHA = '6c3e831d481b58ca3d297cd13d2f21a95256a1edeb806cc46c4b5ce60d8491cb'
# Set only after the independent closed-case and hardware lanes are frozen.
CASE_PROOF = None
CASE_PROOF_SHA = None
HARDWARE_SOURCE_SHA = 'f9d15a6d26b877f63591b3c1ff7e31d3cf9430165783c89cb53b35ea6e32a12f'


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


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
            view = hook['visible_IO_readback']['visible_bytes64']
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
    assert CASE_PROOF is not None and CASE_PROOF_SHA and HARDWARE_SOURCE_SHA, (
        'PENDING: closed native03 custody/read inputs and frozen hardware API are required. '
        'No accepted native value receipt or output directory is created.')
    raise AssertionError('PENDING: integrate the frozen custody schema before acceptance.')


if __name__=='__main__':
    main()
