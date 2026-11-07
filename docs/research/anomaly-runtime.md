# We Are The Anomaly: provisional live Arcade checkpoint

**PROVISIONAL: the Arcade runtime investigation is incomplete.** The owner-closed `native-03` checkpoint now proves the natural Arcade entry, initialization bytes, two floor updates and one rejected upper-copy gate. It contains **11 RAM/VSF pairs and two PNGs**. No accepted upper job, completed 28-job update, buffer publication or 96-write floor-field `$D016` trace has been observed in this batch. A passing bounded receipt is not a complete 50 fps proof.

This continues the [source mechanism](anomaly-arcade.md) and [original Sparkle/payload identity](anomaly-binary.md). Root alone controlled VICE. The analysis checker reads the saved original bytes and captures, then evaluates integer arithmetic and RAM-copy models. It executes no CPU, emulator, downloaded tool, hardware response or pixel renderer. The separate [native Arcade audit](anomaly-native-arcade.md) owns session/restore/observer provenance.

The batch restores the closed `native-02/humanmade-entry.vsf`, with full RAM and CPU state checked against that source. The owner allowed warp during the earlier-demo transit with `SoundEmulateOnWarp=1`, then confirmed **warp off at the guarded incoming driver**, before capturing Arcade's load call. Runtime captures retain speed 100 and normal warp-off execution. Transit elapsed time is not used as an effect benchmark. The session is now closed; the provisional label concerns unfinished witnesses, not a claim that its process remains live.

The early checkpoint avoided reused-address false hits:

```text
break exec $08ae if (@ram:$08bb == $20) && (@ram:$08bc == $00) && (@ram:$08bd == $3b) && (@ram:$08ab == $20) && (@ram:$08ad == $c0)
```

These bytes identify original bundle 35's incoming driver: `$08AB: JSR $C000`, `$08AE: JSR $0809`, later `$08BB: JSR $3B00`. Its eight-page relocation has legitimately changed `$0899:$A8→$B0` and `$089C:$C0→$C8`. Native RAM agrees with **all 59 remaining driver bytes plus those two source-derived modifications**. A demand for the initial pristine 61-byte driver would be wrong at this later stop.

The software index `$02FF` is observed as **33 before loading Arcade and 34 afterward**. It must not be equated with the disk's bundle number 36: earlier direct `$0200` calls bypass the software increment. The byte guard, complete driver state and original decoded payload establish identity without that assumption.

| Natural capture | PC | Clock | Meaning |
| --- | --- | ---: | --- |
| `arcade-load-call` | `$08AE` | 160,083,859 | Before the original sequential-load wrapper. |
| `arcade-load-return` | `$08B1` | 163,832,261 | Arcade payload loaded; wait for the previous part. |
| `arcade-entry` | `$3B00` | 164,459,398 | Actual original call into Arcade. |
| `arcade-ready` | `$3B88` | 164,560,071 | Initialization complete, before RTS. |
| `upper-rejected-post` | `$3D89` | 164,602,120 | Current follow-up checkpoint, raw raster 44/cycle 4. |

At both the load return and `$3B00`, all **41,523 original payload bytes** match the independently decoded bundle: `$2800..$BF2E` and `$E000..$EB03`. The matched original Link artifact's symbol file is the applicable map. The older Parts symbol file's `$3D66/$3D69/$3D6C` hooks are not this production's `$3D83/$3D86/$3D89` hooks.

Initialization installs 96 phase bytes and clears 96 fractional accumulators. All 3,555 floor-update code/pointer bytes remain identical to the original before their first update. It relocates **3,328 bytes** from actual entry RAM `$E000..$ECFF` to `$F040..$FD3F`: 2,820 original helper-code bytes plus **508 separately preserved native-prestate bytes beyond that short payload**. Every byte of the full copy matches. Those extra bytes are not synthesized zero padding. The initial upper-bitmap duplicate helper copies **256 bytes as written**; this note does not generalize that operation into a complete hidden-buffer initialization.

The floor-update hooks are inside music IRQ `$3BE8`, after its `$3C0A: CLI`. Stabilizer IRQ `$B400/$B430` can therefore nest. The host oracle starts from each actual `$3D83` capture and predicts only the 96 fine-scroll values, 96 accumulators, insertion-pointer operands and the 3,840-byte floor bitmap. It does not assume absent nesting or whole-machine/CPU-register equality.

For line `i`, it adds rate `102+i` modulo 256. A carry decrements `$D016`'s saved byte. The original `DCP` detects `$C0→$BF`, resets to `$C7`, copies 39 bitmap bytes left by one cell and inserts one byte from the line's forward stream. The oracle independently indexes those cells and advances the literal source-address operand.

