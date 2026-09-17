#!/bin/bash
#   setsid nohup sim/runners/dual_all.sh > sim/results/dual_all.out 2>&1 &
# Closed loop with the coarse loop FREE, seeded per corner from ring_vcrs (the rail setting
# that puts the loaded ring on the baud rate at that vctrl).  With the slow leg in, holding
# the rail at VDD means trim off AND extra load, so a pinned-trim run no longer describes the
# design -- the dual loop is the design.
set -u
cd /home/ttuser/ssh_analog/ct-worktree
say() { echo "[$(date +%H:%M)] $*"; }
for i in $(seq 1 120); do ps -eo args | grep -q "[n]gspice -b" || break; sleep 30; done
#        corner T     VDD   vctrl vcoarse   (vcoarse from ring_vcrs_*.log)
for spec in "ff -40 1.32 0.60 0.989" \
            "tt 27  1.2  0.60 0.587" \
            "tt 125 1.2  0.60 0.545" \
            "ff 125 1.32 0.60 0.955" \
            "tt -40 1.2  0.60 0.465" \
            "ss 125 1.08 0.85 0.135" \
            "ss -40 1.08 0.60 0.187"; do
  set -- $spec
  say "$1/$2 C/$3 V  seeds vctrl $4, vcoarse $5"
  sim/runners/dual_corner.sh "$1" "$2" "$3" "$4" "$5" >/dev/null 2>&1
  if [ "${2#-}" = "$2" ]; then tag="${1}${2}_$(echo "$3" | tr -d .)"; else tag="${1}m${2#-}_$(echo "$3" | tr -d .)"; fi
  cat "sim/results/run_dual_$tag.out" 2>/dev/null || echo "  (no output)"
done
echo "### DUAL_ALL DONE $(date +%H:%M)"
