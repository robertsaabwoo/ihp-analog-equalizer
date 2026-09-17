#!/bin/bash
#   setsid nohup sim/runners/cp_width.sh > sim/results/cp_width.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim
./run_corners.sh cp_width.spice cp_width 'p_wid|p_temp' >/dev/null 2>&1
cd results
python3 - <<'PY'
import re
num=r'(-?\d\.\d+e[-+]\d{2})'
pat=re.compile(r'^(p_wid|p_temp|p_vdd|q_up_fc|q_dn_fc|v_bn|v_bp) = '+num+r'\s*$', re.I)
for c in ('tt','ff'):
    print(f"--- {c}   (q_dn should be NEGATIVE and grow with width; UI = 1.665 ns)")
    cur={}
    try: f=open(f'cp_width_{c}.log')
    except FileNotFoundError: print("  (no log)"); continue
    for line in f:
        m=pat.match(line.strip())
        if m: cur[m.group(1).lower()]=float(m.group(2))
        elif line.startswith('ROWEND'):
            if len(cur)==7:
                print(f"  {cur['p_temp']:>4.0f}C {cur['p_vdd']:.2f}V  width {cur['p_wid']*1e9:5.2f} ns "
                      f"({cur['p_wid']/1.665e-9:.1f} UI)  q_up {cur['q_up_fc']:+6.2f}  q_dn {cur['q_dn_fc']:+6.2f} fC   "
                      f"bias_n {cur['v_bn']:.3f} bias_p {cur['v_bp']:.3f}")
            cur={}
PY
echo "### CP_WIDTH DONE $(date +%H:%M)"
