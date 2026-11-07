# VICE 3.10 x64sc store traces report a later instruction boundary

**A textual `trace store` timestamp is not a timestamp saved at the bus write.**
In the normal x64sc instruction path, a final store callback occurs one clock
before the checkpoint is printed. Store disassembly deliberately shows the
instruction that caused the access, while the raster position, registers and
stopwatch value come from the later reporting boundary.

This conclusion comes from the pinned official **VICE 3.10** source archive,
SHA-256
`8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`.
No emulator, CPU, compiler, timing test or native process was run in this pass.
The [official monitor manual](https://vice-emu.sourceforge.io/vice_12.html)
documents checkpoint formatting and the `dummy` switch; the precise timing
conclusion below comes from source inspection.

## The actual x64sc path

x64sc's `src/c64/c64cpusc.c` includes `src/mainc64cpu.c`, which includes
**`src/6510dtvcore.c`** at line 809. Reading only the similarly named generic
`6510core.c` would inspect the wrong implementation for this question.

The relevant source sequence is:

1. The instruction's store calls the memory handler. With watchpoints active,
   `store_watch` first queues the accessed **address**, then invokes the actual
   memory write handler.
2. The CPU core advances the clock after that store. Its `SET_ABS` macro orders
   `STORE` before `CLK_INC`.
3. On the next main-loop boundary, `DO_INTERRUPT` checks `MI_WATCH` and drains
   the recorded addresses using `LAST_OPCODE_ADDR` as the instruction owner.
4. The checkpoint formatter obtains the current raster line/cycle and current
   registers at that point. It does not recover a saved access clock.

The queue stores 16-bit addresses and counts. It stores neither write values
nor timestamps. The instruction-owner address is separately retained before
opcode fetch. A `STA` also advances its architectural PC before calling the
store handler, explaining why the formatter needs that separate owner address.

| Pinned source location | Relevant behavior |
|---|---|
| `src/6510dtvcore.c:479–489` | Normal store, and RMW dummy/final stores, each followed by clock increment |
| `src/c64/c64cpusc.c:47–56` | `CLK_INC` advances `maincpu_clk` and the VIC; `SKIP_CYCLE` is zero |
| `src/c64/c64memsc.c:159–189` | Queue address before actual handler; choose regular/dummy watch tables |
| `src/monitor/monitor.c:2826–2839` | Append store addresses without deduplication |
| `src/monitor/monitor.c:2860–2879` | Check each queued store address later |
| `src/6510dtvcore.c:443–448` | Invoke deferred watchpoint check with `LAST_OPCODE_ADDR` |
| `src/monitor/mon_breakpoint.c:485,573,594` | Owner PC for store disassembly; current raster sampled for printing |
| `src/c64/c64.c:1298–1303` | Raster position computed directly from current `maincpu_clk` |
| `src/monitor/monitor.c:1466–1474` | Final printed number is current CPU clock minus stopwatch base |

All paths and excerpt hashes are recorded in the source receipt. The filenames
and line numbers refer to the exact archive above, not a moving source branch.

## Applying it to the supplied STA measurement

The parent investigation supplied this existing Demo Coder observation:

| Point | Clock | PAL monitor position |
|---|---:|---|
| Pre-instruction breakpoint at `$7024`, `STA $D011` | 259,896,790 | line 81, cycle 55 |
| Store trace for that instruction | 259,896,794 | line 81, cycle 59 |
| Derived normal-path memory-handler callback | **259,896,793** | **line 81, cycle 58** |

The four-clock span agrees with the ordinary absolute `STA` path: three fetch
cycles, the store callback, then its clock increment before reporting. The
callback position is a **source-derived interpretation** of that supplied
measurement; this pass did not independently rerun or reread its native trace.
Cycle numbers here use the monitor's zero-based modulo-63 convention.

This locates the emulator's CPU memory-write callback. It does not identify
the later pixel where a VIC register change becomes visible or measure a
physical chip's bus timing.

## INC/DEC perform two writes; the dummy setting controls trace visibility

x64sc's absolute RMW setter writes the old value through `STORE_DUMMY`, advances
one clock, writes the modified value through `STORE`, then advances another
clock. `DEC`/`INC` route through that setter. Both memory-handler callbacks
therefore happen even when the monitor hides dummy accesses.

The source default is **`break_on_dummy_access = 0`**, at
`src/monitor/monitor.c:179`. This is a default, not proof of a running session's
current setting. The monitor's `dummy` command can query or change it.

For one matching store checkpoint, without commands that advance execution:

| Monitor setting | Normal RMW store trace records | Callback clocks relative to reporting boundary `T` |
|---|---:|---|
| `dummy off` | **1**: modified-value write queued | Final write at `T−1`; old-value write at `T−2` still occurs |
| `dummy on` | **2**: old-value then modified-value address queued | Old write at `T−2`, final write at `T−1`; **both records print at `T`** |

There is no address deduplication. Repeated same-address lines with identical
reported time can therefore be two queued RMW accesses. They are not evidence
that both bus writes occurred simultaneously. Conversely, one line with dummy
accesses disabled is not evidence that the CPU performed only one write.

Memory-based checkpoint conditions and attached dump commands run when the
queue is checked. They cannot recover the old-value write's transient state
from the address-only queue after the modified write has already occurred.
If several checkpoints match an address, each can print; the table assumes
one matching checkpoint.

## An exec breakpoint can stop before the final stores are printed

There is an additional endpoint trap: **`MI_BREAK` precedes `MI_WATCH`** in
`src/6510dtvcore.c:435–448`. An execution breakpoint at the instruction after
an RMW operation can enter the interactive monitor while that operation's
store addresses are still queued. The actual writes have happened, but their
trace text need not have been emitted yet.

The parent supplied a concrete native case, not rerun here: `DEC $D011` at
`$6763` begins at clock 265,812,191, line 65 cycle 8; its two dummy-enabled
records print at 265,812,197, cycle 14. An exec breakpoint at the following
`RTS` at `$6769` stops at 265,812,243, cycle 60, with no intervening printed
records for `INC $D011` at `$6766`. This is consistent with the INC's queue
still pending behind the exec-breakpoint monitor entry.

Ending a trace or disabling its checkpoint at that stopped boundary can
therefore truncate the final instruction's printed accesses. Resume with the
trace retained, or place the capture endpoint beyond the queue drain. In the
supplied case, the parent chose the original RTS return `$631B` as that later
endpoint. The parent subsequently reported a clean capture with exactly four
records: two DEC-owned records at clock 265,812,197 and two INC-owned records at
265,812,243. Its return endpoint is 265,812,249, line 66 cycle 3. This agrees
with the source ordering; the native capture remains owned and verified by
the parent investigation, not rerun by this source-only pass.

## Pending monitor queues are outside the restored VSF state

The source also establishes a cross-run caveat. The queued addresses, their
counts and the occurred flags are **static debugger globals in `monitor.c`**.
Their resets occur in `monitor_init` and normal queue draining. The successful
`mon_read_snapshot` path calls the machine snapshot loader and updates the
monitor's current address; it does not clear pending watch queues.

`c64_snapshot_read` restores machine modules without a monitor queue module or
monitor reinitialization. The MAINCPU snapshot saves `last_opcode_info`, but
does **not** save or restore `last_opcode_addr`. Consequently, even byte-identical
restored VSF modules do not prove equivalent pending monitor queues or
instruction-owner bookkeeping.

The parent later reported an extended capture with two extra DEC-labelled
records at the restored pre-instruction clock, before four later DEC/INC
records. The source proves that stale queued accesses can survive this restore
path and be reported using later bookkeeping. It does not independently prove
which prior operation produced those exact early records. The parent's
subsequent clean-queue capture produced the expected four records, and the
earlier six-record attempt is retained separately as a capture artifact.

Relevant pinned locations are `monitor.c:1602–1608,2795–2806`,
`mainc64cpu.c:887–1014`, and `c64/c64-snapshot.c:101–150`.

## Limits on timestamp normalization

Do **not** subtract one clock blindly from every monitor record:

- In `DO_INTERRUPT`, IRQ/NMI and trap/reset handling precede the `MI_WATCH`
  branch. Intervening service can advance time and change state before printing.
- An attached checkpoint command can alter execution or monitor state before
  later queued records are printed.
- The number at the end of a disassembly line is a **stopwatch** value. It
  equals raw `maincpu_clk` only when the relevant stopwatch base is zero. Raster
  positions are computed from the actual current main clock.
- Execution checkpoints and CPU-history records follow different paths. This
  conclusion concerns textual **load/store checkpoint reporting** in x64sc,
  especially the store path inspected here.

For the supplied straight-line `STA` span, the normal `T−1` interpretation is
consistent with the independently supplied pre-instruction clock. For broader
captures, retain the raw reporting time, instruction owner and dummy setting,
and qualify any reconstructed bus clock by the exact executed path.

## Reproduction

```sh
rtk proxy python3 research/vice-trace-timing/inspect_source.py
```

This verifies the existing archive hash, extracts eleven relevant source files
under ignored `build/research/vice-trace-timing/source/`, checks 25 source
structures and writes `source-proof.json` with file hashes, line anchors and
the supplied-clock arithmetic. It does not execute any VICE code.
