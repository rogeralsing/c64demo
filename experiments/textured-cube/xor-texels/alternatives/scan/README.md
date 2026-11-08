# Per-pixel transition scan

For every covered logical column, sample each texture pixel and compare it
with the preceding color. Emit nonzero XOR deltas at entry, color changes
and exit. The real shared prefix fill paints the image afterward.

This is the compact 54-byte control implementation. It preserves all 29,988
texture lookups per loop and reaches 6.79 complete updates/s in PAL VICE.
See the [comparison and reproduction commands](../../README.md).
