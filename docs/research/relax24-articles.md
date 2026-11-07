# Relax #24: resource consumer and the next article-reader boundary

Research date: 7 November 2026. The [two packing stages](relax24-decoder.md) establish the program bytes needed for a narrower consumer trace. That trace reaches a real resource decoder at **`$991D`** and a later **`JMP $C000`**, but it does not yet establish the post-expansion reader or the side-2 article format. **No original article or coding-review filename is identified in this batch.**

## Source and drive-installation path

The input is the frozen inner-stage range `$0801..$FFFE`, SHA-256 `970be5dec0f0204c474dd718aaa2ab1dcc45e18ac94f3357cc8fad165d6d3cf1`, already checked against the original pure CPU fragment. [inspect_articles.py](../../research/relax24/inspect_articles.py) requires the exact inner proof `d86df447082e7ee3d7d55bf8bfaabdc9abe0ff09784746a28656ba78f43eb9cd` and its recorded image identity. It does not mutate that proof or any decoder output.

At `$2000`, the original code reads device state `$BA`, patches `$2501/$255E`, calls `$2500`, then jumps to `$9400`. The installer at `$2500` uses KERNAL command-channel routines, beginning with `$2505: JSR $FFBA`; those routines are not executed or mocked here.

Its source establishes an `M-W` upload path: **31×16 = 496 bytes**, source `$25A8..$2797`, target drive addresses `$0500..$06EF`. The later six-byte command is `4D 2D 45 00 05 0D`, `M-E $0500` followed by CR. This establishes the static installation mechanism, not successful drive execution, an IEC timing proof or the later article-loading protocol. No named loader library is assigned from a signature guess.

## The actual resource consumer

The `$9400` source requests port `$15`, disables display output and calls `$991D`. That routine copies `$9900..$991C` to zero page, then loads five bytes preceding its supplied end pointer into **`$D3..$D7`**. Their uses identify an initial bit buffer, a remaining-byte counter and an output cursor:

| Original call | Supplied end | Five descriptor bytes | Remaining bytes | Initial output cursor |
|---|---|---|---:|---|
| `$9417`, conditional on `$02A6` | `$8FBF` | `1B BA 00 62 B5` | `$00BA` | `$B562` |
| `$942D` | `$9F57` | `4B 23 02 00 10` | `$0223` | `$1000` |
| `$9438` | `$BCE7` | `CB E2 04 00 40` | `$04E2` | `$4000` |
| `$9536` | `$9D2F` | `4B FA 02 00 10` | `$02FA` | `$1000` |
| `$9572` | `$8DF6` | `27 F1 0D 00 D0` | `$0DF1` | `$D000` |

These are **embedded resource descriptors consumed by identified code**. They are not declarations that the twenty side-2 files use this layout. An output cursor also does not establish a decoded output extent.

The final block's count and descriptor delimit the compressed resource bytes **`$8000..$8DF0`**, followed by the five-byte descriptor at `$8DF1..$8DF5`. Its completed expansion is the next useful source of reader code.

The recovered pre-resource bytes also contain an unusual source overlap: `$9516` jumps to `$8ED0`, the `$FB` operand of the preceding BNE. If entered unchanged, that byte would be a 6510 undocumented ISC opcode. This is a pre-expansion observation, not a native execution claim or evidence of another packed stream. The later static successor path passes through `$9519` and the two final resource calls above; the initialized runtime state remains unproved here.

After those calls and additional setup, `$95B8` jumps to `$8FE0`. That code patches `$AE7C/$AE81=$4A` and `$AE7D/$AE82=$1D`, then **`$8FF0` jumps to `$C000`**. The pre-resource `$C000` bytes are `90 90…`; they are not promoted into the post-resource menu or article consumer. This is an explicit code-state boundary, not a filename inferred from directory labels.

## Strict execution stops on an unavailable literal-path read

To inspect the decoder without inventing a return frame, the checker starts at the actual callsite setup **`$9425`**, including the original `$942D: JSR $991D`. Its initially known RAM is only the checked `$0801..$FFFE` output. It declares decimal clear, a safe stack, no IRQ delivery and RAM visibility except I/O, as requested by the excluded source port setup. This is an isolated source-state fragment, not execution of the whole `$9400` initialization.

After **235 completed original instructions / 796 nominal cycles**, execution stops at:

```text
99F2  B1 D1   LDA ($D1),Y
unknown effective address: $0223
```

No decoder output byte has been stored at that point. The value at `$0223` is not supplied. CPU-port and I/O accesses are likewise forbidden.

The current mode byte `$CE` is zero, selecting the literal path. The following original instructions load X from `$CE`, then call the relocated byte reader at `$00D8`, overwriting A. Thus the unavailable value appears dead for this literal output. Nevertheless, this check **does not skip that load, synthesize a byte or claim the call completed**. A future format abstraction would need to declare that distinction and validate the meaningful data paths separately.

The [consumer proof](../../build/research/relax24/article-analysis/consumer-proof.json) retains the exact boundary, established decoder state, all five resource descriptors and source identities. The [curated instruction listing](../../build/research/relax24/article-analysis/consumer-instructions.txt) includes only identified C64 code intervals. Uploaded drive bytes and compressed resources are not disassembled as C64 reader instructions.

## Article questions remain open

The earlier observation that twenty files have a first big-endian word equal to file size minus five remains an observation. This batch has not linked their load/receive path to `$991D`, assigned the other fields, or located the initialized menu's filename-to-category mapping. In particular, **`DR` is not assumed to mean the coding review**.

The next bounded step is a known-memory format model or appropriately isolated fragments for the `$8DF6` resource, followed by the actual post-expansion `$C000` consumer. Only that code can justify a side-2 header interpretation and an attempt to decode an original article. The cached web transcription and Clarence attribution have not been validated against original text here; no wholesale article text is added to tracked files.

## Reproduce this checkpoint

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/relax24/inspect_articles.py
```

The script consumes saved, hash-pinned decoder evidence and uses the existing py65 environment for only the strict prefix above. It performs no VICE, native-process, drive, KERNAL or hardware action. All earlier sources, notes and proofs remain unchanged.
