#!/bin/bash
# The unattended chain: finish the isolated sweeps, pick sizes by rule, verify the chosen
# ring sizing across 27 corners, then spend the long closed-loop runs on the two corners
# that have never been tested at all.
#
#   setsid nohup sim/runners/overnight.sh > sim/results/overnight.out 2>&1 &
#
# Properties, all deliberate:
#   * strictly sequential -- one ngspice at a time (CLAUDE.md 2), everything under
#     tools/safe_ngspice.sh via the runners it calls;
#   * resumable -- every step skips itself if its own DONE marker is already present, so
#     killing this script and restarting it loses at most one step;
#   * MEASUREMENT ONLY -- it does not touch SIZING, the schematics, the netlist or any
#     cell.  Design changes wait for a human to read the numbers.
# Summary lands in sim/results/overnight_summary.txt.
set -u
cd /home/ttuser/ssh_analog/ct-worktree
R=sim/results
say() { echo "[$(date +%H:%M)] $*"; }
done_marker() { grep -q "$2" "$1" 2>/dev/null; }

say "=== overnight chain starting"

# ---- Step A: the ring grid (11/12/13 kohm x 4/6 um, vctrl 0.55-1.05) -----------------
if done_marker $R/ring_centre2.out "RING_CENTRE2 DONE"; then
  say "A: ring grid already complete, skipping"
else
  say "A: ring grid"
  sim/runners/ring_centre2.sh > $R/ring_centre2.out 2>&1 || say "A: exit $?"
fi

# ---- Step B: the pump grid, clean (amplitude bug fixed, TRAPS 2.24) ------------------
if done_marker $R/cp_charge2.out "CP_CHARGE DONE"; then
  say "B: pump grid already complete, skipping"
else
  say "B: pump grid"
  sim/runners/cp_charge.sh > $R/cp_charge2.out 2>&1 || say "B: exit $?"
fi

# ---- Step C: pick sizes by rule ------------------------------------------------------
say "C: picking sizes"
{
  echo "=== ring sizing (tools/pick_ring_sizing.py)"
  python3 tools/pick_ring_sizing.py || true
  echo
  echo "=== pump sizing (tools/pick_pump_sizing.py)"
  python3 tools/pick_pump_sizing.py || true
} > $R/overnight_choice.txt 2>&1
RL=$(grep -oP 'CHOSEN: Rload \K[0-9]+' $R/overnight_choice.txt | head -1 || true)
WT=$(grep -oP 'CHOSEN: Rload [0-9]+ ohm, Wtr \K[0-9]+' $R/overnight_choice.txt | head -1 || true)
say "C: ring choice Rload=${RL:-none} Wtr=${WT:-none}"

# ---- Step D: 27-corner bracket check for the chosen ring sizing ----------------------
if [ -n "${RL:-}" ] && [ -n "${WT:-}" ]; then
  if done_marker $R/ring_bracket.out "RING_BRACKET DONE"; then
    say "D: bracket check already complete, skipping"
  else
    say "D: 27-corner bracket check at Rload=$RL Wtr=$WT"
    python3 - "$RL" "$WT" <<'PY'
import re, sys
rl, wt = sys.argv[1], sys.argv[2]
s = open('sim/decks/vco_ct_pvt.spice').read()
s = s.replace('* vco_ct_pvt.spice --',
  f'* ring_bracket.spice -- vco_ct_pvt.spice with Rload={rl}, Wtr={wt} (chosen by\n'
  f'* tools/pick_ring_sizing.py from the ring_centre2 grid).  Asks the original question of\n'
  f'* the new sizing: is 600.6 MHz between the slowest and fastest the ring can be made at\n'
  f'* every one of the 27 corners?  Ring only.\n'
  f'* vco_ct_pvt.spice --', 1)
m = re.search(r'^\.control\nsave ', s, re.M)
assert m, "second .control block not found"
s = s[:m.start()] + f".control\nalterparam Rload = {rl}\nalterparam Wtr = {wt}\nreset\nsave " + s[m.end():]
open('sim/decks/ring_bracket.spice', 'w').write(s)
print("built ring_bracket.spice")
PY
    ( cd sim && ./run_corners.sh ring_bracket.spice ring_bracket 'p_temp|p_vdd|p_pt|fosc|swing' ) > $R/ring_bracket.out 2>&1 || say "D: exit $?"
    echo "=== RING_BRACKET DONE $(date +%H:%M)" >> $R/ring_bracket.out
  fi
else
  say "D: skipped, no ring choice"
fi

# ---- Step E: the two corners never tested closed loop, dual loop, vcoarse FREE -------
# Seeds from the centring sweeps: ss/125 C needs the trim nearly full on (vco_ct_centre_
# ss125_108.log: 602.7 MHz at vcoarse 0.15, vctrl 0.70); ss/-40 C has far more trim
# authority (700.6 MHz at vcoarse 0.15, so ~0.30 at vctrl 0.65).
for spec in "ss 125 1.08 0.70 0.15" "ss -40 1.08 0.65 0.30"; do
  set -- $spec
  tag="${1}m${3#-}"; [ "${2#-}" = "$2" ] && tag="${1}$2_$(echo "$3" | tr -d .)" || tag="${1}m${2#-}_$(echo "$3" | tr -d .)"
  if done_marker "$R/run_dual_$tag.out" "DONE"; then
    say "E: $tag already done, skipping"
  else
    say "E: dual-loop closed loop at $1/$2 C/$3 V (vctrl $4, vcoarse $5)"
    sim/runners/dual_corner.sh "$1" "$2" "$3" "$4" "$5" || say "E: $tag exit $?"
  fi
done

# ---- Step F: summary -----------------------------------------------------------------
{
  echo "overnight chain summary  $(date +%F_%H:%M)"
  echo
  echo "--- chosen sizes (measurement only; nothing was changed)"
  cat $R/overnight_choice.txt 2>/dev/null | grep -E "CHOSEN|NO CANDIDATE|as built|worst \|net\|" || echo "(none)"
  echo
  echo "--- 27-corner bracket check for the chosen ring sizing"
  grep -E "^(p_temp|fosc|swing)" $R/ring_bracket.out 2>/dev/null | head -5 || echo "(not run)"
  echo "  full table: sim/results/ring_bracket.out"
  echo
  echo "--- the two corners never tested closed loop (current design)"
  for f in $R/run_dual_*.out; do [ -f "$f" ] && { echo "  $f:"; sed 's/^/    /' "$f"; }; done
  echo
  echo "next: read sim/results/overnight_choice.txt, then apply the sizes if the bracket"
  echo "check passes -- SIZING in tools/port_from_sky130.py (Rload, Wtr) and cp_bias.inc,"
  echo "then tools/netlist.sh, pytest, and closed-loop runs at the extremes."
} > $R/overnight_summary.txt 2>&1
say "=== overnight chain finished; summary in $R/overnight_summary.txt"
echo "### OVERNIGHT DONE $(date +%H:%M)"
