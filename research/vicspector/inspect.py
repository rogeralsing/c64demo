#!/usr/bin/env python3
"""Passive source/table checks; never executes Vicspector, VICE, or downloaded JS.

Run from any directory. Retained inputs are required; output is confined to
build/research/vicspector/. This is a bounded timing-model audit, not an emulator.
"""
import hashlib
import html
import importlib.util
import json
from pathlib import Path
import re
import sys
import tarfile
from collections import deque

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "build/research/vicspector"
UP = OUT / "upstream"
COMMIT = "c972f7a0a965d28096cc1396cab01fded307d818"
ARCHIVE = ROOT / "build/research/quondam/hardware-source/vice-3.10.tar.gz"
PINS = {
    "README.md": "fb7d27bd3e4495c0fcdc6120afa99f97621cf37b976e0a30dac2a2202b8a60d6",
    "index.html": "46ce401e161ea13583f179cb83c7eca2ac86f367c3799533f10fc76b98289fc7",
    "LICENSE": "b06869ac0369bf327ee6ef60157f43edadfb64b70f11979269fc7361002061dd",
    "commit.json": "37f62ded432595fd11bccaab87d7cc53f8e8d103d0517f3b2cfa42e9a05b2be3",
    "misc-tech.html": "0c246e0fe48e37f71952cc3d56da052dc7a05b5cc34b0b2a9761c66bdb8f21b7",
    "vic-timing.html": "cee4af890ee00d94d5bc38cfb45af401006741f6f06010d6bf69d7da27fc1315",
}
VICE_PINS = {
    "vicii-chip-model.c": "95ea3ef61e59a1c850ff516c1a827ae849521dce3199307586e061af97db639d",
    "vicii-cycle.c": "561876187fde8bfe8636e64593543aa77a5e0855ebbd9fe56d9da4fa6eb564ba",
    "vicii-mem.c": "f8e2bdd30fbe8abf60a7e77647723f4615834e5b414f2695698ed28b31857edf",
    "viciitypes.h": "c6178cc2e026dcd85640a3ab4b9cd6609713731560e0bbbe4b1a7d8764588493",
    "vicii-fetch.c": "83fe621bfd6c3f9aadfe7c725f02392ba04db70c36248cdfea88d79883bb21d0",
}
SNAP_PINS = {
    "native-02/cell62-preclear.vsf": "bc71aca6d02a424b5463c9c2ac93c196e2778c85d5016b43ed6ce65e2dd46801",
    "native-02/cell62-postclear.vsf": "95c82aa0ef867718172abdbc95a6db557457b4cbf688bd8e131e8148f96f5f86",
    "native-02/cell63-preclear.vsf": "ab6b5b6ce6fd794984618e155fb4470f4e0b6bee03d42cae495a7ed14111b2e9",
    "native-02/cell63-postclear.vsf": "7f276ece54fb820edd714fc2f4e68c167eccc4419cf4b1d50f33014c2502861e",
    "native-02/cell64-preclear.vsf": "15f9dfa4339aea776fbdc778ef3d762c27e247357e10108639205e1cd091d7e8",
    "native-02/cell64-postclear.vsf": "6968c0684eebb7e1a4cd4656e081088b6a762cbe890ad6f15d1eb24b7f9a140f",
    "native-03/pointer0-preclear.vsf": "8c0ff7e5d461319bf8e512e9d1e6b81230efab6db71eba47edb6a61bb47b3951",
    "native-03/pointer0-postclear.vsf": "0437db0430ff51c0746bd1ac073069e444e12a5abd3979e241a718bfd392661b",
    "native-03/mature64-preclear.vsf": "f21ee149acd4a5cfbddd1562f9bc72f3326b0a1dbeb8138151b27988152b9714",
    "native-03/mature64-postclear.vsf": "45c19fa24d1a03ac916daf6f50b5c794d6257a93f926fe80ae69c2d3ad450a32",
    "native-03/mature65-preclear.vsf": "edc203e2ef78f133b92d5b1b87dfe19322eee7071242ef9ac784e4a8c450ca58",
    "native-03/mature65-postclear.vsf": "95183989e683b83b3b5f0e10b9a65b6533a00072af82b60933a922536aa06dce",
    "native-03/mature66-preclear.vsf": "1cd60ea77b425a674bd1f3f4a4eb3422302869ee19912186cd0982e07d8f22d9",
    "native-03/mature66-postclear.vsf": "f4d2a5d61bea0b90f19065021bae7099bd770d237afc622d7e89a1b13797ff06",
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def record(path, expected=None):
    data = path.read_bytes()
    if expected:
        assert sha(data) == expected, f"Input drift: {path}"
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data), "sha256": sha(data)}


