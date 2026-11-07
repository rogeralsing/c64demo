# Trident ghostbyte article and teaching examples

Read [the analysis](../../docs/research/ghostbyte-shine-through.md) for source
identity, mechanism, register schedule, limits and input/output hashes.

```sh
rtk proxy python3 research/ghostbyte/acquire.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/ghostbyte/validate_examples.py
```

`acquire.py` checks pinned Git blob identities and saves raw third-party files
only under ignored `build/research/ghostbyte/`. `validate_examples.py` requires
the project's existing Java/KickAssembler and py65 1.2.0 environment; it installs
nothing. `JAVA` and `KICKASS_JAR` can override the existing tool locations.

Validation assembles the two unmodified teaching sources, exercises two loops
with explicit synthetic raster reads, records their register writes, and
exhaustively checks a separately stated ideal-compositor constraint. It does
not run VICE, reproduce the complete scroller, or identify the code in Orbit
Untold, The Ghost or Nine release binaries. All generated binary, assembly,
trace and acquisition artifacts remain ignored.
