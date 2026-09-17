#!/bin/bash
#   setsid nohup sim/runners/pd_phase.sh > sim/results/pd_phase.out 2>&1 &
set -u
cd /home/ttuser/ssh_analog/ct-worktree/sim/decks
for d in pd_phase_tt125 pd_phase_ffm40; do
  ../../tools/safe_ngspice.sh $d.spice ../results/$d.log 2500 5400 2000 >/dev/null 2>&1
  echo "=== $d  (net nA into vctrl vs clock phase in UI; a zero crossing = a lock phase)"
  grep -c "redefinition of .subckt ring_oscillator" ../results/$d.log | sed 's/^/  ring overrides seen: /'
  python3 - ../results/$d.log <<'PY'
import re, sys
num=r'(-?\d\.\d+e[-+]\d{2})'
pat=re.compile(r'^(p_ph|i_net_na) = '+num+r'\s*$', re.I)
cur={}
for line in open(sys.argv[1]):
    m=pat.match(line.strip())
    if m: cur[m.group(1).lower()]=float(m.group(2))
    elif line.startswith('ROWEND'):
        if len(cur)==2: print(f"  phase {cur['p_ph']:.1f} UI   net {cur['i_net_na']:+8.1f} nA")
        cur={}
PY
done
echo "### PD_PHASE DONE $(date +%H:%M)"
