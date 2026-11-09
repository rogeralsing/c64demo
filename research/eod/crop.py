#!/usr/bin/env python3
"""Reconstruct EOD's original static crop/prefix/clear generator as data."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/eod'
PINS = {
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-051.decoded.prg': 'e4899712681147b233a960d675aab369feebac4ba149073f1051d45f78b5312c',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-052.decoded.prg': '3adc5e1b6990cf41b3d93954de9d92bd3da62b4b562fc636cbd827cf94d67c04',
    'build/research/eod/frame-analysis/accepted-01/frame-proof.json': 'ef77c7a2d93d110ce5caa8c60c313d8d7313325ba51e9d355cff9e855535bb50',
    'build/research/eod/output-case-analysis/accepted-01/output-case-proof.json': '0fe2af337eb6a2674e6cb60b7f861b744457fa7ee8b65e05eed2d10bd9c6a0dd',
    'build/research/eod/prefix-analysis/accepted-01/prefix-proof.json': '3bc7c07dc281850885dc1671cbca55a2c9a42a1340d99bd8fe19afb919ec057b',
}
CASES = (
    ('native-03', 'build/research/eod/frame-analysis/accepted-01/frame-proof.json',
     'b5218a5a088bb0343970327b8ddfc03ea3c177f6bf471db5a739f4bd00817af9'),
    ('native-04', 'build/research/eod/output-case-analysis/accepted-01/output-case-proof.json',
     'c52bb838d493b5d6261b1b55f931df74b358136748ceb9f9de201b8ea499540c'),
)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def original_memory():
    memory = bytearray(65536)
    for number in (51, 52):
        path = BASE/f'file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-{number:03}.decoded.prg'
        raw = path.read_bytes()
        start = int.from_bytes(raw[:2], 'little')
        memory[start:start+len(raw)-2] = raw[2:]
    return memory


def parameters(memory):
    """Read constants from byte-guarded original instructions, not native RAM."""
    guards = []
    def guard(address, hexadecimal, role):
        raw = bytes.fromhex(hexadecimal)
        assert memory[address:address+len(raw)] == raw, (hex(address), role)
        guards.append(dict(address=address, bytes=hexadecimal, role=role))
    def pointer(address, zp):
        assert memory[address:address+1] == b'\xa9'
        assert memory[address+2:address+5] == bytes((0x85,zp,0xa9))
        assert memory[address+6:address+8] == bytes((0x85,zp+1))
        return memory[address+1] | memory[address+5] << 8
    guard(0x0f00, '4c120f', 'Original public initialization entry')
    guard(0x0f4c, 'c601205e10e601', 'Bank I/O out, build at105E, return at0F51, restore port')
    guard(0x11a1, 'a900851e', 'Reset the16-column bounds index for each plane')
    guard(0x11a5, 'a000a98a9104', 'Emit TXA to reset each prefix accumulator')
    guard(0x11b3, '8aa41ed962129045d97212b040', 'Lower inclusive and upper exclusive row tests')
    guard(0x11c0, 'a005b95c1291048810f8', 'Copy six-byte original EOR/STA template')
    guard(0x11ca, 'a000a98d910a', 'Emit absolute STA marker-clear opcode')
    guard(0x11d0, 'a001a5069104910ac8a5079104910a', 'Patch shared marker address into prefix and clear')
    guard(0x11df, 'a004a5089104c8a5099104', 'Patch output address into prefix')
    guard(0x11ea, '18a504690685049002e60518a50a6903850a9002e60b', 'Advance prefix6 and clear3 only for emitted cells')
    guard(0x1200, 'e606d002e60718a508690285089002e609e8e040909d', 'Advance marker1/output2 for every considered row, including skips')
    guard(0x1216, 'e61ea51e290fd087', 'Move to next column; wrap after16')
    guard(0x121e, '38a508e9ff8508a509e9078509', 'Subtract07FF with original SEC/borrow chain')
    guard(0x122b, 'a5084a90034ca111', 'Test output low-bit without modifying stored pointer')
    guard(0x1233, 'a000a9609104910a60', 'Append RTS to both generated streams and return')
    guard(0x125c, '4d00788d0070', 'Original six-byte prefix cell template')
    prefix, marker = pointer(0x1181,4), pointer(0x1189,6)
    output, clear = pointer(0x1191,8), pointer(0x1199,10)
    columns, rows = memory[0x121b]+1, memory[0x1213]
    lower_address = int.from_bytes(memory[0x11b7:0x11b9], 'little')
    upper_address = int.from_bytes(memory[0x11bc:0x11be], 'little')
    lower = list(memory[lower_address:lower_address+columns])
    upper = list(memory[upper_address:upper_address+columns])
    assert columns == 16 and rows == 64
    assert all(0 <= a < b <= rows for a,b in zip(lower,upper))
    return dict(prefix_start=prefix, marker_start=marker, output_start=output, clear_start=clear,
        columns=columns, rows=rows, lower_address=lower_address, upper_address=upper_address,
        lower=lower, upper=upper, output_row_step=memory[0x120a],
        output_plane_rewind=memory[0x1222] | memory[0x1228] << 8,
        group_opcode=memory[0x11a8], clear_opcode=memory[0x11cd],
        terminator=memory[0x1236], template=bytes(memory[0x125c:0x1262])), guards


def generate(p, inclusive_upper=False, rewind_override=None):
    """Typed generator semantics, without an instruction decoder or CPU state."""
    prefix, clear, groups = bytearray(), bytearray(), []
    marker, output, plane = p['marker_start'], p['output_start'], 0
    rewind = p['output_plane_rewind'] if rewind_override is None else rewind_override
    final_cursors = []
    while True:
        assert plane < 2, 'Original bounded two-plane domain'
        for column in range(p['columns']):
            prefix.append(p['group_opcode'])
            pairs = []
            for row in range(p['rows']):
                selected = p['lower'][column] <= row and (
                    row <= p['upper'][column] if inclusive_upper else row < p['upper'][column])
                if selected:
                    cell = bytearray(p['template'])
                    cell[1:3], cell[4:6] = marker.to_bytes(2,'little'), output.to_bytes(2,'little')
                    prefix.extend(cell)
                    clear.extend(bytes((p['clear_opcode'],))+marker.to_bytes(2,'little'))
                    pairs.append(dict(row=row, marker=marker, output=output))
                marker = (marker+1) & 65535
                output = (output+p['output_row_step']) & 65535
            groups.append(dict(plane=plane, column=column, lower=p['lower'][column],
                               upper_exclusive=p['upper'][column], pairs=pairs))
        output = (output-rewind) & 65535
        # Original LSR affects temporary A and C, not the saved pointer.
        final_cursors.append(dict(plane=plane, marker=marker, output_after_rewind=output,
                                  repeat=bool(output & 1)))
        if not output & 1:
            break
        plane += 1
    prefix.append(p['terminator'])
    clear.append(p['terminator'])
    assert p['prefix_start']+len(prefix) <= 65536
    assert p['clear_start']+len(clear) <= p['prefix_start']
    return bytes(prefix), bytes(clear), groups, final_cursors


def closed_form(p):
    """Independent address enumeration, without the source pointer recurrence."""
    prefix, clear, pairs = bytearray(), bytearray(), []
    for plane in range(2):
        for column in range(p['columns']):
            prefix.append(0x8a)
            for row in range(p['lower'][column],p['upper'][column]):
                marker = p['marker_start']+p['rows']*(p['columns']*plane+column)+row
                output = p['output_start']+p['output_row_step']*(p['rows']*column+row)+plane
                prefix.extend(b'\x4d'+marker.to_bytes(2,'little')+b'\x8d'+output.to_bytes(2,'little'))
                clear.extend(b'\x8d'+marker.to_bytes(2,'little'))
                pairs.append((marker,output))
    prefix.append(0x60)
    clear.append(0x60)
    assert len({a for a,b in pairs}) == len({b for a,b in pairs}) == len(pairs)
    return bytes(prefix), bytes(clear), pairs


def differences(expected, actual):
    return sum(a != b for a,b in zip(expected,actual))+abs(len(expected)-len(actual))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE/'crop-analysis').resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    for path,expected in PINS.items():
        assert sha((ROOT/path).read_bytes()) == expected, path
    original = original_memory()
    p,guards = parameters(original)
    prefix,clear,groups,cursors = generate(p)
    direct_prefix,direct_clear,pairs = closed_form(p)
    assert (prefix,clear) == (direct_prefix,direct_clear)
    assert len(groups) == 32 and len(pairs) == sum(len(g['pairs']) for g in groups)
    source_starts = (p['prefix_start'],p['clear_start'])
    controls = []
    for name,options in (('Treat upper bounds as inclusive',dict(inclusive_upper=True)),
                         ('Subtract0800 instead of07FF and stop before second plane',dict(rewind_override=0x800))):
        wrong_prefix,wrong_clear,wrong_groups,_ = generate(p,**options)
        assert wrong_prefix != prefix and wrong_clear != clear
        controls.append(dict(hypothesis=name,rejected=True,groups=len(wrong_groups),
            cells=sum(len(g['pairs']) for g in wrong_groups),prefix_bytes=len(wrong_prefix),
            clear_bytes=len(wrong_clear),prefix_different_bytes=differences(prefix,wrong_prefix),
            clear_different_bytes=differences(clear,wrong_clear)))
    comparisons,inputs = [], [artifact(ROOT/path) for path in PINS]
    for case_name,receipt_name,case_sha in CASES:
        receipt = json.loads((ROOT/receipt_name).read_text())
        assert receipt['pass_'] and receipt['case_sha256'] == case_sha
        for capture in receipt['captures']:
            if capture['stem'] == 'sys':
                continue  # Before this source initialization; deliberately not an oracle.
            record = capture['ram']
            path = ROOT/record['path']
            native = path.read_bytes()
            assert len(native) == record['bytes'] == 65536 and sha(native) == record['sha256']
            bounds = original[0x1262:0x1282]
            expected = (prefix,clear)
            results = [native[start:start+len(raw)] == raw for start,raw in zip(source_starts,expected)]
            assert all(results) and native[0x1262:0x1282] == bounds, (case_name,capture['stem'])
            comparisons.append(dict(case=case_name,stem=capture['stem'],PC=capture['registers']['pc'],
                ram=record,prefix_all_bytes_equal=results[0],clear_all_bytes_equal=results[1],
                original_bound_bytes_equal=True))
            inputs.append(artifact(path))
    assert all(any(row['stem'] == name+'-begin' for row in comparisons)
               for name in ('baseline','p110','p096','p072','p024','p206'))
    out.mkdir(parents=True)
    outputs = []
    for name,raw in (('expected-prefix-D800.bin',prefix),('expected-clear-C400.bin',clear),
                     ('crop.checked.py',Path(__file__).read_bytes())):
        (out/name).write_bytes(raw)
        outputs.append(dict(name=name,bytes=len(raw),sha256=sha(raw)))
    description = {key:value for key,value in p.items() if key != 'template'}
    description['template'] = p['template'].hex()
    proof = dict(pass_=True,scope='Original static initializer bounds and complete emitted prefix/clear bytes; native03/native04 bytes are comparison oracles only',
        producer=artifact(Path(__file__)),inputs=inputs,source_guards=guards,source_parameters=description,
        static_call_path='Controller0701 JSR0F00 ->0F12;0F4C DEC01;0F4E JSR105E;plot-cell generation falls through1181;crop returns0F51 INC01. This occurs before controller loads file52.',
        generation=dict(groups=len(groups),emitted_cells=len(pairs),considered_cells=2*p['columns']*p['rows'],
            skipped_cells=2*p['columns']*p['rows']-len(pairs),prefix_start=p['prefix_start'],
            prefix_bytes=len(prefix),prefix_RTS=p['prefix_start']+len(prefix)-1,
            prefix_sha256=sha(prefix),clear_start=p['clear_start'],clear_bytes=len(clear),
            clear_RTS=p['clear_start']+len(clear)-1,clear_sha256=sha(clear),
            source_pointer_recursion_equals_independent_closed_form=True,plane_end_cursors=cursors),
        bounds=[dict(column=i,lower_inclusive=a,upper_exclusive=b,rows=b-a)
                for i,(a,b) in enumerate(zip(p['lower'],p['upper']))],
        address_contract=dict(marker='7800+1024*plane+64*column+row',output='7000+128*column+2*row+plane',
                              source_bounds='Original1262/1272 constant tables, reused in both planes; no current-pose vertices or runtime framebuffer bytes are inputs'),
        native_comparisons=comparisons,negative_controls=controls,
        limits=['No native RAM, generated descriptor, current projected coordinate, marker or completed output enters expected-byte generation.',
            'The fixed original bounds are inputs from released source constants, not an independently derived geometric enclosure or proof of crop safety.',
            'All49 compared post-initialization captures retain the same plan; no claim is made about unobserved transient initialization stores or other parts overwriting these addresses.',
            'Only emitted code bytes through their final RTS are predicted; surrounding uninitialized gaps and previous-state bytes are not normalized.',
            'The plan still skips398 logical marker/output cells. This proof does not replace preserved previous-output/marker inputs with zeros.',
            'No arbitrary clipping, every visibility branch, full displayed field, animation-wide safety, native timing/FPS or optimization claim follows.',
            'Passive typed integer/source-data analysis only; no CPU interpreter, downloaded host entrypoint, emulator, build or process is executed.'],outputs=outputs)
    raw = (json.dumps(proof,indent=2)+'\n').encode()
    (out/'crop-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,receipt_bytes=len(raw),receipt_sha256=sha(raw),
                         native_comparisons=len(comparisons),cells=len(pairs),prefix_bytes=len(prefix),clear_bytes=len(clear)),indent=2))


if __name__ == '__main__':
    main()
