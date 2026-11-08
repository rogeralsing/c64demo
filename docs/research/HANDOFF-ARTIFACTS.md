# Handoff artifacts and exact restart inputs

Updated 8 November 2026. Research is active. The previous 203-entry inventory
is retained under `build/research/handoff-20261108/prior/`; the subsequent
327-entry inventory and Markdown are preserved under `prior-327/`.
The later 572-entry inventory, Markdown, checkpoint, follow-up and reading map
are preserved under `prior-572/`; its 572 identities were checked before
the current extension, with zero drift across 109,672,052 bytes.
The exact 773-entry inventory, Markdown and three handoff indexes are now
preserved under `prior-773/`; all 773 identities (137,507,596 bytes) passed
again with zero drift before this extension.
The full 990-entry manifest, Markdown and three handoff indexes are now
archived under `prior-990/`; all 990 identities were checked with zero drift
across 151,826,214 bytes before this extension.
The exact five handoff files, including the 1,072-entry inventory, are
preserved under `prior-1072/`; all 1,072 identities passed with zero drift across
159,043,825 bytes before this extension.
The exact five previous handoff files, including the 1,203-entry inventory,
are preserved under `prior-1203/`; all 1,203 identities and 39 receipt pins
passed with zero drift across 169,361,298 bytes before this extension.
The exact five prior handoff files, including the 1,304-entry inventory, are
archived under `prior-1304/`; all 1,304 identities and 43 receipt pins passed
with zero drift across 181,739,367 bytes before this extension.
The exact five prior handoff files, including the 1,413-entry inventory, are
archived under `prior-1413/`; all 1,413 identities and 49 receipt pins passed
with zero drift across 257,608,750 bytes before this extension.
The exact five previous handoff files, including the 1,517-entry inventory,
are archived under `prior-1517/`; all 1,517 identities and 56 receipt pins
passed with zero drift across 283,848,725 bytes before this extension.
The exact five baseline files, including the 1,611-entry inventory, are now
archived under `prior-1611/`; all 1,611 identities and 62 receipt pins passed
with zero drift across 286,236,648 bytes before this extension.
Read [CHECKPOINT](CHECKPOINT.md)
for all findings and [FOLLOW_UP](FOLLOW_UP.md) for the continuation prompt.
This index pins the newest batch; older investigations retain their own
detailed notes and proof chains in the [reading map](README.md).

## Preserve the evidence

The tracked [machine-readable inventory](HANDOFF-ARTIFACTS.json) contains
**2,332 unique artifact/helper identities and 68 receipts/reports**. It preserves
**all 1,611 previous identities and 62 receipt pins**, including earlier inventories.
The newest additions cover source-proven camera units, 12 new rendered poses,
the strict classifier's two retained image failures, a separate exact-projection
reference with primary HTML/text, and accepted replays. There was no new build,
product patch or measured saving. Static user-preview provenance is cosmetic;
the active preview journal remains excluded. Each entry records repository-
relative path, byte count and SHA-256. Hashes do not prove a broader runtime
question completed. Total retained artifact bytes: **337,972,520**.

`build/research/handoff-20261108/gouraud-camera-integrity.json` records the
compact preservation/hash check; `prior-1611-verification.json` records its
archive baseline. All 1,611 previous rows and 62 receipt pins are unchanged.
The inherited cache policy and current-index/bytecode exclusions are unchanged.
The old monitor helper
remains preserved as `handoff-20261108/used-vice-session.py`; the new
cancellable observer and its separate real-wire checks extend that history.

**Keep `/Users/rogerjohansson/git/asynkron/c64demo/build/research/`.** Original
downloads, acquisition indexes, RAM, snapshots, screenshots and large proof
outputs are ignored by Git and are separate from the tracked sources. A fresh
checkout needs those retained inputs to reproduce the checks and resume the
exact native state; the tracked scripts are not substitutes for that data.

## Latest accepted camera-plane negative experiment: 8 November 2026

| New receipt/report | Bytes | SHA-256 |
|---|---:|---|
| `build/research/3dvibe64-camera/source-analysis/units-proof.json` | 22,508 | `665e9233aafe5cc3e25e82b497549117a04f64f2a14fa5f0c335290970284551` |
| `build/research/3dvibe64-camera/analysis/accepted-02/camera-proof.json` | 353,239 | `6023d45cbf7a47ff4f74d61211df512d077cbd046d01537d2a83f05c3a7fa536` |
| `build/research/3dvibe64-camera/source-geometry-analysis/source-geometry-proof.json` | 30,040 | `57c2b2473caf72f073c5a369eb77b5f5d0e4a0bd11ed6efcbca664f0ce86ec46` |
| `build/research/3dvibe64-camera/root-replay-check.json` | 17,703 | `8b447cfaad88ad5bda1da53c6320ae93a0e84c86a2fa57c180826d48de4825d1` |

- [Units](3dvibe64-camera-units.md): 81 products, 18 vertices and 1,536 linked
  table bytes establish eye zero and the compensated +190 table bias.
- [Classifier](3dvibe64-camera.md): 12 consecutive rendered poses in a closed
  81-file / 30,912,553-byte case with 37 RAM/VSF pairs. All full scalar/native
  buffers pass, but strict removal changes 48/66 bitmap bytes and 96/144 pixels
  in poses 9/10. Both palettes stay equal. Candidate acceptance remains false.
