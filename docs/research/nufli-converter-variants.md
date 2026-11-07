# NUFLI converter: four native exports and a verifier race fix

Four exports from the actual adjacent `c64` converter now match their fitted
previews in **12 PAL VICE captures**, three per picture. Independent checks
compare every pixel at the fixed `(32,32)` image origin: **768,000 RGB samples,
zero mismatches**. This extends the earlier
[Smoking Fish investigation](nufli-native.md) to three additional inputs.

The extension also exposed a real bug in the application's VICE verification
script. Its socket reader treated 150 ms without data as command completion.
That could return while VICE was still writing a screenshot. The reader is
fixed and the native reruns pass. No viewer or exporter color-calculation
defect was established by these checks.

## Actual fitter and public exporters

The [variant harness](../../research/nufli/converter_variants.cjs) loads the
real `fli.js`, `nufli-data.js`, `nufli.js` and `nufli-export.js` through the
application's existing VM fixtures. It uses the actual Colodore palette,
fitter, NUF exporter and executable-PRG exporter. It edits no application files
and starts no emulator.

The three new targets are host-decoded palette images from Forgotten,
Oldsmobil and Wrong Way. Their original files and decoded input bytes are
hash-pinned. The new check does **not** claim that these three old original
players have been checked natively. They supply arbitrary legal palette-image
targets; the native acceptance target is each new fit's declared preview.
Smoking Fish remains the separately native-proved original-player reference.

Two file decoders check every new export: the application's separate test
decoder and the independent Python address-formula decoder. Each matches all
64,000 fitted preview indices. Each PRG's embedded picture payload also matches
the public NUF export exactly. All fitted RGB values are actual palette colors
with opaque alpha.

| Target | Fitted pixels changed from input | Preview/export mismatches | Native captures | Fixed-origin native mismatches |
| --- | ---: | ---: | ---: | ---: |
| Smoking Fish | 0 | 0 | 3 | 0 |
| Forgotten | 6 | 0 | 3 | 0 |
| Oldsmobil | 47 | 0 | 3 | 0 |
| Wrong Way | 0 | 0 | 3 | 0 |

The 6 and 47 changed input pixels are fitting-quality measurements. They are
not export inconsistencies: file decoders and native output agree with the
fitter's chosen preview. This does not prove that the heuristic finds the best
possible fit for every representable image.

The new logical run records application HEAD
`71a09368eed151873642b3b236b6a00852ac2b73`, clean at both ends before the verifier
repair. All loaded source and reference hashes remain unchanged through the
run and native captures. The five relevant NUFLI/FLI source files also match
the earlier Smoking Fish audit's HEAD `b5ce8739f62b25fcf8fed27652cef886c35e93d2`
exactly. The later verifier/test repair is separate from those fitter and
player bytes. It was committed in the adjacent `c64` repository as
`b730ceb` (`fix(nufli): wait for complete VICE replies`); all four focused
regression tests passed again before that commit.

## Reproduced failure: a quiet socket is not a completed screenshot

The first Oldsmobil native run stopped with `PIL.UnidentifiedImageError` while
opening `vice-2.png`. The monitor transcript records an empty immediate reply
to `scrsh`; an earlier `bank ram` reply contains two monitor prompts. Commands
and their replies had become misaligned.

After the checker exited, both saved PNGs were valid, 35,535 bytes each, and
each matched all 64,000 expected pixels. The old checker source, complete
transcript and those post-failure observations remain in
`build/research/nufli/converter-native-oldsmobil-01/`. That aborted session is
not counted as a successful three-capture result. Its
[failure receipt](../../build/research/nufli/converter-native-oldsmobil-01/failure-observation.json)
pins the original checker SHA-256
`24bfd2055408b01d7149f339f36aaeee49a514b525dea1351d8b9bd6556de7dc`.

The narrow fix in the actual application's
[verifier](../../../c64/nufli/verify-vice.py) waits for a complete monitor prompt
under one total 30-second deadline. Partial responses and quiet intervals do
not complete a command. EOF and timeout raise explicit errors. An initial
`r` handshake additionally requires a real register row, so a delayed startup
prompt cannot consume the first command's response.

The [four focused regression tests](../../../c64/tests/test_nufli_vice_monitor.py)
cover a delayed/split prompt after a quiet gap, a stale initial prompt, EOF,
and a total deadline while partial data continues arriving. The quiet-gap
case failed against the extracted old reader before the fix. All four pass
with the repaired reader. Run them from the adjacent `c64` repository:

```sh
rtk proxy python3 tests/test_nufli_vice_monitor.py
```

The repaired verifier has SHA-256
`8cd8adfb037dc2596ff9c2d6eace061e0d17b7e8b417237be6451ac332955fb9`.
The image comparison and exported picture/player formats were not changed by
this repair. Both the new Oldsmobil run and the Wrong Way run completed all
three captures through that reader.

## Native results and reproduction

All accepted runs use the application's actual `nufli/verify-vice.py`, PAL at
100% speed with warp off. The root-controlled native lane runs one owned
emulator at a time and closes it afterward. Each capture stops at the player's
normal `$310d` foreground loop. These are samples of static images, not an
animation frame-rate measurement.

The app checker searches a small crop window. The separate
[fixed-origin checker](../../research/nufli/verify_converter_native.py) then
compares the entire 320×200 rectangle at `(32,32)` without a position search
or excluded pixels. It accepts `--native` and `--expected` for each case.

From the research repository, a new case can be reproduced with an unused
output directory:

```sh
rtk proxy node research/nufli/converter_variants.cjs
rtk proxy python3 ../c64/nufli/verify-vice.py \
  build/research/nufli/converter-variants/oldsmobil/converted.prg \
  build/research/nufli/converter-variants/oldsmobil/expected-indices.bin \
  --output build/research/nufli/converter-native-oldsmobil-new
rtk proxy python3 research/nufli/verify_converter_native.py \
  --native build/research/nufli/converter-native-oldsmobil-new \
  --expected build/research/nufli/converter-variants/oldsmobil/expected-indices.bin
```

The [logical receipt](../../build/research/nufli/converter-variants/variants-audit.json)
pins the final harness, application inputs, palette and all three output pairs.
The [native summary](../../build/research/nufli/converter-variants/native-summary.json)
pins all four exports, their preview references, twelve screenshots and exact
checker-source copies. The new native runs and fixed-origin receipts are:

- [Forgotten](../../build/research/nufli/converter-native-forgotten-01/fixed-origin-check.json).
- [Oldsmobil, successful rerun](../../build/research/nufli/converter-native-oldsmobil-02/fixed-origin-check.json).
- [Wrong Way](../../build/research/nufli/converter-native-wrong-way-01/fixed-origin-check.json).

The original programs for the three added targets, NTSC, physical hardware,
browser UI interactions and the full legal NUFLI image space remain outside
this result. A consistent preview/export/native path is a concrete color
correctness result for the inspected images, not a guarantee of optimal
fitting or universal format coverage.
