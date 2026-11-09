# Aloft: closed original cell-execution custody

Research date: 9 November 2026. A fresh original-side1 run is closed and
reaped. The accepted custody proof verifies **18 complete RAM/VSF pairs,
202 completed responses and 2,831 unfiltered watch hooks**. It supplies two
genuine pre-`$0500` inputs, two first-cell returns and two full 200-call
returns. Each chain has 175 independently bounded INC-read raster domains;
none has an ambiguous raster MSB. These are native observations and inputs
for separate passive models, not acceptance of their predicted results.

The [source-cell generator](aloft-cells-20261109.md),
[cell semantics](aloft-cell-semantics-20261109.md) and
[decoded-generation association](aloft-decoded-parts-20261109.md) remain
separate proofs. The [continuation note](aloft-execution-continuation-20261109.md)
owns broader next steps. This case does not identify the named moving
three-layer scene or predict committed pixels, complete animation or FPS.

## Original boot and terminal closure

The [owner closure](../../build/research/aloft-execution-20261109/owner-closure-01.json)
is 13,678 bytes, SHA-256
`a993826c4690c34ab469a386cc039878d6029c4b8436fe617c5c6ca9b3709049`.
The [raw manifest](../../build/research/aloft-execution-20261109/native-01-files.json)
is 6,800 bytes, SHA-256
`d31508400ca57a774a6c602d70aed079e59391f395f1e8521be3abf2e0ca4b2c`.
Its **43 files / 7,118,550 bytes** have canonical listing SHA-256
`40522acace6d13858ee2fe5cd3679524ae7029b296b54314a6f6a320a1a95003`.
Every raw event and sent/received byte remains. The strict auditor derives
2,367 journal events, 200 public commands and two internal startup commands.
All 202 responses complete; no pending response, timeout, interrupt or waiting
notice remains.

The same owner handle 26020 started PID 93687, used original side1 autostart
and true-drive 1541, then exited with observer status 0. The native process
exited `-15` and was reaped at `2026-11-09T10:23:27.122071Z`. No PC/RAM
patch, restore, restart or disk change appears in this case.

Original D64 SHA-256:
`d13eae8daeada64bc61772a2dad2d3e62d1a0d30a34b29103119535610e4cfce`.
At natural SYS `$0810`, all **830 original bootstrap payload bytes** equal the
832-byte PRG after its `$0801` load header. This run passed `$08B5` without a
saved post-copy pair. That missing fresh 416-byte resident observation stays
explicit; later self-modified loader bytes are not normalized into a
whole-resident equality claim.

## All eighteen natural phases

For every pair the checker compares all 65,536 physical RAM bytes with VSF,
strict CPU/memory schemas, saved PC/registers/flags/clock, CPU-port readbacks
and driven bits, PAL beam arithmetic and same-stop ordering. Complete stopped
VIC/CIA state and source-backed DRIVECPU0/DRIVE8 context remain in the outputs.

| Capture | Actual PC | Clock | Raster/cycle |
| --- | --- | ---: | --- |
| sys | `$0810` | 6,960,979 | 43/46 |
| body | `$F02B` | 130,163,026 | 15/49 |
| precall | `$F0AE` | 130,204,323 | 47/18 |
| dispatcher | `$0500` | 130,204,329 | 47/24 |
| cell-entry | `$2000` | 130,204,335 | 47/30 |
| inc-entry | `$201D` | 130,204,374 | 48/6 |
| inc-after | `$2020` | 130,204,380 | 48/12 |
| first-return | `$0503` | 130,204,392 | 48/24 |
| chain-return | `$F0B1` | 130,216,935 | 247/30 |
| after-line | `$F0B8` | 130,216,971 | 248/3 |
| later-precall | `$F0AE` | 131,462,307 | 47/18 |
| later-dispatcher | `$0500` | 131,462,313 | 47/24 |
| later-cell-entry | `$4600` | 131,462,319 | 47/30 |
| later-first-return | `$0503` | 131,462,376 | 48/24 |
| later-chain-return | `$F0B1` | 131,474,919 | 247/30 |
| later-after-line | `$F0B8` | 131,474,955 | 248/3 |
| later-wrap-zero | `$01AC` | 131,478,986 | 0/2 |
| later-wrap-one | `$01AC` | 131,479,049 | 1/2 |

