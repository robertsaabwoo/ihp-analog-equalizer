#!/bin/bash
# PRBS7 closed loop at one PVT corner, self-seeded, with vcoarse! pinned at VDD
# (trim off) so the fine loop is measured on its own.
#
#   sim/runners/prbs_corner.sh <tt|ss|ff> <temp_C> <vdd> [--gen-only]
#
# Step 1 sweeps the trimmed ring at that corner (vco_ct_seed_<tag>.spice, from
# vco_ct_seed_ff125.spice) and interpolates the vctrl that gives 600.6 MHz.
# Step 2 derives e2e_prbs_<tag>.spice from e2e_prbs.spice with that seed.  A
# closed-loop deck seeded off its own ring's lock point measures the seed
# (tools/pick_seed.py header).  Results: sim/results/run_prbs_<tag>.out
set -eu
C="$1"; T="$2"; V="$3"; GEN="${4:-}"
TAG="${C}$(echo "$T" | tr -d -)_$(echo "$V" | tr -d .)"
[ "${T#-}" != "$T" ] && TAG="${C}m${T#-}_$(echo "$V" | tr -d .)"
ROOT=/home/ttuser/ssh_analog/ct-worktree
cd "$ROOT"
OUT=sim/results/run_prbs_$TAG.out
python3 - "$C" "$T" "$V" "$TAG" <<'PY'
import re, sys
c, t, v, tag = sys.argv[1:]
s = open('sim/decks/vco_ct_seed_ff125.spice').read()
assert s.count('cornerMOSlv.lib mos_ff') == 1
s = s.replace('cornerMOSlv.lib mos_ff', f'cornerMOSlv.lib mos_{c}')
assert s.count('VDD VDD 0 1.32') == 1 and s.count('alter Vcrs dc = 1.32') == 1
s = s.replace('VDD VDD 0 1.32', f'VDD VDD 0 {v}').replace('alter Vcrs dc = 1.32', f'alter Vcrs dc = {v}')
n = len(re.findall(r'^\.temp\s+\S+', s, re.M)) + len(re.findall(r'set temp\s*=\s*\S+', s))
assert n == 1, f"seed deck: {n} temperature settings"
s = re.sub(r'^\.temp\s+\S+', f'.temp {t}', s, flags=re.M)
s = re.sub(r'set temp\s*=\s*\S+', f'set temp = {t}', s)
open(f'sim/decks/vco_ct_seed_{tag}.spice', 'w').write(s)
e = open('sim/decks/e2e_prbs.spice').read()
for a, b in (("cornerMOSlv.lib mos_tt", f"cornerMOSlv.lib mos_{c}"),
             ("VDD Vdd 0 1.2\n", f"VDD Vdd 0 {v}\n"),
             ("Vcrs vcoarse! 0 1.20", f"Vcrs vcoarse! 0 {v}")):
    assert e.count(a) == 1, f"e2e_prbs.spice: {a!r}"
    e = e.replace(a, b)
assert '.temp' not in e
e = e.replace(".global sub!", f".temp {t}\n.global sub!", 1)
open(f'sim/decks/e2e_prbs_{tag}.tmpl', 'w').write(e)
print(f"generated vco_ct_seed_{tag}.spice and e2e_prbs_{tag}.tmpl")
PY
[ "$GEN" = "--gen-only" ] && exit 0
: > "$OUT"
( cd sim/decks && ../../tools/safe_ngspice.sh vco_ct_seed_$TAG.spice ../results/vco_ct_seed_$TAG.log 2500 2400 2000 ) >/dev/null 2>&1 || true
SEED=$(python3 - sim/results/vco_ct_seed_$TAG.log <<'PY'
import re, sys
pts=[]; pend={}
for line in open(sys.argv[1]):
    m=re.match(r"^(p_vctrl|fosc|swing) = ([-+0-9.eE]+)",line)
    if m:
        pend[m.group(1)]=float(m.group(2))
        if len(pend)==3: pts.append((pend['p_vctrl'],pend['fosc']/1e6,pend['swing'])); pend={}
g=sorted((v,f) for v,f,s in pts if s>=0.15)
for (v1,f1),(v2,f2) in zip(g,g[1:]):
    if min(f1,f2)<=600.6<=max(f1,f2):
        print(f"{v1+(600.6-f1)*(v2-v1)/(f2-f1):.3f}"); break
PY
)
echo "### $TAG seed (trim off): ${SEED:-NOT FOUND}" >> "$OUT"
if [ -z "$SEED" ]; then echo "600.6 MHz not bracketed with trim off -- not run" >> "$OUT"; echo "=== $TAG DONE ===" >> "$OUT"; exit 0; fi
sed -E "s/^\.ic v\(x1\.x2\.vctrl\)=.*$/.ic v(x1.x2.vctrl)=$SEED/" sim/decks/e2e_prbs_$TAG.tmpl > sim/decks/e2e_prbs_$TAG.spice
( cd sim/decks && ../../tools/safe_ngspice.sh e2e_prbs_$TAG.spice ../results/e2e_prbs_$TAG.log 2500 5400 2000 ) >/dev/null 2>&1 || true
grep -E "^(f_long|f_err|vctrl_s1|vctrl_s2|vctrl_s3|vctrl_ripp|rclk_swing) = " sim/results/e2e_prbs_$TAG.log >> "$OUT" || true
grep -m3 -iE "failed|error" sim/results/e2e_prbs_$TAG.log >> "$OUT" || true
echo "=== $TAG DONE ===" >> "$OUT"
