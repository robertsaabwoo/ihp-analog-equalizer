#!/bin/bash
# Ring-VCO tuning range across PVT: 3 process x 3 temperature x 3 supply, with
# a vctrl sweep inside each.  The process corner is a .lib line, read at parse
# time, so it needs one ngspice run each; temperature and supply are swept
# inside the run with `set temp` and `alter`.  Strictly sequential, and each
# run is wrapped in the memory/wall-clock guard -- see CLAUDE.md.
#
# This is the measurement that decides whether the receiver works: a bang-bang
# phase detector has no frequency acquisition, so a corner at which the ring
# cannot reach 600.6 MHz is a corner at which the loop never locks.
set -eu
cd "$(dirname "$0")/decks"
OUT="../results"; mkdir -p "$OUT"
run() {
    sed -e "s#cornerMOSlv.lib mos_[a-z]*#cornerMOSlv.lib $1#" \
        -e "s#cornerRES.lib  res_[a-z]*#cornerRES.lib  $2#" \
        -e "s#cornerCAP.lib  cap_[a-z]*#cornerCAP.lib  $3#" \
        vco_pvt_fast.spice > "/tmp/vco_pvt_$4.spice"
    ../../tools/safe_ngspice.sh "/tmp/vco_pvt_$4.spice" "$OUT/vco_pvtf_$4.log" 3000 2400 1200
    rm -f "/tmp/vco_pvt_$4.spice"
    echo "  corner $4 done"
}
run mos_tt res_typ cap_typ tt
run mos_ss res_wcs cap_wcs ss
run mos_ff res_bcs cap_bcs ff
