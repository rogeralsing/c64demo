# Aloft: original compressed bytes and retained part generations

Research date: 9 November 2026. This is a finite byte-association study, separate
from identifying the scene described as a moving three-layer pattern. A capture
alias, wrapper counter, logical decoded bundle and disk-directory selection are
different things. No arithmetic conversion between them is used here.

**All 23 declared native source windows now match at least one independently
predicted complete generation.** This includes the full previously declared
2,934-byte Kefrens source span, its later 8,190-byte relocation input, the
selected airline generator and all of its background/text/lookup inputs, and
the selected ribbon setup/IRQ/generator window. Every byte is known, marked as
physical-RAM payload and equal. These are bounded original-byte associations,
not new whole-renderer or scene-identity claims.

The [stream binding](aloft-stream-binding-20261109.md) independently establishes
the original bootstrap/loader association and the first two decoded returns.
The [part-localization study](aloft-parts-20261109.md) previously derived bounded
copies and generators from native-observed source bytes. This follow-on asks
which of those source windows can now be traced back to independently decoded
original packets. It does not replay any C64 instruction.

## Source predictions precede native comparisons

The unchanged [typed format decoder](../../research/aloft-decode-20261109/depacker.py)
starts with unknown RAM and receives only original source-derived packets. Its
strict all-side1 exploration is pinned by the 58,430-byte
[generation receipt](../../build/research/aloft-decode-20261109/stream-analysis/all-side1-exploration-01/all-side1-exploration.json),
SHA-256 `ffc37070df52d17beb032e521a51b3c6fc42b068ab170f471fdf5a8871a11409`.
It saves memory, known-byte masks, payload-written masks and fresh-write masks
at each complete logical return. Each saved state survives later overwrites as
its own immutable artifact.

The new [association producer](../../research/aloft-decode-20261109/effect_binding.py)
validates the source receipt and every listed source output before opening a
native RAM file. The native comparison is a late oracle operation. Neither
native memory nor a mismatch-derived patch mask enters the decoder, transport
or device model.

A positive association requires all of the following for every byte in a
declared contiguous window:

1. The source generation's known mask marks the full byte known.
2. Its payload-written mask identifies a decoded physical-RAM value, rather
   than an unrelated received packet byte or a device value.
3. Its predicted byte equals the retained native byte.

Every declared window is checked against every complete source generation.
Unknown bytes, matching subsets and a favorable later final-RAM state do not
substitute for those checks. No runtime patch is normalized away. The result
also records each window's fresh delta coverage; surviving bytes from earlier
bundles are not relabelled as newly loaded data.

The format buffer `$0300..$03FF` is a special mask domain. Each new received
packet clears its decoded-payload eligibility. Consequently the cumulative
payload mask is monotone outside that buffer, but a previous output there
cannot be counted as payload after packet replacement. The initial failed
checker precondition and its explanation are retained under
[strict-candidate-01](../../build/research/aloft-decode-20261109/effect-analysis/strict-candidate-01/failure.json);
no decoder prediction or native capture changed during that correction.

## Strict source boundary and early associations

The strict model completes logical bundles 0 through 21. It consumes 386 of
the 597 source packets and records 208,957 physical-RAM writes. Partial bundle
22 then writes literal bus values `$0C` to `$DBE8` and `$0F` to `$DBE7` in
I/O-visible mode `$35`. A following match needs an I/O read at `$DBE7`; the
RAM-only model stops rather than treating RAM under I/O as ColorRAM or
inventing a full device byte. Partial bundle 22 is excluded from complete-state
associations.

The first strict comparison establishes these exact selected windows:

| Native oracle | Complete byte window | Strict matching logical generations |
| --- | --- | --- |
| part01-entry | `$0890..$089E`, 15-byte wrapper | 20 |
| part01-entry | `$2C00..$2EFF`, 768-byte selected init/IRQ window | 20, 21 |
| part01-entry | `$7C00..$7FFF`, all 1,024 source glyph bytes | 19, 20, 21 |
| part02-entry | `$0890..$08A2`, 19-byte changed wrapper | 21 |
| part02-entry | `$6600..$67FF`, 512-byte selected source window | 21 |
| part03-entry | The same `$6600..$67FF` window | 21 |

Generation 20 matches all three selected part01 windows simultaneously. Its
fresh writes cover all 15 wrapper bytes and 739 of the 768 bytes in the code
window; the remaining code-window bytes are already decoded values. The glyph
input first matches after generation 19 and survives the next two returns.
Generation 21 matches the selected part02 wrapper and `$6600` window together.
The latter 512 bytes are unchanged between the retained part02 and part03
captures; their second match does not assert a fresh load at the second capture.

