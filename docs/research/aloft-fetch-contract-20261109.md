# Aloft: conditions for cached row-7 graphics fetches

Research date: 9 November 2026. This pass derives a small VIC implementation
contract from pinned official VICE 3.10 source. It explains which conditions
would let the [forty-byte glyph working set](aloft-cell-glyphs-20261109.md)
serve repeated graphics lines without refreshing the forty cached codes and
colors. **It does not establish actual Aloft fetch timing, cache origin or
lifetime, pixels, FPS, or a named FLD/linecrunch effect.** Fresh native work
remains a separate custody/comparison lane. No new native snapshot or expected
RAM value is an input to these predictions.

The source code and all seven derived files are produced by
[fetch_contract.py](../../research/aloft-execution-20261109/fetch_contract.py).
It contains finite address/counter fragments and declared hypothetical
schedules, not a CPU interpreter, full VIC emulator or renderer.

## Numeric model 1 means MOS8565 here

An important implementation distinction is now pinned. In the **viciisc**
namespace of `src/vicii.h` lines 57–63, model 0 is MOS6569, model **1 is
MOS8565**, and model 2 is MOS6569R1. The older `vicii` implementation has
different numeric names; its enum must not be applied to C64SC snapshots.

`viciisc/vicii-chip-model.c` selects the MOS8565 structure for model 1. It
uses the PAL 63-cycle/312-line table and **color_latency=0**. In this branch,
both graphics address selection and idle-graphics address selection use
`reg11_delay`. The separate 6569 color-latency branch includes additional
RAM/character-ROM transition handling and is not this model's rule. The
earlier [context proof](aloft-cell-context-20261109.md) checked numeric model
1; this adds the source-bound chip/latency interpretation without changing
those frozen bytes or claiming a silicon measurement.

Current YSCROLL, the CPU-visible `$D011` raster-MSB read and delayed graphics
mode are different inputs. A CPU `$D011` store updates `regs`/YSCROLL and the
IRQ comparison; it does **not** immediately recompute `bad_line`. That occurs
in the next applicable VIC cycle logic. Consequently a post-INC snapshot can
contain the new register/YSCROLL and the previous `bad_line` simultaneously.

## The actual order matters

The primary source atlas retains exact line ranges and hashes for the rules.
In `vicii_cycle`, the relevant order is:

1. Finish the preceding phi2 sprite fetch and advance the VIC cycle.
2. Perform the new cycle's **phi1 fetch**, choosing graphics or idle graphics
   from the then-current `idle_state`; draw-cycle processing follows.
3. Handle line/frame bookkeeping and recheck the badline condition.
4. Apply VC/VMLI reload and RC rules when their table flags are set.
5. Apply BA/prefetch and conditional matrix fetch logic.
6. Copy current `$D011` into `reg11_delay` for later fetches.

The finite producer models only selected address/counter fragments of this
sequence. It does not execute the draw, sprite, BA/prefetch or corruption
subsystems. A snapshot's resulting RC/idle values are not automatically the
pre-phi1 values used earlier in that same tick.

The producer parses the original PAL initializer rather than inventing a
cycle schedule:

| Event | Hardware-cycle notation | Snapshot zero-based cycle |
| --- | --- | --- |
| VC loaded from VCBASE; VMLI cleared; RC reset if badline | 14 | 13 |
| Matrix-fetch opportunities in phi2 | 15–54 | 14–53 |
| Forty graphics-fetch slots in phi1 | 16–55 | 15–54 |
| RC/display-state update | 58 | 57 |

A graphics slot is not necessarily an active character fetch. With
`idle_state=1`, it calls idle-graphics fetching and leaves VC/VMLI unchanged.
With `idle_state=0`, it uses a cached code, fetches the selected row, increments
VMLI and increments VC modulo 1024. In ordinary character mode with character
base zero, its logical address is `(cached_code << 3) | RC`. Thus **RC7 plus
active display** gives the desired row-7 addresses; RC7 alone does not.
The 2,048 normal-character address cases and all 32 RC58 input combinations
are checked exhaustively as finite data transformations.

At the RC58 update, RC7 first puts display into idle and saves VC in VCBASE.
A simultaneous badline condition then increments RC modulo eight and restores
display. The order of those two tests matters. VC reload at cycle14 resets RC
only if the rechecked badline is true at that point.

## Two sufficient schedules, neither an observed timing claim

The accepted data includes two deliberately conditional examples. Their seed
cache is the independently source-constructed row24; assuming it is present
in the VIC cache is stated explicitly, rather than inferred as its origin.

The **equality-then-cancel** example starts with RC7/idle, permits an early
badline condition to enter display, then changes YSCROLL so equality is false
when the cycle14 badline check runs. Because that check precedes the RC reset,
RC7 survives. All forty graphics slots then select row7, and none of the
matrix-fetch opportunities call the cache-fetch function. Thirteen declared
visibility stages satisfy this fragment. Cancelling before any activation
instead leaves display idle; cancelling only after the RC reset produces
row0 rather than row7. These two negative boundaries prevent treating every
YSCROLL change as equivalent.

The example's “visible to the cycle14 logic” is **not** a CPU bus write at
cycle14. It does not derive instruction clocks, stall behavior or the exact
phase at which a real RMW write becomes visible. Those must be bound by the
native/source execution lane. Under its stated assumptions, the example's
hardware-cycle25 state has ten completed active graphics requests, VMLI10,
VC=VCBASE+10 modulo 1024 and RC7. This is a conditional source expectation,
not an accepted comparison with the new `$0503` capture.

The second example activates display **after** the RC58 update on one line,
then avoids a badline at the next cycle14 and throughout the next matrix
window. It likewise produces forty row7 requests without a cache fetch. This
demonstrates a distinct sufficient arrangement allowed by the source. It is
not assigned to Aloft merely because it can explain a similar working set.