- [Separate reference](backface-source-conventions.md): exact ideal projection
  on 120 triangles in 15 windows / 13 distinct clouds; retained primary HTML,
  text and retrieval receipts. This does not repair integer raster compatibility.
- Root replay matches all 106 classifier files / 3,780,076 bytes exactly; units
  and source-convention proofs also match. Intermediate analyses remain retained.
- New native endpoint: `native-01/pose-12-complete.vsf`, PC `$08D4`, clock
  10183653, raster 29 / raw cycle 18. Fresh generated-PRG autostart, no restore,
  new build, product patch or measured saving. Other native endpoints remain.
- The separate user-requested visible preview is intentionally left running.
  Mutable `preview-01/` is excluded from the inventory. Its static ownership
  record, wrapper and cosmetic screenshot are retained without research
  timing/pixel claims; the dated record does not prove current liveness.

Next isolate actual integer coverage/occlusion at the two counterexamples.
Preserve complete bitmap, both palettes and decoded-pixel regressions before
another rule. No fitted tolerance, hard-coded face skip or policy patch follows.

## Preceding accepted offline omission/policy/math: 8 November 2026

| New receipt/report | Bytes | SHA-256 |
|---|---:|---|
| `build/research/3dvibe64-overdraw/omission-analysis/accepted-01/omission-proof.json` | 27,195 | `e6e2fe1d2f952399333ec7340098ddcf95be2ee00966ce911ec5aa462cc712e9` |
| `build/research/3dvibe64-overdraw/cull-analysis/cull-proof.json` | 36,749 | `a8498b02b8a9c574694998af214d7b9f969292f409e1ca9b3f55e82cd23b0711` |
| `build/research/3dvibe64-overdraw/normal-plane-analysis/normal-plane-proof.json` | 6,202 | `298cb07ee13e08d8f7ab0605c1d86b5664294d3761eff6cc6a8dca9969abfcbe` |
| `build/research/3dvibe64-overdraw/root-replay-check.json` | 4,327 | `a6f01013bbb489a76237165a3c618a7ad6e8472ac69b9e0e76dedb0ee30243c5` |

- [Omission](3dvibe64-overdraw.md) tests all 64 subsets. First/second require
  all four groups; third uniquely has minimum `[2,0,3]`. Omitting either/both 1/7
  preserves all 8,000 bitmap bytes, both 1,024-byte palette arrays and 64,000
  decoded pixels. Removing both deletes 80 spans/339 input pixel writes only
  offline. Face 1 is required in earlier poses; no global ID rule follows.
- [SDK policy](3dvibe64-cull-policy.md): rotated-XY cross −17 passes active
  threshold −32 and actual depth/sliver checks; the −96 path is compiled out.
  Face 1/7 subtrees total 172,828 observed cycles (25.56%), not recoverable
  measured savings. This explains submission, not ideal physical visibility.
- [Separate normal-plane reading](normal-plane-culling.md) retains the PDF,
  text, retrieval record and all three page renders. Exact rational checks
  correct its printed +1 for the stated normal/vertices. The author’s 1991
  implementation remains attribution, not an executable or SDK finding.
- Accepted omission and two fresh replays match all 23 files exactly; cull and
  normal proofs also match. The root report retains its rejected outside-root
  argument before creation; no producer/input changed after that rejection.
  No build, native capture, product change or speed measurement occurred.

That proposed continuation is now the camera study above. The source units
are established, while strict removal fails two new image comparisons; no
hard-coded skips or SDK policy change follows.

## Preceding accepted Gouraud costs and three buffers: 8 November 2026


| New receipt/report | Bytes | SHA-256 |
|---|---:|---|
| `build/research/3dvibe64-profile/source-analysis/accepted-02/anchors.json` | 24,680 | `f61a80d70d90fe58b48c3f3f7109d58f62551d6d81aff4f71fde6f3aeb3c5937` |
| `build/research/3dvibe64-profile/profile-analysis/accepted-02/profile-proof.json` | 33,880 | `ebf994a2f7ed0a211cf98a2a112ea2d2b055de04a493484d238717736c42942a` |
| `build/research/3dvibe64-profile/hypothesis-analysis/cost-hypotheses.json` | 8,295 | `c2459730f4ecbf0efec6ebbc75204d7992236c4c6f11cc20942f661f7d589e99` |
| `build/research/3dvibe64-profile/pixel-analysis/profile-pixels-proof.json` | 50,301 | `a564dc770db6b02afc66607b259cd71971b9ef2810200c642fd5c4cae1cb2710` |
| `build/research/3dvibe64-profile/root-pixel-replay.json` | 4,106 | `46d2371537bde6dc6d5bd7f0435ba95de768a67a7487cec7fa2941751b2c4ca0` |

- [Native costs](3dvibe64-profile.md) use [linked PC/stack anchors](3dvibe64-profile-plan.md).
  Three renders cost 590,499 / 543,692 / 676,134 PAL machine cycles. Third-render
  exclusive shares: spans 38.41%, XY bounds 17.76%, shade edges 16.18%, row/dirty
  setup 9.20%, material 7.06%, clear 6.29%, rotation/lazy projection 2.12%,
  collection/culling 1.34%, lighting 1.03%, residual 0.60%. Actual uniform/general
  routes are 28/140,15/144,11/192 for 530 fully paired spans. IRQ/VIC time is
  included, inclusive helpers overlap, and no delivered-FPS result is claimed.
