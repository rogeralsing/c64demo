"""Assemble and cycle-count a retained column-span delta renderer in py65.

The verification boundary is the final 63-byte hardware sprite and its MCI
mirror. Expected pixels come from the independent native baseline trace. This
specifically catches stale bank histories, empty slots, topology switches, and
incorrect ceil/half-open endpoint handling. No production seam is introduced.
"""
from pathlib import Path
import argparse
import hashlib
import json
import re
import statistics
import subprocess

from py65.devices.mpu6502 import MPU

HERE = Path(__file__).resolve().parent
DEFAULT_TRACE = HERE / "delta-trace.json"

ASM = r'''
.label localX=$30
.label localY=$36
.label count=$3c
.label oldPointer=$40
.label outputPointer=$42
.label mirrorPointer=$44
.label sampleBias=$46
.label mask=$47
.label intervalStart=$48
.label intervalEnd=$49
.label column=$4a
.label columnOffset=$4b
.label slotIndex=$4c
.label newTop=$7000
.label newBottom=$7020
*=$2000 "Span generation and delta update"
generate:
    lda count
    beq !empty+
    jmp !active+
!empty:
    lda #0
    .for(var i=0;i<24;i++) { sta newTop+i; sta newBottom+i }
    rts
!active:
    lda #$ff
    .for(var i=0;i<24;i++) { sta newTop+i }
    lda #0
    .for(var i=0;i<24;i++) { sta newBottom+i }
    jsr edge0
    jsr edge1
    jsr edge2
    jsr edge3
    lda count
    cmp #5
    beq !pentagon+
    jsr edge4
    jsr edge5
    jmp normalize
!pentagon:
    jsr pentEdge4
normalize:
    ldx #23
!column:
    lda newTop,x
    cmp #$ff
    bne !present+
    lda #0
    sta newTop,x
!present:
    dex
    bpl !column-
    rts

.macro SpanEdge(a,b) {
    lda localX+a
    cmp localX+b
    bcc !forward+
    bne !reverse+
    rts
!forward:
    OrderedSpan(localX+a,localY+a,localX+b,localY+b)
!reverse:
    OrderedSpan(localX+b,localY+b,localX+a,localY+a)
}
.macro OrderedSpan(startX,startY,endX,endY) {
    lda startY
    sec
    sbc #20
    sta sampleBias
    lda endX
    sec
    sbc startX
    tax
    lda endY
    sec
    sbc startY
    clc
    adc curveIndexBase,x
    tax
    lda curveLow,x
    sec
    sbc startX
    sta sample+1
    lda curveHigh,x
    sbc #0
    sta sample+2
    ldx startX
!pixel:
sample:
    lda $ffff,x
    clc
    adc sampleBias
    cmp newTop,x
    bcs !notTop+
    sta newTop,x
!notTop:
    cmp newBottom,x
    bcc !notBottom+
    sta newBottom,x
!notBottom:
    inx
    cpx endX
    bne !pixel-
    rts
}
edge0: SpanEdge(0,1)
edge1: SpanEdge(1,2)
edge2: SpanEdge(2,3)
edge3: SpanEdge(3,4)
edge4: SpanEdge(4,5)
edge5: SpanEdge(5,0)
pentEdge4: SpanEdge(4,0)

update:
    ldx slotIndex
    lda oldLow,x
    sta oldPointer
    lda oldHigh,x
    sta oldPointer+1
    lda outputLow,x
    sta outputPointer
    sta mirrorPointer
    lda outputHigh,x
    sta outputPointer+1
    clc
    adc #$10
    sta mirrorPointer+1
    ldx #0
!column:
    stx column
    lda bitMasks,x
    sta mask
    lda byteColumns,x
    sta columnOffset
    txa
    tay
    lda (oldPointer),y
    cmp newTop,x
    beq !topSame+
    sta intervalStart
    lda newTop,x
    sta (oldPointer),y
    sta intervalEnd
    jsr toggleInterval
!topSame:
    ldx column
    txa
    clc
    adc #24
    tay
    lda (oldPointer),y
    cmp newBottom,x
    beq !bottomSame+
    sta intervalStart
    lda newBottom,x
    sta (oldPointer),y
    sta intervalEnd
    jsr toggleInterval
!bottomSame:
    ldx column
    inx
    cpx #24
    bne !column-
    rts

// XOR between the two top endpoints, then between the bottom endpoints.
// Disjoint spans may visit an intermediate pixel twice. XOR cancels those
// visits, retaining exact symmetric-difference coverage without a sort of four
// endpoints. Both MCI mirrors receive the same value after every changed bit.
toggleInterval:
    lda intervalStart
    cmp intervalEnd
    bcc !ordered+
    ldx intervalEnd
    sta intervalEnd
    stx intervalStart
!ordered:
    ldx intervalEnd
    lda rowOffsets,x
    clc
    adc columnOffset
    sta intervalEnd
    ldx intervalStart
    lda rowOffsets,x
    clc
    adc columnOffset
    tay
!pixel:
    lda (outputPointer),y
    eor mask
    sta (outputPointer),y
    sta (mirrorPointer),y
    iny
    iny
    iny
    cpy intervalEnd
    bne !pixel-
    rts
codeEnd:
bitMasks: .fill 24,$80 >> (i&7)
byteColumns: .fill 24,floor(i/8)
rowOffsets: .fill 22,i*3
oldLow: .fill 16,<($6000+i*48)
oldHigh: .fill 16,>($6000+i*48)
outputLow: .fill 16,<($4000+floor(i/8)*$400+(i&7)*64)
outputHigh: .fill 16,>($4000+floor(i/8)*$400+(i&7)*64)
curveIndexBase: .byte 0,10,31,52,73,94,115,136,157,178
tablesEnd:
*=$8000 "Exact ceil crossing curve pointers"
curveLow: .import binary "curve-low.bin"
curveHigh: .import binary "curve-high.bin"
*=$a000 "Exact ceil crossing samples"
curveSamples: .import binary "curve-samples.bin"
curvesEnd:
'''