Both examples yield the same forty logical row7 addresses for codes
`$00..$1F` and `$F0..$F7`, followed by RC7/idle and an advanced VCBASE. They
are mathematical conditions, not two competing claims about what the program
actually does.

## Cache persistence needs an interval, not two equal endpoints

`vicii_fetch_matrix` writes both VBUF and CBUF. With completed prefetch delay
it reads matrix RAM/ROM and ColorRAM; during the delay it writes `$FF` into
VBUF and derives the color nibble from CPU-PC RAM. Merely finding equal cache
values at two stops does not exclude same-value rewrites in between.

For a cache-lifetime proof, either bind **every matrix-fetch opportunity** to
`bad_line=0` over the interval, or reconstruct each cache write with its
inputs and phase. The ordinary frame-start helper resets allow-badlines,
VCBASE and VC but does not clear VBUF/CBUF. This permits persistence; it does
not identify where the retained codes were originally fetched. Reset/restore
and any other cache-changing paths must also be excluded or bound.

The previously retained pre-IRQ RC7/idle1/VCBASE0/badline0 cache match remains
an observation at a stop. It is not an active g-fetch or an origin theorem.
The [signed primary reading](aloft-cell-primary-20261109.md) and
[Bauer reference](https://www.cebix.net/VIC-Article.txt) provide the broader
badline/counter vocabulary. The new contract is derived from exact versioned
implementation branches; it does not attach a technique label from that
vocabulary before actual values and phases meet the relevant conditions.

## What the new native lane must bind

The accepted `capture-contract.json` lists the needed core fields. Full VSFs
at genuine pre-`$0500`, first actual cell entry, return `$0503` and post-`$0500`
`$F0B1` should preserve RC, idle, VC/VCBASE/VMLI, VBUF/CBUF, badline/allow state,
current and delayed `$D011`, cycle flags, model, prefetch and sprite-DMA state,
GBUF and last phi1/bus values. A useful additional comparison brackets the
cycle14 and cycle58 transitions on a line inside the chain. CPU instruction
boundaries may not land there exactly; the nearest stop must not be called
an exact half-cycle observation.

Ordered glyph writes, CPU-port changes, `$D018` and CIA2 bank/DDRA changes
must accompany `$D011` read/dummy/final values. The software read's possible
raster-MSB domain must be independently bound; a post-INC value is not its
input oracle. Duplicate monitor RMW stores reported with one instruction
completion clock do not time the two physical bus writes separately.

`VICIIVSPBug` also needs an actual resource binding if the modeled sequence
can enter its trigger region. The source condition can invoke simulated
memory corruption during particular display activations; a snapshot does not
serialize that resource. The hypothetical examples avoid that condition and
do not simulate the handler.

Finally, the VIC snapshot source explicitly omits `vbank_phi1/2`, RAM-base
pointers and address masks/offsets, which are updated elsewhere. Logical
addresses therefore need a separately bound physical bank, cartridge/Ultimax,
character-ROM and GLUE-transition history before claiming a RAM byte was
fetched. Border/draw-pipeline state and independently committed viewport
pixels remain later requirements. A matching cache or counter is useful
evidence, not a finished image compositor.

## Retention and replay

The [accepted receipt](../../build/research/aloft-execution-20261109/fetch-analysis/accepted-01/fetch-contract-proof.json)
pins nine official source members. Each retained copy is compared byte for
byte against its member in the pinned VICE 3.10 archive
`8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`.
It also pins the existing source-glyph, context and primary-reading receipts.
No new HTTP acquisition or broad creator search was needed. Candidate 01 and
02, their producer snapshots and both example families remain retained.

Offline reproduction from the repository root:

```sh
rtk proxy python3 -B research/aloft-execution-20261109/fetch_contract.py \
  --output build/research/aloft-execution-20261109/fetch-analysis/new-replay
```

The [fresh self replay](../../build/research/aloft-execution-20261109/fetch-analysis/self-replay-check.json)
matches **seven outputs / 247,516 bytes** exactly, with no path normalization,
network access, CPU/native execution or downloaded host execution. Producer:
20,521 bytes,
`b3f77c3f46e12686e51be148419e996bca6faabff3d255aee5e31a2665fffa1b`.
Accepted receipt: 6,358 bytes,
`8bdb1a96436f66b2ea690b6812c8ef78974923dfb7cd66efa6e4a2d4a20fb565`.
The independent [root source review and replay](../../build/research/aloft-execution-20261109/fetch-analysis/root-replay-check.json)
also matches all seven outputs / 247,516 bytes exactly. Its report is 1,461
bytes, SHA-256
`8f2e89ec620712418dc2743fc7109187a577ebefc25277877cb01eafa92ac09d`.

After those predictions were written, a separate
[raw exploratory probe](../../build/research/aloft-execution-20261109/fetch-analysis/raw-native-probe-01.json)
read six completed unique VSFs from the new owner-controlled case. It records
first-return line48/cycle24 with RC7/idle0, VC10, VCBASE0 and VMLI10, agreeing
with the earlier conditional cycle25 expectation. The pre/post-INC states
show badline1/display before the change and badline0/display afterwards; all
forty cached codes/colors still match. The chain-return records VC808,
VCBASE792 and VMLI16. These remain **raw unaccepted observations** pending
closed custody and a separate comparison wrapper. They never seed the
accepted source contract or prove a physical-fetch history, cache origin or
lifetime. The exploratory report is 5,296 bytes,
`f13c542443829d7627a3e0317ea6726fecf1f63939d19de886c4696e946b69b3`.

The next binding is the closed, source-guarded native cell interval and its
actual VIC states; the named layered scene remains a separate open target.