- [Three-buffer acceptance](3dvibe64-profile-pixels.md): all 24,000 bitmap and
  6,144 palette bytes match. First reused B has 1,932 nonzero bytes then becomes
  zero before drawing; omitting that clear gives 896 wrong bytes. This verifies
  a finite clearing outcome, not all dirty tracking or new committed-VIC scanout.
  `$0C` is the source face latch; `$0D` stays 8. Third groups 1/7/2/0/3 include
  face 7's 45 nonempty spans/203 writes, not five proved visible faces or a bug.
- Root source/native/hypothesis replays match. All 16 nonproof pixel outputs
  match exactly; JSON normalization is restricted to output-artifact prefixes
  and `reference_reuse.output_root_only_redirected`. The first comparison
  rejection omitted that bare field; the producer had already succeeded and
  was not rerun. Earlier source-plan path-formatting failures remain history;
  accepted source/native receipts are under `accepted-02`.
- [Cost hypotheses](3dvibe64-cost-hypotheses.md) use older two-sample inputs,
  not new measured savings. [1985 hires reading](hires-dither-1985.md) is a
  separate lead: FACET flat shading and front-view/no-rotation primitives
  provide no fast rotating-Gouraud result; HTML-body custody is absent.

The next task is a NEW offline omission replay on selected source-latched
span groups, comparing final bitmap/palette before changing culling policy.
Then choose exact edge/span work reduction if useful. Preserve the stock
baseline; no product speed fix, 50 Hz SDK claim or Pong change was made.

## Preceding authored Gouraud build/native baseline: 8 November 2026

| New receipt/report | Bytes | SHA-256 |
|---|---:|---|
| `build/research/3dvibe64-native/tool-analysis-02/toolchain-proof.json` | 11,485 | `0456515f35424be6f29fa5fdf651ed1a7c694d596e4a02bad8ccd662f7679093` |
| `build/research/3dvibe64-native/build-analysis/build-proof.json` | 18,801 | `4f051c805788c579f4ef6ecf0b96f067df916b7946944fdf926c34d8b14871fc` |
| `build/research/3dvibe64-native/pixel-analysis/pixel-proof.json` | 36,059 | `6f579e43f1585a2e338909ff77f5c99997ee8e0f793a7fd0ed23a7d3cc699c30` |
| `build/research/3dvibe64-native/root-pixel-replay.json` | 2,779 | `6aabbf85a6307fd78932e0c75870324b1cc47b3e112553ab01dc0c3d9124b02f` |

- [Toolchain](3dvibe64-toolchain.md): official local PowerShell 7.6.9 and
  compiled 64tass 1.60 r3243, four successful host command receipts, unchanged
  SDK and byte-identical symbol reassembly. Archives/catalogs cover 1,148
  extracted regular files. The partial first catalog/manual failure note
  is retained as rejected/nonreceipt history; accepted proof is tool-analysis-02.
- [Build](3dvibe64-build.md): authored smooth octahedron, PRG 49,711 bytes,
  57 tables / 1,011 bound bytes including 132 Bayer and 704 lighting bytes.
  Actual executables, commands, products, symbols and root replays are pinned;
  reconstructible DLLs, assembler source and staged SDK duplicates are not
  individually added to the inventory.
- [Native scalar/pixels](3dvibe64-native-pixels.md): seven exact RAM/VSF pairs
  (458,752 RAM bytes), all 49,709 startup payload bytes exact. Two 8,000-byte
  bitmaps and palette arrays match captured-input scalar sampling. Only
  sample 2 has publication and 64,000 committed visible-body pixels exact.
  First publication was missed after a rejected condition and interruption.
  Full geometry/clipping/culling/edge-shade/clearing/lighting-transform proof,
  borders, complete fields and delivered FPS remain open. The quadrilateral
  silhouette limit is explicit.
- Intervals 577,195/509,905 PAL-model cycles (0.5858/0.5175 seconds) are slow partial-loop
  work including projection/collection/drawing, IRQs and VIC stalls; earlier
  lighting/clearing and later presentation are excluded. No 50 FPS is claimed.
  Stock PAL/Speed=100/warp-off launch flags were requested; no runtime resource
  query was captured. PRG autostart mode 1 is declared loader injection, not a
  1541 original-disk startup witness.
- Tool/build replay bytes match. Pixel replay matches all 12 nonproof outputs
  exactly and JSON after only known output-artifact-prefix normalization,
  as recorded in the root report. Future passive replays need new directories;
  see the safe `runpy` recipe in [FOLLOW_UP](FOLLOW_UP.md).

The next task is NEW natural entry/return profiling of geometry/setup/span/
material costs and actual uniform-bulk versus gradient paths. Preserve this
slow stock baseline before a bounded optimization; Pong stays outside the task.

## Preceding Gouraud source and Spires native extension: 8 November 2026


| New receipt/report | Bytes | SHA-256 |
|---|---:|---|
| `build/research/3dvibe64/proof.json` | 22,122 | `8d9a06abbbf6cdf38d2c7de58575d2897489f13f2536739cca6c131188439e2a` |
| `build/research/spires/native-analysis/native-proof.json` | 93,500 | `8c8ed15ade5f7c273e2efa43ee906ca9eeddb265c62b4f7e3aaf8fa77e31a7b3` |

