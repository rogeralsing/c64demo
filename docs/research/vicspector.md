# Vicspector: useful PAL planner, bounded source audit

[Vicspector](https://github.com/elysium64/vicspector) is a readable, interactive VIC-II timing reference. Its useful parts are the per-cycle bus chart, read/write-aware instruction placement and sprite-offset graph. It is a host-side guide, not a C64 renderer, assembler, cycle-accurate emulator or generator for our complete FPP routine.

Source was downloaded and read on 2026-11-08. No downloaded JavaScript, script, executable or build was run. No new VICE session or CPU execution was performed. Only the new producer, this note and ignored `build/research/vicspector/` were written.

## Pinned inputs and replay

Upstream `main` resolved to commit **`c972f7a0a965d28096cc1396cab01fded307d818`**, committed 2026-09-18: [pinned README](https://github.com/elysium64/vicspector/blob/c972f7a0a965d28096cc1396cab01fded307d818/README.md), [pinned implementation](https://github.com/elysium64/vicspector/blob/c972f7a0a965d28096cc1396cab01fded307d818/index.html). Retained files are in `build/research/vicspector/upstream/`:

| Input | Bytes | SHA-256 |
|---|---:|---|
| `README.md` | 4,236 | `fb7d27bd3e4495c0fcdc6120afa99f97621cf37b976e0a30dac2a2202b8a60d6` |
| `index.html` | 109,268 | `46ce401e161ea13583f179cb83c7eca2ac86f367c3799533f10fc76b98289fc7` |
| `LICENSE` | 1,066 | `b06869ac0369bf327ee6ef60157f43edadfb64b70f11979269fc7361002061dd` |
| GitHub commit response | 32,951 | `37f62ded432595fd11bccaab87d7cc53f8e8d103d0517f3b2cfa42e9a05b2be3` |
| [Åkesson, MISC technical notes](https://www.linusakesson.net/scene/lunatico/misc.php) HTML | 51,632 | `0c246e0fe48e37f71952cc3d56da052dc7a05b5cc34b0b2a9761c66bdb8f21b7` |
| [Åkesson timing-chart page](https://www.linusakesson.net/programming/vic-timing/) HTML | 18,341 | `cee4af890ee00d94d5bc38cfb45af401006741f6f06010d6bf69d7da27fc1315` |

The timing-page HTML was retained for provenance; its linked PDF/image was not independently checked. Primary numerical references are the already retained official VICE 3.10 archive, `build/research/quondam/hardware-source/vice-3.10.tar.gz`, SHA `8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`, and retained [Bauer VIC article](https://ist.uwaterloo.ca/~schepers/MJK/ascii/VIC-Article.txt), SHA `ed558b2480638b153d0ead4726b8b675e4a0b945f2ab4d37c17a3d892cf00828`. The producer reads archive members without extracting them and pins their hashes.

From the repository root:

```sh
rtk proxy python3 research/vicspector/inspect.py
```

This uses Python's standard library, retained inputs and our pinned snapshot decoder. It writes only `build/research/vicspector/proof.json`. It performs no network request on replay. The JSON records every source/member/snapshot pin, parsed tables, graph witnesses and instruction placements. Frozen prior proofs are not modified or rerun.

## What independently matches

The producer parses `vice-3.10/src/viciisc/vicii-chip-model.c`'s PAL initializer as data, and compares it with a human translation of the pinned Vicspector ranges. It does not execute or evaluate upstream code.

* All **512** combinations of sprite-DMA mask and bad/clear line match for **32,256 BA-cycle comparisons**.
* All **32** sprite-pointer/data half-cycle entries match the official table.
* All **63** displayed sprite-X values match the VICE first-phase beam-X table after Vicspector's documented four-pixel shift.
* Using the actual published MISC instruction listing and the VICE BA table, an independent read/write scheduler matches all **29** annotated instruction starts. It reproduces the `NOP` executing at 54 and the following line's 11, plus both crunch writes at 15. The annotations describe the first executed cycle; an instruction may have been waiting earlier.

These are static, settled PAL BA, fetch-table and instruction-schedule checks. AEC was not independently compared. They do not validate changing DMA/badline conditions during a line, arbitrary 6510 instruction semantics, NTSC, border pixel timing or complete raster programs. The scheduler knows the required read/write patterns and instruction lengths for this listing; it is not a CPU emulator.

The budget terminology needs care:

| Settled PAL line | Unrestricted cycles | Additional write-only cycles | CPU held by RDY model |
|---|---:|---:|---:|
| Clear, no sprites | 63 | 0 | 0 |
| Clear, sprite 0 | 58 | 3 | 2 |
| Clear, all eight | 44 | 3 | 16 |
| Badline, no sprites | 20 | 3 | 40 |
| Badline, all eight | 1 | 3 | 59 |

Thus the familiar “23 cycles left on a badline” includes three cycles usable only for writes. “Two cycles per sprite” describes data-DMA bus occupancy; an isolated DMA window also has the three-cycle BA lead-in. A budget is not an instruction count.

The final column is a settled repeating-line CPU/RDY classification: the current and three preceding cycles all have BA low. It is not physical bus ownership or an independent AEC measurement. On a badline with all eight sprites, the official table contains **56 second-phase fetch slots**, but the CPU model is held for **59 cycles**. Cycles **55–57** have no scheduled second-phase fetch; BA never rose between the character and sprite fetch windows, so a CPU already halted on a read cannot resume there. Vicspector's planner follows BA for reads and allows the specified writes through; it does not independently emulate AEC or prove arbitrary read/write patterns are physically executable.

Source anchors: pinned `index.html:1606–1787` (models/bus), `1680–1685` (X shift), `2040–2061` (read/write patterns), `2189–2235` (scheduler). Official `vicii-chip-model.c:112–237` contains the PAL table; `78–83` defines BA masks. Bauer `137–158,219–236,415–449,1107–1137` defines phases and read/write bus availability. MISC retained HTML `327–393` contains the listing and its timing explanation. Vicspector repeats the selected line's bus pattern on overrun; it does not establish that the next physical line has that same state.

## Timing units and the crunch caveat

Vicspector and Bauer number PAL **full clock cycles 1–63**, each containing first/second half-cycles. The processor accesses the bus in the second half. Our VICE snapshot `raster_cycle` is **zero-based 0–62**; add one before comparing cycle labels. Vicspector's X ruler is in sprite-register pixels, advancing eight per full cycle, with a four-pixel shift relative to the first-phase beam-X value. Neither X convention is a screenshot's array index.

The mixed-bit crunch formula is sound. For `MC = (MCBASE + 3) & 63`, the producer checks all 64 origins using a separate bit-by-bit OR/AND reference and VICE's expression; all agree with Vicspector. But Vicspector's explanatory labels describe a `+2` operation at 15 followed by `+1` at 16 (`index.html:1856–1867,1970–1973`). Do not use this wording as proof of internal sub-operations. Bauer's retained account describes a conditional MC-to-MCBASE transfer, with the mixed-bit exception (`1924–1934`). VICE implements that transfer, not two arithmetic increments.

Exact official VICE anchors, archive members under `vice-3.10/src/viciisc/`:

* `viciitypes.h:45–47`, `vicii-chip-model.c:808`: zero-based cycle convention.
* `vicii-chip-model.c:140–143`: crunch check at PAL cycle 15 and MCBASE update at PAL cycle 16.
* `vicii-mem.c:183–213`: clearing an expansion bit with flop 0 applies the formula only in the crunch window, then sets flop 1. It changes MC; the following update copies it to MCBASE.
* `vicii-cycle.c:81–104,490–507`: conditional transfer and later expansion-flop toggle.
* `vicii-cycle.c:63–79,509–513`: MC reload from MCBASE.

There is a phase-description limit: Bauer places the transfer in the first phase of cycle 16. VICE's table labels `UpdateMcBase` `Phi2(16)` and coalesces half-cycle flags (`vicii-chip-model.c:729–731`) into its cycle handler. This audit establishes the cycle convention and implementation behavior, not an independently measured transistor-level half-cycle event.

## The 15/16-line paths are graph results

Our breadth-first simple-cycle enumeration differs from upstream's recursive search. Avoiding terminal offset 63, it finds loops from `$35` of lengths **1,13,14,15,16,17,18,19,20,21,22**, within the same 22-step bound. The JSON includes full witnesses. Examples, `⇒` means crunch:

```text
15: 35→38→3b→3e⇒15→18→1b→1e→21→24→27→2a→2d→30⇒31⇒35
16: 35→38→3b→3e⇒15→18→1b→1e→21→24→27→2a→2d→30→33→36⇒35
```

The published MISC discussion lists eight lengths and omits 15/16 (`misc-tech.html:157–171`). Vicspector's README flags the discrepancy. This check confirms those two mathematical paths; it does not establish why MISC omitted them, whether arbitrary artwork fits their overlapping data rows, or whether MISC's collision-encoded schedule supports them. That explanation remains unresolved.

Separately, the shortest graph path from reset offset 0 to terminal 63 takes **17 transitions**, reproducing the classic reset-to-reuse result. That is a different question from returning to a chosen nonzero origin. No new hardware minimum was discovered.

The graph (`index.html:3399–3429`) has only two outgoing choices: advance by3 or crunch. It omits holding the offset, initial latch/DMA preparation, pointer changes, palette, collisions, instruction placement and badline handling. Its schedule text is a graph plan, not generated executable raster code. MISC itself describes additional latch preparation, three-line collision latency, pointer-update windows and initial offset setup (`misc-tech.html:285–319,384–401`).

## Does this cover our FPP samples?

The producer independently re-decodes seven frozen pre/post-clear pairs: native02 cells62–64; native03 pointer0 and mature64–66. Each contains actual `STX $d017` with X=0, a four-clock transition, `$D017:ff→00`, expansion flop `0→1`, unchanged MCBASE **3,6,9,12,15,18,21,24**, and unchanged MC **6,9,12,15,18,21,24,27**. Snapshot hashes and exact PCs are in the JSON.

Native02's stops are raw cycles 45/49, meaning PAL cycles 46/50. Native03's are raw cycles 46/50, meaning PAL cycles 47/51. These bracket a later write; neither pair places the write at crunch cycle 15. Holding flop 0 across the PAL cycle 16 update preserves MCBASE. The later clear sets flop 1, and the subsequent expansion toggle can reset it for the next line. Bauer explicitly distinguishes late stretching from cycle 15 crunch (`2590–2621`).

Applying the crunch graph to those eight origins instead predicts **7,5,13,13,23,21,21,25**; seven differ from the actual held offsets. Origin 21 is an accidental fixed point, so checking only that sprite would fail to discriminate the models. Vicspector's chart is useful for planning the later writes; its two-edge crunch graph does not model this held-offset routine.

It also does not track our individual cached pointers. Official pointer fetches occur at PAL cycles 58/60/62 for sprites 0–2 and PAL cycles 1/3/5/7/9 for sprites 3–7, with the three bytes immediately following across half-cycles. `vicii-fetch.c:110–153,275–298` uses each sprite's cached pointer and MC, not the latest RAM table value. Use the existing [native data proof](no-bounds-native-spritefpp.md) and [bounded visible proof](no-bounds-spritefpp-visible.md) for original atlas binding and actual scanout; this source audit makes no new pixel, animation, FPS or physical-hardware claim.

Next useful application: enter an already understood PAL instruction sequence with the correct static DMA mask, verify the final write cycles, then validate the complete generated routine against native state and committed pixels. Any new crunch experiment needs explicit latch initialization and native capture at PAL cycles 15/16 before accepting the graph plan as executable behavior.
