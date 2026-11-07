# Lunatico rain primary-source recovery

Read [the analysis](../../docs/research/lunatico-rain.md). The new video still
yielded no caption text through the attempted public routes. The original
release's technical note supplied concrete written rain/WIZ evidence instead.

```sh
rtk proxy python3 research/lunatico-rain/acquire.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/lunatico-rain/read_note.py
```

`acquire.py` requires only the Python standard library and the already archived
official ZIP at `build/research/frontier-followup/lunatico.zip`.
`read_note.py` uses the existing py65 1.2.0 environment; it installs nothing.

The note decoder's original `$1928..$19C4` instructions execute in isolation
with a supplied source/output pointer. Unknown reads and all hardware addresses
are forbidden. Only NMOS `$80` immediate NOP semantics are added to py65.

The output records all 493 source-record addresses, byte lengths, screen codes,
normalized text and CPU instruction counts. The original font is rendered as
a glyph sheet to verify the alphabet and punctuation mapping. Raw bytes,
complete third-party prose, derived images and receipts remain ignored under
`build/research/lunatico-rain/`.

`browser-observations.json` is a sanitized manual receipt from the public
browser inspection: a fresh timedtext request returned zero bytes and the
normal transcript UI returned HTTP 400 `FAILED_PRECONDITION`, including after
reload. Reproduce through the ordinary video's **Show transcript** control;
signed caption URLs are ephemeral. No cookies, request credentials or media
files are archived.
