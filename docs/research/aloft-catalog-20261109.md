# Aloft: source-bound drive code and directory slots

The historical Sparkle primary source at commit **`f354e3b52c9361bf89ebad4f2f1d43504c213381`** independently reconstructs **all 1,536 original drive-code bytes on each of Aloft's three disks**, with zero mismatches. The same source's directory encoding and sector-order recurrence explain all **384 directory slots**. This establishes the disk-format implementation far more precisely than the earlier resident-only match.

These slots are drive state plus a stream pointer. They are not DOS files, decoded resources, or an effect list. No layered-pattern part is identified by this proof.

## Primary-source acquisition and generation

The [earlier loader proof](aloft-loader-20261109.md) showed that the original 416-byte resident matches a later Sparkle reference exactly. That did not establish the drive-side implementation. The follow-up retained the later reference's writer, packer and drive source, then inspected the original drive's source-defined version fields. The historical primary commit was located through the author's `sd.cpp` history before Aloft's release; its commit message is “251230 - drive init code update”.

The exact [historical writer](https://github.com/spartaomg/SparkleCPP/blob/f354e3b52c9361bf89ebad4f2f1d43504c213381/sparkle.cpp), [packer](https://github.com/spartaomg/SparkleCPP/blob/f354e3b52c9361bf89ebad4f2f1d43504c213381/packer.cpp), [drive source](https://github.com/spartaomg/SparkleCPP/blob/f354e3b52c9361bf89ebad4f2f1d43504c213381/resources/sd.asm) and [drive byte array](https://github.com/spartaomg/SparkleCPP/blob/f354e3b52c9361bf89ebad4f2f1d43504c213381/sd.cpp) were retrieved as data. The code was not compiled, evaluated or executed. Each GET has retained original/final URL, HTTP status, headers, UTC retrieval time, byte length and SHA-256. Each source body also matches its Git blob SHA-1 in the commit's retained recursive tree.

The [source directory](../../build/research/aloft-20261109/loader-analysis/catalog-source-02/) includes the tag query, bounded `sd.cpp` history query, tree, seven exact source bodies and all response metadata. The newer reference remains separately retained in `catalog-source-01`; it was not substituted for the historical drive code.

Sparkle's primary source is copyright 2019–2025 Sparta/OMG under the BSD 3-Clause License. The original [LICENSE](../../build/research/aloft-20261109/loader-analysis/catalog-source-02/LICENSE), its retrieval metadata and its commit-tree blob identity are retained alongside the source. The new script is a high-level reference of the named data transformations, not an invocation of the author's host program.

| Historical input | Bytes | SHA-256 |
|---|---:|---|
| `sparkle.cpp` | 236,047 | `270767bed77d894a468ff74c4bfd40ae707663db80713364193dff13ee6e64ee` |
| `packer.cpp` | 83,740 | `bb60128abbe2c5af5f3a1965f7ea66a5f4ef3bcb2523b2a8324758555bb32a6a` |
| `resources/sd.asm` | 53,137 | `7d6b673ff21f6efef523e04d9fb46a53eb05852d4a7182109365d33af684510a` |
| `sd.cpp` | 8,640 | `0e28b8eb743494fab9ad6f914f047d05f4b729c4cc000820267172951ef06537` |
| `loader.cpp` | 5,081 | `78649471dfd302500e0c0b8053869043879d87e0566a450f2eb2e7b041e1162d` |
| `resources/sl.asm` | 20,667 | `46b28b74e9d2528b808e0c3fd0df08ef0ce7537d4a143527932bee46d9dcab60` |

The original D64s and bootstrap PRGs come only from the [frozen disk custody](aloft-original-20261109.md), whose proof SHA-256 is `113eadc069fbf46bb1011d7c9373d175f4c3536950f7a7ee173f471b8f1eef84`.

## Independent drive construction

`InjectDriveCode` in historical `sparkle.cpp`, lines 5698–5864, declares a zero-initialized 1,536-byte host array and copies the 1,427-byte primary `sd` array into it. These zeros are an explicit source declaration; they are not assumed C64 or drive RAM contents.

The new pure reference function follows the source's data construction:

1. Save original block 3.
2. Patch version fields from the source constants `FullDate=20251230`, major 3/minor 3. Their BCD bytes are `$33,$25,$12,$30`.
3. Patch the three-byte product ID using decoded original BAM bytes `$F9/$F8/$F7`.
4. Move original blocks 4, 5 and saved 3 to output blocks 3, 4 and 5 respectively.
5. Patch output `$0360..$0364` using decoded original BAM inverse-interleave and next-side fields.

The predicted six blocks are then compared with original track 18/sectors 11–16. Those drive sectors are **comparison oracles only**. The only original disk inputs to construction are the declared BAM parameters; no expected drive instruction or differing byte is copied into the prediction.

| Side | Full bytes compared | Mismatches | Predicted drive SHA-256 |
|---|---:|---:|---|
| 1 | 1,536 | 0 | `e2c4e9e0a01b237bb72ca85747e77ba6ad5bc85687c1a0e430ab74e93fd62c10` |
| 2 | 1,536 | 0 | `dcb2d845e0ef53583b3b2dfe110087310d1966ac495ea1dc5a32a54316e050e2` |
| 3 | 1,536 | 0 | `aa248184cb8f9c476781628c8fd996719072d019d1d120b203635f9bf5fec012` |

All sides give product ID `$0A10F7` and interleaves **4,3,3,3** for the four speed zones. Source-domain side IDs are 0,2,4; next-side values are 2,4,`$FF`. These are stored-format values interpreted by the exact source, not evidence that every possible disk-change command was exercised.

The historical canonical C64 bootstrap is also 832 bytes. It matches **830/832 original PRG bytes** on every side: only the return-address immediates at `$08FA/$08FD` differ, configuring `$FDFF` instead of the reference's `$10AD`. Its SHA-256 is `0916330e9e7075a446559665572b94a875a8ff0f72472c3d25afc96659c789fa`. Together with the full drive match, this identifies an implementation compatible with the historical source. It still does not prove which exact host executable or build machine produced the release.

## Directory decoding and sector order

Historical `InjectDirBlocks`, lines 702–789, writes two raw 256-byte directory sectors at track 18/sectors 17–18. Each sector uses index order `[0,255,254,…,1]`; undoing it recovers 64 four-byte slots. There is no DOS track/sector link header in these directory sectors.

For the first three fields, `EORtransform` at lines 684–698 is:

```text
f(v) = v XOR $7F  when (v AND $09) is $00 or $09
       v XOR $76  otherwise
```

This function is its own inverse for all 256 input bytes; the producer checks the full byte domain. The fourth field remains unchanged. A decoded slot contains:

| Field | Meaning |
|---|---|
| 0 | Current track, with a separate plugin flag in applicable source paths. |
| 1 | First sector encountered after entering that track. |
| 2 | Number of sectors remaining on the track at this stream position. |
| 3 | Stream pointer used on the C64 side. |

Field 1 is **not the first sector of the bundle**. The producer independently implements `CalcTabs`, source lines 6079–6181, using the original BAM-derived interleaves. It tracks every sector visited, skips track 18, carries the sector cursor between tracks, and applies the source's wrap/decrement rule in **all four zones**. It produces the 664 ordinary data-sector positions for a 35-track D64. Each directory triplet must match exactly one generated track/start-sector/remaining-count state before a first block ordinal and actual track/sector are assigned.

Every slot on every original disk passes that association. Plugin-marked tracks are explicitly rejected rather than normalized; none occur here. Re-encoding all fields and reapplying the sector permutation reproduces all 512 original directory bytes per disk.

| Side | Slots decoded and associated | Distinct state-plus-pointer records |
|---|---:|---:|
| 1 | 128 | 44 |
| 2 | 128 | 29 |
| 3 | 128 | 40 |

The source can pad unused slots with prior/default values and assign alternate directory indices. Therefore **44/29/40 are not counts of resources, bundles, effects, or externally issued calls**. Each output slot preserves its actual numeric index, raw logical bytes, decoded fields and derived block ordinal. For example, side-1 slot 14 decodes to track 13, track-start sector 1, five sectors remaining, pointer `$FA`; its source-derived first block is ordinal 268 at track 13/sector 3.

## Replay and remaining work

Run the new producer into a fresh directory beneath the retained loader analysis scope:

```sh
rtk proxy python3 -B research/aloft-20261109/catalog.py \
  --output build/research/aloft-20261109/loader-analysis/catalog-new-replay
```

[catalog.py](../../research/aloft-20261109/catalog.py) is 14,962 bytes, SHA-256 `d7a0785fec84a3bfdd3d7eec1dadc16b40540dcaceaf0101bca4dee5ba4fd497`. The [accepted proof](../../build/research/aloft-20261109/loader-analysis/catalog-accepted-01/catalog-proof.json) is 13,617 bytes, SHA-256 `a8109b96af82701bf61af84e7b054e8fff8048b1efcfefe52c631e54ee88f2b4`. Its six data products are three predicted drive binaries and three complete slot catalogs; the checked producer copy is retained as well. A fresh self replay reproduces all eight files, **141,761 bytes**, exactly; see [catalog-self-replay-check.json](../../build/research/aloft-20261109/loader-analysis/catalog-self-replay-check.json).

The next bounded step is a typed format decoder driven by these source-derived first-block positions and the exact resident's literal/match rules. It must handle shared transition blocks, separate file/block/bundle terminators, I/O flags, destination wrapping and prior-memory match dependencies. It must establish resource ends from the grammar rather than distance to the next directory slot. Original native loaded RAM can validate a decoded resource, but cannot supply missing compressed bytes or unknown prior-memory values. No resource boundary, complete decoded effect, runtime lighting or layered-pattern algorithm is claimed by this catalog.
