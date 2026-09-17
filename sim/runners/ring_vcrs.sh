#!/bin/bash
#   setsid nohup sim/runners/ring_vcrs.sh > sim/results/ring_vcrs.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim
for i in $(seq 1 120); do ps -eo args | grep -q "[n]gspice -b" || break; sleep 30; done
./run_corners.sh ring_vcrs.spice ring_vcrs 'p_temp|p_vcrs' >/dev/null 2>&1
cd results
python3 - <<'PY'
import re
num=r'(-?\d\.\d+e[-+]\d{2})'
pat=re.compile(r'^(p_temp|p_vdd|p_vcrs|f_mhz|swing) = '+num+r'\s*$', re.I)
BAUD=600.6
for c in ('tt','ss','ff'):
    try: f=open(f'ring_vcrs_{c}.log')
    except FileNotFoundError: print(f"--- {c}: no log"); continue
    rows=[]; cur={}
    for line in f:
        m=pat.match(line.strip())
        if m: cur[m.group(1).lower()]=float(m.group(2))
        elif line.startswith('ROWEND'):
            if 'f_mhz' in cur and cur.get('swing',0)>=0.15: rows.append(cur)
            cur={}
    print(f"--- {c}: coarse rail that puts the ring at {BAUD} MHz, vctrl 0.60, loaded")
    for t in (-40,27,125):
        for v in (1.08,1.20,1.32):
            g=sorted([r for r in rows if r['p_temp']==t and abs(r['p_vdd']-v)<1e-6], key=lambda r:r['p_vcrs'])
            if not g: continue
            seed=None
            for a,b in zip(g,g[1:]):
                if min(a['f_mhz'],b['f_mhz'])<=BAUD<=max(a['f_mhz'],b['f_mhz']):
                    seed=a['p_vcrs']+(BAUD-a['f_mhz'])*(b['p_vcrs']-a['p_vcrs'])/(b['f_mhz']-a['f_mhz']); break
            rng=f"{min(r['f_mhz'] for r in g):.0f}-{max(r['f_mhz'] for r in g):.0f} MHz"
            print(f"  {t:>4}C {v:.2f}V  range {rng:>16}   vcoarse@baud "+(f"{seed:.3f} V" if seed else "NOT REACHED"))
PY
echo "### RING_VCRS DONE $(date +%H:%M)"
