#!/usr/bin/env python3
"""Original cell sinks and retained character-cache values; no VIC execution."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import tarfile

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'build/research/aloft-cells-20261109/glyph-analysis'
GEN = ROOT / 'build/research/aloft-cells-20261109/cell-analysis/accepted-02'
SEM = ROOT / 'build/research/aloft-cells-20261109/semantic-analysis/accepted-01'
CTX = ROOT / 'build/research/aloft-cells-20261109/context-analysis/accepted-01'
NATIVE = ROOT / 'build/research/aloft-20261109/native-analysis/accepted-01/native-proof.json'
READER = ROOT / 'research/quondam/snapshot_state.py'
VICE = ROOT / 'build/research/quondam/hardware-source/vice-3.10.tar.gz'
PINS = {
    GEN / 'cell-generator-proof.json': '480428221ed84aed404dde3dfd8fcf9c378aab39f4e00390bfbe9d77aa399e4c',
    SEM / 'cell-semantics-proof.json': '88e8f06afaa9d066a0587d54b95d8f4a6e8c354eb14908dc09da0e924d5da3ed',
    CTX / 'context-proof.json': '3610d8f46d722667f8d25f4f8976b363afc2c3c632c450f39d8d88d751d7e95e',
    NATIVE: '02243d0cbae68edad8aa5a51aec9e22e9cfa4c52f918f1ba30db9e5226b19eb4',
    READER: 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    VICE: '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def meta(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def output(folder, proof, name):
    row = next(row for row in proof['outputs'] if row['name'] == name)
    path = folder / name
    assert path.stat().st_size == row['bytes'] and sha(path.read_bytes()) == row['sha256']
    return path.read_bytes(), meta(path)


def write(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n')


def address_role(address):
    assert 0 <= address < 0x800 and address & 7 == 7
    alias = None
    if 0x400 <= address < 0x7e8:
        offset = address - 0x400
        alias = dict(matrix_base=0x400, row=offset // 40, column=offset % 40)
    return dict(address=address, glyph_code=address // 8, glyph_row=address & 7,
        conditional_charset_base=0, matrix_alias=alias)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    out = parser.parse_args().output.resolve()
    out.relative_to(BASE)
    assert not out.exists()
    inputs, pinned = [], {}
    for path, digest in PINS.items():
        assert sha(path.read_bytes()) == digest, path
        inputs.append(meta(path))
        if path.suffix == '.json':
            pinned[path] = json.loads(path.read_text())
    gen, sem, ctx = [pinned[path] for path in [GEN/'cell-generator-proof.json',
        SEM/'cell-semantics-proof.json', CTX/'context-proof.json']]
    assert gen['pass_'] and sem['pass_'] and ctx['pass_']
    source_ref = next(row for row in gen['source_contract']['state_files']
                      if row['path'].endswith('memory.bin'))
    source_path = ROOT / source_ref['path']
    assert meta(source_path) == source_ref
    source = source_path.read_bytes()
    assert sha(source[0xf43d:0xf47c]) == 'c84b1a042e5ec3895c205bc7a859ff290ebd68a66253a04f84f23bd170d0f513'
    inputs.append(source_ref)
    raw, ref = output(SEM, sem, 'cell-descriptors.json')
    inputs.append(ref)
    descriptors = json.loads(raw)['cells']
    assert len(descriptors) == 312
    # Exact F43D grammar was independently recognized by the generator proof.
    # Its X count reaches40 after Y0..31, with a second code only at Y>=24.
    matrix = [value for y in range(32) for value in ([y] if y < 24 else [y, y ^ 0xe8])]
    assert len(matrix) == len(set(matrix)) == 40
    codes = set(range(32)) | set(range(0xf0,0xf8))
    assert set(matrix) == codes
    glyphs = {8*code+7:255 for code in codes}
    assert len(glyphs) == 40 and set(glyphs).isdisjoint(range(0x7c0,0x7e8))
    assert set(glyphs).isdisjoint(range(0x400,0x500))
    cell_roles, sinks, active, state_slots = [], set(), set(), set()
    for row in descriptors:
        roles = {}
        for key in ['zp_x','zp_y','scratch_zp','screen_address']:
            address = row[key]
            roles[key] = address_role(address)
            sinks.add(address)
            if key in ('zp_x','zp_y'):
                state_slots.add(address)
            if key in ('zp_x','zp_y') or not row['lookup_writes_suppressed']:
                active.add(address)
        cell_roles.append(dict(pc=row['pc'], admitted_operand_roles=roles,
            result_stores_suppressed=row['lookup_writes_suppressed']))
    assert sinks == active == set(glyphs)
    assert len(state_slots) == 21
    # The actual code uses cached video-matrix bytes for character g-addresses.
    with tarfile.open(VICE) as archive:
        member = 'vice-3.10/src/viciisc/vicii-fetch.c'
        raw = archive.extractfile(member).read()
        lines = raw.decode().splitlines(keepends=True)
        fragment = ''.join(lines[162:208])
        assert '(vicii.vbuf[vicii.vmli] << 3) | vicii.rc' in fragment
        assert '(vicii.regs[0x18] & 0xe) << 10' in fragment
        assert 'if (mode & 0x40)' in fragment
    out.mkdir(parents=True)
    (out/'glyph_mapping.checked.py').write_bytes(Path(__file__).read_bytes())
    (out/'predicted-matrix-row24.bin').write_bytes(bytes(matrix))
    (out/'predicted-color-row24.bin').write_bytes(bytes([8]*40))
    write(out/'predicted-glyph-initial-bytes.json',dict(
        bytes=[dict(address=address,value=value) for address,value in sorted(glyphs.items())],
        origin='F43D original literal/state/scratch stores, not captured RAM'))
    write(out/'glyph-address-map.json',dict(cells=cell_roles,
        operand_address_union=[address_role(a) for a in sorted(sinks)],
        active_store_address_union=sorted(active), STX_STY_state_slots=sorted(state_slots),
        cached_character_row=matrix, conditional_glyph_row=7, conditional_charset_base=0,
        source_matrix_range=[0x7c0,0x7e8], no_sink_overlaps_source_matrix_row24=True,
        note='07xx has both glyph and earlier-matrix aliases. A fetch interpretation is conditional; address roles are not exclusive memory types.'))
    write(out/'primary-glyph-source.json',dict(archive=meta(VICE), member=member,
        member_sha256=sha(raw), first_line=163,last_line=208,text=fragment,
        fragment_sha256=sha(fragment.encode()),
        conditional_rule='BMM0 ECM0; bank0; D01810; ordinary RAM charset0000; glyphaddr=8*cached_code+RC',
        pipeline_limit='Mode selection/delay and whether/when a g-access occurs remain outside this address-only rule.'))
    # All original-source predictions above exist before either native RAM oracle opens.
    spec = importlib.util.spec_from_file_location('pinned_glyph_snapshot_reader',READER)
    reader=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)
    captures = {row['stem']:row for row in pinned[NATIVE]['captures']}
    comparisons=[]
    for stem, expected_pc in [('part08-body',0xf02b),('part08-frame01',0xf080)]:
        row=captures[stem]
        for ref in [row['ram'],row['snapshot']]:
            assert meta(ROOT/ref['path']) == ref
            inputs.append(ref)
        memory=(ROOT/row['ram']['path']).read_bytes()
        path=ROOT/row['snapshot']['path']
        state=reader.read_snapshot(path)
        ram=reader.module_payload(path,'C64MEM')
        cpu=reader.module_payload(path,'MAINCPU')
        assert len(ram)==65555 and memory==ram[4:65540]
        assert len(cpu)==103 and int.from_bytes(cpu[12:14],'little')==row['registers']['pc']==expected_pc
        assert int.from_bytes(cpu[:8],'little')==row['registers']['clock']
        assert row['stop']['natural'] and row['CPU_clock_flags_and_ports_equal']
        assert memory[0x7c0:0x7e8] == bytes(matrix)
        assert all(memory[address]==value for address,value in glyphs.items())
        vic=state['vicii']
        assert vic['color_ram'][960:1000] == [8]*40
        cached=vic['vbuf']==matrix and vic['cbuf']==[8]*40
        if stem=='part08-frame01':
            assert cached and vic['rc']==7
            assert vic['vc']==vic['vcbase']==0 and vic['idle_state']==1
            assert vic['bad_line']==vic['allow_bad_lines']==0
            assert vic['regs'][0x18]==0x10 and vic['regs'][0x16]&0x10
            assert vic['regs'][0x11]&0x60==0
        comparisons.append(dict(stem=stem,pc=expected_pc,clock=row['registers']['clock'],
            all40_source_matrix_bytes_equal=True,all40_initial_glyph_bytes_equal=True,
            all40_device_color_cells_equal8=True,cached40_codes_and_colors_equal_prediction=cached,
            VIC_stopped=dict(RC=vic['rc'],VC=vic['vc'],VCBASE=vic['vcbase'],idle=vic['idle_state'],
                bad_line=vic['bad_line'],allow_bad_lines=vic['allow_bad_lines'],
                D011_stored=vic['regs'][0x11],D016_stored=vic['regs'][0x16],D018_stored=vic['regs'][0x18]),
            capture_RAM_and_VSF_equal=True,
            cache_value_equality_does_not_prove_fetch_origin_or_future_lifetime=True))
    write(out/'native-glyph-comparisons.json',dict(pass_=True,captures=comparisons,
        full_context_and_logical_bank_custody_delegated_to_pinned_context=True))
    outputs=[dict(name=p.name,bytes=p.stat().st_size,sha256=sha(p.read_bytes()))
             for p in sorted(out.iterdir())if p.is_file()]
    proof=out/'glyph-mapping-proof.json'
    write(proof,dict(pass_=True,producer=meta(Path(__file__)),inputs=inputs,outputs=outputs,
        predicted_before_native_oracle_reads=True,source_cell_descriptors=312,
        distinct_active_glyph_row7_addresses=40,STX_STY_only_state_slots=21,
        source_matrix_bytes=40,source_color_cells=40,native_comparison_captures=2,
        preIRQ_all40_cached_codes_and_colors_equal_source_prediction=True,
        mode_and_RAM_charset_interpretation_is_conditional=True,
        no_CPU_native_VIC_or_downloaded_host_execution=True,
        limits=['Cached values match; no matrix-fetch origin/address or retained future cache lifetime is proved.',
            'Stopped RC7 coexists with idle1, VCBASE0 and badline-disabled state. It is not an observed active g-fetch.',
            'Initial FF glyph values matching at two stops are not a proof of every intervening reset/write.',
            '07xx glyph bytes physically alias earlier matrix rows22/23; address interpretations are not exclusive.',
            'No source-only complete bitmap, dynamic field, pixels, bus timing, FPS or named scene identity is established.']))
    print(json.dumps(meta(proof)))


if __name__=='__main__':
    main()
