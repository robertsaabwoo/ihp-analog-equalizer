#!/bin/bash
#   setsid nohup sim/runners/baseline_all.sh > sim/results/baseline_all.out 2>&1 &
# Where the design actually stands after: folded coarse pull-up, self-biased clock stage,
# cp_bias from ibias, balanced clock phases, and the ripple fixes REVERTED.
# Five corners with the trim pinned (fine loop alone, self-seeded) and the two ss corners
# with the coarse loop free, seeded from the LOADED ring sweep (ring_loaded_*.log).
set -u
cd /home/ttuser/ssh_analog/ct-worktree
say() { echo "[$(date +%H:%M)] $*"; }
for i in $(seq 1 120); do ps -eo args | grep -q "[n]gspice -b" || break; [ $((i%10)) -eq 1 ] && say "waiting for the simulator"; sleep 30; done

for spec in "tt 27 1.2" "tt 125 1.2" "ff 125 1.32" "tt -40 1.2" "ff -40 1.32"; do
  set -- $spec
  say "trim pinned: $1/$2 C/$3 V"
  sim/runners/prbs_corner.sh "$1" "$2" "$3" >/dev/null 2>&1
  if [ "${2#-}" = "$2" ]; then tag="${1}${2}_$(echo "$3" | tr -d .)"; else tag="${1}m${2#-}_$(echo "$3" | tr -d .)"; fi
  cat "sim/results/run_prbs_$tag.out" 2>/dev/null || echo "  (no output)"
done

# ss corners: the trim-off ring cannot reach the baud rate there, so the coarse loop must be
# free.  Seeds from ring_loaded: ss/125C needs the trim nearly full on and vctrl ~0.6-0.7;
# ss/-40C has far more trim authority.
say "coarse loop free: ss/125C/1.08V"
sim/runners/dual_corner.sh ss 125 1.08 0.70 0.13 >/dev/null 2>&1
cat sim/results/run_dual_ss125_108.out 2>/dev/null
say "coarse loop free: ss/-40C/1.08V"
sim/runners/dual_corner.sh ss -40 1.08 0.65 0.30 >/dev/null 2>&1
cat sim/results/run_dual_ssm40_108.out 2>/dev/null
echo "### BASELINE DONE $(date +%H:%M)"
