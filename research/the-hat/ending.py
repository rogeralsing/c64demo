#!/usr/bin/env python3
"""Passive code/data mapping of the self-contained original Hat B17 payload."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import zlib

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'build/research/the-hat'
PAYLOAD=BASE/'dali-analysis/accepted-03/b17-2000.bin'
PAYLOAD_SHA='fb41ff61943ba509b4cae952b50f48643006550633a0a181603565834aecaa72'
PINS = {
    'build/research/the-hat/dali-analysis/accepted-03/dali-proof.json': '1687a5b2323ec86881b53b226a5361ac88c6408720498cfd34cf7032b3ad940e',
    'research/the-hat/dali.py': '7195f31a85f0dcac032c10b53a6cefcd48d2832d4edf14da0c331dfcf7412ee0',
    'build/research/the-hat/disk-analysis/accepted-02/disk-proof.json': 'a23fa100137fe60f929af25b6596584089cd93cacd891fe02e7ebc85d47635a3',
    'build/research/the-hat/disk-analysis/accepted-02/raw-b/017-71f3.prg': '633e45dac1c3a1a8255c014b25baecae7482285b9cd663d2d418d579d7e75891',
}
ROWS=(
    'BRK.imp ORA.indx KIL.imp SLO.indx NOP.zp ORA.zp ASL.zp SLO.zp PHP.imp ORA.imm ASL.acc ANC.imm NOP.abs ORA.abs ASL.abs SLO.abs',
    'BPL.rel ORA.indy KIL.imp SLO.indy NOP.zpx ORA.zpx ASL.zpx SLO.zpx CLC.imp ORA.absy NOP.imp SLO.absy NOP.absx ORA.absx ASL.absx SLO.absx',
    'JSR.abs AND.indx KIL.imp RLA.indx BIT.zp AND.zp ROL.zp RLA.zp PLP.imp AND.imm ROL.acc ANC.imm BIT.abs AND.abs ROL.abs RLA.abs',
    'BMI.rel AND.indy KIL.imp RLA.indy NOP.zpx AND.zpx ROL.zpx RLA.zpx SEC.imp AND.absy NOP.imp RLA.absy NOP.absx AND.absx ROL.absx RLA.absx',
    'RTI.imp EOR.indx KIL.imp SRE.indx NOP.zp EOR.zp LSR.zp SRE.zp PHA.imp EOR.imm LSR.acc ALR.imm JMP.abs EOR.abs LSR.abs SRE.abs',
    'BVC.rel EOR.indy KIL.imp SRE.indy NOP.zpx EOR.zpx LSR.zpx SRE.zpx CLI.imp EOR.absy NOP.imp SRE.absy NOP.absx EOR.absx LSR.absx SRE.absx',
    'RTS.imp ADC.indx KIL.imp RRA.indx NOP.zp ADC.zp ROR.zp RRA.zp PLA.imp ADC.imm ROR.acc ARR.imm JMP.ind ADC.abs ROR.abs RRA.abs',
    'BVS.rel ADC.indy KIL.imp RRA.indy NOP.zpx ADC.zpx ROR.zpx RRA.zpx SEI.imp ADC.absy NOP.imp RRA.absy NOP.absx ADC.absx ROR.absx RRA.absx',
    'NOP.imm STA.indx NOP.imm SAX.indx STY.zp STA.zp STX.zp SAX.zp DEY.imp NOP.imm TXA.imp XAA.imm STY.abs STA.abs STX.abs SAX.abs',
    'BCC.rel STA.indy KIL.imp AHX.indy STY.zpx STA.zpx STX.zpy SAX.zpy TYA.imp STA.absy TXS.imp TAS.absy SHY.absx STA.absx SHX.absy AHX.absy',
    'LDY.imm LDA.indx LDX.imm LAX.indx LDY.zp LDA.zp LDX.zp LAX.zp TAY.imp LDA.imm TAX.imp LAX.imm LDY.abs LDA.abs LDX.abs LAX.abs',
    'BCS.rel LDA.indy KIL.imp LAX.indy LDY.zpx LDA.zpx LDX.zpy LAX.zpy CLV.imp LDA.absy TSX.imp LAS.absy LDY.absx LDA.absx LDX.absy LAX.absy',
    'CPY.imm CMP.indx NOP.imm DCP.indx CPY.zp CMP.zp DEC.zp DCP.zp INY.imp CMP.imm DEX.imp AXS.imm CPY.abs CMP.abs DEC.abs DCP.abs',
    'BNE.rel CMP.indy KIL.imp DCP.indy NOP.zpx CMP.zpx DEC.zpx DCP.zpx CLD.imp CMP.absy NOP.imp DCP.absy NOP.absx CMP.absx DEC.absx DCP.absx',
    'CPX.imm SBC.indx NOP.imm ISC.indx CPX.zp SBC.zp INC.zp ISC.zp INX.imp SBC.imm NOP.imp SBC.imm CPX.abs SBC.abs INC.abs ISC.abs',
    'BEQ.rel SBC.indy KIL.imp ISC.indy NOP.zpx SBC.zpx INC.zpx ISC.zpx SED.imp SBC.absy NOP.imp ISC.absy NOP.absx SBC.absx INC.absx ISC.absx',
)
OPCODES=[cell.split('.') for row in ROWS for cell in row.split()]
WIDTH={'imp':1,'acc':1,'imm':2,'zp':2,'zpx':2,'zpy':2,'indx':2,'indy':2,'rel':2,'abs':3,'absx':3,'absy':3,'ind':3}
assert len(OPCODES)==256


def sha(raw):return hashlib.sha256(raw).hexdigest()


def artifact(path):
    raw = path.read_bytes()
    return dict(path=str(path.relative_to(ROOT)), bytes=len(raw), sha256=sha(raw))


def memory():
    raw=PAYLOAD.read_bytes()
    assert len(raw)==26402 and sha(raw)==PAYLOAD_SHA
    result=bytearray(65536)
    result[0x2000:0x2000+len(raw)]=raw
    return result


def instruction(m,pc):
    name,mode=OPCODES[m[pc]]
    size=WIDTH[mode]
    raw=bytes(m[pc:pc+size])
    operand=int.from_bytes(raw[1:],'little') if size>1 else None
    target=(pc+2+(operand if operand<128 else operand-256)) & 65535 if mode=='rel' else operand
    return dict(pc=pc,opcode=m[pc],mnemonic=name,mode=mode,bytes=raw.hex(),size=size,operand=operand,target=target)


def listing(m,start,end):
    rows=[];pc=start
    while pc<end:
        row=instruction(m,pc);rows.append(row);pc+=row['size']
    assert pc==end,(hex(pc),hex(end))
    return rows


def source_selection(phase, index, direction, previous, blank, speed=4):
    """Typed semantics of $3231..$3367; no CPU state or instruction decoder."""
    if direction:
        phase = (phase + speed) & 255
        if phase >= 48:
            phase = (phase - 48) & 255
            index = (index - 1) & 255
            if index & 128:
                index, direction = 0, 0
    else:
        phase = (phase - speed) & 255
        if phase & 128:
            phase = (phase + 48) & 255
            index = (index + 1) & 255
            if index >= 118:
                index, direction = 117, 1
    selected, xpos, high = list(previous), [127]*8, 255
    coordinate, column, slot = (0xffb8 + phase) & 65535, index, 0
    while True:
        assert 0 <= column < 128
        if not blank[column]:
            selected[slot] = column
            xpos[slot] = coordinate & 255
            high &= 255 ^ (1 << slot)
            if coordinate >> 8:
                high |= 1 << slot
            slot += 1
        coordinate = (coordinate + 48) & 65535
        upper, lower = coordinate >> 8, coordinate & 255
        if not upper & 128 and (upper > 1 or (upper == 1 and lower > 128)):
            break
        column += 1
        if slot == 8:
            break
    render_selected = list(selected)
    for slot in range(2):
        if high & (1 << slot) and xpos[slot] & 128:
            xpos[slot] = (xpos[slot] - 8) & 255
    return dict(phase=phase, index=index, direction=direction, selected=selected,
                render_selected=render_selected, xlow=xpos, xhigh_mask=high)


def reference_selection(phase, index, direction, previous, blank, speed=4):
    """Signed arithmetic and direct coordinate enumeration, not byte recurrence."""
    if direction:
        phase += speed
        if phase >= 48:
            phase -= 48
            index -= 1
        if index < 0:
            index, direction = 0, 0
    else:
        phase -= speed
        if phase < 0:
            phase += 48
            index += 1
        if index >= 118:
            index, direction = 117, 1
    candidates = [(column, -72 + phase + 48*(column-index))
                  for column in range(index, 128)
                  if -72 + phase + 48*(column-index) <= 384 and not blank[column]][:8]
    selected, xpos, mask = list(previous), [127]*8, 255
    for slot, (column, coordinate) in enumerate(candidates):
        selected[slot] = column
        upper = coordinate < 0 or coordinate >= 256
        if not upper:
            mask &= 255 ^ (1 << slot)
        low = coordinate & 255
        if slot < 2 and upper and low >= 128:
            low = (low - 8) & 255
        xpos[slot] = low
    return dict(phase=phase, index=index, direction=direction, selected=selected,
                render_selected=list(selected), xlow=xpos, xhigh_mask=mask)


def selection_domain(m):
    blank = list(m[0x336c:0x33ec])
    assert len(blank) == 128 and set(blank) == {0,1}
    digest = hashlib.sha256()
    cases, preservation, examples = 0, 0, []
    for previous in ([0]*8, [5,17,42,67,91,114,1,22]):
        for direction in range(2):
            for index in range(118):
                for phase in range(48):
                    actual = source_selection(phase,index,direction,previous,blank)
                    expected = reference_selection(phase,index,direction,previous,blank)
                    assert actual == expected, (phase,index,direction)
                    assert 0 <= actual['phase'] < 48 and 0 <= actual['index'] < 118
                    digest.update(json.dumps([phase,index,direction,previous,actual],sort_keys=True,separators=(',',':')).encode()+b'\n')
                    cases += 1
                    preservation += any(value == previous[slot] for slot,value in enumerate(actual['selected']))
                    if phase == 0 and index in (0,117) and previous == [0]*8:
                        examples.append(dict(phase=phase,index=index,direction=direction,result=actual))
    assert cases == 22656
    return dict(input_domain=dict(phase=[0,47],index=[0,117],direction=[0,1],speed=4,
                    previous_patterns=[[0]*8,[5,17,42,67,91,114,1,22]]),
                comparisons=cases,all_equal=True,canonical_comparison_sha256=digest.hexdigest(),
                edge_examples=examples,
                limit='Finite typed-source versus independent signed-coordinate calculation; no native helper return or VIC sprite positioning is proved.')


def write_png(path,width,height,pixels):
    def chunk(name,data):
        return struct.pack('>I',len(data))+name+data+struct.pack('>I',zlib.crc32(name+data)&0xffffffff)
    scan = b''.join(b'\0'+pixels[row*width:(row+1)*width] for row in range(height))
    path.write_bytes(b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width,height,8,0,0,0,0))+
                     chunk(b'IDAT',zlib.compress(scan))+chunk(b'IEND',b''))


def prepared_assets(m,out):
    pointers = [m[0x3600+128*band+column] for band in range(13) for column in range(128)]
    used = sorted(set(pointers))
    assert used == list(range(0x30,0xcb))
    sprite_images = [bytes(m[0x4000+64*pointer:0x4000+64*pointer+63]) for pointer in used]
    assert len(set(sprite_images)) == len(used) == 155
    assert sprite_images[0] == bytes(63)
    blank = []
    for column in range(128):
        empty = all(not any(m[0x4000+64*m[0x3600+128*band+column]:
                             0x4000+64*m[0x3600+128*band+column]+63]) for band in range(13))
        blank.append(int(empty))
    assert bytes(blank) == m[0x336c:0x33ec]
    width, height = 128*12, 13*21
    selectors = bytearray(width*height)
    for column in range(128):
        for band in range(13):
            address = 0x4000+64*m[0x3600+128*band+column]
            for row in range(21):
                for byte in range(3):
                    value = m[address+3*row+byte]
                    for pair in range(4):
                        selectors[(21*band+row)*width+12*column+4*byte+pair] = (value >> (6-2*pair)) & 3
    mask = b''.join(bytes((255 if value else 0,))*4 for value in selectors)
    write_png(out/'prepared-nonzero-mask.png',width*4,height,mask)
    (out/'prepared-selectors.bin').write_bytes(selectors)
    return dict(pointer_tables=dict(start=0x3600,bytes=13*128,bands=13,column_slots=128,
                SHA256=sha(bytes(pointers))),unique_sprite_images=155,
                sprite_ids=[0x30,0xca],sprite_data=[0x4c00,0x72c0],sprite_bytes_per_slot=64,
                significant_bytes_per_sprite=63,all_used_images_unique=True,
                blank_flags=dict(start=0x336c,bytes=128,all_equal_independent_pixel_emptiness=True,
                    blank_columns=sum(blank),nonblank_columns=128-sum(blank)),
                prepared_selector_dimensions=[width,height],expanded_mask_dimensions=[width*4,height],
                selector_counts={str(code):selectors.count(code) for code in range(4)},
                selector_sha256=sha(selectors),
                meaning='Prepared13-band sprite-image atlas. PNG is binary nonzero-selector opacity, not a native screenshot or current palette rendering.',
                limit='Prepared273-row geometry does not establish actual displayed height, all-border coverage, source cycle scheduling or visible pixels.')


def source_facts(m):
    guards=[]
    def guard(address,hexadecimal,role):
        raw=bytes.fromhex(hexadecimal)
        assert m[address:address+len(raw)] == raw, hex(address)
        guards.append(dict(address=address,bytes=hexadecimal,role=role))
    guard(0x8000,'a9f9cd12d0d0fba9008df6018df70178','Controller waits249 and clears the frame counter')
    guard(0x8010,'a9368dfeffa9818dffff','Install initialIRQ8136')
    guard(0x803a,'204b8020d202ad4a80f0fb4c0008','Initialize, load next resource, wait completion and hand off0800')
    guard(0x80fd,'a9ff8d1cd0a9ff8d1dd0','Multicolor and X expansion on all eight sprites')
    guard(0x812b,'a9078d16d0a9018d488060','Initializer return8135')
    guard(0x81d6,'a9008d15d0a9108d18d0a9028d00dda91a8d11d0','Frame setup selects screen/palette mode and bank pins')
    guard(0x8211,'a9ff8d15d0a9108d18d0a9028d00dd','Active sprite-frame setup')
    guard(0x82ed,'adcc818d12d0adcd814aa9006a8d0183','Program ending rasterIRQ from81CC/81CD')
    guard(0x8305,'ba8e1a83a91b8dfeffa9838dffffee19d0584c0020','Save SP, arm831B, acknowledge/enableIRQ, jump2000')
    guard(0x831b,'ae1a839aa9008d15d0','EndingIRQ discards body stack and disables sprites')
    guard(0x322d,'4c2d3260','Terminal raster-body self-loop and following RTS')
    guard(0x3231,'adfe34f02c','Horizontal window helper entry')
    guard(0x3343,'ad13352901f00bad0b35100638e9088d0b35','First wrapped sprite X correction')
    guard(0x3355,'ad13352902f00bad0c35100638e9088d0c3560','Second wrapped sprite X correction and return')
    assert m[0x4100:0x4108] == bytes((255,))*8
    assert m[0x43f8:0x4400] == bytes(8)
    assert m[0x4400:0x47e8] == m[0x4800:0x4be8]
    screens=[]
    for start in (0x4400,0x4800):
        lines=[]
        for row in range(25):
            raw=m[start+40*row:start+40*(row+1)]
            text=''.join(chr(value+64) if 1 <= value <= 26 else chr(value) if 32 <= value <= 63 else '.' for value in raw)
            if any(value not in (0x20,0x7f) for value in raw):
                lines.append(dict(row=row,text=text))
        screens.append(dict(start=start,bytes=1000,sha256=sha(m[start:start+1000]),nonblank_lines=lines))
    return dict(guards=guards,controller=0x8000,initializer=[0x804b,0x8136],raster_body=[0x2000,0x3230],
        position_helper=[0x3231,0x3368],initial_end_raster=0x10f,
        callback_targets=[0x019f,0x01a0],callback_contract_not_assumed=True,
        screens=screens,glyph_space_sha256=sha(m[0x4100:0x4108]),glyph7f_sha256=sha(m[0x43f8:0x4400]),
        palette_scope='Initializer assigns background/border0E and all sprite palettes0E;85C1 later changes the three multicolor selector palettes from separate tables. No permanent mask-only or physical color claim.',
        mode_scope='Literal source stores select D0111A, D01607, D01810/20 and CIA2PRA02; effective VICbank and per-line output require actual DDR, timed writes and native state.')


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True)
    out=p.parse_args().output.resolve();out.relative_to((BASE/'ending-analysis').resolve());assert not out.exists()
    for name,expected in PINS.items():
        assert sha((ROOT/name).read_bytes()) == expected, name
    dali=json.loads((BASE/'dali-analysis/accepted-03/dali-proof.json').read_text())
    assert dali['pass']
    m=memory()
    facts=source_facts(m)
    domain=selection_domain(m)
    rows=listing(m,0x2000,0x3368)
    out.mkdir(parents=True)
    (out/'code-2000-3368.json').write_text(json.dumps(rows,indent=2)+'\n')
    (out/'code-2000-3368.txt').write_text(''.join(f"{row['pc']:04X} {bytes.fromhex(row['bytes']).hex(' '):9} {row['mnemonic']} {row['mode']} {'' if row['target'] is None else f'$'+format(row['target'],'04X')}\n" for row in rows))
    assets=prepared_assets(m,out)
    body=[row for row in rows if row['pc'] < 0x3231]
    hardware=Counter((row['mnemonic'],row['operand']) for row in body
        if row['operand'] is not None and row['mode'] in ('abs','absx','absy') and 0xd000 <= row['operand'] <= 0xdfff)
    yvalues=[]
    accumulator=None
    for row in body:
        if row['mnemonic']=='LDA':
            accumulator=row['operand'] if row['mode']=='imm' else None
        if row['mnemonic']=='JSR':
            accumulator=None
        if row['mnemonic']=='STA' and row['operand']==0xd001:
            assert accumulator is not None
            yvalues.append(dict(PC=row['pc'],value=accumulator))
    assert [row['value'] for row in yvalues]==[40,61,82,103,124,145,166,187,208,229,250,15,36]
    assert all((b['value']-a['value']) & 255 == 21 for a,b in zip(yvalues,yvalues[1:]))
    checked=Path(__file__).read_bytes()
    (out/'ending.checked.py').write_bytes(checked)
    outputs=[dict(name=str(path.relative_to(out)),bytes=path.stat().st_size,sha256=sha(path.read_bytes()))
             for path in sorted(out.rglob('*')) if path.is_file()]
    proof=dict(pass_=True,scope='Original B17 prepared sprite atlas, source controller/raster structure and finite typed horizontal-window arithmetic; no native pixel or named-ending identification',
        producer=artifact(Path(__file__)),inputs=[artifact(PAYLOAD)]+[artifact(ROOT/name) for name in PINS],
        source=facts,prepared_assets=assets,selection_domain=domain,
        raster_source=dict(instructions=len(body),hardware_instruction_counts=[dict(mnemonic=op,address=address,count=count) for (op,address),count in sorted(hardware.items())],
            sprite0_Y_store_values=yvalues,spacing_mod256=21,
            note='These are source instruction/site counts, not executed bus writes, rasterline timestamps or native cycle budgets.'),
        retained_diagnostic_scope='Earlier diagnostic01 linear listing intentionally extended into data3368..3513; it remains provisional and is not accepted as executable-code reachability.',
        outputs=outputs,
        limits=['The whole B17decoded image comes from the separately accepted strict Dali source/data decode. This producer does not decode the packed stream again.',
            'Static code labels and declared function semantics are checked against original bytes; no CPU interpreter or execution trace is synthesized.',
            'Prepared nonzero-selector PNG is an asset diagram, not an actual native framebuffer or palette/sprite/character compositor result.',
            'EndIRQ stack reset, D016/D011 timing and native DMA must be observed before proving all-border display coverage or complete output.',
            'The literalTHEHATasset and closing-resource position do not by themselves identify the requested specificupscroller or its full mechanism.',
            'No native/process/build action, downloaded host code execution, network, product or shared-index edit occurs.'])
    raw=(json.dumps(proof,indent=2)+'\n').encode()
    (out/'ending-proof.json').write_bytes(raw)
    print(json.dumps(dict(pass_=True,receipt_bytes=len(raw),receipt_sha256=sha(raw),sprite_images=155,selection_cases=22656),indent=2))


if __name__=='__main__':main()
