#!/bin/bash
#   setsid nohup sim/runners/cold_reseed_ff.sh > sim/results/cold_reseed_ff.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim/decks
../../tools/safe_ngspice.sh e2e_prbs_ffm40_seed070.spice ../results/e2e_prbs_ffm40_seed070.log 2500 5400 2000 >/dev/null 2>&1
echo "=== ff/-40C/1.32V seeded 0.70 (was 0.546)"
grep -E "^(f_long|f_err|vctrl_s1|vctrl_s2|vctrl_s3|vctrl_ripp|vctrl_max|vctrl_min|rclk_swing) = " ../results/e2e_prbs_ffm40_seed070.log
echo "### RESEED_FF DONE $(date +%H:%M)"
