# The Hat: original Dali streams and controller recovery

Research date: 8 November 2026. A typed bitstream/LZ model now reconstructs
eight selected original streams without prior-memory substitutions. The
first stream's **4,350 bytes at $0F00–$1FFD match the native-loaded RAM
exactly**. The larger late side-B candidate becomes concrete decoded
raster/sprite code, with a controller at $8000 and a raster transfer to
$2000. Its identity as the requested ending still needs the original
execution chain and display witness; a late file index is not that evidence.

## Source and original-byte contract

The model derives its grammar from Tobias Bindhammer's retained Bitfire/Dali
source at commit
[`5a3964b533656332c12cc0904f2ce92f44499c6f`](https://github.com/bboxy/bitfire/tree/5a3964b533656332c12cc0904f2ce92f44499c6f).
The relevant originals are
[`loader/resident.asm`](https://github.com/bboxy/bitfire/blob/5a3964b533656332c12cc0904f2ce92f44499c6f/loader/resident.asm)
and [`packer/dali/dzx0_dali.asm`](https://github.com/bboxy/bitfire/blob/5a3964b533656332c12cc0904f2ce92f44499c6f/packer/dali/dzx0_dali.asm).
Their complete original copyright/license notices remain in the retained
source; the receipt also includes the resident's notice with its source
fragments. This independent decoder does not execute that assembly.

Selected instructions in The Hat's actual installed resident agree with
the cited mechanics: refill at $0294, word extension at $02AD, destination
header at $02E4, new-distance assembly at $0328, literal copy at $0384,
repeat-length parsing at $0399 and match/in-place checks at $03BA–$03DC.
Exact opcode guards bind these rules to the captured generation. This is
not an assertion that every option or byte of the published loader equals
The Hat's configured resident.

The [disk extraction lane](the-hat-files.md) owns original ZIP/D64/raw-file
custody. This model consumes its pinned `accepted-02` streams and checks
their header, declared byte count and complete payload hash. It makes no
new disk-order assumption.

## The precise format, including its long-number exception

The raw PRG header supplies the packed load address. The first two payload
bytes supply the destination, low byte then high byte. Bit bytes and literal
bytes share one forward source cursor. Bits are consumed most significant
first. At the logical level, an interlaced number starts at 1: control 1
finishes it; control 0 consumes one payload bit and continues.

**Long values are not ordinary unbounded Elias integers.** In the original
resident, lines 336–340 save the first low eight payload bits when the
implicit leading 1 overflows the accumulator, then decode the high byte
separately. The typed model reproduces that byte-oriented extension. For
example, the late B17 stream supplies low $35 and high $02, giving **565**.
Applying ideal binary continuation to that same sequence is a different
format. The B17 input exercises six extensions, including 753, 1,031 and
3,387; A0's longest operation is only 188 and would not reveal this issue.

The block grammar is:

- Start with a literal run. After literals, a selector chooses a repeated
  distance or a new distance.
- A repeated distance uses the decoded number as its length; the initial
  distance is 1.
- For a new distance, decode `h`, then read raw byte `b`:
  `distance = ((h - 1) * 128 + floor(b / 2)) + 1`.
  `b & 1` is the already consumed first **length control** bit. The new
  match length is that decoded number plus 1.
- After a match, selector 0 means literals; selector 1 means a new distance.
  Copy bytes forward from `destination - distance`, allowing overlap.
- A new-distance number 256 is the source's EOF path. The accepted selected
  samples instead terminate at the original **post-match destination ==
  packed-source-cursor** boundary.

Every write is bounded, and the model rejects an output write that reaches
unconsumed packed input before the original in-place termination. Thus it
does not assume that copied values cannot alter future grammar without
checking the necessary non-overwrite condition. Matches must read original
packed-file bytes or bytes already computed by this model; unknown previous
RAM fails closed. An explicitly marked symbolic mode exists for investigation,
but no accepted case needs it.

The in-place boundary matters: the rest of the already loaded packed file
can be the final original output tail. The model retains those actual bytes,
not zeros and not fabricated additional decoding. B18's twelve-byte tail
contains real IRQ jump/acknowledge/return instructions.

## Eight bounded positive results

Ranges below are inclusive. “Tail” means original packed-file bytes beyond
the post-match stop; all other listed bytes were computed from the stream.

| Raw file | Recovered range | Bytes | Computed / tail | High-byte extensions |
|---|---|---:|---:|---:|
| A0, packed at $1673 | $0F00–$1FFD | 4,350 | 4,350 / 0 | 0 |
| A40, $3AC7 | $2000–$49FF | 10,752 | 10,752 / 0 | 2 |
| A41, $B303 | $5000–$CFFF | 32,768 | 32,768 / 0 | 8 |
| A42, $EC35 | $E000–$F763 | 5,988 | 5,985 / 3 | 1 |
| B0, $0FC3 | $0F00–$1006 | 263 | 262 / 1 | 0 |
| B16, $0874 | $0800–$0964 | 357 | 357 / 0 | 0 |
| B17, $71F3 | $2000–$8721 | 26,402 | 26,402 / 0 | 6 |
| B18, $F022 | $F000–$F0CA | 203 | 191 / 12 | 0 |

All eight decode strictly from unknown initial memory: zero prior-memory
reads and zero unknown output bytes. The A0 prediction then matches all
4,350 bytes of the separately pinned `first-loaded-ram.bin`. Repeating its
prediction with the captured entry RAM as declared context gives the same
target; the context is not required. Completed target bytes are never inputs.
Native lifecycle/capture acceptance belongs to the root's separate case audit.

The receipt retains two deliberately wrong ordinary-word controls. They
reject B17 and A42 rather than silently accepting guessed prior RAM. Earlier
failed candidate probes remain as intermediate artifacts; the first false
B17 prior-memory dependency disappeared when the source's long-number rule
was implemented. It is not evidence of a hidden required dictionary.

## Original controller and raster anchors

These are guarded bytes in the independently decoded original files,
not relocated standalone addresses or injected navigation code:

- **A40:** $283D and $2840 call $02D2 twice; $2848 jumps to $8800.
- **A41:** $883A calls initialization at $8863. **$883D loads #$F1 and
  $883F calls $020C**, returning at $8842. It writes CIA2 DDRA $3F, waits on
  `BIT $DD00`/`BPL`, then $8851 loads #2 and $8853 calls $02D4. It waits on
  $8860 and jumps to $0900 at $885B. This is the concrete side-change caller;
  A42 is a different decoded span of plot cells.
- **B0:** $0F3B calls $02D2 and $0F3E jumps to $E000.
- **B16:** $083D calls $02D2; after its flag wait, $0845 jumps to $8000.
- **B17:** $8000 begins raster-wait/setup code. $803A calls $804B, $803D
  calls $02D2, then a wait on $804A precedes $8045's jump to $0800.
  Its IRQ chain reaches $82CA and **$8317 jumps to raster code at $2000**;
  the later $831B handler restores the saved stack pointer. Consequently,
  the destination $2000 must not be mistaken for its main controller entry.
- **B17 consumer:** $205A loads the index at $3514, $205D reads $3680,Y,
  and $2060 writes sprite pointer $4BF8. Parallel cells use $3515–$351B
  and $4BF9–$4BFF. Repeated $D016 operations and `ROL $D013` occur in this
  raster code. These are concrete consumers, not a complete display model.
- **B18:** code initializes a small IRQ and restores conventional C64 state;
  $F095 onward calls KERNAL reset routines, then $F0A8 jumps through $A000.
  It is reset/outro code, not the recovered upscroller engine.

The B17 first bytes are a useful generation guard:
`A90E8D20D08D21D0A010ADCD814A6AAAA90020A001EA0480A9078D16D0`.
Its decoded output SHA-256 is
`fb41ff61943ba509b4cae952b50f48643006550633a0a181603565834aecaa72`.
Neither that signature nor the file's position alone establishes that it
is the named final all-border upscroller. No scroll text, font-image equality,
full VIC mode, committed pixels or effect timing is inferred here.

## Passive reproduction

```sh
rtk proxy python3 -B research/the-hat/dali.py \
  --output build/research/the-hat/dali-analysis/fresh-replay
```

The producer writes a compact summary, original-byte controller guards,
eight decoded data spans and their typed operation traces. It performs no
HTTP requests, CPU emulation, native/process control, build or product edit.
Current `accepted-03/dali-proof.json`: **29,837 bytes**, SHA-256
`1687a5b2323ec86881b53b226a5361ac88c6408720498cfd34cf7032b3ad940e`.
Producer: **16,504 bytes**, SHA-256
`7195f31a85f0dcac032c10b53a6cefcd48d2832d4edf14da0c331dfcf7412ee0`.
Fresh `replay-02` reproduces all **eighteen files / 2,201,336 bytes** exactly.
Earlier receipts and the path-dependent `replay-01` remain retained; the
final receipt records output names without embedding the output directory.
Independent root source review found no material issue in the stated typed
stream scope. Its fresh passive replay reproduces all eighteen files exactly,
without path normalization. The [2,962-byte root replay report](../../build/research/the-hat/dali-analysis/root-replay-check.json)
has SHA-256
`5528aca9ddac77675a5488c1c652a1514d0ecabc3780693ce458bcf4ba1863c2`.

The next boundary is original native/controller binding of the recovered
late code and its actual font/text/display inputs. This acceptance covers
the eight selected streams, not all sixty-two raw files or the complete demo.
