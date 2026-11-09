# Aloft creator follow-up and Perpetual Fragility's original payload

The targeted creator refresh did **not** recover an author explanation or a
named visual match for Aloft's reconstructed striped effect. It did produce a
separate concrete result: a strict typed decoder now reconstructs **17,403
bytes at `$0801..$4BFB`** from the author's original **Perpetual Fragility**
PRG. This consumes the complete compressed stream and its own end marker.
The predicted payload has not yet been compared with native execution, and its
snowfall generator and display have not been reconstructed.

The [accepted receipt](../../build/research/aloft-motion-20261109/primary-analysis/accepted-01/primary-proof.json)
is 8,993 bytes, SHA-256
`37327f79e5fd255b78d4c7754e561c40135ce35076ee5ff2d6b7e6fcf5f307ea`.
The [producer](../../research/aloft-motion-20261109/primary.py) parses data and
performs finite byte/bit/token transformations. It does not interpret CPU
instructions, run a downloaded program, assemble source, or start an emulator.

## What the refreshed creator routes establish

Quiss's [homepage](https://www.quiss.org/) links actual
[writings](https://www.quiss.org/writings.html),
[blog posts](https://www.quiss.org/writings_blog_posts.html),
[projects](https://www.quiss.org/projects.html), and
[legacy work](https://www.quiss.org/legacy.html). None of those acquired text
bodies mentions Aloft. The blog index lists font/browser articles. The legacy
page concerns his older C64 work. Raistlin's current
[article index](https://c64demo.com/llms.txt) also contains no Aloft entry.
This is a bounded negative about the inspected pages, not a claim that the
implementation is unpublished everywhere.

The refreshed [creator interaction notes](https://csdb.dk/release/?id=259056&show=hidden)
still concern Sparta's joystick-controlled flipped Kefrens on side 2 and
Quiss's playable hangar game. Neither supplies the striped renderer's
algorithm or identifies it with one of those interactions. Peer reviews were
kept separate from implementation-author evidence.

The [CSDb release](https://csdb.dk/release/?id=259056) and the
[Pouët entry submitted by Raistlin](https://www.pouet.net/prod.php?which=105671)
link byte-identical 2,359-byte screenshots. Visual inspection shows an
airplane against a blue sky and clouds. It does not match the striped
prediction preview. Both attempted Demozoo gallery routes returned **HTTP
403**; their response bodies are retained, without inferring gallery contents.

The [HTTP audit](../../build/research/aloft-motion-20261109/primary-analysis/accepted-01/http-audit.json)
checks **22 responses / 1,943,831 retained body bytes**: 19 HTTP 200, two 403,
and one 404. The 404 is the Exomizer project's old wiki URL; its official
repository API and tagged source archives succeeded. TLS verification was not
bypassed.

The refreshed Lunatico author pages, ZIP and conventional `NOTE & VSP TOOL`
extraction reproduce previously retained identities. They are retained as
refresh evidence, not presented as a new rain explanation. The existing
[Lunatico rain note](lunatico-rain.md) remains the relevant result. Its video
caption failures were not retried, and no remote video/audio was downloaded.

## Binding the original compressed program

The earlier [primary reading](row-cache-and-wiz-20261109.md) retained
[Åkesson's author-linked PRG](https://hd0.linusakesson.net/files/lft-perpetual-fragility.prg):
**9,469 bytes**, SHA-256
`9770854332c3a60bb25eaa580d91e47f5d98ff6d47c7b6fdfec1a60b82e985df`.
That pass parsed its BASIC header. This pass follows the original wrapper's
stored bytes and compressed format further.

`SYS 2061` reaches `$080D`. Its prefix is
`A0 35 BA BD 04 2C 9D FC 00 CA D0 F7 4C B4 2B`: a tail-resident copy followed
by a branch to `$2BB4`. The stage at `$2BB4` copies 53 bytes with descending Y.
Its indexed source operand is the start **minus one**, which matters for the
compressed stream boundary.

| Original source bytes | Declared data transformation |
|---|---|
| `$2CC7..$2CFB` | Copy to `$07E7..$081B` |
| `$081C..$2BB3` | Already present portion of the compressed stream |
| `$2C05 = $22` | Initial sentinel bit buffer |
| `$2C06..$2C07 = $00,$4B`, plus Y=`$FC` | Destination starts below exclusive end `$4BFC` |
| `$2C08..$2CC6` | Stored resident corresponds to logical `$0100..$01BE` |

Thus the packed data is **9,165 bytes** at reconstructed addresses
`$07E7..$2BB3`. The typed decoder derives that split from the original copy
operands and length; no native buffer supplies the bytes.

The first tail-copy loop uses `TSX`, so copying the entire resident requires
the entering stack pointer to be at least `$C2`. That is an explicit static
precondition. There is no native startup-SP witness in this lane, and the
format result is not represented as observed execution of the SFX wrapper.

## Format and prediction

Magnus Lind's [official Exomizer repository](https://bitbucket.org/magli143/exomizer)
supplied the tagged 2.0.11, 3.1.1 and 3.1.2 source archives. The
[primary source anchors](../../build/research/aloft-motion-20261109/primary-analysis/accepted-01/packer-primary-anchors.json)
check the retained 3.1.1 C/assembly/header files against their archive members.
The 3.1.1 tag identifies commit
`6a152b5605648f7a41eadd4b011a93ec92f74dd8`.

The original resident binds an **Exomizer 3 format profile** with these
properties:

- MSB-first sentinel bits and interleaved raw-byte extensions for widths over
  seven bits.
- 52 coding entries, split into a length table and three offset tables.
- An explicit first literal flag, with no implicit-first-literal shortcut.
- No offset-reuse branch.
- Literal, overlapping match, literal-block and terminating token classes.

This corresponds to feature-mask bits 0 and 1 in the author's protocol
definitions. It does **not** prove which Exomizer host version produced the
original PRG. The optimized resident's byte guards and destination convention
are checked directly; the current official default profile is not silently
substituted for them.

The decoder begins with unknown output memory. A match can read only an
already written output byte; valid overlapping matches consequently work.
Every output write is also checked against the remaining unread compressed
address interval. Unknown memory, an unsupported token, an unread-source
overwrite, output wrap or trailing compressed bytes rejects the prediction.
The SFX's display-progress I/O hook is not executed or modeled as payload RAM.

The original stream produces **2,117 literal tokens / 5,112 literal bytes** and
**2,647 match tokens / 12,291 match bytes**, followed by one end token. All
9,165 compressed bytes are consumed; the final bit buffer contains only the
`$80` sentinel. The output is one contiguous known range at `$0801..$4BFB`.

The [predicted unpacked PRG](../../build/research/aloft-motion-20261109/primary-analysis/accepted-01/perpetual-unpacked.prg)
is **17,405 bytes**, including its two-byte load header, SHA-256
`4280209180aba0847703b7a1d6e0682df372a927cbcef25656ae04eee53a4863`.
Its entry at `$080D` starts with the original-derived bytes
`A9 7F 8D 0D DC 78 A9 35 85 01`. Full predicted memory, its known-byte mask,
coding tables and the token ledger accompany it. None uses expected native
output as an input or an acceptance condition.

## Reproduction and remaining boundary

Run into a fresh output directory:

```sh
rtk proxy python3 -B research/aloft-motion-20261109/primary.py --output build/research/aloft-motion-20261109/primary-analysis/new-replay
```

The [self replay](../../build/research/aloft-motion-20261109/primary-analysis/self-replay-check.json)
matches all **11 files / 1,207,395 bytes** exactly. The first exploratory
decoder probe rejected an unread-source overwrite caused by including a table
constant in the transferred 53-byte prefix. The original indexed copy exposed
the error. Two later candidates rejected source-anchor transcription errors
before token decoding. Their inputs, source snapshots and failure notes remain
retained; acceptance uses the corrected source and a fresh output directory.

Root independently read the complete frozen producer and repeated the passive
run into another fresh directory. Its
[review/replay report](../../build/research/aloft-motion-20261109/primary-analysis/root-replay-check.json)
also matches all 11 files / 1,207,395 bytes exactly. That report is 2,000 bytes,
SHA-256 `4a77846a9ff6655bba5a920535c2eac98da3e173dd1ba86a1ca7a517a9239cc9`.

The next concrete Perpetual Fragility step is to map this payload's coordinate
producer, bitmap deposition, viewport controls and actual scheduling. A later
original-PRG native run could compare the full predicted output at the natural
post-SFX `$080D` entry, with the entering stack/source-copy state recorded.
Neither the author-described WIZ behavior nor snowflake coordinates, complete
pixels or FPS follow merely from the successful format decode. Aloft's
motion-to-call-list generator and named-scene binding remain separate work.
