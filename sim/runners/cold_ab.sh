#!/bin/bash
#   setsid nohup sim/runners/cold_ab.sh > sim/results/cold_ab.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim/decks
echo "=== A: tt/-40C with a plain inverter instead of sb_inverter"
../../tools/safe_ngspice.sh e2e_prbs_ttm40_nosb.spice ../results/e2e_prbs_ttm40_nosb.log 2500 5400 2000 >/dev/null 2>&1
grep -m1 -i "redefinition of .subckt sb_inverter" ../results/e2e_prbs_ttm40_nosb.log || echo "NO REDEFINITION WARNING -- RESULT VOID"
grep -E "^(f_long|f_err|vctrl_s1|vctrl_s2|vctrl_s3|vctrl_ripp|rclk_swing) = " ../results/e2e_prbs_ttm40_nosb.log
echo "=== B: tt/-40C early trace, first 1 us"
../../tools/safe_ngspice.sh e2e_prbs_ttm40_early.spice ../results/e2e_prbs_ttm40_early.log 2500 5400 2000 >/dev/null 2>&1
grep -E "^(vc_[0-9]{4}|rk_pp) = " ../results/e2e_prbs_ttm40_early.log
echo "### COLD_AB DONE $(date +%H:%M)"
