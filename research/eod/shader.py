#!/usr/bin/env python3
"""Bind original EOD shader code, its 13 levels and thin-pattern X occupancy."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/eod'
EXTRACT = BASE/'file-analysis/accepted-03'
PINS = {
    'build/research/eod/file-analysis/accepted-03/file-proof.json': 'fb8e819f854fd500acb34ea023508a9966f95914f38e1c6de0db77e3f2381db9',
    'build/research/eod/file-analysis/accepted-03/extract.checked.py': '3d64cdd4ec2671a9b70126448a75db0802fcc84815558287f931fbea78284094',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-051.decoded.prg': 'e4899712681147b233a960d675aab369feebac4ba149073f1051d45f78b5312c',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-052.decoded.prg': '3adc5e1b6990cf41b3d93954de9d92bd3da62b4b562fc636cbd827cf94d67c04',
    'build/research/eod/controller-analysis/accepted-01/controller-proof.json': '256828263de51e95cb374db0c177e146e948752f61cc6651ff5371fe956532f6',
    'build/research/eod/controller-analysis/accepted-01/controller.checked.py': '033bafb6ac6e97283175ac6713af0eef60cb7991b653ee1c98c47a1a4afa83c9',
    'build/research/eod/primary/xor-forum.html': '5ce8ceecb2d681d6ade84798bc5dd4119d2d96d5610d65eca1c783941dc9ba42',
    'build/research/eod/primary/xor-forum-retrieval.json': '89a191266f074bbf5812644cb194984025ed0b2ca2697160764a4a778b3422a5',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def pass_plan(pattern, row, x0, x1):
    """Original full/half-X selection; selected endpoints are half-open."""
    assert 0 <= pattern <= 255 and row in (0, 1) and 0 <= x0 <= x1 < 64
    first, second = ((0xc0, 0x30), (0x0c, 0x03))[row]
    a, b = bool(pattern & first), bool(pattern & second)
    if not a and not b:
        return dict(kind='skip', columns=[], slope_factor=0, initial_single_X_advance=0)
    if a and b:
        return dict(kind='full_X', columns=list(range(x0, x1)), slope_factor=1, initial_single_X_advance=0)
    if a:
        start, end = (x0+1)//2, (x1+1)//2
        return dict(kind='half_X_even', columns=[2*k for k in range(start, end)], slope_factor=2,
                    initial_single_X_advance=x0 & 1, initial_fraction_ADC_carry=1 if x0 & 1 else None)
    start, end = x0//2, x1//2
    return dict(kind='half_X_odd', columns=[2*k+1 for k in range(start, end)], slope_factor=2,
                initial_single_X_advance=1-(x0 & 1), initial_fraction_ADC_carry=0 if not x0 & 1 else None)


def thin_line(memory):
    """Source-specific scalar witness for the retained mask04 line; no PC execution."""
    x0, x1, y0, y1, pattern = (memory[a] for a in (0x10, 0x11, 0x12, 0x13, 0x15))
    assert (x0, x1, y0, y1, pattern) == (32, 40, 72, 60, 4)
    assert memory[0x1767] == 10 and memory[0x5514] == 1
    assert memory[0x1a6c:0x1a73] == bytes.fromhex('a98aa008910460')
    assert [memory[a] for a in (0xe9, 0xeb, 0xed, 0xef)] == [0xb0, 0xb2, 0xb4, 0xb6]
    dx, half_dy = x1-x0, abs(y1-y0)//2
    reads = []
    def read(address):
        value = memory[address]
        reads.append(dict(address=address, value=value))
        return value
    def difference(index, carry):
        low = read(0xb000+half_dy+index) - read(0xb400+(half_dy ^ 255)+index) - (1-carry)
        carry = int(low >= 0)
        high = read(0xb200+half_dy+index) - read(0xb600+(half_dy ^ 255)+index) - (1-carry)
        return low & 255, high & 255, int(high >= 0)
    first_index = read(0xaf00+dx)
    lo, hi, carry = difference(first_index, 1)
    second_index = read(0xae00+dx)
    _, second_high, _ = difference(second_index, carry)
    value = lo+second_high
    unsigned_slope = (((hi+(value >> 8)) & 255) << 8) | (value & 255)
    # Original negative-slope path complements both bytes, without adding1.
    slope = unsigned_slope ^ 65535
    lo, hi = slope & 255, slope >> 8
    doubled_lo, doubled_hi = (lo << 1) & 255, ((hi << 1) | (lo >> 7)) & 255
    plan = pass_plan(pattern, 1, x0, x1)
    assert plan['kind'] == 'half_X_even' and plan['initial_single_X_advance'] == 0
    fraction = 0x40 if y0 % 2 == 0 else 0xc0
    integer = (((hi >> 1) | (hi & 128))+(y0 >> 1)) & 255
    # CPY start/end accepts the nonempty half-X interval and leaves carry1.
    carry = 1
    marker = bytearray(memory[0x7800:0x8000])
    plots, cells = [], []
    for index, x in enumerate(plan['columns']):
        k = x//2
        destination = 0x7c00+64*(k//2)
        mask_variable = 0x18 if k % 2 == 0 else 0x1a
        cell = 0xba00+16*k
        expected = (b'\xb9'+destination.to_bytes(2, 'little')+bytes((0x45, mask_variable))+
                    b'\x99'+destination.to_bytes(2, 'little')+bytes.fromhex('8a6506aa986507a8'))
        assert memory[cell:cell+16] == expected
        assert memory[0x1bbd+k] | (memory[0x1bdd+k] << 8) == cell
        mask = ((pattern & 12) << 4) if mask_variable == 0x18 else pattern & 12
        address = destination+integer
        assert 0x7800 <= address < 0x8000
        old = marker[address-0x7800]
        marker[address-0x7800] ^= mask
        plots.append(dict(logical_X=x, address=address, mask=mask, before=old,
                          after=marker[address-0x7800], fraction=fraction, integer=integer, carry=carry))
        cells.append(dict(address=cell, bytes=expected.hex()))
        # Endpoint RTS is at last cell+8, after its store and before its step.
        if index+1 < len(plan['columns']):
            value = fraction+doubled_lo+carry
            fraction, carry = value & 255, value >> 8
            value = integer+doubled_hi+carry
            integer, carry = value & 255, value >> 8
    assert slope == 0xff3f and (doubled_lo | (doubled_hi << 8)) == 0xfe7e
    return dict(marker=bytes(marker), details=dict(inputs=dict(x0=x0, x1=x1, y0=y0, y1=y1, pattern=pattern),
        prepared_table_reads=reads, slope_word=slope, doubled_slope_word=doubled_lo | (doubled_hi << 8),
        X_occupancy=plan['columns'], generated_cells=cells, plots=plots,
        final_generated_fraction=fraction, final_generated_integer=integer, final_carry=carry,
        expected_return_registers=dict(a=memory[0x1a6d], x=fraction, y=memory[0x1a6f], carry=carry),
        scope='Retained line only; prepared arithmetic tables and incoming markers are inputs, completed markers are not.'))


def native_witness(original):
    path = BASE/'controller-analysis/accepted-01/controller-proof.json'
    accepted = json.loads(path.read_text())
    assert accepted['pass_'] and accepted['case_sha256'] == '03b3a0faabf52736b3bb2cc176f4f98a12d4443f5a3d5395d636a91caae9b24c'
    captures = {c['stem']: c for c in accepted['captures']}
    inputs, ram = [], {}
    for stem in ('after51', 'after52', 'stable-frame', 'thin-line', 'thin-line-complete', 'stable-frame-complete', 'next-frame'):
        row = captures[stem]['ram']
        target = ROOT/row['path']
        raw = target.read_bytes()
        assert len(raw) == row['bytes'] == 65536 and sha(raw) == row['sha256']
        inputs.append(artifact(target))
        ram[stem] = raw
    assert ram['after51'][0x800:0x30dd] == original[0x800:0x30dd]
    assert ram['after52'][0x30dd:0x6600] == original[0x30dd:0x6600]
    assert ram['stable-frame'][0x546a:0x547f] == original[0x546a:0x547f]
    for stem in ('stable-frame', 'thin-line', 'thin-line-complete', 'stable-frame-complete', 'next-frame'):
        assert ram[stem][0x1767] == 10 and ram[stem][0x5514] == 1
    before, after = ram['thin-line'], ram['thin-line-complete']
    result = thin_line(before)
    assert result['marker'] == after[0x7800:0x8000]
    entry, exit = captures['thin-line']['registers'], captures['thin-line-complete']['registers']
    assert entry['pc'] == 0x1856 and exit['pc'] == 0x5e62 and exit['sp'] == entry['sp']+2
    expected = result['details']['expected_return_registers']
    assert all(exit[k] == expected[k] for k in ('a', 'x', 'y')) and exit['flags'] & 1 == expected['carry']
    differences = [0x7800+i for i, (a, b) in enumerate(zip(before[0x7800:0x8000], after[0x7800:0x8000])) if a != b]
    assert differences == sorted(p['address'] for p in result['details']['plots']) and len(differences) == 4
    frame0 = captures['stable-frame']['registers']['clock']
    frame1 = captures['stable-frame-complete']['registers']['clock']
    next0 = captures['next-frame']['registers']['clock']
    assert exit['clock']-entry['clock'] == 515 and frame1-frame0 == 58218 and next0-frame0 == 98254
    return dict(accepted_controller_proof=artifact(path), consumed_capture_inputs=inputs,
        full_payload51_native_equal_bytes=10461, full_payload52_native_equal_bytes=13603,
        shader_generation_bound=True, prior_overlay_rejection_reused=accepted['rejected_phase'],
        line=result['details'], marker_comparison=dict(start=0x7800, bytes=2048, all_bytes_equal=True,
            computed_XOR_write_bytes=4, preserved_incoming_bytes=2044, changed_addresses=differences,
            sha256=sha(result['marker'])), return_registers_equal=True,
        observed_elapsed_cycles=dict(line=515, stable_shader_body=58218, one_begin_interval=98254,
            outside_body=40036, source='Accepted original native clock witnesses; scalar predicts no timing.'),
        limits=['One original line, with prepared arithmetic tables and preceding markers as inputs.',
                'These marker bytes are not final displayed spans; common prefix reconstruction/clear is outside546A.',
                'One98,254-cycle begin interval is not a full-scene deliveredFPS measurement.']), result['marker']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE/'shader-analysis').resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    for name, pin in PINS.items():
        assert sha((ROOT/name).read_bytes()) == pin, name
    receipt = json.loads((EXTRACT/'file-proof.json').read_text())
    assert receipt['pass_']
    disk = next(d for d in receipt['disks'] if d['name'] == 'EdgeOfDisgrace_1a.d64')
    memory = bytearray(65536)
    bindings = []
    for number, start, end in ((51, 0x0800, 0x30dd), (52, 0x30dd, 0x6600)):
        row = next(f for f in disk['files'] if f['family'] == 'trackmo' and f['number'] == number)
        path = EXTRACT/row['decoded']['name']
        raw = path.read_bytes()
        assert sha(raw) == row['decoded']['sha256'] and len(raw) == row['decoded']['bytes']
        assert int.from_bytes(raw[:2], 'little') == start and len(raw)-2 == end-start
        memory[start:end] = raw[2:]
        bindings.append(dict(index=number, start=start, end_exclusive=end, source=artifact(path)))
    guards = []
    def guard(pc, raw, role):
        expected = bytes.fromhex(raw)
        assert memory[pc:pc+len(expected)] == expected, (hex(pc), role)
        guards.append(dict(PC=pc, bytes=raw, role=role))
    guard(0x0f0c, '4c8b0f4c920f', 'mainline init and completion-wait API jumps')
    guard(0x0f8b, '206754ee671760a90bcd6717d0fb60', 'shader init then scene-state increment; wait for state11')
    guard(0x17d8, '206a5490b2ee671760', 'scene-state10 frame call and continuation')
    guard(0x5467, '4c855420155520865520595720a95920565b20505d20655e', 'shader init JMP and seven frame calls')
    guard(0x5485, 'ee0a18ee0b18ee0c18ee0d18209d54a9908526a964852760', 'initialization and projection-lookup pointer')
    guard(0x555f, 'a8a20fb96d559ded6088ca10f660', 'copy moving16-byte ramp window into60ED')
    guard(0x5e43, 'e6a9a4a9b1b08510b1b48511b1b28512b1b68513b9ec6059ed608515205618', 'trace adjacent intensity-band transition')
    guard(0x1856, '38a511e510b014', 'line entry swaps descending endpoints')
    guard(0x1871, '8514d00160', 'zero horizontal extent returns')
    guard(0x18c3, 'a51c0a8506a51d2a8507', 'double slope word1C/1D into06/07 for half-X cells')
    guard(0x18e4, 'a51529f0d0034c9f1929c0f03d', 'upper nibble and first-selector rejection')
    guard(0x18f9, 'a5152930f054', 'upper second-selector test')
    guard(0x19ba, 'a515290fd0034c721a290cf03d', 'lower nibble and first-selector rejection')
    guard(0x19cf, 'a5152903f054', 'lower second-selector test')
    guard(0x123c, 'b9007845009900788a651caa98651da8', 'full-X generated-cell template and ordinary slope')
    guard(0x124c, 'b9007845009900788a6506aa986507a8', 'half-X generated-cell template and doubled slope')
    guard(0x193a, 'a5114aa8a5104aaab029', 'odd-site half-X start/end floors')
    guard(0x1953, 'a5114aa89001c8a5104aaa900d', 'even-site half-X start/end ceilings')
    guard(0x1944, 'a508651c8508a509651d8509', 'odd-site initial slope advance preserves carry0')
    guard(0x1960, 'e8a508651c8508a509651d8509', 'even-site initial slope advance preserves carry1')
    guard(0x1a6c, 'a98aa008910460', 'line return epilogue supplies A8A/Y08')
    levels = bytes(memory[0x556e:0x557b])
    assert levels == bytes.fromhex('fffbebeaaaa696955551414000') and len(levels) == 13
    selectors = [[(p >> s) & 3 for s in (6, 4, 2, 0)] for p in levels]
    assert [sum(s) for s in selectors] == list(range(12, -1, -1))
    transitions = bytes(a ^ b for a, b in zip(levels, levels[1:]))
    assert transitions == bytes.fromhex('041001400c3003c004100140')
    transition_rows = []
    occupancy_checks = 0
    for index, pattern in enumerate(transitions):
        fields = [(pattern >> s) & 3 for s in (6, 4, 2, 0)]
        assert sum(bool(f) for f in fields) == 1
        for x0 in range(64):
            for x1 in range(x0, 64):
                for row in (0, 1):
                    planned = pass_plan(pattern, row, x0, x1)
                    shifts = ((6, 4), (2, 0))[row]
                    direct = [x for x in range(x0, x1) if (pattern >> shifts[x & 1]) & 3]
                    assert planned['columns'] == direct
                    occupancy_checks += 1
        transition_rows.append(dict(levels=[index, index+1], pattern=pattern, nonzero_selector_fields=1,
            four_site_occupancy=[bool(x) for x in fields],
            source_classification=[pass_plan(pattern, row, 0, 63)['kind'] for row in (0, 1)]))
    native, marker = native_witness(memory)
    forum = (BASE/'primary/xor-forum.html').read_text()
    assert 'Often you don\'t need to double buffer your line-buffer' in forum
    assert 'unrolled' in forum and 'filler' in forum
    context = dict(URL='https://csdb.dk/forums/index.php?roomid=11&topicid=52629',
        author='HCL', author_timestamp='2008-02-13 09:23', raw_HTML_lines=[187, 190],
        scope='General author explanation of invisible line markers, visible-output buffering and unrolled filler memory; not an explicit EOD implementation specification.')
    out.mkdir(parents=True)
    outputs = []
    for name, raw in (('levels-556e.bin', levels), ('transitions.bin', transitions),
                      ('thin-marker-7800.bin', marker),
                      ('shader.checked.py', Path(__file__).read_bytes())):
        (out/name).write_bytes(raw)
        outputs.append(dict(name=name, bytes=len(raw), sha256=sha(raw)))
    proof = dict(pass_=True, scope='Original native-bound51/52 shader, packed-level algebra, thin-pattern X occupancy and one independent scalar marker-line witness; no whole-frame scanout',
        producer=artifact(Path(__file__)), inputs=[artifact(ROOT/p) for p in PINS], bindings=bindings, guards=guards,
        APIs=dict(mainline_init=0xf0c, init_entry=0x5467, init_body=0x5485, frame=0x546a,
                  frame_continuation=0x17db, scene_state=0x1767, active_state=10, completed_state=11,
                  line=0x1856, boundary_call=0x5e5f, boundary_continuation=0x5e62),
        levels=dict(address=0x556e, count=13, bytes=levels.hex(), selectors=selectors,
                    selector_sums=list(range(12,-1,-1)), runtime_window=0x60ed,
                    scope='Selector-code rank, not perceptual luminance or a verified live palette.'),
        transitions=transition_rows, independent_occupancy_checks=occupancy_checks,
        native_witness=native, primary_author_context=context,
        occupancy_contract=dict(X='Ascending half-open[x0,x1); zero-width returns.',
            full_X='Both selector fields nonzero: one generated cell per X, slope1C/1D.',
            half_even='Only first field: ceil(x0/2)..ceil(x1/2), doubled slope06/07; if x0odd advance original slope with fractional ADC carry1.',
            half_odd='Only second field: floor(x0/2)..floor(x1/2), doubled slope06/07; if x0even advance original slope with fractional ADC carry0.',
            skipped_nibble='An empty row-phase nibble bypasses that complete pass.'),
        limits=['Original loader/wire/fullRAMVSF acceptance is consumed from the pinned independent controller proof, not duplicated here.',
                'The 13-level table and adjacent XORs establish one nonzero two-bit field per transition; one retained line has independent Y stepping/write checks, not arbitrary clipping or all lines.',
                'Quarter occupancy of a four-site pattern does not imply exactly75% fewer elapsed cycles for arbitrary endpoints, slopes or IRQ/VIC phases.',
                'Whole-edge XOR-zero rejection at38B7 is separate from the line routine nibble/parity skipping.',
                'No independent lighting/normal reconstruction, full-frame pixels, timing model, new native execution, CPU interpreter or build.'], outputs=outputs)
    raw = (json.dumps(proof, indent=2)+'\n').encode()
    (out/'shader-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True, receipt_bytes=len(raw), receipt_sha256=sha(raw),
                         levels=len(levels), transition_masks=len(transitions), occupancy_checks=occupancy_checks), indent=2))


if __name__ == '__main__':
    main()
