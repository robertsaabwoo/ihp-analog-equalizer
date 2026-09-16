#!/bin/bash
#   setsid nohup sim/runners/loop_scurve.sh > sim/results/loop_scurve.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim/decks
for d in loop_scurve_tt125 loop_scurve_ffm40; do
  ../../tools/safe_ngspice.sh $d.spice ../results/$d.log 2500 5400 2000 >/dev/null 2>&1
  echo "=== $d"
  grep -m1 -i "redefinition of .subckt tiny_pll_loop_filter" ../results/$d.log || echo "NO REDEFINITION WARNING -- VOID"
  python3 - ../results/$d.log <<'PY'
import re, sys
num=r'(-?\d\.\d+e[-+]\d{2})'
pat=re.compile(r'^(p_vf|f_mhz|i_net_na) = '+num+r'\s*$', re.I)
cur={}
for line in open(sys.argv[1]):
    m=pat.match(line.strip())
    if m: cur[m.group(1).lower()]=float(m.group(2))
    elif line.startswith('ROWEND'):
        if len(cur)==3:
            print(f"  vctrl {cur['p_vf']:.2f}  {cur['f_mhz']:7.1f} MHz  net {cur['i_net_na']:+8.1f} nA")
        cur={}
PY
done
echo "### SCURVE DONE $(date +%H:%M)"