- [3Dvibe64](3dvibe64.md): 132-byte packed Bayer/33-shade mapping and exact
  equal-endpoint bulk-fill rule; 14,025,231 scalar DDA samples, 704 light
  entries and 65,536 UV pairs match independent arithmetic. Runtime source
  computes vertex lighting; no emitted PRG, native pixels or FPS is bound.
- [Spires native](spires-native.md): original boot payloads, 4,550 macro bytes,
  4,032 meaningful generated pattern bytes, seven first-band offsets and
  counter holds bind. All 2,640 finite-window trace stores match across two
  closed/reaped fresh boots with 17 RAM/VSF pairs. Native01 is failed startup
  with no captures; native02's unmasked color guard accepts black `$F0` reads;
  native03's masked guard observes all seven low nibbles blue 6 and a visible
  screenshot. No independent committed-pixel compositor is claimed.
- Correct screen `$AC00` pointers are `$AFF8`, used `$AFF9..$AFFF`; the old
  frozen source annotation is retained as an explicit arithmetic error.
  Other Y bands, TechTech runtime, complete animation and timing remain open.
- Both final producers were reviewed and replayed byte-identical. Next focus
  is the [3Dvibe64 Gouraud build/pixel test](3dvibe64.md): task-local official
  tool setup, a small curved/octahedron scene, emitted tables, then committed
  pixels before timing. Pong is unchanged by this extension; broad research
  and the remaining backlog stay active.

```sh
rtk proxy python3 research/3dvibe64/inspect.py
rtk proxy python3 research/spires/native.py
```

## Preceding passive source/data extension: 8 November 2026

The earlier source-only Spires gaps below are now extended by the bounded
native proof above; its source/asset receipt itself remains unchanged.


| New receipt/report | Bytes | SHA-256 |
|---|---:|---|
| `build/research/spires/analysis/spires-proof.json` | 115,534 | `4408d4819dcb1ab8c30b239dea03a7e15006923628c3a594d548aea06cdb11f3` |
| `build/research/vicspector/proof.json` | 45,746 | `131b50f63a2b87a8319e535786a9dae7baa6d8885f3b40d6a7161aea0b354a56` |
| `build/research/host3d/analysis/host3d-proof.json` | 83,064 | `d901f15037cfb55a6aed4463bf9101792f14d89f6c52b6764fbd56e3fdbd1277` |

- [Spires](spires.md): release/source ZIP disks agree. Independent source
  descriptions check 4,032 meaningful FPP bytes; prepared glyph assets match
  40,000 bytes across five coarse phases. Ten charsets mean five phases in
  two vertical banks, combined with eight fine-scroll values for 40 positions.
  Four imports remain missing; the verified 817-byte tool-LUT mismatch is
  retained. Native timing remains open; the supplied Mach-O generator was
  not run.
- [VIC-II-spector](vicspector.md): 32,256 settled PAL BA classifications,
  32 fetch half-cycle entries, 63 X values and 29 MISC annotations match.
  AEC was not independently compared. Graph return paths of 15/16 lines exist
  mathematically; explanatory +2/+1 labels, arbitrary artwork and timed MISC
  remain separate limits. Seven existing FPP pairs are passive reanalysis.
- [Prepared Dragon](host-3d-2026.md): all 128×8,640 = 1,105,920 bitmap/screen
  bytes agree with an independent decode of supplied host-oracle data.
  Actual directories and 67 kernel bytes bind inside the 88-page bootstrap
  input, excluding uncopied padding. The 24,622-core-cycle lower bound for
  the largest picture is conditional and excludes overhead; no measured FPS.
- Root reviewed and replayed all three final receipts byte-identical. No new
  native session, source rebuild or downloaded/upstream execution occurred.
  At that checkpoint 3Dvibe64 was pending reading; the latest bounded
  source/arithmetic case above now supersedes that status.

```sh
rtk proxy python3 research/spires/inspect.py
rtk proxy python3 research/vicspector/inspect.py
rtk proxy python3 research/host3d/inspect.py
```

## Preceding fresh-original visible/priority extension: 8 November 2026


| New receipt/report | Bytes | SHA-256 |
|---|---:|---|
| `build/research/no-bounds/spritefpp-visible-analysis/spritefpp-visible-proof.json` | 41,404 | `340abccc816d2aeaf67fb6679e391c176def06c5e8f4403b5a92f3a6ff2ec89f` |
| `build/research/anomaly/native-priority-analysis/native-priority-proof.json` | 49,889 | `b1fb325819115c015834facf3edf1fba3329c035f42c2fc2c7be9e2c84db4773` |

- [SpriteFPP native03](no-bounds-spritefpp-visible.md) has 14 RAM/VSF pairs
  and 125 completed commands from fresh original boot with no restore.
  Pointer zero ignores the nonzero native header through held offsets 3–24.
  One committed 133×320 component matches all 42,560 palette indices, with
  all eight sprites visible. Seventy-two X layouts are checked offline, not
  all natively drawn. Reverse priority remains inconclusive here; full
  animation/FPS/standalone execution remain open. The new clear pairs use
  raw cycles 46/50, distinct from the preceding 45/49 case.
- [Anomaly native08](anomaly-native-priority.md) has 3 RAM/VSF pairs and 43
  ordinary commands from fresh original autostart, no restore. All eight
  actual sprite states close the prediction's occlusion condition: committed
  overlap 14/14 matches direct composition; reversed priority gives 1/1.
  A different wall matches 38,784 indices in 101 committed rows 51–151; this
  is not a complete sixth 104-row strip. Native bank `$4000` is unchanged;
  a separate oracle input view renames addresses. Actual `$63F8` pointer
  slots were not traced continuously; endpoint/latch checks do not fill that gap.
