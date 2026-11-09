#!/usr/bin/env python3
"""Original EOD text-display contract and passive retained snapshot checks."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import tarfile

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'build/research/eod'
PINS = {
    'research/quondam/snapshot_state.py': 'c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a',
    'research/anomaly/scanout.py': 'c5e63a07f3060614710518aaf9b9e6c9365c297619af4e19719a4b5f8b62198f',
    'build/research/quondam/hardware-source/vice-3.10.tar.gz': '8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-051.decoded.prg': 'e4899712681147b233a960d675aab369feebac4ba149073f1051d45f78b5312c',
    'build/research/eod/file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-052.decoded.prg': '3adc5e1b6990cf41b3d93954de9d92bd3da62b4b562fc636cbd827cf94d67c04',
    'build/research/eod/frame-analysis/accepted-01/frame-proof.json': 'ef77c7a2d93d110ce5caa8c60c313d8d7313325ba51e9d355cff9e855535bb50',
    'build/research/eod/prefix-analysis/accepted-01/prefix-proof.json': '3bc7c07dc281850885dc1671cbca55a2c9a42a1340d99bd8fe19afb919ec057b',
    'build/research/eod/output-case-analysis/accepted-01/output-case-proof.json': '0fe2af337eb6a2674e6cb60b7f861b744457fa7ee8b65e05eed2d10bd9c6a0dd',
    'build/research/eod/output-case-analysis/accepted-01/output_case.checked.py': '1b5d654fd75c02c3c54abb28d40f8e58f9fe59afb1a6bf01cc74d56ec1213c1d',
    'build/research/eod/multi-pose-analysis/accepted-01/multi-pose-proof.json': 'ca3baca1dd889b3b0e9ef9fe81d5f1f3c89f27c15d7a420f105a19d670f19a11',
    'build/research/eod/multi-pose-analysis/accepted-01/multi_pose.checked.py': '61aa635ccfecff00a44c1d06862305e1387ef2c3faf92e50f30653ef488e8742',
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT/relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def source_memory():
    memory = bytearray(65536)
    for number in (51, 52):
        raw = (BASE/f'file-analysis/accepted-03/EdgeOfDisgrace_1a/trackmo-{number:03}.decoded.prg').read_bytes()
        start = int.from_bytes(raw[:2], 'little')
        memory[start:start+len(raw)-2] = raw[2:]
    return memory


def matrix():
    result = bytearray(1024)
    for row in range(16):
        for column in range(16):
            result[240+40*row+column] = 16*column+row
    return bytes(result)


def cached_span(vbuf):
    matches = [(first, row) for first in range(25) for row in range(16)
               if vbuf[first:first+16] == [16*column+row for column in range(16)]]
    assert len(matches) == 1, matches
    return matches[0]


def compose_row(output, logical_y, palette):
    """Direct four-pair decode, each pair doubled; no VIC shifter replay."""
    assert len(output) == 2048 and 0 <= logical_y < 128 and len(palette) == 4
    return bytes(palette[(output[128*column+logical_y] >> shift) & 3]
                 for column in range(16) for shift in (6,6,4,4,2,2,0,0))


def committed_rectangle(output, setup, middle, complete):
    """Three accepted packets; output is the independent new-pose prediction."""
    assert len(output) == 2048
    packets = (setup, middle, complete)
    for packet in packets:
        ram, state = packet['ram'], packet['state']
        vic = state['vicii']; regs = vic['regs']; cia = state['cia']['CIA2']
        pins = cia['pra'] | (~cia['ddra'] & 255)
        assert ((~pins & 3)*0x4000, regs[0x18]) == (0x4000, 0xbc)
        assert ram[0x6c00:0x7000] == matrix() and ram[0x7000:0x7800] == output
        assert vic['color_ram'] == [9]*1024
        assert regs[0x11] == vic['reg11_delay'] == 0x1b
        assert regs[0x16] & 0x18 == 0x10
        assert regs[0x15] == vic['sprite_dma'] == vic['sprite_display_bits'] == 0
        assert packet['draw']['sprite_pending_bits'] == packet['draw']['sprite_active_bits'] == 0
    sv, mv, ev = [packet['state']['vicii'] for packet in packets]
    assert mv['raster_line'] == 130 and 31 <= mv['raster_cycle'] <= 35
    assert ev['raster_line'] == 220 and 35 <= ev['raster_cycle'] <= 45
    assert sv['raster_line'] < mv['raster_line'] < ev['raster_line']
    for packet, vic in ((middle,mv),(complete,ev)):
        elapsed = packet['registers']['clock']-setup['registers']['clock']
        phase = (vic['raster_line']-sv['raster_line'])*63+vic['raster_cycle']-sv['raster_cycle']
        assert elapsed == phase  # No hidden full-field wrap between the three stops.
    palette = [mv['regs'][0x21]&15,mv['regs'][0x22]&15,mv['regs'][0x23]&15,1]
    fine = mv['regs'][0x16] & 7
    for packet in packets:
        regs = packet['state']['vicii']['regs']
        assert [regs[0x21]&15,regs[0x22]&15,regs[0x23]&15,1] == palette
        assert regs[0x16] & 7 == fine
        assert packet['draw']['cregs'][0x21:0x24] == palette[:3]
    first, row = cached_span(mv['vbuf'])
    assert ((mv['vcbase']+first) & 1023) == 240+40*row
    assert mv['vbuf'] == [matrix()[(mv['vcbase']+index) & 1023] for index in range(40)]
    assert mv['cbuf'] == [9]*40
    assert not mv['idle_state'] and not mv['bad_line']
    assert middle['draw']['xscroll_pipe'] == fine
    assert middle['draw']['vmode11_pipe'] == 0
    assert middle['draw']['vmode16_pipe'] == middle['draw']['vmode16_pipe2'] == 4
    logical_y = 8*row+mv['rc']
    top = mv['raster_line']-logical_y
    left = 32+8*first+fine
    # This rectangle stays strictly inside both ordinary PAL border variants.
    assert 60 <= top and top+128 <= 236 and 40 <= left and left+128 <= 343
    fetch_index = mv['vmli']-1
    assert first <= fetch_index < first+16 and mv['raster_cycle'] < 57
    code = mv['vbuf'][fetch_index]
    fetch_address = 0x7000+8*code+mv['rc']
    fetched = output[fetch_address-0x7000]
    assert fetched == mv['gbuf'] == middle['draw']['gbuf_pipe0']
    assert middle['draw']['vbuf_pipe0'] == code and middle['draw']['cbuf_pipe0'] == 9
    assert fetched != 0  # A nonblank actual byte, not only an all-background latch.
    meta, raster = complete['meta'], complete['raster']
    assert (meta['width'],meta['height'],meta['pitch']) == (384,312,384)
    assert meta['current_line'] == ev['raster_line'] and top+127 < meta['current_line']
    predicted = b''.join(compose_row(output,y,palette) for y in range(128))
    actual = b''.join(raster[line*384+left:line*384+left+128] for line in range(top,top+128))
    assert predicted == actual
    controls = []
    for name, wrong_palette in (('Color_RAM9_instead_of_low_three_bits',palette[:3]+[9]),
                                ('swap_D022_D023',[palette[0],palette[2],palette[1],palette[3]])):
        wrong = b''.join(compose_row(output,y,wrong_palette) for y in range(128))
        differences = sum(a!=b for a,b in zip(wrong,actual))
        assert differences > 0
        controls.append(dict(model=name,different_pixels=differences,rejected=True))
    return dict(rectangle=dict(left=left,top=top,width=128,height=128,pixels=16384),
        cached_anchor=dict(first_vbuf_index=first,character_row=row,RC=mv['rc'],logical_Y=logical_y,
            VCBASE=mv['vcbase'],fine_X=fine),
        actual_fetch=dict(VMli=mv['vmli'],vbuf_index=fetch_index,code=code,address=fetch_address,
            predicted_byte=fetched,gbuf=mv['gbuf'],draw_pipe0_byte=middle['draw']['gbuf_pipe0']),
        palette=palette,all_pixels_equal=True,predicted_sha256=sha(predicted),committed_sha256=sha(actual),
        color_counts={str(color):actual.count(color) for color in sorted(set(actual))},
        commitment=dict(snapshot_current_line=meta['current_line'],last_compared_line=top+127,
                        same_field_clock_phase_equal=True),negative_controls=controls,
        limits=['The source/cached counter anchor and unchanged field write history justify this bounded text rectangle.',
            'Not all glyph fetches are individually latched; one nonblank gbuf byte is directly witnessed.',
            'The complete software input includes independently accepted crop/previous-state conventions; no full312-line or animation acceptance.']), predicted


def write_history(case, original, packets):
    trace = case['display_trace']
    assert trace['no_other_monitor_trace_hits_in_watched_ranges']
    stream_row = next(row for row in case['wire']['files'] if row['path'].endswith('/received.bin'))
    stream_path = ROOT/stream_row['path']
    assert artifact(stream_path) == stream_row
    stream = stream_path.read_bytes()
    def window(ref):
        assert ref['received_stream'] == stream_row['path']
        raw = stream[ref['received_first']:ref['received_end']]
        assert len(raw) == ref['response_bytes'] and sha(raw) == ref['response_sha256']
        return raw.decode()
    ranges = [(0xd000,0xd02e),(0xdd00,0xdd03),(0x6c00,0x6fff),(0x7000,0x77ff),(0xd800,0xdbff)]
    assert [(row['first'],row['last']) for row in trace['arming']] == ranges
    for row in trace['arming']:
        assert row['setup']['command'] == f"trace store {row['first']:04x} {row['last']:04x}"
        assert row['attached_r']['command'] == f'command {row["number"]} "r"'
        assert f'TRACE: {row["number"]}' in window(row['setup'])
        assert f'Setting checkpoint {row["number"]} command to: r' in window(row['attached_r'])
    raw_hits = []
    # The first hit follows monitor prompts on the same line. Deliberately
    # do not anchor this pattern at line start or discard that first store.
    header = re.compile(r'#(\d+) \(Trace store ([0-9a-f]{4})\)\s+(\d+)/\$[0-9a-f]+,\s+(\d+)/\$[0-9a-f]+',re.I)
    for row in trace['raw_windows']:
        text = window(row['response'])
        found = list(header.finditer(text))
        assert len(found) == row['instruction_hits'] == 2
        raw_hits.extend((int(match[1]),int(match[2],16),int(match[3]),int(match[4])) for match in found)
    expected_sources = [(0x16bd,0xd012,'8d12d0'),(0x16c5,0xd019,'ee19d0'),
                        (0x1732,0xd012,'8d12d0'),(0x173a,0xd019,'ee19d0')]
    assert len(trace['observed_instruction_hits']) == trace['instruction_hits'] == len(raw_hits) == 4
    start, end = packets[0]['registers']['clock'], packets[2]['registers']['clock']
    classified = []
    for header_row, hit, (pc,address,opcode) in zip(raw_hits,trace['observed_instruction_hits'],expected_sources):
        regs = hit['attached_post_instruction_registers']
        assert header_row == (hit['checkpoint'],address,regs['line'],regs['cycle'])
        assert (hit['monitor_instruction_PC'],hit['monitored_address'],hit['instruction_hex']) == (pc,address,opcode)
        assert original[pc:pc+3] == bytes.fromhex(opcode)
        assert regs['port00'] == 0x2f and regs['port01'] == 0x35 and start < regs['clock'] < end
        block = stream[hit['received_first']:hit['received_end']]
        assert len(block) == hit['trace_block_bytes'] and sha(block) == hit['trace_block_sha256']
        text = block.decode()
        instruction = re.search(r'\.C:([0-9a-f]+)\s+((?:[0-9a-f]{2}\s+){3})(STA|INC)\s+\$([0-9a-f]{4})',text,re.I)
        assert instruction and (int(instruction[1],16),''.join(instruction[2].split()).lower(),int(instruction[4],16)) == (pc,opcode,address)
        value = regs['a'] if instruction[3].upper() == 'STA' else None
        if address == 0xd012:
            assert value == (0xc0 if pc == 0x16bd else 0xfa)
        classified.append(dict(PC=pc,target=address,instruction=hit['instruction'],store_A=value,
            post_registers=regs,device='VIC I/O under CPU01=$35',
            role='raster IRQ schedule' if address == 0xd012 else 'raster IRQ acknowledge RMW',
            physical_bus_write_count_inferred=False))
    return dict(received_stream=artifact(stream_path),arming=trace['arming'],raw_windows=trace['raw_windows'],
        hits=classified,instruction_hits=4,graphics_mode_bank_matrix_charset_Color_RAM_write_hits=0,
        palette_write_hits=0,unchanged_value_palette_write_hits=0,effective_palette_changes=0,
        source_generation_and_CPU_port_context_guarded=True,
        scope='All four watched store-instruction hits retained, including prompt-prefixed D012 hits. RMW hits do not specify physical bus-write count.')


def new_display(reader, scanout, original):
    case_path = BASE/'output-case-analysis/accepted-01/output-case-proof.json'
    poses_path = BASE/'multi-pose-analysis/accepted-01/multi-pose-proof.json'
    case, poses = json.loads(case_path.read_text()), json.loads(poses_path.read_text())
    assert case['pass_'] and poses['pass_']
    assert case['case_sha256'] == poses['case_sha256'] == 'c52bb838d493b5d6261b1b55f931df74b358136748ceb9f9de201b8ea499540c'
    captures = {row['stem']:row for row in case['captures']}
    baseline = next(row for row in poses['poses'] if row['name'] == 'baseline')
    assert baseline['pass_'] and baseline['registers']['begin'] == captures['baseline-begin']['registers']
    for row in baseline['inputs']:
        assert artifact(ROOT/row['path']) == row
    assert captures['baseline-begin']['ram'] in baseline['inputs']
    assert captures['baseline-filled']['ram'] in baseline['inputs']
    output_row = next(row for row in poses['outputs'] if row['name'] == 'baseline-output-7000.bin')
    output_path = poses_path.parent/output_row['name']
    output = output_path.read_bytes()
    assert len(output) == output_row['bytes'] == 2048 and sha(output) == output_row['sha256']
    assert baseline['comparisons']['filled_output']['all_equal']
    assert sha(output) == baseline['comparisons']['filled_output']['predicted_sha256']
    packets, consumed = [], []
    for stem in ('display-setup','display-mid','display-complete'):
        row = captures[stem]
        for key in ('ram','snapshot'):
            assert artifact(ROOT/row[key]['path']) == row[key]
            consumed.append(row[key])
        state = reader.read_snapshot(ROOT/row['snapshot']['path'])
        draw, meta, raster = scanout.draw_state(reader.module_payload(ROOT/row['snapshot']['path'],'VIC-II'))
        packets.append(dict(ram=(ROOT/row['ram']['path']).read_bytes(),state=state,draw=draw,meta=meta,raster=raster,registers=row['registers']))
    history = write_history(case,original,packets)
    result, predicted = committed_rectangle(output,*packets)
    result.update(accepted_case_proof=artifact(case_path),independent_baseline_proof=artifact(poses_path),
        independent_software_input=artifact(output_path),consumed_capture_inputs=consumed,write_history=history,
        new_baseline_input_compared_without_old_pose_assumption=True)
    return result,predicted


def primary_rules():
    wanted = {
        'src/core/ciacore.c': ['byte = cia_context->c_cia[CIA_PRA] | ~(cia_context->c_cia[CIA_DDRA]);'],
        'src/c64/c64cia2.c': ['tmp = (uint8_t)~byte;', 'new_vbank = tmp & 3;'],
        'src/viciisc/vicii-fetch.c': [
            'return ((vicii.regs[0x18] & 0xf0) << 6) + offset;',
            'a = (vicii.vbuf[vicii.vmli] << 3) | vicii.rc;',
            'a |= (vicii.regs[0x18] & 0xe) << 10;',
            'vicii.cbuf[vicii.vmli] = mem_color_ram_vicii[vicii.vc];',
            'vicii.gbuf = data;', 'vicii.vmli++;'],
        'src/viciisc/vicii-cycle.c': [
            '/* Update RC (Cycle 58 on PAL) */', 'vicii.rc = (vicii.rc + 1) & 0x7;'],
        'src/viciisc/vicii-draw-cycle.c': [
            'mc pixels if MCM=1 and BMM=1, or MCM=1 and cbuf bit 3 = 1',
            'COL_D021, COL_D022, COL_D023, COL_CBUF_MC,',
            'cc = cbuf_reg & 0x07;', 'gbuf_pixel_reg = gbuf_reg >> 6;',
            'if (i == xscroll_pipe)', 'vicii.dbuf[offs + i] = pixel_buffer[i];'],
        'src/viciisc/vicii-draw.c': ['#define DBUF_OFFSET (17 * 8 - vicii.screen_leftborderwidth)'],
        'src/viciisc/vicii-timing.h': ['#define VICII_SCREEN_PAL_NORMAL_LEFTBORDERWIDTH      0x20'],
        'src/viciisc/vicii-timing.c': ['vicii.screen_leftborderwidth = VICII_SCREEN_PAL_NORMAL_LEFTBORDERWIDTH;'],
        'src/viciisc/vicii-snapshot.c': ['SMW_BA(m, vicii.vbuf, VICII_SCREEN_TEXTCOLS)',
            'SMW_BA(m, vicii.cbuf, VICII_SCREEN_TEXTCOLS)', 'SMW_B(m, vicii.gbuf)',
            'vicii_draw_cycle_snapshot_write(m)', 'raster_snapshot_write(m, &vicii.raster)'],
        'src/raster/raster-snapshot.c': ['SMW_DW(m, raster->current_line)',
            'SMW_DW(m, draw_buffer->draw_buffer_pitch)',
            'SMW_BA(m, draw_buffer->draw_buffer_padded_allocations[0], padded_size)'],
        'src/raster/raster.c': ['*padded_size = fb_width * (fb_height + 4);',
            '*unpadded_offset = fb_width * 2;'],
        'src/monitor/mon_lex.l': ['RL\t\t{ yylval.i = e_Rasterline;',
            'CY\t\t{ yylval.i = e_Cycle;'],
    }
    rows = {}
    with tarfile.open(ROOT/'build/research/quondam/hardware-source/vice-3.10.tar.gz',mode='r|gz') as tar:
        for member in tar:
            name = member.name.removeprefix('vice-3.10/')
            if name not in wanted:
                continue
            fragments = wanted[name]
            raw = tar.extractfile(member).read()
            lines = raw.decode().splitlines()
            guards = []
            for fragment in fragments:
                hits = [index+1 for index, line in enumerate(lines) if fragment in line]
                assert hits, (name, fragment)
                guards.append(dict(fragment=fragment, lines=hits))
            rows[name] = dict(member='vice-3.10/'+name, bytes=len(raw), sha256=sha(raw), guards=guards)
    assert set(rows) == set(wanted)
    return [rows[name] for name in wanted]


def retained_states(reader):
    accepted = json.loads((BASE/'frame-analysis/accepted-01/frame-proof.json').read_text())
    assert accepted['pass_']
    captures = {row['stem']: row for row in accepted['captures']}
    result = []
    for stem in ('begin', 'body-complete', 'prefix-before', 'prefix-filled', 'prefix-cleared', 'next-frame'):
        row = captures[stem]
        for key in ('ram', 'snapshot'):
            assert artifact(ROOT/row[key]['path']) == row[key]
        ram = (ROOT/row['ram']['path']).read_bytes()
        state = reader.read_snapshot(ROOT/row['snapshot']['path'])
        vic = state['vicii']; regs = vic['regs']; cia = state['cia']['CIA2']
        port = (cia['pra'] | (~cia['ddra'] & 255))
        bank = (~port & 3)*0x4000
        screen = bank+((regs[0x18] & 0xf0) << 6)
        charset = bank+((regs[0x18] & 14) << 10)
        assert (bank, screen, charset) == (0x4000, 0x6c00, 0x7000)
        assert ram[0x6c00:0x7000] == matrix()
        assert vic['color_ram'] == [9]*1024
        assert not (regs[0x11] & 0x60) and regs[0x11] & 0x10 and regs[0x16] & 0x10
        assert regs[0x15] == vic['sprite_dma'] == vic['sprite_display_bits'] == 0
        item = dict(stem=stem, ram=row['ram'], snapshot=row['snapshot'], beam=[vic['raster_line'],vic['raster_cycle']],
            port_latch=cia['pra'], port_DDR=cia['ddra'], effective_port=port, bank=bank, screen=screen, charset=charset,
            D011=regs[0x11], D016=regs[0x16], D018=regs[0x18], palette_registers=regs[0x20:0x24],
            selector_palette=[regs[0x21]&15,regs[0x22]&15,regs[0x23]&15,1],
            mode='multicolor text; Color RAM9 enables multicolor and selector3 maps to1',
            RC=vic['rc'], VCBASE=vic['vcbase'], VMli=vic['vmli'], gbuf=vic['gbuf'])
        if stem in ('prefix-before','prefix-filled'):
            first, char_row = cached_span(vic['vbuf'])
            assert vic['cbuf'][first:first+16] == [9]*16
            item['cached_lattice'] = dict(first_vbuf_index=first, character_row=char_row,
                codes=vic['vbuf'][first:first+16], colors=vic['cbuf'][first:first+16],
                scope='Matrix/color cache only; RC may already have advanced at PAL58 and these are not all proven glyph fetches.')
        result.append(item)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    out = parser.parse_args().output.resolve()
    out.relative_to((BASE/'display-analysis').resolve())
    assert not out.exists(), 'Choose a fresh output directory'
    for name, expected in PINS.items():
        assert sha((ROOT/name).read_bytes()) == expected, name
    original = source_memory()
    guards = []
    def guard(start, expected, role):
        raw = bytes.fromhex(expected)
        assert original[start:start+len(raw)] == raw, hex(start)
        guards.append(dict(start=start, bytes=expected, role=role))
    guard(0x0f23,'a22ebd2f109d00d0ca10f7','copy original47-byte VIC register template')
    guard(0x0f35,'8d02dd58a200a9099d00d89d00d99d00da9d00dbe8d0f1','CIA2DDR and physical Color RAM initialization')
    guard(0x0fcb,'a900a2009d006c9d006d9d006e9d006fe8d0f1','clear1024screenbytes')
    guard(0x0fde,'a9f08504a96c8505a2008a18a00091046910c8c01090f7','column-major screen lattice first row')
    guard(0x0ff5,'18a504692885049002e605e8e01090e3','screen-lattice pointer advances40 for each of16 rows')
    guard(0x1643,'8d16d0','top IRQ fine-X write')
    guard(0x1667,'a97aa01b8d11d08c11d0','timed transient D011 mode/scroll pulse')
    guard(0x16aa,'8d22d0','top IRQ D022 ramp write')
    guard(0x16b8,'8d23d0','top IRQ D023 ramp write')
    guard(0x174d,'20731a20781a','common prefix then marker clear; no charset-bank swap here')
    template = original[0x102f:0x105e]
    assert len(template) == 47 and template[0x18] == 0xbc and template[0x15] == 0
    byte_offsets = [8*(16*column+row)+rc for column in range(16) for row in range(16) for rc in range(8)]
    assert len(byte_offsets) == len(set(byte_offsets)) == 2048 and set(byte_offsets) == set(range(2048))
    reader = load('eod_display_snapshot', 'research/quondam/snapshot_state.py')
    states = retained_states(reader)
    displayed, indices = new_display(reader,load('eod_display_raster','research/anomaly/scanout.py'),original)
    proof = dict(pass_=True, scope='One original committed128×128 multicolor-text rectangle from the independently predicted new baseline, with actual nonblank fetch and complete watched store history; no full312-line or all-pose claim',
        producer=artifact(Path(__file__)), inputs=[artifact(ROOT/name) for name in PINS], original_guards=guards,
        original_VIC_template=list(template), primary_rules=primary_rules(), states=states,
        matrix=dict(screen=0x6c00,grid_start=0x6cf0,rows=16,columns=16,code='16*column+row',
            char_byte='0x7000+128*column+logical_Y',all_2048_offsets_bijective=True,
            samples_nominal=[64,128],physical_pixels_nominal=[128,128],
            matrix_bytes_checked=1024*len(states),physical_Color_RAM_bytes_checked=1024*len(states)),
        publication=dict(output=0x7000,source_marker=0x7800,
            observation='All retained states select the same active charset; prefix stores directly into that charset. No flip is identified in the inspected common IRQ/shader paths.',
            limit='The new bounded field is coherent and matches actual fetch/output; no whole-animation absence-of-flips or universal publication-latency claim.'),
        committed_display=displayed,
        capture_plan=dict(start='selected pose prefix-filled1750, then next-frame546A',
            setup='first following16BB after top palette/D016 work',
            actual_fetch='line130 raw31..35 beforePAL58; bind VMli−1, cached code/color, RC and actual gbuf',
            committed='same field line220 raw35..45, after complete candidate canvas; derive rectangle from actual middle anchor',
            trace_stores=['D000..D02E','DD00..DD03','6C00..6FFF','7000..77FF','D800..DBFF'],
            target='One bounded128×128 physical-index rectangle if all mode/phase/write/commit guards pass; otherwise retain smaller proven sample.'),
        limits=['Current RAM, cached matrix/color, graphics fetch latches and committed raster pixels are separate evidence.',
            'The original top IRQ changes fineX, transient D011 and ramp colors; final current registers cannot be assumed to describe earlier lines.',
            'Exactly one128×128 rectangle is accepted; border/canvas surroundings, all312rasterlines and other poses remain separate.',
            'No CPU interpreter, new native/emulator/build/process action or product change.'])
    out.mkdir(parents=True)
    outputs = []
    for name,raw in (('matrix-6c00.bin',matrix()),('predicted-display-indices.bin',indices),
                     ('display.checked.py',Path(__file__).read_bytes())):
        (out/name).write_bytes(raw)
        outputs.append(dict(name=name,bytes=len(raw),sha256=sha(raw)))
    proof['outputs'] = outputs
    raw = (json.dumps(proof,indent=2)+'\n').encode()
    (out/'display-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,receipt_bytes=len(raw),receipt_sha256=sha(raw)),indent=2))


if __name__ == '__main__':
    main()
