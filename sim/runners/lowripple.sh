#!/bin/bash
#   setsid nohup sim/runners/lowripple.sh > sim/results/lowripple.out 2>&1 &
# The two ripple fixes, closed loop: nominal (regression) then ff/-40C (the decisive one).
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim/decks
for d in e2e_prbs e2e_prbs_ffm40_lowripple; do
  ../../tools/safe_ngspice.sh $d.spice ../results/${d}_lr.log 2500 5400 2000 >/dev/null 2>&1
  echo "=== $d"
  grep -E "^(f_long|f_err|vctrl_s1|vctrl_s2|vctrl_s3|vctrl_ripp|vctrl_max|vctrl_min|rclk_swing) = " ../results/${d}_lr.log
  grep -m2 -iE "failed|error" ../results/${d}_lr.log
done
echo "### LOWRIPPLE DONE $(date +%H:%M)"
