#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3 "$HERE/prepare.py"
exec sh "$HERE/../build-one.sh" "$HERE"
