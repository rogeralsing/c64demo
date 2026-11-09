# Aloft: original bootstrap and resident loader identity

The original Aloft bootstrap installs **416 bytes at `$0160..$02FF` that match Sparta's primary SparkleCPP resident byte for byte**. This establishes a concrete loader/depacker implementation, including its public call addresses. It does not identify Aloft's exact host-tool release: the retained reference tag is `v3.4.260405`, which postdates Aloft's February 2026 release, and the complete bootstrap programs differ.

This is a passive source/data proof. No C64 instructions, assembler, emulator, downloaded script, or host binary were executed by this producer. It does not decode Aloft's trackmo resources or identify the layered-pattern part.

## Original bytes and primary source

The [original disk custody](aloft-original-20261109.md) retains all three original D64s and their actual DOS bootstrap chains. Each side has 48 directory-art PRG entries pointing at the same four-sector chain, track 18/sectors 7–10. There are three identical 832-byte PRG objects, rather than 48 distinct DOS programs per side. The bootstrap loads at `$0801`; its BASIC `SYS 2064` selects `$0810`.

Inputs are pinned in [loader-proof.json](../../build/research/aloft-20261109/loader-analysis/accepted-01/loader-proof.json). The important identities are:

| Input | Bytes | SHA-256 |
|---|---:|---|
| Each original bootstrap PRG | 832 | `7e283e390a10c2b7784ac1885081234c21a754d161e938babd504a13da2ee2e5` |
| Original disk proof | 19,558 | `113eadc069fbf46bb1011d7c9373d175f4c3536950f7a7ee173f471b8f1eef84` |
| Primary `loader.cpp` | 5,183 | `6b60719200fe199b0bb36b2b836e4d4aa09d574f3e50704baca38a64624617f1` |
| Primary `resources/sl.asm` | 20,735 | `223deb8c52b2aad69f8e5d4ba4573c196b0685f1a595f8e655f35c29d7777c02` |

