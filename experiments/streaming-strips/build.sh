#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
python3 build.py prepare
sh ../build-one.sh "$PWD" "$@"
python3 build.py disk
