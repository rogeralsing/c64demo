# A Mind Is Born: source and arithmetic checks

Original work by Linus Åkesson / lft:
https://www.linusakesson.net/scene/a-mind-is-born/index.php .
The author labels it [CC BY-NC-SA 4.0](https://creativecommons.org/licenses/by-nc-sa/4.0/).
This directory contains our analysis programs. Raw author HTML, extracted code,
PRG, complete derived byte listing and receipts remain ignored build artifacts.

Inputs:

- Pinned original `build/research/frontier/a_mind_is_born.prg`, SHA-256
  `7da29c8eed5acc39c5a1d3f0d40f5057c516cb6d2a04a18b15d71e6f8903f1f5`.
- Archived author page `build/research/a-mind-is-born/author.html`. The source
  check parses its eighteen inline preformatted blocks. It does not execute
  downloaded host code. A fresh page can be saved from the author URL; its hash
  is recorded because comments or page metadata may change independently.

From the repository root:

```sh
rtk proxy python3 research/a-mind-is-born/source_bytes.py
rtk proxy build/research/tower-power/cpu-venv/bin/python research/a-mind-is-born/validate_arithmetic.py
```

The second command uses the existing isolated py65 1.2.0 environment. Its small
NMOS instruction additions are explicit, including immediate LAX restricted to
operand zero. Outputs are `source-byte-proof.json`, `payload-annotated.txt` and
`arithmetic-proof.json` under `build/research/a-mind-is-born/`.

These scripts perform no VICE launch, hardware/ROM emulation or native playback.
The music check compares literal register-write instructions, not SID sound.
Visual checks supply all byte-valued timer/envelope fixtures, not a model of
their time evolution or an assertion of visual frame cadence. See the
[research note](../../docs/research/a-mind-is-born.md) for exact coverage and gaps.
