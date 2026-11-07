# Boo! binary research

See [the binary research note](../../docs/research/boo-binary.md) for evidence,
counts, source hashes and scope. These scripts require Python plus py65 1.2.0.
The ignored Tower research virtual environment can be reused:

```sh
rtk proxy build/research/tower-power/cpu-venv/bin/python research/boo/unpack_6502.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/boo/inspect_binary.py
```

`unpack_6502.py` requires the exact released `build/research/boo/boo.prg`, executes
its original bootstrap and RAM postprocessor, then stops before demo startup.
It adds the stable NMOS NOP/LAX instructions needed by those bytes and stops on
hardware-visible I/O. A non-completed run exits nonzero.

`inspect_binary.py` reconstructs the drive payload statically, executes isolated
original RAM-only generator/selector routines, and compares them with independent
rank/step contracts. It adds the selector's NMOS RLA instruction. It imports the
existing Tower disassembler and BRR scene generator as host utilities.

All author binaries, source downloads, RAM images, disassemblies and receipts
stay under ignored `build/research/boo/static/`. There is no VICE launch, IEC
mock, full drive execution, display rendering or native performance measurement.
