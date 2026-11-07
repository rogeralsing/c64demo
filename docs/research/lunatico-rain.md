# Lunatico rain: original written explanation recovered

The rain mechanism now has direct written author evidence. The original
**Lunatico** disk note explains that its ripples combine **WIZ with character
graphics**: apparent ripple animation can advance at 50 fps while the actual
bumpmapping runs more slowly. This resolves part of the earlier evidence gap;
it does not recover the full bumpmapper implementation.

The new [Rain Effect Explained page](https://www.linusakesson.net/scene/lunatico/rain.php),
posted **6 November 2026**, identifies the effect as part of the **2016** demo
and embeds [video `F2TkzDaa8A4`](https://www.youtube.com/watch?v=F2TkzDaa8A4).
The page still supplies no algorithmic prose. The substantive text recovered
here is from the original release, not a transcript of that new video.

## What the original note says

The [author's release page](https://www.linusakesson.net/scene/lunatico/index.php)
explicitly points readers to the technical note on Side 1. The note's rain
section, decoded lines **384–397**, attributes inspiration to the bumpmapper
in **Error 23 by Resource & The Dreams**. Absolute-address speedcode normally
fixes the sampled bump surface in place; this version builds the surface
according to WIZ, allowing fast apparent ripple animation while the bumpmapper
updates more slowly.

The note defines **WIZ: Wraparound Isometric Zoetropes** in its own preceding
section. Seamless bitmap tiles exploit the VIC's nonrectangular memory
wraparound. Arranged animation phases are sampled through AGSP viewpoint
motion, so moving the viewpoint advances many neighboring small animations at
once. Overlapping those elements creates the impression of a large animated
surface. These are the author's explanations; no AGSP or rain raster routine
was executed here.

The rate distinction matters: **50 fps describes the resulting ripple
animation**, not a measured 50 Hz bumpmap recalculation. The note does not
provide a height equation, derivative/normal calculation, lighting lookup
layout, precise bumpmapper rate or pixel dimensions for this part. Those remain
open. Its MISC sprite-crunch section is separate and supplies no substitute
rain algorithm.

## How the written source was recovered

`research/lunatico-rain/read_note.py` reuses the previously archived
[official ZIP](https://hd0.linusakesson.net/files/lft-lunatico.zip), verifies its
identity, extracts Side 1's conventional DOS chain for `NOTE & VSP TOOL`, and
uses only the tool's original RAM text-line decoder.

| Original artifact | Bytes | SHA-256 |
|---|---:|---|
| Official Lunatico ZIP | 272,533 | `1e22a02eeef77d98a8c348b03cbb808b489b3cf842d14db25dbf72f79eb9e6c0` |
| `NOTE & VSP TOOL` PRG | 23,064 | `66a74aa174c936c3c53366f9e620c0b6edddfd04c45472f18551affca0ce9f60` |

The note is not stored as readable ASCII. Startup sets a text-record pointer to
`$1A80` and calls the line worker at `$1928`. Each record carries backward and
forward byte lengths; the compressed payload starts two bytes after that
record's address. The worker reads a bitstream and tables, writes character
codes, and fills the remaining columns with spaces. It skips the unused eighth
byte of each aligned eight-byte data group.

The script traverses the record chain, checks every backward link and calls the
original **`$1928..$19C4`** routine separately for each line. Inputs are the
original compressed-record pointer and an explicit output buffer at `$F000`.
Every read must come from original loaded bytes or memory already written by
that call. Any access in `$D000..$DFFF` is forbidden.

The existing **py65 1.2.0** environment executes **493 lines** in **756,407 CPU
instructions**, terminating at record `$4493`. All calls return within their
instruction bound. The CPU extension is the NMOS `$80` immediate NOP used by
the original worker; the code bytes are not patched. Its normal
self-modification of the source pointer is retained.

Original font bytes at `$0F3C..$113B` are rendered into an analysis glyph sheet
and visually checked: IDs 0–9 are digits, 10–35 letters, and punctuation is
mapped from the actual glyphs. The textual export normalizes letter case to
lowercase; full screen-code bytes, including their color bits, remain in the
receipt. No unmapped glyphs remain in these 493 lines. This is a decoded author
note, rather than text guessed from the effect's name or video metadata.

The normalized text SHA-256 is
`9225c060e6454b762e3c81586f730978664f4c5d94a32724844addc7b02a5296`.
`note-receipt.json` is SHA-256
`fc9379046f46ff55ccb243d56e10b0dfd4e9a4e7be0ff7d6b4148f0fd541f020`.
The complete decoded text, original files, glyph sheet and receipts are ignored
artifacts under `build/research/lunatico-rain/`; the tracked files contain our
analysis and reproduction scripts.

## What happened to the new video's captions

The public YouTube page was inspected on **7 November 2026**. It identifies
`lftkryo` as author, a duration of **1,263 seconds / 21:03**, and an English
automatic-caption track. Fresh metadata confirms that a track is advertised;
it does not supply caption text.

The actual attempts were:

| Route | Observed result |
|---|---|
| Earlier saved direct caption attempt | HTTP response body had zero bytes |
| Fresh browser's own advertised timedtext request | HTTP 200, `Content-Length: 0` |
| Same-origin fetch of the fresh track with `fmt=json3` | HTTP 200, zero text bytes |
| Normal **Show transcript** UI | HTTP 400, `FAILED_PRECONDITION`, zero rendered segments |
| Clean page reload and normal transcript UI again | Same HTTP 400 precondition failure, zero rendered segments |

The metadata and sanitized observations are preserved in
`browser-observations.json`. These outcomes mean the attempted routes supplied
no transcript here; they do **not** establish that captions are unavailable
for every viewer or environment. No remote video or audio was downloaded to
work around the problem, and no explanation was inferred from search tags.

## Reproduction and remaining work

From the repository root:

```sh
rtk proxy python3 research/lunatico-rain/acquire.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/lunatico-rain/read_note.py
```

The first script archives the two primary author pages, pins the reused ZIP and
preserves the earlier caption attempt's identity. The second extracts the note,
runs its bounded decoder and emits text, glyph and per-line receipts. Neither
starts the VSP tool, its music, the demo loader, the rain part or a native
emulator.

The next concrete target is the original rain part: identify its packed
payload, map the fixed-address speedcode and WIZ data representation, then
compare update scheduling with native output. An accessible transcript could
also provide the new video's more detailed explanation. The original note
supports the representation and rate distinction above; it does not complete
those remaining checks.
