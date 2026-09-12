#!/bin/bash
set -u
cd /home/ttuser/ssh_analog/ct-worktree
SRC=/home/ttuser/ssh_analog/ttsky-analog-equalizer/xschem
python3 - <<'PY'
import re
p='tools/port_from_sky130.py'; s=open(p).read()
for m in ("M1","M4"):
    s=re.sub(rf'\("ring_inverter", "{m}"\): \{{"W": 3, "L": [0-9.]+\}}',
             f'("ring_inverter", "{m}"): {{"W": 3, "L": 0.7}}', s)
for r in ("R1","R2"):
    s=re.sub(rf'\("ring_inverter", "{r}"\): \{{"R": \d+\}}',
             f'("ring_inverter", "{r}"): {{"R": 10000}}', s)
open(p,'w').write(s)
PY
python3 tools/port_from_sky130.py --src "$SRC" --dst xschem >/dev/null 2>&1
./tools/netlist.sh >/dev/null 2>&1
sed -i "s/^\.ic v(x1\.x2\.vctrl)=.*/.ic v(x1.x2.vctrl)=0.595/" sim/decks/e2e_lock.spice
echo "### 0.7 um pair, 10000 ohm, trim legs on, trim off, seed 0.595"
( cd sim/decks && ../../tools/safe_ngspice.sh e2e_lock.spice ../results/r10k.log 2500 3600 2000 ) >/dev/null 2>&1
L=sim/results/r10k.log
printf 'f=%-11s err=%-10s vctrl=%-8s e1=%-8s e2=%-8s ripple=%-9s clk=%s\n' \
 "$(grep -m1 '^f_long = '     $L|awk '{print $3}')" "$(grep -m1 '^f_err = '  $L|awk '{print $3}')" \
 "$(grep -m1 '^vctrl_lock = ' $L|awk '{print $3}')" "$(grep -m1 '^vctrl_e1 = '$L|awk '{print $3}')" \
 "$(grep -m1 '^vctrl_e2 = '   $L|awk '{print $3}')" "$(grep -m1 '^vctrl_ripp = '$L|awk '{print $3}')" \
 "$(grep -m1 '^rclk_swing = ' $L|awk '{print $3}')"
grep -m2 -iE "failed" $L || true
echo "=== R10K DONE ==="
