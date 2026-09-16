#!/bin/bash
#   setsid nohup sim/runners/clkcmp.sh > sim/results/clkcmp.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim/decks
../../tools/safe_ngspice.sh clkcmp_ffm40.spice ../results/clkcmp_ffm40.log 2500 2400 2000 >/dev/null 2>&1
echo "=== ff/-40C: ring vs recovered clock frequency"
grep -E "^(f_ring|f_clk|f_sb|vc|ring_pp|clk_pp) = " ../results/clkcmp_ffm40.log
grep -m4 -iE "no such vector|failed|error" ../results/clkcmp_ffm40.log
echo "### CLKCMP DONE $(date +%H:%M)"
