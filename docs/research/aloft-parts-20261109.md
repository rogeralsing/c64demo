# Aloft: finite loaded-part localization and source generation

Research date: 9 November 2026. This note distinguishes the loaded programs
encountered after the original inflight-menu orientation. It proves bounded
copy/table/template results from earlier source generations and compares later
RAM only after prediction. **The named three-layer moving pattern remains
unbound.** Similar part numbers, text-stream counts or a colorful screenshot
do not supply that association.

The [creator-content follow-up](aloft-primary-20261109.md) retains the separate
open mechanism questions. The [original disk study](aloft-original-20261109.md)
owns release identities. The source inputs here are native-observed loaded
RAM, not independently decompressed original effect payloads. Full original
boot, wire ordering, monitor/checkpoint generations, process closure and
input history belong to the root-owned custody producer, not this checker.

## Address reuse and software counters

`part01` through `part09` are capture aliases for observations in one natural
run. They are not asserted to be DOS filenames, standalone effects or original
bundle numbers. Byte `$088D` is observed separately from those aliases.

The common source routes are:

- `$0800`: increment the low clock byte, conditionally increment the high
  byte, then jump through the music route at `$0903`. The increment operands
  themselves are later patched; `$FE/$FF` is not a universal counter domain.
- `$0809`: `INC $088D`, then `JMP $021C` (the loaded sequential API).
- `$080F`: `STA $088D`, then `JMP $019C` (the separate indexed API route).

The same `$0890` address contains several different wrappers:

| Capture group | Observed `$088D` | Guarded source route |
| --- | --- | --- |
| part01-entry | `$14` | `JSR $2C00`, `JSR $2C30`, push return `$088F`, then jump through `$0809`. |
| part02-entry / part03-entry / part04-entry | `$15/$16/$17` | Wait on masked `$D020`; load, call `$6600`; load again, call `$E000`. Natural post-load PCs are `$089A/$08A0`. |
| part05-entry | `$18` | Test sixteen bytes at `$3000`; optionally call `$E000`; wait for `$FE/$FF >= $0DFA`; call `$E021`. |
| part06-entry / part06-precopy | `$19/$1C` | Call `$4800`; three sequential loads with handshakes; relocate a newly loaded asset; later clear its original location. |
| part07-entry | `$1D` | Call `$8000`; wait for `$FE/$FF >= $1502`; call `$8017`, then `$2000`; queue another load. |
| part08-entry | `$1F` | Call `$F000`; wait in the redirected `$FA/$FB` clock domain; call `$F02B`. |
| part09-entry | `$21` | Wrapper/source pin only. This lane does not analyze its renderer. |

The part05 table predicate computes `$F2 + floor(X/4)` for `X=0..15`:
four each of `$F2,$F3,$F4,$F5`. The `ALR #$FE` clears the carry used by the
following addition. Matching that initialization signature can skip the init;
it does not identify a visual effect.

Part01's init fills color destinations, copies `$7C00..$7FFF` to
`$2800..$2BFF`, and initializes `$FA/$FB` to `$0196`. `$2C30` arms an IRQ
route and returns. Sprite-pointer/position and raster-color work continues
in the IRQ; a wrapper return is not an entire-scene completion boundary.
Part02-entry still has zero bytes at `$E000`; using those bytes to classify
the later `$E000` call would confuse source generations. The part04 post-load
capture supplies that later code.

## Part06: exact relocation, handshakes and clear

This wrapper's renderer at `$4800` belongs to a separate mechanism study.
The wrapper calls the sequential loader at `$0893`, `$0898` and `$08A1`.
Byte `$11` advances load phases; the renderer supplies `$12/$13` handshakes.
There is no wrapper-owned drawing into `$6000`: this lane treats the newly
arrived bytes as an observed loaded asset until a separate original-stream
decoder binds them.

The natural before-copy stop is `$08A4`; after-copy is `$08C5`, before the
next `INC $11`. The source copy is:

| Source range, inclusive | Destination range, inclusive | Bytes |
| --- | --- | ---: |
| `$6000..$7EFF` | `$E000..$FEFF` | 31 × 256 = 7,936 |
| `$7F00..$7FFD` | `$FF00..$FFFD` | 254 |
| Combined | | **8,190** |

The tail's `X=$FE..1` intentionally leaves `$FFFE/$FFFF` untouched. The
independent prediction takes the genuine before-copy source span, then checks
all 8,190 destination bytes after the copy. They match exactly. The source
span is also unchanged at that boundary, and both vector bytes are preserved.

After the `$13` handshake, the `$08CB` loop clears **8,192 bytes** at
`$6000..$7FFF`. At natural `$08DD`, every byte is zero and all 8,190 relocated
bytes remain unchanged. This is a source-bound copy/clear equivalence, not an
observation of every actual write or of unrelated concurrently running IRQ
state. The full source guards and paired RAM identities are in the receipt.

## Part07: background generation precedes text reuse

The init at `$8000` calls `$836E`. Its source starts at `$9000` and has a
52-byte row stride. Eleven shifted windows copy forty bytes per row for
twenty-five rows. The destinations are:

```text
4400 4C00 5400 5C00 6400 6800 6C00 7000 7400 7800 7C00
```

