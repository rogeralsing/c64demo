#!/usr/bin/env python3
"""Read VICE 3.10 C64SC VSF state without running VICE or another CPU.

Schema: official vice-3.10.tar.gz SHA256
8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1.
Sources: src/snapshot.{c,h}; src/viciisc/vicii-snapshot.c (VIC-II1.3),
viciitypes.h; src/core/ciacore.c +ciatimer.c (CIA2.5).

read_snapshot(path) returns JSON-serializable header/modules/vicii/cia dicts.
module_payload(path,name) returns the exact raw module payload bytes separately.
"""
import argparse
import hashlib
import json
from pathlib import Path

SOURCE_ARCHIVE_SHA256 = "8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1"
SCHEMA_SOURCE = {"release":"VICE3.10", "archive_sha256":SOURCE_ARCHIVE_SHA256,
                 "vicii_writer":"vice-3.10/src/viciisc/vicii-snapshot.c:83-147",
                 "cia_writer":"vice-3.10/src/core/ciacore.c:2248-2341"}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def split_modules(data):
    if data[:19] != b"VICE Snapshot File\x1a" or tuple(data[19:21]) != (2,0):
        raise ValueError("Expected VICE snapshot header2.0")
    if data[37:50] != b"VICE Version\x1a":
        raise ValueError("Missing VICE version/revision header")
    header = {"snapshot_version":list(data[19:21]),
              "machine":data[21:37].split(b"\0",1)[0].decode("ascii"),
              "emulator_version":list(data[50:54]),
              "svn_revision":int.from_bytes(data[54:58],"little"), "first_module_offset":58}
    modules = {}
    cursor = 58
    while cursor < len(data):
        if cursor+22 > len(data):
            raise ValueError("Truncated snapshot module header")
        name = data[cursor:cursor+16].split(b"\0",1)[0].decode("ascii")
        size = int.from_bytes(data[cursor+18:cursor+22],"little")
        if not name or size<22 or cursor+size>len(data) or name in modules:
            raise ValueError(f"Invalid/duplicate module at {cursor}: {name!r}/{size}")
        modules[name] = {"version":list(data[cursor+16:cursor+18]),
                         "offset":cursor, "size":size, "payload_offset":cursor+22,
                         "payload_size":size-22, "module_sha256":sha(data[cursor:cursor+size]),
                         "payload_sha256":sha(data[cursor+22:cursor+size])}
        cursor += size
    return header, modules


class Fields:
    def __init__(self, data):
        self.data, self.offset, self.values, self.layout = data, 0, {}, {}

    def take(self, name, size, array=False):
        start = self.offset
        self.offset += size
        if self.offset > len(self.data):
            raise ValueError(f"Truncated module field {name}")
        raw = self.data[start:self.offset]
        value = list(raw) if array else int.from_bytes(raw,"little")
        self.layout[name] = {"payload_offset":start, "bytes":size}
        self.values[name] = value
        return value


def decode_vicii(payload, version):
    if version != [1,3]:
        raise ValueError(f"VIC-II schema {version} unsupported; expected1.3")
    f = Fields(payload)
    for name,size,array in [
        ("model",1,False),("regs",64,True),("raster_cycle",4,False),("cycle_flags",4,False),
        ("raster_line",4,False),("start_of_frame",1,False),("irq_status",1,False),
        ("raster_irq_line",4,False),("raster_irq_triggered",1,False),
        ("vbuf",40,True),("cbuf",40,True),("gbuf",1,False),("dbuf_offset",4,False),
        ("dbuf",65*8,True),("ysmooth",4,False),("allow_bad_lines",1,False),
        ("sprite_sprite_collisions",1,False),("sprite_background_collisions",1,False),
        ("clear_collisions",1,False),("idle_state",4,False),("vcbase",4,False),
        ("vc",4,False),("rc",4,False),("vmli",4,False),("bad_line",4,False),
        ("light_pen_state",1,False),("light_pen_triggered",1,False),
        ("light_pen_x",4,False),("light_pen_y",4,False),("light_pen_x_extra_bits",4,False),
        ("light_pen_trigger_cycle",8,False),("reg11_delay",1,False),("prefetch_cycles",4,False),
        ("sprite_display_bits",4,False),("sprite_dma",1,False),
        ("last_color_reg",1,False),("last_color_value",1,False),("last_read_phi1",1,False),
        ("last_bus_phi2",1,False),("vborder",1,False),("set_vborder",1,False),
        ("main_border",1,False),("refresh_counter",1,False),("color_ram",1024,True)]:
        f.take(name,size,array)
    sprites=[]
    for index in range(8):
        sprites.append({name:f.take(f"sprite{index}_{name}",size) for name,size in
                        [("data",4),("mc",1),("mcbase",1),("pointer",1),("exp_flop",1),("x",4)]})
    # Draw-cycle/raster state follows the fixed1881-byte VIC core. Preserve its
    # exact hash; this reader intentionally does not guess those nested schemas.
    assert f.offset == 1881 and f.layout["vbuf"]["payload_offset"] == 84
    assert f.layout["cbuf"]["payload_offset"] == 124
    values = f.values
    values.update(sprites=sprites, core_bytes_parsed=f.offset,
                  opaque_draw_raster_tail_bytes=len(payload)-f.offset,
                  opaque_draw_raster_tail_sha256=sha(payload[f.offset:]),
                  vbuf_sha256=sha(bytes(values["vbuf"])), cbuf_sha256=sha(bytes(values["cbuf"])),
                  field_layout=f.layout, raster_cycle_numbering="zero-based; PAL hardware-cycle comments add1")
    return values


