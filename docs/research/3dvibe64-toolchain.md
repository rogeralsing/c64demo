# 3Dvibe64: retained toolchain and first local build

On 8 November 2026, this research case built a new six-vertex octahedron with
the previously pinned 3Dvibe64 1.15.1 SDK. It used PowerShell 7.6.9 and a locally
compiled 64tass 1.60 r3243 on macOS 26.5.1 arm64. The SDK source remained
unchanged. These host executions belong to this new case; the earlier
[source-only study](3dvibe64.md) remains frozen with its original limits.

The [scene](../../research/3dvibe64-native/scene.json),
[scene rationale](3dvibe64-native-scene.md), [emitted-build audit](3dvibe64-build.md)
and [native pixel study](3dvibe64-native-pixels.md) describe separate inputs and
claims. This note covers acquisition, extraction, host execution and recovery.

## Acquisition and trust boundary

The official [PowerShell release API](https://api.github.com/repos/PowerShell/PowerShell/releases/latest)
returned v7.6.9, published 25 October 2026. The retained API document identifies
the macOS arm64 archive. Its SHA-256 matched both the API asset digest and the
official release's `hashes.sha256`. That checksum file is UTF-16 with a BOM.
The [release page](https://github.com/PowerShell/PowerShell/releases/tag/v7.6.9)
and its download URLs are primary sources. The acquisition receipt records
the actual retrieval time, headers, redirects, bytes and digest; a server's
HTTP Date is not substituted for the host timestamp.

The [64tass project](https://tass64.sourceforge.net/) provided
`64tass-1.60.3243-src.zip` through SourceForge. Its retained SHA-256 is a custody
pin for those downloaded bytes. No separate publisher checksum was obtained.
The official source archive, rather than a binary from a demo ZIP, was compiled.

The SDK archive is the already acquired `3Dvibe64_1.15.1_source.zip`, bound to
upstream commit `b19df459b7efe50d514b59fe876c0bc7c326c5b4` in the frozen study.
The builder and bundled material table were inspected before execution.
Research use does not establish permission for commercial SDK redistribution;
the retained SDK contains its PolyForm Noncommercial license.

All downloads and retrieval records live under
[acquired](../../build/research/3dvibe64-native/acquired/). The extraction layout
is retained in [extraction-layout.json](../../build/research/3dvibe64-native/extraction-layout.json).
Archive extraction rejected absolute paths, traversal and inappropriate special
members. Python's data extraction filter was used for the PowerShell tar.

## Executed commands

All tools are local to `build/research/3dvibe64-native/`. No global installation
or persistent PATH change was made. The root agent alone ran tools and VICE.
The [command recorder](../../research/3dvibe64-native/run_step.py) starts an
explicit argument array with `shell=False`, captures stdout/stderr, waits for
the child and records its actual exit status. It was not used to own VICE.

First, `/usr/bin/make -j4 CC=/usr/bin/cc 64tass` built only the requested compiler
target. The selected Makefile target compiles and links; no install target ran.
Its [execution receipt](../../build/research/3dvibe64-native/tool-steps/assemble-64tass/result.json)
records exit zero. The produced compiler identifies itself as
`64tass Turbo Assembler Macro V1.60.3243` in the actual assembly output.

The [PowerShell AST probe](../../research/3dvibe64-native/probe-builder.ps1)
parsed the unchanged builder without executing its body. PowerShell Core
reported version 7.6.9, 67,441 tokens and no parse errors in the
[probe result](../../build/research/3dvibe64-native/tool-steps/powershell-parse/stdout.bin).

The actual builder then ran with these explicit selections:

```text
-SceneFile <repo>/research/3dvibe64-native/scene.json
-Precision legacy
-GraphicsMode 6
-MemoryLayout high-basic-v2
-VideoStandard pal
-CameraMode fixed
-CameraViewport normal
-Quality fast
-Projection extended-table
-NoFpsOverlay
-SkipCmdUpdate
```

`TASS64_EXE` pointed to the newly compiled local executable.
`POWERSHELL_TELEMETRY_OPTOUT=1` was set for the process. PowerShell ran with
`-NoLogo -NoProfile -NonInteractive -File`; the full absolute argument array,
working directory and environment overrides are retained in
[build-01/command.json](../../build/research/3dvibe64-native/build-01/command.json).
The audited ordinary `legacy` route does not use the optional Python, Mode 7,
legacy-plus or native-probe helpers. Its only external build process is 64tass.
`-SkipCmdUpdate` prevents launcher CMD rewrites. No network or installation
operation is part of that selected SDK route.

The builder returned zero after assembly and its final memory checks. This
matters because the SDK copies the PRG before those checks; an existing PRG
alone would not prove a successful build. The
[SDK delta](../../build/research/3dvibe64-native/build-01/sdk-delta.json) contains
exactly three additions: `work/3Dvibe64.asm`, `work/3Dvibe64.prg` and
`work/build/3Dvibe64.prg`. All 387 original SDK files remained byte-identical.

The retained products are
[assembly](../../build/research/3dvibe64-native/build-01/products/3Dvibe64.asm)
and [PRG](../../build/research/3dvibe64-native/build-01/products/3Dvibe64.prg).
The PRG is 49,711 bytes, including its two-byte `$0801` load address.
A second 64tass invocation added VICE labels to the saved assembly. Its PRG
matched the first build byte-for-byte. It exported 968 symbols. Exact command,
result and streams remain in [symbols-01](../../build/research/3dvibe64-native/symbols-01/).

## Passive verification and cache policy

The [toolchain auditor](../../research/3dvibe64-native/inspect_toolchain.py)
executes no compiler, SDK code or emulator. It rechecks official PowerShell
digests, archive identities, 1,148 extracted regular files, executable hashes,
four successful command receipts, parser result, SDK delta and equal PRGs.
The accepted [proof](../../build/research/3dvibe64-native/tool-analysis-02/toolchain-proof.json)
binds those inputs. Its
[member index](../../build/research/3dvibe64-native/tool-analysis-02/archive-member-index.json)
is a catalog of derived files, not 1,148 additional independent acquisitions.
The archives contain 613 PowerShell members, 198 64tass members and 387 SDK
members; directory and other non-regular members explain the smaller file count.

The first passive audit attempt successfully checked the files but failed while
making an output pin from a relative path. Its partial catalog remains in
`tool-analysis/`. The auditor now resolves paths and uses an output-independent
catalog name. Acceptance belongs to `tool-analysis-02/`; the partial first
directory is not represented as a successful receipt. No tool or native capture
was rerun to fix that bookkeeping error.

Recheck in a fresh directory:

```sh
rtk proxy python3 research/3dvibe64-native/inspect_toolchain.py \
  --output build/research/3dvibe64-native/tool-analysis-replay-NEW
```

A new output directory is required; replace `NEW` with an unused suffix.
The root's retained `tool-analysis-replay/` proof and catalog matched the
accepted files byte-for-byte. For a host rebuild, retain the old case and
extract into a new workspace; use the command receipts as the exact build
recipe. A passive proof replay does not rebuild the PRG or establish an
identical binary on every host compiler.

The handoff retains the downloaded archives and retrieval records, member
catalog, actual executed `pwsh`/`64tass` binaries, SDK before/delta inventories,
execution receipts, products and own analysis sources. Unchanged unpacked SDK,
PowerShell runtime files and 64tass source members are reconstructible caches;
they are not individually repeated as handoff artifacts. Their full identities
remain checked by the catalog. Tool execution was real; no claim of a host
sandbox or physical C64 validation follows from these receipts.
