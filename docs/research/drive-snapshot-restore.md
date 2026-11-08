# Drive snapshot restoration: two explicit differences

Anomaly's restored snapshot preserves the five checked C64 modules exactly,
but two drive modules are not byte-identical. The differences are confined to
**three payload bytes**. They must not be hidden by a whole-machine equality
claim or by rewriting saved state.

Both retained snapshots are 193,261 bytes:

| Snapshot, relative to repository root | SHA-256 |
| --- | --- |
| `build/research/anomaly/native-06/floor-line-drawn.vsf` | `2428affe32e414636d3444b1cfa72f41d25d7e466adf0ff0ad07dbabf28d32c8` |
| `build/research/anomaly/native-07/restored-floor.vsf` | `92718572db123cac63422ab8093b760baf8562b260d5a61bbc6ea87ab9ff8cb3` |

## What differs

Offsets below are zero-based within each module's payload, excluding its
22-byte module header. Multibyte values are little-endian.

| Module | Payload bytes | Field | Before → restored | Changed bytes |
| --- | --- | --- | --- | --- |
| DRIVE8 v2.0, 145 bytes | 27..30 | DWORD `GCR_head_offset` | 19,373 (`$4bad`) → 16,953 (`$4239`) | offset27 `$ad→$39`; offset28 `$4b→$42` |
| DRIVECPU0 v1.3, 2,152 bytes | 43..50 | CLOCK `stop_clk` | 169,513,186 → 169,513,187 | offset43 `$e2→$e3` |

Every other byte in those two payloads matches. The actual drive CPU clock
remains 169,513,187; `last_clk` remains 167,013,188, `cycle_accum` 62,614 and
`last_exc_cycles` 0. `GCR_head_offset` is a bit position, not a clock.

The complete C64MEM, MAINCPU, CIA1, CIA2 and VIC-II payloads match. That
statement does not imply full drive or whole-machine equality.

## Source explains resynchronization, with a remaining limit

Provenance is the retained official
[VICE3.10 archive](https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/),
local `build/research/quondam/hardware-source/vice-3.10.tar.gz`, SHA-256
`8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`.
Line references name members beneath `vice-3.10/` in that archive:

- `src/drive/drive-snapshot.c:184,388` writes and reads `GCR_head_offset`.
  `src/drive/rotation.c:256..271` interprets it as a bit offset.
- `src/drive/drivecpu.c:571,651` writes and reads `stop_clk`.
  `src/snapshot.h:112,129` defines CLOCK serialization as qword.
- After reading the CPU state, `src/drive/drive-snapshot.c:547` calls
  `drive_enable()`. `src/drive/drive.c:515..516` explicitly resynchronizes
  `stop_clk = *clk_ptr`. This explains the observed +1 exactly. It is not a
  rebase of the drive or main CPU clock.
- Later, `src/drive/drive-snapshot.c:570` calls `drive_set_half_track()`.
  `src/drive/drive.c:723..732` rescales the head offset by the new track size
  divided by the prior `GCR_current_track_size`.

The numerical fit `19373 * 6250 // 7142 = 16953` is consistent with that
rescale. The prior denominator is not serialized in DRIVE8, so these two
modules alone do **not** establish that those were its actual runtime sizes.
The source provides a restore adjustment mechanism; its exact head-offset
calculation remains an inference rather than a fully observed state history.

## Passive reproduction and continuation

Use the existing [snapshot reader](../../research/quondam/snapshot_state.py);
this reads files only and starts no emulator or CPU:

```sh
rtk proxy python3 - <<'PY'
import importlib.util
from pathlib import Path
import sys
sys.dont_write_bytecode = True
spec = importlib.util.spec_from_file_location("snapshot_reader", "research/quondam/snapshot_state.py")
reader = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reader)
before = Path("build/research/anomaly/native-06/floor-line-drawn.vsf")
after = Path("build/research/anomaly/native-07/restored-floor.vsf")
for name in ("C64MEM", "MAINCPU", "CIA1", "CIA2", "VIC-II"):
    print(name, reader.module_payload(before, name) == reader.module_payload(after, name))
comparison = reader.compare_modules(before, after)
for row in comparison["different_modules"]:
    if row["module"] in ("DRIVE8", "DRIVECPU0"):
        print(row["module"], row["differences"])
PY
```

For a future No Bounds native03 continuation, explicitly compare restored
drive/IEC state as well as C64 state. If exact drive/IEC continuation cannot
be established, prefer a **fresh original-disk boot** and natural navigation
to the next checkpoint. Preserve the original and restored snapshots and
their differences; do not edit snapshot state to force equality.
