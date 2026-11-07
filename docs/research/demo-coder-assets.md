# Demo Coder: stream 46's stored Rubicon picture

Research date: 7 November 2026. **Stream 46 stores the unreleased Rubicon loading picture, rather than MEGA Dudes.** A passive ordinary multicolor decode produces the recognizable sunglasses portrait, RUBICON logo and HEWSON lettering. This identifies the stored artwork; it does not reconstruct the raster program's frame or establish its complete stretch transform.

The release author, Trident, says the **FLD-with-stretch** effect uses an unreleased loading picture from The Sarge's Rubicon, dating it to 1991. His separate description assigns the Eyes crew picture to MEGA. The image decoded here agrees with the Rubicon description. [Author's 25 November 2024 release comment](https://csdb.dk/release/index.php?id=247776)

![Ordinary multicolor decode of the first 176 stored lines](../../build/research/demo-coder/asset-analysis/original-first-176-lines.png)

This PNG is a **storage diagnostic**, with the actual initialized Color RAM and background color. It is not a VIC frame oracle.

## Exact inputs and decoding rule

The input is the complete `046-2000-unpacked.prg`: 40,963 file bytes, comprising its two-byte load address and the 40,961-byte `$2000..$C000` payload. The payload SHA-256 is `3be2386eeb9c9f0d3bb274eab04fd7aa48f7df3b3a10199df3d49cecaabec31c`. The tool also reads the closed native session's `selector-entry`, `selector-initialized` and `selector-visible-c` RAM/VSF pairs. Each 65,536-byte RAM file must equal the physical RAM in its corresponding VSF. It reads the existing pinned VICE 3.10 snapshot parser without starting a CPU, drive or emulator.

For ordinary multicolor bitmap mode, each two-bit value selects background `$D021`, screen high nibble, screen low nibble, or physical Color RAM low nibble, respectively. Each logical pixel occupies two horizontal pixels. These are the documented Commodore rules. [Programmer's Reference Guide, page 128](https://www.devili.iki.fi/Computers/Commodore/C64/Programmers_Reference/Chapter_3/page_128.html)

For cell `c = 40*(y//8) + column`, the decoder reads bitmap byte `base + 8*c + (y&7)`, screen byte `screen+c`, and physical Color RAM cell `c`. It uses background **0**, from both initialized and visible-C VIC state. Color RAM comes from the VIC snapshot module, not ordinary RAM underneath `$D800`. Its first 1,000 cells equal the low nibbles of the original `$4000..$43E7` source; the final 24 retain their entry values. The RGB palette is the repository's Colodore palette; PNGs preserve exact color indices without filtering or blending.

## Independent artwork match

The linked [C64GFX artwork page](https://c64gfx.com/image/9993572) names **Unreleased Rubicon Loading Screen**, credits **The Sarge**, and identifies its release as The Demo Coder. Its [linked PNG](https://d2certfx9n6wgt.cloudfront.net/artwork/9993572.png?v=7103e964) is archived unchanged: 7,191 bytes, SHA-256 `7018bb0f9df0160323771e70be287801da8100d64ea505cb9ecc8b36c4e4ae34`. The gallery is corroborating image evidence; Trident's release comment supplies the primary author statement about the effect and artwork.

The gallery PNG uses a different RGB palette. The checker therefore compares **palette classes**, requiring a one-to-one mapping between all 12 used colors:

- The first 176 decoded lines match **all 56,320 pixels** at gallery offset `(32,35)`, with zero differences.
- The remaining 128 bitmap bytes, representing the first 16 cells of the next character row, match another **1,024 pixels** at source `(0,176)`, again with zero differences.

Thus all pixels represented by the stored 7,168-byte bitmap prefix match the Rubicon image under that color mapping. This is not byte equality with an original graphics-format file, nor RGB equality with the gallery PNG. The receipt retains every tested vertical offset, including the nonmatching trials, the mapping, PNG palette and hashes. The archived gallery HTML is SHA-256 `f2d16f8deb19ff119b69edbe0633578a13fa3decf3e00e0a67e364310834a511`. The existing archived author release page is SHA-256 `5ab1d02d6ff5df51dabaf3c7387bf13c1cbc60432309111d67e8f0394b02301c`.

## Storage and shifted copies

The stream does **not** hold a conventional contiguous 200-line bitmap at `$2000` alongside a nonoverlapping screen at `$3C00`. An ordinary 320×200 bitmap consumes 8,000 displayed bytes within an 8 KiB allocation. Here, `$3C00` begins after only **7,168 bytes**, or 896 cells: 22 complete character rows and the first 16 cells of row 22.

| Role | Original or initialized range | Established content |
|---|---|---|
| Bitmap prefix | `$2000..$3BFF` | 7,168 original picture bytes. |
| Screen attributes | `$3C00..$3FE7` | 1,000 original bytes, copied unchanged to `$5C00`, `$DC00` and `$FC00`. |
| Color source | Original `$4000..$43E7` | Its low nibbles initialize physical Color RAM before this RAM is overwritten by a shifted bitmap copy. |
| Shifted bitmap 1 | `$4000..$5BFF` | Exactly original `$2001..$3C00`, a one-byte source offset. |
| Shifted bitmap 2 | `$C000..$DBFF` | Exactly original `$2002..$3C01`, a two-byte source offset. |
| Clear bitmap prefix | `$E000..$FBFF` | 7,168 zero bytes. |

The full [200-line ordinary decode](../../build/research/demo-coder/asset-analysis/original-ordinary-mc.png) deliberately reads **832 screen bytes as bitmap data** near its bottom. Its resulting clutter is a falsifying result for a complete ordinary 200-line interpretation, not recovered picture detail. With the same gallery alignment and palette mapping, all differences begin at line 176; the last 24 lines contain 5,026 differing pixels.

The shifts operate on the bitmap's **byte-row storage**. In each eight-byte cell, +1 selects the next row for seven positions, then crosses into the next cell on the eighth. +2 selects a row two ahead for six positions, then crosses into the next cell for two. Across 896 copied cells, that gives respectively **896** and **1,792** cross-cell bytes. The final one/two source bytes also cross into the screen source. They are not ordinary vertically shifted copies of the whole picture. The diagnostic [plus-one](../../build/research/demo-coder/asset-analysis/initialized-plus1-ordinary-mc.png) and [plus-two](../../build/research/demo-coder/asset-analysis/initialized-plus2-ordinary-mc.png) renders retain these discontinuities.

All **21 byte contracts pass** at initialized and visible-C state: the original prefix, both shifted copies, cleared prefix, four screen copies and physical Color RAM remain exact. Ordinary color-index renders of each populated bank are identical between initialization and visible C. The result rules out missing or changed stored artwork as the explanation for the thin native bands.

## What the thin native bands do and do not establish

The [native visible-C PNG](../../build/research/demo-coder/native-01/selector-visible-c.png) remains an original-program output observation. Its same-stop state is PC `$6336`, clock **265,804,255**, raster **251**, raw cycle **10**, before the escape handler's teardown store. It has `$D011=$75`, `$D016=$18`, `$D018=$FB`, CIA2 port A `$FB`, and both border flags set. This one instant cannot describe all modes and addresses used while the preceding image was drawn.

The ordinary decoder deliberately ignores time-varying ECM/bitmap mode, bank selection, RC/VC, matrix fetches and borders. The [separate raster investigation](demo-coder-raster.md) owns those measured transitions, including ECM gating, repeated RC=0 observations, later RC progression and the late badline pulse. Unchanged image bytes are compatible with a very different raster presentation. These passive renders cannot determine the exact cause of every band or supply the missing complete-frame transform.

The asset evidence supports a **Rubicon artwork identity**, consistent with the author's FLD-with-stretch description. It does not assign the stream to MEGA, prove that every source row is stretched, establish historical priority, or turn an ordinary bitmap decoder into a physical-VIC pixel oracle.

## Reproduction and receipt

```sh
rtk proxy python3 research/demo-coder/decode_assets.py
```

This reads existing local inputs and emits nine analysis PNGs plus [the structured receipt](../../build/research/demo-coder/asset-analysis/asset-evidence.json). To archive the two public gallery resources first, add `--fetch-reference`; each download is bounded to 1 MiB and the expected PNG hash is pinned. HTTP status, final URL, headers, retrieval time and raw-byte hashes remain in `reference/acquisition.json`. All third-party bytes and generated outputs remain under ignored `build/`.

The [decoder](../../research/demo-coder/decode_assets.py), SHA-256 `6a853a29182e7a04adff8417ded960ec71e0be44e85b062467f8d0633c075e64`, uses only the standard library and the existing passive snapshot reader. Final receipt SHA-256: **`ebf8dc31608f6ea830cbbabcd1efe447b3bde063960b82074b9319bb25b99885`**. No CPU or emulator was executed for this analysis.
