# Second Reality native-03: CA continuation, four loads and DB stops

The closed native-03 batch passes **11 full-RAM/snapshot pairs**, totaling
720,896 compared bytes without address exclusions. Every recorded CPU state
and beam position matches its snapshot. Four complete original-file payloads
also match, totaling **12,913 bytes**. The four PNGs are output observations;
this is not an independent display-frame reconstruction.

The session restored exactly one saved snapshot:
`native-02/ca-iteration-d.vsf`, at `$C85F`, clock **300,297,278**. The first
post-restore CPU observation equals the source snapshot. This is a snapshot
continuation, not another cold boot or an uninterrupted extension of
native-02. **No synthetic inputs, code/PC patches or later restores** occur
in this session. The earlier sessions' explicitly recorded synthetic menu
inputs remain part of its inherited history.

The [native-02 receipt](../../build/research/second-reality/native-parts-analysis/native-parts-evidence.json)
is frozen at SHA-256
`fc9be5785818dd4febbd5f8a9837394956130f75582884516a562c45c140feb4`.
The checker pins it, its identified source snapshot, the reused reader hashes
and the complete new monitor transcript. Session metadata records owner
closure at **2026-11-07 12:59:35 UTC**, VICE cleanup exit `-15`; it does not
claim the demo exited naturally.

## Actual loaded-file witnesses

The first natural `$CF00` stop is **307,281,968**, raster 307/cycle 35,
with `A=$00, X=$44, Y=$41`: a literal **DA** request. The subsequent source
mapping and complete payload comparisons come from the independent
[transition checker](../../research/second-reality/inspect_da.py), not a
new disk parser or CPU execution in this lane.

| File | Header load range, inclusive | Payload bytes | Actual return PC | Return clock | Final loader pointer |
|---|---|---:|---:|---:|---:|
| DA | `$4000..$47FF` | 2,048 | `$0843` | 309,201,376 | `$4800` |
| DB | `$C000..$CBFF` | 3,072 | `$084C` | 311,246,041 | `$CC00` |
| EA | `$6000..$6EE8` | 3,817 | `$0855` | 313,650,839 | `$6EE9` |
| EB | `$7000..$7F87` | 3,976 | `$085E` | 316,242,809 | `$7F88` |

All four full payload ranges are exact. Their original PRG and payload
hashes are checked, their native capture hashes must match this lifecycle
receipt, and the actual `$CF3B/$CF3C` destination pointer is checked at each
return. The source worker's
[transition receipt](../../build/research/second-reality/da-analysis/da-transition-proof.json),
SHA-256 `eb75376e089794a6d1468090274b8a27259e3550b91f3139566e95e87beffe2c`,
retains 18 exact transition checks. Its seven overlapping RAM/snapshot
capture identities are joined to this batch rather than silently reused
from different stops.

Load headers alone do not identify execution entries or future effect
roles. DA is a preload in this transition; the next observed execution
entry is **DB at `$C000`**, clock 316,575,687, raster 250/cycle 57.

## Prepared-state and iteration observations

The capture named `db-prepared` reaches **`$C620`**, clock 317,986,879,
raster 186/cycle 49. Its RAM, CPU and beam identity are exact. The separate
DB analysis owns the meaning and correctness of generated preparation;
the capture label alone does not prove a generator or renderer model.

The four later stops all reach `$C200`:

| Capture | Clock | Raster/cycle |
|---|---:|---:|
| `db-iteration-a` | 318,777,145 | 250 / 43 |
| `db-iteration-b` | 318,858,785 | 298 / 35 |
| `db-iteration-c` | 318,940,175 | 30 / 29 |
| `db-iteration-d` | 319,023,529 | 105 / 34 |

The observed intervals are **81,640**, **81,390** and **83,354** clocks.
These are logical code-boundary intervals under the original machine's
interrupts and VIC activity. They are not whole-frame checkpoints, fixed
presentation periods or isolated graphics costs. PNG integrity is checked
and each file is tied to its exact native context; no screenshot is promoted
to a complete-frame pixel oracle.

## Preserve the non-file staging bytes

The transition proof also checks an 8,192-byte staging copy into
`$2000..$3FFF`, conditional on actual DB-entry RAM. EA and EB account for
7,793 bytes. The other **399 bytes** are explicitly separated:

- 143 preserved native pre-state bytes: a 23-byte tail and a 120-byte tail.
- 256 bytes from the explicitly backed-up current loader page.

They are not invented padding or extra EA/EB file contents. This passive
checker pins that state-transition result and its input captures; it does
not rerun the transfer or duplicate its source analysis.

## Reproduction and scope

Run [native_next.py](../../research/second-reality/native_next.py) against the
existing closed files. It starts no emulator, process, interpreter or input
action. Its authoritative
[native-next-evidence.json](../../build/research/second-reality/native-next-analysis/native-next-evidence.json)
has `status: complete`, `pass: true`, with source, capture, restore and
script hashes retained. The original disk file configured for this session
is also checked against the already established disk hash.

This batch establishes capture lineage, exact physical RAM/CPU/beam context
and the independently matched file/transition bytes. It makes no new claim
about DB's pixel-combining rule, full display composition, physical-VIC
timing, SID audio or whole-demo behavior. See the earlier
[native continuation](second-reality-native-parts.md) and
[CA coverage analysis](second-reality-ca-coverage.md) for their separate
contracts.
