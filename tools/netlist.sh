#!/bin/bash
# Netlist the whole design into one includable file of .subckt definitions.
#
#   tools/netlist.sh
#
# Produces sim/netlists/blocks.inc, which every testbench includes.  Each
# testbench then instantiates only the block it is testing, so a CTLE AC sweep
# does not carry 121 devices of CDR it is not looking at.
#
# The source is xschem/ctle_cdr_rx_lvs.sch -- a one-instance wrapper that
# exists solely so xschem emits a .subckt for the chip top.  Netlisting
# ctle_cdr_rx.sch directly makes it the top level and emits no .subckt at all.
# The wrapper's own single instance line is stripped here, because an include
# file must define subcircuits and instantiate nothing.
#
# Two traps this script exists to avoid, both silent:
#   * xschem's -r flag is --no_readline, NOT an rcfile flag.  Passing it gives
#     a truncated netlist full of "Symbol not found" and a zero exit status.
#   * if PDK/PDK_ROOT point at a different process, the sg13cmos5l symbols are
#     not on XSCHEM_LIBRARY_PATH, every device silently fails to resolve, and
#     the netlist comes out structurally valid and empty of transistors.
set -eu

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
. "$ROOT/env.sh"

OUT="$ROOT/sim/netlists"
mkdir -p "$OUT"

cd "$ROOT/xschem"
xschem -n -s -x -q --rcfile ./xschemrc -o "$OUT" ctle_cdr_rx_lvs.sch

RAW="$OUT/ctle_cdr_rx_lvs.spice"
[ -s "$RAW" ] || { echo "netlist.sh: xschem produced no netlist" >&2; exit 1; }

if grep -q "Symbol not found" "$RAW"; then
    echo "netlist.sh: 'Symbol not found' in the netlist -- XSCHEM_LIBRARY_PATH is wrong." >&2
    grep -n "Symbol not found" "$RAW" >&2
    exit 1
fi

# Guard against the empty-netlist failure mode: this design has 71 MOSFETs.
n_mos=$(grep -c "sg13_lv_[np]mos" "$RAW" || true)
if [ "$n_mos" -lt 60 ]; then
    echo "netlist.sh: only $n_mos MOSFETs in the netlist -- symbols did not resolve." >&2
    exit 1
fi

# Strip the wrapper's own instance; keep everything else byte for byte.
#
# Matched by shape -- any line at column 0 that instantiates ctle_cdr_rx --
# rather than by its exact text.  An earlier version matched the full line
# including the pin names, and when the bias pin was renamed vbias -> ibias
# the match silently stopped working.  blocks.inc then still instantiated the
# entire chip, so every testbench that included it got a second copy of the
# receiver named x1, colliding with the block it was actually trying to test.
# ngspice's report of that was "device already exists, bail out" naming a
# device four levels down a hierarchy the testbench never mentioned.
grep -vE '^[xX][^ ]* .* ctle_cdr_rx[[:space:]]*$' "$RAW" > "$OUT/blocks.inc"

# Verify nothing is instantiated outside a .subckt block.  Instances *inside*
# one are the design; instances outside it are the whole chip coming along for
# the ride into every testbench.
stray=$(awk '
    /^[.]subckt/ { depth++; next }
    /^[.]ends/   { if (depth > 0) depth--; next }
    depth == 0 && /^[xX]/ { print NR": "$0 }
' "$OUT/blocks.inc")
if [ -n "$stray" ]; then
    echo "netlist.sh: blocks.inc instantiates something at the top level -- it must" >&2
    echo "            define subcircuits only, or every testbench that includes it" >&2
    echo "            elaborates the entire chip alongside the block under test." >&2
    echo "$stray" >&2
    exit 1
fi

echo "netlist.sh: $OUT/blocks.inc  ($n_mos MOSFETs, $(grep -c '^\.subckt' "$OUT/blocks.inc") subcircuits)"
