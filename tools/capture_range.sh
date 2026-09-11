#!/bin/bash
# How far off can the ring be and still be caught by the fine loop alone?
#
# docs/RING_DUAL_LOOP.md section 3.2 sets the coarse search rate from a number
# that has never been measured: the fine loop's capture range.  The argument is
# that the search must move the ring by much less than that range during the
# 1.5 us the fine loop needs to settle, or it sweeps straight through lock.
# Without the range the rate is a guess.
#
# The band probe already bracketed it crudely -- the ring locks at 7355 ohm,
# and fails at 8460 (4.0 % slow after the loop has done all it can) and at 6400
# (12.1 % fast).  This walks in from both sides.  Each point is a full 1.5 us
# closed-loop transient, about twenty minutes, so this is an overnight job and
# the points are ordered so that the most informative ones run first.
#
# Reads out f_long (did it reach the baud rate), vctrl_lock (where the fine
# loop had to sit to do it) and the e1/e2 pair (is vctrl still drifting, which
# is what "not locked" looks like -- see section 2).
set -eu
cd "$(dirname "$0")/.."
ROOT=$(pwd)
SRC=/home/ttuser/ssh_analog/ttsky-analog-equalizer/xschem

setR () {
  python3 - "$1" <<'PY'
import re, sys
p='tools/port_from_sky130.py'; s=open(p).read()
s=re.sub(r'    \("ring_inverter", "R1"\): \{"R": \d+\},\n    \("ring_inverter", "R2"\): \{"R": \d+\},\n', '', s)
if sys.argv[1] != "nominal":
    s=s.replace('    ("ring_inverter", "M1"): {"W": 3, "L": 0.9},',
        f'    ("ring_inverter", "R1"): {{"R": {sys.argv[1]}}},\n'
        f'    ("ring_inverter", "R2"): {{"R": {sys.argv[1]}}},\n'
        '    ("ring_inverter", "M1"): {"W": 3, "L": 0.9},')
open(p,'w').write(s)
PY
  python3 tools/port_from_sky130.py --src "$SRC" --dst xschem >/dev/null 2>&1
  ./tools/netlist.sh >/dev/null 2>&1
}

# Slow side first (7355 locks, 8460 does not), then the fast side
# (7355 locks, 6400 does not).  Interleaved so that a run that gets killed
# still leaves a bracket on both sides.
for R in 7900 6900 8200 6600 7600 7100; do
  setR "$R"
  ( cd sim/decks && "$ROOT/tools/safe_ngspice.sh" e2e_lock.spice \
      "../results/e2e_cap_$R.log" 2500 2700 2000 )
  L="sim/results/e2e_cap_$R.log"
  printf '  R=%-5s f=%-12s err=%-10s vctrl=%-10s e1=%-10s e2=%-10s ripple=%s\n' \
    "$R" \
    "$(grep -m1 '^f_long = '     "$L" | awk '{print $3}')" \
    "$(grep -m1 '^f_err = '      "$L" | awk '{print $3}')" \
    "$(grep -m1 '^vctrl_lock = ' "$L" | awk '{print $3}')" \
    "$(grep -m1 '^vctrl_e1 = '   "$L" | awk '{print $3}')" \
    "$(grep -m1 '^vctrl_e2 = '   "$L" | awk '{print $3}')" \
    "$(grep -m1 '^vctrl_ripp = ' "$L" | awk '{print $3}')"
done
setR nominal
echo "=== CAPTURE RANGE DONE (nominal restored) ==="
