# Shared row-event jumps

Build a 128-byte next-event table from the shared row UV contributions once
per pose. Each covered column follows that table, clipped to its exact entry
and exit, samples only changed texels and emits nonzero XOR color deltas.

This selected 112-byte implementation uses 13,750 texture lookups per loop
and reaches 8.01 complete updates/s in PAL VICE. See the
[comparison and reproduction commands](../../README.md).
