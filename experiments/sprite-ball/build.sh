#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
variant=${1:-baseline}
case "$variant" in
    golden) set -- -define GOLDEN_PENTAGON ;;
    baseline) set -- ;;
    *) echo "Usage: sh build.sh [golden|baseline]" >&2; exit 2 ;;
esac
mkdir -p "build/$variant"
python3 model.py --output build
exec "${KICKASS:-kickass}" main.asm -odir "$PWD/build/$variant" \
    -o "$PWD/build/$variant/sprite-ball.prg" -symbolfile -vicesymbols "$@"
