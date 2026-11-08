#!/bin/sh
set -eu

experiment_dir=${1:?Usage: run-one.sh EXPERIMENT_DIRECTORY [VICE_OPTIONS...]}
shift
experiment_dir=$(CDPATH= cd -- "$experiment_dir" && pwd)
sh "$(dirname -- "$0")/build-one.sh" "$experiment_dir"
exec "${VICE:-x64sc}" -pal +saveres -speed 100 +warp +autostart-warp \
    -sound -autostartprgmode 1 -autostart "$experiment_dir/build/example.prg" "$@"
