# Handoff artifacts and exact restart inputs

Recorded 7 November 2026. Research is paused. Read [CHECKPOINT](CHECKPOINT.md)
for all findings and [FOLLOW_UP](FOLLOW_UP.md) for the continuation prompt.
This index pins the newest batch; older investigations retain their own
detailed notes and proof chains in the [reading map](README.md).

## Preserve the evidence

The tracked [machine-readable inventory](HANDOFF-ARTIFACTS.json) contains
**203 unique artifact/helper identities** from the four final research
receipts and exact continuation inputs. Each entry records repository-relative
path, byte count and SHA-256. These are existing evidence hashes, not proof
that a broader effect or runtime question has been completed.

**Keep `/Users/rogerjohansson/git/asynkron/c64demo/build/research/`.** Original
downloads, acquisition indexes, RAM, snapshots, screenshots and large proof
outputs are ignored by Git. They are not included in this commit. A fresh
checkout needs those retained inputs to reproduce the checks and resume the
exact native state; the tracked scripts are not substitutes for that data.

## Final research receipts

| Receipt | Bytes | SHA-256 |
|---|---:|---|
| `build/research/anomaly/upper-analysis/upper-proof.json` | 1,142,094 | `67ac3c820f62f2f8bdfa1342a8790459c4ce673145c1080393f471a896a4ff3f` |
| `build/research/anomaly/native-upper-analysis/native-upper-evidence.json` | 282,689 | `53274dec47bf09e196878d973ec6c5f10782497d61ff36cf50f97db31bc108fd` |
| `build/research/relax24/resource-recovery-01/resource-proof.json` | 6,296 | `f56b8b0b650d104433c46cea100dd3d08a82e43175a76b43cd7eb10b87a8ca7b` |
| `build/research/frontier-2026/primary-notes/primary-notes-proof.json` | 18,983 | `5ec288fd0dfc3fe0913318ce64eb5032c477592afadd214a467bc6064c0cc0aa` |

The receipts bind their producers, original inputs and outputs. Their claims are:

- **Anomaly upper model:** 28 jobs, all declared RAM/state domains, a direct
  4,160-byte bitmap plus 520-byte attribute oracle, and completed first publication.
- **Anomaly native audit:** 67 RAM/VSF pairs, three PNGs, exact parent restore,
  28 first-update trace entries and three 96-store fields. The rejected uniform
  63-clock timestamp hypothesis is retained; physical bus phases remain unproved.
- **Relax24 resource:** 3,569 compressed bytes yield 9,216 bytes at AC00..CFFF
  in two functional models, with all 7,501 match reads known. No CPU continuation
  through the dead-value unknown read or initialized reader/menu is claimed.
- **Primary-source lane:** eight immutable Git blobs, 14,336 packed artwork
  bytes, 28,672 restored bytes and 46,080 bob-mask cases. Negative controls and
  the five empty Rodents-caption responses remain explicit. No native claim.

## Recheck without rerunning native execution

Run from `/Users/rogerjohansson/git/asynkron/c64demo`:

```sh
rtk proxy python3 research/anomaly/inspect_upper.py
rtk proxy python3 research/anomaly/native_upper.py
rtk proxy python3 research/relax24/decode_resources.py
rtk proxy python3 research/frontier-2026/primary_notes.py
```

These read saved inputs and regenerate bounded receipts. They do not launch
VICE or repeat the multi-million-instruction Relax packing proofs. The current
producer/receipt pairs have already passed. Before revising a producer, archive
it and its old receipt; do not overwrite a frozen proof to erase a failed gate.

Verify every indexed file without rewriting anything:

```sh
rtk proxy python3 - <<'PY'
import hashlib, json
from pathlib import Path
manifest = json.loads(Path('docs/research/HANDOFF-ARTIFACTS.json').read_text())
for item in manifest['artifacts']:
    data = Path(item['path']).read_bytes()
    assert len(data) == item['bytes'], item['path']
    assert hashlib.sha256(data).hexdigest() == item['sha256'], item['path']
print('All indexed artifacts match.')
PY
```

## Exact next inputs

- **Anomaly:** `build/research/anomaly/native-04/field-04-pre.vsf`, SHA-256
  `70fbfcde49a6c1b9a1b18ad538d7e0684cc1c7fdaf2ec6a42b40ad734bbf1b5b`,
  PC B400, clock 167006965, beam 152/13. Session is owner-closed. Restore
  with the same original side-one disk and verify full state identity before
  further execution. The next target is coherent VIC scanout and broader timing.
- **Relax24:** compare the 496-byte uploaded drive block from inner RAM
  $25A8..$2797, installed at drive $0500..$06EF, with recovered $AC00..$ACF7.
  Bind request `02 30 30` before claiming a transfer. Retained `00.prg` is
  13,822 bytes, loads at $2000 and ends with word $080C; this is compatibility
  with the trailer/JMP contract, not executed-reader or transfer proof.
- **Primary sources:** bind the finite-bob source/generated plotters to the
  original No Bounds part before investigating alleged Aloft reuse. For
  Rodents, obtain the author transcript or actual released code. Keep Hat/Aloft
  algorithms unresolved until their own artifacts explain them.

Sprite-ball was committed separately as `3da9ae1` while this research handoff
was being prepared. Its README owns its fixed shading/gap-order design and
remaining limits.
Default hexagon PRG SHA-256 is
`9771ac67a648d4e66426c4b48373e9c19dc3db9fe0ed98f5dfbd824d30825744`;
its receipt is `4ceaa34b0cbd1d88b426df59afcfe971f425f83e6f12c2bdca49f47f5422594b`.
The receipt covers 257 presentations, 129,528 sprite bytes, 11,316 edge
samples and maximum 46,092 of 58,968 clocks. Baseline/golden native receipts
remain historical; they do not validate their newly shared shading code.
