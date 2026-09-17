#!/bin/bash
# Starts the current-steering pump measurement once the overnight chain is finished, so the
# queue stays full without two runners fighting over a deck.
#   setsid nohup sim/runners/after_overnight.sh > sim/results/after_overnight.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree
for i in $(seq 1 480); do
  grep -q "OVERNIGHT DONE" sim/results/overnight.out 2>/dev/null && break
  sleep 30
done
echo "[$(date +%H:%M)] overnight chain done (or timed out); starting cp_steer"
sim/runners/cp_steer.sh > sim/results/cp_steer.out 2>&1 || echo "cp_steer exit $?"
echo "=== comparison: switched vs current-steering, worst |q_up + q_dn| over 27 corners"
python3 tools/pick_pump_sizing.py sim/results/cp_charge_tt.log sim/results/cp_charge_ss.log sim/results/cp_charge_ff.log 2>&1 | grep -E "CHOSEN|as built" | sed 's/^/  switched:  /'
python3 tools/pick_pump_sizing.py sim/results/cp_steer_tt.log sim/results/cp_steer_ss.log sim/results/cp_steer_ff.log 2>&1 | grep -E "CHOSEN|as built" | sed 's/^/  steering:  /'
echo "### AFTER_OVERNIGHT DONE $(date +%H:%M)"
