# Primary follow-up: animation stored spatially

Linus Åkesson's [Perpetual Fragility explanation](https://linusakesson.net/scene/perpetual-fragility/index.php)
describes overlapping animation phases in one bitmap, revealed through AGSP
offset changes. He calls this WIZ. Snow positions follow a prepared path;
the scene does not require redrawing every visible flake. His color stencil
uses one forty-byte matrix row, held through badline inhibition. A compile-time
scheduler places timed snippets around sprite stalls. These are author
statements about his own demo, separate from the Aloft reconstruction.

The new [finite checker](../../research/aloft-pixels-20261109/primary_followup.py)
verifies the arithmetic consequence of his declared increment 595 modulo 1024:
all 1,024 offsets occur exactly once. All 512 odd increments have the same
period. It also checks 1,024 coarse viewports using
`(offset + 40*y_char + x_char) mod1024`: each 320×200 view addresses 1,000
distinct cells in the 1,024-cell ring. This explains the skewed wrapping;
it does not reconstruct the author's snowflake coordinates.

The [retained acquisition](../../build/research/aloft-pixels-20261109/reading-analysis/acquisition-01/http-retention.json)
contains three HTTP 200 bodies, 212,666 bytes, with no certificate bypass.
The 9,469-byte PRG linked by the author has BASIC `SYS 2061`; its packed payload was
not decoded or executed. Anonymous comments are excluded.

The [receipt](../../build/research/aloft-pixels-20261109/reading-analysis/accepted-01/primary-followup-proof.json)
and [self replay](../../build/research/aloft-pixels-20261109/reading-analysis/self-replay-check.json)
match all four files / 175,551 bytes. The independent
[peer review/replay](../../build/research/aloft-pixels-20261109/reading-analysis/peer-replay-check.json)
also matches exactly. Actual PRG behavior, pixels and FPS remain
future work. [Earlier Finite Bobs reading](primary-2026-notes.md) covers a
different AGSP application; it is not new Aloft source evidence.
