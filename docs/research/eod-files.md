# Edge of Disgrace: original disk files and the shader note

Research date: 8 November 2026. The three original release disks now have
bounded DOS/trackmo extraction and explicitly identified BB1 decoder
outputs. The original notefile's entire **ditheredvector** section matches
the retained NFO mirror after a stated character and whitespace conversion.
This binds the shader explanation to original release bytes; it does not
yet identify or validate the shader implementation.

The separate [original native boot acceptance](eod-native-boot.md) checks
the main payload. It must not be extended to every extracted stream.
See also [the earlier author-source research](stock-gouraud-sources.md).

## Original inputs and custody

The retained release ZIP has SHA-256
`21ec8560179a7ff4bf5c77b6102632f9a078aabddffea2f5534b304109ea353e`.
Its three 174,848-byte D64 members were extracted as data into
`build/research/eod/release/`. The producer pins each disk and the earlier
release/source receipts; it does not run an archive executable.

| Original disk | SHA-256 |
|---|---|
| `EdgeOfDisgrace_0.d64` | `ee9570df68c3ddd1fda60ea3360dd5880c2ac95ed110bbe1bd60fdb91dec3f61` |
| `EdgeOfDisgrace_1a.d64` | `0624697997c57209929fc36ff7121ec7c61760a88576edbf0768d63e77d28956` |
| `EdgeOfDisgrace_1b.d64` | `b348369ba5c7644019e4bf7f3cb8a5e81529b220e10b76dc5c0b7ad548310628` |

