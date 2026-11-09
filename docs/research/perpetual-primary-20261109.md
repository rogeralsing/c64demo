# Perpetual Fragility: primary explanation and exact author layout data

The [author's Perpetual Fragility article](https://www.linusakesson.net/scene/perpetual-fragility/index.php)
provides a detailed implementation explanation and embedded sprite-layout data.
This pass retains its current bytes, indexes eleven sections and extracts that
layout. It finds **no explicit source-code or README download** among the
article's links. That bounded negative does not imply that private or otherwise
published source does not exist.

The [accepted primary receipt](../../build/research/perpetual-20261109/primary-analysis/accepted-01/primary-proof.json)
is 2,547 bytes, SHA-256
`479a558cda23edfbbfa529fb71e95f1e8e091bdf8f82e3b037a6426c43f01e65`.
Its inputs are the actual HTTP bodies, never expected renderer output.

## Explanation kept separate from execution

Åkesson describes persistent bitmap deposition from an animation-order
coordinate list, rather than redrawing every snowflake every frame. The
viewport advances through spatially arranged phases. He explains a repeated
40-cell colour stencil, suppression of later badlines and timed separation of
matrix data from sprite pointers. The timed routine is generated at compile
time. His 1,496-frame path length is distinct from the deliberately misleading
1,156-dot scroll-text claim.

The [claim index](../../build/research/perpetual-20261109/primary-analysis/accepted-01/author-claims.json)
records exact UTF-8 byte ranges, fragment hashes and text for each article
section, followed by explicit requirements for binding it to released code.
The requirements include locating the real coordinate consumer and bitmap
updates, establishing matrix-fetch/cache lifetime and proving the bank-switch
schedule. Author prose alone satisfies none of those runtime checks.

## The embedded layout is actual source data

The article's single preformatted block contains **149 sequential
hexadecimal-labelled rows, `$1F..$B3`, each 207 characters wide**. The author
uses dashes for normal-width strips and equals signs for X-expanded strips;
the literal `*` and `#` artwork labels are preserved.

The [layout export](../../build/research/perpetual-20261109/primary-analysis/accepted-01/author-tree-layout.json)
records every row and each marked column. Its 30,843 cells consist of 15,718
spaces, 4,041 dashes, 5,917 equals signs, 579 stars and 4,588 hashes. The
[plain-text export](../../build/research/perpetual-20261109/primary-analysis/accepted-01/author-tree-ascii.txt)
preserves the original preformatted data.

These are coordinates in an authored diagram. No origin mapping to actual
VIC X/Y registers, sprite-memory format, palette, DMA interval or pixel field
is assumed. Such a mapping needs an independent comparison with the released
sprite data and its consumers. Counting diagram columns does not prove a
hardware sprite count or simultaneous display width.

## Links, current retrieval and repeatable checks

Six requests returned HTTP 200: the 71,182-byte article and five explanatory
PNGs, totaling **272,938 body bytes**. Requested/final URLs, status, headers,
byte counts and SHA-256 digests are retained in the
[HTTP manifest](../../build/research/perpetual-20261109/primary-analysis/acquisition-01/http-retention.json).
TLS verification was not bypassed. The PNG parser checks every chunk CRC and
their actual dimensions: four 600×350 diagrams and one 1800×1050 diagram.

The [link inventory](../../build/research/perpetual-20261109/primary-analysis/accepted-01/article-link-inventory.json)
separates author content from navigation and comments. The file downloads are
the demo PRG, two music PRGs and an MP3. The current three comment headers
contain no authenticated `lft` author reply; their technical opinions are not
used as authority. The embedded video is recorded as a link, without fetching
video, audio or captions. An exploratory exact-heading lookup failed because
the discussion heading includes an HTML attribute; its diagnostic is retained,
and parsing uses the actual markup.

The five PNGs illustrate phase placement and the nonrectangular bitmap address
layout. They are not treated as the original snowflake coordinate table. This
pass neither repeats the earlier 595-mod1024/odd-step checks nor adds a
synthetic WIZ fixture. The original packer reconstruction remains in the
[preceding investigation](aloft-motion-primary-20261109.md).

Run the [passive producer](../../research/perpetual-20261109/primary.py) into a
fresh directory:

```sh
rtk proxy python3 -B research/perpetual-20261109/primary.py --output build/research/perpetual-20261109/primary-analysis/new-replay
```

The [self replay](../../build/research/perpetual-20261109/primary-analysis/self-replay-check.json)
matches all **8 files / 403,982 bytes** exactly. It performs no network requests,
CPU interpretation, native execution, builds or downloaded-host execution.
Primary extraction is not a complete display, timing or frame-rate proof.
