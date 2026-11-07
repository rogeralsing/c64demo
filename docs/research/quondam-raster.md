# Quondam's repeated character row: native raster evidence

Research date: 7 November 2026. The original PAL program repeats **the VIC's cached 40 character/color entries**, even while VCBASE advances. A late `$D011` change lets RC wrap from 7 to 0 and keeps display active without replacing that cache. Charset and palette changes then give successive bands different pixels from the same cached character codes.

This closes the row-reuse question left open in [the original-program map](quondam.md). It does not reconstruct the full tunnel image or its asset generator. The root-owned VICE session supplied the snapshots and traces; the analysis tools below only read those files and control no emulator or process.

## Exact source and snapshot schema

The decoder follows the **official VICE 3.10 release source**, not a current trunk layout. [Official source archive](https://sourceforge.net/projects/vice-emu/files/releases/vice-3.10.tar.gz/download):

- 14,366,175 bytes;
- SHA-256 `8e5bac18cbcb9f192380ad3ef881f8790f5b75c41d7b3da65d831985d864d6d1`;
- `configure.ac` declares 3.10.0;
- `src/viciisc/vicii-snapshot.c` declares **VIC-II module v1.3**;
- `src/core/ciacore.c` declares **CIA module v2.5**.

The captured files identify producer 3.10.0, machine `C64SC`, and VIC model 1, the PAL 8565. The source archive, untouched selected files, per-file hashes, failed tag-route attempt, and provenance are preserved in `build/research/quondam/hardware-source/`.

`research/quondam/snapshot_state.py` exposes:

```python
read_snapshot(path)          # serializable header/modules/vicii/cia dictionaries
module_payload(path, name)  # exact raw payload, separate from JSON state
compare_modules(a, b)       # all payload differences, without exclusions
```

The VSF header is 58 bytes. Each module has a 16-byte name, one-byte major and minor versions, and a little-endian four-byte size including its 22-byte header. The captured VIC-II module is 123,437 bytes, with a 123,415-byte payload. The decoder parses its fixed 1,881-byte core and preserves hashes of the remaining draw/raster state; whole-module comparisons still include every byte.

Selected **payload-relative offsets**, derived from the actual writer order:

| Field | Offset | Bytes |
| --- | ---: | ---: |
| 64 stored VIC registers | 1 | 64 |
| Raster cycle / raster line | 65 / 73 | 4 each |
| `vbuf`, cached screen codes | 84 | 40 |
| `cbuf`, cached color entries | 124 | 40 |
| Draw buffer | 169 | 520 |
| Allow-bad-lines latch | 693 | 1 |
| Idle / VCBASE / VC | 697 / 701 / 705 | 4 each |
| RC / VMLI / bad-line state | 709 / 713 / 717 | 4 each |
| Serialized Color RAM | 761 | 1,024 |

The draw-buffer constant is **65×8**, even for this PAL capture; assuming 63×8 would misalign the later fields. The serialized Color RAM comes from the real Color RAM array via `mem_color_ram_to_snapshot`, separately from charset RAM under `$D800`.

## Why a late bad-line condition repeats cached characters

Christian Bauer describes this as **doubled text lines** in §3.14.5: creating the bad-line condition late in the last row lets RC roll over and continues the display without reading another character row. His cycles are one-based. [Author's VIC-II reference](https://www.cebix.net/VIC-Article.txt), preserved here at revision date 2024-09-29, SHA-256 `ed558b2480638b153d0ead4726b8b675e4a0b945f2ab4d37c17a3d892cf00828`.

The pinned VICE code gives a precise implementation to compare with the snapshots:

- `vicii-chip-model.c` gives PAL character-matrix fetch slots at hardware cycles 15–54, zero-based 14–53.
- `vicii-cycle.c:528–563` checks the bad-line condition and, at hardware cycle 58, copies VC into VCBASE when RC is 7. If display is active or a bad-line condition holds, RC increments modulo eight and idle is cleared.
- `vicii-cycle.c:594–608` performs a matrix fetch only when both the bad-line condition and a matrix-fetch slot are present.
- `vicii-fetch.c:172–173` forms a text graphics address from **cached `vbuf[VMLI]`, RC, and the charset selection**, rather than reading a new screen code from VCBASE on every pixel row.

Thus VCBASE need not stay at zero. Its advance does not refresh `vbuf` by itself. A late condition after the matrix-fetch window can wrap RC while the same cached codes supply the next glyph rows. Quondam's changing charset/palette bands exploit that distinction.

## Native timing and the first row wrap

The original PRG retains SHA-256 `e86e4bcf40e859f4ec3fcc83a86f8f0c172b6efa0a38d8dc199a85717fddc17c`. No payload or PC patches were used. The complete sampled store trace has **51 `$D011` writes**; the 24 late-window writes are reported at zero-based raster cycle **54**, which is hardware cycle **55** in Bauer's convention. This is after the matrix-fetch slots and before the hardware-cycle-58 row-counter update.

The focused snapshot sequence belongs to the following captured frame, whose vertical-scroll phase shifts the late raster from 55 to 56. Do not combine the previous frame's raster numbers with the next frame's state as if they were one trace.

| Snapshot / observation | Raster / zero-based cycle | RC | VCBASE | VC / VMLI | Idle | Bad line |
| --- | --- | ---: | ---: | --- | ---: | ---: |
| `initial-row-fetch.vsf` | 50 / 10 | 1 | 0 | 40 / 40 | 0 | 0 |
| `before-late-write.vsf` | 56 / 50 | 7 | 0 | 36 / 36 | 0 | 0 |
| After the `$D011` STA completes, monitor observation | 56 / 54 | 7 | 0 | VMLI 40 | 0 | late condition asserted |
| `after-late-wrap.vsf` | 56 / 60 | 0 | 40 | 40 / 40 | 0 | 1 |

Before the write, `$D011=$19` and YSCROLL is 1, which does not match raster 56's low bits. Afterward `$D011=$18`, YSCROLL is 0, and the late condition matches. The full cached screen row is **`$4C,$4D,…,$73`** in both snapshots; all 40 cached colors are `$08`.

The state change is therefore not a frozen-VCBASE trick: VCBASE advances from 0 to 40. RC wraps, idle remains zero, and the character cache remains the same. The parser reads these from the official serialized fields, rather than inferring them from a screenshot or ordinary CPU memory.

## Twenty-four consecutive cached-row wraps

The valid `after-window-01.vsf` through `after-window-24.vsf` captures occur at rasters **57, 65, …, 241** within one frame. Every capture has:

- RC 0, idle 0, and bad-line state 0 at the sampled start of the next line;
- VCBASE and VC equal to **40, 80, …, 960**;
- VMLI 40, before that new line's normal VC/VMLI reload;
- the same cached codes `$4C..$73` and cached colors `$08`;
- all 1,024 serialized Color RAM entries equal to `$08`.

The charset selections and the `(0,12)/(12,0)` multicolor register orientations change across those bands, confirming that the retained codes are interpreted through changing data/register state. The new direct Color RAM evidence also supports selector `11` being black in this capture; it is no longer only the initialization-path inference recorded for `native-01`.

There is also a physical-RAM discriminator. In the initial-row snapshot, the active screen's first 40 bytes at `$7000..$7027` are `$4C..$73`, while the **next** 40 bytes at `$7028..$704F` are 24 zero bytes followed by 16 `$AA` bytes. They are not another copy of the cached row. The receipt derives RAM from the pinned `c64memsnapshot.c` v0.1 writer layout—four prefix bytes, 65,536 RAM bytes, and 15 suffix bytes—and cross-checks that mapping against all 65,536 bytes of the separately saved raw untraced RAM, without exclusions. The repeated cache therefore cannot be explained by merely reading identical successive screen rows.

The **post-window instruction stop is not always at cycle 1**:

| Captures | Actual zero-based cycle |
| --- | ---: |
| 01–05 | 1 |
| 06–12 | 12 |
| 13 | 1 |
| 14–16 | 8 |
| 17–24 | 1 |

The receipt retains those measured positions and accounts for them in its clock comparisons. It would be incorrect to call the complete post-store sequence constant-latency. Sprite DMA is a possible contributor, but no individual stall-cause proof was performed here.

## Instrumentation controls retain the real difference

The plain store trace, a constant-print automatic action, and the later automatic I/O-action recheck all produce the same 51 store records. The completed frame controls compare every module, including the full VIC-II payload and its draw/raster buffers. CPU, RAM, and complete VIC state agree at the endpoints.

Both whole-file comparisons nevertheless have **one byte that differs**, at absolute offset 65,838: CIA1 v2.5 payload offset 33.

| Control pair | Byte values | Full relative TOD-alarm values |
| --- | --- | --- |
| Plain trace / untraced | 139 / 137 | 4,235 / 4,233 cycles |
| Instrumented / control frame | 185 / 186 | 4,281 / 4,282 cycles |

The exact writer at `ciacore.c:2298` serializes `todclk - rclk` using `SMW_CLOCK`; `snapshot.h` defines this as an **eight-byte** clock, beginning at offset 33. The read path schedules the corresponding TOD alarm again. The flags indicate the TOD counter is stopped, but the scheduled tick/alarm phase remains serialized emulator state. It is **not a disposable diagnostic byte**, and whole-machine identity is not claimed.

The CIA code models power-tick variation, but that does not establish the specific cause of these trial differences. The parser and comparison receipts retain them without masking or excluding the CIA module.

Two failed observations are preserved separately and excluded from the display proof. The first automatic I/O-action trial diverged unexpectedly; the later matching recheck did not reproduce it, so the cause remains unknown. A raster-49 conditional wait failed to reach its checkpoint before the observation timeout; its subsequent wrong-frame snapshots are named `attempt-timeout-*`. Neither is silently relabeled as a successful capture or evidence that the I/O command always perturbs execution.

## Receipts, reproduction, and limits

The primary native receipt is **`build/research/quondam/native-02/raster-evidence.json`**, produced by the separately owned `research/quondam/raster_capture.py`. It pins the original program, complete transcript, parser, code states, valid snapshots, controls, and rejected observations. The session was closed after capture.

The source/schema cross-check is `build/research/quondam/hardware-source/schema-proof.json`; source URLs/hashes are in `downloads.json` and `selected-source.json`. The module reader can also be used directly:

```sh
rtk proxy python3 research/quondam/snapshot_state.py \
  build/research/quondam/native-02/before-late-write.vsf \
  build/research/quondam/native-02/after-late-wrap.vsf \
  --output build/research/quondam/native-02/decoded-wrap.json
```

This proves cached-row reuse and its row-counter behavior for the captured original-program frame in VICE 3.10's PAL 8565 model. It is stronger than merely observing repeated CPU screen entries or a visually similar tunnel. It does not provide an independent full-frame pixel oracle, recover the asset generator's 3D mathematics, establish every pose's timing, or substitute for measurements on physical VIC revisions.
