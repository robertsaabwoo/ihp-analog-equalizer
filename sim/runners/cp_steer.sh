#!/bin/bash
#   setsid nohup sim/runners/cp_charge.sh > sim/results/cp_steer.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim
./run_corners.sh cp_steer.spice cp_steer 'p_wn|p_ivp' >/dev/null 2>&1
cd results
python3 - <<'PY'
import re, collections
num=r'(-?\d\.\d+e[-+]\d{2})'
pat=re.compile(r'^(p_wn|p_ivp|p_temp|p_vdd|q_up_fc|q_dn_fc) = '+num+r'\s*$', re.I)
rows=[]
for c in ('tt','ss','ff'):
    cur={}
    try: f=open(f'cp_steer_{c}.log')
    except FileNotFoundError: continue
    for line in f:
        m=pat.match(line.strip())
        if m: cur[m.group(1).lower()]=float(m.group(2))
        elif line.startswith('ROWEND'):
            if len(cur)==6: cur['c']=c; rows.append(cur)
            cur={}
print(f"rows {len(rows)}   (q_up + q_dn = 0 for an ideal pump; + = net up charge per decision pair)")
by=collections.defaultdict(list)
for r in rows: by[(r['p_wn'],r['p_ivp'])].append(r['q_up_fc']+r['q_dn_fc'])
print(" Wnsw  invP   worst |net| fC   mean net fC   n")
for k in sorted(by):
    v=by[k]
    print(f"  {k[0]:.1f}  {k[1]:.1f}    {max(abs(x) for x in v):8.2f}      {sum(v)/len(v):+8.2f}   {len(v)}")
# the corner that fails and the one that works, for the present sizing
for k in sorted(by):
    if k==(0.5,2.0):
        for r in rows:
            if (r['p_wn'],r['p_ivp'])==k and ((r['c']=='ff' and r['p_temp']==-40 and abs(r['p_vdd']-1.32)<1e-6) or (r['c']=='tt' and r['p_temp']==125 and abs(r['p_vdd']-1.2)<1e-6)):
                print(f"  as-built {r['c']} {r['p_temp']:.0f}C {r['p_vdd']:.2f}V: q_up {r['q_up_fc']:+.2f} fC, q_dn {r['q_dn_fc']:+.2f} fC, net {r['q_up_fc']+r['q_dn_fc']:+.2f} fC")
PY
echo "### CP_STEER DONE $(date +%H:%M)"
