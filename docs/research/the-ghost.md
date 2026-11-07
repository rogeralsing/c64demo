# The Ghost: original disks, complete offline depacking and an idle-byte foothold

The original **The Ghost** release is now acquired and all **62 custom-loader
files** have been depacked with the release's own CPU routine. This gives a
concrete base for investigating its border effects. It does not establish
native display output or cycle-safe raster timing.

The [CSDb release](https://csdb.dk/release/?id=239394) identifies Fairlight and
Genesis Project, 10 February 2024, Fjälldata 2024; code is credited to Trident,
music to Fegolhuzz, graphics to Pal, redcrab and The Sarge. The release links
[the recording](https://www.youtube.com/watch?v=B54owm1mUuc).

## Primary author explanations

Trident's [production notes](https://csdb.dk/release/?id=239394&show=notes),
posted 3 December 2024, distinguish several mechanisms. The moving Fjälldata
logo and lower-border raindrops use ghostbyte shine-through; he explicitly
points to Orbit Untold for the method. Other passages use expanded sprites
under ghostbyte masks. The greetings stagger data-copy phases between scrolls
and precombine narrow glyphs into 16-pixel units. A dither effect alternates
three-cycle-offset lines although its updates have six-cycle granularity.
These are attributed explanations, not timings measured here.

His 6 April note links a longer
[making-of discussion beginning around 1:27:43](https://www.youtube.com/watch?v=ICAV27sdvxk&t=5263).
That video was discovered, not transcribed or independently checked in this
pass. No complete author-published demo source was found on the inspected
release routes or in the previously inspected Trident repository.

## Acquisition and exact identity

The web reader rejected the CSDb page as restricted. Ordinary HTTPS retrieval
through Python's standard library succeeded with HTTP 200 for both pages and
the linked original ZIP. That is an access-method difference, not a missing
release or an inferred mirror.

The exact binary route is
[the_ghost-flt_and_gp.zip](https://csdb.dk/getinternalfile.php/253352/the_ghost-flt_and_gp.zip).
The ZIP contains two D64 files and no source files.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Original ZIP | 155,348 | `3b11eb23bff844ee25092237c0809a353a97d97b1a5c5cc160b0631708613e53` |
| `the-ghost-a.d64` | 174,848 | `568373df6b4451fe1f591dea0e217aefff0c147cd8987a6382b4ced1c1c9ce0b` |
| `the-ghost-b.d64` | 174,848 | `19545727ff108d80c2b6aa51912235e919651383239438add178a48d82ab6c93` |
| Shared DOS bootstrap | 2,680 | `6feb3cfa5e6ae767d1e9a60c3d03b2d58fbb31a86843fdf8e0faa4d91fc7e1c4` |

`acquire.py` records URLs, timestamps, response metadata, bytes and hashes.
The pages, archive, extracted disks, original loader references, disassemblies
and derived binaries stay in ignored `build/research/the-ghost/`.

## The DOS directory is artwork, not the part inventory

Side A has 47 conventional PRG directory entries and side B has 29. Their
listed block counts are zero. Every entry on both sides follows the same
track-18 sector chain, sectors 2 through 12, yielding the identical bootstrap.
Thus counting directory rows as independent demo parts would be misleading.

The bootstrap loads at `$0801`. Its BASIC line contains `SYS2078`, entry
`$081E`, and a `BITNAX` label. The actual custom part directories are elsewhere.
These conclusions come from parsed disk bytes and linked DOS sectors, without
running DOS, a drive or an emulator.

## Bounded original bootstrap execution

The original bootstrap copies its depacker to `$0020..$011F`, stages packed
bytes near the top of RAM and self-modifies those original instructions as it
decompresses. It reaches `JMP $8A00` after **230,795 instructions** in the
existing py65 1.2.0 model. Execution stops before the first instruction there,
`BIT $D011`, which would enter a hardware raster wait.

The resulting RAM SHA-256 is
`28568e19e8f4df3c07e94af53aa048a3951fec279039111dc4f86e58f08065ee`.
The last original instructions restore the processor-port latch with
`DEC $01`, enable interrupts with `CLI`, then perform the transfer. No IRQ
delivery is modeled. A guard found no hardware-visible I/O accesses during
this bounded bootstrap run.

Static inspection at `$8A00` finds a call to installer `$8000`, resident-code
copies, raster synchronization and a later jump to `$02D6`. The installer
contains KERNAL serial calls and drive-code upload; those paths are inspected
as bytes and are never executed in this pass.

## This release uses the older Bitfire directory format

The six-byte records in track 18, sectors 18/17, match the older layout in
[Bitbreaker's original writer](https://github.com/bboxy/bitfire/blob/092ea04e865db6d6193ecae48b81615d9ad52dd4/bitfire/d64write.c):

```text
start track, physical sector, load low, load high, size-minus-one low, size-minus-one high
```

The reference is pinned to `bboxy/bitfire` commit
`092ea04e865db6d6193ecae48b81615d9ad52dd4`, with Git blob and SHA-256 checks for
the writer, resident and drive sources. This identifies the format; it does
not claim that the complete released loader matches that commit byte for byte.

There are 42 slots per directory sector, fixed interleave 4, and full
256-byte payload sectors without CBM DOS links. Side A has **17 files**, all
in sector 18's table; side B has **45**, continuing into sector 17's table.
The disk-side markers are `$F0/$F1` at byte 255. Every start position, file
length, physical sector bound, absence of sector sharing and continuous
allocation order is checked independently. The packed payloads total
**166,513 bytes**, excluding supplied PRG load words.

This is deliberately a separate extractor. The later 63-entry, four-field
column layout used by the existing Next Round investigation would parse these
disks incorrectly.

## All 62 files return through the original plain-depack API

The installer literally maps `$8701..$8800` to `$0200..$02FF` and
`$87DA..$88D9` to `$02D9..$03D8`. Reproducing those copies yields the resident
depacker. Its plain API begins at `$02E1` and disables its page-refill loader
poll through its own original self-modification.

The host supplies the same absolute source-pointer operands that receiver
helper `$022A` normally writes: low bytes at `$02AF/$0324/$0387`, high bytes at
`$02B0/$0325/$0388`. No serial receive or drive routine runs. The processor-port
latch is `$34`, matching a RAM-under-I/O depack call; all memory remains an
explicit flat-RAM model.

All **62 calls return**, taking **7,816,276 CPU instructions** in total, and
produce **691,459 bytes** across their separate output ranges. Every read
requires previously loaded or written memory; none touches uninitialized
memory in the fixture. An independent audit checks each output's start and
end against its packed header, verifies its bytes/hash, and confirms one
contiguous destination range per file. Depending on the file, 0–9 trailing
packed bytes remain unread when the destination-end condition returns.

These sizes are cumulative across reused address spaces, not simultaneous
RAM occupancy. Processing directory order preserves earlier unpacked RAM
within a side, while each side starts independently. This proves a bounded
transformation of the acquired bytes, not the original scene-loading sequence,
live working state or hardware loader behavior.

The primary result is `depack.json`, SHA-256
`78edf06a29de7c671bdcf91ddbfe07460b4c447254aea0f5efbfbd9c2bf7950f`.
`output-inventory.tsv` and `release-map.json` give all file ranges and hashes.

## A bank-aware first-scene foothold

Side A raw file 0 depacks to `$0E00..$1CE1`; its startup calls the resident
loader and jumps to `$2000`. Raw file 1 produces exactly `$2000..$7FFF`,
24,576 bytes, payload SHA-256
`c8919472979de1c66abdd094aebaf8f73eec86c8c63072c1ad1c5ab8200a1828`.
The following anchors are verified in those original unpacked bytes:

| Instruction address | Operation |
|---|---|
| `$2098` | Reset path writes `$D016=$08`, `$DD00=$03`, `$D018=$14` |
| `$2108` | IRQ path writes `$DD00=$02`, `$D018=$80` |
| `$214B/$214E` | Load `$20B2`, then store it to `$7FFF` |
| `$2195/$2197` | Select `$D011=$3B`, with ECM clear |
| `$21ED/$21EF` | Write `$D011=$13`; following code sets `$D021=$0E` |
| `$2235/$2237` | Clear `$7FFF`; following code restores `$D011=$1B` |

With CIA2's low port bits configured as outputs by the installer,
`$DD00=$02` selects VIC bank `$4000`; its ordinary idle byte is **`$7FFF`**,
and `$D018=$80` selects screen memory `$6000`. Searching only for stores to
`$3FFF` would miss this path. The addresses in the table are instruction
locations, not raster-cycle numbers. No IRQ has been executed or visual scene
assigned from these anchors alone.

## Remaining boundary

The next useful step is to map one selected unpacked part to an original
runtime capture, then inspect the actual ghostbyte updates, sprite data,
priority, register order and VIC revision behavior. Neither the 2023 Trident
teaching example nor Nine's invalid-mode schedule has been byte-matched to
The Ghost. Their relationship remains author-attributed background in
[ghostbyte-shine-through.md](ghostbyte-shine-through.md).

No VICE, drive, renderer, application code, configuration or process was
modified or controlled in this pass.
