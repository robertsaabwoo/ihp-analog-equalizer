#!/bin/bash
# Run one deck once per process corner.
#
#   sim/run_corners.sh <deck.spice> <result-prefix> [grep-keys]
#
# A .lib section is chosen at parse time, so unlike temperature and supply the
# process corner cannot be swept inside a single ngspice run -- see CLAUDE.md
# section 2.  This edits the cornerMOSlv line in place, runs, and puts it back.
set -eu
D="$1"; P="$2"; K="${3:-p_temp|p_vdd|p_vctrl|fosc|swing}"
cd "$(dirname "$0")/decks"
for c in tt ss ff; do
  sed -i "s#cornerMOSlv.lib mos_..#cornerMOSlv.lib mos_$c#" "$D"
  ../../tools/safe_ngspice.sh "$D" "../results/${P}_$c.log" 2500 2400 2000
  echo "--- $c"
  grep -E "^($K) " "../results/${P}_$c.log" | awk '{print $1,$3}' \
    | paste $(printf -- '- %.0s' $(seq 1 $(echo "$K" | tr '|' '\n' | wc -l))) \
    | column -t
done
sed -i "s#cornerMOSlv.lib mos_..#cornerMOSlv.lib mos_tt#" "$D"
echo "=== $P DONE ==="
