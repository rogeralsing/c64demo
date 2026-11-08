# Relax #24: original drive and C64 loader contract

Research date: 8 November 2026. The recovered `$C000` request **`02 30 30`** now binds to the actual **496-byte uploaded drive image**, its two-byte directory lookup, the original side-2 `00…` entry, its 55-sector file chain, and the recovered `$AC00` receiver. This is an **original-byte-gated functional contract**, conditional on successful sector service and completed serial byte handshakes. It is not a captured transfer or original CPU/native execution.

[loader-contract.py](../../research/relax24/loader-contract.py) checks 36 original instruction intervals and reproduces the byte-level behavior with the Python standard library. It consumes the frozen [archive](../../build/research/relax24/archive-proof.json), [inner](../../build/research/relax24/decoder-analysis/inner-proof.json), [consumer](../../build/research/relax24/article-analysis/consumer-proof.json), and [resource](../../build/research/relax24/resource-recovery-01/resource-proof.json) receipts without rewriting them. The earlier **235-instruction CPU stop at unknown `$0223` remains unchanged**. No CPU, ROM, drive, KERNAL or hardware response is supplied to pass that stop.

The source remains the [original Relax #24 release archive](https://c64.rulez.org/pub/c64/Magazines/Relax/Relax_24_Phuture.zip), already acquired and hash-pinned by the archive receipt. No article identity is inferred from a two-letter directory name.

Before correcting two receiver edge descriptions, the preceding script and loader receipt were preserved in the [correction archive](../../build/research/relax24/loader-contract-01/checkpoint-archive/wrap-carry-correction-before.json). The current checker pins and verifies those historical copies. The added edge cases are synthetic byte-interface checks, not new CPU or native observations.

## Upload and filename binding

The original inner installer sends 31 `M-W` chunks of 16 bytes. Its destination calculation subtracts `$20A8` from each source pointer:

```text
inner source:       $25A8..$2797
uploaded drive RAM: $0500..$06EF
bytes:              496
execute command:    4D 2D 45 00 05 0D   (M-E $0500, CR)
drive-image SHA256: d0225bd8f23d19858bddf5ff2dd1cbfa7a95c12bd9ec556522c9e49606d29748
```

The checked [drive image](../../build/research/relax24/loader-contract-01/drive0500-06ef.bin) is extracted from those actual source bytes. It is not a separately selected loader implementation. Its entry calls `$067F` for a hardware handshake, then `$05C3` to receive three bytes through `$065D`:

| Received byte | Actual drive use |
|---|---|
| First, `$02` | Saved on the stack and returned in A; `$0506: LDA $0E` immediately replaces it. No command dispatch follows. |
| Second, `$30` | Stored in `$0E`, then copied to `$06A5` as the first filename byte. |
| Third, `$30` | Stored in `$0F`, then copied to `$06A6` as the second filename byte. |

Thus `$02` is a transmitted byte, but assigning it a distinct command operation would exceed this source. All 256 possible first-byte values yield the same directory lookup in the functional model.

The drive starts its lookup at track `$12` (18), sector 1, using `$0700` as the sector buffer. At `$051D` it accepts entries satisfying **`type & $83 == $82`**, then compares only the first two filename bytes. It advances by 32 bytes for each slot. After the eighth slot, it takes the next directory-sector number from `$0701` while resetting the track to 18; the next-sector byte's high bit ends the search. It does not compare the remaining fourteen filename bytes or follow the directory link's track byte.

For `30 30`, the first match is directory track 18, sector 1, slot 1: original type `$C2`, filename prefix `00`, first file sector **track 17, sector 0**. The type mask accepts its locked, closed PRG entry. This binding follows the drive instructions and original sector bytes, rather than the extracted filename label alone.

## Sector service and transfer format

At `$05FB`, the drive requests asynchronous service by writing `$80` to `$04`, enables interrupts, and waits while `$04` is negative. Status `$01` reaches `$062D: SEI; RTS`. Other statuses enter a retry/recovery path, including accesses to previously resident `$16/$17` state and a `$C0` request. Exhausting retries removes the sector-call return address and enters the same failure sender used for a missing filename.

The functional model explicitly assumes that a successful call establishes the requested original D64 sector at `$0700`. It does **not** execute, replace or prove the resident service that makes this happen. The uploaded bytes alone do not establish the drive firmware, initial zero page, interrupts, job completion or physical disk access.

After a successful file-sector read, the drive uses bytes 0 and 1 as its next track and sector. A nonfinal sector emits offsets 2 through 255. For the actual nonempty final sectors, it emits offsets 2 through the last-count byte inclusive, totaling `last_count - 1` file bytes. The checker retains the original wrapping Y loop; it does not generalize the normal case to a hypothetical empty final sector.

The byte-level transfer format is:

| Bytes | Meaning in the checked sender/receiver pair |
|---|---|
| `$AC $AC` | One literal `$AC` in file data. The drive doubles every `$AC`, including one in a hypothetical load header. |
| `$AC $C3` | End of a nonfinal sector; the C64 performs its inter-sector handshake. |
| `$AC $FF` | End of file; the C64 returns with carry clear. |
| `$FE $FE $AC $F7` | Drive failure response. Before an address header has been received, as in the missing-file path, the C64 takes `$FEFE` as its cursor and returns carry set without storing data. |

The C64 control path actually treats any `$AC` followed by a byte other than `$AC`, `$FF` or `$F7` as a handshake control. `$C3` is the value this drive sends. Literal `$C3`, `$F7` and `$FF` need no escaping unless preceded by the escape byte in the encoded stream.

If a later sector fails after the address header was already consumed, the same failure sender's `$FE $FE` bytes are ordinary output data at the current cursor. Only the following `$AC $F7` terminates with carry set. A bounded synthetic receiver case `00 20 55 FE FE AC F7` checks three stores (`55 FE FE`) and returned cursor `$2003`; it does not claim a native sector failure occurred.

The C64 consumes its **first two received bytes directly** as a little-endian load address, before entering the escape parser. Thus the header path does not undo a doubled `$AC`; the real `00` header `00 20` avoids that issue. The output loop increments `$AE/$AF` after every stored byte. At a full `$FFFF->$0000` wrap, `$AC57: BNE` falls through **`$AC59: CLC`**, returning carry clear before another stream control is consumed. A bounded synthetic `FF FF 55 AC FF` case checks the single store at `$FFFF`, cursor zero, carry clear, and unread `$AC $FF`. The actual `00` transfer never wraps.

The original bit routines send low bits first and assemble eight received bits by repeated ROR. The checker exhausts all 256 byte values, verifies that the initial accumulator value is discarded after eight bits, and round-trips every byte through the escape format. This verifies byte order and encoding only. CIA/VIA pin mapping, inversion, DDR settings, hardware polling, interrupt timing and successful handshakes remain outside the model.

## `00`: file bytes to returned cursor and jump target

The drive model follows all 55 original `00` sectors, reproducing **13,822 file bytes** exactly. Its sector identities, sector hashes and file bytes agree with the earlier independently implemented archive extractor. The file SHA-256 remains:

```text
889a7648417cf6734832dd4cf8f5883415d8dc31457b33803e7272630a2bbc6a
```

There are 48 literal `$AC` bytes and 54 nonfinal-sector separators. Including doubled escapes and the final `$AC $FF`, the expected serial byte stream contains **13,980 bytes**, SHA-256 `4e907336b46ad86a295394eaeaa0d8acb17d673b6afb7e69829739926014d331`. The [wire artifact](../../build/research/relax24/loader-contract-01/request00-wire.bin) is a generated expectation, not a native capture.

Applying the recovered C64 receiver's byte contract gives:

| Result | Checked value |
|---|---|
| Initial address bytes | `00 20`, load address `$2000` |
| Output stores | 13,820 distinct ascending bytes, `$2000..$55FB` |
| Returned cursor | `$55FC` |
| Return carry | Clear |
| Restored X/Y | `$30/$30` |
| Stored-byte SHA-256 | `dd8dff99a0f316d5d2a17a98949b738f31fbba6497151d763724a7f386d8fecf` |

Every received output byte equals the corresponding original file byte after its two-byte header. The stores do not overlap `$AC00` loader or `$C000` consumer code. The generated RAM artifact includes a known mask; bytes outside those stores are placeholders, never treated as established machine state.

At `$C15D`, the actual source subtracts two from the returned cursor, reads the final two bytes at `$55FA/$55FB`, and writes them into `$C3B2/$C3B3`, the operand of the later `$C3B1: JMP`. Those bytes are **`0C 08`**, giving **`JMP $080C`**. This now follows from the directory selection, actual file chain, escape protocol and C64 output cursor together; the earlier load-header/trailer compatibility observation alone did not establish it.

The later `$C380` source copies `$2000..$ABFF` to `$0801..$9400`. That mapping places the received `00` body at `$0801..$3DFC`, with `$080C` beginning **`A0 00 78` (`LDY #$00; SEI`)**. The first relocated word is also `$080C`, consistent with its BASIC-layout prefix. In this isolated transfer model the source tail `$55FC..$ABFF` remains unknown. The checker neither supplies those bytes nor claims that the full copy, intervening KERNAL calls or patched jump execute.

The drive-level model also reconstructs all **21 original side-2 file streams**, agreeing with their independently extracted bytes, sector counts and sector hashes. That check does not route the other files' first two bytes through `$AC00` as load addresses or assign an article-header format.

## The second request and remaining native boundary

The next recovered foreground request, `$C17B`, sends **`02 FF FF`**. No original directory entry matches `FF FF`; the actual lookup checks all 24 slots over directory sectors 1, 4 and 7. It emits `FE FE AC F7` and jumps to external drive ROM **`$EB22`**. The C64 receive contract returns carry set with cursor `$FEFE`, restores X/Y to `$FF/$FF`, and makes no output store. The ROM target's behavior is not supplied, and the first byte `$02` is still not a separately decoded shutdown command.

The next evidence that would promote this contract to an actual transfer is precise:

1. After the real upload, capture drive RAM `$0500..$06EF` and compare it with the pinned image above.
2. Observe the actual drive's sector service establishing the requested track/sector buffer at `$0700`, with a successful return at `$062D`. Capturing the first directory and first file sectors would bind the code to original disk access.
3. At the real C64 **`$C15D`**, after `$C15A: JSR $AC00` returns, capture registers/flags, `$AE/$AF` and RAM `$2000..$55FB`. Expected cursor: `$55FC`; expected carry: clear; expected stored-byte hash: `dd8dff99a0f316d5d2a17a98949b738f31fbba6497151d763724a7f386d8fecf`.

These are capture requests, not claimed results. Initialized menu state, continuous bootstrap execution, physical transfer timing, later copy reachability, article decoding and coding-review identity remain open.

## Reproduce

```sh
rtk proxy python3 research/relax24/loader-contract.py
```

The new [loader proof](../../build/research/relax24/loader-contract-01/loader-proof.json) pins the script, frozen receipts, source images and generated artifacts. Its [source-site gates](../../build/research/relax24/loader-contract-01/source-sites.json), [directory lookup](../../build/research/relax24/loader-contract-01/request00-lookup.json), [sector ledger](../../build/research/relax24/loader-contract-01/request00-sector-ledger.json), byte stream, output RAM and known masks are retained beside it. The checks guard distinct protocol risks: selecting the wrong directory offsets, treating `$02` as a dispatch table, truncating the final sector, losing escaped `$AC`, confusing sector control with data, or returning the wrong end cursor. No native process or earlier multi-million-instruction proof is rerun.
