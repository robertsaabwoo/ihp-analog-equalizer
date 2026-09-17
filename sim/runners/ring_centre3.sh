#!/bin/bash
#   setsid nohup sim/runners/ring_centre.sh > sim/results/ring_centre3.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim/decks
for d in ring_centre3_ffm40 ring_centre3_ss125; do
  ../../tools/safe_ngspice.sh $d.spice ../results/$d.log 2500 2400 2000 >/dev/null 2>&1
  echo "=== $d"
  python3 - ../results/$d.log <<'PY'
import re, sys
num=r'(-?\d\.\d+e[-+]\d{2})'
pat=re.compile(r'^(p_rl|p_wt|p_trim|p_vc|f_mhz|swing) = '+num+r'\s*$', re.I)
cur={}
for line in open(sys.argv[1]):
    m=pat.match(line.strip())
    if m: cur[m.group(1).lower()]=float(m.group(2))
    elif line.startswith('ROWEND'):
        if len(cur)==6:
            t = "off" if cur['p_trim']>0.5 else "ON "
            flag = "  <-- 600.6 reachable" if abs(cur['f_mhz']-600.6)<25 and cur['swing']>=0.15 else ""
            print(f"  R{cur['p_rl']:.0f} Wtr{cur['p_wt']:.0f} trim {t} vctrl {cur['p_vc']:.2f}  {cur['f_mhz']:7.1f} MHz  swing {cur['swing']:.3f}{flag}")
        cur={}
PY
done
echo "### RING_CENTRE3 DONE $(date +%H:%M)"
