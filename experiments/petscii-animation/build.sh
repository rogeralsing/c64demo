#!/bin/sh
set -eu
cd "$(dirname "$0")"
python3 prepare.py
exec sh ../build-one.sh "$PWD" "$@"
