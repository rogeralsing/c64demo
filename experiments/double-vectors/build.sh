#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
SHARED="$HERE/../prepared-fragments"
sh "$SHARED/build.sh"
sh "$HERE/../build-one.sh" "$HERE"
cmp "$HERE/build/example.prg" "$SHARED/build/example.prg"
