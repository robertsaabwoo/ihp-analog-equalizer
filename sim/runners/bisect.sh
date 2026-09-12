#!/bin/bash
# Bisect the branch's lock failure.  Four things changed at once relative to
# main: input pair 0.9 -> 0.7 um, ring load 7355 -> 9000 ohm, a pMOS trim leg
# across each load resistor, and the coarse loop instantiated in CDR.  Each run
# changes ONE of them back.
set -eu
cd /home/ttuser/ssh_analog/ct-worktree
SRC=/home/ttuser/ssh_analog/ttsky-analog-equalizer/xschem

setring () {   # $1 = Lin um, $2 = Rload ohm
python3 - "$1" "$2" <<'PY'
import re, sys
p='tools/port_from_sky130.py'; s=open(p).read()
s=re.sub(r'\("ring_inverter", "M1"\): \{"W": 3, "L": [0-9.]+\}',
         f'("ring_inverter", "M1"): {{"W": 3, "L": {sys.argv[1]}}}', s)
s=re.sub(r'\("ring_inverter", "M4"\): \{"W": 3, "L": [0-9.]+\}',
         f'("ring_inverter", "M4"): {{"W": 3, "L": {sys.argv[1]}}}', s)
s=re.sub(r'\("ring_inverter", "R1"\): \{"R": \d+\}',
         f'("ring_inverter", "R1"): {{"R": {sys.argv[2]}}}', s)
s=re.sub(r'\("ring_inverter", "R2"\): \{"R": \d+\}',
         f'("ring_inverter", "R2"): {{"R": {sys.argv[2]}}}', s)
open(p,'w').write(s)
PY
python3 tools/port_from_sky130.py --src "$SRC" --dst xschem >/dev/null 2>&1
./tools/netlist.sh >/dev/null 2>&1
}

run () {  # $1 = tag, $2 = vctrl seed
  sed -i "s/^\.ic v(x1\.x2\.vctrl)=.*/.ic v(x1.x2.vctrl)=$2/" sim/decks/e2e_lock.spice
  ( cd sim/decks && ../../tools/safe_ngspice.sh e2e_lock.spice "../results/bisect_$1.log" 2500 3600 2000 )
  L=sim/results/bisect_$1.log
  printf '%-26s f=%-12s err=%-10s vctrl=%-9s e1=%-9s e2=%-9s ripple=%s\n' "$1" \
    "$(grep -m1 '^f_long = '     $L|awk '{print $3}')" \
    "$(grep -m1 '^f_err = '      $L|awk '{print $3}')" \
    "$(grep -m1 '^vctrl_lock = ' $L|awk '{print $3}')" \
    "$(grep -m1 '^vctrl_e1 = '   $L|awk '{print $3}')" \
    "$(grep -m1 '^vctrl_e2 = '   $L|awk '{print $3}')" \
    "$(grep -m1 '^vctrl_ripp = ' $L|awk '{print $3}')"
}

echo "=== A: branch as-is (Lin 0.7, R 9000, trim legs, coarse loop) ==="
setring 0.7 9000 ; run A_branch_asis 0.55

echo "=== B: ring back to main's sizing, everything else still added ==="
setring 0.9 7355 ; run B_mainring 0.62

echo "=== C: main's load, branch's pair ==="
setring 0.7 7355 ; run C_shortpair_only 0.55

echo "=== D: main's pair, branch's load ==="
setring 0.9 9000 ; run D_bigload_only 0.62

setring 0.7 9000
echo "=== BISECT DONE (branch sizing restored) ==="
