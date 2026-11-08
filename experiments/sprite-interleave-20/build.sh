#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
sh ../sprite-interleave/build.sh
exec sh ../build-one.sh "$PWD" "$@"
