#!/bin/sh
set -eu
cd "$(dirname "$0")"
sh build.sh
exec "${VICE:-x64sc}" -pal -VICIImodel 6569 +saveres -speed 100 +warp +autostart-warp -autostartprgmode 1 -autostart "$PWD/build/example.prg" "$@"
