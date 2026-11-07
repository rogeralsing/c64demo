# VICE 3.10 text-monitor store timestamp semantics

Read [the findings](../../docs/research/vice-trace-timing.md).

```sh
rtk proxy python3 research/vice-trace-timing/inspect_source.py
```

Standard library only. The script reads the already archived official
`build/research/quondam/hardware-source/vice-3.10.tar.gz`, checks its SHA-256,
extracts relevant source only into ignored `build/research/vice-trace-timing/`,
and records source hashes and line references.

The example clock pair comes from the parent native investigation and is
explicitly labeled as supplied evidence. The script performs arithmetic on
that pair; it runs no emulator, CPU, compiler or native timing experiment.

The exact source path is x64sc's `c64cpusc.c` → `mainc64cpu.c` →
`6510dtvcore.c`. Normal store traces use the instruction-owner PC with a later
boundary's clock/state. RMW traces show one or two queued stores depending on
the live `dummy` setting. The complete interpretation and interrupt/stopwatch
qualifications are in the analysis.
