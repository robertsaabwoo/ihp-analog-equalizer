#!/bin/bash
#   setsid nohup sim/runners/pd_probe_ff.sh > sim/results/pd_probe_ff.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim/decks
../../tools/safe_ngspice.sh pd_probe_ffm40.spice ../results/pd_probe_ffm40.log 2500 2400 2000 >/dev/null 2>&1
echo "=== pd_probe_ffm40 (up_avg/dn_avg = duty x VDD; compare tt125 0.382/0.175, ttm40 0.287/0.193)"
grep -E "^[a-z0-9_]+_(avg|pp) = " ../results/pd_probe_ffm40.log
grep -m3 -iE "no such vector|error" ../results/pd_probe_ffm40.log
echo "### PD_FF DONE $(date +%H:%M)"
