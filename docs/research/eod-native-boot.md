# Edge of Disgrace: original disk-0 boot agrees with the passive decoder

Research date: 8 November 2026. The original disk-0 program reaches its
natural `$0900` entry after its own SFX depacker. **All 63,231 decoded
payload bytes at `$0801..$FEFF` match native RAM**, with zero differences.
The comparison uses the separately retained passive decoder's result;
this producer runs no emulator or CPU instruction interpreter.

This establishes the main boot payload, not the later Gouraud effect.
See [disk/file extraction](eod-files.md) and the
[primary Gouraud author evidence](stock-gouraud-sources.md) for the
separate content-side research.

## Original bytes and natural stops

The ordinary DOS entry `EDGE OF DISGRACE`, starting at track 1 / sector 0,
occupies 130 sectors. Its PRG has 32,864 bytes including its `$0801` load
address, SHA-256
`d45e1474288f537841351bbf95cafbc6df2ecf50f3f86b0547352d7c67c9e724`.
All **32,862 loaded payload bytes** match the first native capture.

| Capture | Natural PC | Machine clock | Raster / raw cycle |
|---|---:|---:|---:|
| `sys` | `$080D` | 85,514,861 | 178 / 47 |
| `sfx` | `$0334` | 86,019,674 | 79 / 41 |
| `unpacked` | `$0900` | 90,297,558 | 278 / 36 |

The BASIC stub contains `SYS2061`. At `$080D`, the original code sets
port `$34`, copies sixty bytes from `$081F` into zero page `$0006`, and
jumps to `$0008`. That relocated startup moves the compressed input and
copies the decoder from `$085B`. The acceptance compares **all 192 code
bytes `$085B..$091A` against native `$0334..$03F3`**.

The decoder exit at `$03B0` is guarded as:

```asm
LDA #$37
STA $01
CLI
JMP $0900
```

The decoded PRG has 63,233 bytes including its load address, SHA-256
`3087048a4b95171955f57adcc455be06b858fa29e72cf7550ea3aae5c638795a`.
Its 63,231 payload bytes equal the complete native interval, including
data as well as instructions. The native process stopped before `$0900`
executed. No later part or custom loader handoff is inferred from it.

## Full state-pair and wire checks

All three full RAM/VSF pairs agree on 65,536 physical RAM bytes, CPU
registers/flags, machine clock and VIC beam position. PAL clock division
also agrees with the recorded line and raw cycle.

CPU-port checks use C64MEM **version 0.1**, payload length 65,555. Monitor
`$00/$01` are compared with serialized `dir_read/data_read` at offsets
65542/65541; driven output bits are checked separately against the latch.
Unused-bit/decay state is guarded as zero. The latch is not substituted
for input readback, and no tape state is invented. The pinned official
VICE 3.10 archive supplies `c64memsnapshot.c:217–230`,
`c64mem.c:267–338` and `c64pla.c:53–75`; member hashes are in the receipt.

The original disk is both `-autostart` and `-8`. Launch arguments specify
PAL, speed 100, `+warp`, `+autostart-warp`, and a true 1541 drive. These
are launch checks, not a fabricated runtime speed/warp query. The exact
22-command sequence consists of observation, breakpoint management,
natural continuation and captures; it contains no CPU/RAM/register patch
or snapshot restore.

The evidence retains two distinct observer events:

- Sequence 5 initially produced a 30.15-second waiting notice, with zero
  received bytes. That same command later completed naturally at `$080D`;
  there was no retry or restart.
- At `17:39:53.630686 UTC`, an interruption request was rejected with
  `No pending x/exit`. Sequence 5 had already completed, no command was
  active, and no interrupt `r` reached the monitor wire. This was not an
  interrupted native run.

The frozen wire auditor is unchanged. The producer extracts only its
`audit_session` function and applies two exact, in-memory replacements:
the original-disk autostart contract, and a branch validating that one
inactive rejection event. No event is removed or filtered. Original and
adapted function hashes and the exact replacement text are recorded.

The owned process was explicitly closed and reaped, exit −15. The closed
case contains **13 files / 834,331 bytes**, canonical listing SHA-256
`0acb6d27127338b7634e4cb1a68e5c62f60f88f5f458fcc191ea91b0f057dd0c`.

## Reproduce and limits

```sh
rtk proxy python3 research/eod/native_boot.py --output build/research/eod/native-analysis/fresh-replay
```

Choose a fresh directory. The producer pins the original disk, closed
case manifest, trusted readers/auditor, official VICE archive, and the
accepted-02 extraction receipt and its checked source copy. It executes
no downloaded tool source. The extractor's later content-file correction
does not change this main PRG or decoded payload; this acceptance makes
no claim that every indexed stream is a valid compressed program.

Final acceptance is `native-analysis/accepted-01/native-boot-proof.json`,
15,365 bytes, SHA-256
`5fb362350de04f09d2d4381bc600249f8ff588901aa58e1414c9fa59544c083c`.
The other outputs are the compared decoder bytes and checked producer.
The producer is 14,267 bytes, SHA-256
`f1c0c0eaa4be5380bec55b84b34461b43b0065689a0ab94342c411dffb53bb55`.
Both the author's fresh replay and the independent root replay reproduce
all three outputs exactly, 29,824 bytes total. The root comparison is
`native-analysis/root-replay-check.json`, 917 bytes, SHA-256
`12af341da6a471791c2e1e53e994565a6cc51a9a365828b323f8beaa7c234528`.

No shader, displayed image, Gouraud interpolation, content-side load,
frame rate or whole-demo equivalence is accepted by this boot result.
No new native execution, build, subprocess or product changes occur in
the passive reproduction.
