#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

target=${1:-cube}
if [ "$#" -gt 0 ]; then shift; fi
case "$target" in
    cube) name=vector-cube ;;
    filled) name=filled-cube ;;
    icosahedron) name=icosahedron ;;
    interlaced) name=icosahedron-interlaced ;;
    dither) name=icosahedron-dither ;;
    tonal) name=icosahedron-tonal ;;
    gouraud) name=icosahedron-gouraud ;;
    fast) name=icosahedron-fast ;;
    glenz) name=glenz ;;
    raster) name=hello-raster ;;
    *) echo "Usage: $0 [cube|filled|icosahedron|interlaced|dither|tonal|gouraud|fast|glenz|raster] [RetroDebugger options...]" >&2; exit 2 ;;
esac

retro_bin=${RETRO_DEBUGGER:-$(command -v retrodebugger || true)}
if [ -z "$retro_bin" ]; then
    for candidate in "/Applications/Retro Debugger.app/Contents/MacOS/Retro Debugger" /opt/homebrew/bin/RetroDebugger /usr/local/bin/RetroDebugger; do
        if [ -x "$candidate" ]; then retro_bin=$candidate; break; fi
    done
fi
if [ -z "$retro_bin" ] || ! command -v "$retro_bin" >/dev/null 2>&1; then
    echo "RetroDebugger not found. Install it or set RETRO_DEBUGGER to its executable." >&2
    exit 1
fi

./build.sh "$target"
exec "$retro_bin" \
    -pass -c64 -wait 1000 \
    -prg "$PWD/build/$name.prg" \
    -debuginfo "$PWD/build/$name.dbg" -autojmp -unpause "$@"