The first target is read from genuine dispatcher JSR bytes, then matches the
actual natural stop. The first observed call program uses two targets,
`$2000/$2023`; the later program uses 69 distinct targets. Both actual programs
have 200 JSRs and a final RTS. No guessed scene, wrapper-counter arithmetic or
predicted endpoint chooses a target. Each captured dispatcher-to-`$F0B1`
interval is **12,606 machine cycles**; this is not delivered FPS.

The actual 601-byte dispatcher and all 11,232 generated cell bytes are equal
at the declared captures within each call. This captured equality alone is
not continuous executable-history proof. A consumer must close its finite
write footprints and declare any exclusion of an unmodeled external NMI
handler or RAM-writing DMA. Unobserved memory accesses are not reconstructed.

Checkpoint IDs retain creation/deletion and enable/disable histories. ID1
is created for SYS, deleted, reused for `$F02B`, deleted and reused for `$F0AE`.
Each source-byte predicate is evaluated at its own captured stop. Checkpoint18
later changes from `RL == $0000` to `RL == $0001`; each wrap stop uses its
then-current condition. Reused IDs do not inherit earlier conditions.

## Ports, watches and dummy observer behavior

The original `$F080: DEC $00` changes live DDR from `$2F` to `$2E`. Execution
pairs show `$2E/$35`; the IRQ restore returns DDR to `$2F` before wrap. The
frozen pair-reader adapter removes only its fixed `$2F` suffix. Wire/VSF DDR
equality, readbacks and driven-bit checks stay strict. Physical RAM aliases
under `$00/$01` and their CPU-visible device values remain separate.

| Watch ID | Operation | Inclusive range |
| --- | --- | --- |
| 3 | store | `$D000..$D03F` |
| 4 | store | `$DD00..$DD03` |
| 6 | store | `$0000..$00FF` |
| 7 | store | `$0787..$07BF` |
| 8 | load | `$D011` |

Dedicated port watch 2 is deleted before overlapping zero-page watch 6 is used. Every
execution watch has an exact attached `r`. Both bounded chains require all
five unconditional watches enabled before dispatcher resume and through the
full return. Watches are disabled during intervening navigation; no continuous
watched coverage is claimed there. Dummy starts off, is enabled at command 34,
and is queried on at 35, 121 and 182. The checker requires its latest setting on
before each window and no intervening setting mutation; queries are allowed.
Final command 202 confirms all checkpoints deleted.

The [retained observer-source record](../../build/research/aloft-execution-20261109/native-analysis/observer-source-01/source-record.json)
binds exact official VICE3.10 archive members as data: dummy memory-table
routing, the per-operation nine-entry queue limit, FIFO duplicate retention,
load-before-store queue flushing, current-clock trace formatting and attached
commands. It does not turn queue output into universal physical bus order or
supply raw bus data.

Execution-breakpoint handling precedes queued watch flushing. Command 71 stops
at `$201D`, clock 130204374, after `$201B: STY $0F`; that STY hook prints only
on command 79, with the **same earlier completion clock**. Command 79 then
executes INC and stops at `$2020`, clock 130204380. The next resume flushes INC's
load and two store hooks. Records retain both the parent response/raw offsets
and their instruction/completion clock. No late hook is discarded or treated
as a new physical access merely because it prints in a later response.

Duplicate old/final RMW hooks remain. Their shared clock is not separate bus
timestamps and they contain no raw bus byte. Direct STA/STX/STY/SAX hooks have
separately labelled post-register store operands. No such operand is invented
for RMW. Exact actual opcodes, A/X/Y/SP and flags remain oracle fields.

## Independent inputs and comparison-only oracles

The [independent-inputs output](../../build/research/aloft-execution-20261109/native-analysis/accepted-02/independent-inputs.json)
has separate `first`/`later` entries, containing genuine pre-`$0500` data:

