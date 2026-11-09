# Aloft ribbons: forty character-row bytes and a matching retained cache

Research date: 9 November 2026. The cell addresses reveal a compact graphics
layout: **all 312 admitted routines write within row7 of just forty glyphs**
under charset `$0000`. The original initializer constructs a forty-character
screen row naming exactly those glyphs. In the retained pre-IRQ snapshot,
all forty cached character codes and color nibbles equal that source layout.

This explains the small working set behind the generated programs. It is
not yet a complete explanation of the displayed raster field. That snapshot
has RC7 but is idle, with VC/VCBASE0 and badlines disabled. A future execution
witness must establish when character fetches actually use those bytes and
whether the cache remains unchanged.

## The source constructs one specific character row

The [generator proof](aloft-cells-20261109.md) independently binds all source
bytes and the adjacent `$F43D` initializer. Its first loop writes Color RAM
`$DBC0..$DBE7` with `$08`. The next loop fills screen addresses
`$07C0..$07E7` with:

```text
00 01 02 ... 16 17 18 F0 19 F1 1A F2 1B F3 1C F4 1D F5 1E F6 1F F7
```

For screen base `$0400`, these are row24, columns0..39. The finite source
formula is `row[c]=c` for the first24 columns, followed by pairs
`$18+k,$F0+k` for `k=0..7`. Original `EOR #$E8` produces the second member
of each pair; the row stops after forty columns.

The forty codes are unique. Their set is `$00..$1F` plus `$F0..$F7`.
The same initializer sets these forty row7 bytes to `$FF`:

| Glyph codes | Row7 RAM addresses | Count |
| --- | --- | ---: |
| `$00..$1F` | `$0007 + 8*i`, `i=0..31` |32 |
| `$F0..$F7` | `$0787 + 8*i`, `i=0..7` |8 |

These are source predictions, produced before either native RAM comparison.
Both retained pre-`$F02B` and pre-`$F080` captures match all forty matrix
bytes, all forty glyph-initial bytes and all forty device Color RAM nibbles.
The later equality does not prove every intervening reset or write.

## Every admitted cell uses the same forty-byte set

The [cell-semantics contract](aloft-cell-semantics-20261109.md) identifies four
operand roles: two state slots, a lookup-result scratch slot and an absolute
lookup-result destination. Across all 312 source-predicted cells, each address
is below `$0800` and its low three bits are7. Both the operand-address union
and the actual-store union are **exactly the forty initialized addresses**.
The eight boundary cases' suppressed stores do not enlarge that union.

STX/STY state slots alone cover only21 glyphs, `$00..$14`. The other result
destinations complete the forty-glyph union. It would be incorrect to call
all forty addresses STX/STY state slots, or to infer dynamic coverage of all
forty from one selected sequence of69 call targets.

The descriptor field `screen_address` is a name for an absolute store operand,
not proof that the VIC consumes that location as a matrix byte. Under bank0,
charset `$0000`, character mode and RC7, its address instead has the glyph
interpretation `8*characterCode+7`. The same formula applies to the state and
scratch destinations. The `$0400..$04FF` bit-reversal lookup is disjoint from
this working set and supplies transformed pixel-pattern bytes.

There is also a deliberate physical alias:

| Address | Glyph interpretation at charset `$0000` | Matrix interpretation at screen `$0400` |
| --- | --- | --- |
| `$0787` | Glyph `$F0`, row7 | Row22, column23 |
| `$07BF` | Glyph `$F7`, row7 | Row23, column39 |

These are simultaneous address interpretations, not separate memory types.
All forty glyph sinks are disjoint from the initialized matrix row24 at
`$07C0..$07E7`; some sinks do overlap earlier matrix rows. Describing them as
“not screen RAM” would hide that alias and could give a wrong future fetch model.

## The retained cache already matches the constructed row

