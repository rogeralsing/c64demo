# No Bounds: original-release binding for SpriteFPP

The original **No Bounds (2023)** disk's SpriteFPP bundle independently
decodes to the published production Link artifact: all **20,211 part bytes**
and its **50-byte DISK driver** match exactly. Of the earlier supplied
standalone PRG's 14,793 checked geometry bytes, **14,790 are defined by this
original bundle and match**, with no differences. Its three leading atlas
padding bytes at `$4000..$4002` are outside the original load and remain
unknown in this offline reconstruction. They have not been silently filled
with the standalone's zeros.

This is original-disk payload binding through byte-bound Sparkle data
semantics. It does not substitute the supplied standalone initializer for
the production initializer or establish native FPP scanout.

## Which disks are original

[Elder0010's project page](https://www.elder0010.com/projects/no-bounds/)
identifies Genesis Project's release at X on **3 June 2023** and links
[CSDb release 232957](https://csdb.dk/release/?id=232957). That release's
[NoBounds-GP.zip](https://csdb.dk/getinternalfile.php/246029/NoBounds-GP.zip)
is internal file **246029**, exposed through download-link ID **286167**.
The current linked ZIP has only two members:

| Original artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `NoBounds-GP.zip` | 312,201 | `d847bdf0c64ff9568854096596f5d9c4167023dd9270f6cde26365896fea8b1c` |
| `NoBounds-GP-Side1.d64` | 174,848 | `f603e03f94ed4df416584419a696e1832b0710308de8faf2d0179b0a7725fe70` |
| `NoBounds-GP-Side2.d64` | 174,848 | `c26dd9428f1ef2737921c2f153b63e1453d51706d886b044e4151cbdf83997f7` |

Both production disks from the author's published repository at commit
`965807c511e2025b5c5e1ffb2a6235a4efd6ae5b` were independently acquired and
are byte-identical to these ZIP members. This comparison binds those saved
repository disks to the release download; it does not claim a fresh source
build reproduces them.

The repository also includes per-part test disks. The separately retained
`NoBounds/D64/SpriteFPP.d64` is **not** either original side: its SHA-256 is
`56f289a7515f8d2225a6b9c07f1ae1c7028b68efc1b849e73737daf469ff60e5`.
Its script declares product ID `$9f33`, while the production script declares
`$9f32` and a two-sided sequence. The repository's many other part-specific
disks and its source-code ZIP are not used as original-release authority.
No alternative final/rebuild disk is silently substituted.

HTTP URLs, redirects, status, headers, acquisition times and exact bodies are
retained under ignored `build/research/no-bounds/original/`, including the
primary pages and immutable source comparisons. The receipt verifies every
saved body and each selected source file's immutable Git blob identity.

## Actual boot and loader binding

The original boot chain starts at **18/7** on both sides. Both contain the
same 834-byte PRG, SHA-256
`40cd90f462434ea395d1c03e09d5cb6336186ab2229e4889c4d3abb48a2816ea`.
It loads at `$0801`; BASIC `SYS2064` enters **`$0810`**. Side 1 also has a
separate ordinary DOS chain at 34/0, named `DEMO CREDITS /GP`; it is extracted
separately and is not mistaken for the boot chain.

The boot matches the retained canonical
[Sparkle Loader.prg](https://github.com/spartaomg/SparkleCPP/blob/427e8be5743e70e9ea206eeef49cb4c971b1cba3/Resources/Loader.prg)
in every byte except file offsets **261 and 264**, the configured RTS-entry
operands. They resolve to **`$ff40`**. This is an exact code comparison,
not a loader-name inference from the repository's mixed older Sparkle files.

The original's six raw drive-code sectors **18/11 through 18/16** also match
the pinned Sparkle **2.3.23.105** SD image in all **1,536 bytes** after its
documented product/version/interleave configuration. The checked original
drive version bytes are `$23,$01,$05`; the product is `$009f32`. There are
eight pre-configuration differences on side 1 and ten on side 2, all retained
individually in the receipt. The configured drive-image SHA-256 values are:

- Side 1: `c2f89e8d6e7d3abc146d75d6bf4813245a35ee4daf59986cbf4ef8b4c0e6dcd7`.
- Side 2: `d61a2dd0d8e430c03873f285ab449349317c32c5f9b5b6b3836401c5dc0e3ebf`.

The boot and SD binding permits reuse of the previously audited
[offline Sparkle decoder](../../research/anomaly/inspect_boot.py), pinned
here by SHA-256
`1ce2fc8725d7f6f693931ae527de34f1abd175451ef6a66c43d14ce6cfbe87bb`.
Its primary SL/SD/Packer source receipts are reverified before reuse.
Matching these code/resource bytes establishes the applicable data semantics,
not one uniquely identified host builder executable. No downloaded executable
is run.

The original bootstrap's resident-copy checkpoint is `$08b5`; the literal
copy installs 416 bytes at `$0160..$02ff`. Only 412 source bytes belong to the
834-byte boot PRG: the four source bytes `$0b41..$0b44` lie outside it. This
lane does not synthesize them, execute a KERNAL/drive probe or flatten hardware
responses into RAM. Resident `LoadNext` is `$0200`; the byte-bound offline
decode does not depend on guessed values for that native source tail.

## Original bundle 31

The production
[NoBoundsA.sls](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Main/Sparkle/NoBoundsA.sls)
expands to **45 groups**, including the streaming sub-script. The decoder
finds 46 distinct internal entries on original side 1, including its terminal
entry. The relevant source sequence is:

| Bundle | Declared work |
| ---: | --- |
| 26 | Fade from No Bounds. |
| 27 | Trailblazer. |
| 28 | Preload PlasmaVector assets. |
| 29 | PlasmaVector DISK and initial data. |
| 30 | Remaining PlasmaVector data and visibility data. |
| **31** | **SpriteFPP DISK plus three production part sections.** |
| 32 | Preload Parallax. |
| 33 | Parallax DISK. |

Bundle 31 starts at original **track 23, sector 9**, physical-order block
**435**, with bit pointer **232**. Its 26 disk blocks reconstruct four ranges:

| Original destination, inclusive | Payload bytes |
| --- | ---: |
| `$088f..$08c0` | 50-byte DISK driver |
| `$4003..$5102` | 4,352 |
| `$8000..$a43f` | 9,280 |
| `$ab00..$c4b2` | 6,579 |

All **20,211 part bytes** equal the corresponding explicit sections of the
published production
[Link/SpriteFPP/SpriteFPP.prg](https://github.com/RobertTroughton/C64Demo-PublicReleases/blob/965807c511e2025b5c5e1ffb2a6235a4efd6ae5b/NoBounds/Link/SpriteFPP/SpriteFPP.prg),
33,970 bytes, SHA-256
`397ab215391c900d39fcc1d5b8da93e9f7bd8b251fde78f5f0a190fb253388aa`.
The 50-byte driver also equals its published Link PRG exactly. The decoder
begins with wholly unknown RAM and accepts back-references only to bytes
already defined inside this bundle. It does not import a previous effect's
memory to make decoding succeed.

## Geometry-domain comparison with the supplied standalone

The earlier [prepared-geometry investigation](frontier-geometry-20261108.md)
used `Parts/SpriteFPP/SpriteFpp.prg`, a 48,386-byte standalone artifact with
SHA-256 `7aba9b129119ec31aa31d06e663ebaca0bf221247c71af532f3b529c4a359e1a`.
Its independently checked data/code domains compare as follows:

| Domain | Requested bytes | Original file-defined exact bytes | Unknown |
| --- | ---: | ---: | ---: |
| Atlas at `$4000` | 4,352 | 4,349 | 3 |
| Frame rows at `$ab00` | 5,824 | 5,824 | 0 |
| Frame tables at `$c200` | 224 | 224 | 0 |
| Pointer-update cells at `$802a` | 4,389 | 4,389 | 0 |
| Prefix at `$8026` | 4 | 4 | 0 |
| **Total** | **14,793** | **14,790** | **3** |

There are **zero differences among defined bytes**. The only unresolved
addresses are `$4000,$4001,$4002`: the production manifest starts loading at
`$4003`, while the supplied standalone includes zeros in those padding bytes.
Their values after the preceding PlasmaVector runtime are not established
by this bundle. The atlas's prepared strip payload begins at slot byte 3;
that source layout alone does not establish which offsets the original VIC
actually fetches.

The complete loaded production sections differ from the standalone at
**2,208 addresses outside these matched domains**. Every address/value pair
is retained. These are comparisons between supplied build variants, not
observed runtime patches. The production initializer and standalone wrapper
therefore must remain separate even though the prepared geometry domains
agree.

## Natural native checkpoints

The original production DISK entry is `$0890`. It waits for music counter
`$19fb`, then calls the true production initializer **`$c300`** at `$08a4`.
That initializer starts:

```text
c300: 2c 11 d0 10 fb 2c 11 d0 30 fb a9 fb 8d 11 d0
```

It returns at `$c36b` to `$08a7`, where the DISK script calls `$0809` to
preload Parallax while SpriteFPP runs. This is the original return-based
initializer, rather than the standalone's BASIC/SID/self-loop wrapper.

A natural `$c300` breakpoint should be qualified by the SpriteFPP kernel
signature at `$8026`; other parts can reuse the same entry address. Its
37-byte prefix/first-cell signature is:

```text
a0 ff a2 00 8c 17 d0 ad 00 07 8d f8 43 8d f9 43 8d fa 43
8d fb 43 8d fc 43 8d fd 43 8d fe 43 8d ff 43 8e 17 d0
```

That is Y=`$ff`, X=0, followed by a cell that sets `$d017`, loads the row's
`$0700` value, writes all eight sprite pointers, then resets `$d017` through
X. The 133 matched cells occupy `$802a..$914e`. Before initialization, a
native capture can compare every byte in the four decoded ranges and inspect
the three excluded padding bytes without redirecting PC or injecting data.

## Reproduction and limits

The producer uses **Python's standard library only**:

```sh
rtk proxy python3 research/no-bounds/inspect_original.py
```

It requires the retained acquisition/source archive and pinned audited decoder
inputs. Outputs under ignored `build/research/no-bounds/original-analysis/`
include `original-binding.json`, both boot chains, the secondary DOS chain,
the reconstructed bundle and a separate 65,536-byte known mask. Zero bytes
where that mask is clear are placeholders, not original RAM evidence.

No source assembler, downloaded host program, C64/drive CPU, emulator or
hardware was run in this lane. No native loader timing, drive margin,
initialization-state equality, complete displayed-frame reconstruction or
full-demo success is inferred from the offline decode.
