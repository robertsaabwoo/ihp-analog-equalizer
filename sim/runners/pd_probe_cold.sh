#!/bin/bash
#   setsid nohup sim/runners/pd_probe_cold.sh > sim/results/pd_probe_cold.out 2>&1 &
# Is the detector's correction inverted at the cold (fast-ring) corners?  The
# self-biased clock stage added delay; at -40 C the bit period is shortest.
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim/decks
../../tools/safe_ngspice.sh pd_probe_ttm40.spice ../results/pd_probe_ttm40.log 2500 2400 2000 >/dev/null 2>&1
echo "=== pd_probe_ttm40 (up/dn averages: up-dominant while the ring is FAST = inverted)"
grep -E "^[a-z0-9_]+_(avg|pp) = " ../results/pd_probe_ttm40.log
grep -m3 -iE "no such vector|error" ../results/pd_probe_ttm40.log
echo "### PD_COLD DONE $(date +%H:%M)"
