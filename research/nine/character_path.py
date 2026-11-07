#!/usr/bin/env python3
"""Nine's character replacement and handoff, from original relocated code.

No VICE/process control, hardware-read substitution, renderer edits or full
demo execution. Existing SFX/relocation proof is reused, not replayed.
"""
import argparse
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/"build/research/nine"
OUT=BASE/"character-analysis"
INPUT=BASE/"lft-nine.prg"
PRG_SHA="a257fa0436bc0d97fbeaa906c55489786a26ee6a9213aa3fd0d8e21f9612d839"
RAM_SHA="82b6eb9f4b175512ce3f8073d187b7e29f3140a673631bca0658b1b4bfde0a7e"
CELLS=tuple(40*y+x for y in range(3) for x in range(3))


def sha(data):return hashlib.sha256(data).hexdigest()


def execute(ram,start,stops,limit=10000):
    """Original instructions until a named boundary, with explicit RAM inputs.

    Existing Memory records mapped writes separately; any hardware/ROM read
    raises rather than supplying a fabricated raster/register value.
    """
    from inspect_binary import Memory,MPU
    memory=Memory(INPUT.read_bytes(),0)
    memory.data[:]=ram
    memory.known[:]=bytes((1,))*65536
    memory.trace_writes=True
    cpu=MPU(memory=memory,pc=start)
    cpu.sp,cpu.p=0xFD,cpu.UNUSED|cpu.INTERRUPT
    count=0
    while cpu.pc not in stops:
        assert min(start,*stops)<=cpu.pc<=max(start,*stops),hex(cpu.pc)
        assert count<limit,"Bounded instruction limit"
        assert cpu.instruct[memory.data[cpu.pc]].__name__!="inst_not_implemented"
        memory.pc,memory.cycles=cpu.pc,cpu.processorCycles
        cpu.step()
        count+=1
    assert not memory.dependencies
    return memory,dict(stop_pc=cpu.pc,instructions=count,nominal_CPU_cycles=cpu.processorCycles)


def font_conversion(ram):
    result=[]
    for digit in range(9):
        sprite=ram[0x7800+64*digit:0x7800+64*digit+63]
        # Independently reshape 21 rows x3 bytes into row-major3x3 glyphs.
        # Each8-byte glyph is one vertical byte lane; rows21..23 are blank.
        rows=sprite+bytes(9)
        expected=bytes(rows[(tile_y*8+y)*3+tile_x]
                       for tile_y in range(3) for tile_x in range(3) for y in range(8))
        first=0x4178+72*digit
        assert ram[first:first+72]==expected
        base=ram[0xA6E9+digit]
        assert 0x4000+8*base==first
        result.append(dict(digit_index=digit,sprite=0x7800+64*digit,sprite_bytes=63,
                           font=first,font_bytes=72,first_character=base,
                           padding_bottom_rows=3,font_sha256=sha(expected)))
    return result


def fixture(ram,digit,phase):
    data=bytearray(ram)
    data[:2]=bytes((0x2F,0x35))
    data[2:256]=bytes(254)
    data[0x4800:0x4C00]=bytes((0xA5,))*1024
    columns=(0,1,4,7,13,20,27,28)
    rows=(0,1,4,7,13,20,21,22)
    col,row=columns[phase],rows[(phase+digit)%8]
    xs=[32+(i*23+phase*5)%224 for i in range(8)]+[24+8*col+phase]
    ys=[40+(i*17+phase*3)%180 for i in range(8)]+[47+8*row+(phase*3)%8]
    high=[(i+digit+phase)&1 for i in range(9)]
    colors=[(i+digit+phase*2)&15 for i in range(9)]
    pointers=[0xE0+(digit+i+1)%9 for i in range(8)]+[0xE0+digit]
    for a,values in ((0x27,xs),(0x47,ys),(0x50,high),(7,colors),(0x10,pointers)):
        data[a:a+9]=bytes(values)
    data[0x22]=0x0D  # main character branch; no CD/CE/CF producer pending.
    data[0x1D]=(0,19,20,61)[phase%4]
    old=0x4800+40*row+col if phase==0 else (0x4800+40*row+col-1 if phase==1 else
                                         0x4800+40*((row+8)%23)+(col+5)%29)
    data[0x24:0x26]=old.to_bytes(2,"little")
    return data,dict(digit=digit,phase=phase,column=col,row=row,old_screen=old,
                     x=xs,y=ys,high=high,colors=colors,pointers=pointers)


