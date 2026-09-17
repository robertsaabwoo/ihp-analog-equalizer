#!/bin/bash
#   setsid nohup sim/runners/ring_loaded.sh > sim/results/ring_loaded.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim
./run_corners.sh ring_loaded.spice ring_loaded 'p_temp|p_vdd' >/dev/null 2>&1
cd results
python3 - <<'PY'
import re
num=r'(-?\d\.\d+e[-+]\d{2})'
pat=re.compile(r'^(p_temp|p_vdd|p_trim|p_vc|f_mhz|swing) = '+num+r'\s*$', re.I)
for c in ('tt','ss','ff'):
    try: f=open(f'ring_loaded_{c}.log')
    except FileNotFoundError: print(f"--- {c}: no log"); continue
    print(f"--- {c}   (LOADED: ring + CDR diff amp + clock stage + buffers)")
    cur={}
    for line in f:
        m=pat.match(line.strip())
        if m: cur[m.group(1).lower()]=float(m.group(2))
        elif line.startswith('ROWEND'):
            if len(cur)==6:
                t='ON ' if cur['p_trim']<0.5 else 'off'
                mark=' <-- baud' if abs(cur['f_mhz']-600.6)<12 and cur['swing']>=0.15 else ''
                print(f"  {cur['p_temp']:>4.0f}C {cur['p_vdd']:.2f}V trim {t} vctrl {cur['p_vc']:.2f}  {cur['f_mhz']:7.1f} MHz  swing {cur['swing']:.3f}{mark}")
            cur={}
PY
echo "### RING_LOADED DONE $(date +%H:%M)"
