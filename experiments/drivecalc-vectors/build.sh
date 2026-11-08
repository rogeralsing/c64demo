#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
sh "$HERE/drive/build.sh"
exec sh "$HERE/../build-one.sh" "$HERE" "$@"
