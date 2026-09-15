#!/bin/bash
# Ground truth at the worst pump-mismatch corner: does PRBS7 still lock at
# ff / 125 C / 1.32 V with the 1.8 um trim, where the DC sweep says +72 %?
set -u
cd /home/ttuser/ssh_analog/ct-worktree
L=sim/results/vco_ct_seed_ff125.log
until grep -q "ngspice-42 done\|exit rc=" "$L" 2>/dev/null; do sleep 30; done
SEED=$(python3 - "$L" <<'PY'
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
echo "### seed at ff/125C/1.32V (trim off): ${SEED:-NOT FOUND}"
[ -n "$SEED" ] || { echo "600.6 MHz not bracketed at this corner -- cannot seed"; echo "=== FF125 DONE ==="; exit 0; }
python3 - "$SEED" <<'PY'
import sys, re
s=open('sim/decks/e2e_prbs.spice').read()
subs=[("cornerMOSlv.lib mos_tt","cornerMOSlv.lib mos_ff"),
      ("VDD Vdd 0 1.2\n","VDD Vdd 0 1.32\n"),
      ("Vcrs vcoarse! 0 1.20","Vcrs vcoarse! 0 1.32")]
for a,b in subs:
    assert a in s, f"missing: {a!r}"
    s=s.replace(a,b)
s=re.sub(r"^\.ic v\(x1\.x2\.vctrl\)=.*$", f".ic v(x1.x2.vctrl)={sys.argv[1]}", s, count=1, flags=re.M)
s=s.replace(".global sub!", ".temp 125\n.global sub!",1)
open('sim/decks/e2e_prbs_ff125.spice','w').write(s)
PY
( cd sim/decks && ../../tools/safe_ngspice.sh e2e_prbs_ff125.spice ../results/e2e_prbs_ff125.log 2500 5400 2000 ) >/dev/null 2>&1
grep -E "^(f_long|f_err|vctrl_s1|vctrl_s2|vctrl_s3|vctrl_ripp|rclk_swing) = " sim/results/e2e_prbs_ff125.log
grep -m3 -iE "failed|error" sim/results/e2e_prbs_ff125.log || true
echo "=== FF125 DONE ==="
