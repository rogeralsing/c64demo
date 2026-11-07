#!/usr/bin/env python3
"""Prepare/check existing A Mind Is Born captures; no emulator/process control.

Without --capture this emits only the original-program checkpoint map. With
captures it calls the existing pure music_reference function, not its Cpu class
or arithmetic proof runner. Use the established cpu-venv for that model import.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys

REPO=Path(__file__).resolve().parents[2]
BASE=REPO/"build/research/a-mind-is-born"
OUTPUT=BASE/"native-analysis"
PRG_SHA="7da29c8eed5acc39c5a1d3f0d40f5057c516cb6d2a04a18b15d71e6f8903f1f5"
REGISTERS=re.compile(r"^\.;([0-9a-f]{4})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+"
    r"([0-9a-f]{2})\s+([0-9a-f]{2})\s+([0-9a-f]{2})\s+([01]{8})\s+(\d+)\s+(\d+)\s+(\d+)",re.I)

sys.path.insert(0,str(REPO/"research/quondam"))
from snapshot_state import module_payload, read_snapshot  # noqa: E402


def sha(data):return hashlib.sha256(data).hexdigest()


def program():
    data=(BASE/"a_mind_is_born.prg").read_bytes()
    assert len(data)==256 and sha(data)==PRG_SHA
    return data


def checkpoint_map():
    blob=program()
    locations=[("SYS/shared NOP",0x08B1,"loaded",1),
               ("startup SEI",0x08B2,"loaded",1),("KERNAL screen clear call",0x08B9,"loaded",3),
               ("copy preparation",0x08BC,"loaded",2),("copy loop",0x08BE,"loaded",3),
               ("relocation jump",0x08C9,"loaded",3),
               ("first relocated instruction",0x00CC,"relocated",2),
               ("main CLI",0x00D1,"relocated",1),("main loop",0x00D2,"relocated",3),
               ("font stack write",0x00DA,"relocated",1),("VIC memory select",0x00DF,"relocated",3),
               ("IRQ entry after ROM prologue",0x0031,"relocated",4),
               ("end blanking RMW",0x0045,"relocated",3),("software reset-vector jump",0x0048,"relocated",3),
               ("IRQ tail jump",0x00AF,"relocated",3)]
    rows=[]
    for name,address,kind,count in locations:
        offset=address-0x0801+2 if kind=="loaded" else address+1
        rows.append({"name":name,"address":address,"hex":f"${address:04X}","kind":kind,
                     "original_bytes_hex":blob[offset:offset+count].hex(" ")})
    return {"program_sha256":PRG_SHA,"file_bytes":256,"payload_bytes":254,
        "loaded_interval_inclusive":[0x0801,0x08FE],"basic_SYS_decimal":2225,
        "basic_next_line_word":int.from_bytes(blob[2:4],"little"),"checkpoints":rows,
        "external_ROM_entries":{"clear_screen":0xE544,"normal_IRQ_tail":0xEA7E,"reset_vector":0xFFFC},
        "copied_loaded_source_interval_inclusive":[0x0803,0x08FE],
        "copied_loaded_destination_interval_inclusive":[3,0xFE],"copied_loaded_bytes":252,
        "extra_unloaded_source":0x08FF,"extra_destination":0xFF,
        "native_checks_run":False}


def capture_registers(text):
    current=None
    result={}
    for line in text.splitlines():
        line=line.strip()
        if line=="x":current=None
        match=REGISTERS.match(line)
        if match:
            f=match.groups()
            current=dict(zip(("pc","a","x","y","sp","port00","port01"),(int(x,16) for x in f[:7])))
            current.update(flags=int(f[7],2),raster_line=int(f[8]),raster_cycle=int(f[9]),stopwatch=int(f[10]))
        match=re.match(r'(?:bsave|dump|screenshot) "([^"]+)"',line)
        if match:
            result[Path(match[1]).name]=dict(current) if current is not None else None
    return result


def check_relocation(data):
    blob=program()
    assert len(data)==65536
    assert data[0x0801:0x08FF]==blob[2:],"Loaded payload differs before the main loop"
    assert data[3:255]==blob[4:],"252-byte relocation differs"
    assert data[255]==data[0x08FF],"Extra source byte08FF did not reachFF"
    assert data[0x0314:0x0316]==bytes((0x31,0)),"Inherited IRQ-low31/high0 contract differs"
    return {"pass":True,"loaded_payload_bytes_compared":254,"relocated_loaded_bytes_compared":252,
            "unloaded_byte_08FF_copied_to_FF":data[255],"IRQ_vector":0x0031,
            "initial_video_pointer":int.from_bytes(data[0xCB:0xCD],"little"),
            "scope":"At PC00CC before first instruction/CLI; no whole visual replay"}


def arithmetic_model():
    path=REPO/"research/a-mind-is-born/validate_arithmetic.py"
    receipt=json.loads((BASE/"arithmetic-proof.json").read_text())
    assert receipt["pass"] and receipt["script_sha256"]==sha(path.read_bytes())
    spec=importlib.util.spec_from_file_location("mind_original_arithmetic",path)
    model=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(model)
    return model,path


def check_irq_transition(before,after):
    """One nonterminal0031→EA7E body, with captured live inputs and no main loop."""
    assert len(before)==len(after)==65536
    blob=program()
    assert before[0x31:0xB2]==blob[0x32:0xB3],"Native IRQ body differs from original"
    assert before[3:5]==bytes((0xFF,0xD3)) and before[0x0F:0x11]==bytes((0x1C,0xD0))
    assert before[0x0D]==0x19,"The final VIC-loop load must select25 SID stores"
    model,path=arithmetic_model()
    expected=bytearray(before)
    result=model.music_reference(expected)
    if result is None:
        raise ValueError("Reset branch needs captured VIC RMW input/ROM vector; this check covers normal IRQs")
    bar,note,script,writes=result
    differences=[i for i,(a,b) in enumerate(zip(expected,after)) if a!=b]
    assert not differences,[(f"{i:04x}",expected[i],after[i]) for i in differences[:20]]
    changes=[{"address":i,"before":a,"after":b} for i,(a,b) in enumerate(zip(before,after)) if a!=b]
    assert all(row["address"]<256 for row in changes)
    return {"pass":True,"all_physical_RAM_bytes_compared":65536,"bar":bar,"note_index":note,
            "script_write":list(script) if script else None,"zero_page_changes":changes,
            "expected_final_A_X":after[0x0A],"expected_final_Y":0,
            "literal_expected_VIC_and_SID_writes":[{"address":a,"value":b} for a,b in writes],
            "literal_write_count":len(writes),"model_file":str(path.relative_to(REPO)),
            "model_sha256":sha(path.read_bytes()),
            "scope":"Captured normal IRQ body only; no SID readback/sound or asynchronous main-loop oracle"}


def check_snapshot_RAM(path,raw):
    """Official C64MEM0.1 writer: four port/cart bytes, physical RAM,15 suffix bytes."""
    state=read_snapshot(path)
    metadata=state["modules"]["C64MEM"]
    assert metadata["version"]==[0,1] and metadata["payload_size"]==65555
    payload=module_payload(path,"C64MEM")
    assert payload[4:65540]==raw,"Physical RAM differs between same-stop VSF and raw dump"
    return {"snapshot":str(path),"snapshot_sha256":sha(path.read_bytes()),
            "module_version":metadata["version"],"module_payload_sha256":metadata["payload_sha256"],
            "physical_RAM_payload_offset":4,"RAM_bytes_compared":65536,"RAM_mismatches":0,
            "RAM_sha256":sha(raw),
            "schema_source":"VICE3.10 src/c64/c64memsnapshot.c:180-197,216-230",
            "schema_source_sha256":"12058072799a1b0c8d46df7d978a8051bf4d6ef5e7fb26921ac82cd94ed2e149"}


def check_terminal(root,registers,log):
    before=(root/"ram-terminal-before.bin").read_bytes()
    after=(root/"ram-terminal-after.bin").read_bytes()
    assert len(before)==len(after)==65536 and before==after
    assert before[0x45:0x4B]==bytes.fromhex("4e 11 d0 6c fc ff")
    snapshots=[read_snapshot(root/f"terminal-{phase}.vsf") for phase in ("before","after")]
    regs=[registers[f"terminal-{phase}.vsf"] for phase in ("before","after")]
    assert [r["pc"] for r in regs]==[0x45,0x48]
    assert regs[1]["stopwatch"]-regs[0]["stopwatch"]==6
    assert all(regs[0][k]==regs[1][k] for k in ("a","x","y","sp","port00","port01"))
    vic_before,vic_after=[s["vicii"] for s in snapshots]
    assert all(r["port01"]&7==7 for r in regs)
    assert all((v["raster_line"],v["raster_cycle"])==(r["raster_line"],r["raster_cycle"])
               for v,r in zip((vic_before,vic_after),regs))
    read=(vic_before["regs"][0x11]&0x7F)|((vic_before["raster_line"]&0x100)>>1)
    shifted=read>>1
    assert vic_after["regs"][0x11]==shifted and not shifted&0x10
    expected_flags=(regs[0]["flags"]&~0x83)|(read&1)|(2 if shifted==0 else 0)|(shifted&0x80)
    assert regs[1]["flags"]==expected_flags
    reads=[int(x,16) for x in re.findall(r"^>C:d011\s+([0-9a-f]{2})",log,re.M|re.I)]
    post_read=(vic_after["regs"][0x11]&0x7F)|((vic_after["raster_line"]&0x100)>>1)
    assert reads==[read,post_read],"Observed VIC reads must include the captured raster ninth bit"
    word=re.findall(r"^>C:fffc\s+([0-9a-f]{2})\s+([0-9a-f]{2})",log,re.M|re.I)
    assert len(word)==1
    target=int(word[0][0],16)|(int(word[0][1],16)<<8)
    entry=registers["reset-vector-entry.vsf"]
    assert entry["pc"]==target and entry["stopwatch"]-regs[1]["stopwatch"]==5
    assert all(entry[k]==regs[1][k] for k in ("a","x","y","sp","flags"))
    ready=registers["reset-ready.vsf"]
    assert ready["pc"]==0xE5CD and "commodore 64 basic v2" in log.lower() and "ready." in log.lower()
    assert before[0x13]==0 and before[0x20]==0x40
    return {"pass":True,"original_terminal_bytes":before[0x45:0x4B].hex(" "),
            "clock_low_at_13":before[0x13],"bar_high_at_20":before[0x20],"clock_word":0x4000,
            "instruction_registers":regs,"LSR_observed_cycles":6,
            "VIC_stored_before":vic_before["regs"][0x11],"VIC_read_before":read,
            "VIC_stored_after":shifted,"VIC_read_after":post_read,"DEN_cleared":True,
            "all_physical_RAM_bytes_unchanged":65536,
            "same_stop_snapshot_RAM":[check_snapshot_RAM(root/f"terminal-{phase}.vsf",data)
                                      for phase,data in zip(("before","after"),(before,after))],
            "CPU_view_reset_vector":target,"reset_vector_entry":entry,"JMP_observed_cycles":5,
            "BASIC_READY_entry":ready,"READY_screen_observed":True,
            "snapshot_and_output_hashes":[{"file":str(root/name),"sha256":sha((root/name).read_bytes())}
                                         for name in ("reset-vector-entry.vsf","reset-ready.vsf","reset-ready.png")],
            "intervention":"Warp enabled only to skip wall-clock wait after visual0512; disabled at0045 before terminal proof steps",
            "scope":"Observed original mapped-I/O LSR and software JMP through captured ROM vector to later BASIC READY; no RESET-pin/audio/full-program oracle"}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture",type=Path)
    args=parser.parse_args()
    OUTPUT.mkdir(parents=True,exist_ok=True)
    mapping=checkpoint_map()
    (OUTPUT/"checkpoint-map.json").write_text(json.dumps(mapping,indent=2)+"\n")
    if args.capture is None:
        print("Prepared checkpoint-map.json; no native captures checked.")
        return
    root=args.capture
    log=(root/"monitor.log").read_text(errors="replace")
    registers=capture_registers(log)
    names=["ram-after-relocation.bin","ram-before-irq.bin","ram-after-irq.bin"]
    values=[(root/name).read_bytes() for name in names]
    snapshots=[check_snapshot_RAM(root/name.removeprefix("ram-").replace(".bin",".vsf"),data)
               for name,data in zip(names,values)]
    regs=[registers[name] for name in names]
    assert all(r is not None for r in regs),"Issue monitor r before each proof RAM dump"
    assert [r["pc"] for r in regs]==[0x00CC,0x0031,0xEA7E]
    assert all(r["flags"]&4 for r in regs),"Proof boundaries must precede CLI or lie inside IRQ"
    assert all(r["port01"]&7==7 for r in regs),"Expected normal I/O/KERNAL banking"
    relocation=check_relocation(values[0])
    irq=check_irq_transition(values[1],values[2])
    assert regs[1]["sp"]==regs[2]["sp"],"IRQ body should not change stack pointer"
    assert (regs[2]["a"],regs[2]["x"],regs[2]["y"])==(irq["expected_final_A_X"],irq["expected_final_A_X"],0)
    visuals=[]
    for label in ("0128","0512"):
        name=f"ram-visual-{label}.bin"
        if not (root/name).exists():
            continue
        snapshot=root/f"visual-{label}.vsf"
        png=root/f"visual-{label}.png"
        state=read_snapshot(snapshot)
        vic,cia=state["vicii"],state["cia"]["CIA1"]
        assert registers[name]["pc"]==0x0031
        visuals.append({"label":label,"registers":registers[name],
                        "same_stop_snapshot_RAM":check_snapshot_RAM(snapshot,(root/name).read_bytes()),
                        "png":str(png),"png_sha256":sha(png.read_bytes()),
                        "stored_D011":vic["regs"][0x11],"stored_D018":vic["regs"][0x18],
                        "Color_RAM_low_nibbles":sorted(set(x&15 for x in vic["color_ram"])),
                        "first1000_Color_RAM_low_nibbles":sorted(set(x&15 for x in vic["color_ram"][:1000])),
                        "CIA1_timer_A_latch":cia["timer_a_latch"],
                        "CIA1_CRA":cia["cra"],"CIA1_ICR_mask":cia["icr_mask"],
                        "scope":"Output observation; no asynchronous whole-image or SID-audio oracle"})
    terminal=check_terminal(root,registers,log) if (root/"ram-terminal-before.bin").exists() else None
    session=json.loads((root/"session.json").read_text())
    result={"pass":True,"program_sha256":PRG_SHA,"relocation":relocation,"normal_IRQ":irq,
            "capture_registers":dict(zip(names,regs)),
            "IRQ_body_observed_cycles":regs[2]["stopwatch"]-regs[1]["stopwatch"],
            "same_stop_snapshot_RAM":snapshots,
            "visual_observations":visuals,
            "terminal_lifecycle":terminal,
            "session_closed_utc":session.get("closed_utc"),"VICE_exit_code":session.get("exit_code"),
            "inputs":[{"file":str(root/name),"sha256":sha((root/name).read_bytes())} for name in names+["monitor.log"]],
            "script_sha256":sha(Path(__file__).read_bytes()),
            "scope":"Original relocation, one captured normal IRQ transition, output observations and bounded terminal lifecycle; no whole-image, sound or complete-program oracle"}
    (OUTPUT/"native-evidence.json").write_text(json.dumps(result,indent=2)+"\n")
    count=len(snapshots)+len(visuals)+(len(terminal["same_stop_snapshot_RAM"]) if terminal else 0)
    print(f"PASS:254 loaded bytes,252 relocated loaded bytes, one normal IRQ all-RAM transition; {count} exact RAM/VSF pairs; terminal={bool(terminal)}.")


if __name__=="__main__":main()
