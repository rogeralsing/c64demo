# Reproduce Trident's scheduling example

Run from the repository root:

```sh
rtk proxy python3 research/macro-scheduling/acquire.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/macro-scheduling/validate.py
```

Acquisition pins author repository commit
`80d1027742815e55cda13a80cb4826744dd75c83`, checks Git blob identities, and keeps
unchanged third-party source and slides under ignored
`build/research/macro-scheduling/`. `slides-text.json` follows the presentation's
slide-order relationships. It extracts XML paragraphs without rendering slides
or inferring a spoken transcript.

Validation assembles the original standalone source with Kick Assembler 5.25.
Set `JAVA` or `KICKASS_JAR` to override their local paths. The existing research
Python environment supplies py65 1.2.0. Bounded original CPU execution checks
1,001 complete scene-sequence calls and 16 manually injected IRQ entries.

`proof.json` records assembly identities, independent all-RAM counter checks,
literal I/O events, continuation targets and nominal cycle counts. It is not a
native VIC, DMA, IRQ-latency or physical bus result. The standalone source is
not replaced by a slide excerpt or identified as a released demo's code.

See [the investigation](../../docs/research/macro-scheduling.md) for contracts,
limits and possible transfers. No emulator is started by these scripts.
