#!/bin/bash
#   setsid nohup sim/runners/pd_trim.sh > sim/results/pd_trim.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim/decks
for d in pd_trim_ffm40 pd_trim_tt125; do
  ../../tools/safe_ngspice.sh $d.spice ../results/$d.log 2500 5400 2000 >/dev/null 2>&1
  echo "=== $d"
  grep -c "redefinition of .subckt cp_bias" ../results/$d.log | sed 's/^/  cp_bias overrides seen: /'
  python3 - ../results/$d.log <<'PY'
import re, sys, collections
num=r'(-?\d\.\d+e[-+]\d{2})'
pat=re.compile(r'^(p_w2|p_ph|i_net_na) = '+num+r'\s*$', re.I)
cur={}; by=collections.defaultdict(list)
for line in open(sys.argv[1]):
    m=pat.match(line.strip())
    if m: cur[m.group(1).lower()]=float(m.group(2))
    elif line.startswith('ROWEND'):
        if len(cur)==3: by[cur['p_w2']].append(cur['i_net_na'])
        cur={}
for w in sorted(by):
    v=by[w]
    print(f"  XMP2 {w:.2f} um  n={len(v)}  phase-average {sum(v)/len(v):+7.1f} nA   (min {min(v):+7.1f}, max {max(v):+7.1f})")
PY
done
echo "### PD_TRIM DONE $(date +%H:%M)"
