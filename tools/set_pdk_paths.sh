#!/bin/bash
# Point every deck at this machine's PDK.
#
#   tools/set_pdk_paths.sh            uses $PDK_ROOT (see env.sh)
#   tools/set_pdk_paths.sh /some/pdk  uses that instead
#
# The decks carry absolute paths in their `.lib` and `pre_osdi` lines, because
# ngspice does not expand environment variables in `.lib` and the alternative --
# relying on a `.spiceinit` in the working directory -- means a deck only runs
# from one place and silently picks up whatever `.spiceinit` it happens to find
# instead.  A `~/.spiceinit` left over from sky130 work is a real thing to have
# on a machine that does both.
#
# So the paths are absolute and committed, and this script rewrites them.  It
# is idempotent and prints what it changed.
set -eu

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NEW="${1:-${PDK_ROOT:-$HOME/pdk}}"

if [ ! -d "$NEW/ihp-sg13cmos5l/libs.tech" ]; then
    echo "no PDK at $NEW/ihp-sg13cmos5l -- run tools/setup_pdk.sh first" >&2
    exit 1
fi

changed=0
for f in "$ROOT"/sim/decks/*.spice "$ROOT"/sim/decks/*.inc "$ROOT"/char/*.spice; do
    [ -e "$f" ] || continue
    if grep -qE '/[^ ]*/ihp-sg13cmos5l/libs\.tech' "$f"; then
        before=$(md5sum "$f" | cut -d' ' -f1)
        sed -i -E "s#[^ '\"]*/(ihp-sg13cmos5l|ihp-sg13g2)/libs\.tech#$NEW/\1/libs.tech#g" "$f"
        after=$(md5sum "$f" | cut -d' ' -f1)
        if [ "$before" != "$after" ]; then
            echo "  updated $(basename "$f")"
            changed=$((changed + 1))
        fi
    fi
done

echo "PDK paths set to $NEW ($changed file(s) changed)"
