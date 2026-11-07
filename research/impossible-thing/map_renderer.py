#!/usr/bin/env python3
"""Map conditional decoded renderer bytes; run only two RAM-only setup spans."""
import importlib.util
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/impossible-thing'
spec=importlib.util.spec_from_file_location('impossible_boot',Path(__file__).with_name('inspect_boot.py'))
boot=importlib.util.module_from_spec(spec);spec.loader.exec_module(boot)
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler


def main():
    output=BASE/'renderer';output.mkdir(parents=True,exist_ok=True)
    proof_path=BASE/'binary/boot-proof.json';proof=json.loads(proof_path.read_text())
    source_path=BASE/'binary/conditional-unpacked.ram';mask_path=BASE/'binary/conditional-known-mask.bin'
    memory=bytearray(source_path.read_bytes());known=bytearray(mask_path.read_bytes())
    first,end=proof['conditional_decoder']['output_first'],proof['conditional_decoder']['output_end_exclusive']
    assert boot.sha(memory[first:end])==proof['conditional_decoder']['output_sha256']
    original=bytes(memory)
    # These spans stop before/after the literal Color RAM loop. Neither
    # executes that loop, IRQ delivery or the display-enable sequence.
    _,tables=boot.execute(memory,known,0x205a,0x2099,io_visible=True)
    assert tables['boundary'] is None
    _,generation=boot.execute(memory,known,0x20b2,0x21ec,io_visible=True)
    assert generation['boundary'] is None
    texture=bytes(v&3 for v in original[0x2755:0x2855])
    for shift,start in [(0,0x3e00),(2,0x3c00),(4,0x3a00),(6,0x3800)]:
        assert memory[start:start+512]==bytes(v<<shift for v in texture)*2
    # Independent structure: each copied 57-byte template gets eight output
    # addresses, one per glyph row. Final kernel's last INY becomes RTS.
    template=original[0x21ed:0x2226];assert len(template)==57 and template[-1]==0xc8
    fields=[(9,0),(12,1),(23,2),(26,3),(37,4),(40,5),(51,6),(54,7)]
    banks=[]
    for code_start,charset in [(0x4000,0xe000),(0x7900,0xe800)]:
        expected=bytearray()
        for glyph in range(256):
            cell=bytearray(template)
            for offset,row in fields:
                assert cell[offset-1]==0x8d
                cell[offset:offset+2]=(charset+8*glyph+row).to_bytes(2,'little')
            expected.extend(cell)
        expected[-1]=0x60
        actual=memory[code_start:code_start+len(expected)]
        assert actual==expected
        banks.append(dict(first=code_start,end_exclusive=code_start+len(expected),bytes=len(expected),
            glyphs=256,bytes_per_glyph=57,charset_first=charset,charset_end_exclusive=charset+2048,
            literal_output_addresses=2048,full_bytes_exact=True,sha256=boot.sha(actual)))
    screen_template=original[0x2606:0x260c]
    assert screen_template==bytes.fromhex('8a 69 40 91 08 c8')
    assert memory[0x2606:0x26f6]==screen_template*40
    assert memory[0x2701:0x270e]==bytes.fromhex('a6 0a e8 86 0a e0 19 b0 03 4c 00 26 60')
    # Only direct instructions from explicit roots are followed. This graph
    # ends at indirect/generated/external code; it is not a runtime trace.
    dis=Disassembler(MPU(memory=list(original)));todo=[0x2000,0x2033];seen={};edges=[]
    branch={0x10,0x30,0x50,0x70,0x90,0xb0,0xd0,0xf0}
    while todo:
        pc=todo.pop()
        if pc in seen or not 0x2000<=pc<0x2920:continue
        op=original[pc];length,text=dis.instruction_at(pc);seen[pc]=(length,text)
        if text=='???' or op in (0,0x40,0x60):continue
        if op in (0x20,0x4c,0x6c):
            target=int.from_bytes(original[pc+1:pc+3],'little')
            edges.append(dict(pc=pc,kind='JSR' if op==0x20 else 'JMP' if op==0x4c else 'indirect',target=target))
            if op!=0x6c:todo.append(target)
            if op!=0x20:continue
        if op in branch:
            delta=original[pc+1] if original[pc+1]<128 else original[pc+1]-256
            todo.append((pc+2+delta)&65535)
        todo.append(pc+length)
    listing=output/'direct-instructions.txt'
    listing.write_text('\n'.join(f'{pc:04X} {original[pc:pc+n].hex(" "):9} {text}' for pc,(n,text) in sorted(seen.items()))+'\n')
    bank_listing=output/'one-generated-glyph.txt';pc=0x4000;rows=[];dis=Disassembler(MPU(memory=list(memory)))
    while pc<0x4039:
        length,text=dis.instruction_at(pc);rows.append(f'{pc:04X} {memory[pc:pc+length].hex(" "):9} {text}');pc+=length
    bank_listing.write_text('\n'.join(rows)+'\n')
    (output/'prepared-conditional.ram').write_bytes(memory)
    report=dict(script=boot.record(Path(__file__)),boot_helper=boot.record(Path(__file__).with_name('inspect_boot.py')),
        conditional_boot_receipt=boot.record(proof_path),conditional_source=boot.record(source_path),
        inherited_preconditions=proof['conditional_decoder']['preconditions'],table_preparation=tables,
        code_generation=generation,texture=dict(first=0x2755,end_exclusive=0x2855,bytes=256,
            two_bit_values=sorted(set(texture)),sha256=boot.sha(texture)),
        generated_glyph_banks=banks,generated_total_bytes=sum(b['bytes'] for b in banks),
        generated_screen_loop=dict(template=[0x2606,0x260c],copies=40,
            repeated_copy_first=0x260c,repeated_copy_end_exclusive=0x26f6,
            scope='Original 6-byte template repeated 39 times after the existing first copy. Runtime execution not measured.'),
        static_nominal_lower_bound=dict(glyph_reads=16,glyph_absolute_stores=8,
            ordinary_glyph_cycles=114,glyph_bank_cycles=256*114+4,
            screen_rows=25,screen_columns=40,screen_cell_cycles=12,screen_cells_cycles=12000,
            one_charset_and_screen_image_cycles=41188,two_halves_per_28BD_call_cycles=82376,
            two_standard_PAL_frames_cycles=39312,
            scope='Static instruction lower bound only, conditional on decoded code. Excludes setup, row overhead, indirect-index page crossings, VIC stalls and IRQs. Not a measured native refresh rate.'),
        direct_edges=sorted(edges,key=lambda item:item['pc']),instruction_listing=boot.record(listing),
        generated_glyph_listing=boot.record(bank_listing),prepared_image=boot.record(output/'prepared-conditional.ram'),
        scope='Conditional decoded bytes and two isolated RAM-only setup spans. No native match, frame timing, rendered image, generated renderer execution or complete affine-transform proof.',pass_=True)
    report['pass']=report.pop('pass_');path=output/'renderer-map.json';path.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(receipt=str(path.relative_to(ROOT)),sha256=boot.sha(path.read_bytes()),
                         generated_bytes=report['generated_total_bytes'],banks=banks),indent=2))


if __name__=='__main__':main()
