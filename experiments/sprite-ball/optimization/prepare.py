#!/usr/bin/env python3
"""Prepare isolated snapshots for the sprite-ball delta-rendering experiments."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    here = Path(__file__).resolve().parent
    experiment = here.parent
    repository = experiment.parents[1]
    output = args.output.resolve()
    if output.exists():
        raise SystemExit(f"Refusing to overwrite an existing experiment: {output}")
    output.mkdir(parents=True)
    manifest = {}
    for name in ("baseline", "shape-cache"):
        snapshot = output / name
        target = snapshot / "experiments/sprite-ball"
        shutil.copytree(experiment, target, ignore=shutil.ignore_patterns(
            "build", "optimization", "__pycache__"))
        shutil.copy2(repository / "verify.py", snapshot / "verify.py")
        shutil.copytree(repository / "palettes", snapshot / "palettes")
        if name == "baseline":
            for source in target.rglob("*"):
                if source.is_file():
                    manifest[str(source.relative_to(target))] = hashlib.sha256(source.read_bytes()).hexdigest()
        patch = "capture-trace.patch" if name == "baseline" else "shape-cache.patch"
        subprocess.run(["rtk", "git", "apply", str(here / patch)], cwd=target, check=True)
    for directory, filename in (("baseline", "profile_reference.py"),
                                ("shape-cache", "benchmark_shape_cache.py"),
                                ("changed-bytes", "benchmark_changed_bytes.py"),
                                ("boundary-delta", "boundary_delta.py")):
        destination = output / directory
        destination.mkdir(exist_ok=True)
        shutil.copy2(here / filename, destination / filename)
    (output / "source-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(output)


if __name__ == "__main__":
    main()