def assemble():
    curves, low, high = bytearray(), bytearray(), bytearray()
    for dx in range(1, 10):
        for dy in range(-10, 11):
            address = 0xa000 + len(curves)
            low.append(address & 255)
            high.append(address >> 8)
            curves.extend(20 - ((-n*dy)//dx) for n in range(dx))
    for name, data in (("low", low), ("high", high), ("samples", curves)):
        (HERE / f"curve-{name}.bin").write_bytes(data)
    (HERE / "span-delta.asm").write_text(ASM)
    subprocess.run(["rtk", "proxy", "kickass", "span-delta.asm", "-o", "span-delta.prg", "-symbolfile"], cwd=HERE, check=True)
    symbols = {name: int(value, 16) for name, value in re.findall(r"\.label ([\w]+)=\$([0-9a-f]+)", (HERE/"span-delta.sym").read_text(), re.I)}
    return symbols


def run(cpu, address):
    cpu.pc = address
    cpu.sp = 0xfd
    cpu.memory[0x1fe] = 0xfe
    cpu.memory[0x1ff] = 0x1f
    start = cpu.processorCycles
    steps = 0
    while cpu.pc != 0x1fff:
        cpu.step()
        steps += 1
        if steps > 100000:
            raise AssertionError(f"Kernel failed to return at {cpu.pc:04x}")
    return cpu.processorCycles-start


def spans(data):
    top, bottom = [0]*24, [0]*24
    for x in range(24):
        ys = [y for y in range(21) if data[y*3+x//8] & (0x80>>(x&7))]
        if ys:
            assert ys == list(range(ys[0],ys[-1]+1)), "Initial sprite is not column-convex"
            top[x], bottom[x] = ys[0], ys[-1]+1
    return top+bottom


def stats(values):
    return {"count":len(values), "min":min(values), "mean":statistics.mean(values), "median":statistics.median(values), "max":max(values), "total":sum(values)}


class CountingMemory(list):
    def __init__(self):
        super().__init__([0]*65536)
        self.sprite_writes = 0

    def __setitem__(self, index, value):
        if isinstance(index, int) and (0x4000 <= index < 0x4600 or 0x5000 <= index < 0x5600):
            self.sprite_writes += 1
        super().__setitem__(index,value)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", type=Path, default=DEFAULT_TRACE)
    parser.add_argument("--profile", type=Path, help="Original clear/draw/fill CPU profile for matching pose indices")
    parser.add_argument("--allow-partial", action="store_true")
    args = parser.parse_args()
    trace = json.loads(args.trace.read_text())
    assert len(trace["frames"]) == 513 or args.allow_partial, "Wait for complete canonical trace"
    symbols = assemble()
    cpu = MPU(memory=CountingMemory())
    program = (HERE/"span-delta.prg").read_bytes()
    load = program[0]+program[1]*256
    cpu.memory[load:load+len(program)-2] = program[2:]
    for bank in range(2):
        initial = trace["initial_buffers"][str(bank)]
        cpu.memory[0x4000+bank*0x400:0x4200+bank*0x400] = initial
        cpu.memory[0x5000+bank*0x400:0x5200+bank*0x400] = initial
        for slot in range(8):
            state = spans(initial[slot*64:slot*64+63])
            address = 0x6000+(bank*8+slot)*48
            cpu.memory[address:address+48] = state
    generation, update, total, by_shape = [], [], [], {0:[], 1:[]}
    exact_bytes, changed_shapes, same_shapes, empty = 0, 0, 0, 0
    frames_report, sprite_writes = [], []
    for frame in trace["frames"]:
        gen_cycles, update_cycles = 0, 0
        cpu.memory.sprite_writes = 0
        for entry in frame["slots"]:
            bank, slot = frame["bank"], entry["slot"]
            index = bank*8+slot
            address = 0x4000+bank*0x400+slot*64
            assert cpu.memory[address:address+63] == entry["old"], (frame["index"],slot,"wrong buffer history")
            vertices = entry["vertices"]
            assert len(vertices) in (0,5,6), (frame["index"],slot,"unsupported vertex count")
            for i,(x,y) in enumerate(vertices):
                nx,ny = vertices[(i+1)%len(vertices)]
                assert 0 <= x < 24 and 0 <= y <= 20
                assert abs(nx-x) <= 9 and abs(ny-y) <= 10
            cpu.memory[0x3c] = len(vertices)
            cpu.memory[0x4c] = index
            for i,(x,y) in enumerate(vertices):
                cpu.memory[0x30+i],cpu.memory[0x36+i] = x,y
            g = run(cpu,symbols["generate"])
            u = run(cpu,symbols["update"])
            gen_cycles += g
            update_cycles += u
            actual = cpu.memory[address:address+63]
            mirror = cpu.memory[address+0x1000:address+0x1000+63]
            assert actual == entry["new"], (frame["index"],slot,"pixel mismatch",actual,entry["new"],vertices)
            assert mirror == actual, (frame["index"],slot,"mirror mismatch")
            state_address = 0x6000+index*48
            assert cpu.memory[state_address:state_address+24] == cpu.memory[0x7000:0x7018], (frame["index"],slot,"top history mismatch")
            assert cpu.memory[state_address+24:state_address+48] == cpu.memory[0x7020:0x7038], (frame["index"],slot,"bottom history mismatch")
            exact_bytes += 126
            changed_shapes += entry["old"] != entry["new"]
            same_shapes += entry["old"] == entry["new"]
            empty += not vertices
        generation.append(gen_cycles)
        update.append(update_cycles)
        total.append(gen_cycles+update_cycles)
        by_shape[frame["shape_mode"]].append(gen_cycles+update_cycles)
        sprite_writes.append(cpu.memory.sprite_writes)
        frames_report.append({"index":frame["index"],"generation_cycles":gen_cycles,"delta_cycles":update_cycles,"total_cycles":gen_cycles+update_cycles})
    report = {
        "strategy":"retained convex column spans with XOR endpoint intervals",
        "status":f"pixels exact for native {len(trace['frames'])}-pose trace",
        "trace":args.trace.name,"trace_sha256":hashlib.sha256(args.trace.read_bytes()).hexdigest(),
        "prototype_sha256":hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "assembled_source_sha256":hashlib.sha256((HERE/"span-delta.asm").read_bytes()).hexdigest(),
        "measurement":"assembled NMOS 6502 kernels executed by py65; CPU cycles exclude VIC DMA and IRQ",
        "generation_cycles_per_pose":stats(generation),"delta_update_cycles_per_pose":stats(update),"combined_cycles_per_pose":stats(total),
        "by_shape_combined":{str(k):stats(v) for k,v in by_shape.items() if v},
        "mirrored_sprite_stores_per_pose":stats(sprite_writes),
        "exact_mirrored_sprite_bytes":exact_bytes,"slot_updates":changed_shapes+same_shapes,
        "changed_shapes":changed_shapes,"unchanged_shapes":same_shapes,"empty_slots":empty,
        "history_bytes":16*48,"scratch_span_bytes":48,"zero_page_temporaries_bytes":13,
        "kernel_code_bytes":symbols["codeEnd"]-0x2000,
        "support_table_bytes":symbols["tablesEnd"]-symbols["codeEnd"],
        "curve_pointer_bytes":378,"curve_sample_bytes":symbols["curvesEnd"]-0xa000,
        "included":"new-span initialization, exact ceil edge generation, normalization, per-slot history/output pointer setup, span comparisons, retained-state writes, both mirrored sprite updates, all 8 slots including empty",
        "limitations":["Not integrated into packed native memory map; requires RAM/code placement work before deployment", "Initialization seeds both bank histories from native trace; a production startup would initialize zero histories before entrance zoom", "Uses convex column coverage, verified for every pose in trace", "Per-slot JSR dispatch by caller adds 12 cycles per slot for two calls if original dispatcher cannot absorb both entry points"],
        "frames":frames_report,
        "reproduce":"rtk proxy python prototype.py --trace delta-trace.json --profile reference-cpu-cycles.json"
    }
    if args.profile:
        profile = json.loads(args.profile.read_text())
        original = {frame["index"]:frame for frame in profile["frames"]}
        matched = [frame for frame in frames_report if frame["index"] in original]
        original_cycles = [sum(original[frame["index"]][key] for key in ("clear_cycles","draw_cycles","fill_cycles")) for frame in matched]
        delta_cycles = [frame["total_cycles"] for frame in matched]
        report["comparison"] = {
            "profile":args.profile.name,"poses":len(matched),
            "original_raster_plus_metadata_cycles":stats(original_cycles),
            "span_generation_and_delta_cycles":stats(delta_cycles),
            "extra_cycles_before_common_metadata":stats([new-old for new,old in zip(delta_cycles,original_cycles)]),
            "mean_cycle_ratio_lower_bound":statistics.mean(delta_cycles)/statistics.mean(original_cycles),
            "qualification":"Conservative loss comparison: original includes drawFace position/color metadata; delta excludes that common work. Caller JSR costs and VIC/IRQ time excluded. This is not a measured integrated frame time."
        }
    (HERE/"report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({k:v for k,v in report.items() if k != "frames"},indent=2))


if __name__ == "__main__":
    main()