def source_inputs():
    records = [record(UP / name, pin) for name, pin in PINS.items()]
    assert json.loads((UP / "commit.json").read_text())["sha"] == COMMIT
    records.append(record(ARCHIVE, "8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1"))
    sources = {}
    with tarfile.open(ARCHIVE) as archive:
        for name, pin in VICE_PINS.items():
            member = f"vice-3.10/src/viciisc/{name}"
            data = archive.extractfile(member).read()
            assert sha(data) == pin
            sources[name] = data.decode()
            records.append({"archive_member": member, "bytes": len(data), "sha256": pin})
    bauer = ROOT / "build/research/quondam/hardware-source/Bauer-VIC-Article.txt"
    records.append(record(bauer, "ed558b2480638b153d0ead4726b8b675e4a0b945f2ab4d37c17a3d892cf00828"))
    return records, sources


def parse_pal(source):
    """Parse a fixed C initializer as data, without preprocessing/evaluation."""
    text = source.split("static const struct ViciiCycle cycle_tab_pal[] = {", 1)[1].split("\n};", 1)[0]
    pattern = re.compile(
        r"\{ Phi([12])\((\d+)\),\s+(0x[0-9a-f]+),\s+(?:Vis\(\d+\)|None),\s+"
        r"(Spr(?:Ptr|Dma[012])\(\d\)|Refresh|Fetch[GC]|Idle|None),\s+"
        r"(BaSpr[123]\([0-7](?:,\s*[0-7])*\)|BaFetch|None),\s+([^}]+)\}")
    rows = {}
    for phase, cycle, x, fetch, ba, flags in pattern.findall(text):
        key = (int(cycle), int(phase))
        rows[key] = dict(x=int(x, 16), fetch=fetch, ba=ba, flags=flags.strip())
    assert len(rows) == 126 and set(rows) == {(c, p) for c in range(1, 64) for p in (1, 2)}
    return rows


def ba_from_vice(row, mask, badline):
    label = row["ba"]
    if label == "None":
        return False
    if label == "BaFetch":
        return badline
    return any(mask & (1 << int(i)) for i in re.findall(r"\d", label.split("(")[1]))


def vicspector_line(mask, badline):
    """Human translation of the pinned JS ranges, never JS execution."""
    ba = {c: badline and 12 <= c <= 54 for c in range(1, 64)}
    for sprite in range(8):
        if mask & (1 << sprite):
            p = 58 + 2 * sprite if sprite < 3 else 1 + 2 * (sprite - 3)
            for delta in range(-3, 2):
                ba[(p + delta - 1) % 63 + 1] = True
    return ba


