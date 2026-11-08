#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
"${PYTHON:-python3}" prepare.py
exec sh ../build-one.sh "$PWD" "$@"
