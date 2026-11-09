# Perpetual Fragility: paused research checkpoint

Research execution was paused by the user on 9 November 2026. Publishing this
checkpoint does not resume the research goal. The full objective remains to
scan the web, read blogs and articles, find boundary-pushing demos, reverse
engineer/decompile them, understand their mechanisms and document every finding.

## Last completed evidence boundary

The accepted [Aloft motion continuation](aloft-motion-continuation-20261109.md)
and its artifact inventory remain the last completed publication: **11,546
artifacts / 283 receipt rows**. Its read-only audit is:

```sh
rtk proxy python3 -B build/research/handoff-20261109/aloft-motion-inventory.py
```

The Perpetual work below is retained **outside that accepted inventory**. Do not
count its draft native reader or candidate payload analysis as accepted results.
Generated captures and analysis outputs remain in ignored `build/`, following
the repository's existing policy. This commit preserves the source and notes;
it does not upload the local capture corpus.

## Retained work and limits

- [Primary evidence](perpetual-primary-20261109.md) and
  [primary.py](../../research/perpetual-20261109/primary.py) retain the author's
  article, five explanatory figures and exact 149×207 ASCII sprite layout.
  Eight self-replayed files / 403,982 bytes match. No independent root replay
  was performed for this new lane before the pause.
- [payload.py](../../research/perpetual-20261109/payload.py) contains source-only
  typed relocation and initialization models. `payload-analysis/candidate-03/`
  retains eight relocation records, predicted installed memory, the 663-deposit
  startup bitmap, packed-coordinate analysis and WIZ/sprite-X descriptors.
  These are **candidates**, without a final accepted receipt or native renderer
  comparison. Do not replace the actual implementation with a synthetic WIZ
  example when continuing.
- [Native custody draft](perpetual-native-20261109.md) and
  [native.py](../../research/perpetual-20261109/native.py) remain fail-closed:
  `CLOSED_PROFILE` is unset and the final role/comparison integration is
  unfinished. The preliminary root check finds all 9,467 loaded packed bytes
  and all 17,403 independently predicted unpacked bytes equal to native RAM.
  This is not yet a selected closed-custody receipt.

## Original native case and closure

The original packed PRG ran in `build/research/perpetual-20261109/native-01/`,
using root-owned handle 70913, PID 13008 and port 63952. No snapshot was restored,
no emulator was restarted, no disk was changed and no PC/RAM patch was used.
Warp stayed off. Four natural RAM/VSF pairs were captured:

| Stem | PC | Machine clock | RAM / VSF sequences |
| --- | --- | ---: | --- |
| `packed-sys` | `$080D`, packed generation | 3,093,663 | 14 / 15 |
| `unpacked-entry` | `$080D`, decoded generation | 4,763,877 | 20 / 21 |
| `installed-init` | `$1800`, relocated effect initialization | 5,070,726 | 26 / 27 |
| `menu-entry` | `$1873`, before menu setup | 5,237,127 | 32 / 33 |

The native-app UI service failed to start. A macOS System Events SPACE request
targeted the owned x64SC process, but delivery to the emulated CIA is unproved.
The guarded `$1944` menu exit was never observed. Sequence 36 remained pending
and produced one observation-timeout notice; it was not retried or restarted.

After the pause, the owner closed the same handle. The helper interrupted the
pending run with read-only `r`, drained the response at `$191F`, then terminated
and reaped its owned VICE process. The observer exited 0; VICE exited −15.
Closure time is `2026-11-09T12:39:26.241789+00:00`. There are **35 completed
responses and one interrupted response**, with no final RAM/VSF pair at the
interrupted stop. No first effect IRQ, completed snow image, WIZ update or FPS
was captured.

The [passive freeze script](../../research/perpetual-20261109/freeze_paused_case.py)
preserves these owner facts without claiming native acceptance:

- `native-01-files.json`: 2,469 bytes, SHA-256
  `de3d111dd77c4b90d2bd7990159da9c859c278edaca1a1306cc1c78189488f69`;
- `paused-owner-closure.json`: 5,647 bytes, SHA-256
  `13243c29844c14291a1a5a98f2f2443e485cf3dece84b383ecbca876ff88fe6f`.

All fifteen raw case files, the preliminary byte check, candidates and failed
observations remain retained locally. Never overwrite or reopen this closed
case merely to replay passive models.

## Resume only when requested

First inspect this checkpoint and the retained closed case. Finish a strict
closed profile that preserves sequence 36's wait/interruption and the unproved
SPACE delivery; do not filter them away. Bind the four natural stops to their
actual code generations and compare both complete packed/unpacked ranges.
Review and independently replay the typed relocation/initialization candidates
before promoting them. A future rendering observation needs a new owned case
and a source-supported menu/input path; a guessed PC jump or memory patch is
not the original demo's execution.
