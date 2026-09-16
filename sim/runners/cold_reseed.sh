#!/bin/bash
#   setsid nohup sim/runners/cold_reseed.sh > sim/results/cold_reseed.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim/decks
../../tools/safe_ngspice.sh e2e_prbs_ttm40_seed080.spice ../results/e2e_prbs_ttm40_seed080.log 2500 5400 2000 >/dev/null 2>&1
echo "=== tt/-40C seeded 0.80 (was 0.637)"
grep -E "^(f_long|f_err|vctrl_s1|vctrl_s2|vctrl_s3|vctrl_ripp|vctrl_max|vctrl_min|rclk_swing) = " ../results/e2e_prbs_ttm40_seed080.log
echo "### RESEED DONE $(date +%H:%M)"