def decode_cia(payload, version):
    if version != [2,5]:
        raise ValueError(f"CIA schema {version} unsupported; expected2.5")
    f = Fields(payload)
    for name,size,array in [
        ("pra",1,False),("prb",1,False),("ddra",1,False),("ddrb",1,False),
        ("timer_a",2,False),("timer_b",2,False),("tod_tenths",1,False),("tod_seconds",1,False),
        ("tod_minutes",1,False),("tod_hours",1,False),("sdr",1,False),("icr_mask",1,False),
        ("cra",1,False),("crb",1,False),("timer_a_latch",2,False),("timer_b_latch",2,False),
        ("icr_pending",1,False),("timer_flags",1,False),("sr_bits",1,False),("tod_alarm",4,True),
        ("read_icr_age",1,False),("tod_flags",1,False),("tod_latch",4,True),
        ("relative_tod_alarm_cycles",8,False),("timer_a_state",2,False),("timer_b_state",2,False),
        ("shifter_low",1,False),("sdr_valid",1,False),("irq_enabled",1,False),
        ("tod_tickcounter",1,False),("shifter_high",1,False),("sdr_alarm",1,False),
        ("sp_cnt_input",1,False),("sdr_delay",4,False),("sp_cnt_output",1,False),("ifr_delay",4,False),
        # SMW_DB writes native double bytes. Retain raw bytes without assuming
        # producer endianness/IEEE details to interpret these unrelated fields.
        ("ack_irqflags_double_raw",8,True),("new_irqflags_double_raw",8,True)]:
        f.take(name,size,array)
    assert f.offset == len(payload) == 77
    assert f.layout["relative_tod_alarm_cycles"] == {"payload_offset":33,"bytes":8}
    f.values.update(tod_latched=bool(f.values["tod_flags"]&1),
                    tod_stopped=bool(f.values["tod_flags"]&2),field_layout=f.layout)
    return f.values


def read_snapshot(path):
    """Return serializable header, module hashes, VIC1.3 and CIA2.5 fields."""
    path=Path(path)
    data=path.read_bytes()
    header, modules=split_modules(data)
    if header["machine"] != "C64SC" or header["emulator_version"][:3] != [3,10,0]:
        raise ValueError("This audited schema is restricted to C64SC snapshots produced by VICE3.10.0")
    result={"file":str(path),"file_bytes":len(data),"file_sha256":sha(data),
            "header":header,"modules":modules,"schema_source":SCHEMA_SOURCE}
    for name,metadata in modules.items():
        start=metadata["payload_offset"]
        payload=data[start:start+metadata["payload_size"]]
        if name=="VIC-II":result["vicii"]=decode_vicii(payload,metadata["version"])
        elif name in ("CIA1","CIA2"):
            result.setdefault("cia",{})[name]=decode_cia(payload,metadata["version"])
    return result


def module_payload(path,name):
    """Return exact raw payload bytes, separately from serializable state."""
    data=Path(path).read_bytes()
    _,modules=split_modules(data)
    m=modules[name]
    return data[m["payload_offset"]:m["payload_offset"]+m["payload_size"]]


def compare_modules(first,second):
    """Report every payload difference; no field or module is excluded."""
    a,b=read_snapshot(first),read_snapshot(second)
    result=[]
    for name in sorted(set(a["modules"])|set(b["modules"])):
        if name not in a["modules"] or name not in b["modules"]:
            result.append({"module":name,"missing_from_one_file":True});continue
        aa,bb=module_payload(first,name),module_payload(second,name)
        differences=[{"payload_offset":i,"first":x,"second":y} for i,(x,y) in enumerate(zip(aa,bb)) if x!=y]
        if differences or len(aa)!=len(bb) or a["modules"][name]["version"]!=b["modules"][name]["version"]:
            result.append({"module":name,"first_version":a["modules"][name]["version"],
                           "second_version":b["modules"][name]["version"],
                           "first_payload_bytes":len(aa),"second_payload_bytes":len(bb),"differences":differences})
    return {"first":str(first),"second":str(second),"different_modules":result,
            "all_module_payloads_equal":not result,"exclusions":[]}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshots",type=Path,nargs="+")
    parser.add_argument("--output",type=Path)
    args=parser.parse_args()
    result={"snapshots":[read_snapshot(p) for p in args.snapshots]}
    if len(args.snapshots)==2:result["comparison"]=compare_modules(*args.snapshots)
    text=json.dumps(result,indent=2)+"\n"
    if args.output:args.output.write_text(text)
    else:print(text,end="")


if __name__=="__main__":main()