- Both cases are owner-closed and reaped. Root independently reviewed and
  replayed both receipts byte-identical. Navigation warp is declared; proof
  resumes are unwarped at Speed=100. Anomaly retains two waiting notices, a
  same-process/socket interruption and a rejected read-only WarpMode query.
- At this earlier checkpoint Spires and vicspector were pending leads.
  Their latest passive source/asset audits above supersede that reading-only
  status without adding native observations.

```sh
rtk proxy python3 research/no-bounds/spritefpp_visible.py
rtk proxy python3 research/anomaly/native_priority.py
```

## Preceding original-release and native extensions: 8 November 2026

Candidate native03 and conditional 403-update capture gaps below are
historical; the fresh-boot notes above now own those observed results.


| New receipt/report | Bytes | SHA-256 |
|---|---:|---|
| `build/research/no-bounds/original-analysis/original-binding.json` | 413,163 | `c4f25403d9c737ec15873d7bb2aee4a4175a0af76151f5924a49230c3d474373` |
| `build/research/no-bounds/native-spritefpp-analysis/native-spritefpp-proof.json` | 37,525 | `55158e5ed27edb840106ddaf6363d2cf8cf8fd4c98be2e6651ba002dad186fee` |
| `build/research/no-bounds/plasma-vector-analysis/plasma-vector-proof.json` | 14,909 | `11f6cb2276f40338a696a8e3ded9bda4e9a1e63cedaa6d8bf24a1a5aed123447` |
| `build/research/anomaly/native-upper-fetch-analysis/native-upper-fetch-proof.json` | 40,901 | `9e49c34e002474b9df311aca423519833cdf5118e39327f64d036a0e35bb09e2` |
| `build/research/anomaly/overlap-plan/overlap-plan.json` | 5,138 | `c1248d9b3b11751960e7576497879e595eef914e5f0df88aed5fc6ba037d6193` |

- [Original No Bounds](no-bounds-original.md): genuine two-disk release,
  exact Sparkle byte binding and all 20,261 file-known bundle-31 production
  bytes. Separate test/standalone builds are not original-entry substitutes.
- [Original SpriteFPP native-02](no-bounds-native-spritefpp.md): eleven exact
  RAM/VSF pairs, natural production entry/return and 24 nonzero cached-pointer
  data-latch witnesses across three held-counter cells. All 68×24 atlas
  payload bytes match; eight slot-15 padding bytes are the live pointer table.
  Initial palette zero means DMA proof, not visible pixels. Native-01 is
  retained as cancelled navigation with no RAM/VSF pairs, not FPP evidence.
- [Anomaly native-07](anomaly-native-upper-fetch.md): six exact RAM/VSF pairs,
  active nonzero bank-$C000 fetch, observed borrow/wrap branches and a fifth
  39,936-index strip; five separately proved upper outputs total 199,680
  indices over one prepared wall image. The fifth output has no upper-sprite
  overlap, so reverse priority remains inconclusive.
- `research/anomaly/overlap_plan.py` predicts a conditional candidate after
  403 further upper updates, earliest among sprites 4–7 only. It is not native
  observation or an all-eight scene proof. Future capture must check all-eight
  occlusion and fresh actual CIA/bank, bitmap, palette and artwork.
- [PlasmaVector](no-bounds-plasma-vector.md): 256 prepared projected poses,
  generated character/color-LUT sampling and 971 literal PRG bytes. Original
  loaded-part/generated-RAM/native-pixel binding remains open. The static
  [SpriteFPP plan](spritefpp-native-plan.md) is retained; its older binding
  gap is superseded by the two original-release notes above.

All five new producer receipts were reviewed and replayed byte-identical.
Passive reproductions (stdlib Python; no VICE):

```sh
rtk proxy python3 research/no-bounds/inspect_original.py
rtk proxy python3 research/no-bounds/native_spritefpp.py
rtk proxy python3 research/frontier-2026/plasma_vector.py
rtk proxy python3 research/anomaly/native_upper_fetch.py
rtk proxy python3 research/anomaly/overlap_plan.py
```

## Preceding extensions: 8 November 2026

The following frozen receipts retain their earlier scopes. The new original
SpriteFPP and Anomaly bank-$C000/fifth-strip results supersede their old gaps.


| New receipt/report | Bytes | SHA-256 |
|---|---:|---|
| `build/research/anomaly/upper-scanout-analysis/upper-scanout-proof.json` | 50,335 | `7a6f5a32c52adb85cde0b851ecff47f5154ca301240e48e52d1a810b5ccdc4d3` |
| `build/research/vice-live-verification/verification/verification.json` | 18,167 | `a9e38e278e3ebee0cf492ad75e7b0a00d66d31e116ac3709e2d7987d35fc3e77` |
| `build/research/dragonbond/native-tail-analysis/native-tail-evidence.json` | 19,759 | `ee53c8d9c22c281154273d17c21efa4ef60703fea4649c9e5a42a514b7b980b3` |
| `build/research/dragonbond/scanout-analysis/scanout-proof.json` | 21,959 | `25a7c16ee97941ff45392409e40116cab560fa3f84cfce1e7c76282d8e65a8bd` |
| `build/research/frontier-geometry-20261108/geometry-findings.json` | 16,158 | `45f056681a0fab3f91826c703d1c754bb78f363e91712ff9c0832c0ae595be6b` |

