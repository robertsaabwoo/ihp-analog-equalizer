#!/bin/bash
# Dual-loop closed loop (vcoarse FREE) at one PVT corner, on e2e_dual.spice's 0101
# stimulus (PULSE, not PRBS7), seeded from a coarse centring sweep (vco_ct_centre_<tag>.spice).
#
#   sim/runners/dual_corner.sh <tt|ss|ff> <temp_C> <vdd> <vctrl_seed> <vcoarse_seed> [--gen-only]
#
# For corners where the trim-off ring cannot reach 600.6 MHz (prbs_corner.sh
# reports "not bracketed"), so the fine loop alone cannot be tested there.  vcoarse
# is a state variable of the simulation: it is seeded, not pinned, and
# vcrs_walk_mV says how far the coarse loop moved it.
# Results: sim/results/run_dual_<tag>.out
set -eu
C="$1"; T="$2"; V="$3"; VC="$4"; VCRS="$5"; GEN="${6:-}"
TAG="${C}$(echo "$T" | tr -d -)_$(echo "$V" | tr -d .)"
[ "${T#-}" != "$T" ] && TAG="${C}m${T#-}_$(echo "$V" | tr -d .)"
cd /home/ttuser/ssh_analog/ct-worktree
python3 - "$C" "$T" "$V" "$VC" "$VCRS" "$TAG" <<'PY'
import re, sys
c, t, v, vc, vcrs, tag = sys.argv[1:]
s = open('sim/decks/e2e_dual.spice').read()
subs = [("cornerMOSlv.lib mos_tt", f"cornerMOSlv.lib mos_{c}"),
        ("VDD Vdd 0 1.2\n", f"VDD Vdd 0 {v}\n")]
for a, b in subs:
    assert s.count(a) == 1, f"e2e_dual.spice: {a!r} x{s.count(a)}"
    s = s.replace(a, b)
assert '.temp' not in s
s = s.replace(".global sub! vcoarse!", f".temp {t}\n.global sub! vcoarse!", 1)
n1 = len(re.findall(r'^\.ic v\(x1\.x2\.vctrl\)=\S+', s, re.M))
n2 = len(re.findall(r'^\.ic v\(vcoarse!\)=\S+', s, re.M))
assert n1 == 1 and n2 == 1, (n1, n2)
s = re.sub(r'^\.ic v\(x1\.x2\.vctrl\)=\S+', f'.ic v(x1.x2.vctrl)={vc}', s, flags=re.M)
s = re.sub(r'^\.ic v\(vcoarse!\)=\S+', f'.ic v(vcoarse!)={vcrs}', s, flags=re.M)
s = f"* e2e_dual_{tag}.spice -- e2e_dual.spice at {c}/{t} C/{v} V, vctrl seed {vc}, vcoarse seed {vcrs} (vcoarse free).\n" + s
open(f'sim/decks/e2e_dual_{tag}.spice', 'w').write(s)
print(f"generated e2e_dual_{tag}.spice")
PY
[ "$GEN" = "--gen-only" ] && exit 0
OUT=sim/results/run_dual_$TAG.out
echo "### $TAG dual loop, vctrl seed $VC, vcoarse seed $VCRS" > "$OUT"
( cd sim/decks && ../../tools/safe_ngspice.sh e2e_dual_$TAG.spice ../results/e2e_dual_$TAG.log 2500 5400 2000 ) >/dev/null 2>&1 || true
grep -iE "^(f_long|f_err|vctrl_lock|vctrl_ripp|rclk_swing|vcrs_e1|vcrs_e2|vcrs_walk_mv|vcrs_creep_mv|vctrl_e1|vctrl_e2) = " sim/results/e2e_dual_$TAG.log >> "$OUT" || true
grep -m3 -iE "failed|error" sim/results/e2e_dual_$TAG.log >> "$OUT" || true
echo "=== $TAG DONE ===" >> "$OUT"
