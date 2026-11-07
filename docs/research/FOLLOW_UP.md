# Follow-up prompt

Copy the prompt below into a new chat opened on the same workspace. The
ignored build directory contains the original captures and must be retained.
The [checkpoint](CHECKPOINT.md) provides the complete case map and evidence
boundaries; the prompt intentionally points to it rather than duplicating
every old receipt.

---

Continue the C64 demo research in
`/Users/rogerjohansson/git/asynkron/c64demo`.

The objective is to scan primary blogs/articles, find demos that push the
machine, reverse-engineer their released code, understand their mechanisms,
and document verified findings and remaining gaps. Keep the broad objective;
do not redefine completion around the existing cases.

First read:

1. `docs/research/CHECKPOINT.md`
2. `docs/research/README.md` and `docs/research/technique-map.md`
3. `docs/research/anomaly-runtime.md` and `docs/research/anomaly-native-arcade.md`
4. `docs/research/relax24-resources.md` and `docs/research/relax24-articles.md`

Recheck actual Git/filesystem state. Another chat is editing sprite-ball
assets and renderer files in this shared repository. Preserve unrelated
edits. Research baseline commit is `d50d173`; inspect later commits and the
working tree for subsequent research, renderer, and sprite-ball changes.
The converter's NUFLI monitor fix is already committed as
`b730ceb` in `/Users/rogerjohansson/git/asynkron/c64`. No new converter feature
or NUFLI viewer replacement is requested. Do not commit new work without a
fresh commit instruction.

Every shell command must start with `rtk`; read
`/Users/rogerjohansson/.codex/RTK.md`. Use agents for independent source/model
work, but keep one owner for VICE/process control. Do not touch unrelated
preview processes. Preserve frozen proofs and failed observations; archive
old producers/receipts before correcting a checker. Downloaded host tools
are not to be run merely because they are included in a demo's archive.

**First priority: finish Anomaly's live Arcade witness.** Its original
Sparkle 2.3.23.105 disk has 39 independently decoded bundles; Arcade bundle 36
matches all 41,523 Link payload bytes. The latest native batch is closed
and deliberately incomplete: two floor updates and a rejected upper gate
pass, but accepted jobs, publication and the 96-write field remain pending.

Resume from:

```text
build/research/anomaly/native-03/upper-rejected-post.vsf
SHA256 db7c7cae5e97a0f0c90229fde26767d162ff3f2dd28f5d2d44e18147644a7449
PC 3D89, clock 164602120, raster 44, raw cycle 4
```

Use the same original
`build/research/anomaly/original/WeAreTheAnomaly-Side1.d64`, SHA-256
`d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd`.
Start a new owned `research/vice_session.py` session with `--no-autostart`
and that disk attached. The interactive execution tool needs `tty=true`
so stdin stays open. Restore the snapshot, capture RAM/VSF before execution,
and compare complete RAM, CPU/ports and beam to its parent. Do not jump to
`$3B00`, load a substituted part or alter the program counter.

Warp is off at the saved runtime state. Keep normal-speed measurement
separate from host warp transit. VICE's working monitor control is `warp`,
not a `WarpMode` resource; the earlier failed read queries are preserved.

The next useful monitor condition is:

```text
break exec $36e6 if (((A - @ram:$36e7) & $80) != $00) && (@ram:$0007 != $00)
```

This stops after the actual `$D012` sample, before its CMP, only when the
signed gate accepts and the upper update is pending. Capture that prestate
and the natural `$3D89` return; model the real copy job independently.
Install execution tracepoints at `$36F3/$38BB/$39B1/$39CA` before resuming to
record the remaining pixel-row, attribute-row and new-column jobs. The saved
state has row 0/status 1 and **zero prior job trace hits**. The complete
first update requires 13+13+1+1 jobs. At first `$B84B`, capture before the
publication helper, then `$B864` after publication. Test completion; do not
assume it. Read the runtime note for exact state and all source addresses.

For a floor field, begin at `$B400`, trace stores to `$D016`, and stop at
`$B828`; the following `$B857` upper-scroll write is separate. Validate
actual values, code and table history, then observe several consecutive
fixed boundaries for cadence. Store-trace timestamps are observer-boundary
times, not automatically bus-write phases. Nested IRQs can interrupt the
floor update; do not claim whole-machine equality from the scoped arithmetic
model or call a single code-loop interval FPS.

If observing a running session times out, re-poll the same handle or inspect
its authoritative state. Never restart solely because a timeout expired.
Capture filenames must match actual observed PCs; do not save an unconfirmed
stop under an expected label.

**Parallel priority: recover Relax #24's resource consumer.** The two packing
stages are frozen and checked; reuse them rather than rerunning the four-
million-instruction outer proof. The new resource script is only a format
checkpoint: zero resources/articles are decoded. Implement the functional
`$991D` format for `$8000..$8DF0` with descriptor
`$8DF1..$8DF5 = 27 F1 0D 00 D0`, mutable memory and known-byte masks.
The strict CPU prefix still stops at `$99F2` reading unknown `$0223`.
A pure format model may explicitly exclude the proven dead literal read;
never supply a fake byte to the CPU or assert continuous execution across
it. Require every used match source to be known. Recover the actual
post-expansion `$C000` consumer before interpreting side-2 headers, assigning
`DR` to any article, or claiming the cached Clarence review is validated.

Continue afterward with later Second Reality effects, moving presets in
The Impossible Thing, the Hat/Aloft original artifacts, and the broader
reading-map queue. Primary author claims, pinned source, original-binary
models, native observations and independent output oracles must stay
separate. Do not infer alpha blending, live 3D, a loader family or a frame
rate from appearance alone.

Write findings to the repository notes/scripts and ignored evidence tree.
Update the reading map and checkpoint after meaningful progress. Report
what passed, what remains unproved and the exact next step. Do not mark the
broad research complete because a bounded batch passes.

---

## Compact prompt

For a shorter handoff, use:

```text
Continue the C64 rendering research in /Users/rogerjohansson/git/asynkron/c64demo.
Read docs/research/CHECKPOINT.md and docs/research/FOLLOW_UP.md first, then follow
the continuation steps there. Resume the saved Anomaly Arcade state to verify
accepted upper-buffer jobs, publication and the 96-write D016 field; continue
the known-memory Relax24 resource parser in parallel. Preserve unrelated edits
and frozen evidence, use rtk for every shell command, and never invent unknown
RAM/hardware inputs or call scoped checks full-frame/FPS proof. Document new
findings and explicit gaps; keep the broader demo-research objective intact.
```
