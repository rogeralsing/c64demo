#!/usr/bin/env python3
"""Original Aloft part08 assets, finite initializer emissions and phase ABI.

Pure source-byte recognition and typed copy/patch math, not a CPU interpreter.
Native RAM is opened only after all independent predictions are persisted.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-motion-20261109/table-analysis'
COLOR_BASE = ROOT / 'build/research/aloft-decode-20261109/color-analysis/accepted-01'
SOURCE_SHA = '95a344b261b1b28d229da9778df80bae06eff39470ff4515820ce4e1fa86869e'
KNOWN_SHA = '438d63cca7a6a2f1eec8919adc9ac56936283ee29ce6c4af19f901e55b7e5ae9'
DELTA_SHA = '055dcbd8906b8ca8e76866349ef00ef40022d88447f90728773bc9666d810e1e'
COLOR_SHA = '44bbc6a94b22db33d81dc9f15178f1303a2db19fb22484292e0c6f894f00f4b2'
OLD_NATIVE = ROOT / 'build/research/aloft-20261109/native-analysis/accepted-01/native-proof.json'
OLD_NATIVE_SHA = '02243d0cbae68edad8aa5a51aec9e22e9cfa4c52f918f1ba30db9e5226b19eb4'
NATIVE = ROOT / 'build/research/aloft-execution-20261109/native-analysis/accepted-02/native-proof.json'
NATIVE_SHA = '5db9694db276541a5fd2b5cb386e92639e6da2c0d6cd644caf758eb113cc2326'
READER = ROOT / 'research/quondam/snapshot_state.py'
READER_SHA = 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a'
GUARDS = [
    (0xf000, 0xf02b, 'ecb358dacb400d3b9bd03031d417438736ffdd5ccde670e55f756c7334ca0c0d', 'initializer call order and clock redirect'),
    (0xf02b, 0xf080, 'd0b7c5c4d5dd5dc8e7d275934c318f7130eda25e91e47afed32d4dc3154a4296', 'postbody setup including05/06 seeds'),
    (0xf0bd, 0xf12f, '61b9d9b4478ebd79c9d57483bf74dc52d47055731072ad699535bebcc44e1961', 'reset, music, phase-call and counter ordering'),
    (0xf12f, 0xf2c2, '3cbd29f1225b203988d3be4b5c4e936573f4d8a5610f31f402235f366aaef3d6', 'four motion phase controllers'),
    (0xf2c2, 0xf43d, 'ecefbb67c618ac39c977aa610a2bbe826b8004223744fc98008b40f0c4183fd1', 'palette assets'),
    (0xf64e, 0xf676, '6ca3ee75335df1bf395835675652ea3b8ca508bc6eb7d671bbcdf4d127121cd9', '25 dispatcher-template copies'),
    (0xf676, 0xf686, '24f81e90ae08cce973a16edd7b232f2749d3e8740829ddaa107788beaa37d803', 'complete bit-reversal overwrite'),
    (0xf686, 0xf787, 'e3f97023b6c0ac3937ebd1ef424ccdfca9ca8980d65343f82e426db9c11d9a2f', 'four200-term program emitters'),
    (0xf817, 0xf858, 'ae77a3a5b93a0b5900cf43a2c079e53584e11e6b46b9934ff24d622ab58eac63', 'dispatcher and four motion templates'),
]
PHASES = [
    dict(index=0, entry=0xf12f, program=0xc000, X_operand=0xf130, Y_operand=0xf132,
         initial_X=7, initial_Y=0x5b, X_step=-3, Y_step=2, fade_in_operand=0xf142,
         fade_out_operand=0xf165, threshold={'ZP05_at_least':0x62}, next_entry=0xf18d,
         palettes=[[0xf2d2,0xf2e2,0xf2f2],[0xf302,0xf311,0xf320]], palette_register_groups=[[0x21],[0x22],[0x20,0x23]]),
    dict(index=1, entry=0xf18d, program=0xc800, X_operand=0xf18e, Y_operand=0xf190,
         initial_X=0x15, initial_Y=0x23, X_step=2, Y_step=-1, fade_in_operand=0xf19e,
         fade_out_operand=0xf1c1, threshold={'ZP05_at_least':0xd2}, next_entry=0xf1e9,
         palettes=[[0xf32f,0xf33e,0xf34d],[0xf35c,0xf36b,0xf37a]], palette_register_groups=[[0x21],[0x20,0x22],[0x23]]),
    dict(index=2, entry=0xf1e9, program=0xd000, X_operand=0xf1f3, Y_operand=0xf1f5,
         initial_X=0x2d, initial_Y=0x0f, X_step=-2, Y_step=-1, fade_in_operand=0xf208,
         fade_out_operand=0xf231, threshold={'ZP06_below':2,'ZP05_at_least':0x42}, next_entry=0xf259,
         palettes=[[0xf389,0xf398,0xf3a7],[0xf3b6,0xf3c5,0xf3d4]], palette_register_groups=[[0x20,0x21],[0x22],[0x23]]),
    dict(index=3, entry=0xf259, program=0xd800, X_operand=0xf263, Y_operand=0xf265,
         initial_X=0x34, initial_Y=0x57, X_step=1, Y_step=1, fade_in_operand=0xf277,
         fade_out_operand=0xf2a0, threshold={'ZP06_below':2,'ZP05_at_least':0x90}, next_entry=None,
         palettes=[[0xf3e3,0xf3f2,0xf401],[0xf410,0xf41f,0xf42e]], palette_register_groups=[[0x21],[0x22],[0x20,0x23]]),
]


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return dict(path=path.relative_to(ROOT).as_posix(), bytes=len(raw), sha256=sha(raw))


def checked(path, digest):
    raw = path.read_bytes()
    assert sha(raw) == digest, str(path)
    return raw


def check_ref(ref):
    raw = checked(ROOT / ref['path'], ref['sha256'])
    assert len(raw) == ref['bytes']
    return raw


def output_meta(path):
    raw = path.read_bytes()
    return dict(name=path.name, bytes=len(raw), sha256=sha(raw))


def emit_json(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def source_inputs():
    proof_path = COLOR_BASE / 'color-stream-proof.json'
    proof = json.loads(checked(proof_path, COLOR_SHA))
    assert proof['pass_'] is True
    source = checked(COLOR_BASE / 'bundle031-memory.bin', SOURCE_SHA)
    known = checked(COLOR_BASE / 'bundle031-known-mask.bin', KNOWN_SHA)
    delta = checked(COLOR_BASE / 'bundle031-delta-write-mask.bin', DELTA_SHA)
    assert len(source) == len(known) == len(delta) == 65536
    assert all(known[0xe600:0xf858])
    assert all(delta[0xe600:0xf000]), 'all five assets are actually rewritten in this generation'
    guards = []
    for first, end, digest, purpose in GUARDS:
        assert sha(source[first:end]) == digest
        guards.append(dict(first=first, end_exclusive=end, sha256=digest, purpose=purpose,
                           bytes_hex=source[first:end].hex(), all_source_known=True))
    # No generic execution is needed: these fixed calls select the four typed initializers.
    assert source[0xf01c:0xf02b] == bytes.fromhex('203df4207cf4204ef62086f64c76f6')
    assert source[0xf043:0xf04b] == bytes.fromhex('a9008505a9028506')
    assert source[0xf117:0xf123] == bytes.fromhex('200008202ff1e605d002c606')
    return source, guards, [meta(proof_path), meta(COLOR_BASE / 'bundle031-memory.bin'),
                            meta(COLOR_BASE / 'bundle031-known-mask.bin'), meta(COLOR_BASE / 'bundle031-delta-write-mask.bin')]


def predict_dispatcher(source):
    template = source[0xf817:0xf830]
    assert template == bytes.fromhex('200020'*7 + '20232060')
    memory = bytearray([0] * 601)
    ledger = []
    for group in range(25):
        for y in range(24, -1, -1):
            address = 0x500 + group * 24 + y
            memory[address - 0x500] = template[y]
            ledger.append([address, template[y]])
    assert memory[-1] == 0x60
    targets = [int.from_bytes(memory[i * 3 + 1:i * 3 + 3], 'little') for i in range(200)]
    assert targets == [0x2023 if i % 8 == 7 else 0x2000 for i in range(200)]
    return bytes(memory), dict(source=[0xf817,0xf830], groups=25, copies=625,
                               distinct_bytes=601, overlap_stores=24,
                               descending_copy=True, group_stride=24,
                               initialized_targets=targets, final_RTS_address=0x758,
                               runtime_mutable_high_byte_addresses=[0x502 + 3*i for i in range(200)],
                               original_low_bytes_persist=[0x23 if i % 8 == 7 else 0 for i in range(200)],
                               ordered_copy_sha256=sha(json.dumps(ledger,separators=(',',':')).encode()))


def predict_programs(source):
    """Recognize exactly four fixed source emitters, then apply their typed math."""
    specifications = [(0xc000,0xf830,-2,4,0xe600,0xe800),
                      (0xc800,0xf83a,-1,2,0xea00,0xec00),
                      (0xd000,0xf844,-0x81,2,0xea00,0xec00),
                      (0xd800,0xf84e,-0x55,1,0xea00,0xee00)]
    results, final_templates, ledger = [], bytearray(source[0xf830:0xf858]), []
    for base, template_address, x_step, y_step, x_table, y_table in specifications:
        template = bytearray(source[template_address:template_address + 10])
        assert template == bytes([0xbd,0,x_table>>8,0x79,0,y_table>>8,0x8d,2,5,0x60])
        output = bytearray(1801)
        terms = []
        for i in range(200):
            target = int.from_bytes(template[7:9], 'little')
            assert target == 0x502 + 3*i
            for y in range(9,-1,-1):
                output[9*i+y] = template[y]
                ledger.append([base+9*i+y,template[y]])
            terms.append(dict(index=i, pc=base+9*i, LDA_base=x_table+template[1],
                              ADC_base=y_table+template[4], store_address=target,
                              LDA_source_asset=x_table, ADC_source_asset=y_table,
                              incoming_ADC_carry_required=True))
            template[1] = (template[1] + x_step) & 255
            template[4] = (template[4] + y_step) & 255
            template[7:9] = (target+3).to_bytes(2,'little')
        assert output[-1] == 0x60
        final_templates[template_address-0xf830:template_address-0xf830+10] = template
        results.append(dict(base=base, end_exclusive=base+1801, template_source=template_address,
                            x_low_step=x_step, y_low_step=y_step, bytes=bytes(output), terms=terms,
                            final_unemitted_template=bytes(template), copies=2000, distinct_bytes=1801,
                            last_RTS_address=base+1800))
    return results, bytes(final_templates), dict(logical_stores=len(ledger), distinct_bytes=7204,
                                                overwritten_RTS_bytes=796,
                                                logical_write_sha256=sha(json.dumps(ledger,separators=(',',':')).encode()),
                                                pure_binary_arithmetic_precondition=True,
                                                source_port_order='F704 DEC01 before D000/D800 writes; F784 INC01 afterward. C000/C800 emitted first. Physical mapping is a separately checked captured context.')


def phase_abi(source):
    result = []
    for phase in PHASES:
        row = dict(phase)
        assert source[row['X_operand']] == row['initial_X'] and source[row['Y_operand']] == row['initial_Y']
        assert source[row['X_operand']-1] == 0xa2 and source[row['Y_operand']-1] == 0xa0
        assert source[row['fade_in_operand']] == source[row['fade_out_operand']] == 14
        row.update(byte_arithmetic_modulus=256, fade_initial_index=14,
                   phase_immediates_are_runtime_mutable=True,
                   incoming_carry_not_defined_by_table_ABI=True)
        if row['index'] == 3:
            assert source[0xf29f:0xf2a8] == bytes.fromhex('a20ed005a9018d8f08')
            row['exit_behavior'] = 'At fade-out X==0 request088F=1; BNE, not BMI, guards the request. No invented negative-index stop if wrapper continues.'
        else:
            row['exit_behavior'] = 'After final fade-out, a negative immediate selects source patch of JSR F11A operand F11B/F11C to next entry.'
        result.append(row)
    return dict(phases=result, source_initial_motion_call=dict(JSR_PC=0xf11a,target=0xf12f,
                 low_operand=0xf11b,high_operand=0xf11c),
                counter=dict(low_ZP=5,high_ZP=6,initial_low=0,initial_high=2,
                             initialized_after_F02B_at=[0xf043,0xf04b],
                             update_after_motion_call='INC05; if result zero DEC06',
                             no_invented_frame_count_or_effect_ID=True),
                ordering=['F0BD resets40glyph sinks','F117 JSR0800 (music/source context external to this ABI)',
                          'F11A invokes active motion controller','F11D advances05/06counter'],
                clock_redirect=dict(source_FE_to_FA=True,source_FF_to_FB=True,
                                    resident_0801_operand=0xfa,resident_0805_operand=0xfb),
                runtime_program_input='8-bit X,8-bit Y and incoming carry are genuine inputs; table assets do not supply a carry default.',
                coverage='Four source controllers and initialized assets/programs. Runtime target evaluation and inter-frame evolution belong to independent motion producer.')


def paired_oracle(reader, capture):
    raw = check_ref(capture['ram'])
    check_ref(capture['snapshot'])
    path = ROOT / capture['snapshot']['path']
    state = reader.read_snapshot(path)
    cpu, mem = reader.module_payload(path,'MAINCPU'), reader.module_payload(path,'C64MEM')
    assert state['modules']['MAINCPU']['version'] == [1,4] and len(cpu) == 103
    assert state['modules']['C64MEM']['version'] == [0,1] and len(mem) == 65555
    assert raw == mem[4:65540] and len(raw) == 65536
    reg = capture['registers']
    assert int.from_bytes(cpu[:8],'little') == reg['clock']
    assert int.from_bytes(cpu[12:14],'little') == reg['pc']
    assert list(cpu[8:12]) == [reg[x] for x in ('a','x','y','sp')] and cpu[14] == reg['flags']
    assert reg['port00'] == mem[1] == mem[65542] and reg['port01'] == mem[65541]
    assert (reg['line'],reg['cycle']) == (state['vicii']['raster_line'],state['vicii']['raster_cycle'])
    assert (reg['line'],reg['cycle']) == (reg['clock']//63%312,reg['clock']%63)
    return raw


def late_native_comparisons(source, programs, dispatcher, final_templates, lookup):
    old = json.loads(checked(OLD_NATIVE, OLD_NATIVE_SHA))
    new = json.loads(checked(NATIVE, NATIVE_SHA))
    checked(READER, READER_SHA)
    spec = importlib.util.spec_from_file_location('motion_table_frozen_reader',READER)
    reader = importlib.util.module_from_spec(spec);spec.loader.exec_module(reader)
    old_by = {x['stem']:x for x in old['captures']}
    new_by = {x['stem']:x for x in new['captures']}
    choices = [('old-body',old_by['part08-body'],True),('old-preIRQ',old_by['part08-frame01'],False),
               ('first-pre0500',new_by['dispatcher'],True),('later-pre0500',new_by['later-dispatcher'],False)]
    entry_registers = old_by['part08-entry']['registers']
    assert not (entry_registers['flags'] & 8) and entry_registers['port01'] == 0x35
    comparisons, observed = [], []
    for label,capture,initial_dispatcher in choices:
        ram = paired_oracle(reader,capture)
        assert not (capture['registers']['flags'] & 8)
        assert capture['registers']['port01'] == 0x35
        assert ram[0xe600:0xf000] == source[0xe600:0xf000]
        assert ram[0xf2c2:0xf43d] == source[0xf2c2:0xf43d]
        assert ram[0x400:0x500] == lookup
        assert ram[0xf830:0xf858] == final_templates
        for program in programs:
            assert ram[program['base']:program['end_exclusive']] == program['bytes']
        if initial_dispatcher:
            assert ram[0x500:0x759] == dispatcher
        else:
            assert all(ram[0x500+i*3] == 0x20 and ram[0x501+i*3] == dispatcher[i*3+1] for i in range(200))
            assert ram[0x758] == 0x60
        initial_source_operands = label == 'old-body'
        if initial_source_operands:
            for p in PHASES:
                for key in ('X_operand','Y_operand','fade_in_operand','fade_out_operand'):
                    assert ram[p[key]] == source[p[key]]
        observations = dict(label=label,capture=capture,
                            ZP05=ram[5],ZP06=ram[6],FA=ram[0xfa],FB=ram[0xfb],
                            active_motion_JSR=int.from_bytes(ram[0xf11b:0xf11d],'little'),
                            phase_mutable_bytes=[dict(phase=p['index'],X=ram[p['X_operand']],Y=ram[p['Y_operand']],
                                fade_in=ram[p['fade_in_operand']],fade_out=ram[p['fade_out_operand']]) for p in PHASES],
                            values_are_observations_not_table_prediction_seeds=True)
        observed.append(observations)
        comparisons.append(dict(label=label,capture=capture,
             all65536_RAM_equal_snapshot=True,CPU_ports_clock_beam_equal=True,
             all2560_original_motion_asset_bytes_equal=True,all379_palette_asset_bytes_equal=True,
             all7204_runtime_program_bytes_equal=True,all40_final_source_template_bytes_equal=True,
             all256_bit_reversal_bytes_equal=True,
             initial_dispatcher_comparison=dict(performed=initial_dispatcher,bytes=601 if initial_dispatcher else 0,
                                               all_equal=True if initial_dispatcher else None),
             all401_dispatcher_opcode_low_RTS_bytes_equal=True,
             initial_phase_operand_comparison=dict(performed=initial_source_operands,
                                                   all_equal=True if initial_source_operands else None),
             decimal_clear_and_RAM35_mapping_at_declared_boundary=True,
             source_context_not_pre_motion_boundary=True))
    return comparisons,observed,[meta(OLD_NATIVE),meta(NATIVE),meta(READER)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    args = parser.parse_args()
    out=(ROOT/args.output).resolve();out.relative_to(BASE);out.mkdir(parents=True,exist_ok=False)
    (out/'motion_tables.checked.py').write_bytes(Path(__file__).read_bytes())
    source,guards,inputs=source_inputs()
    dispatcher,dispatcher_abi=predict_dispatcher(source)
    programs,templates,program_ledger=predict_programs(source)
    phases=phase_abi(source)
    lookup=bytes(int(f'{x:08b}'[::-1],2) for x in range(256))
    assets=[]
    for address in range(0xe600,0xf000,512):
        data=source[address:address+512];assert data[:256]==data[256:]
        p=out/f'asset-{address:04x}-512.bin';p.write_bytes(data)
        assets.append(dict(base=address,end_exclusive=address+512,data=output_meta(p),
                           kind='original compressed-stream asset',known_bytes=512,bundle31_rewritten_bytes=512,
                           two_identical_256_byte_periods=True,minimum=min(data),maximum=max(data),
                           analytic_curve_formula_not_inferred=True))
    (out/'initial-dispatcher-0500.bin').write_bytes(dispatcher)
    (out/'bit-reversal-0400.bin').write_bytes(lookup)
    (out/'final-motion-templates-f830.bin').write_bytes(templates)
    (out/'palette-assets-f2c2-f43d.bin').write_bytes(source[0xf2c2:0xf43d])
    program_rows=[]
    for program in programs:
        p=out/f'program-{program["base"]:04x}.bin';p.write_bytes(program['bytes'])
        program_rows.append({k:v for k,v in program.items() if k not in ('bytes','final_unemitted_template','terms')}
                            |dict(data=output_meta(p),final_unemitted_template_hex=program['final_unemitted_template'].hex(),
                                  term_count=200,term_stride=9,term_opcodes=[0xbd,0x79,0x8d],
                                  LDA_asset=program['terms'][0]['LDA_source_asset'],
                                  ADC_asset=program['terms'][0]['ADC_source_asset'],
                                  destination_formula='0502+3*i',
                                  low_operand_formula='(initial_low+i*step)&255; source high byte is not advanced on low wrap',
                                  indexed_asset_offset_domain=[0,510],incoming_ADC_carry_required=True))
    abi=dict(assets=assets,programs=program_rows,dispatcher=dispatcher_abi,
             dispatcher_data=output_meta(out/'initial-dispatcher-0500.bin'),
             lookup_data=output_meta(out/'bit-reversal-0400.bin'),
             final_templates_data=output_meta(out/'final-motion-templates-f830.bin'),
             palette_assets_data=output_meta(out/'palette-assets-f2c2-f43d.bin'),
             motion=phases,program_generation=program_ledger,
             binary_arithmetic_and_IO_hidden_for_D000_programs_required=True,
             incoming_carry_unspecified=True,native_output_seeding=False)
    emit_json(out/'source-guards.json',guards)
    emit_json(out/'table-abi.json',abi)
    # Immutable source predictions are now on disk, before any native RAM read.
    predicted_pins=[output_meta(p) for p in sorted(out.iterdir()) if p.is_file()]
    comparisons,observations,more_inputs=late_native_comparisons(source,programs,dispatcher,templates,lookup)
    assert predicted_pins==[output_meta(out/x['name']) for x in predicted_pins]
    emit_json(out/'native-mutable-observations.json',observations)
    emit_json(out/'native-comparisons.json',comparisons)
    proof=dict(pass_=True,producer=meta(Path(__file__).resolve()),inputs=inputs+more_inputs,
               independent_predictions_persisted_before_native_RAM_reads=True,
               source_asset_bytes=2560,runtime_program_bytes=7204,runtime_program_terms=800,
               initial_dispatcher_bytes=601,bit_reversal_bytes=256,palette_asset_bytes=379,
               native_contexts=len(comparisons),all_declared_native_comparisons_equal=True,
               no_CPU_native_emulator_build_or_downloaded_host_execution=True,
               dynamic_motion_target_evaluation_delegated=True,
               table_ABI=output_meta(out/'table-abi.json'),
               limits=['Original asset values are decoded bytes, not a recovered analytic sine equation or physical angle model.',
                       'Phase indices and05/06captured mutable state remain separate from source initial seeds.',
                       'No incoming ADC carry is invented from expected targets. Music/caller return carry must be independently bound by the runtime consumer.',
                       'Old F02B is before05/06 setup; the later source-generation contexts are not pre-F12F boundaries.',
                       'No future frames, named scene identity, full animation, physical timing or FPS claim.'],
               outputs=[output_meta(p) for p in sorted(out.iterdir()) if p.is_file()])
    p=out/'motion-table-proof.json';emit_json(p,proof);print(json.dumps(meta(p)))


if __name__=='__main__':
    main()
