# Stock Gouraud: source-based cost hypotheses

Measure the span loop, its caller setup and material writes separately before
changing code. The cheap exact candidates are a guarded material bypass/cache
path and a shade-DDA path that permits at most one increment per pixel.
Broader Bayer-constant subruns offer more work to remove, but need a careful
break-even test. Rewriting Bayer generation or dropping duplicate row stores
does not explain the observed half-second intervals: generation is already a
132-byte table, and the raw row-store work is a small part of the budget.

These are hypotheses and source-derived workload counts for the **two already
accepted pixel samples**, not measured function attribution. The separate
native profile lane owns entry/return anchors and exclusive call-tree costs.
No product, SDK, Pong or frozen artifact is changed here.

[`research/3dvibe64-profile/cost_model.py`](../../research/3dvibe64-profile/cost_model.py)
reads pinned span records and emitted source, then writes only
`build/research/3dvibe64-profile/hypothesis-analysis/`. Its receipt is
`cost-hypotheses.json`. It executes neither a CPU nor the SDK renderer.

## What is already optimized

The pinned [SDK builder](https://github.com/Librologica/3Dvibe64/blob/b19df459b7efe50d514b59fe876c0bc7c326c5b4/work/build-3Dvibe64.ps1)
uses the ordinary Mode 6 byte-span kernel. The current PRG is
`69b0d86f79106b2bf9654d85bd631bc68c12f4efd708454a0048560b3c1bfdeb`.

- Lines 37680–37724 construct four packed 33-byte Bayer rows. The native pixel
  loop does table loads, masks and ORs; it does not calculate Bayer thresholds
  or perform lighting for every pixel.
- Lines 31254–31450 combine four aligned pixels into a byte, carry three shade
  advances in registers, and aggregate partial-byte read/modify/write work.
- Lines 31452–31527 bulk-fill a complete span when its two endpoint shades
  select the same packed Bayer byte for that row. Spans shorter than eight
  pixels bypass the classifier.
- Lines 31542–31562 contain the exact RAM-state shade advance. The scalar
  repeated-subtraction implementation is not the path used for every pixel:
  three advances per full byte are already register-carried.

The emitted ASM is the authority for current instruction paths. Its edge-shade
DDA contains an additional host-applied register/remainder simplification;
copying an older source-template block into a timing model would be wrong.

## Captured workload, not a whole-object benchmark

| Source-predicted work | Sample 1 | Sample 2 |
|---|---:|---:|
| Span inputs / average pixels per span | 168 / 22.50 | 161 / 15.09 |
| All pixel writes, including overlap | 3,780 | 2,429 |
| Uniform whole spans / their pixels | 28 / 552 | 7 / 97 |
| Nonuniform spans / their pixels | 140 / 3,228 | 154 / 2,332 |
| Full byte groups in nonuniform spans | 740 | 484 |
| Partial byte groups / their pixels | 162 / 268 | 217 / 396 |
| Register-carried DDA advances | 2,220 | 1,452 |
| RAM-state DDA advances | 868 | 726 |
| Successful shade increments, register / RAM | 982 / 458 | 703 / 528 |
| Advances requiring more than one increment | 3 | 103 |
| Maximum increments in one advance | 20 | 13 |
| Material cell touches / unique cells | 1,072 / 252 | 729 / 168 |

Classification above follows the accepted inputs and immutable kernel source;
internal branch markers were not part of those older captures. The new native
profile should verify actual uniform/general paths. The model checks that
full/partial pixels and DDA advances reconcile with the accepted span totals.

## Ranked experiments after the measured cause is known

1. **Fixed material specialization or existing span-cache reuse.** The current
   scene uses one fixed `$BF/$01` ramp, yet the Gouraud caller directly invokes
   `apply_material_span_a/b` on every row. `MATERIAL_CELL_SPAN_CACHE=1` does not
   mean this caller uses `maybe_apply_material_span_*`. There are 820/561
   repeated touches to cells already touched by the same ramp within these
   windows. The direct helper’s nominal call/loop estimate, including its
   caller JSR, is `44×cells + 45×A_spans + 42×B_spans`: 54,224/39,321 cycles,
   before indexed-page, pointer-carry, VIC and IRQ effects. That is a useful
   measured bucket, not a claimed saving. Source references: material reader
   2424–2480, active-only flags 8059–8067, cache gating 8527, and Gouraud caller
   26943–26977. A configuration-only test would remove fixed object overrides
   and select the same global gray/reflectivity-1 ramp; simply choosing the
   same global values while retaining fixed overrides does **not** set the
   active-only flags, which require `$FF` descriptors. Any cache path needs
   correct reset/invalidation at material, face and buffer transitions, and
   must retain Color RAM behavior across the two bitmap banks. Do not generalize
   this to multimaterial scenes or an active VIC conflict policy.

2. **An exact one-step DDA domain, then partial-span overhead.** In 138/140 and
   105/154 nonuniform spans, `delta <= extent`, so each advance needs at most
   one shade increment. The current loop rechecks after an accepted increment.
   A guarded path can avoid that recheck without quantizing slopes; keep the
   general repeated-subtraction path for steep shade changes and zero extent.
   Gross nominal recheck blocks account for about 21,272/13,490 cycles in that
   domain, before a replacement’s dispatch/liveout costs. This is only about
   3.7%/2.6% of the old complete interval, so this detail alone cannot create a
   fast renderer. Sample 2 has more short/partial spans, making function-call,
   scratch-memory and partial-byte overhead worth separating from successful
   DDA subtraction work. Preserve `sign×floor(k×delta/extent)` for descending
   shades; flooring the signed fraction changes accepted pixels.

3. **Extend exact Bayer-constant filling inside a gradient.** Whole-span
   classification already skips 552/97 pixel samples. Inside the remaining
   spans there are 201/127 maximal packed-pattern runs at least eight pixels
   long, covering 2,308/1,511 pixels. Monotone shade interpolation and the
   verified endpoint-equality property make these legitimate constant-pattern
   intervals. Finding native boundaries may require division, extra state or
   guarded chunk tests; on average 15–23-pixel spans that setup can erase the
   gain. This is the larger algorithmic opportunity **if** measured kernel
   work dominates, but it is less cheap than reusing existing material logic.
   Start with a bounded full-byte case and preserve unaligned boundary masks,
   inclusive endpoints and screen-anchored phase. Do not replace exact slopes
   or shades with a quantized approximation.

4. **Small Mode 6 specialization cleanups.** All four emitted Bayer rows start
   at `$B526/$B547/$B568/$B589`; every high byte is `$B5`. The caller nevertheless
   loads that high byte and writes seven self-modified operands each span.
   A proven compile-time constant can remove about 5,376/5,152 nominal cycles
   before any setup cost, around 1% of the old intervals. Separately,
   `gouraud_init_span_pointers` still calculates `ptr1` for the Mode7 host
   contract, while the Mode6 kernel writes the adjacent physical row via
   `ptr0,Y=1`. Its unused initializer half is 22 nominal cycles per call,
   3,696/3,542 total. Restrict such removal to the exact Mode6 caller contract;
   retain Mode7’s required cursor and any scratch/liveout obligations. These
   are small follow-ups, not an explanation of the main cost.

## Why row duplication and generic table rewrites rank low

Two physical rows per logical row require 2,144/1,458 bitmap stores in the
source-predicted paths. The second row’s existing instruction sequences cost
about 10,974/8,373 nominal cycles: eight cycles for a full-byte duplicate and
nineteen for a boundary read/modify/write duplicate. That is approximately
1.9%/1.6% of the old intervals before VIC effects. Omitting a row changes the
image and already fails the pixel controls. Preserve both rows for an exact
optimization.

Similarly, just eliminating material store instructions would remove only
12,864/8,748 nominal cycles; the material helper’s repeated pointer/loop work
is why its complete measured bucket matters. Do not confuse store counts with
whole-routine costs. These figures overlap other categories and must not be
summed into an overall attribution pie chart.

## ABI and measurement boundaries

At `$A000`, seven bytes `$B43B..$B441` hold start/end X, absolute shade delta,
signed direction, error, extent and start shade. The accepted domain is
`0<=x0<=x1<160`, `0<=y<100`, shades 0..32, initial error zero and inclusive
extent `x1-x0`. A singleton uses its start shade only. `drawbuf=$0B`, row
pointers `$25..$28`, and `yrow=$2F` bind the physical addressing.

The caller returns through `$957D`, restores X from `yrow`, checks `face_ymax`
and reloads the next span. Scratch/register changes still need an explicit
caller/IRQ review before any optimization; do not infer that a byte is dead
just because the final bitmap agrees. `apply_material_span_*` uses `ptr1` for
Color RAM before the pixel kernel initializes bitmap cursors, a separate use
from the kernel’s apparently redundant `ptr1` preparation.

The anchor lane separates `gouraud_fill_bounds` parent work, child material
calls, child span calls and uniform/general paths. Geometry/bounds and
shade-edge work are separate parents. `rotate_project_vertices` is not the
whole projection cost: this emitted build performs lazy projection during
face collection. Child costs must be subtracted before assigning exclusive
percentages. This lane deliberately does not duplicate that anchor map or
manufacture function timings from span-entry gaps.

The older `$1153 → $08D4` totals remain 577,195/509,905 PAL cycles. They exclude
earlier lighting/clearing and later presentation. No hypothesis establishes
whole-loop FPS, a net speedup, another object’s cost or physical hardware.

## Replay

```sh
rtk proxy python3 research/3dvibe64-profile/cost_model.py
```

Only the new hypothesis receipt and checked producer copy are written. Each
nominal figure is an isolated source-instruction model, with no new dispatcher
cost, indexed/branch page penalties, pointer carries, VIC stalls or IRQs.
Actual cost attribution and net image-preserving improvements require the
closed native profile plus the independent pixel check. No fix is made here.
