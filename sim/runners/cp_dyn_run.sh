#!/bin/bash
#   setsid nohup sim/runners/cp_dyn_run.sh > sim/results/cp_dyn.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim
./run_corners.sh cp_dyn.spice cp_dyn 'p_temp|p_vdd' >/dev/null 2>&1
cd results
python3 - <<'PY'
import re
num=r'(-?\d\.\d+e[-+]\d{2})'
for c in ('tt','ss','ff'):
    print(f"--- {c}  (net current into vctrl, nA; + = charging up)")
    cur={}
    for line in open(f'cp_dyn_{c}.log'):
        m=re.match(r'^(p_temp|p_vdd|p_vout|i_net_na) = '+num+r'\s*$', line.strip(), re.I)
        if m: cur[m.group(1).lower()]=float(m.group(2))
        if line.startswith('ROWEND'):
            if len(cur)==4:
                print(f"  {cur['p_temp']:>4.0f}C {cur['p_vdd']:.2f}V vout {cur['p_vout']:.2f}  {cur['i_net_na']:+8.1f} nA")
            cur={}
PY
echo "### CP_DYN DONE $(date +%H:%M)"
