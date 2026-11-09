#!/usr/bin/env python3
"""Two original EOD visibility boundaries and one committed output field."""
import argparse
import ast
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/eod'
CASE_PROOF = 'build/research/eod/boundary-case-analysis/accepted-01/boundary-case-proof.json'
CASE_SHA = 'd328247aab0c1a8953189ea5acfe9aa1bd29a39d04cab5857814309b8f7cca37'
PINS = {
    CASE_PROOF: '8acd59eb714d844855043cefe5526b872c3569a7af47779c7b7aabbda37c23b1',
    'research/eod/geometry.py': '7c70f18cc1f586ddb8be70f8a4be5bd9ce67a456eb2d4772ef74cb3f97415d4b',
    'research/eod/contours.py': '2fce8719143284f21b232b6a9fa80696b08cb63f9f81c5fb1ecda49270cca7d5',
    'research/eod/multi_pose.py': '61aa635ccfecff00a44c1d06862305e1387ef2c3faf92e50f30653ef488e8742',
    'research/eod/crop.py': 'ba122ec09c19223cfbbe979cf3d67c33c0c02e5424825acd61ec83cecf956c17',
    'research/eod/display.py': '4566af3d510f8b7108697456b8decc48c427c2cc0b033e369e42315eaa0f050d',
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'research/anomaly/scanout.py': 'c5e63a07f3060614710518aaf9b9e6c9365c297619af4e19719a4b5f8b62198f',
    'build/research/eod/crop-analysis/accepted-01/crop-proof.json': 'c4096025b34405d20d488d793b1a3551110986aac1738dffe4608c508cecf1e8',
    'build/research/eod/display-analysis/accepted-02/display-proof.json': 'c10a8291e174609d250c0149d500aa49f4c584752b3a6e7cf592ce3a090f982f',
    'build/research/eod/display-analysis/accepted-02/display.checked.py': '4566af3d510f8b7108697456b8decc48c427c2cc0b033e369e42315eaa0f050d',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-051.decoded.prg': 'e4899712681147b233a960d675aab369feebac4ba149073f1051d45f78b5312c',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-052.decoded.prg': '3adc5e1b6990cf41b3d93954de9d92bd3da62b4b562fc636cbd827cf94d67c04',
    'build/research/eod/boundary-analysis/accepted-01/boundary-proof.json': '465f38a0e3cde6e6c739083f698807ca6d7bacfc7851757a1ff9e20e5b9c1001',
    'build/research/eod/boundary-analysis/accepted-01/boundary.checked.py': 'bc29b8dbc13670eca4de2962db40d05a317183c2adea2b8578f867234796d5b7',
    'build/research/eod/boundary-analysis/accepted-02/boundary-proof.json': '1ee04a33efc9d805f172fb33e023c44202baa5ce7c28ab3ab355cc9598d13fc9',
    'build/research/eod/boundary-analysis/accepted-02/boundary.checked.py': '506f672ff992af2a50287619a696c65320a126e4bd8df52f927d1a6810050b39',
}
STAGES = {'begin':0x546a,'vertices':0x5473,'visibility':0x5476,'body':0x17db,
          'prefix-before':0x1a73,'filled':0x1750,'cleared':0x1753}
