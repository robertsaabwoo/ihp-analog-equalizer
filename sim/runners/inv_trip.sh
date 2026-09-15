#!/bin/bash
# inverter_buffer trip point across corners -> sim/results/inv_trip.out
cd "$(dirname "$0")/../decks" || exit 1
out=../results/inv_trip.out; : > $out
set -- "tt 27 1.20" "ff 125 1.32" "ff -40 1.32" "ss -40 1.08" "ss 125 1.08" "tt 27 1.32" "ff 27 1.20"
i=0
for c in "$@"; do
  ../../tools/safe_ngspice.sh inv_trip_$i.spice ../results/inv_trip_$i.log 300 2400 2000 >/dev/null 2>&1
  echo "$c  $(grep -E '^trip *= ' ../results/inv_trip_$i.log | tail -1)" >> $out
  i=$((i+1))
done
echo DONE >> $out
