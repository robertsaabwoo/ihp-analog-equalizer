#!/bin/bash
# Two full closed-loop runs, the only measurement that actually answers this.
#
#   F : branch ring (0.7 um / 9000 ohm), trim legs REMOVED, coarse loop present
#       -> if this locks, the trim legs are the cause and the corner work
#          (which is what the 0.7/9000 ring buys) is safe.
#   E : main's ring (0.9 / 7355), trim legs removed -- a control that should
#       reproduce main's lock exactly.  If E does not lock, something about the
#       branch *other* than the ring and the trim is at fault, and the whole
#       comparison is suspect.
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
trim () { if [ "$1" = off ]; then
   sed -i 's|^    "ring_inverter.sch": add_coarse_trim,|#   "ring_inverter.sch": add_coarse_trim,|' tools/port_from_sky130.py
 else sed -i 's|^#   "ring_inverter.sch": add_coarse_trim,|    "ring_inverter.sch": add_coarse_trim,|' tools/port_from_sky130.py; fi }
run () {
  sed -i "s/^\.ic v(x1\.x2\.vctrl)=.*/.ic v(x1.x2.vctrl)=$2/" sim/decks/e2e_lock.spice
  ( cd sim/decks && ../../tools/safe_ngspice.sh e2e_lock.spice "../results/dec_$1.log" 2500 3600 2000 ) >/dev/null 2>&1
  L=sim/results/dec_$1.log
  printf '%-22s f=%-11s err=%-10s vctrl=%-8s e1=%-8s e2=%-8s ripple=%-9s clk=%s\n' "$1" \
   "$(grep -m1 '^f_long = '     $L|awk '{print $3}')" "$(grep -m1 '^f_err = '  $L|awk '{print $3}')" \
   "$(grep -m1 '^vctrl_lock = ' $L|awk '{print $3}')" "$(grep -m1 '^vctrl_e1 = '$L|awk '{print $3}')" \
   "$(grep -m1 '^vctrl_e2 = '   $L|awk '{print $3}')" "$(grep -m1 '^vctrl_ripp = '$L|awk '{print $3}')" \
   "$(grep -m1 '^rclk_swing = ' $L|awk '{print $3}')"
}
trim off
echo "--- F: branch ring 0.7/9000, NO trim legs"; setring 0.7 9000; run F_branchring_notrim 0.55
echo "--- E: main ring 0.9/7355, NO trim legs (control, should lock)"; setring 0.9 7355; run E_mainring_notrim 0.62
trim on; setring 0.7 9000
echo "=== DECISIVE DONE (branch config restored) ==="
