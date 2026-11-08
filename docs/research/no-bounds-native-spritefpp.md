# No Bounds: original SpriteFPP counter holding and shared-strip fetches

The original released disk now has a native witness for its SpriteFPP
mechanism. Eight hardware sprites use one cached pointer while their held
MCBASE offsets are **3,6,9,12,15,18,21,24**. Three consecutive interior cells
provide **24 nonzero three-byte data-latch matches** against original,
file-defined atlas bytes. Clearing `$d017` changes the expansion flip-flops
without changing those offsets. The observed mechanism is counter holding
across PAL cycle16, not the special cycle15 crunch case.

This connects the [original-bundle binding](no-bounds-original.md) and
[prepared atlas/pose model](frontier-geometry-20261108.md) to actual original
execution. It does not establish a complete displayed frame: the first-field
palette remains black. The earlier prepared-pose counts are not counted again
as new native work.

## Original startup and variant identity

The owned VICE case is `build/research/no-bounds/native-02/`. It booted the
original side 1 disk with SHA-256
`f603e03f94ed4df416584419a696e1832b0710308de8faf2d0179b0a7725fe70`.
No PC redirection, RAM injection, snapshot restore, downloaded host binary or
source rebuild was used. Two navigation resumes used declared warp; the
initializer and FPP proof resumes used warp off and Speed100. Eleven native
resumes and 99 serialized commands completed on one owned process/socket;
two observation timeouts continued on their original handles. The owner
explicitly closed and reaped that process before the passive audit pinned it.

The 834-byte boot PRG includes a two-byte load header. Its **832 loaded bytes**
match native RAM at `$0801` before the natural BASIC `SYS2064` entry `$0810`.
The conditional production entry at `$c300` matches **all 20,261 known bundle
bytes**, including the 50-byte DISK driver. The actual call is
`$08a4: JSR $c300`; its stack contains the stored JSR return `$08a6`, and the
initializer naturally returns to `$08a7`. This is the original common-demo
initializer, not the separate standalone wrapper.

The three bytes excluded from bundle 31, `$4000..$4002`, are actually
**`47 ec 98`** here. Their values are recorded as native prior state; they
have not become file-defined bytes or been replaced with standalone zeros.
No pointer 0 fetch was collected in this case to prove those header bytes
unused.

## Concrete checkpoints

The audit verifies full 64 KB RAM/VSF equality and explicit monitor CPU/VIC
coordinates for all eleven pairs. These are raw zero-based raster cycles:

| Checkpoint | PC | Clock | Line / raw cycle |
| --- | ---: | ---: | ---: |
| Original boot | `$0810` | 6,977,568 | 307 / 3 |
| Production initializer entry | `$c300` | 141,106,918 | 256 / 22 |
| Natural initializer return | `$08a7` | 141,123,577 | 208 / 49 |
| First prepared pointer/X table | `$9237` | 141,190,588 | 24 / 28 |
| First FPP prefix | `$8026` | 141,193,881 | 76 / 45 |
| Cell62 before / after clear | `$8846 / $8849` | 141,197,850 / 854 | 139 / 45,49 |
| Cell63 before / after clear | `$8867 / $886a` | 141,197,913 / 917 | 140 / 45,49 |
| Cell64 before / after clear | `$8888 / $888b` | 141,197,976 / 980 | 141 / 45,49 |

At `$08a7` CIA2 still selects bank 0. By `$9237`, PRA=`$c0`, DDRA=`$3d` and
input pull-ups produce low pins `%10`, selecting bank **`$4000`**. D018=0
places the sprite pointers at `$43f8..$43ff`. Reading DDR alone would have
misidentified the bank at the initializer return.

Actual initialized sprite Y registers are **75,74,73,72,71,70,69,68**. At
line 76/raw45 the native MCBASE vector is already 3 through 24 in steps of3;
MC equals MCBASE and all cached pointers still select the defined blank `$ff`
slot. Those initial zero latches are retained as startup state rather than
counted as nonzero data proof.

## Holding, pointer latency and fetched data

At each interior pre-clear point, D017=`$ff`, expansion flip-flops are all0,
and MCBASE is 3 through 24. All eight complete data fetches have occurred; MC
is **6,9,12,15,18,21,24,27**. Four native cycles later, D017=0 and flip-flops
are all1. MC, MCBASE, cached pointers and data remain identical. The next
pre-clear point is exactly63 elapsed cycles later. These stops are well after
PAL cycle16, not at the special PAL15 crunch phase. The producer also computes
that hypothetical crunch result and checks that it differs from the observed
unchanged counters.