At the genuine stopped pre-IRQ `$F080` input, the
[machine context](aloft-cell-context-20261109.md) has stored `$D018=$10`,
`$D016=$18`, `$D011=$10`, and logical bank0 with no pending GLUE alarm.
Those stopped selectors are consistent with screen `$0400`, charset `$0000`
and multicolor text. Each of the forty relevant device color nibbles is8.
The mode's multicolor flag therefore selects paired bits for those characters:
forty eight-pixel cells represent320 physical pixels, or160 multicolor samples.
This geometry is conditional on those selectors and the actual fetch state.
The [primary VIC reading](aloft-cell-primary-20261109.md) owns the mode rules.

More specifically, the pinned VIC1.3 snapshot contains:

```text
VBUF[0..39] = the forty source-constructed character codes
CBUF[0..39] = $08 in every slot
RC = 7; VC = VCBASE = 0
idle = 1; bad_line = 0; allow_bad_lines = 0
```

Official `viciisc/vicii-fetch.c` calculates a character graphics address from
**cached** `VBUF[VMLI]`, RC and the charset bits of `$D018`. It does not
re-read the live matrix code for every character graphics access. The new
[address-only source anchor](../../build/research/aloft-cells-20261109/glyph-analysis/accepted-01/primary-glyph-source.json)
retains the exact official member and relevant function, including separate
bitmap and ECM paths. If character mode, bank0, charset0 and RC7 apply at a
future graphics access, the forty cached codes select exactly the forty
glyph-row addresses above.

Cache-value equality does **not** identify the physical matrix access that
loaded it, nor prove it persists during later drawing. RC7 while idle is not
an active graphics fetch. The source also has mode-delay, fetch/bus and bank
dependencies outside the address expression. The retained orientation image
is not an independently reconstructed pixel oracle.

## Verified interpretation and next witness

The source layout and cache values support a raster-line renderer using a
forty-byte character-row working set, rather than requiring a complete image
buffer for the cell writes. This is an interpretation supported by the
address map, initializer and retained cache. Its field-level realization still
requires the actual ordered glyph updates, `$D011` read/dummy/final accesses,
badline/RC evolution and character fetches. In particular, the distinction
between FLD and a late-badline technique cannot be settled from `INC $D011`
alone.

The new [glyph mapper](../../research/aloft-cells-20261109/glyph_mapping.py)
uses original source and source-predicted cell descriptors. It writes the
matrix/color/glyph predictions before opening either native RAM oracle. Its
[accepted proof](../../build/research/aloft-cells-20261109/glyph-analysis/accepted-01/glyph-mapping-proof.json)
is 4,849 bytes, SHA-256
`64d053eefd919df04025e2300efc4630860d6b9fb1b332b78960367b43ed3fc0`.
A fresh [self replay](../../build/research/aloft-cells-20261109/glyph-analysis/self-replay-check.json)
reproduces all eight outputs / 316,663 bytes exactly. Independent full-source
peer review and another fresh replay reproduce the same eight files.
The [peer report](../../build/research/aloft-cells-20261109/glyph-analysis/peer-replay-check.json)
is 6,777 bytes, SHA-256
`e6bc95bab2a08320ee6b49e66005f7240d12793ca0a98710a6028773f7572d17`.
It independently confirms all forty cached codes/colors while preserving the
fetch, lifetime and pixel limits. Earlier generator, semantics, context and
reading producers remain unchanged.

```sh
rtk proxy python3 -B research/aloft-cells-20261109/glyph_mapping.py \
  --output build/research/aloft-cells-20261109/glyph-analysis/replay-NEW
```

Next capture genuine pre-`$0500` inputs and a cell or chain return in a new
owned original-disk case. Check glyph writes at their actual times and the
retained cache/RC/fetch behavior. Preserve CMP/NOP read uncertainties, CPU
ports and physical aliases. Full pixels, animation/FPS, physical timing and
the named three-layer scene remain separate open work; the broad research
goal remains active.
