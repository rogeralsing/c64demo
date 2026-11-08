#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
case "${1-}" in
    xor-hybrid) shift; exec sh ../run-one.sh "$PWD/xor-hybrid" "$@" ;;
    ortho) shift; exec sh ../run-one.sh "$PWD/ortho" "$@" ;;
    one-face) shift; exec sh ../run-one.sh "$PWD/one-face" "$@" ;;
    all) shift ;;
esac
exec sh ../run-one.sh "$PWD" "$@"
