#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
sh "$HERE/build.sh"
exec "${VICE:-x64sc}" -default +saveres -pal -speed 100 +warp +autostart-warp \
    -drive8type 1541 -drive8truedrive +trapdevice8 -drive8idle 0 -sound -autostartprgmode 1 \
    -autostart "$HERE/build/example.prg" "$@"
