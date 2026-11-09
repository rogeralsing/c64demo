#!/usr/bin/env python3
"""Finite source/template/table mathematics for native-observed Aloft part06.

No CPU instructions, emulator, drive, native process, build or socket run.
Entry/init/precopy files are declared source observations, not an independent
decode of compressed disk resources or a closed whole-session custody proof.
"""
import argparse
from collections import Counter
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tarfile
import traceback

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-20261109'
CASE = BASE / 'native-01'
PINS = {
    'part06-entry-ram.bin': 'cdeb8d6f5964a37998bead8ca6d255f102e55c59c442a900d9aa859d2281ed10',
    'part06-initialized-ram.bin': '0d4bbf37ea84b6fdd74f8e8667cf6b08195471aa92a4435fa30e53eebcaa0cf9',
    'part06-precopy-ram.bin': 'b4edf3b485c79116dfd68914cd06d19828153943a6dae600397fa679c54a82a5',
    'part06-entry.vsf': 'a785fd5325cd442786215246750ffd88971834d7e73debec7a901eefdcb2998c',
    'part06-initialized.vsf': '795cf38a0d037d4c99b97a502173468472cafbf8442c16072ed11e9eb68f197f',
    'part06-precopy.vsf': '1b05ab6cb50316185eaf501992edaee0df5b43838cfba4c71bb022ebe7b8b6e9',
}
HELPERS = {
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'research/tower-power/static_loader.py': '21da904962fa53ab7fa3c72caf0bc5a21fa4eb0a94f2be6155ef06a6994b4ce4',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def load(name, path):
    assert sha((ROOT / path).read_bytes()) == HELPERS[path]
    spec = importlib.util.spec_from_file_location(name, ROOT / path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def guard(memory, first, hexadecimal, role):
    raw = bytes.fromhex(hexadecimal)
    assert memory[first:first + len(raw)] == raw, (hex(first), role)
    return dict(first=first, end_exclusive=first + len(raw), hex=raw.hex(), role=role)


def snapshots(reader):
    memories, contexts = {}, {}
    expected = {'part06-entry': (0x890, 99375303), 'part06-initialized': (0x893, 99495185),
        'part06-precopy': (0x8a4, 109545058)}
    for stem, (pc, clock) in expected.items():
        rawpath, snapshot = CASE / (stem + '-ram.bin'), CASE / (stem + '.vsf')
        for path in (rawpath, snapshot):
            assert artifact(path)['sha256'] == PINS[path.name]
        raw = rawpath.read_bytes()
        mem = reader.module_payload(snapshot, 'C64MEM')
        cpu = reader.module_payload(snapshot, 'MAINCPU')
        state = reader.read_snapshot(snapshot)
        assert len(raw) == 65536 and raw == mem[4:65540]
        assert int.from_bytes(cpu[:8], 'little') == clock and int.from_bytes(cpu[12:14], 'little') == pc
        assert cpu[14] & 8 == 0, 'Finite ADC/SBC expressions require binary mode.'
        assert (clock // 63 % 312, clock % 63) == (state['vicii']['raster_line'], state['vicii']['raster_cycle'])
        glue = reader.module_payload(snapshot, 'GLUE')
        assert state['modules']['GLUE']['version'] == [1,0] and len(glue) == 3 and glue[0] == 1
        contexts[stem] = dict(RAM=artifact(rawpath), snapshot=artifact(snapshot), PC=pc, clock=clock,
            flags=cpu[14], C64MEM_port_latch=mem[0], C64MEM_DDR=mem[1],
            all65536_RAM_bytes_equal_snapshot=True, beam=[state['vicii']['raster_line'], state['vicii']['raster_cycle']],
            VIC_regs=state['vicii']['regs'], CIA2_PRA=state['cia']['CIA2']['pra'], CIA2_DDRA=state['cia']['CIA2']['ddra'],
            GLUE_raw=glue.hex(), GLUE_type=glue[0], GLUE_old_vbank=glue[1], GLUE_alarm_active=glue[2],
            actual_ColorRAM_sha256=sha(bytes(state['vicii']['color_ram'])),
            actual_ColorRAM_unique=sorted(set(state['vicii']['color_ram'])),
            source_kind='Native-observed original program state; independent original-disk depack match not available in this lane.')
        memories[stem] = raw
    return memories, contexts


def source_contract(entry, decoder):
    guards = [
        guard(entry, 0x4800, 'a200a9d6', 'Initialization screen value and index'),
        guard(entry, 0x4834, 'a905', 'Initialization device ColorRAM value'),
        guard(entry, 0x4845, 'a900a020a2009d0060e8d0faee4d4888d0f4', 'Self-modified 32-page zero clear'),
        guard(entry, 0x4857, 'a9008d21d0a9068d22d0a9018d23d0a9188d18d08d16d0a93d8d02dd', 'Mode, shared colors and initial bank DDR'),
        guard(entry, 0x4882, 'a2faa04f8efeFF8cffFFa97e8d11d0a9028d12d0a9018d19d060', 'Initial raster IRQ vector and boundary setup'),
        guard(entry, 0x489c, '854f86508451a91e38ed06dc8dac481000', 'Register-save and CIA1TimerB-read branch operand'),
        guard(entry, 0x4aa0, 'eaeaeaeaeaeaeaeaeaeaeaeaeaeaeaea60', 'Fixed sixteen-NOP helper; no renderer inferred inside it'),
        guard(entry, 0x4b49, 'a9738d11d0a9748d11d0a23ea93d', 'Raster body X3E/A3D constants'),
        guard(entry, 0x4b79, 'a07d8c11d0eaea440020004c4cf54e', 'Body entry to first kernel'),
        guard(entry, 0x4ef5, 'a97e8d11d0a9028d12d0a9fa8dfeffa94f8dffffa9018d19d0202650203751206652', 'Raster-end stage/motion/patch calls'),
        guard(entry, 0x4ffa, '488a489848a97e8d11d0a92f8d12d0a99c8dfeffa9488dffffa9018d19d0202250', 'Line02 IRQ selects raster47 and callback'),
        guard(entry, 0x5022, '20000860', 'External0800 callback, outside renderer model'),
        guard(entry, 0x5029, 'a9148d18d0', 'Character-stage D01814'),
        guard(entry, 0x5078, 'a9188d18d0a957853a', 'Bitmap-stage D01818 and phase-table base57'),
        guard(entry, 0x5266, 'a206b546953fca10f9a9168dc852a641a442bd5e89854db9ae89854e', 'Seven-byte snapshot of motion state and pattern selectors'),
    ]
    screens = [0x400, 0x4400, 0x8400, 0xc400]
    assert [int.from_bytes(entry[p + 1:p + 3], 'little') for p in range(0x4804, 0x4834, 3)] == [a + b for a in screens for b in (0,0x100,0x200,0x300)]
    assert [int.from_bytes(entry[p + 1:p + 3], 'little') for p in range(0x4836, 0x4842, 3)] == [0xd800,0xd900,0xda00,0xdb00]
    prelude = bytes.fromhex('20a04ac410ad12d069ff290709708d11d0c8')
    assert len(prelude) == 18
    assert all(entry[0x48c4 + i * 18:0x48c4 + (i + 1) * 18] == prelude for i in range(26))
    tail = bytes.fromhex('a9708d11d04c004b')
    assert entry[0x4a98:0x4aa0] == tail
    for i in range(12):
        base = 0x4c00 + 64 * i
        assert entry[base:base + 4] == bytes.fromhex('eaac085d')
        assert entry[base + 4:base + 34] == bytes.fromhex('2c02dd') * 10
        assert entry[base + 34:base + 44] == bytes.fromhex('ea8c11d0eace') + (base + 2).to_bytes(2,'little') + bytes.fromhex('d0d4')
        expected_exit = bytes.fromhex('2cffff') if i == 11 else bytes([0x4c]) + (base + 0x41).to_bytes(2,'little')
        assert entry[base + 44:base + 47] == expected_exit
        assert entry[base + 47:base + 53] == bytes.fromhex('a97e8d11d060')
        variable = 0x16 + i
        patch = bytes.fromhex('8a1865') + bytes([variable]) + bytes.fromhex('2907aa18653a8d') + (base + 3).to_bytes(2,'little')
        patch += bytes([0xa5, variable, 0x8d]) + (base + 2).to_bytes(2,'little')
        assert entry[0x4f1b + 18 * i:0x4f1b + 18 * (i + 1)] == patch
    rows = decoder.traverse(entry, [0x4800,0x489c,0x4ffa,0x5026,0x5137,0x5266], 0x4800,0x5376)
    assert not any(0x5166 <= row['address'] < 0x5266 for row in rows)
    return dict(guards=guards, static_reachable_listing=rows, initialization_screens=screens,
        prelude=dict(first=0x48c4, repeated_blocks=26, block_bytes=18, block_hex=prelude.hex(),
            D011_expression='0x70 | ((sampled_D012 - 1 + int(Y >= ZP10)) & 7)',
            sampled_D012_is_unbound_external_input=True),
        kernel_template=dict(first=0x4c00, count=12, stride=64, bank_slot_count=10, bank_slot_offsets=list(range(4,34,3)),
            LDY_low_offset=2, LDY_high_offset=3, exit_opcode_offset=44,
            note='Template bytes and finite mutations only; source reachability is not an executed raster schedule.'),
        data_ranges=[[0x5166,0x5266],[0x5700,0x5f00],[0x8850,0x9200]])


def phase_tables(entry, precopy):
    result = []
    for base, value in [(0x5700,0x38),(0x8a00,0x18)]:
        predicted = bytes(value + ((page - index) & 7) for page in range(8) for index in range(256))
        assert predicted == entry[base:base + 2048] == precopy[base:base + 2048]
        result.append(dict(first=base,end_exclusive=base + 2048,bytes=2048,sha256=sha(predicted),
            formula=f'{value:#x} + ((page_index - low_address) & 7)',
            field_bits=dict(ECM=False,BMM=bool(value & 0x20),DEN=True,RSEL25=True),
            label='bitmap active-row controls' if value == 0x38 else 'character active-row controls'))
    return result


def predict_segments(source, observed):
    a,b,index_a,index_b,total,lo,hi = observed[0x46:0x4d]
    pointer = lo + 256 * hi
    assert pointer == 0x4c00 and 0 < a <= 35 and 0 < b <= 45
    initial = dict(countdown_a=a,countdown_b=b,index_a=index_a,index_b=index_b,
        initial_clip_accumulator=total,kernel_pointer=pointer,declared_input_addresses=[0x46,0x4d])
    rows = []
    for i in range(12):
        select_a, select_b = source[0x895e + index_a], source[0x89ae + index_b]
        assert select_a % 10 == select_b % 10 == 0 and select_a <= 210 and select_b <= 40
        length = min(a,b)
        if a == b:
            a,b,index_a,index_b = 35,45,index_a + 1,index_b + 1
        elif a < b:
            b,a,index_a = b - a,35,index_a + 1
        else:
            a,b,index_b = a - b,45,index_b + 1
        exit_opcode = 0x4c
        if total + length >= 256:
            length,total,exit_opcode = 256 - total,0,0x2c
        else:
            total += length
        assert length > 0
        opcodes = bytes(source[0x8850 + select_a + j] or source[0x892c + select_b + j] for j in range(10))
        assert set(opcodes) <= {0x8d,0x8e,0x8f}
        assert opcodes == bytes(observed[pointer + 4 + j * 3] for j in range(10))
        assert observed[pointer + 44] == exit_opcode and observed[0x16 + i] == length
        rows.append(dict(kernel=pointer,length=length,primary_pattern_offset=select_a,secondary_pattern_offset=select_b,
            opcode_hex=opcodes.hex(),exit_opcode=exit_opcode,all_ten_opcode_cells_equal=True,exit_and_length_equal=True))
        if total == 0:
            break
        pointer += 64
    assert len(rows) == 10 and sum(row['length'] for row in rows) == 164
    assert sum(row['length'] for row in rows) + initial['initial_clip_accumulator'] == 256
    phase, operand_rows = 6, []
    for i in range(12):
        base = 0x4c00 + 64 * i
        count = observed[0x16 + i]
        phase = (phase + count) & 7
        page = observed[0x3a] + phase
        assert observed[base + 2:base + 4] == bytes([count,page])
        operand_rows.append(dict(kernel=base,count=count,page=page,active=i < len(rows),
            count_kind='predicted by finite merge' if i < len(rows) else 'declared stale unused ZP value',
            both_LDY_operand_bytes_equal=True))
    return dict(inputs=initial,segments=rows,phase_operands=operand_rows,
        active_segments=len(rows),active_opcode_cells=10 * len(rows),active_logical_rows=sum(row['length']for row in rows),
        unused_templates=2,full_native_execution_or_motion_prediction=False,
        note='Current pre-copy software variables are declared inputs. Comparison proves the guarded merge/patch consistency, not when these source instructions executed.')


def primary_anchors():
    path=ROOT/'build/research/quondam/hardware-source/vice-3.10.tar.gz'
    assert artifact(path)['sha256']==HELPERS[str(path.relative_to(ROOT))]
    result=[]
    with tarfile.open(path)as archive:
        for member,ranges in {
            'vice-3.10/src/core/ciacore.c':[(799,811)],
            'vice-3.10/src/c64/c64cia2.c':[(60,74),(136,155)],
            'vice-3.10/src/c64/c64gluelogic.c':[(86,107),(169,180)],
            'vice-3.10/src/6510core.c':[(1686,1695),(3040,3050)],
            'vice-3.10/src/viciisc/vicii-mem.c':[(370,398)],
        }.items():
            raw=archive.extractfile(member).read();lines=raw.decode().splitlines(keepends=True)
            for first,last in ranges:
                text=''.join(lines[first-1:last]);result.append(dict(member=member,member_sha256=sha(raw),
                    first_line=first,last_line=last,fragment_sha256=sha(text.encode()),text=text))
    return result


def banks(context):
    assert context['CIA2_PRA']==0xf8
    result=[]
    for opcode,value in [(0x8d,0x3d),(0x8e,0x3e),(0x8f,0x3d & 0x3e)]:
        pins=(0xf8 | (~value & 255)) & 3
        bank=(~pins & 3) * 0x4000
        result.append(dict(opcode=opcode,operation={0x8d:'STA A',0x8e:'STX X',0x8f:'SAX A&X'}[opcode],
            requested_DDRA=value,logical_effective_PA_low_pins=pins,logical_VIC_bank=bank,
            character_D01814=dict(screen=bank + 0x400,charset=bank + 0x1000),
            bitmap_D01818=dict(screen=bank + 0x400,bitmap=bank + 0x2000)))
    assert [row['logical_VIC_bank']for row in result]==[0x4000,0x8000,0]
    return dict(PRA_input=0xf8,A=0x3d,X=0x3e,rows=result,actual_GLUE_type=context['GLUE_type'],
        limits='Logical CIA pins/requested bank only. Actual GLUE type1 has source branches for transient bank3/delayed DDR changes; these are not evaluated here. Logical character addresses do not resolve VIC character-ROM visibility. No same-cycle fetch, bus timing, badline or pixel composition is derived.')


def run(output):
    output.relative_to(BASE/'kefrens-analysis')
    output.mkdir(parents=True,exist_ok=False)
    source=Path(__file__).read_bytes();(output/'kefrens.checked.py').write_bytes(source)
    try:
        reader=load('aloft_kefrens_snapshot','research/quondam/snapshot_state.py')
        decoder=load('aloft_kefrens_disassembly','research/tower-power/static_loader.py')
        memories,contexts=snapshots(reader)
        entry,initialized,precopy=[memories[name]for name in ('part06-entry','part06-initialized','part06-precopy')]
        contract=source_contract(entry,decoder)
        assert all(initialized[a:a+1024]==bytes([0xd6])*1024 for a in contract['initialization_screens'])
        assert not any(initialized[0x6000:0x8000]) and contexts['part06-initialized']['actual_ColorRAM_unique']==[5]
        assert entry[0x4aa0:0x4ab1]==initialized[0x4aa0:0x4ab1]==precopy[0x4aa0:0x4ab1]
        assert entry[0x8850:0x89fe]==precopy[0x8850:0x89fe]
        phases=phase_tables(entry,precopy)
        patch=predict_segments(entry,precopy)
        truth=banks(contexts['part06-precopy'])
        write_json(output/'source-contract.json',contract)
        write_json(output/'finite-patch-comparison.json',patch)
        write_json(output/'snapshot-source-context.json',contexts)
        write_json(output/'primary-source-anchors.json',primary_anchors())
        write_json(output/'display-data-contract.json',dict(phase_tables=phases,bank_truth=truth))
        outputs=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes()))for p in sorted(output.iterdir())if p.is_file()]
        proof=dict(pass_=True,scope='Native-observed original part06 source/template contracts and finite patch/table consistency; no independent compressed-disk decode or raster execution.',
            producer=artifact(Path(__file__)),inputs=[artifact(CASE/name)for name in PINS]+[artifact(ROOT/name)for name in HELPERS],
            native_source_states={stem:dict(PC=row['PC'],clock=row['clock'],RAM=row['RAM'],snapshot=row['snapshot'])for stem,row in contexts.items()},
            source_code_first=0x4800,source_code_end_exclusive=0x5376,
            initialization_comparisons=dict(four1024byte_screen_maps_equal_D6=True,device_ColorRAM_all1024_equal5=True,
                all8192_bitmap_bytes6000_8000_zero=True),
            fixed_4AA0_NOP_helper_equal_in_all_three_states=True,
            phase_table_bytes_checked=4096,phase_tables=phases,bank_truth=truth,
            finite_merge_comparison=dict(active_segments=patch['active_segments'],active_opcode_cells=patch['active_opcode_cells'],
                active_rows=patch['active_logical_rows'],all_active_exit_and_count_cells_equal=True,
                all24_LDY_operand_bytes_equal=True,two_unused_templates_not_executed_by_this_descriptor=True),
            outputs=outputs,limits=[
                'Source arrays are natural native observations with same-RAM/VSF and PC/clock checks. Whole-session wire custody and independent original-disk part06 decoding are separate pending proofs.',
                'The trueprecopy ZP46..4C and phase base3A are declared mathematical inputs, not independently predicted motion state.',
                'No chronological raster trace, absolute write cycles, cycle budget, IRQ deadline, full field or pixels are reconstructed.',
                'Logical DDRA bank requests do not resolve the GLUE DDR-transition path, VIC pipelines, badlines, matrix/color fetches or analog hardware output.',
                'Bitmap6000 atprecopy is an observed loaded asset from wrapper calls, not an independently predicted CPU drawing result; wrapper relocation/counters are owned elsewhere.',
                'Named three-layer-pattern versus flipped/bitmapKefrens target attribution and joystick input are not inferred from directory/partnumber alone.',
                'No arbitrary phase/geometry/motion theorem, animation/FPS, product change, CPU interpreter, emulator, native process, build, socket or downloaded host execution.'])
        write_json(output/'kefrens-source-proof.json',proof)
        print(json.dumps(dict(pass_=True,proof=artifact(output/'kefrens-source-proof.json'),active_segments=patch['active_segments'],active_rows=patch['active_logical_rows'])))
    except Exception as error:
        write_json(output/'failure.json',dict(pass_=False,error=repr(error),traceback=traceback.format_exc(),producer_sha256=sha(source)))
        raise


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True,type=Path)
    run(parser.parse_args().output.resolve())
