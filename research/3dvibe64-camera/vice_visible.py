#!/usr/bin/env python3
"""Open the owned VICE preview visibly; leave all emulation flags unchanged."""
import os
import sys

VICE = '/opt/homebrew/bin/x64sc'
arguments = [value for value in sys.argv[1:] if value != '-minimized']
os.execv(VICE, [VICE, *arguments])
