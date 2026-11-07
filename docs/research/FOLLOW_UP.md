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

1. `docs/research/CHECKPOINT.md` and `docs/research/HANDOFF-ARTIFACTS.md`
2. `docs/research/README.md` and `docs/research/technique-map.md`
3. `docs/research/anomaly-upper.md` and `docs/research/anomaly-native-upper.md`
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

**First priority: extend Anomaly's coherent display witness.** The original
Sparkle disk and all 41,523 Arcade Link bytes are bound. The closed native-04
batch now checks the first accepted gate, all 28 upper jobs, completion before
publication, a direct 4,680-byte prepared-image oracle and three fields of
96 source/value-matched `$D016` stores. Read `anomaly-upper.md` and
`anomaly-native-upper.md`; do not repeat native-03's now-completed task list.

For further native work, resume:

```text
build/research/anomaly/native-04/field-04-pre.vsf
SHA256 70fbfcde49a6c1b9a1b18ad538d7e0684cc1c7fdaf2ec6a42b40ad734bbf1b5b
PC B400, clock 167006965, raster 152, raw cycle 13
```

Use the same original
`build/research/anomaly/original/WeAreTheAnomaly-Side1.d64`, SHA-256
`d452497845598cca8936fdf57c60fdc9c70cd7e64110e049fa6fc7d735f940cd`.
Start a new owned `research/vice_session.py` session with `--no-autostart`
and that disk attached. The interactive execution tool needs `tty=true`
so stdin stays open. Restore once and verify complete RAM, MAINCPU, ports,
registers and beam against the parent before execution. Do not jump to an
entry, load a substituted part or alter the program counter.

Warp was off, Speed=100. Keep measurement separate from any host warp
transit. The working monitor control is `warp`, not a `WarpMode` resource.
Preserve the former failed read queries and the rejected all-63-timestamp
assumption. Three full floor observer vectors repeat +19,656 clocks, but
within-field trace deltas are not uniformly 63. The following `$B857` upper
scroll store is separate from each 96-write floor field. Monitor timestamps
are not automatically bus-write phases, and screenshots are not independent
full-field pixel proofs. Next prove coherent scanout/composition using real
bank, bitmap, attributes and register history, then broaden update/timing
coverage before claiming complete FPS or a maximum renderer budget.

If an observation times out, re-poll the same handle or inspect authoritative
state. Never restart solely because a timeout expired. Capture filenames
must match actual stops. All prior owned research sessions are closed;
do not wait on their old handles or touch unrelated previews.

**Parallel priority: bind Relax24's real loader to the original disk.**
The new known-memory `$991D` parser recovers all 9,216 bytes at `$AC00..$CFFF`
from all 3,569 compressed bytes; both functional models and all 7,501 match
sources pass. The strict CPU prefix still stops at `$99F2` reading unknown
`$0223`: only its dead-value dependency is omitted by the pure models.
Do not invent RAM, rerun the multi-million-instruction packing proofs, or
claim that initialized CPU/display state follows from functional expansion.

Read `relax24-resources.md` and retained
`build/research/relax24/resource-recovery-01/resource-proof.json`. The real
`$C000` consumer calls `$AC00` with X=Y=$30, yielding request `02 30 30`.
Match the uploaded drive receiver's command/name contract, establish the
actual `00` file transfer and its final-two-byte JMP target, then follow the
real reader/article consumer. The other four embedded resources, header
meaning, any `DR` article identity and the cached Clarence review remain
unverified. Preserve the frozen older resource checkpoint and CPU stop.

The exact next drive input is the frozen inner image's `$25A8..$2797`,
uploaded as 496 bytes to drive `$0500..$06EF`; its source and upload identity
are in `build/research/relax24/article-analysis/consumer-proof.json`. Match
that receiver to the recovered `$AC00..$ACF7` sender/receiver. The retained
`00.prg` has a compatible `$2000` load address and final word `$080C`, but
that compatibility is not yet a proven transfer or executed reader entry.

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
the continuation steps there. Extend the verified Anomaly 28-job update,
publication and three-field witness to coherent scanout and wider timing
coverage from native-04. In parallel, bind Relax24 loader request `02 30 30`
to the uploaded drive receiver and actual `00` file/trailer. Preserve unrelated edits
and frozen evidence, use rtk for every shell command, and never invent unknown
RAM/hardware inputs or call scoped checks full-frame/FPS proof. Document new
findings and explicit gaps; keep the broader demo-research objective intact.
```
