#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
variant=baseline
case "${1:-}" in golden|baseline) variant=$1; shift ;; esac
sh build.sh "$variant"
exec "${VICE:-x64sc}" -pal +saveres -speed 100 +warp +autostart-warp \
    +sound -autostartprgmode 1 -autostart "$PWD/build/$variant/sprite-ball.prg" "$@"
