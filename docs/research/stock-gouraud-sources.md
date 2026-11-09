# Primary author evidence for classic C64 Gouraud shading

The strongest retained technical lead is **HCL's Edge of Disgrace release
NFO**. It describes a specific shader algorithm, whereas the Mekanix and
Applause sources mainly establish author attribution. None of these retained
pages independently proves an exact stock CPU clock, correct interpolation,
native pixels or performance. Released shader assembly has not been located
in this bounded source pass.

The new passive producer is
[`sources.py`](../../research/stock-gouraud/sources.py). Exact HTTP bodies and
retrieval metadata are retained under `build/research/stock-gouraud/primary/`;
the final receipt is `analysis/accepted-02/source-proof.json` beneath that
project's build directory. No old source, product or native capture changed.

## What the authors actually establish

| Primary author source | Useful evidence | Remaining boundary |
|---|---|---|
| [HCL's EOD release NFO](https://www.pouet.net/prod_nfo.php?which=51983) | Detailed shader description; identifies its author and distinguishes the later shader from an earlier Gouraud-looking texture. | Author algorithm claim, not inspected shader code or native measurement. |
| [HCL's Mekanix production note](https://csdb.dk/release/?id=94438&show=notes) | HCL identifies his Gouraud part as an enhancement of EOD. | Establishes lineage, without describing new interpolation arithmetic. |
| [Browar's Coders Talk interview](https://attitude.triad.se/index.php?action=readtext&issue=3&which=7) | The coder identifies his own multicolor Gouraud Z-buffer in Applause. | Names the effect; does not explain its interpolation or hardware timing. |

In EOD's `ditheredvector` section, HCL describes 16-bit calculations and
perspective for the Gouraud cube, four colors and 13 dithered levels. He
contrasts a tracing-line routine with a conventional filler and describes
skipping zero plots on thin lines between adjacent dither steps. This is
concrete runtime-rasterizer evidence beyond a uniform pattern selected per
face; it does not independently establish how every light/shade input is
produced. The earlier `x-vector` section describes only a Gouraud-styled
texture and must remain distinct.

The three-out-of-four zero-iteration reduction is **HCL's claim**. This
analysis verifies its presence in the retained text, but supplies no invented
bit-mask algebra or cycle-saving percentage. Original shader instructions
and actual dither transitions would be needed to prove the optimization.

Release identities are retained separately:
[EOD](https://csdb.dk/release/?id=72550),
[Mekanix](https://csdb.dk/release/?id=94438&show=notes), and
[Applause](https://csdb.dk/release/?id=4019). They identify ordinary C64 demo
releases and their credited authors. That supports their platform identity;
it is not an accelerator-exclusion rule or a verified 1 MHz run. No
qualifying Crest shader source was found in this pass.

## Exact retained locations

The text files are derived readable views; the original HTTP bodies remain
byte-for-byte inputs. The receipt also records the raw HTML body line of
each anchor, avoiding reliance on a search-engine snippet.

| Anchor | Derived text location | Raw body line |
|---|---|---:|
| HCL identifies himself as the NFO author | `eod-nfo.txt:15` | 90 |
| Earlier textured `x-vector` | `eod-nfo.txt:44` | 119 |
| Gouraud/dithered-vector section | **`eod-nfo.txt:96–123`** | **171–198** |
| Next section, delimiting that discussion | `eod-nfo.txt:124` | 199 |
| Mekanix Gouraud lineage | `mekanix-author-note.txt:40` | 134 |
| Browar's own Applause claim | `browar-interview.txt:58` | 110 |

The corresponding derived files are in
`build/research/stock-gouraud/analysis/accepted-02/`. The Mekanix page
explicitly labels HCL's post as submitted on 6 December 2011. The interview
separates each coder's answer; the matched statement is Browar's answer to
the question about his own best C64 effect.

## HTTP custody and the original release ZIP

The 8 November 2026 retrieval retained **six HTTP 200 bodies** and metadata
for all seven attempted resources. Each successful entry records requested
URL, final URL, status, headers, UTC retrieval time, exact byte count and
SHA-256. The separate author-domain URL
`https://www.boozedesign.com/pub/eod_note.html` failed name resolution; its
`URLError` metadata is retained, with no invented HTTP status or body. The
successful NFO input is therefore explicitly the release-NFO mirror.

The original release download was obtained from
[the CSDb-linked ZIP](https://csdb.dk/getinternalfile.php/67631/EdgeOfDisgrace.zip):
**362,298 bytes**, SHA-256
`21ec8560179a7ff4bf5c77b6102632f9a078aabddffea2f5534b304109ea353e`.
Its entire member inventory is:

| Member | Bytes | SHA-256 |
|---|---:|---|
| `EdgeOfDisgrace_0.d64` | 174,848 | `ee9570df68c3ddd1fda60ea3360dd5880c2ac95ed110bbe1bd60fdb91dec3f61` |
| `EdgeOfDisgrace_1a.d64` | 174,848 | `0624697997c57209929fc36ff7121ec7c61760a88576edbf0768d63e77d28956` |
| `EdgeOfDisgrace_1b.d64` | 174,848 | `b348369ba5c7644019e4bf7f3cb8a5e81529b220e10b76dc5c0b7ad548310628` |

The passive ZIP reader validates each member's CRC and hashes its bytes in
memory. There is **no separate NFO/text member to compare**. This does not
mean the disks lack a note program. No disk note is depacked or executed, so
mirror-to-original-disk NFO equality remains unproved. No archive host
executable is extracted or run.

Selected successful body pins are:

| Body | Bytes | SHA-256 |
|---|---:|---|
| EOD NFO mirror HTML | 23,586 | `b8b52a2ba5ce98577d9047f69c1eb398d7e5d50c257537553b0c3faf629cb318` |
| EOD release identity HTML | 158,243 | `2d67059b36131a0b60aecdaed7d7569c96f5c02d33202aa03cbe1d3c1c2b0d33` |
| Mekanix author-note HTML | 18,160 | `b0243bc21ecfa1f64f312108772a9e42b458c87f3f852746be91e94d944391ec` |
| Browar interview HTML | 17,714 | `e281fd688d7b97f2515712e63c33184d7df3518e88978ffb34751990785ab65e` |
| Applause release identity HTML | 17,631 | `36ca885598013cafa52840014910800938b66b694f48e02c02e1c5b31587f8f8` |

All 13 primary body/metadata files have literal hash guards in the new
producer. Dynamic page counters, headers and dates are not re-fetched during
replay or treated as permanently stable live content.

## Replay and the next bounded question

From the repository root, choose a fresh output directory:

```sh
rtk proxy python3 research/stock-gouraud/sources.py \
  --output build/research/stock-gouraud/analysis/replay-next
```

Replay is fully offline: it checks the frozen HTTP inputs, extracts readable
text/locations, inventories the ZIP as data, and writes a compact receipt
and checked producer. Output references are local filenames; no output-path
prefix or new retrieval timestamp enters the receipt. Nonempty output
directories are refused. `accepted-01` is an intermediate receipt;
`accepted-02` is final.

The 13 retained primary files total **602,983 bytes**. A fresh `replay-01`
reproduces all **seven analysis outputs, 151,066 bytes**, byte-for-byte,
including the receipt and checked producer. Independent read-only review
found no producer defect; all 33 artifact references and all 2,379 previously
frozen artifact hashes checked unchanged.

| Final artifact | Bytes | SHA-256 |
|---|---:|---|
| Producer | 11,328 | `8150e69c5c2c652bdb7160b55c351e87126dc704f34a1562b76cacb64207e189` |
| Source receipt | 11,809 | `9f7641d1eea14ce9b7580b534772f18cd43f93091e0e829996a1a3c1d11ee36e` |

The next useful question is whether the original shader can be obtained
with author attribution, then bound to its release and exact shade-step
behavior. Native stock-clock and pixel checks would be separate work.
These pages must not be promoted into a claim of measured shader speed,
full runtime lighting, or independently verified interpolation.
