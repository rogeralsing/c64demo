# Detached, two-sided panels: renderer compatibility

This is a read-only assessment of the current single-object renderer, including the interlaced icosahedron and its unrolled edge dispatch. The target appearance is an exploded cube made of separated panels. The screenshot alone does not specify whether those panels stay aligned with their original cube faces, rotate independently, or intersect; those distinctions change the cheapest correct solution.

**The current edge sampler is reusable. Its existing distinct-color XOR palette does not implement opaque depth order, and sorting its calls does not fix that.** A bounded two-layer case can instead use aliased palette selectors to obtain opaque priority in one prefix pass. General painter rendering can use masks or visibility resolution; a depth buffer is not automatically necessary.

## What the current renderer actually computes

The relevant code is in [xor-fill.asm](../../src/xor-fill.asm), [cull.asm](../../src/cull.asm), and [icosahedron-model.asm](../../src/icosahedron-model.asm).

1. `cullFaces` assigns each outward-wound face a visibility flag. `drawCubeBoundaries` turns that into `xorFaceColors[f]`: the face's two-bit color selector when visible, zero otherwise.
2. Each mesh edge has exactly two neighboring faces. `XorCubeEdge`, `XorIcosahedronEdge`, and the indexed noninterlaced loop compute their transition as `colorA XOR colorB`. A zero transition is skipped.
3. `drawBoundary` samples one crossing per integer logical X in the half-open interval `[leftX,rightX)`. Crossing Y is the exact rational ceiling. It XORs a packed color transition into an immediate operand of the fill code. Vertical edges contribute no crossing to this vertical-prefix formulation.
4. `xorFill` starts the running byte at zero for each visited byte-column. Generated cells execute `EOR #marker; STA charset; STX markerOperand`, with X zero. The result is written and its marker is reset. Selected interlaced rows use the same logic after crossing-to-field mapping.

Equivalently, for a logical pixel covered by a set of accepted faces:

```text
output = XOR of the two-bit color selectors of all those faces
```

The edge-delta optimization is the linearity of that expression: two coincident contributions can be combined before rasterization. It has no depth state. Neither marker accumulation nor the final XOR depends on submission order. The unrolled chain's descending edge order is therefore not a painter order.

This expression describes pixel **selectors**. When several selectors map to the same display color, a useful non-injective palette can make their XOR result look like opaque priority. The current palette has distinct selector colors; the specialized construction below changes that assignment rather than creating depth state.

For the current closed convex solid, accepted front faces partition the projected silhouette, apart from shared boundaries. Each covered pixel belongs to one surface, so its XOR is simply that surface's color. Back-face rejection consequently also removes surfaces hidden by the convex solid. This is the geometric reason the current opaque-looking result works; it is not a general property of XOR filling.

## Assumptions detached panels break

| Current assumption | Consequence for open panels |
| --- | --- |
| One-sided outward surfaces form a closed convex boundary | A back-facing panel may be visible through a gap and needs rendering. Front-facing classification alone no longer resolves occlusion. |
| Each edge joins two faces | A detached panel's rim has one incident face; its outside contribution must be explicit zero. The current model builder rejects one-face edges. |
| Neighboring faces use different selectors | This ensures a visible shared color transition, not correct depth. Unrelated overlapping panels can still share a color or XOR to a third color. |
| With the current distinct-color palette, accepted surfaces have disjoint interiors in projection | Overlap produces XOR mixing. A palette-alias construction can relax this to two separately nonoverlapping layers. |
| A fixed 12-vertex, 20-triangle icosahedron satisfies audited bounds | An exploded cube needs different topology, often duplicated panel-local corners, new bounds, and new transform/range verification. |

The selectors are numbers, not independent opaque layers. Two overlapping color-1 panels give `1 XOR 1 = 0`, creating a background hole. Colors 1 and 2 give selector 3, producing the third display color instead of either panel. All three together give zero. Changing palette RGB values does not change these algebraic failures.

The three-color face-adjacency coloring in `icosahedron-model.asm` only ensures that adjacent visible triangles have a nonzero transition. Equal colors across a genuine shared edge would actually be valid if a seamless region were desired: the zero transition would correctly erase the internal border. A triangle count, adjacency coloring, and visible-surface count are separate concerns.

