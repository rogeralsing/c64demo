#!/usr/bin/env python3
"""Decompile the two original Hat B8 raster branches into guarded source macros.

This is a static, source-specific translation. It neither runs a CPU nor
evaluates a native write trace. Live VIC reads and RMW rules remain inputs.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/the-hat'
SOURCE = BASE / 'dali-analysis/neighbor-probe-02/accepted-01'
PINS = {
    SOURCE / 'source-classification.json': '838ed0bd5534acce676b06528f4c311adbccc8f1fc62462d5b68abfe628dcb8f',
    SOURCE / 'b08.bin': '5c8150c48068c62f8a77d8c97b18de33360dcb03046e0f5e9ffcb01ca6704ba6',
    SOURCE / 'b09.bin': '9d0f80b7bc33c981a7befe2274ac98f30bf00c77916702016588b5e028e9a578',
}
# Only the instructions present in this fixed, completely covered region.
OPS = {
    0xad: ('LDA', 'abs', 3), 0xa9: ('LDA', 'imm', 2), 0xb9: ('LDA', 'absy', 3),
    0xa2: ('LDX', 'imm', 2), 0xac: ('LDY', 'abs', 3), 0xa0: ('LDY', 'imm', 2),
    0xc8: ('INY', 'imp', 1), 0x18: ('CLC', 'imp', 1), 0x69: ('ADC', 'imm', 2),
    0x8d: ('STA', 'abs', 3), 0x8e: ('STX', 'abs', 3), 0x8c: ('STY', 'abs', 3),
    0x8f: ('SAX', 'abs', 3), 0xce: ('DEC', 'abs', 3), 0xee: ('INC', 'abs', 3),
    0xea: ('NOP', 'imp', 1), 0x04: ('NOP', 'zp', 2), 0x20: ('JSR', 'abs', 3),
    0x4c: ('JMP', 'abs', 3), 0x29: ('AND', 'imm', 2), 0xf0: ('BEQ', 'rel', 2),
}
EVEN = [0x8556, 0x8978, 0x8dec, 0x9261, 0x96d6, 0x9b4b, 0x9fc0, 0xa435]
ODD = [0xa8df, 0xad01, 0xb174, 0xb5e9, 0xba5d, 0xbed1, 0xc346]
EVEN_INDEX = [(0,0),(1,0),(1,1),(2,0),(2,1),(2,2),(2,3),(3,0),
              (4,0),(5,0),(5,1),(5,2),(5,3),(6,0),(6,1),(7,0),(7,1)]
ODD_INDEX = [(0,0),(0,1),(0,2),(0,3),(1,0),(1,1),(2,0),(2,1),
             (3,0),(3,1),(4,0),(4,1),(5,0),(5,1),(5,2),(5,3),(6,0)]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return dict(path=str(path.resolve().relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def output_meta(path):
    raw = path.read_bytes()
    return dict(name=path.name, bytes=len(raw), sha256=sha(raw))


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def decode(memory, first, end):
    rows = []
    pc = first
    while pc < end:
        op, mode, width = OPS[memory[pc]]
        assert pc + width <= end
        raw = bytes(memory[pc:pc+width])
        operand = int.from_bytes(raw[1:], 'little') if width > 1 else None
        row = dict(pc=pc, op=op, mode=mode, width=width, hex=raw.hex().upper())
        if operand is not None:
            row['operand'] = operand
        if mode == 'rel':
            row['target'] = pc + 2 + (operand if operand < 128 else operand-256)
        rows.append(row)
        pc += width
    assert pc == end
    return rows


def memory_class(address):
    if 0xd000 <= address <= 0xd3ff:
        reg = address & 0x3f
        if reg <= 0x0f:
            return dict(kind='VIC_sprite_Y' if reg & 1 else 'VIC_sprite_X_low',
                        canonical=0xd000+reg, sprite=reg//2)
        return dict(kind='VIC_register', canonical=0xd000+reg)
    if 0x43f8 <= address <= 0x43ff or 0x47f8 <= address <= 0x47ff:
        return dict(kind='sprite_pointer_RAM', address=address,
                    table=address & 0xfff8, sprite=address & 7)
    if address in (0x8976, 0x8977, 0xacff, 0xad00):
        return dict(kind='self_modified_JMP_operand', address=address)
    raise AssertionError(('unclassified source address', hex(address)))


def compile_block(memory, rows, first, end, role):
    """Recognize source idioms, retaining arithmetic and live-read dependencies.

    No instruction is executed. The output is a declarative macro sequence;
    the only state-like names are source carry chains and sampled table indices.
    """
    rs = [r for r in rows if first <= r['pc'] < end]
    assert rs[0]['pc'] == first and rs[-1]['pc'] + rs[-1]['width'] == end
    macros, i, last_value, carry, index = [], 0, None, {'entry_carry': True}, {'entry_Y': True}
    last_value_input = None
    sample_number, samples = 0, []
    table_uses, pointer_uses, y_uses = [], [], []

    def emit(kind, lo, hi, **fields):
        a, z = rs[lo]['pc'], rs[hi-1]['pc'] + rs[hi-1]['width']
        obj = dict(kind=kind, first=a, end_exclusive=z,
                   hex=bytes(memory[a:z]).hex().upper(), **fields)
        macros.append(obj)
        return obj

    def read_value(row):
        if row['mode'] == 'imm':
            return dict(literal=row['operand'])
        if row['mode'] == 'abs':
            return dict(read8=memory_class(row['operand']))
        assert row['mode'] == 'absy'
        assert row['operand'] in (0xf200,0xf300,0xf400,0xf500,0xf600,0xf700)
        return dict(table=row['operand'], index=dict(index), index_modulus=256)

    while i < len(rs):
        r, lo = rs[i], i
        op = r['op']
        if op == 'LDA':
            value = read_value(r)
            i += 1
            addend, incoming_carry, cleared = None, None, False
            if i < len(rs) and rs[i]['op'] == 'ADC':
                assert rs[i]['mode'] == 'imm' and rs[i]['operand'] in (8,21)
                addend, incoming_carry = rs[i]['operand'], dict(carry)
                i += 1
                if i < len(rs) and rs[i]['op'] == 'CLC':
                    cleared = True
                    i += 1
            writes = []
            while i < len(rs) and rs[i]['op'] == 'STA':
                w = rs[i]
                writes.append(dict(pc=w['pc'], address=w['operand'],
                                   destination=memory_class(w['operand'])))
                i += 1
            assert writes or addend is None, ('unrecognized add/store idiom', hex(r['pc']))
            result = f'v{r["pc"]:04X}'
            fields = dict(input=value, result=result, writes=writes)
            if addend is not None:
                fields.update(addend=addend, carry_in=incoming_carry,
                              byte_result='(input + addend + carry_in) & 255',
                              sum_carry='(input + addend + carry_in) >> 8',
                              clear_carry_after_sum=cleared)
                carry = {'literal': 0} if cleared else {'sum_carry_of': result}
            kind = 'add_and_write_group' if addend is not None else (
                'copy_and_write_group' if writes else 'retain_value_for_later_writes')
            emit(kind, lo, i, **fields)
            last_value = result
            last_value_input = (value, addend)
            if 'table' in value:
                table_uses.append(dict(pc=r['pc'], table=value['table'], index=value['index'],
                                       writes=writes))
            if addend == 8:
                assert len(writes) == 1 and value.get('read8',{}).get('kind') == 'sprite_pointer_RAM'
                src, dst = r['operand'], writes[0]['address']
                assert dst == src ^ 0x400
                pointer_uses.append(dict(pc=r['pc'], source=src, destination=dst,
                                         addend=8, carry_in=incoming_carry,
                                         carry_cleared_after_sum=cleared))
            elif addend == 21:
                assert value.get('read8',{}).get('kind') == 'VIC_sprite_Y'
                assert all(w['destination']['kind'] == 'VIC_sprite_Y' for w in writes)
                y_uses.append(dict(pc=r['pc'], source=r['operand'],
                                   destination_sprites=[w['destination']['sprite'] for w in writes],
                                   addend=21, carry_in=incoming_carry,
                                   carry_cleared_after_sum=cleared))
        elif op == 'STA':
            assert last_value is not None
            writes = []
            while i < len(rs) and rs[i]['op'] == 'STA':
                w = rs[i]
                writes.append(dict(pc=w['pc'], address=w['operand'],
                                   destination=memory_class(w['operand'])))
                i += 1
            emit('write_previous_value', lo, i, value=dict(result=last_value), writes=writes)
        elif op == 'LDY':
            i += 1
            if r['mode'] == 'abs':
                assert r['operand'] in (0xd012,0xd112)
                index = {'sample': sample_number, 'offset': 0}
                obj = emit('sample_live_raster_low', lo, i, source_address=r['operand'],
                           canonical=0xd012, sample=sample_number, post_pc=r['pc']+3,
                           post_register='Y', index=dict(index))
                samples.append({k: obj[k] for k in ('first','post_pc','source_address','sample')})
                sample_number += 1
            else:
                assert r['mode'] == 'imm' and r['operand'] in (0,16)
                index = {'literal': r['operand']}
                writes = []
                while i < len(rs) and rs[i]['op'] == 'STY':
                    assert rs[i]['operand'] == 0xd018
                    writes.append(dict(pc=rs[i]['pc'], address=0xd018))
                    i += 1
                emit('literal_lookup_index_and_write', lo, i, value=r['operand'], writes=writes)
        elif op == 'INY':
            assert 'sample' in index
            index = dict(index, offset=(index['offset']+1)&255)
            emit('advance_sampled_lookup_index', lo, i+1, index=dict(index), modulus=256)
            i += 1
        elif op == 'CLC':
            carry = {'literal': 0}
            emit('clear_sum_carry', lo, i+1)
            i += 1
        elif op == 'LDX':
            assert r['mode'] == 'imm' and r['operand'] == 0x88
            emit('set_fixed_X', lo, i+1, value=0x88)
            i += 1
        elif op in ('DEC','INC','STX'):
            steps = []
            while i < len(rs) and rs[i]['op'] in ('DEC','INC','STX'):
                r = rs[i]
                dest = memory_class(r['operand'])
                assert dest['kind'] in ('VIC_sprite_X_low','VIC_register')
                assert dest['canonical'] <= 0xd00e or dest['canonical'] == 0xd016
                steps.append(dict(pc=r['pc'], address=r['operand'], destination=dest,
                                  operation='literal_write' if r['op']=='STX' else 'RMW',
                                  value=0x88 if r['op']=='STX' else None,
                                  delta=None if r['op']=='STX' else (-1 if r['op']=='DEC' else 1)))
                i += 1
            emit('coordinate_and_border_write_train', lo, i, ordered_steps=steps,
                 RMW_read='Actual software-visible register read, then byte add delta modulo 256; physical dummy/final bus writes require the hardware layer.')
        elif op == 'SAX':
            assert r['operand'] == 0xd111 and last_value is not None
            assert last_value_input == ({'literal': 0xf0}, None)
            emit('mask_write_D011_mirror', lo, i+1, address=0xd111, canonical=0xd011,
                 value=dict(bitwise_AND=[dict(result=last_value),dict(literal=0x88)]),
                 source_literal=0xf0, derived_value_under_X88=0x80)
            i += 1
        elif op == 'NOP':
            padding = []
            while i < len(rs) and rs[i]['op'] == 'NOP':
                r = rs[i]
                assert r['mode'] == 'imp' or (r['mode']=='zp' and r['operand']==0x80)
                padding.append(dict(pc=r['pc'], hex=r['hex'],
                                    source_read_address=0x80 if r['mode']=='zp' else None))
                i += 1
            emit('padding', lo, i, instructions=padding)
        elif op == 'JSR':
            assert r['operand'] in (0x019f,0x01a0,0x01a4)
            emit('external_delay_call', lo, i+1, target=r['operand'],
                 required_contract='Returns preserving A,X,Y and carry; actual shared helper bytes and IRQ nesting need runtime generation guards, not an assumed fixed elapsed cost.')
            i += 1
        elif op == 'JMP':
            assert i == len(rs)-1
            emit('normal_flow_edge', lo, i+1, initial_target=r['operand'],
                 mutable_operand=r['pc'] in (0x8975,0xacfe))
            i += 1
        else:
            raise AssertionError(('unhandled source idiom',r))
    assert macros[0]['first'] == first and macros[-1]['end_exclusive'] == end
    assert all(a['end_exclusive'] == b['first'] for a,b in zip(macros,macros[1:]))
    return dict(first=first, end_exclusive=end, bytes=end-first,
                source_sha256=sha(bytes(memory[first:end])), role=role,
                instruction_sites=len(rs), macros=macros, raster_samples=samples,
                table_uses=table_uses, pointer_transfers=pointer_uses,
                sprite_Y_groups=y_uses, exit_carry=carry)


def runs(values):
    result = []
    for index, value in enumerate(values):
        if result and result[-1]['target'] == value:
            result[-1]['last_raster_low'] = index
        else:
            result.append(dict(first_raster_low=index,last_raster_low=index,target=value))
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    out = args.output.resolve()
    assert out.is_relative_to(BASE/'raster-source-analysis') and not out.exists()
    for path, pin in PINS.items():
        assert sha(path.read_bytes()) == pin
    memory = bytearray(65536)
    memory[0x4000:0xd000] = (SOURCE/'b08.bin').read_bytes()
    memory[0xe000:0xf800] = (SOURCE/'b09.bin').read_bytes()
    rows = decode(memory,0x8516,0xc7ba)
    assert len(rows) == 6525
    assert bytes(memory[0x8516:0x8520]) == bytes.fromhex('ADF8432908F0034CAAA8')
    blocks = [compile_block(memory, rows,0x8520,0x8556,'even X/patched-JMP prologue'),
              compile_block(memory, rows,0xa8aa,0xa8df,'odd X/patched-JMP prologue')]
    for parity, prefix in enumerate(blocks):
        literal_writes = [(w['address'],m['input']['literal'])
                          for m in prefix['macros'] if m['kind']=='copy_and_write_group'
                          for w in m['writes']]
        initial = [0xf0+parity,0x28+parity,0x58+parity,0x88+parity,
                   0xb8+parity,0xe8+parity,0x18+parity,0x48+parity]
        patch, target = (0x8976,0x8556) if parity==0 else (0xacff,0xa8df)
        assert literal_writes == list(zip(range(0xd000,0xd010,2),initial)) + [
            (patch,target&255),(patch+1,target>>8)]
        assert sum(m['kind']=='set_fixed_X' for m in prefix['macros']) == 1
        assert prefix['macros'][-1]['kind']=='clear_sum_carry'
        prefix.update(variant=parity,initial_X_low=initial,patched_jump_reset=target,
                      fixed_X=0x88,exit_carry={'literal':0})
    graph = []
    for parity, starts, final, lo, hi in ((0,EVEN,0xa8aa,0xf400,0xf500),
                                         (1,ODD,0xc7ba,0xf600,0xf700)):
        targets = [memory[lo+i] | memory[hi+i]<<8 for i in range(256)]
        assert set(targets) == (set(starts) if parity==0 else set(starts)-{0xbed1})
        for number, (first,end) in enumerate(zip(starts, starts[1:]+[final])):
            assert bytes(memory[first:first+3]) == bytes.fromhex('CE16D0')
            block = compile_block(memory,rows,first,end,
                                  'initial color loop with live dispatch' if number==0 else 'regular D011/pointer loop')
            block.update(variant=parity,reachable_from_8516=first in targets)
            assert len(block['pointer_transfers']) == 16
            assert len(block['sprite_Y_groups']) == (4 if number==0 else 7)
            assert sorted(w for g in block['sprite_Y_groups'] for w in g['destination_sprites']) == sorted(list(range(8))*2)
            f2 = [u for u in block['table_uses'] if u['table']==0xf200]
            f3 = [u for u in block['table_uses'] if u['table']==0xf300]
            if number == 0:
                assert not f2 and len(f3)==3
                assert [(u['index']['sample'],u['index']['offset']) for u in f3] == [(0,0),(1,0),(2,0)]
                assert len(block['raster_samples'])==4
                edge = dict(kind='live_raster_table_dispatch',jump_pc=end-3,
                            low_table=lo,high_table=hi,sample_pc=block['raster_samples'][-1]['first'],
                            post_sample_pc=block['raster_samples'][-1]['post_pc'],
                            target_formula='low[r] | (high[r] << 8)',
                            targets_by_raster_low=targets,runs=runs(targets),
                            source_operand_initial_target=starts[0])
            else:
                assert not f3 and len(f2)==17
                sequence = [(u['index']['sample'],u['index']['offset']) for u in f2]
                assert sequence == (EVEN_INDEX if parity==0 else ODD_INDEX)
                assert len(block['raster_samples']) == (8 if parity==0 else 7)
                edge = dict(kind='self_loop',jump_pc=end-3,target=first)
                assert block['macros'][-1]['initial_target'] == first
            block['normal_flow'] = edge
            blocks.append(block)
            graph.append(dict(first=first,end_exclusive=end,variant=parity,
                              reachable_from_8516=block['reachable_from_8516'],normal_flow=edge))
    blocks.sort(key=lambda b:b['first'])
    assert blocks[0]['first']==0x8520 and blocks[-1]['end_exclusive']==0xc7ba
    assert all(a['end_exclusive']==b['first'] for a,b in zip(blocks,blocks[1:]))
    assert sum(b['bytes'] for b in blocks)+10 == 0xc7ba-0x8516
    # Independently compare source instruction-site write inventory to macro outputs.
    source_writes = Counter((r['op'],r['operand']) for r in rows if r['op'] in ('STA','STX','STY','SAX','INC','DEC'))
    macro_writes = Counter()
    for block in blocks:
        for macro in block['macros']:
            for w in macro.get('writes',[]):
                macro_writes[('STY' if macro['kind']=='literal_lookup_index_and_write' else 'STA',w['address'])] += 1
            for s in macro.get('ordered_steps',[]):
                op = 'STX' if s['operation']=='literal_write' else ('DEC' if s['delta']==-1 else 'INC')
                macro_writes[(op,s['address'])] += 1
            if macro['kind']=='mask_write_D011_mirror':
                macro_writes[('SAX',macro['address'])] += 1
    assert source_writes == macro_writes
    anchors = [dict(block=b['first'],variant=b.get('variant'),**sample)
               for b in blocks for sample in b['raster_samples']]
    assert len(anchors)==106 and sum(a['source_address']==0xd112 for a in anchors)==2
    table_info = [dict(first=first,end_exclusive=first+256,
                       sha256=sha(bytes(memory[first:first+256])),
                       original_values=sorted(set(memory[first:first+256])),
                       runtime_generation_must_be_checked=True)
                  for first in (0xf200,0xf300,0xf400,0xf500,0xf600,0xf700)]
    out.mkdir(parents=True)
    dump(out/'raster-blocks.json',dict(selector=dict(first=0x8516,end_exclusive=0x8520,
         hex=bytes(memory[0x8516:0x8520]).hex().upper(),read_pointer=0x43f8,mask=8,
         zero_prefix=0x8520,nonzero_prefix=0xa8aa),blocks=blocks))
    dump(out/'raster-read-anchors.json',dict(points=anchors,
         input_contract='For each actually executed LDY D012/D112, bind the actual loaded Y value after the read. INY-based indices are derived, not fresh VIC samples. No expected store value is a model input.'))
    dump(out/'raster-graph.json',dict(kernel_graph=graph,
         external_cutoff='CIA1 Timer-B IRQ828C abandons the active source path; normal-flow edges do not predict where an interrupt lands.',
         dead_generated_loop=0xbed1,all_original_dispatch_entries_checked=512))
    (out/'raster_source.checked.py').write_bytes(Path(__file__).read_bytes())
    proof = dict(pass_=True,scope='Complete source-specific macro decomposition of both B8 raster branches; no native write replay, CPU execution, absolute timing or committed pixels',
        producer=meta(Path(__file__).resolve()),inputs=[meta(p) for p in PINS],
        source_range=dict(first=0x8516,end_exclusive=0xc7ba,bytes=0xc7ba-0x8516,
                          sha256=sha(bytes(memory[0x8516:0xc7ba])),instruction_sites=len(rows),
                          exact_nonoverlapping_macro_coverage=True),
        selector_and_prologues=dict(even_prefix=0x8520,odd_prefix=0xa8aa,
                                    both_set_X=0x88,both_clear_carry=True),
        kernel_count=15,reachable_kernel_count=14,unreachable_original_dispatch_target=0xbed1,
        all_source_instruction_writes_covered=True,
        write_site_inventory=[dict(op=op,address=addr,count=count) for (op,addr),count in sorted(source_writes.items())],
        live_raster_read_sites=len(anchors),
        F200_index_sequence_even=[dict(sample=s,offset=o) for s,o in EVEN_INDEX],
        F200_index_sequence_odd=[dict(sample=s,offset=o) for s,o in ODD_INDEX],
        tables=table_info,
        external_runtime_inputs=['Initial sprite X-high register D010, current VIC positions/control bytes, actual pointer RAM and effective bank pins.',
            'CPU decimal flag must be clear for the declared binary8-bit ADC formulas. The branch prologues clear carry but do not execute CLD.',
            'Actual loaded low-raster value at each executed LDY D012/D112. The read anchor list distinguishes new samples from derived INY indices.',
            'Current table generations F200..F7FF; original file bytes are pinned but later updates are not silently forbidden.',
            'Actual shared delay-helper code at019F/01A0/01A4 must preserve value/carry temporaries; source descriptors retain calls rather than inventing fixed clocks.',
            'Software-visible RMW reads, VIC mirrors and NMOS dummy/final bus writes belong to the independently guarded hardware layer.',
            'IRQ cutoff event and current source position; normal-flow graph alone neither schedules nor suppresses interrupts.'],
        limits=['Static source decoding is restricted to21 opcodes actually present in this exact17060-byte region; no generic interpreter or stepper is included.',
            'Macros retain source carry inputs and explicit post-add CLC placement. Pointer/Y increments are not replaced with ideal independent additions.',
            'There are221 F200 table-load/STA D011 sites and11 additional SAX D111 sites. Each SAX retains source literalF0 and masks it with X88, producing80 under the declared prologue contract.',
            'Full source coverage does not imply all generated blocks execute: original dispatch never selects BED1.',
            'No native expected write values are consumed, and no displayed rectangle, complete upscroll or frame-rate result is asserted.'],
        outputs=[output_meta(p) for p in sorted(out.iterdir())])
    dump(out/'raster-source-proof.json',proof)
    p=out/'raster-source-proof.json'
    print(json.dumps(dict(pass_=True,receipt=output_meta(p),blocks=len(blocks),kernels=15,
                          macros=sum(len(b['macros']) for b in blocks),live_reads=len(anchors)),indent=2))


if __name__=='__main__':
    main()
