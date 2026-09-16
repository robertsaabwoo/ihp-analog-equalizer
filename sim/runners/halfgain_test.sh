#!/bin/bash
# Loop-gain test at tt/-40C/1.2V: pump current halved via a cp_bias override.
#   setsid nohup sim/runners/halfgain_test.sh > sim/results/halfgain.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim/decks
../../tools/safe_ngspice.sh e2e_prbs_ttm40_halfgain.spice \
  ../results/e2e_prbs_ttm40_halfgain.log 2500 5400 2000 >/dev/null 2>&1
echo "=== override took?"
grep -m1 -i "redefinition of .subckt cp_bias" ../results/e2e_prbs_ttm40_halfgain.log \
  || echo "NO REDEFINITION WARNING -- RESULT VOID"
grep -E "^(f_long|f_err|vctrl_s1|vctrl_s2|vctrl_s3|vctrl_ripp|rclk_swing) = " \
  ../results/e2e_prbs_ttm40_halfgain.log
echo "### HALFGAIN DONE $(date +%H:%M)"
