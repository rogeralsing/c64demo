# The Lab side two: extracted payload and a patterned span primitive

All 25 custom files on the original side-two disk have been extracted and
decoded with The Lab's own resident 6502 depacker. One decoded stage contains
a horizontal span renderer, a 16-material density palette, and sprite-shaped
destination addressing. Its isolated span operation passes 25,408 original-CPU
cases. Original native loading now confirms all 17,630 file-15 bytes before its
handoff. This note does not yet identify that span stage in a native screenshot
or establish its complete display configuration. A later multicolor bitmap
vector engine is a separate investigation.

The release and recovered author note are documented separately in
[The Lab research](the-lab.md). Brush credits Bitbreaker's span filling extended
with stencils for his border vectors. MMS describes a separate vector engine.
That attribution must not be assigned to a binary candidate merely because it
contains patterned polygons. [Original release and extras note](https://csdb.dk/release/?id=262146)

## Reproduce the extraction and CPU checks

`research/the-lab/inspect_side2.py` consumes the original ignored downloads and
uses py65 1.2.0. With the existing research environment:

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/the-lab/inspect_side2.py
```

Inputs remain under `build/research/the-lab/`:

| Input | Bytes | SHA-256 |
| --- | ---: | --- |
| `release/side2.d64` | 196,608 | `d34101d9b5852020ed56b3574aae854c7b16befff893df77a6d6ec08198cdf3b` |
| `side2-bootstrap.prg` | 2,510 | `a1d61674083c1c8f5b7e7532a0b6709ebdd897375ba26d23e0892042ebe25d78` |

The primary ZIP is [the-lab.zip](https://csdb.dk/getinternalfile.php/280582/the-lab.zip).
Extracted binaries, full RAM images, disassembly, and JSON receipts are ignored
under `build/research/the-lab/side2-analysis/`; no released assembly source is
copied into tracked files.

The checks execute the original bootstrap from `$080D` in flat RAM. It expands
the payload and reaches `$2000` after 79,841 instructions, before hardware
detection and loader installation. The CPU supplies the stable NMOS semantics
of `DCP zp`, `LAX zp`, and absolute `NOP` where required. It stops on an unsupported
instruction or visible I/O dependency instead of fabricating hardware behavior.
There is no VICE, IEC, drive, ROM, raster, or timing emulation in this procedure.

## Custom disk format and original depacker

The disk is a 40-track image. Its decorative DOS directory does not enumerate
the demo payload. The custom directory at track 18, sector 18 begins
`01 00 00 F1` and contains 25 records. The second directory sector is unused.
The four 63-byte stripes encode load low, load high minus one, and packed length
minus one. Data fills entire 256-byte sectors without DOS link bytes.

The sector walk uses interleave four on tracks 1–17, interleave three after
track 18, and skips track 18 for data. These interpretations come from the
[Bitfire disk writer at pinned commit 5a3964b](https://github.com/bboxy/bitfire/blob/5a3964b533656332c12cc0904f2ce92f44499c6f/d64write/d64write.c).
The Lab's 40-track image requires extending the geometry beyond the separate
Next Round extractor's 35-track guard; its fixed depacker offsets are also
different. The pinned source is a format reference, not proof that this release
uses an identical Bitfire build.

The extraction produces **178,926 packed payload bytes**. The script reproduces
the two literal resident-code copies made by the original installer, then calls
the installed plain-depack entry at `$02DE`. The original source pointer is
`$02/$03`, and destination pointer is `$05/$06`. All original depacker instructions
and self-modification execute; the hardware loader at `$0240` must never be
called during this plain-depack API check. Each file is supplied at its declared
packed load address, with RAM retained between files and resident code restored.

All 25 files return after **5,113,492 instructions** and write a total of
**455,996 distinct destination bytes per file, summed across files**. There are
no reads from an unknown back-reference source and no visible I/O accesses.
The resident `$0200..$03F8` slice has SHA-256
`5e696e396a934e5867e08eb970eacb95f776abc2a6ec90b824bafd5955d4b54b`.
These checks validate decoding in the stated RAM context; they do not validate
the on-disk transport or reproduce every preceding stage's runtime RAM changes.
The returned source pointer is internal bookkeeping, not a measured packed
stream-consumption counter.

The inventory is comprehensive for this directory. Addresses below are
inclusive; file numbers are decimal and zero based:

| Files | Observed depacker store ranges | Lead, without scene attribution |
| --- | --- | --- |
| 0 | `$0400–$1FF9` | Main sequence, IRQ/music entry points. |
| 1–4 | `$4000–$CFFF`, `$D000–$FF3F`, `$2600–$BFFF`, `$C000–$FDFF` | Initial stage and controller payloads. |
| 5–12 | Predominantly `$5600`; also `$7000` and `$6E00` | Multiple successive data/code payloads; not assigned from their load addresses alone. |
| 13–15 | `$7900–$BFC1`, `$6700–$78F6`, `$3420–$78FD` | Retained control/pattern tables plus the span candidate. |
| 16–18 | `$2600–$CFFF`, `$D000–$FF3F`, `$0600–$1A66` | Later controller and SID-style entry payload. |
| 19 | `$3000–$FF3F` | A tile/byte compositor is visible at `$3B00–$3C16`. |
| 20–24 | `$2000–$902F`, three payloads at `$8C00`, `$4940–$CF78` | Another engine and successive assets; stage identity remains open. |

`bitfire-files.json` records packed offsets, sector locations, lengths and
per-file hashes. `depacked-files.json` records observed output ranges, checksums
and CPU instruction counts. Sequential `.ram.bin` snapshots include retained
bytes from earlier files; an address outside the current file's written range
must be checked against its packed load as well as earlier payloads. In-place
depacking can leave an already-correct loaded tail unchanged: file 20 has eleven
such bytes at `$9030–$903A`, and file 23 has seven at `$C320–$C326`. These loaded
tail bytes are part of the logical payload even though the depacker does not
store them again. The [native MMS audit](the-lab-mms.md) uses them explicitly.

## Original native handoff

The original side-two bootstrap ran with its original disk attached in the
owned `build/research/the-lab/side2-live-01/` session. No PC, renderer, payload,
or sector was changed. Warp advanced the earlier stages and was disabled at
the original `$2A05 JSR $3420` handoff, stopwatch 148,462,290. At that point,
`$3420` contains `JMP $7C89` and the expected span entry bytes are present.

The raw capture `ram-progress-01.bin` matches **17,630 of 17,630 bytes** of the
decoded original `15-3420-78fd.prg`, with no exclusions. The receipt is
`file15-comparison.json`. This validates native load/transport for the candidate
in addition to the offline checks; the capture still shows a black transition,
not the user's green checker polygon.

A guard on the isolated `$59B0` entry did not stop the subsequent native run.
The stage can use other specialized paths, and the program later overwrote the
span code. That observation does not invalidate the isolated primitive, but it
means the exact active drawing path still needs to be matched at runtime.
The later saved frame belongs to the multicolor, speech-balloon sequence and
must not be attributed to this earlier span renderer. The original session
and restorable later snapshots are retained separately.

## Candidate span and pattern contract

The strongest span candidate is the sequential RAM snapshot after file 15,
SHA-256 `f8aa696e0483b48983a668476ccee4c8123fc0e57fde0a1f3618e8836fac2f1d`.
File 15 provides `$3420 JMP $7C89`; the controller at `$7C89` and the pattern
tables survive from file 13.

The isolated entry at `$59B0` accepts **X = left sample, A = right sample,
inclusive, Y = logical row**. The domain is 192 one-bit horizontal samples by
84 logical rows, represented by 24 byte columns. It builds endpoint masks,
loads a material byte for the row, maps the destination row, and jumps to
`$3651`. The independently checked operation is:

- A span in one byte ORs `pattern & leftMask & rightMask` into that byte.
- A split span ORs the masked pattern into the first and last bytes.
- Complete interior byte columns receive the pattern through direct stores.

This is a span renderer, not a boundary-marker/prefix-XOR filler. It can write
full interior bytes without reading them. Its boundary OR operation alone does
not provide opaque replacement of a previously painted polygon's zero pattern
bits; that would require coverage handling elsewhere. Stencils and full-scene
occlusion are not established by this isolated contract.

The implementation has the same partial-byte/interior-store architecture as
[Bitbreaker's span article](https://codebase64.net/doku.php?id=base:filling_the_vectors).
It is not claimed to be a byte-identical copy of the article's current inline
source. In particular, the article's dispatch instruction sequence is not a
signature found in this decoded candidate.

The 24 pointers use this offset for byte column `c` and logical row `y`:

```text
(c // 3) * 256 + (c % 3) + 64 * (y // 21) + 3 * (y % 21)
```

This is sprite-shaped storage: three columns per 256-byte block, four groups
of 21 rows, with sprite-padding bytes. It proves the data layout, not the
physical dimensions, sprite expansion, raster multiplexing, or final VIC mode.
The controller selects bases `$E0/$E8` and `$F0/$F8` for two such slices.

Materials use an 88-byte slot within paired pages:

```text
$8400 + (material // 2) * 256 + (material % 2) * 88 + phase
```

The callers choose phase 0 or 4. All 88 stored rows repeat every four rows, so
these two entry phases preserve the material pattern. Material 8 is the familiar
`$AA/$55` checker; sparse materials include `$88/$00/$22/$00`. The four-row
32-bit population counts are `0, 2, 4, …, 28, 32`: sixteen stored densities,
including black and solid. This is binary evidence of spatial density patterns,
not an inference from a scaled image.

`span-candidate-validation.json` records **25,408 cases** and **2,082,816 executed
original instructions**: all 18,528 possible inclusive horizontal spans at one
row/material, plus 6,880 cases across sprite-row boundaries, selected materials,
both phases, endpoint bit positions and lengths. The buffer begins with
nonzero data, so the oracle distinguishes OR at boundary bytes from replacement
of interior bytes. It compares every buffer byte to an independent address/mask
formula and stops before the original continuation at `$5B0D`.

This test does not cover the specialized fast chunks, every triangle edge
stepping case, runtime stencil construction, object transforms, or complete
frame behavior. The decoded `$3423–$3650` edge setup contains quotient/remainder
and error steppers; no BRR interpretation is needed for this primitive.

## Native handoff route to match next

The original bootstrap reaches `$2000`, installs the resident through `$3800`,
loads custom file 0 via `$02E6`, and jumps to `$0480`. The main eventually calls
`$2600` at `$04F0`. File 3 supplies `$2600 JMP $2609`; that controller's sequence
reaches **`$2A05 JSR $3420`** after its earlier payload loads. This is a useful
pre-candidate native breakpoint. Check `$3420 = 4C 89 7C` and the `$59B0` bytes
before interpreting the hit: these addresses also exist during earlier stages.

The `$7C89` controller calls pointer initialization at `$5901`, alternates buffer
selection and invokes triangle records through `$5A24`. Its counter is bounded
by `$8EB5` (164 in this snapshot). That is a lead for studying its input stream;
it does not yet prove whether these particular coordinates are transformed
live, prepared triangles, an animation, or a transition. The author's separate
claim about real-time vectors must await a matched runtime stage.

Record `$D011/$D016/$D018`, sprite registers and their raster changes during
that matched stage, then compare RAM around `$3420`, `$59B0`, `$7C89` and the
pattern pages to this snapshot. Matching the running screen and tracing the
triangle producer are the remaining steps before attributing these findings
to the green patterned image or the exploded-panel sequence.
