# The three profiled Gouraud images are correct

All three cost-profile frames match the frozen independent scalar reference:
**24,000 bitmap bytes**, **3,072 Screen RAM bytes** and **3,072 physical Color
RAM bytes**, with zero differences. Every span has its actual CPU stack and
parameter dumps checked. The third render reuses buffer B: its starting image
equals the first completed B image, then all 1,932 nonzero bytes are cleared
before the third drawing pass. This verifies the captured clear outcome,
without claiming that the entire dirty-tracking algorithm is proved.

The producer is [`research/3dvibe64-profile/check_pixels.py`](../../research/3dvibe64-profile/check_pixels.py).
Its receipt is
`build/research/3dvibe64-profile/pixel-analysis/profile-pixels-proof.json`.
Native cost attribution belongs to the separate profile producer. The
[cost hypotheses](3dvibe64-cost-hypotheses.md) remain source-based hypotheses,
not substitutes for measured exclusive function costs.

## Closed inputs and unchanged reference

The accepted case is `build/research/3dvibe64-profile/native-01`, 29 files and
14,444,407 bytes, directory SHA-256:
`13bfd23f30bf0b7a2db7a9e8dc4ceb8dc69e77d81c76862fe9b372a1f23ef714`.
Its program remains the same 49,711-byte PRG:
`69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb`.
All 49,709 loaded bytes match the natural `$080D` start snapshot.

The declared startup is generated-PRG autostart mode 1 loader injection. It is
not an original disk loading witness. There are no subsequent manual CPU,
register or RAM patches, no snapshot restores and no interrupted resumes.
The single owned process is closed and reaped. The frozen raw-wire auditor
checks all 153 serialized commands, with only its explicit autostart metadata
adapted. Eleven RAM/VSF pairs compare **720,896 RAM bytes**, CPU clock/registers,
ports and beam positions.

Three read-only query failures remain retained: unquoted `resourceget Speed`
and `resourceget WarpMode` fail syntax, and quoted `"WarpMode"` is an unknown
resource. Successful quoted Speed queries report 100. `InitialWarpMode` is
retained as a startup resource and is not treated as a runtime warp query.
No host elapsed-time FPS inference is made.

The checker imports the pinned
[`research/3dvibe64-native/pixels.py`](../../research/3dvibe64-native/pixels.py),
SHA-256 `859e1ece975ea57c283cf0c4dcef47be95cf91c72d8d9eba29cd4765da8e16a2`,
without calling its `main()`. Its scalar, Bayer, pixel-address, palette and PNG
functions remain unchanged; only their output root is redirected to this
new `pixel-analysis/`. The old producer, old proof, scene and all frozen files
stay intact. The [original pixel note](3dvibe64-native-pixels.md) describes the
scalar arithmetic and its earlier committed-VIC sample.

## The larger trace payload is checked explicitly

This profile attaches three read-only displays at span entry `$A000`:

```text
m 0100 01ff; m 000b 002f; m b43b b441
```

The new parser permits exactly **300 unique addresses** per span: the full
256-byte stack plus the same 37-byte zero-page and seven-byte span ABI ranges.
It segments against every trace header, so stack dumps attached to other
profile anchors cannot accidentally become span data. Each A000 event must
have all three complete displays, valid coordinates/shades and actual row
pointers for the selected buffer.

The two saved bytes above the actual CPU stack pointer must decode to `$957C`,
hence RTS target `$957D`, for every span. The pinned PRG independently contains
`JSR $A000` at `$957A`. This binds the measured span entry to the accepted
Gouraud caller, without emulating CPU execution or deriving an image from
function timing.

The three bounded span streams are resume responses **98, 119 and 140**.
Their baselines stop at `$1153`, after the actual clear/shade update, and their
completions stop at `$08D4`. Each frame also has an earlier `$08CB` preclear
begin capture. A fourth begin capture retains the next continuation.

## Three independently replayed completed buffers

| Result | First | Second | Third |
|---|---:|---:|---:|
| Draw buffer | B | A | B |
| Actual spans | 168 | 159 | 203 |
| Logical pixel writes, including overlap | 3,780 | 2,656 | 2,666 |
| Unique logical pixels | 3,611 | 2,569 | 2,273 |
| Sampled shade range | 2..32 | 2..32 | 2..32 |
| Bitmap / Screen / Color RAM differences | **0 / 0 / 0** | **0 / 0 / 0** | **0 / 0 / 0** |

