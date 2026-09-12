#!/bin/bash
# Unattended: widen the seed sweep, then run the two closed-loop tests that
# separate the shorter input pair from the bigger load, each seeded at its own
# ring's lock point.
set -u
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

echo "### widening the seed sweep"
( cd sim/decks && ../../tools/safe_ngspice.sh ring_seed.spice ../results/ring_seed.log 2500 3000 2000 ) >/dev/null 2>&1
echo "### seeds"; python3 tools/pick_seed.py

trim off
for cfg in "0.7 7355" "0.9 9000"; do
  set -- $cfg; lin=$1; rl=$2
  seed=$(python3 tools/pick_seed.py "$lin" "$rl")
  if [ -z "$seed" ]; then echo "### Lin=$lin R=$rl : baud rate not reachable, skipping"; continue; fi
  echo "### closed loop: Lin=$lin Rload=$rl seeded at $seed"
  setring "$lin" "$rl"
  sed -i "s/^\.ic v(x1\.x2\.vctrl)=.*/.ic v(x1.x2.vctrl)=$seed/" sim/decks/e2e_lock.spice
  tag="auto_${lin}_${rl}"
  ( cd sim/decks && ../../tools/safe_ngspice.sh e2e_lock.spice "../results/$tag.log" 2500 3600 2000 ) >/dev/null 2>&1
  L=sim/results/$tag.log
  printf '%-18s f=%-11s err=%-10s vctrl=%-8s e2=%-8s ripple=%-9s clk=%s\n' "$tag" \
   "$(grep -m1 '^f_long = '     $L|awk '{print $3}')" "$(grep -m1 '^f_err = '  $L|awk '{print $3}')" \
   "$(grep -m1 '^vctrl_lock = ' $L|awk '{print $3}')" "$(grep -m1 '^vctrl_e2 = '$L|awk '{print $3}')" \
   "$(grep -m1 '^vctrl_ripp = ' $L|awk '{print $3}')" "$(grep -m1 '^rclk_swing = ' $L|awk '{print $3}')"
done
trim on; setring 0.7 9000
echo "=== AUTO DONE ==="