The current face value is constant across its entire polygon. Patterned panels add a separate question: a zero/black sample inside a stipple or checker pattern is usually still an **opaque covered surface**, not a hole through to the panel behind it. Coverage must remain separate from pattern color. Screen-aligned patterns exposed through a moving stencil, projected coplanar colored patches, and surface-coordinate texture mapping are different implementations; their appearance in a still image does not identify which one is used.

### Two-sidedness and shared boundaries

A thin physical panel should be represented once for coverage. Projected area sign can select its front/back color or shading; it should not automatically reject its back side. Adding two coincident opposite-wound polygons and submitting both to the XOR compositor cancels identical colors. Retaining the current `area >= 0` policy with duplicated front/back faces also risks double acceptance at zero area.

For a flat quad split into two triangles, both triangles can use the same selected panel color. Their shared diagonal has delta zero; the four exterior edges contribute `panelColor XOR 0`. Alternatively, emit the four quad perimeter edges directly. Moving a face away from its original cube neighbors means it no longer shares their geometric edges: the original eight shared cube corners and twelve-edge list cannot simply be reused as though the cube were still welded.

### Culling is not an occlusion test

The exact projected signed-area calculation remains useful for orientation and one-sided back-face rejection. For two-sided panels, both nondegenerate signs can be visible. It does not determine whether a different panel is in front of a pixel.

The interlaced depth shortcut is narrower still. Its face sum of `rotatedZ` decides visibility outside the fallback band only because it was audited for the **specific** 21/34 icosahedron, camera 144, Q6 transform, projection, and 29/20 zoom. The source contains guards for those assumptions. It is not a Z buffer, painter comparator, or general convex-polyhedron theorem. Disable it for the panel model; use exact orientation, or derive and verify a new model-specific shortcut later. Translating or independently rotating panels invalidates the existing proof even if the picture still resembles a cube.

## Compatible ways forward

### A. Keep XOR overlap as an intentional visual effect

All panel perimeter crossings can still be aggregated, including arbitrary overlaps. The existing compositor then produces a deliberate XOR/stencil appearance. This requires accepting color mixing and cancellation as part of the effect. It does not reproduce opaque panels hiding each other.

### B. Painter-sort panels, then overwrite only their covered pixels

If a valid far-to-near order exists, rasterize each complete panel into a coverage mask and composite it over the destination. With packed two-bit pixels:

```text
destination = (destination AND NOT coverageMask)
              OR (panelPixels AND coverageMask)
```

Here each covered logical pixel has mask bits `11`; uncovered pixels have `00`. A black opaque pixel still needs coverage even though its color selector is zero.

The current exact DDA, half-open corner rule, and prefix idea can generate those masks. The existing `xorFill` routine cannot be called unchanged once per panel: it starts from zero and stores background throughout its visited rectangle, erasing previously drawn panels outside the current polygon. It needs a mask-aware store/compositor, or a separate mask pass and merge. Marker reset can remain fused with mask traversal, but rectangle clearing must happen for the whole scene rather than accidentally between painter layers.

Sorting by a panel's average Z is only a heuristic. For exact painter rendering, establish relative depth on each projected overlap and find a consistent order. Strictly disjoint convex panels have a consistent depth relationship within a connected overlap, but several panels can still form a cyclic occlusion order. Intersecting panels can require splitting. In those cases, one whole-polygon order is insufficient.

### C. A cheaper special case: panels on a larger convex box

Suppose each cube face is merely translated outward along its normal, stays parallel to its original plane, and remains a subset of a face of one common larger convex box. With the camera outside that box, a ray meets at most one entry face and one exit face. Thus near/front panels are interior-disjoint from one another in projection, as are far/back panels. The exact result has only two potential layers:

```text
far/back panel color, then near/front panel where covered
```

Within each layer the XOR representation is valid. There are two ways to combine those layers: a restricted palette-priority encoding, or explicit coverage composition for richer materials.

#### One prefix pass with two global tones

