#!/usr/bin/env python3
"""Build the runnable examples and retain logs, artifacts, and a JSON receipt."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time


ROOT = Path(__file__).resolve().parents[1]
ROOT_TARGETS = {
    "cube": "vector-cube",
    "filled": "filled-cube",
    "icosahedron": "icosahedron",
    "interlaced": "icosahedron-interlaced",
    "dither": "icosahedron-dither",
    "tonal": "icosahedron-tonal",
    "gouraud": "icosahedron-gouraud",
    "fast": "icosahedron-fast",
    "glenz": "glenz",
    "painted": "painted-cube",
    "pong": "pong-cube",
    "raster": "hello-raster",
}
COMPANION_SUFFIXES = {".d64", ".d81", ".g64", ".crt"}


@dataclass(frozen=True)
class Target:
    name: str
    folder: Path
    arguments: tuple[str, ...] = ()
    expected_artifact: Path | None = None

    @property
    def required_artifact(self) -> Path:
        return self.expected_artifact or self.folder / "build" / "example.prg"

    def artifacts(self) -> list[Path]:
        required = self.required_artifact
        artifacts = [required] if required.is_file() else []
        if self.expected_artifact is not None:
            return artifacts
        return sorted(artifacts + [
            path
            for path in (self.folder / "build").glob("*")
            if path.is_file() and path.suffix.lower() in COMPANION_SUFFIXES
        ])


def discover_targets() -> list[Target]:
    targets = [
        Target(f"root:{name}", ROOT, (name,), ROOT / "build" / f"{output}.prg")
        for name, output in ROOT_TARGETS.items()
    ]
    sprite_folder = ROOT / "experiments" / "sprite-ball"
    targets.extend(
        Target(
            f"sprite-ball:{variant}",
            sprite_folder,
            (variant,),
            sprite_folder / "build" / variant / "sprite-ball.prg",
        )
        for variant in ("hexagon", "baseline", "golden")
    )
    for script in sorted((ROOT / "experiments").glob("*/build.sh")):
        if script.parent.name != "sprite-ball":
            targets.append(Target(f"experiment:{script.parent.name}", script.parent))
    return targets


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def write_receipt(folder: Path, receipt: dict) -> None:
    temporary = folder / "receipt.json.tmp"
    temporary.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    temporary.replace(folder / "receipt.json")


def build_target(target: Target, receipt_folder: Path) -> dict:
    slug = target.name.replace(":", "--")
    log_path = receipt_folder / f"{slug}.log"
    command = ["sh", str(target.folder / "build.sh"), *target.arguments]
    previous_outputs = {
        path: (path.stat().st_mtime_ns, path.stat().st_size)
        for path in target.artifacts()
    }
    started = time.monotonic()
    result = {
        "target": target.name,
        "command": command,
        "cwd": str(target.folder),
        "started_at": utc_now(),
        "log": log_path.name,
        "artifacts": [],
    }
    print(f"Building {target.name}", flush=True)
    with log_path.open("w", encoding="utf-8") as log:
        try:
            completed = subprocess.run(
                command, cwd=target.folder, stdout=log, stderr=subprocess.STDOUT, check=False
            )
            result["exit_code"] = completed.returncode
            result["success"] = completed.returncode == 0
            assembler_output = log_path.read_text(encoding="utf-8", errors="replace")
            if re.search(r"ERROR IN ASSERTION|\b[1-9][0-9]* failed\b", assembler_output):
                result["success"] = False
                result["error"] = "Assembler reported a failed assertion."
            if result["success"]:
                artifacts = [
                    path for path in target.artifacts()
                    if previous_outputs.get(path)
                    != (path.stat().st_mtime_ns, path.stat().st_size)
                ]
                if target.required_artifact not in artifacts:
                    result["success"] = False
                    result["error"] = (
                        "Build returned zero but produced no fresh required runnable image: "
                        f"{target.required_artifact.name}."
                    )
                    artifacts = []
                for source in artifacts:
                    relative_source = source.relative_to(target.folder)
                    destination = receipt_folder / "artifacts" / slug / relative_source
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, destination)
                    result["artifacts"].append(
                        {
                            "source": str(source.relative_to(ROOT)),
                            "copy": str(destination.relative_to(receipt_folder)),
                            "bytes": destination.stat().st_size,
                            "sha256": hashlib.sha256(destination.read_bytes()).hexdigest(),
                        }
                    )
        except OSError as error:
            result["success"] = False
            result["error"] = str(error)
            log.write(f"\nBuild runner error: {error}\n")
    result["finished_at"] = utc_now()
    result["duration_seconds"] = round(time.monotonic() - started, 3)
    print(f"{'PASS' if result['success'] else 'FAIL'} {target.name}: {log_path}", flush=True)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="*", help="Target IDs from --list; omit to build all.")
    parser.add_argument("--list", action="store_true", help="List discovered targets without building.")
    arguments = parser.parse_args()
    targets = {target.name: target for target in discover_targets()}
    unknown = sorted(set(arguments.targets) - targets.keys())
    if unknown:
        parser.error(f"Unknown targets: {', '.join(unknown)}. Use --list.")
    selected = list(dict.fromkeys(arguments.targets)) if arguments.targets else list(targets)
    if arguments.list:
        for name in selected:
            print(name)
        return 0

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S.%fZ")
    receipt_folder = ROOT / "build" / "examples" / timestamp
    receipt_folder.mkdir(parents=True)
    receipt = {
        "version": 1,
        "root": str(ROOT),
        "started_at": utc_now(),
        "selected_targets": selected,
        "success": False,
        "results": [],
    }
    write_receipt(receipt_folder, receipt)
    try:
        for name in selected:
            receipt["results"].append(build_target(targets[name], receipt_folder))
            write_receipt(receipt_folder, receipt)
    except KeyboardInterrupt:
        receipt["interrupted"] = True
        return 130
    finally:
        receipt["finished_at"] = utc_now()
        receipt["success"] = (
            len(receipt["results"]) == len(selected)
            and all(result["success"] for result in receipt["results"])
        )
        write_receipt(receipt_folder, receipt)
        print(f"Receipt: {receipt_folder / 'receipt.json'}", flush=True)
    return 0 if receipt["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