def check_bus(js, pal):
    # Bind the manual translation to exact source constructs and pinned bytes.
    for anchor in ["cycles: 63", "s0p: 58", "for (let c = 12; c <= 54; c++)",
                   "for (let d = -3; d <= 1; d++)", "at(p).ph2 = { t: \"s\", spr: i, nth: 1 }"]:
        assert anchor in js
    comparisons = 0
    budgets = []
    for bad in (False, True):
        for mask in range(256):
            model = vicspector_line(mask, bad)
            official = {c: ba_from_vice(pal[c, 2], mask, bad) for c in range(1, 64)}
            assert model == official
            # Settled repeating-line CPU/RDY budget, not an AEC ownership check.
            # Four low-BA cycles include the current cycle and three lead-in
            # cycles. The CPU remains held when BA spans adjacent fetch windows,
            # even when a particular cycle contains no scheduled phi2 fetch.
            cpu_held = {c: all(official[(c - d - 1) % 63 + 1] for d in range(4)) for c in official}
            free = sum(not official[c] for c in official)
            writes = sum(official[c] and not cpu_held[c] for c in official)
            if mask in (0, 1, 255):
                budgets.append(dict(badline=bad, mask=mask, free=free, write_only=writes,
                                    cpu_held_by_rdy_model=sum(cpu_held.values())))
            comparisons += 63
    # Distinguish that CPU budget from physical fetch occupancy explicitly.
    # On the all-eight-sprite badline BA does not rise between c-accesses and
    # sprite DMA. Cycles55..57 lack a scheduled phi2 fetch but cannot restart
    # a CPU already halted on a read. No independent AEC signal check is made.
    all_ba = {c: ba_from_vice(pal[c, 2], 255, True) for c in range(1, 64)}
    all_held = {c: all(all_ba[(c - d - 1) % 63 + 1] for d in range(4)) for c in all_ba}
    no_fetch_held = [c for c in range(1, 64)
                    if pal[c, 2]["fetch"] == "None" and all_held[c]]
    phi2_fetch_slots = sum(pal[c, 2]["fetch"] != "None" for c in range(1, 64))
    assert no_fetch_held == [55, 56, 57] and phi2_fetch_slots == 56
    # Check individual pointer/data fetch half-cycles against the official table.
    fetches = []
    for s in range(8):
        p = 58 + 2 * s if s < 3 else 1 + 2 * (s - 3)
        expected = [(p, 1, f"SprPtr({s})"), (p, 2, f"SprDma0({s})"),
                    (p + 1, 1, f"SprDma1({s})"), (p + 1, 2, f"SprDma2({s})")]
        for c, phase, label in expected:
            assert pal[c, phase]["fetch"] == label
        fetches.append(dict(sprite=s, pointer_phi1=p, byte0_phi2=p, byte1_phi1=p + 1, byte2_phi2=p + 1))
    # Vicspector shows sprite-register X, shifted four pixels from table beam X.
    x_rows = []
    for c in range(1, 64):
        sx = (0x194 + 8 * (c - 1) - 4) % 0x1f8
        assert (sx + 4) % 0x1f8 == pal[c, 1]["x"]
        x_rows.append(dict(cycle=c, vicspector_sprite_x=sx, vice_phi1_beam_x=pal[c, 1]["x"]))
    return dict(ba_cases=512, ba_cycle_comparisons=comparisons, ba_mismatches=0,
                fetch_halfcycle_comparisons=32, fetch_mismatches=0, budgets=budgets,
                budget_classification="settled repeating-line CPU/RDY model using four consecutive low-BA cycles; not AEC equivalence",
                aec_independently_compared=False,
                all_sprite_badline_example=dict(cpu_held_by_rdy_model=59, phi2_fetch_slots=phi2_fetch_slots,
                                               no_phi2_fetch_but_cpu_held=no_fetch_held),
                pal_fetches=fetches, x_comparisons=63, x_mismatches=0, x_table=x_rows)


def crunch(base):
    mc = (base + 3) & 63
    # Independent bitwise reference: OR bits0/2/4, AND bits1/3/5.
    return sum((((base >> bit) & 1) | ((mc >> bit) & 1) if bit % 2 == 0
                else ((base >> bit) & 1) & ((mc >> bit) & 1)) << bit for bit in range(6))


