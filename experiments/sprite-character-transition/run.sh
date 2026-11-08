#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
sh build.sh
exec "${VICE:-x64sc}" -pal +saveres -speed 100 +warp +autostart-warp \
    -VICIImodel 6569 -autostartprgmode 1 -autostart "$PWD/build/example.prg" "$@"
