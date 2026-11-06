# YKTR Glenz: observations from the original program

We inspected Cruzer/Camelot's **You Know The Routine**, released on 19 January 2004, to verify the immediate-EOR technique against a running implementation. This is the first demo, not YKTR2. Its disk contains `02 - glenz trash`.

The archive came from [SCS-TRC](ftp://ftp.scs-trc.net/pub/c64/Demos/pal/c/Camelot/You_know_the_Routine.zip). Its SHA-256 is `8f999bb5f2ceb856a919abf6908903e0e11e87747d3f8063b93f5686433cdbef`; the extracted part's SHA-256 is `9d00ba72febe0ec34420a8f7773cc5578613eb6dd586781f943b1bb69a85b41a`. See the [production listing](https://c64.ch/productions/2841/You_Know_The_Routine) and [Cruzer's implementation notes](https://codebase64.net/doku.php?id=base%3Acolorcycleplasma).

## Confirmed in unpacked RAM

The main loop calls the filler at `$9000`, then calls a separate reset routine at `$8040`. The filler contains 376 five-byte cells, each using an immediate EOR followed by an absolute store. Twelve additional cells seed the running value.

The reset routine has 376 stores targeting those immediate marker operands, plus twelve stores restoring the seed operands. A live observation found 66 nonzero marker operands before reset. After reset, all 376 markers were zero and all twelve seeds were `$ff`. The program clears its edge operands separately; it does not redraw old edges or apply a second prefix fill to clear the displayed image.

The nominal instruction costs are 2,370 cycles for the filler and 1,576 for reset, excluding caller overhead, interrupts, and VIC-II stalls. These are not complete-frame measurements.

The line routine at `$383f` reads an 8 KB table region at `$4000..$5fff` and enters generated plotting code at `$7000`. A row-address table stores scaled offsets. Plotting toggles filler operands through a zero-page pointer. The endpoint is temporarily changed to RTS and restored afterward, matching the generated-entry technique used in our renderer.

Reconstructing its initializer reproduced all 8,192 table bytes exactly. It selects 131 representative slopes from an 8.8 fixed-point enumeration. This quantizes the available directions: one internal endpoint request for a slope of 1/10 selects 1/8, producing a different row at sample nine on that internal grid. Runtime parity adjustments mean this example should not be interpreted as a claim about the demo's external raster convention.

## Limits and implications

The original filler has a 48-row logical window and writes every second physical scanline. Its four-bit masks also group neighboring multicolor pixels. The row-address table maps rows 0..47 to offsets `5*y+1`, ranging from 1 to 236, so these addresses fit in one byte. Our 128-row canvas needs offsets up to 636 for that instruction layout. The original's viewport and quantized slopes therefore cannot be adopted unchanged while preserving our exact pixels.

For our renderer, operand reset and scaled-row addressing must be included in the benchmark. Six cycles for an immediate-EOR/store pair alone omits both costs. An inline reset makes each cell eight bytes and ten cycles; it can also let filling overwrite stale output directly.

Local evidence is retained under `build/research/yktr1/`: unpacked RAM, native capture, disassembly, decoded operand mappings, and a live before/after reset proof. Those third-party binaries are ignored build artifacts.