- **Anomaly upper window:** four complete 104×384 strips match all 159,744
  palette indices. Field 4 joins the frozen same-field floor into a coherent
  200×384 bitmap window with 76,800 exact indices. It uses 199 committed
  raster rows plus one completed current DBUF row, excludes lines outside
  51–250 and retains the common prepared-wall-image and active-fetch limits.
  See [the new result](anomaly-upper-scanout.md), rather than interpreting
  the old upper-gap wording as the current state.
- **Dragonbond successor tail:** new native-03 restores the exact native-02
  endpoint and stops naturally at raster 267 inside the music IRQ. All eight
  bank-$8000 successor-tail latches match original bytes. The old optional
  failure and cleanup remain frozen; [the new tail audit](dragonbond-native-tail.md)
  owns this separate captured success and process closure.
- **Dragonbond visible bands:** [the new bitmap/sprite compositor](dragonbond-scanout.md)
  matches 10,368 palette indices in 27 second-field rows, including 7,984
  nonzero indices. Four position-changing rows remain excluded, and the
  all-black DEN-clear first DMA field is not used as visible-picture proof.
  The failed color-boundary guard and inconclusive priority control remain
  archived.
- **Cancellable monitor:** [the new live observer](vice-live-observer.md)
  and real retained JSON/wire verification address interruption, partial
  output, timeout notices and owned closure. The frozen helper, UTC-collision
  failure, old incomplete observation and external cleanup are preserved.
- **SpriteFPP geometry:** [the new source/asset model](frontier-geometry-20261108.md)
  matches 14,793 supplied PRG bytes and 559,104 prepared logical samples.
  The 68 strip keys and 64 pose lists are prepared geometry. That static
  receipt claims neither original FPP execution nor a general runtime texture
  mapper; [the later native result](no-bounds-native-spritefpp.md) owns the
  separate original DMA proof.

Reproduce these new checks without native execution:

```sh
rtk proxy python3 research/anomaly/upper_scanout.py
rtk proxy python3 research/verify_vice_live.py
rtk proxy python3 research/dragonbond/native_tail.py
rtk proxy python3 research/dragonbond/scanout.py
rtk proxy python3 research/frontier-2026/geometry_next.py
```

## Earlier receipts and reports: 8 November 2026

These original receipts retain their scopes and bytes. The latest extensions
above supersede their named upper-window, optional-tail and observer limits;
they do not rewrite the earlier observations.

| Receipt/report | Bytes | SHA-256 |
|---|---:|---|
| `build/research/anomaly/native-tail-analysis/native-tail-evidence.json` | 5,235 | `6a059c275606b55e1fc6bfa14a6ac2093112548981fb78182209883d2274ba9e` |
| `build/research/anomaly/sprite-scanout-analysis/sprite-scanout-proof.json` | 49,746 | `f0c67d0a1a674e9f15e19caa75a16d2b346d2aaaab886b1536d6220dc97b47b4` |
| `build/research/dragonbond/original-analysis/original-analysis.json` | 82,839 | `ad4d83c3d32dcc341e9ad8bcdbc510957d4a668368d659b06ad5ec7aa3ea87cb` |
| `build/research/dragonbond/original-analysis/native-handover.json` | 20,042 | `450f867d9bfbfcb492aeec4fdbeb8252b604d2e6bbf4576143788d9626698c25` |
| `build/research/dragonbond/native-analysis/native-evidence.json` | 278,877 | `f6be9f8c2e9acf40199743fe49f74c03137ca0d83935a2c4caea0b65721113e1` |
| `build/research/frontier-reading-20261108/reading-findings.json` | 11,687 | `9b4705999561d154a9688d294411ab4cf788155482a3749eb146a51a3b447963` |
| `build/research/frontier-followups-20261108/followup-findings.json` | 8,765 | `6d3c9d4198281016c308ddf59fb6021d95e312e9fff74e8646edcb9bcf982e67` |

- **Anomaly:** one complete 96×384 floor field matches all 36,864 palette
  indices. Native-06's original five-clock continuation completes the last
  32 DBUF pixels; 95 completed raster rows plus that completed current row
  form the observation. The previous partial producer and all 20 evidence
  files remain pinned under `sprite-scanout-analysis/frozen-native05/`.
- **Dragonbond:** original bootstrap output and installed host/drive code
  match. All sixteen released intermediate triples use 33 new head bytes
  and 30 old tail bytes; eight native sprite-0 DMA/data witnesses cover both
  VIC banks. The owner audit checks 27 RAM/VSF pairs, 1,769,472 RAM bytes,
  26 completed resumes, one incomplete optional attempt and explicit
  external cleanup. The absent raster267 tail is not a captured state.
- **Further primary reading:** No Bounds' ten-map lattice matches 10,240
  supplied bytes and 9,000 synthesized visible cells. The Star Wars model
  matches its complete 7,544-byte table block and 428,813 truth cases,
  preserving two lazy-copy exceptions and the failed refinements.

These are bounded results. Wider changing-image/native/pixel coverage,
physical IEC transfer, original Hat/Aloft algorithms, and broad production
timing remain open. The broad research goal is active.