- CPU registers, CPU-view ZP with explicit 00/01 readbacks, and physical aliases.
- All256 lookup bytes at `$0400`, the actual 601 dispatcher bytes, 200 JSRs/targets
  and final RTS.
- All 40 initial glyph values: `$0007 + 8*i`, `i=0..31`, and `$0787 + 8*i`,
  `i=0..7`.
- Raw stored snapshot `$D011`, initial VIC/CIA context and independent
  operand-read raster domains.

For each watched INC, the immediately preceding watched STY zp has next PC equal
to the INC PC. Its completion lower-bounds the operand read; INC completion
upper-bounds it, including stalls. The checker derives every possible raster
line in that inclusive clock interval. A raster MSB is unique only when all
lines agree. Both chains have 175 domains and zero ambiguities; completion
clocks never become exact physical read cycles.

Post-INC A/flags/results and store values are absent from read-domain inputs.
The [hook-oracles output](../../build/research/aloft-execution-20261109/native-analysis/accepted-02/hook-oracles.json)
retains every actual hook and separate first-return/full-return endpoint data.
All 40 glyph values and CPU-view ZP are comparison targets there. Stored `$D011`
comes from VSF VIC registers; live I/O peek raster bit 7 remains distinct.
The [machine-context output](../../build/research/aloft-execution-20261109/native-analysis/accepted-02/machine-context.json)
retains all 18 stopped states. Manual bank-I/O peeks stay raw oracles too.
Offsets/hashes use original bytes, with event UTF8-replacement text checked
separately; PETSCII is not re-encoded into a changed byte stream.

## Exact failures, wrap scope and replay

Commands 177–181 omit required resource-name quotes. All five completed
transport responses contain monitor syntax errors and remain explicit
rejected read-only queries; none supplies a resource value. Corrected 183–187,
without resuming, establish warp off, Speed 100, VICIIModel 1, border mode 0 and VSP bug resource 0.
Earlier successful queries remain. No failed row is removed and no general
error-parser relaxation is used.

The wrap snapshots row0/cycle2 and row1/cycle2 are **63 cycles apart**, referring
to the same preceding completed field. They are not two independently
displayed generations and do not prove framebuffer row lifetime or pixels.
Cell/motion comparison, fetch-state binding and pixel composition remain
separate consumers with explicit limits.

The [accepted02 proof](../../build/research/aloft-execution-20261109/native-analysis/accepted-02/native-proof.json)
is 131,527 bytes, SHA-256
`5db9694db276541a5fd2b5cb386e92639e6da2c0d6cd644caf758eb113cc2326`.
The [producer](../../research/aloft-execution-20261109/native.py) is 39,449 bytes,
SHA-256 `99bea080d4e2fa74f4c3656dfd6084af752e0747247c1ef67e7688c1ec92d967`.
Five accepted files total **5,777,428 bytes**. Candidate01/accepted01 stay
immutable; accepted02 hardens dummy-state/trace assertions. All three data ABI
files are byte-identical to accepted01.

A fresh [self replay](../../build/research/aloft-execution-20261109/native-analysis/self-replay-check.json)
reproduces all five files exactly. Report 1,329 bytes, SHA-256
`3c831f3676dd54cfeecbde2a46bda996d7a056b434f5ff75740fef41c591218d`.
Root reviewed the final source and independently reproduced all five files /
5,777,428 bytes. The [root report](../../build/research/aloft-execution-20261109/native-analysis/root-replay-check.json)
is 1,165 bytes, SHA-256
`8da787f27a10b9c5ff554c81af7e81899cdff51e942d521fdda840254cde71f8`.

```sh
rtk proxy python3 -B research/aloft-execution-20261109/native.py --output build/research/aloft-execution-20261109/native-analysis/<fresh-directory>
```

The producer is passive Python plus trusted frozen readers/auditor adapters.
It starts no native process, socket, emulator, target CPU interpreter, build or
downloaded host program. The original case is closed. This lane performs no
additional capture or mutable-index publication.
