# Aloft cell execution: owner closure and continuation

Research date: 9 November 2026. The broad C64 research objective remains active.
This new pass follows the frozen generator, finite semantics, glyph mapping and
primary VIC reading. It does not replace the separate named-scene, side-two,
Hat, Lab or EOD backlogs.

The original user reference, The Lab's large colored polygon ball, is already
resolved by the [scene study](the-lab-ball.md), [fresh native custody](the-lab-ball-native.md)
and [complete color/pixel comparison](the-lab-ball-pixels.md). That ball uses
multicolor bitmap graphics with sprites disabled in the observed interval,
prepared projected edges, runtime XOR boundaries and vertical filling, plus
per-cell attributes. It must not be confused with this Aloft character/raster
mechanism or The Lab's distinct sprite-vector parts.

## The new original-disk case is closed

The root-owned [native case](../../build/research/aloft-execution-20261109/native-01/session.json)
started the untouched original side-one D64 as both autostart program and drive 8.
It used true 1541 emulation and default PAL resources. The owner closed the
observer after all 202 responses completed and all monitor checkpoints were
removed. Unified session 26020 exited 0; owned VICE PID 93687 exited −15 and was
reaped at 2026-11-09T10:23:27.122071+00:00.

There were no snapshot restores, RAM/PC patches, disk changes, restarts,
interrupts or observation timeouts. Warp was used only for earlier navigation,
then disabled before the observed cell windows. Queries bind Speed=100,
VICIIModel=1 (the source-bound MOS8565 PAL branch), border mode 0 and VICIIVSPBug=0.
Dummy-access checkpoint reporting was enabled before both execution windows.
Five final read-only resource queries omitted required quotes and returned
syntax errors. They changed no resource; the exact corrected queries and
successful responses follow without resuming execution.

The root [owner record](../../build/research/aloft-execution-20261109/owner-closure-01.json)
maps all eighteen RAM/VSF pairs to their actual response sequences. The
[closed raw-file manifest](../../build/research/aloft-execution-20261109/native-01-files.json)
pins the complete case. These are custody inputs, not independent renderer
or pixel proofs. The [freezer](../../research/aloft-execution-20261109/freeze_case_01.py)
reads retained files and records the owner's terminal-handle observation; it
does not control a process or execute C64 code.

The fresh natural SYS capture binds the original bootstrap. The run passed
the resident-copy return at `$08B5` without retaining a pair. Do not invent a
fresh complete resident comparison or normalize later self-modification to
hide that missing observation.

## Two different actual call lists

The first captured pre-`$F0AE` boundary is clock 130204323, raster 47/cycle 18.
Its genuine `$0500` dispatcher state follows at clock 130204329; the first
selected cell is `$2000`. The natural first return at `$0503` is
clock 130204392, and the complete return at `$F0B1` is clock 130216935.
The first list contains 200 calls to two distinct targets.

Navigation then ignores exactly 63 further guarded `$F0AE` hits, preserving
the original running state. The next captured boundary is 64 PAL fields later,
clock 131462307, again raster 47/cycle 18. This genuine list has 69 distinct
targets, starts at `$4600`, reaches `$0503` at clock 131462376 and `$F0B1` at
clock 131474919. Watchpoints were disabled only during declared navigation and
reenabled before the later dispatcher resume. The two genuine input states
must remain separate; the first list's simple mask/state results cannot seed
the later list.

Both pre-call-to-return intervals are 12,612 machine cycles. The owner wrote
the [first schedule](../../build/research/aloft-execution-20261109/capture-plan-01.json)
and [later schedule](../../build/research/aloft-execution-20261109/later-capture-plan-01.json)
before opening their corresponding post-call oracles. The source-derived cost
is outer JSR 6 + 200×63 + dispatcher RTS 6. This is a bounded original instruction
interval, not delivered FPS or a physical-silicon timing result.

The first sequence additionally brackets `INC $D011`: entry clock 130204374,
raster 48/cycle 6, and completion clock 130204380, cycle 12. The observed VIC state
changes from badline 1/display to badline 0/display while retaining RC 7. At the
first return, VC 10/VMLI 10 agree with the independently frozen conditional
fetch expectation. Exact acceptance and the interval-wide fetch argument are
owned by the separate proofs below; equal endpoint caches alone are not a
cache-origin or lifetime theorem.