```sh
rtk proxy python3 research/anomaly/native_tail.py
rtk proxy python3 research/anomaly/sprite_scanout.py
rtk proxy python3 research/dragonbond/native_capture.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/dragonbond/inspect_original.py --handover build/research/dragonbond/native-02
rtk proxy python3 research/frontier-2026/reading_next.py
rtk proxy python3 research/frontier-2026/followups.py
```

These commands read saved evidence; they launch no native session. The
Dragonbond original-instruction model needs py65 in the retained CPU venv
and the shown `--handover` argument; its default source-only mode would
overwrite the frozen report with a different scope.

## Exact latest continuation inputs

The earlier four demo endpoints are unchanged. The authored Gouraud endpoint
advances to the closed profile's fourth begin; the preceding accepted visible
baseline is retained in its evidence ancestry and unchanged artifact rows.

| Case | Snapshot SHA-256 | Original PC / clock / raster / raw cycle |
|---|---|---|
| `no-bounds/native-03/mature-window-complete.vsf` | `967f604ebde48b649edee3715ece4b08836710ce091e62de246eb6908e5f6a02` | `$0CFA` / 143600978 / 220 / 38 |
| `anomaly/native-08/priority-row-committed.vsf` | `09df702e9fcac59d9c81a3ced230a58a7fcc8bbe7296a6b249ed42131f0db992` | `$B400` / 175046267 / 152 / 11 |
| `dragonbond/native-03/bank80-new-tail.vsf` | `a8b8558f366e94512c1d6682987e57d5dca63a60a4d79edb1566f457138df7c3` | `$12A9` / 149028968 / 267 / 11 |
| `spires/native-03/colored-window-complete.vsf` | `96691e36ee0e6aa645cd8be6e116a60297b554894ae8d8cfe9a8678839302855` | `$A2B1` / 77633652 / 192 / 12 |
| `3dvibe64-profile/native-01/fourth-begin.vsf` | `f31c7ce5b0ef00f8f93727447ea0857640c8d5e184a912fe9b76b3dec968b97f` | `$08CB` / 5131747 / 24 / 19 |

All sessions are terminal. Three renders are complete; the fourth begin is
not a completed fourth render/image. Generated-PRG loader injection remains
explicit, distinct from original-disk lineages. Any new native case states
fresh startup/restore and verifies relevant initial state before execution.
The immediate next task is pose-dependent camera/plane verification; the
offline omission experiment is complete and no new native endpoint was added.
Never overwrite accepted, failed or replay directories. See the qualified
fresh-OUT replay instructions and complete backlog in [FOLLOW_UP](FOLLOW_UP.md).

## Preceding continuation inputs and observer failure

| Case | Snapshot SHA-256 | Original PC / clock / raster / raw cycle |
|---|---|---|
| `anomaly/native-06/floor-line-drawn.vsf` | `2428affe32e414636d3444b1cfa72f41d25d7e466adf0ff0ad07dbabf28d32c8` | `$B82A` / 167013188 / 250 / 62 |
| `dragonbond/native-02/bank80-after-full-new.vsf` | `79a7cd97a25334167698fac3603037c6069e2c3d98e6de7ce3b1824bf3f86ea1` | `$3278` / 149028238 / 255 / 37 |

Both preceding paths are under `build/research/`. Both sessions are owner-closed;
there is no reusable live handle. Dragonbond's optional observation ended
before helper cleanup; `owner-cleanup.json` separately proves the exact
orphaned process was absent after SIGTERM. Its child exit code and a later
machine checkpoint were not observed in that old attempt. The separate
native-03 continuation above now uses the cancellable observer and an
any-original-instruction raster stop. Its exact tail capture extends the
boundary without changing the failed attempt's history. See the frozen
[Dragonbond native lineage](dragonbond-native.md).

## Earlier 8 November receipts, retained unchanged

| Receipt | Bytes | SHA-256 |
|---|---:|---|
| `build/research/anomaly/native-scanout-analysis/native-scanout-evidence.json` | 68863 | `70fe556b8c80bf6a73721b4f51852e30bc9f6b103f1e3bff06e4e2e1b1e7dfa2` |
| `build/research/anomaly/scanout-analysis/scanout-proof.json` | 38086 | `ed4a71298f786f7dddaa205c0d217c615fa451bf90ce0a99597f378b91a2236e` |
| `build/research/relax24/loader-contract-01/loader-proof.json` | 15381 | `9d1ba05126fab006b85517227922b593cce5214d57b6006fb4c796ccba012c61` |
| `build/research/frontier-20261108/findings.json` | 1882362 | `0d36903c9cfcd055e980343f0668946d66d6765cdcf393e3527aa4de1f868974` |

This earlier batch established four coherent 24-row Anomaly strips
(36,864 pixel indices), a closed five-pair native continuation, the
source-byte-gated Relax24 loader contract and three primary investigations.
Its strip-only scope remains frozen; the complete field above extends it.
The old four receipts below retain their original scope.

```sh
rtk proxy python3 research/anomaly/native_scanout.py
rtk proxy python3 research/anomaly/scanout.py
rtk proxy python3 research/relax24/loader-contract.py
rtk proxy python3 research/frontier-2026/november.py
```

