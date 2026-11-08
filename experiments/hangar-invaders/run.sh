#!/bin/sh
set -eu
HERE=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
# Numeric keypad4/6 move and0 fires. Later options can select a custom keyset.
exec sh "$HERE/../run-one.sh" "$HERE" -controlport2device 1 -joydev2 1 \
    -keyset +joystick2autofire "$@"
