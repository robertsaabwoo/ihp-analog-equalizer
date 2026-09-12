#!/bin/bash
# The branch ring locks at vctrl = 0.473 with Kvco = 1239 MHz/V, against main's
# 0.595 V and 522 MHz/V -- 2.4x the loop gain, same charge pump, same filter.
# A bang-bang loop's correction per update scales with Kvco, and so does the
# effect of the pump's 11 % current mismatch.  Cut the pump current to match.
set -u
cd /home/ttuser/ssh_analog/ct-worktree
SRC=/home/ttuser/ssh_analog/ttsky-analog-equalizer/xschem
setpump () {
python3 - "$1" <<'PY'
import re, sys
p='tools/port_from_sky130.py'; s=open(p).read()
s=re.sub(r'\("tiny_pll_bias_gen_res", "R\[2\.\.0\]"\): \{"R": \d+\}',
         f'("tiny_pll_bias_gen_res", "R[2..0]"): {{"R": {sys.argv[1]}}}', s)
open(p,'w').write(s)
PY
python3 tools/port_from_sky130.py --src "$SRC" --dst xschem >/dev/null 2>&1
./tools/netlist.sh >/dev/null 2>&1
}
for R in 58000 96000; do
  echo "### pump bias resistor $R ohm (nominal 24000; higher = less pump current)"
  setpump $R
  sed -i "s/^\.ic v(x1\.x2\.vctrl)=.*/.ic v(x1.x2.vctrl)=0.473/" sim/decks/e2e_lock_slow.spice
  ( cd sim/decks && ../../tools/safe_ngspice.sh e2e_lock_slow.spice "../results/gain_$R.log" 2500 5400 2000 ) >/dev/null 2>&1
  L=sim/results/gain_$R.log
  printf 'R=%-7s f=%-11s err=%-10s vctrl=%-8s e1=%-8s e2=%-8s ripple=%-9s clk=%s\n' "$R" \
   "$(grep -m1 '^f_long = '     $L|awk '{print $3}')" "$(grep -m1 '^f_err = '  $L|awk '{print $3}')" \
   "$(grep -m1 '^vctrl_lock = ' $L|awk '{print $3}')" "$(grep -m1 '^vctrl_e1 = '$L|awk '{print $3}')" \
   "$(grep -m1 '^vctrl_e2 = '   $L|awk '{print $3}')" "$(grep -m1 '^vctrl_ripp = '$L|awk '{print $3}')" \
   "$(grep -m1 '^rclk_swing = ' $L|awk '{print $3}')"
done
setpump 24000
echo "=== GAIN SWEEP DONE (pump restored to 24k) ==="
