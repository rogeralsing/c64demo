# NUFLI: Mufflon's embedded viewer and the data behind the picture

The interesting part of NUFLI is the combination of a hires bitmap, six
expanded sprite underlays, two left-edge repair sprites and a generated
raster program. The image has 320×200 static pixels; it is not a bitmap with
an unrestricted colour byte per pixel. This note inspects Mufflon 1.0's actual
embedded viewer and four pictures bundled with its source release. It does
not establish that Crest Slide Story's earlier slideshow uses this identical
viewer. See [the frontier overview](frontier-demos.md) for that production's
credits and release context.

The later [native validation](nufli-native.md) runs the original Smoking Fish
viewer and compares two complete 64,000-pixel captures with the independently
decoded indices. It also records the research checker's corrected picture
origin. That single-picture result is separate from the source/format checks
below and does not establish every picture or the later PAL/NTSC player.
The native note also contains a separate audit of this project's current
converter and its newer r1440 player: its fitted/exported reference picture
matches three PAL captures. NTSC and other physical VIC revisions remain
outside those measured results.

## Original material and identity

The primary source is the [Mufflon 1.0 release](https://csdb.dk/release/?id=93314),
including its [source, GUI and bonus archive](https://csdb.dk/getinternalfile.php/180585/Mufflon1.0-source+GUI+Bonus.zip).
The author README credits Bitbreaker with the converter, Crossbow with the
NUFLI/MUIFLI formats and C64 editors, and DeeKay with the concept, conversion
strategies, sample pictures and README. The C code is `mufflon.c`; its
`convert_nufli()` begins at line 1244, and the three embedded viewer arrays are
in `mufflon.h:571..604`.

The ZIP SHA-256 is
`c610bc91ec7f60bd7c19c19fe0ecc4e97288a26b12e65febad3827da1f4d4adf`.
Our extraction compares the inspected C/H/README and both D64s directly with
their ZIP members. All three embedded blocks match byte-for-byte in all four
unpacked bundled NUFs: Smoking Fish, Forgotten, Oldsmobil and Wrong Way.
This is source-to-packaged-picture identity, not a claim that a newly compiled
converter reproduces every original conversion choice. The five bundled MUI
files are a different format and were excluded.

The inspected viewer is **PAL-only**. In the later
[NUFLI Editor 1.12 release notes](https://csdb.dk/release/?id=95473&show=notes),
DeeKay explicitly describes Crossbow's PAL/NTSC replacement and the older
PAL-only viewers emitted by Mufflon. Do not generalize the following bytes
or timing to that replacement.

## What occupies memory

`write_result()` emits the load word `$2000`, then `$5a00` data bytes:
**23,042 bytes total**, occupying `$2000..$79ff`. The entry is `$3000`, not
the load address. Offsets below are relative to the file payload, after its
two-byte load word. These regions interleave with deliberately placed screen
and sprite chunks; they are not one linear conventional bitmap file.

| Data or code | File offset / CPU address | Role |
|---|---|---|
| First 5,120 bitmap bytes | offset`$4000..$53ff`, RAM`$6000..$73ff` | Bitmap image rows0..127 |
| Last 2,880 bitmap bytes | offset`$1400..$1f3f`, RAM`$3400..$3f3f` | Bitmap image rows128..199 |
| Six 101-entry switch tables | offsets`$0400,$0480,$0800,$0880,$0c00,$0c80` | Initial six sprite colours plus100 colour/control phases |
| Startup, generator and IRQ code | `$3000..$31f4` | 501 original bytes |
| Template, tables, switch helper and tail | `$3300..$33d5` | 214 bytes, including data |
| Initial VIC register image | `$3fc0..$3fef` | 48 bytes copied to`$d000..$d02f` |
| Initial left-edge colours | `$3ff0,$3ff1,$3ff6,$3ff7` | `$d026,$d025,$d02e,$d027` respectively |
| Generated raster code | `$1000..$1f41` | **3,906 bytes**, generated at startup |

The writer's four 100-entry address tables describe the matrix rows and three
classes of sprite chunks. Our decoder derives their addresses independently
with arithmetic and checks **all 400 entries** against the original tables.
Normal underlay chunks are interleaved with screen matrices; sprite 6 has a
special top-half store at RAM`$7400..$75ff`. The two repair-sprite stores for
the top half are at`$7600..$77ff` and`$7800..$79ff`. Lower-half chunks reuse
RAM in the first16KB VIC bank. Twelve eight-byte sprite-pointer tables are
also copied into the picture's different screen matrices.

The top bitmap is displayed from VIC bank`$4000`, bitmap base`$6000`.
The lower image switches to VIC bank`$0000`, bitmap base`$2000`: its continuing
bitmap address counter reaches the stored bytes at`$3400`. Startup copies
`$2280..$22a7` to`$0280..$02a7`, the first lower matrix row that could not be
loaded at its eventual low-RAM address in the NUF file.

## Bitmap and sprite ownership

The initial VIC image sets `$d016=$08`: hires bitmap pixels, not multicolour
bitmap pairs. A bitmap1 selects the screen byte's high-nibble ink; bitmap0
exposes its low-nibble paper unless a sprite underneath is opaque. Both
colours therefore come from screen RAM. The viewer does not stream colour
RAM for the ordinary picture.

Sprites 1..6 are hires and expanded horizontally (`$d01d=$7e`). They cover
image x24..311 in six 48-pixel regions. Each sprite bit occupies two hires
pixels, while the bitmap can select ink independently on either of those
pixels. One sprite colour is shared over that 48-pixel region; the rightmost
eight image pixels have no normal sprite underlay. This explains why “three
arbitrary colours in every8×2 block” is an incomplete description: the third
colour has a larger horizontal sharing constraint, and some pairs of colour
choices cannot coexist under one expanded sprite bit.

At image x0..23, sprite 0 is hires and sprite 7 is multicolour
(`$d01c=$80`), both unexpanded in X. `$d01b=$ff` places all sprites behind
foreground bitmap pixels. Sprite0 has higher sprite priority than sprite 7.
The multicolour codes1/2/3 use`$d025/$d02e/$d026`; the hires repair sprite
uses`$d027`. Mufflon models the left FLI-bug region with ordinary AFLI ink
and paper in the first two lines of each eight-line group; later lines have
the fixed light-grey ink 15 plus sprite colours. All four bundled examples
cover every otherwise-transparent left-edge pixel in those later lines.

The two vertical colour grids differ. Bitmap ink/paper pairs start at even
image y. Normal sprite colour entry i>0 starts at y=`2*i-1`; the left-edge
colour changes use y=`2*i`. That stagger is present in the original writer,
not an approximation added by our decoder. DeeKay also describes the original
even/odd design in the later
[author discussion](https://csdb.dk/forums/?firstpost=40&roomid=11&topicid=168587).

## Generator and raster mechanism

`$3000` installs the first IRQ vector, initializes the VIC, and generates 100
phases from the six switch tables. The four phase variants are
**38/40/40/38 bytes**, repeated 25 times, followed by a six-byte tail:
`25*(38+40+40+38)+6 = 3906`. The output is straight-line raster code, with
colour constants and register addresses already embedded. There is no
per-picture-line loop or six-table lookup in the displayed raster body.

The helper at`$33b0` interprets each switch-table byte as follows:

| High nibble | Generated action |
|---|---|
| `0` | Write that byte to the slot's normal sprite colour`$d028..$d02d` |
| `1` | Write`$d4` to`$d000+(low nibble)`; the converter reserves eight such slots for the sprite Y-position handoff |
| `2` | Write the byte to border`$d020` |
| other | Write the byte to`$d020+(high nibble)`; e.g.5/6/7/e select the four left-edge sprite colour registers |

The VIC uses the relevant low colour bits. A slot whose normal sprite colour
need not change can thus service another register without enlarging the
raster body. `find_free_register_switches()` and `set_8_switches()` allocate
these opportunities; scarce switch slots are part of the image constraints.

The startup programs a raster IRQ at41; the first handler at`$3110` arms
line 42 and permits a second IRQ. `$3130` discards the nested IRQ stack frame
and applies the short jitter correction before setting up the image. It
preserves CIA2's upper port bits while selecting the top VIC bank. Sprite Y
registers are first set to 43 and then 170. The tightly placed
`STY $d017 / STA $d018,Y / STY $d017` sequence uses Y=`$ff`; the indexed store
lands at`$d117`, a VIC mirror of`$d017`. This expansion-register manipulation
is part of the sprite-row trick; replacing it with ordinary sprite motion
would not preserve the display.

The generated body cycles`$d011` through`$38/$3a/$3c/$3e` while selecting screen
matrices through`$d018`. It therefore implements every-other-line FLI and
sprite colour updates. The phase63 screen-selection store at`$19bd` is
patched to`STY $dd00`, switching to the lower VIC bank. The body ends with
`LDY #$10 / STY $d011 / RTS`, and the IRQ handler rearms line 41 for the next
frame. Exact beam positions and sprite crunch/fetch behaviour require the
VIC, not just a CPU instruction count.

## Finite checks and decoded sample

The [reproduction scripts](../../research/nufli/README.md) check the following:

- The original `$3000..$3108` generator executes in flat RAM for all four
  NUFs: **150,974 original instructions** total. Its generated bytes and 100
  phase starts match a separate host builder exactly. Low-RAM copies and
  sprite-pointer setup are also checked.
- Every possible switch byte in each of six slots is compared against the
  original `$33b0` CPU helper: **1,536 cases**.
- Each original generated body executes unchanged and produces exactly 801
  register-store instructions, independently checked against the format:
  600 colour/control slots, 100`$d011` phases, 99`$d018` stores, one bank switch,
  and the final`$d011` store. Each body takes**4,736 nominal CPU cycles**,
  including RTS. **This omits VIC stalls, IRQ setup and physical bus timing;
  it is not the wall-clock time occupied on a C64.**
- The separate logical decoder checks 400 address-table entries, decodes all
  four pictures to 64,000 palette indices each, and records plane ownership.

Receipts: [extraction](../../build/research/nufli/extraction.json),
[generator validation](../../build/research/nufli/generator-validation.json),
[logical decode](../../build/research/nufli/decode-validation.json).
The [Smoking Fish logical composite](../../build/research/nufli/02-SMOKING_FISH.NUF-logical.png)
contains 28,421 bitmap-ink pixels, 16,685 paper pixels, 14,552 normal-sprite
pixels and 4,342 repair-sprite pixels. This establishes what the independently
decoded layers contribute; the PNG is not a native capture. Its nearest
palette-index agreement with the bundled input art is 56,309/64,000. That
input BMP is not a lossless oracle for the saved NUF, so disagreements are
not assigned wholly to conversion or to decoding.

No analog display, border-rasterbar placement, native VIC/IRQ/DMA behaviour,
NTSC compatibility, editor interaction or original slideshow loader has been
validated in this lane. The code-generation and format checks should not be
read as those broader claims.

## Bounded native handoff

Use the original extracted
`build/research/nufli/amigaconverts+samples/02-SMOKING_FISH.NUF.prg`:
SHA-256`f44e6c1c3285683d2d73864e6d676e68539b77beb3e43daabd4a22adaa929093`.
On a reset PAL C64, load the PRG normally respecting its embedded`$2000`
address, then use the author's documented **SYS 12288 / JMP$3000** entry.
Do not assume BASIC RUN/autostart from the file's load address. The README
explicitly documents that every unpacked NUF contains its viewer and
speedcode generator.

Keep normal reset/BASIC mapping and CIA direction state: KERNAL ROM and I/O
must remain visible (normally`$01=$37`), CIA2 PA0/1 must be outputs, and the
normal KERNAL IRQ prologue/`$ea81` exit must be available. The viewer replaces
`$0314/15` and never returns to BASIC. In addition to the loaded image and
generated code, it writes zero-page scratch`$02,$03,$3a,$fb/$fc` and setup
copies at`$0280..$02a7,$03f8..$03ff,$07f8..$07ff,$33d8..$33ff,$7ff8..$7fff`.
These are preconditions and an ownership map for a native check, not a claim
that such a check has already run.
