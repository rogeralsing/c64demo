# A Mind Is Born: native relocation and IRQ proof

Checked 7 November 2026. The original release booted normally in PAL VICE 3.10. Native captures pass the complete 254-byte loaded-payload check, the 252-byte loaded-data relocation check, and an independent comparison of **all 65,536 physical RAM bytes across one normal IRQ body**. Its original ending naturally reaches the captured ROM reset vector and later BASIC READY. Seven raw RAM dumps match their same-stop VICE snapshots exactly. The [existing source/arithmetic note](a-mind-is-born.md) supplies the earlier 194-byte source comparison and bounded original-CPU arithmetic proofs; those are separate from this native run.

Original work and explanation: [Linus Åkesson / lft's walkthrough](https://www.linusakesson.net/scene/a-mind-is-born/index.php), [official PRG](https://hd0.linusakesson.net/files/a_mind_is_born.prg). The local 256-byte file is pinned by SHA-256 `7da29c8eed5acc39c5a1d3f0d40f5057c516cb6d2a04a18b15d71e6f8903f1f5`.

## Natural startup and checkpoint map

The two-byte load address is `$0801`; 254 payload bytes occupy `$0801..$08FE`. The BASIC text executes decimal **2225**, `$08B1`. Its next-line word is `$080D` in the released binary, despite `$080B` in the author's prose; the byte checker preserves that discrepancy.

| Address | Original bytes | Meaning and useful capture point |
| --- | --- | --- |
| `$08B1` | `EA` | Executed `NOP`, also the preceding IRQ jump's high operand. Record inherited X here. |
| `$08B2` | `78` | `SEI`; startup masks IRQs. |
| `$08B9` | `20 44 E5` | Calls the existing KERNAL screen-clear routine. |
| `$08BC` | `A2 FD` | Loads the copy-loop count. |
| `$08BE` | `BD 02 08` | Copy-loop source read. |
| `$08C9` | `4C CC 00` | Natural jump to relocated code. |
| **`$00CC`** | `A9 50` | First relocated instruction, before main `CLI`; best relocation boundary. |
| `$00D1` | `58` | Main enables IRQs. |
| `$00D2` | `AD 04 DC` | Main visual loop reads CIA1 timer low. |
| `$00DA` | `48` | Generated font byte pushed into the stack page. |
| `$00DF` | `8C 18 D0` | Main stores VIC screen/font selection. |
| **`$0031`** | `E6 13 E6 13` | Natural custom IRQ entry, after the KERNAL prologue. |
| `$00AF` | `4C 7E EA` | Jump to the existing KERNAL IRQ tail. |
| **`$EA7E`** | ROM-dependent | Stop before the tail acknowledges/restores/returns. Arm only after reaching `$0031`. |
| `$0045` | `4E 11 D0` | Terminal read/modify/write of `$D011`. |
| `$0048` | `6C FC FF` | Software jump through the ROM reset vector. |

The original vector low byte `$0314=$31` is inherited from the standard environment. Startup clears only `$0315`, routing the existing KERNAL dispatcher to `$0031`. The code neither installs a new interrupt timer nor supplies its own ROM dispatcher/tail.

**Recommended sequence:** reach `$08B1` naturally, then `$00CC`; save raw RAM before executing the latter's first instruction. Remove that breakpoint, reach `$0031` naturally, and capture its inputs. Only then arm `$EA7E` and capture the completed body. Arming the ROM-tail breakpoint during BASIC autostart could stop in unrelated earlier system activity.

The checkpoint JSON is `build/research/a-mind-is-born/native-analysis/checkpoint-map.json`. Creating it performs no CPU/emulator execution:

```sh
rtk proxy python3 research/a-mind-is-born/native_capture.py
```

## Relocation: exactly which bytes can be compared

The native `$00CC` capture checks all 254 loaded payload bytes against the original file, then checks **252 loaded bytes `$0803..$08FE` against zero page `$03..$FE`**. All match. The first two loaded payload bytes are not copied over the CPU port.

The loop also reads **`$08FF` into `$FF`**. `$08FF` is outside the loaded file, so it must not be filled with an assumed zero or compared with a nonexistent PRG byte. At the relocation boundary, `$FF` should equal the captured RAM byte `$08FF`. The script later uses `$FF` as a dummy write location.

The copy itself preserves `$00..$02`; a full-startup comparison across the ROM screen-clear call would additionally need that routine's side effects considered. The checker does not substitute a guessed initial zero page. It also checks that the resulting software IRQ vector is `$0031`.

Loaded RAM is useful as an original-byte reference **at this early boundary**. Later the visual loop deliberately reads and writes pages that include the now-dead loaded program. A later mismatch at `$0801..$08FE` is not automatically code corruption: execution has moved into zero page.

## One captured IRQ has an independent, feasible oracle

The normal handler reads its control inputs from zero page and the retained tables. It does not sample the live timer or SID envelope; those reads are in the main loop. Therefore the interval **`$0031→$EA7E`**, with the main loop suspended and the ROM tail not yet executed, is suitable for a precise arithmetic comparison.

`research/a-mind-is-born/native_capture.py` imports only the existing model module and calls its pure `music_reference` function on a copy of the captured input RAM. It does not instantiate the module's CPU class, run its large proof matrices, or emulate hardware. The model file hash must match the already passed arithmetic receipt.

The checker verifies the original relocated IRQ body and its important retained constants, including `$D3FF/$D01C` indirect bases and `$0D=$19`. That last literal supplies 25 for the SID-copy loop; its hardware pulse-width interpretation does not replace the shadow byte used by the CPU.

It then compares:

- all **65,536 physical RAM bytes** after the normal body with the predicted mutations;
- all changed zero-page locations, including clock, LFSR, script and self-modified main-loop bytes;
- final A/X equal to the current bass-frequency low shadow, Y zero, and unchanged SP between the two IRQ-body boundaries;
- the 34 expected literal store values in the receipt: nine VIC-target stores and 25 SID-target stores.

The last item is an expected instruction/write sequence derived from the oracle. It is **not** a comparison with SID readback or SID sound unless a separate native write trace is supplied. The normal body does not push/pop the stack, so unchanged physical stack RAM across these particular boundaries is meaningful; the preceding ROM IRQ prologue already wrote into the stack-backed font before the input capture.

The terminal reset branch is deliberately not accepted as a normal `$EA7E` transition. It needs its own dynamic VIC read and ROM-vector observation.

## Measured native transition

The original 256-byte PRG was autostarted without changing its BASIC header or forcing a program counter. Natural execution hit `$08B1` at clock 3,147,026 with inherited X zero. Breakpoints then observed these original-code boundaries:

| Boundary | Physical raster / zero-based cycle | VICE clock | Result |
| --- | --- | ---: | --- |
| `$00CC`, before relocated main | 95 / 21 | 3,190,278 | 254 original loaded bytes and 252 relocated loaded bytes exact; IRQ vector `$0031` |
| `$0031`, before first custom IRQ | 96 / 6 | 3,190,326 | Captured live inputs, A=`$00`, X/SP=`$F0`, Y=`$84` |
| `$EA7E`, after custom body | 107 / 28 | 3,191,041 | All physical RAM equals the independent prediction; A/X=`$02`, Y=`$00`, SP still `$F0` |

The body spans **715 observed emulated cycles**, including native VIC/CPU scheduling. This is a measured interval between instruction boundaries, not a claim that its instruction-only cost is 715 cycles. The only physical RAM changes are `$0A,$0B,$13,$1C,$CC,$FF`, all exactly predicted. `$CC` changes from `$A9` to `$09`, demonstrating the intended self-modified main-loop opcode in actual native execution.

The first IRQ arrives immediately after `CLI`, before the main loop has performed its first `$D018` selection. This confirms why that first IRQ must not be rejected for lacking the later steady ECM memory layout.

Each proof boundary includes both an explicit RAM-view dump and a VSF. The read-only checker uses the official VICE 3.10 `C64MEM` v0.1 writer: four port/cartridge bytes precede 65,536 physical RAM bytes, followed by 15 port-state bytes. Its version and 65,555-byte payload length are asserted. The three initial proof dumps, two visual dumps and two terminal dumps each agree with that extraction over **every RAM byte**, without masking the stack, CPU-port addresses, I/O-underlying RAM or ROM-underlying RAM. The pinned writer is `src/c64/c64memsnapshot.c:180–197,216–230`, SHA-256 `12058072799a1b0c8d46df7d978a8051bf4d6ef5e7fb26921ac82cd94ed2e149`, from the official VICE 3.10 archive pinned by the [Quondam hardware proof](quondam-raster.md).

## Later output observations and timer cadence

The run continued naturally to `$0031` after 128 and 512 completed custom IRQ calls. These counts follow the transcript's breakpoint ignores: 127 entries skipped after the already completed first body, then 383 skipped between the two visual checkpoints. The screenshots show distinct black/white text-grid states; the later image contains larger irregular dark gaps. These are observed original-program output, not a reconstructed whole-image oracle.

| Completed IRQ calls | Entry clock | Physical raster / zero-based cycle | Capture |
| ---: | ---: | --- | --- |
| 128 | 5,279,164 | 180 / 16 | `native-01/visual-0128.png` |
| 512 | 11,585,212 | 124 / 16 | `native-01/visual-0512.png` |

Both snapshots store `$D011=$50`, `$D018=$30`, and black low nibbles in the first 1,000 Color RAM cells, consistent with ECM screen `$0C00` and stack-page font use in VIC bank zero. The 24 unused Color RAM cells retain other initial values. The native I/O observation also reports screen `$0C00`, character data `$0000`, and no enabled sprites. Register readback `$D018=$31` includes the unused low bit; it does not contradict the stored `$30`.

The two observed entry clocks differ by **6,306,048 cycles over 384 IRQ intervals**, exactly 16,422 cycles per interval on average. Both snapshots show CIA1 Timer A latch `$4025` (16,421), with continuous system-clock counting and its IRQ enabled. The measured interval agrees with latch-plus-one and the inherited approximately 60 Hz music service on PAL. It does not establish 60 Hz visual updates, sound fidelity, or constant instruction-entry latency at every interrupt. The first immediately pending interrupt is not used to infer that cadence.

## Original ending: dynamic VIC read, software reset-vector jump

After the 512-call observation, the capture operator enabled warp to skip wall-clock waiting and set an execution breakpoint on the original `$0045`. The program reached that ending naturally. Warp was disabled there before the instruction observations below; no code, data, PC or ROM vector was supplied to make it terminate.

| Boundary | Physical raster / zero-based cycle | VICE clock | Observation |
| --- | --- | ---: | --- |
| `$0045`, before `LSR $D011` | 304 / 4 | 137,689,780 | A/X=`$40`; clock low `$13=$00`, bar/high `$20=$40` |
| `$0048`, before `JMP ($FFFC)` | 304 / 10 | 137,689,786 | Six cycles elapsed; stored `$D011=$68`, DEN clear |
| `$FCE2`, original ROM target entry | 304 / 15 | 137,689,791 | Five-cycle indirect jump through the captured `$FFFC` word |
| `$E5CD`, later ROM input/READY loop | 44 / 52 | 139,815,952 | BASIC V2 startup text and `READY.` observed |

The terminal clock is `$4000`, formed from the **noncontiguous** low byte `$13` and high/bar byte `$20`; `$14` is not its high byte. The original six instruction bytes `$0045..$004A` remain `4E 11 D0 6C FC FF`.

At raster 304 the current raster's ninth bit is one. The before-snapshot stores `$50` in VIC register 17, while I/O readback is `$D0`. Therefore the original read/modify/write shifts **`$D0→$68`**. The after-snapshot stores `$68`; readback is `$E8` because bit 7 still reports the current raster, not the written bit. The checker derives this from the captured raster/register values, checks both I/O readbacks and resulting CPU flags, and confirms that A/X/Y/SP are unchanged by the LSR. All 65,536 physical RAM bytes are unchanged, including underlying RAM `$D011`: the write goes to mapped VIC I/O.

The CPU-view read of `$FFFC/$FFFD` is `$E2,$FC`. The subsequent original `JMP ($FFFC)` reaches `$FCE2` in five cycles with the same registers and SP. Continued ROM execution reaches the observed BASIC READY state. This is a **software jump into the ROM reset path**, not an observed CPU RESET-pin sequence. The READY screenshot and monitor screen text establish the later output state; this pass does not compare every intermediate IRQ, ROM instruction, SID write or sound sample.

## Hardware and observation details

Record CPU registers with monitor `r` immediately before each proof RAM dump. Use explicit **RAM view** for the 64 KB dump and explicit **I/O or CPU view** for chip registers. Normal startup requires the KERNAL and I/O to remain visible; the checker records the CPU port and expects its low mapping bits to remain 7 at these boundaries.

Startup uses inherited **X** for its text-color/background stores before the ROM clear. Record X at `$08B1` rather than inventing a zero precondition. Color RAM being black should be established from that path or sampled directly. The handler later writes its palette shadows to border/background/ECM color registers; compare their low nibbles when inspecting native readback.

Some literal VIC stores target collision registers that ignore writes. SID registers mostly do not provide ordinary write-value readback. Expected literal stores must therefore remain distinct from the chips' readback values. Side-effect-free inspection also matters for collision latches and CIA interrupt acknowledgment.

The main loop sets `$D011=$50` for ECM and `$D018=$30` for screen `$0C00` and font `$0000`, assuming VIC bank zero. Its ECM glyph indices 32–63 address **`$0100..$01FF`, the stack page**. PHA-generated font bytes, hardware interrupt pushes, ROM prologue pushes and IRQ return traffic all share it. This is intentional visual state, not an isolated framebuffer.

The first IRQ can become pending immediately after `CLI`, before the first main-loop `$D018` write. Do not require `$D018=$30` at that first IRQ solely from the source ordering. A later main-loop capture can establish the active display state.

The existing CIA1 system service supplies the interrupt period. The author's 60 Hz music description is not a newly installed timer or a 60 Hz visual-frame guarantee. A timer-period claim requires actual CIA state or repeated native IRQ clock observations.

At song end, `$0045` executes `LSR $D011`. Reading `$D011` includes the current raster's ninth bit in bit 7. With the otherwise expected `$50` mode bits, the shifted write can therefore be **`$28` or `$68`**, depending on the sampled raster half. Clearing DEN is the robust consequence; the flat fixture's `$28` must not be imposed unconditionally on native output. The following `JMP ($FFFC)` is a software jump through the visible ROM vector, not a CPU RESET-pin event. Read the actual vector rather than hardcoding a particular KERNAL revision's destination.

## Capture interface and receipts

Place these raw RAM files and their monitor transcript in the root-owned native capture directory:

| Filename | Register PC at dump |
| --- | --- |
| `ram-after-relocation.bin` | `$00CC` |
| `ram-before-irq.bin` | `$0031` |
| `ram-after-irq.bin` | `$EA7E` |
| `monitor.log` | Includes `r` before each proof dump. |

Run the checker with the established environment, which supplies the existing model's import dependency:

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python \
  research/a-mind-is-born/native_capture.py \
  --capture build/research/a-mind-is-born/native-01
```

The passing output is `build/research/a-mind-is-born/native-analysis/native-evidence.json`, with the proof inputs, model/script hashes, measured IRQ-body interval, seven exact RAM-to-snapshot checks, two later visual observations and the terminal lifecycle checks. The transcript, snapshots, raw RAM and PNGs remain under `build/research/a-mind-is-born/native-01/`. The root-owned capture session closed at `2026-11-07T09:15:54.320107+00:00`; its recorded VICE cleanup exit code is −15.

This lane does not promise a deterministic whole-screen or sound replay. Timer phase, live SID envelope, ROM environment, asynchronous interrupts, cyclic stack/font writes and main-loop pointer interleavings remain part of the actual production.
