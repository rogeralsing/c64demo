#!/bin/sh
set -eu
cd "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
case "${1-}" in
    one-face) shift; exec sh ../build-one.sh "$PWD/one-face" "$@" ;;
    all) shift ;;
esac
exec sh ../build-one.sh "$PWD" "$@"