TARGETS = (('p082',82,5,6),('p028',28,3,13))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)),bytes=len(raw),sha256=sha(raw))


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name,ROOT/relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def fraction_record(numerator,denominator):
    from math import gcd
    divisor = gcd(numerator,denominator)
    return dict(numerator=numerator//divisor,denominator=denominator//divisor)


def compare_blocks(predicted,native,ranges):
    addresses=[address for start,end in ranges for address in range(start,end)]
    assert len(predicted) == len(addresses)
    observed=bytes(native[address] for address in addresses)
    errors=[dict(address=address,predicted=a,observed=b)
            for address,a,b in zip(addresses,predicted,observed) if a != b]
    return dict(bytes=len(predicted),ranges=ranges,all_equal=not errors,mismatches=len(errors),
                predicted_sha256=sha(predicted),observed_sha256=sha(observed),examples=errors[:8])


def fallback(visibility, native_vertices, native_visibility, face, determinant_expected, geometry):
    row = next(item for item in visibility['faces'] if item['index'] == face)
    points = row['arithmetic']['points']
    native_points = [(native_vertices[0x41+offset],native_vertices[0x43+offset])
                     for offset in row['record_offsets']]
    assert points == native_points
    (x0,y0),(x1,y1),(x2,y2) = points
    dx1,dy1,dx2,dy2 = x1-x0,y1-y0,x2-x0,y2-y0
    determinant = dx1*dy2-dy1*dx2
    assert determinant == determinant_expected
    carry,details = geometry.face_carry(points)
    assert details == row['arithmetic'] and details['path'] == 'seven equal quotient bits'
    assert carry == row['returned_carry'] == 1 and row['face_flag'] == 0
    assert native_visibility[0x60fd+face] == 0
    bits = details['quotient_bits']
    assert len(bits) == 7 and all(a == b for a,b in bits)
    u,v,w,t = details['absolute_differences']
    r1,d1,r2,d2 = min(u,v),max(u,v),min(w,t),max(w,t)
    assert d1 and d2 and max(d1,d2) <= 128
    q1,q2 = 128*r1//d1,128*r2//d2
    packed_bits = int(''.join(str(pair[0]) for pair in bits),2)
    assert q1 == q2 == packed_bits
    return dict(face=face,points=points,coordinate_differences=[dx1,dy1,dx2,dy2],
        signed_products=[dx1*dy2,dy1*dx2],signed_projected_determinant=determinant,
        normalized_ratios=[fraction_record(r1,d1),fraction_record(r2,d2)],
        exact_ratio_difference=fraction_record(r1*d2-r2*d1,d1*d2),
        original_quotient_bits=bits,independent_floor128_buckets=[q1,q2],
        no_ASL_byte_wrap_for_these_denominators=True,
        source_path=details['path'],returned_C=carry,predicted_face_flag=0,native_face_flag=0,
        area_sign_substitution=dict(face_flag_if_determinant_positive=int(determinant>0),
            same_native_flag=False,rejected_as_identical_visibility_replacement=True),
        interpretation='A finite seven-bit comparison tie returns SEC. The exact projected determinant is positive; it must not silently replace the original decision. This is not an independent physical-visibility or lighting proof.')


def prefix_from_source(before,marker,groups):
    output,cleared = bytearray(before[0x7000:0x7800]),bytearray(marker)
    for group in groups:
        accumulator = 0
        for pair in group['pairs']:
            accumulator ^= marker[pair['marker']-0x7800]
            output[pair['output']-0x7000] = accumulator
            cleared[pair['marker']-0x7800] = 0
    return bytes(output),bytes(cleared)


def analyze_pose(target,captures,geometry,contours,helpers,groups,code,p,out):
    name,counter,face,determinant = target
    memories,registers,inputs = {},{},[]
    for stage,pc in STAGES.items():
        record = captures[name+'-'+stage]
        assert record['registers']['pc'] == pc
        memories[stage],pin = helpers.read_capture(record)
        registers[stage] = record['registers']
        inputs.append(pin)
    before = memories['begin']
    assert before[0x1767] == 10 and list(before[0x5513:0x5515]) == [counter,1]
    source = helpers.source_guards(before,geometry)
    for memory in (before,memories['prefix-before']):
        assert memory[p['prefix_start']:p['prefix_start']+len(code[0])] == code[0]
        assert memory[p['clear_start']:p['clear_start']+len(code[1])] == code[1]
    assert before[0x7000:0x7800] == memories['prefix-before'][0x7000:0x7800]
    result = dict(name=name,inputs=inputs,registers=registers,source_guards=source,
        begin_angles=list(before[0x17ea:0x17ed]),begin_phase=1,begin_counter=counter)
    try:
        state = contours.initialize_contour_tables(geometry.initialize_tables(before))
        upstream = []
        for stage in ('ramp_stage','coefficient_stage','vertex_stage'):
            state,details = getattr(geometry,stage)(state)
            upstream.append(dict(stage=stage,details=details))
        vertices = bytes(state[0x40:0x70]+state[0xe8:0xf0])
        state,visibility = geometry.visibility_stage(state)
        upstream.append(dict(stage='visibility_stage',details=visibility))
        flags = bytes(state[0x60fd:0x6103]+state[0x6133:0x613f])
        boundary = fallback(visibility,memories['vertices'],memories['visibility'],face,determinant,geometry)
        model,stages = contours.run_stages(state)
        marker = stages['outer']
        output,cleared = prefix_from_source(before,marker,groups)
    except (AssertionError,ValueError,IndexError) as error:
        result.update(pass_=False,model_error=dict(type=type(error).__name__,message=str(error)))
        return result,[],None
    comparisons = dict(
        vertices=compare_blocks(vertices,memories['vertices'],((0x40,0x70),(0xe8,0xf0))),
        visibility=compare_blocks(flags,memories['visibility'],((0x60fd,0x6103),(0x6133,0x613f))),
        body_marker=helpers.compare(marker,memories['body'][0x7800:0x8000],0x7800),
        prefix_before_marker=helpers.compare(marker,memories['prefix-before'][0x7800:0x8000],0x7800),
        filled_marker=helpers.compare(marker,memories['filled'][0x7800:0x8000],0x7800),
        filled_output=helpers.compare(output,memories['filled'][0x7000:0x7800],0x7000),
        cleared_output=helpers.compare(output,memories['cleared'][0x7000:0x7800],0x7000),
        cleared_marker=helpers.compare(cleared,memories['cleared'][0x7800:0x8000],0x7800))
    files = []
    for suffix,raw in (('vertices.bin',vertices),('visibility.bin',flags),('marker-7800.bin',marker),
                       ('output-7000.bin',output),('cleared-7800.bin',cleared)):
        filename=name+'-'+suffix
        (out/filename).write_bytes(raw)
        files.append(dict(name=filename,bytes=len(raw),sha256=sha(raw)))
    result.update(pass_=all(row['all_equal'] for row in comparisons.values()),comparisons=comparisons,
        fallback=boundary,upstream=upstream,branch_coverage=helpers.branch_summary(model,upstream),
        preserved_marker_nonzero_bytes=sum(bool(value) for value in cleared),
        observed_elapsed_machine_cycles=dict(
            body=registers['body']['clock']-registers['begin']['clock'],
            prefix=registers['filled']['clock']-registers['prefix-before']['clock'],
            clear=registers['cleared']['clock']-registers['filled']['clock']),outputs=[row['name'] for row in files])
    return result,files,output


def display_result(case,captures,predicted,display,reader,scanout,original,out):
    packets,inputs = [],[]
    for stage in ('setup','mid','complete'):
        record = captures['p082-display-'+stage]
        for key in ('ram','snapshot'):
            assert artifact(ROOT/record[key]['path']) == record[key]
            inputs.append(record[key])
        snapshot = ROOT/record['snapshot']['path']
        state = reader.read_snapshot(snapshot)
        draw,meta,raster = scanout.draw_state(reader.module_payload(snapshot,'VIC-II'))
        packets.append(dict(ram=(ROOT/record['ram']['path']).read_bytes(),state=state,draw=draw,
                            meta=meta,raster=raster,registers=record['registers']))
    history = display.write_history(case,original,packets)
    original_failure = None
    try:
        result,pixels = display.committed_rectangle(predicted,*packets)
    except AssertionError as error:
        middle = packets[1]['state']['vicii']
        original_failure=dict(type=type(error).__name__,message=str(error),
            mid_GBUF=middle['gbuf'],mid_VMli=middle['vmli'],mid_RC=middle['rc'])
        rejected_path=BASE/'boundary-analysis/accepted-01/boundary-proof.json'
        rejected=json.loads(rejected_path.read_text())
        assert not rejected['pass_'] and rejected['case_sha256'] == case['case_sha256']
        assert all(row['pass_'] for row in rejected['poses'])
        assert rejected['display']['frozen_helper_failure'] == original_failure
        one_guard_path=BASE/'boundary-analysis/accepted-02/boundary-proof.json'
        one_guard=json.loads(one_guard_path.read_text())
        assert not one_guard['pass_'] and one_guard['case_sha256'] == case['case_sha256']
        assert one_guard['display']['frozen_helper_failure'] == original_failure
        assert one_guard['display']['adapter_failure']['type'] == 'AssertionError'
        checked_display=BASE/'display-analysis/accepted-02/display.checked.py'
        source=checked_display.read_text()
        node=next(node for node in ast.parse(source).body
                  if isinstance(node,ast.FunctionDef) and node.name == 'committed_rectangle')
        original_function=ast.get_source_segment(source,node)+'\n'
        old_span="    assert first <= fetch_index < first+16 and mv['raster_cycle'] < 57"
        new_span="    assert first == 22 and fetch_index == 16 and not (first <= fetch_index < first+16) and mv['raster_cycle'] < 57"
        old_blank='    assert fetched != 0  # A nonblank actual byte, not only an all-background latch.'
        new_blank='    assert fetched == 0  # This separately accepted case has an actual blank latch.'
        traceback=error.__traceback__
        while traceback.tb_next:
            traceback=traceback.tb_next
        assert source.splitlines()[traceback.tb_lineno-1] == old_span
        replacements=((old_span,new_span),(old_blank,new_blank))
        adapted=original_function
        for old,new in replacements:
            assert adapted.count(old) == 1
            adapted=adapted.replace(old,new)
        assert adapted.replace(new_span,old_span).replace(new_blank,old_blank) == original_function
        namespace=dict(display.__dict__)
        exec(compile(adapted,'<EOD-native06-blank-fetch-adapter>','exec'),namespace)
        try:
            result,pixels=namespace['committed_rectangle'](predicted,*packets)
        except AssertionError as adapted_error:
            return dict(pass_=False,inputs=inputs,write_history=history,
                frozen_helper_failure=original_failure,
                adapter_failure=dict(type=type(adapted_error).__name__,message=str(adapted_error))),[]
        previous_limit='Not all glyph fetches are individually latched; one nonblank gbuf byte is directly witnessed.'
        assert result['limits'].count(previous_limit) == 1
        result['limits']=[('Not all glyph fetches are individually latched; this case witnesses one actual blank gbuf byte outside the effect span, with no inside/nonblank-glyph latch witness.'
                          if text == previous_limit else text) for text in result['limits']]
        background=result['palette'][0]
        foreground=len(pixels)-result['color_counts'].get(str(background),0)
        assert foreground > 0
        adapter_name='blank-fetch-adapter.checked.py'
        (out/adapter_name).write_text(adapted)
        result.update(frozen_helper_rejected_precondition=original_failure,
            corrected_failure_attribution=dict(source_line=traceback.tb_lineno,expression=old_span,
                original_and_one_guard_adapter='Both failed at the span guard before reaching the fetched-nonzero/fetched-zero assertion. Initial nonblank-only attribution was wrong; this is observer footprint, not renderer failure.'),
            rejected_receipt=artifact(rejected_path),
            rejected_checked_source=artifact(BASE/'boundary-analysis/accepted-01/boundary.checked.py'),
            rejected_one_guard_receipt=artifact(one_guard_path),
            rejected_one_guard_checked_source=artifact(BASE/'boundary-analysis/accepted-02/boundary.checked.py'),
            adapter=dict(original_checked_source=artifact(checked_display),original_function_sha256=sha(original_function.encode()),
                adapted_function_sha256=sha(adapted.encode()),
                literal_replacements=[dict(before=old,after=new) for old,new in replacements],
                guard_replacements=2,other_function_source_unchanged=True,
                output_limit_metadata_corrected=True,foreground_committed_pixels=foreground,
                inside_glyph_latch_witness=False,nonblank_glyph_latch_witness=False,
                rationale='Same exact mode/bank/layout/cache/clock/history and all16384 committed-index comparisons. The sample-specific in-span/nonzero fetch conditions become exact observed outside-span/index16/first22/zero conditions; actual image is not blank.'))
        adapter_output=dict(name=adapter_name,bytes=len(adapted.encode()),sha256=sha(adapted.encode()))
    filename='p082-committed-indices.bin'
    (out/filename).write_bytes(pixels)
    result.update(pass_=True,inputs=inputs,write_history=history,
        independent_input='This producer p082-output-7000.bin, computed from p082-begin and ORIGINAL crop bounds only')
    outputs=[dict(name=filename,bytes=len(pixels),sha256=sha(pixels))]
    if original_failure is not None:
        outputs.append(adapter_output)
    return result,outputs


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    out=parser.parse_args().output.resolve()
    out.relative_to((BASE/'boundary-analysis').resolve())
    assert not out.exists(),'Choose a fresh output directory'
    for name,expected in PINS.items():
        assert sha((ROOT/name).read_bytes()) == expected,name
    case=json.loads((ROOT/CASE_PROOF).read_text())
    assert case['pass_'] and case['case_sha256'] == CASE_SHA
    captures={row['stem']:row for row in case['captures']}
    geometry=load('eod_boundary_geometry','research/eod/geometry.py')
    contours=load('eod_boundary_contours','research/eod/contours.py')
    helpers=load('eod_boundary_helpers','research/eod/multi_pose.py')
    crop=load('eod_boundary_crop','research/eod/crop.py')
    display=load('eod_boundary_display','research/eod/display.py')
    reader=load('eod_boundary_snapshot','research/quondam/snapshot_state.py')
    scanout=load('eod_boundary_scanout','research/anomaly/scanout.py')
    original=crop.original_memory()
    p,crop_guards=crop.parameters(original)
    prefix,clear,groups,cursors=crop.generate(p)
    assert (prefix,clear) == crop.closed_form(p)[:2]
    assert original[0x5b25:0x5b27] == bytes.fromhex('a006')
    assert original[0x5b43:0x5b48] == bytes.fromhex('8810e13860')
    out.mkdir(parents=True)
    poses,files,predicted=[],[],{}
    for target in TARGETS:
        result,outputs,output=analyze_pose(target,captures,geometry,contours,helpers,groups,(prefix,clear),p,out)
        poses.append(result);files.extend(outputs);predicted[target[0]]=output
    if predicted['p082'] is not None:
        actual_display,outputs=display_result(case,captures,predicted['p082'],display,reader,scanout,original,out)
        files.extend(outputs)
    else:
        actual_display=dict(pass_=False,blocked_by='p082 software model failed; no completed-output seed substituted')
    checked=Path(__file__).read_bytes()
    (out/'boundary.checked.py').write_bytes(checked)
    files.append(dict(name='boundary.checked.py',bytes=len(checked),sha256=sha(checked)))
    proof=dict(pass_=all(row['pass_'] for row in poses) and actual_display['pass_'],
        scope='Two additional original source-exact software poses at seven-bit visibility ties, source-generated crop plan and one bounded committed p082 display rectangle',
        producer=artifact(Path(__file__)),inputs=[artifact(ROOT/name) for name in PINS],case_sha256=CASE_SHA,
        crop=dict(source_only=True,source_guards=crop_guards,groups=len(groups),cells=sum(len(g['pairs']) for g in groups),
            prefix_bytes=len(prefix),prefix_sha256=sha(prefix),clear_bytes=len(clear),clear_sha256=sha(clear),
            plane_end_cursors=cursors,native_descriptors_used_as_generation_input=False),
        poses=poses,display=actual_display,
        limits=['Accepted case custody is consumed by hash; no duplicate wire/CPU/snapshot audit or new native process occurs here.',
            'Each software pose starts only from its own captured begin RAM. Current vertices, visibility, marker and output targets are comparison oracles only.',
            'Crop bounds and all expected prefix/clear descriptors come only from pinned original51/52 code/constants; generated native bytes are equality guards, never seeds.',
            'Static source sine/projection data, generated plot-cell context and incoming previous-state bytes remain explicit inputs.',
            'Positive exact projected determinants do not silently replace the source seven-bit comparison. This is finite source behavior, not independently established physical visibility or normal lighting.',
            'Fixed crop safety, arbitrary geometry/clipping, every helper branch and the entire animation remain unproved.',
            'The display scope is the committed128x128 rectangle and observed cache/history. This case witnesses an outside-effect blank midfetch, not an inside/nonblank-glyph latch; no complete312-line field, deliveredFPS or optimization savings claim.'],outputs=files)
    raw=(json.dumps(proof,indent=2)+'\n').encode()
    (out/'boundary-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=proof['pass_'],receipt_bytes=len(raw),receipt_sha256=sha(raw),
        poses=[dict(name=row['name'],pass_=row['pass_']) for row in poses],display_pass=actual_display['pass_']),indent=2))
    if not proof['pass_']:
        raise SystemExit(1)


if __name__=='__main__':
    main()