The [native Lab open-panel engine](the-lab-mms.md) demonstrates the important exception to a blanket “XOR cannot be opaque” claim. Let A and B be binary layer coverages, with at most one region of each layer at a sample. Emit transition contributions 1 for A and 3 for B. In character mode choose outside code 3, alias global selectors 1 and 2 to the A tone, put the B tone in selector 0, and use Color RAM black for selector 3:

| Coverage | Code `3 XOR A XOR (3*B)` | Hardware selection |
| --- | ---: | --- |
| Outside | 3 | Color RAM black. |
| A only | 2 | `$D023`, A tone. |
| B only | 0 | `$D021`, B tone. |
| Both | 1 | `$D022`, the same A tone. |

A therefore has opaque priority over B with the existing kind of single prefix traversal. Marker reset stays zero and the prefix seed becomes `$FF`, combining exactly with [Tower N2's outside-code palette](tower-power-n2-palette.md). Sorting the edges remains irrelevant. In the supporting-box geometry, one may assign the entry/near panels to A and exit/far panels to B; the geometric two-layer argument supplies the required interpretation. A generic screenshot or native A/B label alone does not establish that relationship.

The character-mode version supplies **one global A tone and one global B tone**. It does not preserve the current three independent face colors. The Lab's multicolor bitmap can vary its duplicated screen-color nibbles and Color RAM per cell; reproducing its multiple panel colors needs that local palette capacity and suitable prepared assignments. Two different A materials sharing a cell cannot both become distinct colors under one aliased selector pair.

This encoding also requires same-layer nonoverlap. Two A regions at a sample cancel their contributions, and two B regions do likewise. Arbitrarily tilting the panels, crossing supporting planes, or adding more layers can invalidate the geometric or palette constraints.

#### Patterns and richer colors

B may stipple between its tone and empty black when there is no layer behind it: its per-sample contribution is either 3 or zero, and A still wins over both. An **opaque black sample in A** is different. Omitting A's contribution makes B visible; it does not paint black over B. An arbitrary A checker therefore cannot be added by treating black as an absent transition. It needs coverage-aware selection, prepared visible fragments, another palette construction with its own proof, or explicit compositing.

For independent panel colors or general opaque patterns, separately reconstructed layer colors can be composed near-over-far with a coverage mask. If every covered pixel has a constant nonzero selector, near-layer coverage can be derived from its packed color bits. Opaque black requires an explicit coverage representation. This path needs composition work/storage, but not necessarily general polygon clipping or a per-pixel depth buffer.

The supporting-box guarantee is lost when panels tilt independently, cross other supporting planes, or otherwise leave that common convex shell. “Exploded cube” by itself is not enough to claim the two-layer property. Interlaced field parity is also not a spare layering channel: opposite-parity pixels hold display history and must remain intact.

### D. Resolve visible intervals before the existing final prefix pass

Another compatible design keeps one final framebuffer write. For each logical X, derive the projected Y interval of every panel, resolve which panel is nearest over each interval, and emit **final visible color transitions**. The existing color-prefix kernel can then consume those transitions unchanged.

For a known valid painter order, interval overwrite can resolve coverage. For general tilted/intersecting geometry, use depth-aware interval clipping/splitting or a small depth buffer. Constant-color planar panels lend themselves to column spans; arbitrary texture mapping would additionally require surface-coordinate interpolation. The current three constant selectors are not texture coordinates.

Preclipping far polygons against nearer coverage is another way to produce interior-disjoint fragments for the existing XOR aggregate. It trades framebuffer merge work for geometry/visibility work; it is not automatically cheaper on the 6510.

## Practical scope for a first panel prototype

Choose the geometric and color restrictions first. Six parallel, outward-translated cube-face quads allow the bounded two-layer approach above, with either two-tone palette priority or richer mask composition. General independently rotating cards need a verified painter order with masked overwrite, plus a fallback for cycles/intersections, or explicit visible-span resolution.

In either case, reuse the exact edge-crossing rule, column-major charset layout, buffer/field histories, and marker-reset discipline. Replace the closed-mesh adjacency requirement, orientation policy, model-specific Z shortcut, and aggregate composition rule where they no longer apply. Recheck camera/near-plane and screen bounds for the enlarged panel motion, update dirty bounds for the union of all panels, and measure the whole new renderer before promising its cadence. No renderer or test changes were made for this assessment.
