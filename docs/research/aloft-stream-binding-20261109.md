# Aloft: independent native slot and stream association

Research date: 9 November 2026. Two original source-decoded bundles now match
clean return states in a fresh original-disk run. The first **493 payload
bytes** and the cumulative **5,977 payload bytes** are exact; packet-format
state is checked separately. Prediction starts with unknown RAM and receives
only original-source packets. Native output is an oracle, never a repair or
initial-memory seed.

This result does not identify the named three-layer moving pattern. The
earlier part06 Kefrens, part07 airline/text program, part08 vertical ribbons
and part09 bob/coin observations remain distinct. The
[previous localization](aloft-parts-20261109.md),
[source directory catalog](aloft-catalog-20261109.md) and original native
records are preserved unchanged.

## Separate the two native families

The old family is `build/research/aloft-20261109/native-01`: its frozen
[custody proof](../../build/research/aloft-20261109/native-analysis/accepted-01/native-proof.json)
contains **25 captures**. The fresh family is
`build/research/aloft-decode-20261109/native-01`: its separate
[closed custody proof](../../build/research/aloft-decode-20261109/native-analysis/accepted-01/native-proof.json)
contains **seven natural captures**. The same final directory name does not
make them one run. Their distinct manifests, process closures, raw journals
and source/checkpoint generations remain bound by their custody producers.

This checker pins both proofs and their producers. Each association retains
its RAM/VSF identity and the exact stop/register response sequences, raw byte
ranges and whole-journal references. It neither replays a native process nor
replaces the full custody audits. The old initial-SYS observation gap is not
silently filled by the new run.

The [fresh native detail](aloft-stream-native-20261109.md) and separate
[monitor-condition study](vice-condition-precedence-20261109.md) explain the
new startup observations and the earlier checkpoint issue. They add new
evidence without rewriting the old case.

## The drive RAM supplies an independent index anchor

The VSFs include `DRIVECPU0`; the old case did not retain C64 state alone.
The original VICE 3.10 writer defines DRIVECPU version 1.3 as:

| Payload section | Bytes |
| --- | ---: |
| CPU/register prefix |52 |
| Five old interrupt CLOCK fields |40 |
| 1541 RAM |2,048 |
| Three new interrupt DWORD fields |12 |
| Total |**2,152** |

Thus drive RAM starts at payload offset **92**. `DRIVE8` version 2.0 also
confirms true-drive operation and type 1541 at its exact type field. The
checker reads the retained official archive as data, checks the four extracted
source members byte for byte, and rejects other module versions/sizes/types.
It does not execute drive instructions or guess an offset by searching for
plausible RAM contents.

Historical Sparkle source at commit
`f354e3b52c9361bf89ebad4f2f1d43504c213381` binds a specific self-modified
instruction. The exact primary `sd` array uniquely places `DirLoop` at
`$05A5`, initially `LDA $0700,X`. `LoadStart` writes its low operand byte as
four times the directory index within a sector; `$5E` selects directory
sector 17 or 18. The cached directory lives at drive `$0700..$07FF`.

All **25 old captures** contain operand **`$0714`**, directory sector 17,
and a complete 256-byte cache uniquely matching original side 1. Therefore
the last drive-directory selection is **slot 5** (`$14 / 4`), while the
observed wrapper counter ranges from `$13` to `$22`.

This is a concrete reason not to equate `$088D` with a directory slot.
`LastT`, `LastS` and `SCtr` subsequently change as fetching progresses; their
current values must not be frozen as a start record. The persistent index
also does not count every sequential bundle or prove an explicit C64 command
at every capture. Drive bootstrap enters the same selector for slot 0 without
requiring a C64 `SendCmd` call.

## Pointer bytes have different storage domains

The source catalog correctly leaves the fourth directory field untransformed
on disk. However, the drive's GCR receive/cache path transforms **all** logical
directory bytes. The first three host-encoded fields thereby become numeric
drive fields; the fourth raw pointer becomes an encoded drive pointer. The
second transformation during transfer restores the raw C64 pointer.

| Selection | Disk/catalog raw pointer | Drive cached `$23` | Raw C64 domain |
| --- | --- | --- | --- |
| slot 0 | `$FE` | `$88` | `$FE` |
| slot 5 | `$3F` | `$40` | `$3F` |

The checker predicts all six possible directory-sector caches from the three
original disks before inspecting native RAM. Every loaded cache has exactly
one full-byte match. It compares the encoded pointer in the correct domain;
it does not mistake `$40` for a different original stream offset.

## Fresh first packet and source return are bound

The fresh run observes these actual source phases:

| Phase | PC | PAL machine clock |
| --- | --- | ---: |
| Receive entry | `$019F` |8,739,203 |
| First unconsumed packet | `$021C` |9,380,860 |
| First payload entry | `$FE00` |9,423,692 |
| Next original call | `$FE41` |9,434,894 |
| Next call returned | `$FE44` |10,036,048 |