def character_cases(ram):
    result=[]
    for digit in range(9):
        for phase in range(8):
            data,case=fixture(ram,digit,phase)
            expected=bytearray(data)
            screen=0x4800+40*case["row"]+case["column"]
            base=ram[0xA6E9+digit]
            for offset in CELLS:expected[case["old_screen"]+offset]=0
            for index,offset in enumerate(CELLS):expected[screen+offset]=base+index
            expected[0x4BF8:0x4C00]=bytes(case["pointers"][:8])
            expected[0x20]=0
            expected[0x46]=case["column"]
            expected[0x61]=case["y"][8]-47
            expected[0x62]=case["x"][8]&7
            expected[0x24:0x26]=screen.to_bytes(2,"little")
            expected[0x40]=screen&255
            expected[0x41]=(screen>>8)^0x90
            expected[0xCE]=1
            writes=[(0xD001+2*i,case["y"][i]) for i in range(8)]
            writes += [(0xD000+2*i,case["x"][i]) for i in reversed(range(8))]
            writes += [(0xD010,sum(case["high"][i]<<i for i in range(8)))]
            writes += [(0xD027+i,case["colors"][i]) for i in range(8)]
            writes += [(0xD800+screen-0x4800+offset,case["colors"][8]) for offset in CELLS]
            actual,cpu=execute(data,0x92C0,{0x94A1})
            differences=[i for i,(a,b) in enumerate(zip(expected,actual.data)) if a!=b]
            assert not differences,[(hex(i),expected[i],actual.data[i]) for i in differences[:12]]
            assert [(a,v) for pc,a,v in actual.io]==writes
            result.append(dict(digit=digit,phase=phase,screen=screen,old_screen=case["old_screen"],
                               fine_x=expected[0x62],fine_y=expected[0x61]&7,
                               glyph_base=base,color=case["colors"][8],shape_control_1D=data[0x1D],
                               sprite_pointer_writes=8,screen_cell_writes=18,color_RAM_writes=9,
                               all_physical_RAM_matches=True,mapped_IO_sequence_matches=True,**cpu))
    return result


def sprite_cases(ram):
    results=[]
    fixtures=((list(range(9)),[60+17*i for i in range(9)]),
              ([2,0,8,1,7,3,6,4,5],[210-17*i for i in range(9)]),
              ([8,2,6,0,1,7,3,5,4],[90,40,90,60,40,60,90,40,60]))
    for number,(order,ys) in enumerate(fixtures):
        data,case=fixture(ram,number,number)
        data[0x22]|=0x20
        data[3]=5
        data[0x47:0x50]=bytes(ys)
        data[0x77:0x80]=bytes(order)
        expected=bytearray(data)
        ordered=sorted(order,key=lambda n:ys[n])
        expected[0x77:0x80]=bytes(ordered)
        for source,target in ((0x47,0x80),(0x27,0x89),(0x50,0x92),(7,0x9B),(0x10,0xA4)):
            expected[target:target+9]=data[source:source+9]
        expected[0x68]=data[3]
        expected[0xCF]=1
        # Last insertion that moved a new item before any existing prefix item.
        moved=[i for i in range(8) if ys[order[i+1]]<max(ys[n] for n in order[:i+1])]
        if moved:expected[0x92FA]=moved[-1]
        actual,cpu=execute(data,0x92C0,{0x9319})
        assert actual.data==expected and not actual.io
        results.append(dict(case=number,input_order=order,y_values=ys,stable_sorted_order=ordered,
                            all_physical_RAM_matches=True,IO_writes=0,flag_CF=1,**cpu))
    return results


def IRQ_priority(ram):
    results=[]
    for cd,ce,cf,target in ((1,1,1,0x9A09),(0,1,1,0x9A4A),(0,0,1,0x9A96),(0,0,0,0x9AF1)):
        data=bytearray(ram)
        data[:2]=bytes((0x2F,0x35))
        data[0xCD:0xD0]=bytes((cd,ce,cf))
        actual,cpu=execute(data,0x9A05,{target})
        assert actual.data==data and not actual.io
        results.append(dict(flags_CD_CE_CF=[cd,ce,cf],selected_code=target,**cpu))
    return results