These compare the entire 8,000-byte target bitmap and both 1,024-byte palette
arrays per frame. Uncovered pixels start from captured baseline memory;
inclusive endpoints, signed rational shade interpolation, screen-fixed Bayer
phase, partial-byte neighbors and duplicated physical rows all retain the
previously accepted scalar contract. The fixed material is `$BF/$01`.

The same meaningful wrong references fail in every frame:

| Wrong model: differing bitmap bytes | First | Second | Third |
|---|---:|---:|---:|
| Hold the start shade | 1,044 | 908 | 860 |
| Floor the negative signed increment | 180 | 210 | 228 |
| Shift Bayer Y by one | 1,786 | 1,222 | 1,078 |
| Omit the duplicated physical row | 966 | 700 | 618 |

The previews are decoded completed bitmaps with the verified palette, not
new committed-VIC scanout comparisons:

- [First completed preview](/Users/rogerjohansson/git/asynkron/c64demo/build/research/3dvibe64-profile/pixel-analysis/first-preview.png)
- [Second completed preview](/Users/rogerjohansson/git/asynkron/c64demo/build/research/3dvibe64-profile/pixel-analysis/second-preview.png)
- [Third completed preview](/Users/rogerjohansson/git/asynkron/c64demo/build/research/3dvibe64-profile/pixel-analysis/third-preview.png)

## Reusing and clearing buffer B

The observed begin-buffer sequence is **B, A, B, A**. All 8,000 bytes of B in
`third-begin.bin` equal B in `first-complete.bin`, including **1,932 nonzero
bytes**. At `third-shades.bin`, the same B region is entirely zero before its
new spans execute. Replaying the third spans over the stale B image instead
of that cleared baseline gives **896 wrong bytes**. Thus clearing matters to
the actual accepted third image; the cost profile is not timing an untouched
or empty buffer.

This proves a finite before/after clearing result for this reuse. It does not
prove every dirty range, every individual clear store, other geometry, or the
absence of transient/redundant writes.

## Draw IDs are work identities, not a visibility theorem

The captured collector variable `faceidx=$0D` stays 8 in all 530 spans. It
cannot identify the active drawing face. However, emitted
`MODE4_FACE_ID_LATCH=1` also applies in this Mode 6 build, with source sharing
off. Its `mode4_current_face_id=$0C` is already inside the captured zero-page
range. That actual latch gives these contiguous span groups:

| Frame | Source-latched face ID : number of spans |
|---|---|
| First | `3:42, 2:42, 1:42, 0:42` |
| Second | `1:34, 2:48, 0:29, 3:48` |
| Third | `1:35, 7:45, 2:49, 0:25, 3:49` |

Third face 7 produces **45 nonempty spans, 203 pixel writes**, widths 1..8.
It is not merely an empty call. This independently identifies actual raster
work; it does not establish five correct physical visible faces of a convex
octahedron or a culling defect.

The source has conservative culling enabled, negative-area tolerances
`$20/$60` and sliver handling. Those are context, not a proved cause of the
additional work. The receipt retains raw completed `sx`, `sy`, `syQ2` and
lazy-projection validity flags. Some first/second entries were not projected
and can be stale. No independent projection/culling pipeline is added here,
and CPU Y after material setup is not substituted for the source face latch.

## Replay and limits

```sh
rtk proxy python3 research/3dvibe64-profile/check_pixels.py
```

Only the new profile `pixel-analysis/` artifacts are generated: the receipt,
checked producer, raw span records including stacks, reference bitmaps,
palette-index images and previews. No SDK, renderer, assembler, emulator or
downloaded executable runs. Native events and exclusive timing attribution
are handled by the separate profile producer.

The checker verifies the images belonging to those actual profiled inputs.
It does not prove geometry, clipping, culling, edge-shade construction or the
full illumination transform; it adds no committed-VIC crop or delivered FPS
claim. Further image-preserving experiments must retain these pixel checks
before interpreting any cycle saving. No optimization is made by this work.