def graph_check(js, mem):
    assert "return ((mc | b) & 0x15) | (mc & b & 0x2a);" in js
    assert "0x2a & (mcbase & mc)" in mem
    assert "0x15 & (mcbase | mc)" in mem
    table = []
    for base in range(64):
        mc = (base + 3) & 63
        vicspector = ((mc | base) & 0x15) | (mc & base & 0x2a)
        vice = (0x2a & (base & mc)) | (0x15 & (base | mc))
        assert vicspector == vice == crunch(base)
        table.append(dict(base=base, mc=mc, normal=mc, crunch=crunch(base)))
    # Breadth-first simple-cycle enumeration, unlike upstream recursive DFS.
    start = 0x35
    q = deque([(start, (), frozenset([start]))])
    loops = {}
    expanded = 0
    while q:
        cur, path, seen = q.popleft()
        expanded += 1
        if len(path) >= 22:
            continue
        for action, nxt in (("normal", (cur + 3) & 63), ("crunch", crunch(cur))):
            if nxt == 63:
                continue
            new = path + ((action, nxt),)
            if nxt == start:
                loops.setdefault(len(new), new)
            elif nxt not in seen:
                q.append((nxt, new, seen | {nxt}))
    assert sorted(loops) == [1, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22]
    # A different question: shortest path from reset0 to DMA terminal63.
    q = deque([(0, ())])
    seen = {0}
    while q:
        cur, path = q.popleft()
        if cur == 63:
            terminal = path
            break
        for nxt in ((cur + 3) & 63, crunch(cur)):
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, path + (nxt,)))
    assert len(terminal) == 17
    return dict(formula_cases=64, formula_mismatches=0, offset_table=table,
                origin=start, bound=22, simple_paths_expanded=expanded,
                loop_lengths=sorted(loops), loop_witnesses={str(k): list(v) for k, v in sorted(loops.items())},
                reset0_to_terminal63_steps=len(terminal), terminal_path=[0] + list(terminal),
                note="15/16-line witnesses are graph results; no timed code, latch setup, pixels or hardware run proved")


def misc_listing(pal):
    """Read only published source lines; schedule our own R/W micro-patterns."""
    lines = (UP / "misc-tech.html").read_text().splitlines()
    rows = []
    for lineno, line in enumerate(lines, 1):
        clean = html.unescape(re.sub(r"<[^>]+>", "", line)).strip()
        m = re.fullmatch(r"(nop|sty|lda|sta|shy)\s*(.*?)\s*;\s*(\d+)(.*)", clean)
        if m and 327 <= lineno <= 370:
            op, operand, cycle, rest = m.groups()
            n = 2 if op == "nop" or operand.startswith("#") else 5 if op == "shy" else 4
            rw = "R" * (n - 1) + "W" if op in ("sty", "sta", "shy") else "R" * n
            rows.append(dict(source_line=lineno, instruction=f"{op} {operand}".strip(), annotation=int(cycle), rw=rw))
    assert len(rows) == 29
    t = 54
    ba = {c: ba_from_vice(pal[c, 2], 255, False) for c in range(1, 64)}
    for row in rows:
        executed, stalled = [], []
        for access in row["rw"]:
            while access == "R" and ba[(t - 1) % 63 + 1]:
                stalled.append(t)
                t += 1
            executed.append(t)
            t += 1
        assert (executed[0] - 1) % 63 + 1 == row["annotation"], row
        row.update(executed_absolute_cycles=executed, stalled_absolute_cycles=stalled,
                   write_cycle=((executed[-1] - 1) % 63 + 1) if row["rw"][-1] == "W" else None)
    assert [((c - 1) % 63 + 1) for c in rows[0]["executed_absolute_cycles"]] == [54, 11]
    assert rows[1]["write_cycle"] == rows[16]["write_cycle"] == 15
    return dict(instructions=len(rows), annotation_mismatches=0, rows=rows,
                caveat="static no-badline, all-eight-DMA BA/RDY schedule, not independent AEC or CPU emulation; source annotations are first executed cycles, not attempted starts")