def control_switches(ram):
    # These are the authored main-program control writes, not a cycle schedule.
    result=[]
    state=0x3D
    for pc in range(0x8304,0x8875):
        if ram[pc:pc+3]==bytes.fromhex("a5 22 49") and ram[pc+4:pc+6]==bytes.fromhex("85 22"):
            mask=ram[pc+3]
            before,state=state,state^mask
            mode="crunched/ghostbyte producer CD" if not state&4 else ("9-digit sprite producer CF" if state&0x20 else "8sprites+character producer CE")
            result.append(dict(pc=pc,hex=f"${pc:04X}",xor_mask=mask,before=before,after=state,
                               producer_after=mode))
    return result


def native_stamp(directory,ram):
    """Existing natural captures only. This branch executes no CPU model."""
    from native_capture import contexts,physical_ram,read_snapshot
    monitor=(directory/"monitor.log").read_text(errors="replace")
    events={event["filename"]:event for event in contexts(monitor)}
    stems=("before-char-switch","after-char-switch","character-entry",
           "character-before-stamp","character-after-stamp")
    expected_pcs=(0x857F,0x8585,0x931A,0x93F8,0x949F)
    images,states,regs,inputs={}, {}, {}, []
    for stem,pc in zip(stems,expected_pcs):
        raw=directory/f"ram-{stem}.bin"
        snapshot=directory/f"{stem}.vsf"
        event=events[raw.name]
        assert event["command"]=="bsave" and event["bank"]=="ram"
        assert event["first"]==0 and event["end_inclusive"]==65535
        data=raw.read_bytes()
        assert len(data)==65536 and physical_ram(snapshot)==data
        reg=event["registers"]
        assert reg["pc"]==pc and reg["port01"]&7==5
        assert events[snapshot.name]["registers"]==reg
        state=read_snapshot(snapshot)
        assert (state["vicii"]["raster_line"],state["vicii"]["raster_cycle"])==(reg["raster_line"],reg["raster_cycle"])
        images[stem],states[stem],regs[stem]=data,state,reg
        inputs.append(dict(raw=str(raw),raw_sha256=sha(data),snapshot=str(snapshot),
                           snapshot_sha256=sha(snapshot.read_bytes()),RAM_matches=65536,registers=reg))
    before,after=images[stems[0]],images[stems[1]]
    assert before[0x857F:0x8585]==bytes.fromhex("a5 22 49 20 85 22")
    changed=bytearray(before);changed[0x22]^=0x20
    assert changed==after and before[0x22]==0x2C and after[0x22]==0x0C
    assert before[0x3F]==after[0x3F]==12
    assert regs[stems[1]]["clock"]-regs[stems[0]]["clock"]==8
    entry=images["character-entry"]
    assert entry[0x22]==0x0C and entry[0x3F]==11
    before,after=images["character-before-stamp"],images["character-after-stamp"]
    assert before[0x93F8:0x949F]==ram[0x93F8:0x949F]
    assert before[0x4178:0x4400]==ram[0x4178:0x4400] and before[0x4000:0x4008]==bytes(8)
    assert before[0xCD:0xD0]==after[0xCD:0xD0]==bytes(3)
    digit=before[0x18]-0xE0
    assert 0<=digit<9
    base=ram[0xA6E9+digit]
    old=int.from_bytes(before[0x24:0x26],"little")
    screen=0x4800+40*(before[0x61]//8)+before[0x46]
    expected=bytearray(before)
    for offset in CELLS:expected[old+offset]=0
    for index,offset in enumerate(CELLS):expected[screen+offset]=base+index
    expected[0x24:0x26]=screen.to_bytes(2,"little")
    expected[0x40]=screen&255
    expected[0x41]=(screen>>8)^0x90
    differences=[i for i,(a,b) in enumerate(zip(expected,after)) if a!=b]
    assert not differences,differences[:20]
    colors=[s["vicii"]["color_ram"] for s in (states["character-before-stamp"],states["character-after-stamp"])]
    expected_colors=list(colors[0])
    for offset in CELLS:expected_colors[screen-0x4800+offset]=before[0x0F]&15
    assert expected_colors==colors[1]
    before_reg,after_reg=regs["character-before-stamp"],regs["character-after-stamp"]
    assert before_reg["sp"]==after_reg["sp"]
    elapsed=after_reg["clock"]-before_reg["clock"]
    # Keep the consumed transcript prefix stable while root captures later stages.
    end=events["character-after-stamp.vsf"]["transcript_line"]
    prefix="\n".join(monitor.splitlines()[:end])+"\n"
    (OUT/"native-character-transcript.log").write_text(prefix)
    result=dict(pass_=True,program_sha256=PRG_SHA,script_sha256=sha(Path(__file__).read_bytes()),
                existing_native_reader_sha256=sha((ROOT/"research/nine/native_capture.py").read_bytes()),
                inputs=inputs,raw_snapshot_RAM_pairs=5,
                script_switch=dict(before_22=0x2C,after_22=0x0C,other_RAM_unchanged=True,observed_cycles=8,
                                   shape_3F_at_switch=12,shape_3F_first_character_entry=11),
                stamp=dict(old_screen=old,screen=screen,row=before[0x61]//8,column=before[0x46],
                           image_index=digit,character_codes=list(range(base,base+9)),color=before[0x0F]&15,
                           screen_addresses=[screen+offset for offset in CELLS],
                           Color_RAM_addresses=[0xD800+screen-0x4800+offset for offset in CELLS],
                           all_physical_RAM_matches=65536,all_Color_RAM_matches=1024,observed_cycles=elapsed,
                           packet_CE_still_unpublished=True),
                transcript=dict(file=str(OUT/"native-character-transcript.log"),sha256=sha(prefix.encode()),
                                original_file=str(directory/"monitor.log"),prefix_end_line=end),
                scope="One natural authored switch and first original character stamp. Explicit same-stop snapshots; no asynchronous earlier-wait oracle, whole-image match or performance-average claim.")
    result["pass"]=result.pop("pass_")
    (OUT/"character-native-proof.json").write_text(json.dumps(result,indent=2)+"\n")
    print(f"PASS:natural22switch; firstcharacterstamp{screen:04X}; all64KRAM/all1024ColorRAM; {elapsed}observedcycles.")


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture",type=Path,help="Check existing natural character captures; no CPU model execution")
    args=parser.parse_args()
    assert sha(INPUT.read_bytes())==PRG_SHA
    ram=(BASE/"binary/relocated-ram.bin").read_bytes()
    assert len(ram)==65536 and sha(ram)==RAM_SHA
    previous=BASE/"binary/binary-proof.json"
    original_proof=json.loads(previous.read_text())
    assert original_proof["input_sha256"]==PRG_SHA and original_proof["relocation"]["RAM_sha256"]==RAM_SHA
    OUT.mkdir(parents=True,exist_ok=True)
    if args.capture:
        native_stamp(args.capture,ram)
        return
    result=dict(pass_=True,program_sha256=PRG_SHA,relocated_RAM_sha256=RAM_SHA,
                reused_binary_proof_sha256=sha(previous.read_bytes()),
                script_sha256=sha(Path(__file__).read_bytes()),
                original_memory_mapper_sha256=sha((ROOT/"research/nine/inspect_binary.py").read_bytes()),
                font_conversion=font_conversion(ram),character_cases=character_cases(ram),
                sprite_handoff_cases=sprite_cases(ram),IRQ_priority_cases=IRQ_priority(ram),
                authored_control_switches=control_switches(ram),
                character_publisher=dict(entry=0x931A,before_glyph_write=0x9439,publish_CE=0x949F,return_=0x94A1),
                consumer=dict(IRQ_dispatch=0x9A05,character_setup=0x9A4A,character_split_IRQ=0x9CBA,
                              character_acknowledge=0x9CF4,sprite_mux=0x9D00,wide_mux=0x9E00),
                scope="Original released RAM-only CPU slices and independent glyph/placement/order references. Explicit fixtures; no full demo chronology timing, raster/ROM-read substitution, VIC/VICE or visual proof.")
    result["pass"]=result.pop("pass_")
    path=OUT/"character-proof.json"
    path.write_text(json.dumps(result,indent=2)+"\n")
    print(f"PASS:9sprite/font conversions; {len(result['character_cases'])} character placements;3sprite handoffs;4IRQ priorities.")


if __name__=="__main__":main()
