#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

case "${1:-cube}" in
    cube) source=src/cube.asm; name=vector-cube ;;
    filled) source=src/filled.asm; name=filled-cube ;;
    icosahedron) source=src/icosahedron.asm; name=icosahedron ;;
    interlaced) source=src/icosahedron-interlaced.asm; name=icosahedron-interlaced ;;
    dither) source=src/icosahedron-dither.asm; name=icosahedron-dither ;;
    tonal) source=src/icosahedron-tonal.asm; name=icosahedron-tonal ;;
    gouraud) source=src/icosahedron-gouraud.asm; name=icosahedron-gouraud ;;
    fast) source=src/icosahedron-fast.asm; name=icosahedron-fast ;;
    glenz) source=src/glenz.asm; name=glenz ;;
    painted) source=src/painted.asm; name=painted-cube ;;
    pong) source=src/pong.asm; name=pong-cube ;;
    raster) source=src/main.asm; name=hello-raster ;;
    *) echo "Usage: $0 [cube|filled|icosahedron|interlaced|dither|tonal|gouraud|fast|glenz|painted|pong|raster]" >&2; exit 2 ;;
esac

java_bin=${JAVA:-${JAVA_HOME:+$JAVA_HOME/bin/java}}
if [ -z "$java_bin" ]; then
    java_bin=$(command -v java || true)
    # /usr/bin/java is a launcher stub on macOS, not an installed JRE.
    if [ -z "$java_bin" ] || [ "$java_bin" = /usr/bin/java ]; then
        for candidate in /opt/homebrew/opt/openjdk/bin/java /usr/local/opt/openjdk/bin/java; do
            if [ -x "$candidate" ]; then java_bin=$candidate; break; fi
        done
    fi
fi
if [ -z "$java_bin" ] || ! command -v "$java_bin" >/dev/null 2>&1; then
    echo "Java not found. Install Java 11 or newer, or set JAVA to its executable." >&2
    exit 1
fi

kickass_jar=${KICKASS_JAR:-${XDG_DATA_HOME:-$HOME/.local/share}/c64-tools/KickAssembler/KickAss.jar}
if [ ! -f "$kickass_jar" ]; then
    echo "KickAssembler not found at: $kickass_jar" >&2
    echo "Download https://theweb.dk/KickAssembler/ and set KICKASS_JAR to KickAss.jar." >&2
    exit 1
fi

mkdir -p build
exec "$java_bin" -jar "$kickass_jar" "$source" \
    -odir "$PWD/build" -o "$PWD/build/$name.prg" \
    -debugdump -debug -symbolfile -vicesymbols \
    -asminfo 'files|errors' -asminfofile "$PWD/build/$name.info"
