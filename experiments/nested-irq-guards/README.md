# Per-call-site nested IRQ guards

An original demonstration of the separate 2026 guard technique documented
in the [scheduling source note](../../docs/research/february-2026.md).
It complements [macro-scheduling](../macro-scheduling/README.md), whose
continuations and cooperative waits have a different execution contract.
No published example code, font or artwork is copied.

```sh
sh build.sh
sh run.sh
python3 verify.py
```

Seven raster IRQ slots continue each PAL field. Each slot runs a short
counter job, schedules the next IRQ, and selects one of two call sites.
Each site has its own self-modified `running` immediate. A busy site skips
its new call. An idle site marks its flag, enables IRQ nesting and calls
the same long worker routine. Completion clears only that site's flag.

The two sites can therefore overlap in the same routine, while each site
blocks its own reentry. Every IRQ preserves A/X/Y on its actual stack frame,
so the long worker's loop registers resume correctly. Shared counters have
short interrupt-disabled updates; the long workload itself remains
interruptible. This example does not make arbitrary shared routine state
safe or add more CPU time to a field.

An original status font shows starts, completions, skipped calls, live depth
and independent fast jobs. The status snapshot updates before its text rows
once per field; the short counter job runs on all seven IRQs.

The [native proof](build/verification/verification.json) audits 100 consecutive
PAL intervals and 796 actual start/skip/completion events against a separate
per-site stack model. Observed starts are 49/48, completions 48/48, and skips
351/252. One call remains active at the retained final boundary, consistent
with the event prefix and live flag; VICE then exits 0.

Both sites enter the same routine simultaneously, reaching depth two.
Every skipped entry belongs to its already active site. All 700 independent
fast jobs execute. Actual guards, counters and depth match the event model
at every field boundary. All 6,400,000 viewport pixels match the independently
predicted hexadecimal status and font composition. Stack bounds and complete
PAL field intervals also pass.

[Preview](build/verification/nested-irq-guards.gif), full screenshots and
event traces remain beside the receipt. The preview slows each field to
60 ms. Author-reported byte/cycle overhead figures and physical-hardware
behavior are not claimed by this teaching implementation.
