#!/bin/sh
set -eu

experiment_dir=${1:?Usage: build-one.sh EXPERIMENT_DIRECTORY [KICKASSEMBLER_OPTIONS...]}
shift
cd "$experiment_dir"

java_bin=${JAVA:-${JAVA_HOME:+$JAVA_HOME/bin/java}}
if [ -z "$java_bin" ]; then
    java_bin=$(command -v java || true)
    if [ -z "$java_bin" ] || [ "$java_bin" = /usr/bin/java ]; then
        for candidate in /opt/homebrew/opt/openjdk/bin/java /usr/local/opt/openjdk/bin/java; do
            if [ -x "$candidate" ]; then java_bin=$candidate; break; fi
        done
    fi
fi
if [ -z "$java_bin" ] || ! command -v "$java_bin" >/dev/null 2>&1; then
    echo "Java not found. Install Java 11 or newer, or set JAVA." >&2
    exit 1
fi

kickass_jar=${KICKASS_JAR:-${XDG_DATA_HOME:-$HOME/.local/share}/c64-tools/KickAssembler/KickAss.jar}
if [ ! -f "$kickass_jar" ]; then
    echo "KickAssembler not found at: $kickass_jar" >&2
    exit 1
fi

mkdir -p build
assembly_status=0
"$java_bin" -jar "$kickass_jar" main.asm \
    -odir "$PWD/build" -o "$PWD/build/example.prg" \
    -symbolfile -vicesymbols "$@" >build/assembler.log 2>&1 || assembly_status=$?
cat build/assembler.log
if [ "$assembly_status" -ne 0 ]; then exit "$assembly_status"; fi
# KickAssembler reports failed .assert directives while still exiting zero.
if LC_ALL=C grep -Eq 'ERROR IN ASSERTION|[1-9][0-9]* failed' build/assembler.log; then
    echo "KickAssembler assertion failed; this build is not valid." >&2
    exit 1
fi
