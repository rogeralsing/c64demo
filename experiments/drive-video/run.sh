#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
sh build.sh
exec "${VICE:-x64sc}" -pal +saveres -speed 100 +warp +autostart-warp \
    -drive8type 1541 -drive8truedrive +trapdevice8 -drive8idle 0 \
    -autostartprgmode 1 -autostart "$PWD/build/example.prg" "$@"
