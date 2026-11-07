# Recovering The Lab's included note

The release and findings are documented in [the research note](../../docs/research/the-lab.md).
The original downloaded extras disk and bootstrap remain under ignored
`build/research/the-lab/`; their exact hashes are recorded there.

The owned PAL VICE session `note-live-01/` ran the original note bootstrap with
the original extras disk attached. It stopped at `$080D`, then executed the
reader and saved raw 64K RAM after two and four million instructions. The later
native screenshot displays the note's first page. No PC changes or disk-input
mocks were used.

Export the complete readable note and verify that its bytes stayed unchanged:

```sh
rtk proxy python3 research/the-lab/read_note.py \
  build/research/the-lab/note-live-01/ram-after-4m.bin \
  --compare build/research/the-lab/note-live-01/ram-after-2m.bin \
  --output build/research/the-lab/note-live-01/decoded
```

The extractor requires the exact original dispatch bytes at `$0884`, handles
the four-byte styling commands actually present, and stops at the reader's
`$FE` terminator. It produces 49 pages from `$6800..$B05E`, a raw region copy,
and a hash/command receipt. It removes inverse styling for text readability
while retaining unknown custom-font symbols as hexadecimal markers. It does
not decode the packed disk directly or reproduce the note's graphical layout.

The reader's VIC mode is not evidence of any vector stage's VIC mode. The
included text provides author statements, which still need to be matched to
the exact executing effect before attributing a binary algorithm to a user's
screenshot.
