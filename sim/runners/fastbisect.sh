#!/bin/bash
set -eu
cd /home/ttuser/ssh_analog/ct-worktree
SRC=/home/ttuser/ssh_analog/ttsky-analog-equalizer/xschem
setring () {
python3 - "$1" "$2" <<'PY'
import re, sys
p='tools/port_from_sky130.py'; s=open(p).read()
for m in ("M1","M4"):
    s=re.sub(rf'\("ring_inverter", "{m}"\): \{{"W": 3, "L": [0-9.]+\}}',
             f'("ring_inverter", "{m}"): {{"W": 3, "L": {sys.argv[1]}}}', s)
for r in ("R1","R2"):
    s=re.sub(rf'\("ring_inverter", "{r}"\): \{{"R": \d+\}}',
             f'("ring_inverter", "{r}"): {{"R": {sys.argv[2]}}}', s)
open(p,'w').write(s)
PY
python3 tools/port_from_sky130.py --src "$SRC" --dst xschem >/dev/null 2>&1
./tools/netlist.sh >/dev/null 2>&1
}
trim () {   # $1 = on|off
  if [ "$1" = off ]; then sed -i 's|^    "ring_inverter.sch": add_coarse_trim,|#   "ring_inverter.sch": add_coarse_trim,|' tools/port_from_sky130.py
  else sed -i 's|^#   "ring_inverter.sch": add_coarse_trim,|    "ring_inverter.sch": add_coarse_trim,|' tools/port_from_sky130.py; fi
}
run () {
  sed -i "s/^\.ic v(x1\.x2\.vctrl)=.*/.ic v(x1.x2.vctrl)=$2/" sim/decks/pd_bisect.spice
  ( cd sim/decks && ../../tools/safe_ngspice.sh pd_bisect.spice "../results/pdb_$1.log" 2500 900 2000 ) >/dev/null 2>&1
  L=sim/results/pdb_$1.log
  printf '%-22s up=%-8s dn=%-8s bias=%-8s ringpp=%-8s vctrl %s -> %s  drift=%s mV/ns\n' "$1" \
    "$(grep -m1 '^up_duty = '$'\t*' $L|awk '{print $3}')" \
    "$(grep -m1 '^dn_duty = ' $L|awk '{print $3}')" \
    "$(grep -m1 '^bias_pct = ' $L|awk '{print $3}')" \
    "$(grep -m1 '^ring_pp = ' $L|awk '{print $3}')" \
    "$(grep -m1 '^vc_1 = ' $L|awk '{print $3}')" \
    "$(grep -m1 '^vc_2 = ' $L|awk '{print $3}')" \
    "$(grep -m1 '^drift_mV_ns = ' $L|awk '{print $3}')"
}
trim on ; setring 0.9 7355 ; run B_mainring_trimON   0.62
          setring 0.7 7355 ; run C_shortpair_only    0.55
          setring 0.9 9000 ; run D_bigload_only      0.62
trim off; setring 0.9 7355 ; run E_mainring_trimOFF  0.62
          setring 0.7 9000 ; run F_branch_trimOFF    0.55
trim on ; setring 0.7 9000
echo "=== FAST BISECT DONE ==="