Historical Anomaly parent is
`build/research/anomaly/native-05/field-post.vsf`, SHA-256
`2185b4f932c49c900223c9e5c3598fc66c6fd8b1e04704158699659aa574b28a`,
PC B828, clock 167013183, beam 250/57. Its owned session is closed.
Native-06 above supersedes it as the latest completed stop.

Relax24's request/file/trailer link is now proven at the conditional byte
interface. Next bind actual resident sector service and capture C15D with
cursor55FC, carry clear and the loaded-byte hash in `relax24-loader.md`.
Dragonbond's prepared intermediate data now has the bounded two-bank DMA
witnesses above; the PDF and release-specific split remain distinct.

## Earlier research receipts: 7 November

| Receipt | Bytes | SHA-256 |
|---|---:|---|
| `build/research/anomaly/upper-analysis/upper-proof.json` | 1,142,094 | `67ac3c820f62f2f8bdfa1342a8790459c4ce673145c1080393f471a896a4ff3f` |
| `build/research/anomaly/native-upper-analysis/native-upper-evidence.json` | 282,689 | `53274dec47bf09e196878d973ec6c5f10782497d61ff36cf50f97db31bc108fd` |
| `build/research/relax24/resource-recovery-01/resource-proof.json` | 6,296 | `f56b8b0b650d104433c46cea100dd3d08a82e43175a76b43cd7eb10b87a8ca7b` |
| `build/research/frontier-2026/primary-notes/primary-notes-proof.json` | 18,983 | `5ec288fd0dfc3fe0913318ce64eb5032c477592afadd214a467bc6064c0cc0aa` |

The receipts bind their producers, original inputs and outputs. Their claims are:

- **Anomaly upper model:** 28 jobs, all declared RAM/state domains, a direct
  4,160-byte bitmap plus 520-byte attribute oracle, and completed first publication.
- **Anomaly native audit:** 67 RAM/VSF pairs, three PNGs, exact parent restore,
  28 first-update trace entries and three 96-store fields. The rejected uniform
  63-clock timestamp hypothesis is retained; physical bus phases remain unproved.
- **Relax24 resource:** 3,569 compressed bytes yield 9,216 bytes at AC00..CFFF
  in two functional models, with all 7,501 match reads known. No CPU continuation
  through the dead-value unknown read or initialized reader/menu is claimed.
- **Primary-source lane:** eight immutable Git blobs, 14,336 packed artwork
  bytes, 28,672 restored bytes and 46,080 bob-mask cases. Negative controls and
  the five empty Rodents-caption responses remain explicit. No native claim.

## Recheck without rerunning native execution

Run from `/Users/rogerjohansson/git/asynkron/c64demo`:

```sh
rtk proxy python3 research/anomaly/inspect_upper.py
rtk proxy python3 research/anomaly/native_upper.py
rtk proxy python3 research/relax24/decode_resources.py
rtk proxy python3 research/frontier-2026/primary_notes.py
```

These read saved inputs and regenerate bounded receipts. They do not launch
VICE or repeat the multi-million-instruction Relax packing proofs. The current
producer/receipt pairs have already passed. Before revising a producer, archive
it and its old receipt; do not overwrite a frozen proof to erase a failed gate.

Verify every indexed file without rewriting anything:

```sh
rtk proxy python3 - <<'PY'
import hashlib, json
from pathlib import Path
manifest = json.loads(Path('docs/research/HANDOFF-ARTIFACTS.json').read_text())
for item in manifest['artifacts']:
    data = Path(item['path']).read_bytes()
    assert len(data) == item['bytes'], item['path']
    assert hashlib.sha256(data).hexdigest() == item['sha256'], item['path']
print('All indexed artifacts match.')
PY
```

## Earlier continuation inputs (superseded above)

- **Anomaly:** `build/research/anomaly/native-04/field-04-pre.vsf`, SHA-256
  `70fbfcde49a6c1b9a1b18ad538d7e0684cc1c7fdaf2ec6a42b40ad734bbf1b5b`,
  PC B400, clock 167006965, beam 152/13. Session is owner-closed. Restore
  with the same original side-one disk and verify full state identity before
  further execution. One later full floor is proven above; upper-wall output
  and broader workload/timing remain open.
- **Relax24:** compare the 496-byte uploaded drive block from inner RAM
  $25A8..$2797, installed at drive $0500..$06EF, with recovered $AC00..$ACF7.
  Bind request `02 30 30` before claiming a transfer. Retained `00.prg` is
  13,822 bytes, loads at $2000 and ends with word $080C; this is compatibility
  with the trailer/JMP contract, not executed-reader or transfer proof.
- **Primary sources:** bind the finite-bob source/generated plotters to the
  original No Bounds part before investigating alleged Aloft reuse. For
  Rodents, obtain the author transcript or actual released code. Keep Hat/Aloft
  algorithms unresolved until their own artifacts explain them.

Sprite-ball was committed separately as `3da9ae1` while this research handoff
was being prepared. Its README owns its fixed shading/gap-order design and
remaining limits.
Default hexagon PRG SHA-256 is
`9771ac67a648d4e66426c4b48373e9c19dc3db9fe0ed98f5dfbd824d30825744`;
its receipt is `4ceaa34b0cbd1d88b426df59afcfe971f425f83e6f12c2bdca49f47f5422594b`.
The receipt covers 257 presentations, 129,528 sprite bytes, 11,316 edge
samples and maximum 46,092 of 58,968 clocks. Baseline/golden native receipts
remain historical; they do not validate their newly shared shading code.
