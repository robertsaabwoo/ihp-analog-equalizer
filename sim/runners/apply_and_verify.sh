#!/bin/bash
# Apply the chosen ring sizing, then verify it where it matters.
#   setsid nohup sim/runners/apply_and_verify.sh > sim/results/apply_verify.out 2>&1 &
#
# Sequential and detached.  The sizing came from the ring_centre grids scored by
# tools/pick_ring_sizing.py, and ring_bracket.out confirms the baud rate is still between
# the ring's extremes at all 27 corners.  Seeds are re-derived by prbs_corner.sh, because a
# slower ring moves every corner's lock point and the old fixed seeds are now wrong.
set -u
cd /home/ttuser/ssh_analog/ct-worktree
say() { echo "[$(date +%H:%M)] $*"; }

for i in $(seq 1 120); do
  ps -eo args | grep -q "[n]gspice -b" || break
  [ $((i % 10)) -eq 1 ] && say "waiting for the simulator"
  sleep 30
done

say "applying Rload 11000, Wtr 4"
python3 tools/apply_ring_sizing.py 11000 4 || { say "apply FAILED"; exit 1; }

say "regression: nominal, self-seeded"
sim/runners/prbs_corner.sh tt 27 1.2 >/dev/null 2>&1
cat sim/results/run_prbs_tt27_12.out 2>/dev/null

say "the corner that fails: ff/-40C/1.32V, trim pinned, self-seeded"
sim/runners/prbs_corner.sh ff -40 1.32 >/dev/null 2>&1
cat sim/results/run_prbs_ffm40_132.out 2>/dev/null

say "the same corner with the coarse loop FREE (dual loop)"
sim/runners/dual_corner.sh ff -40 1.32 0.60 1.20 >/dev/null 2>&1
cat sim/results/run_dual_ffm40_132.out 2>/dev/null

say "hot corner regression, coarse loop free"
sim/runners/dual_corner.sh tt 125 1.2 0.62 1.20 >/dev/null 2>&1
cat sim/results/run_dual_tt125_12.out 2>/dev/null

say "=== done"
echo "### APPLY_VERIFY DONE $(date +%H:%M)"