def fpp_samples():
    reader_path = ROOT / "research/quondam/snapshot_state.py"
    reader_pin = record(reader_path, "c2de249e3d3a6fea3f42e0f72227d1b6d5cdc4fcee87fce49f1de301cc0df06a")
    spec = importlib.util.spec_from_file_location("vicspector_snapshot_reader", reader_path)
    reader = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(reader)  # Our pinned repository decoder; no downloaded code.
    records, pairs = [reader_pin], []
    base = ROOT / "build/research/no-bounds"
    for name in SNAP_PINS:
        records.append(record(base / name, SNAP_PINS[name]))
    for name in SNAP_PINS:
        if "-preclear" not in name:
            continue
        post_name = name.replace("-preclear", "-postclear")
        pre, post = [reader.read_snapshot(base / x)["vicii"] for x in (name, post_name)]
        cpu_pre, cpu_post = [reader.module_payload(base / x, "MAINCPU") for x in (name, post_name)]
        ram = reader.module_payload(base / name, "C64MEM")[4:65540]
        pc = int.from_bytes(cpu_pre[12:14], "little")
        assert ram[pc:pc + 3] == bytes.fromhex("8e 17 d0") and cpu_pre[9] == 0  # STX $d017, X=0.
        assert int.from_bytes(cpu_post[12:14], "little") == pc + 3
        assert int.from_bytes(cpu_post[:8], "little") - int.from_bytes(cpu_pre[:8], "little") == 4
        offsets = list(range(3, 25, 3))
        assert pre["raster_line"] == post["raster_line"]
        assert post["raster_cycle"] - pre["raster_cycle"] == 4
        assert pre["raster_cycle"] in (45, 46) and post["raster_cycle"] in (49, 50)
        assert pre["regs"][0x17] == 255 and post["regs"][0x17] == 0
        assert [s["mcbase"] for s in pre["sprites"]] == [s["mcbase"] for s in post["sprites"]] == offsets
        assert [s["mc"] for s in pre["sprites"]] == [s["mc"] for s in post["sprites"]] == [b + 3 for b in offsets]
        assert all(s["exp_flop"] == 0 for s in pre["sprites"])
        assert all(s["exp_flop"] == 1 for s in post["sprites"])
        pairs.append(dict(pre=name, post=post_name, line=pre["raster_line"], instruction_pc=pc,
                          raw_pre=pre["raster_cycle"], raw_post=post["raster_cycle"],
                          pal_pre=pre["raster_cycle"] + 1, pal_post=post["raster_cycle"] + 1,
                          clocks=4, actual_mcbase=offsets, actual_mc=[b + 3 for b in offsets],
                          hypothetical_cycle15_crunch=[crunch(b) for b in offsets],
                          hypothetical_differs=7))
    assert len(pairs) == 7
    return records, pairs


def main():
    records, sources = source_inputs()
    js = (UP / "index.html").read_text()
    pal = parse_pal(sources["vicii-chip-model.c"])
    bus = check_bus(js, pal)
    graph = graph_check(js, sources["vicii-mem.c"])
    listing = misc_listing(pal)
    sample_inputs, samples = fpp_samples()
    proof = dict(upstream_commit=COMMIT, inputs=records + sample_inputs,
                 method="own Python parser/model; source strings treated only as data; no upstream execution",
                 bus=bus, crunch_graph=graph, misc_schedule=listing, fpp_samples=samples,
                 limitations=["PAL only; no NTSC or dynamic line-transition acceptance",
                              "settled repeating-line CPU/RDY budget and published instruction patterns, not AEC equivalence or a CPU emulator",
                              "no hardware test or generated raster code",
                              "graph loop existence does not prove arbitrary artwork or MISC encoding works",
                              "seven snapshots pairs reused passively; no new native evidence"])
    OUT.mkdir(parents=True, exist_ok=True)
    path = OUT / "proof.json"
    path.write_text(json.dumps(proof, indent=2, sort_keys=True) + "\n")
    print(json.dumps(dict(proof=record(path), ba_comparisons=bus["ba_cycle_comparisons"],
                          ba_mismatches=0, aec_independently_compared=False,
                          all_sprite_badline_example=bus["all_sprite_badline_example"],
                          misc_instructions=listing["instructions"],
                          loop_lengths=graph["loop_lengths"], fpp_pairs=len(samples)), indent=2))


if __name__ == "__main__":
    main()
