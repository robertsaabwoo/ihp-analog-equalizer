#!/bin/bash
# CTLE AC across 27 PVT corners: 3 process x 3 temperature x 3 supply.
#
# Temperature and supply are swept inside one ngspice run with `set temp` and
# `alter`, because the VM this is developed on cannot afford 27 process starts
# (see CLAUDE.md).  The process corner has to be a separate run: it is chosen
# by a .lib line, and .lib is read at parse time, so no control-section command
# can change it.  Hence three decks, run strictly one after another.
#
# Resistor and capacitor corners are moved with the MOS corner rather than left
# at typical, so "ss" here means slow transistors AND high-resistance poly AND
# low-density metal capacitance -- the combination that costs the most gain.
set -eu
cd "$(dirname "$0")/decks"
OUT="../results"; mkdir -p "$OUT"

run_corner() {   # $1 mos section  $2 res section  $3 cap section  $4 label
    sed -e "s#cornerMOSlv.lib mos_[a-z]*#cornerMOSlv.lib $1#" \
        -e "s#cornerRES.lib  res_[a-z]*#cornerRES.lib  $2#" \
        -e "s#cornerCAP.lib  cap_[a-z]*#cornerCAP.lib  $3#" \
        ctle_ac.spice > "/tmp/ctle_ac_$4.spice"
    ../../tools/safe_ngspice.sh "/tmp/ctle_ac_$4.spice" "$OUT/ctle_ac_$4.log" 3000 1200 1200
    rm -f "/tmp/ctle_ac_$4.spice"
    echo "  $4 done"
}

run_corner mos_tt res_typ cap_typ tt
run_corner mos_ss res_wcs cap_wcs ss
run_corner mos_ff res_bcs cap_bcs ff

echo
for c in tt ss ff; do
    echo "=== corner $c ==="
    python3 ../tools/parse_sweep.py "$OUT/ctle_ac_$c.log" \
        p_temp,p_vdd,itail,voutcm,vst,vbias_v,gdc,gnyq,boost,gsys --last gsys 2>/dev/null \
      || python3 ../../tools/parse_sweep.py "$OUT/ctle_ac_$c.log" \
        p_temp,p_vdd,itail,voutcm,vst,vbias_v,gdc,gnyq,boost,gsys --last gsys
done