The primary sources are [Sparta's `loader.cpp`](https://github.com/spartaomg/SparkleCPP/blob/41d6963b8334dd5f0046ff0dfccb29ef7d9ad0fb/loader.cpp) and [`resources/sl.asm`](https://github.com/spartaomg/SparkleCPP/blob/41d6963b8334dd5f0046ff0dfccb29ef7d9ad0fb/resources/sl.asm), both at commit `41d6963b8334dd5f0046ff0dfccb29ef7d9ad0fb`. Their retained HTTP-200 retrieval records, URLs and hashes are in [sparkle-acquisition.json](../../build/research/colors/binary/source/sparkle-acquisition.json). This new check parses the C++ byte-array initializer as data; it does not compile or evaluate it.

## Exact installer transformation

The original code at `$0894` disables interrupts, sets CPU port `$01=$35`, reduces the stack to `$015F`, and writes `$3C` to `$DD02`. At `$08A1` it sets X to zero and clears `$DD00`. The guarded loop starts at `$08A6`:

```asm
lda $099f,x
sta $0160,x
lda $0a3f,x
sta $0200,x
inx
bne $08a6
```

The reference script recognizes this exact two-copy structure, checks the initialization, and evaluates the **fixed indexed copies as data** for X=0..255. It predicts 512 copy writes over 416 unique destination bytes. The 96 overlapping destinations receive the same value from both source positions; that equality is checked rather than assumed. All original source bytes are present inside the PRG, ending at `$0B3E`. No unloaded or padded RAM is used.

The same calculation is independently applied to the primary C++ array, whose copy sources are `$09B0/$0A50`. Its complete PRG is 849 bytes, SHA-256 `c3af3c519034fb5fe8dfa4cc7749b8e55922f599de5caf6d6ef3158568ff87d0`. The two resident predictions match at **all 416 positions**, with zero mismatches:

```text
$0160..$02FF, 416 bytes
SHA-256 b09c13f9f60a28aa87cf1b157b4035df325eb60bf6d79fe8f176cf7aa606db48
```

The [resident binary](../../build/research/aloft-20261109/loader-analysis/accepted-01/resident-0160.bin) and [source contract](../../build/research/aloft-20261109/loader-analysis/accepted-01/loader-contract.json) retain the result, all guarded installer spans, source maps and API entry bytes. This result describes the state immediately after the copies. The following PAL/NTSC test and later receiver/depacker self-modification can change it.

## Source-bound API and depacker

| Original resident PC | Primary label | Contract |
|---|---|---|
| `$0160` | `Sparkle_IRQ` | Fallback IRQ saves registers/CPU port, acknowledges VIC IRQ, calls the patchable subroutine at `$016E`, restores, returns. |
| `$017A` | `Sparkle_SendCmd` | Sends the caller's command byte; source documentation distinguishes bundle, disk-change and drive-reset commands. |
| `$019C` | `Sparkle_LoadA` | Calls `Sparkle_SendCmd`, then falls into `Sparkle_LoadFetched`. |
| `$019F` | `Sparkle_LoadFetched` | Receives a drive-provided block before depacking. |
| `$0205` | `Set01` | Loads `$35` into CPU port `$01`; `$0209` is its RTS/`Done`. |
| `$021C` | `Sparkle_LoadNext` | Sequential bundle entry; consumes buffered state and receives another block when needed. |

The API label meanings come from the pinned assembly, especially lines 263–327, 397–399, 426–458 and 654–666; each address has an original byte guard. `$02/$03` are the destination pointer, `$04` is bit state, and `$0300..$03FF` is the received buffer. These are source contracts, not evidence that every possible command was exercised in Aloft.

The resident includes a compressed-data grammar, not only an IEC receiver. Assembly lines 418–423 describe a 256-byte block with destination fields at the high end and a descending byte stream interleaved with bit state. The implementation handles literal copies and short/near/far mid/long matches, with distinct end-of-file, end-of-block and end-of-bundle tags. `LitCopy` at source lines 527–530 and `MatchCopy` at 558–561 copy downward through Y after adjusting the destination pointer. Match input is already materialized destination memory, so a future decoder must track valid source bytes, overlapping matches and 16-bit arithmetic explicitly.

A breakpoint at `$021C` is **not by itself a count of external files**. `Sparkle_LoadFetched` can re-enter the sequential depacker after receiving another block, and `Sparkle_LoadNext` can consume already buffered data. Native call/return stacks and data-generation binding are needed to count a demo controller's external requests.

## Natural checkpoints and initial destination

The original bootstrap gives useful checkpoints without inventing a scene address:

1. `$0810`: original BASIC SYS entry.
2. `$08B5`: both indexed copies have finished, before PAL/NTSC patching. The initial bytes are `AD12D0 CD12D0 F0FB 30F6`.
3. `$019F`: first `Sparkle_LoadFetched` entry.
4. `$FE00`: configured return destination after the first successful loader invocation.

The fourth address comes directly from the original handoff at `$08F9`: `LDA #$FD/PHA; LDA #$FF/PHA; JMP $019F`. It pushes return value `$FDFF`, and RTS adds one. It is not taken from the reference source's different `$10AD` configuration, and it is not an identified effect entry. The first loading operation may overwrite the bootstrap, which the primary installer comment explicitly anticipates.

## Replay and remaining boundary

Run the new producer into a **fresh** output directory:

```sh
rtk proxy python3 -B research/aloft-20261109/loader.py \
  --output build/research/aloft-20261109/loader-analysis/new-replay
```

The accepted producer is [loader.py](../../research/aloft-20261109/loader.py), 10,584 bytes, SHA-256 `f727a4bf66ad88b2ba409cb2df157cae0884c29333c2f3f9d2d97da07c5e162f`. Its accepted proof is 7,554 bytes, SHA-256 `9ed6758c8a18bdd0350b223806d9334070ed3001e679dc0e3a8e398357647897`. A fresh self replay reproduces all four files, **22,583 bytes**, exactly; see [self-replay-check.json](../../build/research/aloft-20261109/loader-analysis/self-replay-check.json). An independent peer read the full source and also reproduced all four files exactly; [peer-replay-check.json](../../build/research/aloft-20261109/loader-analysis/peer-replay-check.json) is 1,397 bytes, SHA-256 `7fcd157562c79e1df8cdfe7c800ce9bf22254297e5fc9c6ec298b325fdbfbd49`. The earlier candidate is retained separately, including its subsequently corrected source-line metadata.

The resident equality makes a pure format decoder plausible. It does not yet establish how original D64 sectors become the `$0300` byte sequence, how drive-side indices find bundles, or which bundle contains the requested layered-pattern effect. The next source step is to bind those disk/drive transformations to original bytes and decode a small native-observed bundle from original disk inputs. Completed native RAM must remain an oracle rather than a decoder seed. Full host-tool version, effect identity, display mode and performance remain outside this static proof.