At the first packet-ready stop, drive `DirLoop` selects `$0700`, its cache is
original side 1/directory sector 17, and its encoded pointer `$88` corresponds
to raw `$FE`. The saved C64 stack returns to `$FE00`. All **256 original-source
predicted packet bytes** equal the unconsumed `$0300..$03FF` native buffer.
Zero bytes at buffer offsets 0 and 1 are expected first-indexed drive patches;
they are not evidence that this packet was already consumed.

The [typed source decoder](../../build/research/aloft-decode-20261109/stream-analysis/accepted-01/stream-proof.json)
uses the frozen [transport model](../../build/research/aloft-decode-20261109/block-analysis/accepted-01/block-proof.json)
and declared original packet prefix. It starts with unknown RAM, rejects
unknown match dependencies, and supplies a separate decoded-write mask.
Bundle 0 writes exactly:

```text
0800..08DF   224 bytes
FE00..FF0C   269 bytes
```

All **493** bytes equal the native `$FE00` pre-execution capture. The later
256-byte packet-buffer state, including saved cursor `$2A`, also matches.
This gives **749 known bytes**, partitioned into decoded payload and format
state. The comparison does not count packet metadata as effect payload.

## The next call is sequential, not an assumed indexed request

The independently decoded original source at `$FE41` is `JSR $021C`, with
continuation `$FE44`. It is parameterless `LoadNext`, not `LoadA`. Between
the `$FE00` return and this call, the application does execute code.

The source main path writes five I/O registers and sets RAM `$08FF=0`.
That address was unknown in the first decoder mask; its native value is not
injected into the decoder. Separately, all **749 previously source-known
bytes** still match at the actual `$FE41` call boundary, including the entire
packet buffer. This is an endpoint invariant, not an absence-of-intermediate-
IRQ or hardware-write claim.

Continuing from its own derived state, the decoder consumes thirteen original
packets in the declared canonical order and emits 5,484 additional payload
bytes. All **5,977 cumulative payload bytes** equal the native `$FE44` return,
as do all **6,233 known bytes** when the final 256-byte format buffer is
included. Saved cursor `$12` independently agrees with native `$03FF`.

The source grammar and catalog provide precise logical equivalences:

| Source return | Source packet ordinal | Saved cursor | Directory-equivalent continuation |
| --- | ---: | --- | ---: |
| bundle 0 |1 | `$2A` |slot 1 |
| bundle 1 |12 | `$12` |slot 2 |

Each ordinal/pointer pair has exactly one matching side-1 directory record.
These are **logical continuation equivalences**, not claims that C64 issued
indexed commands 1 and 2. The drive's retained selector remains slot 0.
Likewise, the old `loadnext01` stop at `$021C` has a saved `$0890` continuation
and cursor `$33` inside a previously consumed packet. It is not an indexed
slot `$14` request merely because its wrapper counter is `$14`.

## Acceptance limits and replay

Only the first unconsumed packet is compared as a complete received packet.
The thirteen-packet canonical source order is not an observed rotational
transfer trace or a proof that every legal out-of-order schedule has the same
result. The two clean output boundaries establish finite byte equivalence.
Later decoder exploration and old middle-stream generations remain separate;
they are not promoted by the old slot-5 anchor or counter arithmetic.

No captured output or changed-address mask is supplied to prediction. Genuine
pre-call RAM could only become a separately declared initial context in a
different proof. This acceptance uses unknown initial memory and the decoder's
own earlier known state, with the application-boundary invariant checked
afterward. Neither old menu-state RAM nor fabricated zeros fill missing input.

The [binding producer](../../research/aloft-decode-20261109/native_binding.py)
is 26,342 bytes, SHA-256
`48510dcfd070f06db424fe91c2fe4e607c51ca8922340a26e1523d557d2406c0`.
The [accepted proof](../../build/research/aloft-decode-20261109/binding-analysis/accepted-01/native-binding-proof.json)
is 15,326 bytes, SHA-256
`60003d4a605b2891a385a31630ee752183c48f3002d577ac7c7f2a78fc07c06d`.
The [fresh self-replay](../../build/research/aloft-decode-20261109/binding-analysis/self-replay-check.json)
reproduces all four outputs / 182,969 bytes exactly. Its 858-byte report SHA-256
is `5c209013af6d355a0daef5ff9fec32960f182d1960c7f71daa6efea8de4b655a`.
Full independent root review found no material defect. The
[fresh root replay report](../../build/research/aloft-decode-20261109/binding-analysis/root-replay-check.json)
confirms all four files / 182,969 bytes exactly; it is 1,693 bytes, SHA-256
`7cc1c4c32d2c037ede7a8112143f394e1ca25cbf3098b03b1dd3dc862575a6b4`.
The initial catalog-schema lookup failure, checked source, old-state probe,
candidate and both preliminary native-comparison probes remain retained.

```sh
rtk proxy python3 -B research/aloft-decode-20261109/native_binding.py --output build/research/aloft-decode-20261109/binding-analysis/<fresh-directory>
```

This lane performs no native control, CPU interpretation, build, network
request or downloaded-host execution. The named three-layer pattern, complete
effect algorithms, physical IEC timing, committed pixels, animation/FPS and
product work remain outside these bounded results. The broad research stays
active.