For shift `s`, row `r` and column `c`, the scalar reference reads
`entry[9000 + 52*r + s + c]`. It predicts all **11,000 bytes** independently;
every byte equals the later `part07-armed` RAM. That state is at `$08AA`,
after `$8017` and before the `$2000` call.

`$2000` then expands four source character streams through the genuine
`$8A00` index and `$8800` glyph tables. Each character emits eight looked-up
rows plus one spacing row, followed by a final `$FF` terminator:

| Source text | Destination | Characters | Predicted bytes |
| --- | --- | ---: | ---: |
| `$3DB5` | `$9000` |53 |478 |
| `$3E21` | `$A000` |53 |478 |
| `$3DEB` | `$B000` |53 |478 |
| `$3E57` | `$C000` |53 |478 |

All **1,912 bytes** equal `part07-generated` at `$08AD`. The earlier `$9000`
background input is copied before this text generation overwrites that
address. Neither later text output nor later background screens are used as
prediction inputs.

Source `$8017` configures eight hi-res, Y-expanded sprites, with paired X
positions separated by four pixels. The IRQ chain changes sprite Y values
and pointer pairs at `$80BC/$816E/$81CF/$8239`, with `$828E` performing clock
and display-state updates. `$82C6` chooses scroll/D018 values and patches
pointer immediates. Initial `$D016=$18` and later low-bit-only `$D016`
writes belong to different phases; the body source uses `$D011=$5B`
(ECM set, bitmap mode clear). These are source routes, not a completed pixel
or whole-animation timing reconstruction. The root's visual orientation of
this captured program is distinct from the targeted checker-pattern scene.

## Part08: a different clock domain and generated call kernel

`$F000` copies `$FE/$FF` to `$FA/$FB`, then patches the operand bytes at
`$0801/$0805` to `$FA/$FB`. Its wrapper waits against `$16C2` in that domain.
The cleanup later copies the counter back and restores the original operands.
A report that reads only `$FE/$FF` throughout this part would use the wrong
generation of the clock.

The bounded call-kernel generator is `$F64E`; `$F43D` is setup, not that
generator. `$F64E` copies the 25-byte template at `$F817` twenty-five times
with a 24-byte destination stride. Each template has seven `JSR $2000`,
one `JSR $2023`, then `RTS`. The next template overwrites the preceding RTS,
leaving **200 calls and one final RTS**, spanning `$0500..$0758`.
All **601 independently predicted bytes** equal the later pre-body snapshot.

`$F02B` installs IRQ `$F080`, which calls `$0500`. The current `$2000/$2023`
cells use zero-page state and the `$0400` lookup, update character-selection
state, and distinguish an `INC $D011` normal path from a `$D011=$18` row-end
path. Other templates and runtime patches require more work. The observed
vertical-ribbon program does not yet establish which scene the discussion
calls the three-layer moving pattern. This note does not predict all cell values,
VIC fetches, dummy accesses, committed pixels or raster timing.

## Inputs, limits and replay

The checker pins **21 complete RAM/VSF pairs**. It checks all 65,536 physical
RAM bytes against each snapshot, strict MAINCPU 1.4/C64MEM 0.1 sizes, the
saved CPU PC/clock/SP, CPU-port context and PAL beam arithmetic. It uses the
already pinned snapshot reader and static instruction decoder; no C64
instruction is executed. Its selected-site listings are not a complete
reachability graph or dynamic instruction trace.

The [accepted source receipt](../../build/research/aloft-20261109/part-analysis/accepted-01/part-localization-proof.json)
is 35,948 bytes, SHA-256
`717eadcfc45d37accd79a272f80ffd1e4430c8ed8e68bb38fd20158cb84685c8`.
The [producer](../../research/aloft-20261109/part_localization.py) is 13,352
bytes, SHA-256
`71706d8eced71d1a33d27afa21c12cb32d6f2694a1f382498c91764eca3c6fc0`.
Its [fresh self-replay](../../build/research/aloft-20261109/part-analysis/self-replay-check.json)
matches all seven outputs / 84,284 bytes exactly; the 1,334-byte report SHA-256
is `8b7dc0894a7585911369cc8b2e2de276065c88ffb47098d8e5ba4a87dbb18bde`.
The initial successful candidate, diagnostic linear listings and candidate
source remain. Candidate01's receipt used an output-directory path; its
separate note explains the directory-independent correction before acceptance.
The diagnostic listings may cross data boundaries and are not formal control
flow evidence.

```sh
rtk proxy python3 -B research/aloft-20261109/part_localization.py --output build/research/aloft-20261109/part-analysis/<fresh-directory>
```

The broader research remains active. The next target boundary is an explicit
original instruction/data and visual association for the three-layer pattern,
not relabelling any of these already distinct loaded programs. No native
action, restore, CPU interpreter, downloaded host execution, FPS/optimization
or product change is performed by this lane.

Root read the complete producer and this note, then independently reproduced all seven outputs / **84,284 bytes** exactly. The [root report](../../build/research/aloft-20261109/part-analysis/root-replay-check.json) is 2,080 bytes, SHA-256 `9899b48368115802e1eaf3cf66c9e14753b88d4fa0744841ec67d835a1c6c74e`. The now accepted [closed original native custody](aloft-native-20261109.md) supplies the separate wire, boot-lineage and checkpoint/state association.