| Observed update | Carry lines | Coarse-copy lines | Bitmap stores | Native elapsed clocks |
| --- | ---: | ---: | ---: | ---: |
| `floor-a-pre→post` | 0 | 0 | 0 | 1,589 |
| `floor-b-pre→post` | 70 | 8 | 320 | 5,207 |

The second update wraps exactly lines **32, 40, 54, 62, 70, 72, 80 and 88**. Both intervals match every fine byte, accumulator, floor code/pointer byte and bitmap byte in the declared domains. Their unfiltered RAM observations retain two and four stack-byte differences, respectively; the host model does not manufacture JSR stack traffic. These elapsed clocks belong to the observed IRQ call intervals, including their execution context. They are not a whole-field timing result or a display-rate measurement.

The upper gate capture is **before `$36E6: CMP #$24`**, after the real `LDA $D012`. Its A register contains **`$2B`**, not a guessed value read from a later raster snapshot. The exact branch predicate is `bit7((A-threshold)&$FF)`. `$2B-$24=$07`, so BMI is not taken and the routine returns. The observed interval to `$3D89` is **10 clocks**, and **all 65,536 RAM bytes are unchanged**. Status remains pending. This corroborates the rejected path; it does not observe an accepted row copy.

Four exec tracepoints were installed before leaving `arcade-ready`: `$36F3` (pixel row), `$38BB` (color row), `$39B1` (new color column) and `$39CA` (new pixel column). The recorded window through this checkpoint contains **zero hits**. Consequently none of the first upper update's 28 jobs has yet run. The source claim of 13 pixel rows + 13 color rows + two new-column jobs remains an expected sequence to witness, not a runtime result of this batch.

The final saved state is:

| State | Value |
| --- | --- |
| PC / clock / raw beam | `$3D89` / 164,602,120 / 44:4 |
| Upper status / row / color-row counter | 1 / 0 / 0 |
| Job dispatch | `$36F3`, first pixel row still pending |
| Upper fine phase / delay / buffer selection | `$C7` / 14 / 0 |
| Current pixel source → destination | `$4008 → $E000` |
| Current color source → destination | `$6001 → $CC00` |
| Incoming color/pixel column pointers | `$6B00` / `$B900` |

The follow-up restore file is `build/research/anomaly/native-03/upper-rejected-post.vsf`, SHA-256 **`db7c7cae5e97a0f0c90229fde26767d162ff3f2dd28f5d2d44e18147644a7449`**. Its matching raw RAM hash is `9fc3ecf7924e67edd8261c7b8c465fef0db93906504e27cfc06c4f9a5bcf7ca6`. A new owner-controlled session can restore that state with the same original side-one disk, verify the exact stop, install the four job tracepoints, and wait for a sampled gate that actually accepts:

```text
break exec $36e6 if (((A - @ram:$36e7) & $80) != $00) && (@ram:$0007 != $00)
```

This uses VICE's actual A register and the mutable immediate threshold. Parentheses preserve its documented expression order. Capture the accepted `$36E6` prestate and its `$3D89` return, then compare the selected job's source/destination RAM without inventing a raster read. `upper_model`'s accepted-job branches and `publication_model` currently remain **unexercised host models**, outside the passing runtime evidence.

Subsequent bounded targets are first **`$B84B`** before buffer publication, then **`$B864`** after the swap/reset/status setup and port writes. Check the actual pre-publication status instead of assuming that all jobs completed. The source swaps unconditionally; incomplete status would be a useful falsifying result. Count the expected 13+13+1+1 job hits before that first swap.

For the separate floor-register witness, capture **`$B400→$B828`** with a `$D016` STORE trace. Original code expands 40 static write sites into **96** table-indexed writes through the guarded Y-controlled loops: eight sites ×3, eight ×2, eight, eight, eight ×5. The subsequent upper-phase store is `$B857` and must be distinguished from those 96 floor writes. The receipt archives the planned original-PC/index schedule, but **no native `$D016` store sequence or complete display field was captured here**. Preserve original pending checkpoints and receipts before extending either model or its scope. No full 50 fps claim should follow from these partial witnesses.

Reproduce the finite closed-checkpoint comparisons with:

```sh
rtk proxy python3 research/anomaly/inspect_arcade.py
```

[inspect_arcade.py](../../research/anomaly/inspect_arcade.py) SHA-256 is **`c016696ab829fec52b9b10830af2b8111806cc629f734d40b3c7cbc5a392b978`**. Ignored `runtime-analysis/runtime-proof.json` is **`17ed1c6adafb0b33f0a0ca0b9830bfcfa5ff913818a8ad4bd18bcd5c53f7b2fb`**, with **20 exact domain checks**, all 11 snapshot/RAM identities, source pins, floor-store lists, rejected-gate state and the planned register schedule. `pass=true` refers only to these completed bounded checks; `runtime_witness_complete=false` and the explicit missing-witness list remain authoritative.
