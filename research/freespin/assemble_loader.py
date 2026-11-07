#!/usr/bin/env python3
"""Assemble the pinned published loader with the release-derived frame constant."""

import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


REPOSITORY = Path(__file__).resolve().parents[2]
ROOT = REPOSITORY / "build/research/freespin"


def digest(data):
    return hashlib.sha256(data).hexdigest()


def main():
    source = ROOT / "loader-published.asm"
    assert digest(source.read_bytes()) == "df345e8812d48209daf33956d92e7e1cf1e590023c31d2280c3c117ca9465ec0"
    java = os.environ.get("JAVA") or ("/opt/homebrew/opt/openjdk/bin/java" if Path("/opt/homebrew/opt/openjdk/bin/java").exists() else shutil.which("java"))
    jar = Path(os.environ.get("KICKASS_JAR", Path.home() / ".local/share/c64-tools/KickAssembler/KickAss.jar"))
    if not java or not jar.exists():
        raise SystemExit("Requires Java and Kick Assembler; set JAVA and KICKASS_JAR if not installed at the existing project locations.")
    wrapper = ROOT / "loader-wrapper.asm"
    wrapper.write_text('.const FRAME_CYCLES = 20000\n.import source "loader-published.asm"\n')
    target = ROOT / "loader-published-20000.prg"
    command = [java, "-jar", str(jar), str(wrapper), "-o", str(target), "-symbolfile"]
    subprocess.run(command, check=True, cwd=ROOT)
    blob = target.read_bytes()
    assert blob[:2] == bytes((2, 7)) and len(blob) == 246
    receipt = {"source_sha256": digest(source.read_bytes()), "frame_cycles": 20000,
               "kickass_jar_sha256": digest(jar.read_bytes()), "command": command,
               "prg_sha256": digest(blob), "executable_bytes": len(blob) - 2,
               "range_end_exclusive": [0x702, 0x7F6],
               "scope": "Unmodified published loader source; only its missing FRAME_CYCLES parameter supplied from release bytes"}
    (ROOT / "assembly.json").write_text(json.dumps(receipt, indent=2) + "\n")


if __name__ == "__main__":
    main()
