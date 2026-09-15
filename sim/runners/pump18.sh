#!/bin/bash
# 10000 ohm ring + up-source trimmed to 1.8 um, both patterns.
set -u
cd /home/ttuser/ssh_analog/ct-worktree
SRC=/home/ttuser/ssh_analog/ttsky-analog-equalizer/xschem
python3 tools/port_from_sky130.py --src "$SRC" --dst xschem >/dev/null 2>&1
./tools/netlist.sh >/dev/null 2>&1
echo "### netlist check:"
grep -A8 '^\.subckt tiny_pll_charge_pump' sim/netlists/blocks.inc | grep XMPSRC
grep -A8 '^\.subckt ring_inverter' sim/netlists/blocks.inc | grep XR1
for d in e2e_lock e2e_prbs; do
  sed -i "s/^\.ic v(x1\.x2\.vctrl)=.*/.ic v(x1.x2.vctrl)=0.595/" sim/decks/$d.spice
  ( cd sim/decks && ../../tools/safe_ngspice.sh $d.spice "../results/${d}_pump18.log" 2500 5400 2000 ) >/dev/null 2>&1
  L=sim/results/${d}_pump18.log
  printf '%-10s f=%-11s err=%-10s vctrl=%-8s e1=%-8s e2=%-8s ripple=%-9s clk=%s\n' "$d" \
   "$(grep -m1 '^f_long = '     $L|awk '{print $3}')" "$(grep -m1 '^f_err = '  $L|awk '{print $3}')" \
   "$(grep -m1 '^vctrl_lock = ' $L|awk '{print $3}')" "$(grep -m1 '^vctrl_e1 = '$L|awk '{print $3}')" \
   "$(grep -m1 '^vctrl_e2 = '   $L|awk '{print $3}')" "$(grep -m1 '^vctrl_ripp = '$L|awk '{print $3}')" \
   "$(grep -m1 '^rclk_swing = ' $L|awk '{print $3}')"
done
echo "=== PUMP18 DONE ==="
