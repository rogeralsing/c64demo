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
    *) echo "Usage: $0 [cube|filled|icosahedron|interlaced|dither|tonal|gouraud|fast|glenz|raster] [VICE options...]" >&2; exit 2 ;;
esac

vice_bin=${VICE:-$(command -v x64sc || true)}
if [ -z "$vice_bin" ]; then
    for candidate in /opt/homebrew/bin/x64sc /usr/local/bin/x64sc; do
        if [ -x "$candidate" ]; then vice_bin=$candidate; break; fi
    done
fi
if [ -z "$vice_bin" ] || ! command -v "$vice_bin" >/dev/null 2>&1; then
    echo "VICE x64sc not found. Install VICE or set VICE to its executable." >&2
    exit 1
fi

./build.sh "$target"
if [ "$target" = cube ] || [ "$target" = filled ] || [ "$target" = icosahedron ] || [ "$target" = interlaced ] || [ "$target" = dither ] || [ "$target" = tonal ] || [ "$target" = gouraud ] || [ "$target" = fast ] || [ "$target" = glenz ]; then
    # The cube is silent. Keep playback at real speed without persisting settings.
    set -- +saveres -speed 100 +warp +autostart-warp +sound "$@"
fi
exec "$vice_bin" -pal -autostartprgmode 1 \
    -autostart "$PWD/build/$name.prg" "$@"
