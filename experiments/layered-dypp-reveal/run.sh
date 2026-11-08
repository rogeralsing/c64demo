#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
sh build.sh
exec "${VICE:-x64sc}" -default +saveres -pal -speed 100 +warp +autostart-warp \
    -sound -autostartprgmode 1 -autostart "$PWD/build/example.prg" "$@"