These windows include data and padding where stated. They are not recovered
resource lengths or full reachability graphs. The evidence identifies exact
original-byte generations supplying the selected native sources; it does not
prove which wrapper request returned every byte or that an original effect
has one bundle. The [previous drive/C64 binding](aloft-stream-binding-20261109.md)
owns the separate directory-selection evidence. `$088D` is application
bookkeeping, not a directory slot or a logical bundle index.

None of the strict completed states matches the full declared later Kefrens
source `$4800..$5375`, the later 8,190-byte relocation input, or the selected
airline and ribbon source windows. This negative result describes the strict
model's boundary, not absence of those bytes from the original demo.

## Separate low-nibble device extension

The [ColorRAM extension receipt](../../build/research/aloft-decode-20261109/color-analysis/accepted-01/color-stream-proof.json)
is 110,630 bytes, SHA-256
`44bbc6a94b22db33d81dc9f15178f1303a2db19fb22484292e0c6f894f00f4b2`.
Its [source model](../../research/aloft-decode-20261109/color_memory.py) wraps
the same frozen token decoder with a separate device-memory domain. Initial
RAM and device low bits remain unknown. A device write establishes only the
four stored ColorRAM bits; the high bits of a subsequent device read remain
unknown. Only a proven ColorRAM sink may discard those unknown bits. They do
not become arbitrary full-byte physical-RAM values or native oracle inputs.
The accepted source argument binds the actual resident copy/cache-control
instructions; this note consumes that separate proof rather than introducing
another decoder or device model.

Before opening native RAM, the association producer checks every output of
this pinned extension and independently verifies that all four RAM state/mask
files in its first 22 generations equal the strict prediction byte for byte.
The extension's device-low-bit files remain separate. This checker compares
only full, known physical-RAM bytes to its native windows; it does not use a
ColorRAM high nibble, native ColorRAM state, or RAM under I/O as a substitute.

The extended source prediction completes logical generations **0 through 42**
and consumes all **597** packets in the declared original-side1 plan. It stops
in attempted generation 43 on packet-plan exhaustion. The one physical-RAM
write after the last complete return is excluded. Neither exhaustion nor the
43 complete returns proves the original end of a side, a resource count,
actual disk rotation order or the number of effects.

## Later source associations

The following table gives the **first complete source generation** matching
each later window. The full receipt retains every matching generation, every
other state's unknown/mismatch counts, and fresh-write coverage. A first
match is not an inferred actual wrapper request or directory command.

| Retained native source/input | Complete byte window | First matching generation | Fresh bytes there |
| --- | --- | ---: | ---: |
| part04-entry init window | `$E000..$E0FF`, 256 bytes | 23 | 256 |
| part05-entry init/body/IRQ window | `$E000..$E17F`, 384 bytes | 23 | 384 |
| part05-entry selected wrapper | `$0890..$08BF`, 48 bytes | 24 | 48 |
| part06-entry wrapper | `$0890..$08DC`, 77 bytes | 25 | 77 |
| part06-entry declared Kefrens source | `$4800..$5375`, 2,934 bytes | 25 | 2,934 |
| part06-precopy relocation input | `$6000..$7FFD`, 8,190 bytes | 28 | 8,190 |
| part07-entry wrapper | `$0890..$08AC`, 29 bytes | 29 | 29 |
| part07-entry init/IRQ/copy window | `$8000..$83E3`, 996 bytes | 29 | 996 |
| part07-entry text-generator window | `$2000..$2173`, 372 bytes | 29 | 372 |
| part07-entry four text streams | `$3DB5..$3E8C`, 216 bytes | 29 | 216 |
| part07-entry glyph values | `$8800..$88FF`, 256 bytes | 29 | 256 |
| part07-entry glyph indices | `$8A00..$8AFF`, 256 bytes | 29 | 256 |
| part07-entry background input | `$9000..$9513`, 1,300 bytes | 29 | 1,300 |
| part08-entry call-kernel template | `$F817..$F82F`, 25 bytes | 30 | 25 |
| part08-entry wrapper | `$0890..$089D`, 14 bytes | 31 | 14 |
| part08-entry setup/IRQ/generator window | `$F000..$F83F`, 2,112 bytes | 31 | 1,085 |
| part09-entry wrapper only | `$0890..$0895`, 6 bytes | 33 | 6 |

