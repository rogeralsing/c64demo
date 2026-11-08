#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
sh ../build-one.sh "$PWD/drive"
exec sh ../build-one.sh "$PWD" "$@"
