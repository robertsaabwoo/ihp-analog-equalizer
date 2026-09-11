#!/bin/bash
# One run per process corner: a .lib section is chosen at parse time, so unlike
# temperature and supply it cannot be swept inside a single ngspice run.
# Same shape as sim/run_ctle_ac.sh.
set -eu
cd "$(dirname "$0")/decks"
for c in tt ss ff; do
  sed -i "s#cornerMOSlv.lib mos_..#cornerMOSlv.lib mos_$c#" vco_ct_pvt.spice
  ../../tools/safe_ngspice.sh vco_ct_pvt.spice "../results/vco_ctpvt_$c.log" 2500 2400 2000
  echo "--- $c"
  grep -E "^(p_temp|p_vdd|p_pt|fosc|swing) " "../results/vco_ctpvt_$c.log" \
    | awk '{print $1,$3}' | paste - - - - - | column -t
done
sed -i "s#cornerMOSlv.lib mos_..#cornerMOSlv.lib mos_tt#" vco_ct_pvt.spice
echo "=== CT PVT DONE ==="
