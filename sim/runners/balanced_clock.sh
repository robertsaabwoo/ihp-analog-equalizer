#!/bin/bash
#   setsid nohup sim/runners/balanced_clock.sh > sim/results/balanced_clock.out 2>&1 &
# Verify the balanced clock phases (rclk- from the ring's other output instead of by
# inverting rclk+).  Target: the detector's phase-average, +77.1 nA at ff/-40C and +10.4 nA
# at tt/125C before the change (pd_phase_*.log), should fall toward zero -- that average is
# what an unlocked loop integrates, and it is the term no ring or filter change touched.
set -u
cd /home/ttuser/ssh_analog/ct-worktree
say() { echo "[$(date +%H:%M)] $*"; }
for i in $(seq 1 120); do ps -eo args | grep -q "[n]gspice -b" || break; [ $((i%10)) -eq 1 ] && say "waiting for the simulator"; sleep 30; done

say "phase-average at ff/-40C (was +77.1 nA)"
( cd sim/decks && ../../tools/safe_ngspice.sh pd_phase_ffm40.spice ../results/pd_phase_ffm40_bal.log 2500 5400 2000 ) >/dev/null 2>&1
python3 - sim/results/pd_phase_ffm40_bal.log <<'PY'
import re, sys
num=r'(-?\d\.\d+e[-+]\d{2})'
pat=re.compile(r'^(p_ph|i_net_na) = '+num+r'\s*$', re.I)
cur={}; vals=[]
for line in open(sys.argv[1]):
    m=pat.match(line.strip())
    if m: cur[m.group(1).lower()]=float(m.group(2))
    elif line.startswith('ROWEND'):
        if len(cur)==2:
            print(f"  phase {cur['p_ph']:.1f} UI  net {cur['i_net_na']:+8.1f} nA"); vals.append(cur['i_net_na'])
        cur={}
if vals: print(f"  PHASE-AVERAGE {sum(vals)/len(vals):+.1f} nA over {len(vals)} phases   (was +77.1)")
PY

say "closed loop at ff/-40C/1.32V, trim pinned, self-seeded"
sim/runners/prbs_corner.sh ff -40 1.32 >/dev/null 2>&1
cat sim/results/run_prbs_ffm40_132.out 2>/dev/null

say "hot regression tt/125C/1.2V"
sim/runners/prbs_corner.sh tt 125 1.2 >/dev/null 2>&1
cat sim/results/run_prbs_tt125_12.out 2>/dev/null

say "nominal regression"
sim/runners/prbs_corner.sh tt 27 1.2 >/dev/null 2>&1
cat sim/results/run_prbs_tt27_12.out 2>/dev/null
echo "### BALANCED DONE $(date +%H:%M)"