The decoder conventions were reviewed from J.B. Langston's
[demotools source](https://github.com/jblang/demotools/tree/08492ee030dfaa362912a4ee616a17130267b36a),
commit `08492ee030dfaa362912a4ee616a17130267b36a`.
The original files, retrieval metadata and commit response are retained in
`build/research/eod/tool-source/`. The new self-contained producer includes
the full MIT notice. It does not import or execute those downloaded files
or their `debooze` entrypoint.

Langston's README specifically names EOD's track-18/sector-6 index, while
explicitly leaving EOD's runtime equivalence unverified. This analysis adds
structural checks and a separate original-main comparison rather than
treating that README as proof of every output.

## DOS chains, indexed chains and aliases

The extractor enforces the original 35-track geometry, sector bounds,
acyclic chains and directory sector counts. It strips each sector's two
link bytes. A terminal link `00,N` contributes **N−1** payload bytes.
Raw PETSCII names remain recorded as bytes; generated filenames use numeric
slots rather than untrusted disk names.

| Disk | Actual DOS files | T18/S6 pairs | Headerless candidates |
|---|---:|---:|---:|
| 0 | 6 | 0 | 0 |
| 1a | 1 | 59 | 58 |
| 1b | 1 | 33 | 32 |

Disk 0 contains the main demo, notefile, soundtrack, HCB editor and two HCB
data files. Its T18/S6 is `00 FF` followed by zeros, not a valid trackmo
index. Directory-art DEL entries are recorded without interpreting their
dummy references as actual files.

Both scene-side indexes contain track/sector pairs followed only by zero
pairs. Their **last pair is T18/S2**, an exact alias of that side's four-sector
emergency DOS bootstrap. All four shared sectors are explicitly classified
as that alias. There are no other cross-file sector overlaps, and no file
chain overlaps directory/BAM/index metadata.

The final receipt retains 100 chain observations: eight DOS files plus 92
indexed entries. This includes two repeated bootstrap aliases. The two HCB
files have no recognized BB1 wrapper and remain explicitly raw files.

## Decoder result and its limits

The scalar preserves the format-specific initial bit byte, sentinel refill,
literal-to-copy mode carryover, `$FF` end marker and bytewise overlapping
backward copies. It rejects truncation, references to unwritten output and
64 KB output wrapping. It never fills undefined history with assumed zeros.
Stream consumption and unused tail bytes remain in the receipt.

The main disk-0 PRG is **32,864 bytes**, SHA-256
`d45e1474288f537841351bbf95cafbc6df2ecf50f3f86b0547352d7c67c9e724`.
Its normal wrapper uses stream offsets `$11C/$11D/$11F`, including the
initial two-byte PRG load address. Initial bit state is `$5E`, output begins
at `$0801`, and the stream consumes the complete file. The decoded PRG is
63,233 bytes; its **63,231 data bytes occupy `$0801..$FEFF`**. Decoded PRG
SHA-256 is
`3087048a4b95171955f57adcc455be06b858fa29e72cf7550ea3aae5c638795a`.
The separate native proof checks these data bytes against the original
unpacker handoff at `$0900`.

The soundtrack has an explicitly recognized original wrapper variant:
`JSR $73C7/NOP` replaces its initial port setup. Its candidate stream leaves
17 original trailing bytes. This difference is recorded, not silently
discarded as though every stream must finish at EOF.

**Side 1b index 3, T1/S16, requires further binding.** Its 302-sector chain
contains 76,610 bytes. Applying the headerless BB1 hypothesis to its leading
`FF FF FF` header produces destination `$FFFF`, an immediate end marker,
**zero output data bytes**, and 76,604 unused bytes. The retained two-byte
`trackmo-003.rejected-empty.prg` is therefore uninformative; it is not an accepted packed
payload or evidence that the whole chain has been decoded. The producer's
passing structural checks do not accept every headerless format hypothesis.
`rejected_hypotheses` records this explicit rejection. Raw bytes, chain and
this anomalous result remain available.

The other **89 headerless candidates** produce nonempty bounded outputs.
These remain decoder results pending original loader/runtime comparisons.
There is no silent raw fallback following a decoder error, no native shader
claim, and no inference that all candidates are runnable standalone parts.

## Original notefile versus the NFO mirror

[Dane's original production note](https://csdb.dk/release/?id=72550&show=notes)
directs readers to disk 0's notefile. DOS slot 5, `NOTE OF DISGRACE`, is
14,655 packed bytes. Its decoded PRG is **40,962 bytes**, data destination
`$0800`, SHA-256
`c7bc8c058664e0723feb3cd0ce9ca210fa521c0cd2c3ce446b0d1ef25449ed6a`.

The note does not contain the mirror as a contiguous ASCII byte string.
The original shader section occupies **`$5B48..$62F7`**, 1,968 bytes, ending
before `ab-zoom:`. Its characters are all `$01..$1A` or `$20..$3F`. The
comparison declares its translation explicitly:

- `$01..$1A` becomes ASCII `a..z`.
- `$20..$3F` stays unchanged.
- Remove only ASCII space, tab, CR and LF from both section texts.

All **1,440 remaining bytes** match the independently retained mirror
section exactly. Punctuation, letter case and order are preserved. The
normalized SHA-256 is
`82813d977e4c628d0d44fc701731db2913a705491f8630c2a94ff426a29da24e`.
The receipt retains original section bytes, translated text and normalized
text. Whole-notefile equality, font/rendering equivalence and native
execution of the note are not claimed.

This strengthens the custody of HCL's existing statements about a
16-bit/perspective shader, four colors, thirteen dither levels and avoiding
zero plots in thin tracing lines. Those remain **author algorithm claims**
until the actual shader and its inputs are bound. It does not derive a new
three-of-four skipping algorithm from the prose.

## Replay and next step

```sh
rtk proxy python3 research/eod/extract.py --output build/research/eod/file-analysis/fresh-replay
```

Choose a fresh output directory. Final passive acceptance is
`build/research/eod/file-analysis/accepted-03/file-proof.json`,
**438,361 bytes**, SHA-256
`fb8e819f854fd500acb34ea023508a9966f95914f38e1c6de0db77e3f2381db9`.
The producer is **19,137 bytes**, SHA-256
`3d64cdd4ec2671a9b70126448a75db0802fcc84815558287f931fbea78284094`.
It emits 203 files totaling 1,748,655 bytes, including raw/decoded candidates,
the checked producer and receipt. `accepted-01` preserves the earlier
ASCII-only note observation. `accepted-02` retains the subsequent section
comparison. `accepted-03` supersedes its global decode classification by
explicitly rejecting the empty headerless candidate; unchanged main-payload
bytes remain usable by the separately pinned native proof. A fresh
self-replay reproduces all 203 final files byte for byte. Root independently
reproduced all 203 final outputs exactly; `file-analysis/root-replay-check.json`
records that comparison (837 bytes, SHA-256
`34d34b64857db9f9ab23ef6273801ac86cf8fc21fa33074fe0a3112392b90912`).
Static peer review found no material issue in the decoder, chain checks and
section comparison.

Continue by identifying the original ditheredvector/Gouraud part in the
side-1a/1b chain sequence and binding loaded code to its corresponding raw
and decoded candidates. Resolve the T1/S16 special chain explicitly. Then
inspect real edge, shade-transition and tracing-line instructions before
making pixel, skipping, timing or performance claims. No product renderer,
unrelated textured-cube work or prior frozen evidence is changed here.

One static lead for that next task is side-1a candidates 51/52: their
decoded ranges are contiguous (`$0800..$30DC` and `$30DD..$65FF`), and the
second begins with a jump to `$310F`. This is a code/data localization lead,
not an identified shader or proof that index order equals runtime scene
order.
