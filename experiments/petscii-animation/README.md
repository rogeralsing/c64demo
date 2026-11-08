# Prepared PETSCII animation

An original standalone counterpart to **The Hat's prepared PETSCII artwork**.
The [owning research note](../../docs/research/february-2026.md) records artist
redcrab's statement about 500 animation frames available as GIFs, linked from
the [production notes](https://csdb.dk/release/?id=259070&show=notes). That
statement establishes prepared artwork. It does not establish its released
packing or playback algorithm. The Hat's final all-border upscroller is a
separate, unresolved mechanism and is not represented by this example.

This example has **16 own frames**, an own player and own colored orbital
ring/disc artwork. The host prepares 40×25 screen-code and foreground-color
matrices. The moving shapes use the actual C64 uppercase/graphics ROM's 16
quadrant block patterns, giving an 80×50 semigraphic grid; titles use that
same ROM. These are PETSCII graphics represented as VIC screen codes, not a
PETSCII control-code stream or a substituted ASCII/RAM font.

```sh
sh experiments/petscii-animation/build.sh
sh experiments/petscii-animation/run.sh
python3 experiments/petscii-animation/verify.py
```

Requirements are the repository's existing KickAssembler/Java, Python/Pillow
and VICE `x64sc`. The normal runner uses PAL 6569, speed 100, with warp and
autostart warp disabled. It uses VICE's installed character ROM; no ROM bytes
are redistributed. Output stays in this folder's ignored `build/`.

## Representation and publication

Each raw frame contains 1,024 screen bytes followed by 1,024 color-shadow
bytes, including 24 unused padding cells. Sixteen frames total 32,768 bytes.
The side-effect-free `compress(raw)` function is imported from
[`prepared-bubbles/prepare.py`](../prepared-bubbles/prepare.py); its byte-command
format encodes literal runs or an 8-bit backward distance with forward
overlapping matches. This is an Oscar64-compatible stream, not standard
LZO1X. The prepared scene occupies **4,700 compressed bytes**, plus 32 pointer
bytes. Neither its scene renderer nor its sprite player is copied.

The C64 decodes the next complete 2 KiB frame into the hidden buffer using
this example's own decoder. It then waits for a new PAL field and uploads
the hidden color shadow into the single physical ColorRAM behind the beam:
row `r` starts no earlier than raster `59 + 8r`, after all eight visible
scanlines of the old row. The old screen remains selected for that whole
field. A ready flag is set after all 1,000 stores; the next raster-0 IRQ
publishes the new screen with `$d018`. Thus an upload field contains old
pixels even when a late RAM dump already contains the next frame's colors.
No blank field or partially decoded screen is published.

Memory:

| Range | Use |
| --- | --- |
| `$0801–$080c` | BASIC startup |
| `$1000–$11b3` | CPU player and IRQ code in RAM beneath VIC ROM addressing |
| `$2000–$23ff`, `$2400–$27ff` | Screen A and color shadow A |
| `$2800–$2bff`, `$2c00–$2fff` | Screen B and color shadow B |
| `$4000–$59e1` | Unrolled beam-following color-upload kernel |
| `$6000–$727b` | Frame pointers and compressed original art |

VIC bank 0 with `$d018=$84/$a4` selects these two screens and the real ROM
at VIC `$1000`; CPU code at RAM `$1000` is not a character set. Hires text
mode, 25 rows, no sprites, black background/border. Normal PRG LOAD ends at
`$727b`, below I/O. No disk loader or streamed playback is claimed.

## Native evidence and cadence

The default verifier passed **129 PAL fields**, including all 16 normal
publications, alternating buffers and wrap from frame 15 to frame 0.
Every interval between publications was **8 fields / 157,248 PAL clocks**:
about **6.27 animation frames/s**, while VIC scanout continues at about
50.12 fields/s. A steady 16-frame cycle is 128 fields, about 2.55 seconds.
The first presentation's startup alignment can vary by one field; the
measured steady interval is recorded rather than inferred from a counter.

The one native verifier independently checks:

- Every packed frame against its raw screen/color asset, including 344
  overlapping matches, then each live 2 KiB hidden decode before upload.
- All 16 quadrant masks against physical ROM glyph bytes, native ROM/bank
  selection, and the complete visible screen/color shadow at every observed
  decode and field boundary.
- All 1,024 physical ColorRAM bytes each field and all **16,000 active-cell
  stores**, in address order with values and per-row scanout deadlines.
  In this run the final row finished by raster 262/cycle 33, at least
  **3,117 clocks before the next field origin**.
- Every pixel of each **384×272** native screenshot: **13,473,792 pixels**,
  including the full 320×200 display and borders. Expected pixels come from
  prepared asset bytes plus the actual ROM, independently of the host art
  renderer and C64 player. Upload fields must still match the old complete
  frame despite their new physical ColorRAM values.
- Exact 19,656-clock field intervals, frame order and complete loop/wrap.
  The monitor observes natural program boundaries and never patches RAM,
  changes the PC or enables production test modes.

Receipt: `build/verification/receipt.json`; complete images and monitor trace
are alongside it. `petscii-animation.gif` is the captured field sequence,
rounded to 20 ms per PAL field, including initial presentation and wrap.
The verifier closes its owned VICE process even on failure.

Verified PRG SHA-256:
`7b772c0ab4d9243156b2951611cd1ec8b36e96e38b3d5abfc006764cc31d0652`.
The ROM input was VICE's 4,096-byte `chargen-901225-01.bin`, SHA-256
`fd0d53b8480e86163ac98998976c72cc58d5dd8eb824ed7b829774e74213b420`.
The verifier resolves and explicitly supplies the installed ROM and records
its hash rather than depending on an ignored research file.

This proves an own prepared PETSCII player on PAL 6569 digital emulation.
It does not claim the original 500 frames, original art, original codec or
player, an all-border display, runtime geometry, an expanded physical palette,
analog temporal blending or physical-machine verification.
