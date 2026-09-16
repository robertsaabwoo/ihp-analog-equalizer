#!/bin/bash
# The remaining corner work, in one detached run: ff/-40C and tt/-40C closed loop
# (trim pinned off), then the ss/-40C coarse centring sweep.
#
#   setsid nohup sim/runners/finish_corners.sh > sim/results/finish_corners.out 2>&1 &
#
# Detached on purpose: interactive sessions have twice ended mid-transient and
# killed a 15-minute run.  Strictly sequential -- one ngspice at a time.
set -u
cd /home/ttuser/ssh_analog/ct-worktree
echo "### started $(date +%F_%H:%M)"
for spec in "ff -40 1.32" "tt -40 1.2"; do
  set -- $spec
  sim/runners/prbs_corner.sh "$1" "$2" "$3" >/dev/null 2>&1
  tag="${1}m${2#-}_$(echo "$3" | tr -d .)"
  echo "===== $spec"
  cat "sim/results/run_prbs_$tag.out" 2>/dev/null || echo "no output"
done
( cd sim/decks && ../../tools/safe_ngspice.sh vco_ct_centre_ssm40_108.spice \
    ../results/vco_ct_centre_ssm40_108.log 2500 2400 2000 ) >/dev/null 2>&1
echo "===== ss -40 centring"
python3 - sim/results/vco_ct_centre_ssm40_108.log <<'PY'
import re, sys
num = r'(-?\d\.\d+e[-+]\d{2})'
pend = {}
for line in open(sys.argv[1]):
    m = re.match(r'^(p_vcrs|p_vctrl|fosc|swing) = ' + num + r'\s*$', line.strip())
    if m:
        pend[m.group(1)] = float(m.group(2))
        if len(pend) == 4:
            print(f"vcoarse {pend['p_vcrs']:.2f} vctrl {pend['p_vctrl']:.2f}  "
                  f"{pend['fosc']/1e6:7.1f} MHz  swing {pend['swing']:.3f}")
            pend = {}
PY
echo "### ALL DONE $(date +%F_%H:%M)"