## Observer details that matter

Monitor checkpoint IDs are reused after deletion. Identify a checkpoint by
ID plus creation sequence, and track enable/disable intervals separately.
The original IRQ's `$F080: DEC $00` changes DDR from `$2F` to `$2E`; the ending
`INC $00` restores `$2F`. A fixed foreign DDR assertion is invalid, while strict
same-stop wire/VSF DDR and port readback equality remains necessary.

An execution breakpoint can stop before queued watch hooks are printed. The
next resume drains those earlier hooks with their earlier instruction clocks.
Loads and stores use separate queues; a read/modify/write produces a load and
two store hooks with the same completion clock. Neither that shared clock nor
load-before-store printing is the physical bus timing/order. Bound an INC
operand read using the preceding watched STY completion and INC completion;
reject any raster-MSB domain spanning the 255/256 boundary.

The final two snapshots stop at PC`$01AC`, clocks131478986 and131479049,
raster 0/cycle 2 and raster 1/cycle 2. They are 63 cycles apart in the same field.
They retain the same preceding field's normal viewport; they are not two
different animation generations. Raw VIC drawbuffer data remains a future
comparison oracle until its schema, lifetime and independent pixel model are
separately bound.

The later [passive viewport probe](../../build/research/aloft-execution-20261109/viewport-probe-01/viewport-probe.json)
uses the frozen extended reader plus the actual normal-border resource query.
Both extracted 384×272 normal viewports, raster rows 16–287, are byte-identical:
104,448 indices each, SHA-256
`841e9d323e9b60dfa0faaead5c8be99ca6af81e572858128ca62163aa2ff0906`.
These are two retained observations of one preceding field, available as
future oracles. The probe does not predict their pixels, establish full 312-row
allocation freshness or measure animation cadence. Its
[source](../../research/aloft-execution-20261109/viewport_probe.py) launches no
process and advances no CPU, VIC or pixel pipeline.

## Continue from accepted boundaries

Read the [native ABI/custody](aloft-execution-native-20261109.md),
[typed execution model](aloft-cell-execution-20261109.md) and
[source-only fetch contract](aloft-fetch-contract-20261109.md), followed by the
[actual logical-fetch binding](aloft-fetch-binding-20261109.md). Their final
receipts define what is accepted; the original plans and raw observations
above do not silently upgrade pending results.

Keep genuine pre-`$0500` ZP/port/lookup/code/call-list inputs separate from
ordered hook and endpoint oracles. Preserve unknown indirect-CMP values and
flags. Recognized cells and a JSR/RTS-only dispatcher can support a finite
write-set argument; endpoint code equality alone cannot exclude a transient
writer. State the external NMI/RAM-writing DMA assumptions explicitly.

The completed typed model matches all 800 direct glyph store values and all
1,350 reported hook operations/PCs/addresses in each complete chain. It also
matches all forty final glyph bytes, both zero-page representations, return
registers and stored `$D011` at the first-cell and whole-chain endpoints.
The first full chain changes four glyph slots; the later chain changes 38.
The 25 literal `$D011` STA values per chain are observed directly. INC bus
values are source-derived; post-INC N/Z and preserved A/X/Y are independent
comparison evidence, not operand-read inputs.

The separate logical-fetch binding now covers early activation/cancellation
over all 200 lines of both captured chains. Under its explicit source closure,
each interval requests 8,000 logical row 7 graphics fetches and no matrix/cache
fetches. Four independently predicted return counter/cache states match.
The changes are conservatively bounded between same-line cycles 6 and 12;
they are not assigned exact physical bus-access timestamps.

Next bind physical bank/ROM/cartridge mapping and returned glyph bytes. Derive
the displayed multicolor values from predicted glyph stores, source-bound
logical fetches and genuine initial palette/border inputs, then compare the
retained committed viewport. Cache fetch origin, the named layered scene,
arbitrary fields and delivered animation cadence remain distinct work. No new
emulator launch is required merely to replay these retained inputs.
