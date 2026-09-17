#!/bin/bash
#   setsid nohup sim/runners/rhalf_verify.sh > sim/results/rhalf_verify.out 2>&1 &
# Test the loop-filter resistor halving (15k -> 7.5k) where it is supposed to matter.
# docs/notes/capture_model.md: the capture criterion is Phi = Kvco * I_pump * R * T_b, and
# every corner that locks sits at <= 7.7e-3 while ff/-40C sits at 1.58e-2.  Halving R halves
# Phi, which should put ff/-40C at ~7.9e-3 -- at the boundary, with the ring untouched (the
# ring cannot be slowed without hurting ss/125C, which already cannot reach the baud rate).
set -u
cd /home/ttuser/ssh_analog/ct-worktree
say() { echo "[$(date +%H:%M)] $*"; }
for i in $(seq 1 120); do ps -eo args | grep -q "[n]gspice -b" || break; [ $((i%10)) -eq 1 ] && say "waiting for the simulator"; sleep 30; done

say "ff/-40C/1.32V, trim pinned, self-seeded -- the corner that never captures"
sim/runners/prbs_corner.sh ff -40 1.32 >/dev/null 2>&1
cat sim/results/run_prbs_ffm40_132.out 2>/dev/null

say "nominal regression, self-seeded"
sim/runners/prbs_corner.sh tt 27 1.2 >/dev/null 2>&1
cat sim/results/run_prbs_tt27_12.out 2>/dev/null

say "hot regression, trim pinned"
sim/runners/prbs_corner.sh tt 125 1.2 >/dev/null 2>&1
cat sim/results/run_prbs_tt125_12.out 2>/dev/null

echo "### RHALF DONE $(date +%H:%M)"
