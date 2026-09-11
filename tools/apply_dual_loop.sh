#!/bin/bash
# Put the dual loop into the design, as one step.
#
# Three things have to happen together or the repository is briefly incoherent
# in a way that produces wrong numbers rather than errors:
#
#   1. re-run the port, which rewrites xschem/ from the sky130 source with the
#      new ring sizing and applies add_coarse_trim and add_coarse_loop;
#   2. re-netlist, which is what the decks actually read;
#   3. migrate the decks, because the CDR's loop filter output stops being the
#      anonymous `net1` and becomes `vctrl`, and because every deck that
#      measures the *fine* loop alone now has to pin `vcoarse!` -- with it free,
#      the coarse loop quietly corrects whatever detuning the deck is applying
#      and every point passes.
#
# Step 3 is the one that matters.  Step 1 and 2 on their own leave a tree where
# e2e_lock.spice still runs, still reports a lock, and is measuring a different
# circuit from the one it claims.
#
# Holds the ngspice lock for the duration, so it cannot land in the middle of a
# running sweep's re-read of blocks.inc.
set -eu
cd "$(dirname "$0")/.."
SRC=${SRC:-/home/ttuser/ssh_analog/ttsky-analog-equalizer/xschem}

exec 9>"${TMPDIR:-/tmp}/.safe_ngspice.lock"
echo "[apply] waiting for the ngspice lock..."
flock 9
echo "[apply] got it"

python3 tools/port_from_sky130.py --src "$SRC" --dst xschem
python3 tools/gen_coarse_loop.py
./tools/netlist.sh
python3 tools/migrate_decks.py
python3 -m pytest test -q

echo
echo "--- ring_inverter"
grep -A16 '^\.subckt ring_inverter' sim/netlists/blocks.inc | grep -E '^X'
echo "--- CDR"
grep -A16 '^\.subckt CDR ' sim/netlists/blocks.inc | grep -E '^x|^\.subckt'
echo "--- device count"
python3 tools/area_budget.py | tail -8
