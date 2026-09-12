#!/bin/bash
# LVS one cell: does the layout match the schematic?
#
#   mag/lvs_cell.sh robs_xor
#
# Layout side  : extracted from <cell>.mag by magic
# Schematic side: pulled out of sim/netlists/blocks.inc by tools/cell_netlist.py
#
# Verify EVERY cell before building anything on top of it.  An error in a leaf
# cell that is instantiated ten times is ten errors at the next level up, and
# netgen will report them as a mismatch in the parent, where they are far
# harder to read.
set -eu
cell="${1:?usage: lvs_cell.sh <cell>}"
cd "$(dirname "$0")"
ROOT=$(cd .. && pwd)
PDK=${PDK_ROOT:-/home/ttuser/pdk}/ihp-sg13cmos5l
RC=$PDK/libs.tech/magic/ihp-sg13cmos5l.magicrc
SETUP=$PDK/libs.tech/netgen/ihp-sg13cmos5l_setup.tcl

[ -f "$cell.mag" ] || { echo "no $cell.mag -- run 'make gen CELL=$cell' first"; exit 1; }

python3 "$ROOT/tools/cell_netlist.py" "$cell" > "$cell.sch.spice"
magic -dnull -noconsole -rcfile "$RC" tcl/extract.tcl "$cell" >/dev/null 2>&1
rm -f ./*.ext

netgen -batch lvs \
    "$cell.lvs.spice $cell" \
    "$cell.sch.spice $cell" \
    "$SETUP" "$cell.lvs.report" > /dev/null 2>&1 || true

echo "--- $cell"
tail -20 "$cell.lvs.report" | grep -viE "^$" || true
if grep -q "Circuits match uniquely" "$cell.lvs.report"; then
    echo "LVS: MATCH"
else
    echo "LVS: no match yet -- full report in mag/$cell.lvs.report"
    exit 1
fi
