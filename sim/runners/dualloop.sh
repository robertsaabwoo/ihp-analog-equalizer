#!/bin/bash
# The coarse loop closed-loop, on the 10000 ohm ring with the 1.8 um pump trim.
# Run ONLY after e2e_prbs_pump18 locks -- on a configuration whose fine loop
# does not hold PRBS7 these measure nothing useful.
#   e2e_dual       : vcoarse at the rail, vctrl at its lock point.  The loops
#                    must not disturb each other; f and ripple must match e2e_lock.
#   e2e_dual_walk  : vcoarse 0.55 V, where the ring sits on the steep side.  The
#                    pull-up must walk vcoarse up while the clock stays on the data.
set -u
cd /home/ttuser/ssh_analog/ct-worktree
grep -q 'w=1.8u' <(sed -n '/^\.subckt tiny_pll_charge_pump/,/^\.ends/p' sim/netlists/blocks.inc) \
  || { echo "netlist does not carry the 1.8 um pump trim -- refusing"; exit 1; }
for d in e2e_dual e2e_dual_walk; do
  ( cd sim/decks && ../../tools/safe_ngspice.sh $d.spice "../results/${d}_pump18.log" 2500 5400 2000 ) >/dev/null 2>&1
  L=sim/results/${d}_pump18.log
  echo "--- $d"
  grep -E "^(f_long|f_err|vctrl_lock|vctrl_ripp|rclk_swing|vcrs_e1|vcrs_e2|vcrs_walk_mv|vcrs_creep_mv|vctrl_e1|vctrl_e2) = " $L
done
echo "=== DUALLOOP DONE ==="
