#!/bin/bash
#   setsid nohup sim/runners/ring_slow.sh > sim/results/ring_slow.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim
for i in $(seq 1 120); do ps -eo args | grep -q "[n]gspice -b" || break; sleep 30; done
./run_corners.sh ring_slow_sweep.spice ring_slow 'p_csl|p_temp' >/dev/null 2>&1
cd results
python3 - <<'PY'
import re
num=r'(-?\d\.\d+e[-+]\d{2})'
pat=re.compile(r'^(p_csl|p_temp|p_vdd|p_vc|f_mhz|swing) = '+num+r'\s*$', re.I)
for c,label in (('ff','ff/-40C/1.32V needs SLOWING'),('ss','ss/125C/1.08V needs every MHz')):
    print(f"--- {c}: {label}   (trim off; slow leg engaged)")
    cur={}
    try: f=open(f'ring_slow_{c}.log')
    except FileNotFoundError: print("  (no log)"); continue
    want=(-40,1.32) if c=='ff' else (125,1.08)
    for line in f:
        m=pat.match(line.strip())
        if m: cur[m.group(1).lower()]=float(m.group(2))
        elif line.startswith('ROWEND'):
            if cur.get('p_temp')==want[0] and abs(cur.get('p_vdd',0)-want[1])<1e-6:
                fq=cur.get('f_mhz'); s=cur.get('swing',0)
                print(f"  Csl {cur.get('p_csl',0):.1f} um  vctrl {cur.get('p_vc',0):.2f}  "
                      f"{('%7.1f'%fq) if fq is not None else '   dead'} MHz  swing {s:.3f}")
            cur={}
PY
echo "### RING_SLOW DONE $(date +%H:%M)"
