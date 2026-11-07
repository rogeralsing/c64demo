# Relax #24: original magazine archive recovered

The original **Spring 1998 Relax #24** distribution is available from the
[Commodore archive's Relax directory](https://c64.rulez.org/pub/c64/Magazines/Relax/).
The exact [Relax_24_Phuture.zip](https://c64.rulez.org/pub/c64/Magazines/Relax/Relax_24_Phuture.zip)
acquired on 7 November 2026 contains a side-2 D64 and a single-entry side-1
LYNX container. The side-2 directory explicitly says **MAY 13** and
**SPRING 1998**; these are literal directory labels, not an independently
verified publication chronology.

This resolves the original-artifact acquisition gap behind the
[Second Reality contemporary-review lead](second-reality-sources.md).
It does **not yet validate the cached web transcription** against the
original magazine. Clarence's coding review remains reviewer analysis,
separate from explanations by Second Reality's credited coders and from
our checked original-machine behavior.

## Exact container identities

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Original ZIP | 188,038 | `cd0573d52adacd50927facd065ab8a7d51a8b236bd80f2a5ba90ec7e80f9bb21` |
| `REL24_S2.D64` | 174,848 | `5f9e3b02ce0ed6feb8e75e1b7b006ccc803c07f0448555d4f2609f94d5c3f76b` |
| `REL24_S1.LNX` | 31,465 | `85bc680309d41538003c4ed49262b693bfedc4ebafa62edf96d64e3ac747fa46` |
| Extracted side-1 program | 31,211 | `ea9040469d211c87cdfd1aaa2a5eca04685be741d679bc1537cb7cc280810180` |

The side-1 container identifies itself as **STAR LYNX 0.80, JOE/STA**.
Its one 254-byte directory block describes one PRG, 123 blocks with a
last-sector-used count of 224. Following the documented
[LYNX layout](https://ist.uwaterloo.ca/~schepers/formats/LNX.TXT), the exact
member length is `(123−1)×254 + 224−1 = 31,211` bytes. The extraction accounts
for every container byte; no padding or invented bytes are added.

The side-2 inventory follows **21 separate PRG chains**, totaling
**154,245 file bytes**. Every chain has a valid EOF, its sector count agrees
with the directory, and no sector is shared between the extracted files.
Full raw filenames, file-to-disk byte mappings and final-sector counts are
preserved. The directory's PRG type alone does not prove that an article's
first two bytes are a normal load address or that its body is executable.

## Reproduction and remaining work

Run [acquire.py](../../research/relax24/acquire.py) to replay the local
extraction. `--fetch` downloads only the pinned public ZIP, checks its exact
hash and records the request. The script reuses the established DOS-chain
reader and records that reader's identity; it does not execute a CPU,
start VICE or decode the magazine's article format.

The [archive proof](../../build/research/relax24/archive-proof.json) has
`pass: true`, SHA-256
`0c68892c3a73cdeda0854eaa28db205672a9b02ed3f04ce185dbda72ad656fac`.
Original responses, request metadata, original containers and extracted
files stay in the ignored build directory. The acquisition route discovery
also preserves the successful HTTP and HTTPS directory responses and a
CSDb scener-page response. Failed web-tool rendering of the directory or
format document was not treated as proof that the underlying download
route was unavailable.

The [reader inspection](relax24-reader.md) now maps the file-established
wrapper copies and backward bit/LZ structure, while retaining the strict
startup hardware stop. The reader and its articles remain undecoded. Next:
recover the coding review using the original reader's format and compare
the relevant passages with the cached transcription. Filename guesses or
byte-string coincidences do not establish which file contains an article.
No additional Second Reality algorithm, update rate or hardware claim
follows from this acquisition.