The [official VICE3.10 source](https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/)
provides the audited snapshot layout, fetch phases, MC reset/update and D017
semantics. The exact pinned source fragments are retained with the receipt.
CPU monitor store coordinates are observer boundaries, not asserted physical
bus-write timestamps.

The current RAM pointer table is **one row newer** than the actual cached VIC
pointers in all three cells:

| Cell | Current RAM pointers | Actual eight cached pointers | Distinguishing data examples |
| --- | ---: | ---: | --- |
| 62 | `$05` | `$06` | sprite 0 `0000aa`, interior `aaaaaa`, sprite 7 `aa8000` |
| 63 | `$0a` | `$05` | sprite 0 `0000ff`, interior `ffffff`, sprite 7 `ffc000` |
| 64 | `$0b` | `$0a` | sprite 0 `2aaaaa`, remaining slices `aaaaaa` |

Each native latch equals three original bytes at
`$4000 + cached_pointer*64 + MCBASE`. All 24 triplets are nonzero and lie
inside the original file-defined mask. Wrong models fail independently:
substituting fresh RAM pointers changes **24/24** triplets, starting at counter 0
changes **24/24**, and making every sprite use offset 3 changes **21/24**.
The latter deliberately leaves sprite 0 matching; it is not presented as a
control that must fail every sample.

The trace checks all eight pointer stores in cells 0..64, 520 stores in total,
alongside 65 D017 sets and 64 flushed clears. Pointer stores are observed at
raw17..45, after the early-line sprite fetch window. The final cell 64 clear
is established by its before/after snapshots; its delayed trace callback had
not flushed before closure and is not invented. There are 2,095 observer trace
records, representing 2,094 unique instruction/target/clock records: the broad
initializer trace overlaps the dedicated D017 trace once. Both original
records remain in the trace artifact.

## Atlas padding is live workspace

After entry, precisely eight bytes in the loaded atlas domain change:
**`$43f8..$43ff`**, the sprite pointer table. They occupy **slot 15 offsets 56..63**,
outside every prepared strip's payload at offsets 3..26. The audit checks all
68 payloads against original bytes and verifies that the other 4,344 bytes of
the loaded atlas domain remain original at these endpoints. It reports the
eight pointer-table exceptions explicitly instead of calling the whole atlas
immutable.

The first prepared pose is frame 0, X size 0, Y size 127. Its X expansion mask is
`$04`, and sprite X registers are 110,134,158,0,0,0,206,230. This initial growth
state is not proof of a mature 192-pixel-wide visible object. All selected
sprite/background colors remain 0 despite the nonzero data fetches, so no
visible shading, priority reconstruction or displayed-frame rate is claimed.

## Replay and continuation

```sh
rtk proxy python3 research/no-bounds/native_spritefpp.py
```

The passive producer writes
[`native-spritefpp-proof.json`](../../build/research/no-bounds/native-spritefpp-analysis/native-spritefpp-proof.json)
and its full store trace under ignored `build/research/no-bounds/native-spritefpp-analysis/`.
The closed case digest is
`7ba2f44ed1dc2775e6db09dd239a64a26a03c261f0f20728904d95e22e425033`.
The frozen wire auditor's original startup assertion permits only manual
loads. This producer reuses its pinned function with one recorded in-memory
adaptation: require the exact original-disk autostart contract. Raw-byte,
serialization, timeout and closure checks are preserved; the frozen auditor
and observer files are unchanged.

Continue in a **new native03 case** by restoring the pinned
[`cell64-postclear.vsf`](../../build/research/no-bounds/native-02/cell64-postclear.vsf),
checking complete restored RAM/CPU/CIA/VIC equality before execution, and
resuming naturally. Candidate cell 92's pre-clear PC is `$8c24`. Its previous
prepared row selects pointer 0; accept that only if actual saved cached pointers
confirm it. Compare the latch data at held offsets with the nonzero native
`$4000..$4002` header as a discriminating wrong zero-offset model. That witness
was suggested after this case closed and has **not** been collected.

Then follow the natural fade until colors become nonzero, collect a mature
prepared pose and phase-qualified scanout, and reconstruct displayed pixels
before claiming visible output. The supplied standalone needs its own genuine
BASIC startup and separate verification. No existing native02 file should be
modified for either continuation.