The selected part06 wrapper and complete declared renderer source match
together in generations 25 through 28. The later loaded relocation input
matches generation 28; no post-relocation target bytes seed that association.
This closes the compressed-original-byte gap for the source span used by the
[separate Kefrens mechanism study](aloft-kefrens-20261109.md) and the original
input of the previously proven 8,190-byte relocation. It does not reclassify
the source span as an entire compressed resource, nor does it simulate the
renderer or the relocation instructions.

All seven selected part07 source/input windows match **together in generations
29 and 30**. They include the genuine 52-column background, four original text
streams, both complete lookup domains and the selected generator code. The
previously proven 11,000 copied screen bytes and 1,912 generated text bytes
therefore have original-packet-bound inputs. Neither those later native
outputs nor the later overwriting of `$9000` enters the source prediction.

The part08 template first matches in generation 30, while the selected
`$F000..$F83F` window first matches in generation 31. Only 1,085 of that
window's 2,112 bytes are freshly written at generation 31; 1,027 are surviving
known decoded values. The wrapper, window and template match together in
generations 31 and 32. This is why requiring every byte to be freshly written
by the same bundle, or calling the entire window a new resource, would be
incorrect. The original 25-byte input of the separately proven 601-byte
`$0500` call-kernel expansion is now bound without using its native output.

Part09 remains a six-byte wrapper association only. No renderer or visual
algorithm is inferred from that short window. The complete comparison also
retains persistent early matches beyond the strict boundary, rather than
pretending the first matching state is the only state containing those bytes.

## Native oracles and bounded conclusions

The oracle is the closed original side1 native case, pinned by its
[accepted custody proof](../../build/research/aloft-20261109/native-analysis/accepted-01/native-proof.json),
SHA-256 `02243d0cbae68edad8aa5a51aec9e22e9cfa4c52f918f1ba30db9e5226b19eb4`.
This association producer checks ten selected full 65,536-byte RAM exports
against their paired VSFs, strict CPU/memory snapshot layouts, saved PC/clock,
CPU registers and port context. It retains the original natural-stop sequence
and the custody proof's beam metadata, including any cycle-zero distinction.
Boot, wire, monitor-checkpoint and process custody remain with that separate
proof. New bootstrap captures from the stream-binding lane are not mixed into
the old case.

The source format simulation does not run the application or IRQ handlers
between loads. A matching selected source window validates those bytes at that
capture; it is not a theorem that all earlier decoded RAM remained unmodified.
The canonical source packet order also remains separate from an actual drive
rotation trace or a proof over all possible packet orders.

The named three-layer scene remains unbound. The distinct Kefrens, airline,
vertical-ribbon and later bobs observations keep their own source generations
and visual limits. There is no new committed-pixel, complete animation,
transfer waveform, hardware timing, FPS or optimization result in this note.

## Replay status

The [accepted association receipt](../../build/research/aloft-decode-20261109/effect-analysis/accepted-01/effect-binding-proof.json)
is 117,262 bytes, SHA-256
`882027ffe37e5651ec2c18ea7a3e511824d10f5d15da264c73b855fb6769c5ce`.
The producer is 29,957 bytes, SHA-256
`a8e88ef6ba235e33e6fd4e123e28845c180b153110d1864c83e8f4941a8665c6`.
A fresh [self replay](../../build/research/aloft-decode-20261109/effect-analysis/self-replay-check.json)
matches all four files / **2,915,862 bytes** exactly. Its 1,180-byte report has
SHA-256 `8d52f9c24f68bb28464329d9ba192e8901f88f4dd4e3f2283ab4adb7c898b7de`.

All strict candidates, the initial precondition failure and the first
ColorRAM-backed comparison remain under the new analysis scope. The producer
requires a fresh directory there:

```sh
rtk proxy python3 -B research/aloft-decode-20261109/effect_binding.py --output build/research/aloft-decode-20261109/effect-analysis/<fresh-directory>
```

Root read the complete final source and independently replayed all four files
/ **2,915,862 bytes** exactly. The [root report](../../build/research/aloft-decode-20261109/effect-analysis/root-replay-check.json)
is 3,061 bytes, SHA-256
`3bce05df2d9f36114fc169e168f6b1179582a2525fdd2f1c99aa04aabf5138f7`.
It independently confirms 23 full windows, ten native pairs and 43 completed
source generations. The producer and accepted outputs are frozen.

A concrete next source question is whether the original generation31
`$F47C` generator and its templates independently reproduce the generated
`$2000/$2023` cell variants in the part08 pre-body capture, including their
zero-page/lookup dependencies and runtime patches. That is separate from the
already matched 25-byte `$0500` call template, and from naming the unresolved
three-layer scene. No new native action or renderer expansion is performed
by this association lane.
