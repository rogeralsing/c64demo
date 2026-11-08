#!/usr/bin/env python3
"""Verify that texture color transitions are consumed by the real XOR fill."""
from pathlib import Path
import runpy
import sys

HERE = Path(__file__).resolve().parent
sys.argv = [sys.argv[0], "--folder", str(HERE), "--texture-markers", *sys.argv[1:]]
runpy.run_path(str(HERE.parent / "xor-hybrid/verify.py"), run_name="__main__")
