## 2026-09-17 evening: the fast-cold corner LOCKS

**ff/-40 C/1.32 V: 600.621 MHz, +0.0034 %** (`run_dual_ffm40_132.out`), coarse rail settling
at 0.985 V -- the slow leg engaged.  That corner had never locked in any configuration.

What made it possible: the **bidirectional coarse trim**.  An nMOS-switched cap_cmomf on each
ring node, gated by the same `vcoarse!` rail but conducting when the rail is HIGH, i.e. when
the pMOS speed-up legs are off.  One rail now spans slow to fast, and `ring_vcrs_*.log` shows
the rail can place the loaded ring on 600.6 MHz at **26 of 27 corners at vctrl 0.60**, the
27th (ss/125 C/1.08 V) at vctrl 0.85.  Before it, the fast-cold corner had no setting at all.
Switch 1 um, cap 1 um square; the switch loads the ring node even when off, which at 2 um
cost ss/125 C/1.08 V ~8 % of its reach.

Also in: balanced detector clock phases (rclk- from the ring's other output through its own
sb_inverter + inverter_buffer, not by inverting rclk+), which halved the unlocked drift
(+77.1 -> +41.8 nA) and fixed tt/-40 C's approach-from-below.

**Open: the other corners need their seeds refined.** With the trim pinned no longer
describing the design, every run is dual-loop and needs a per-corner starting rail.  Seeds
taken from the ring sweep are close but not exact, and where they are off the loop starts
off-frequency and drifts before it can capture -- e.g. tt/125 C ran at 580 MHz with the rail
at 0.537 V, so that rail wants to be ~0.1 V lower.  `sim/runners/seed_refine.sh` iterates:
run, read the error, correct the rail by the measured sensitivity, re-run.

## Baseline after the 2026-09-17 changes -- read this first

Design now: folded coarse pull-up + self-biased clock stage (`sb_inverter`) + pump bias from
`ibias` (`cp_bias`) + **balanced clock phases** (rclk- from the ring's other output through
its own sb_inverter and inverter_buffer, replacing the single_inverter).  The ripple fixes
(half pump current, 3x filter caps) and the 7.5 kohm filter resistor were tried and
**reverted** -- they fixed nothing and cost tt/125 C its lock by slowing acquisition ~5x.

PRBS7, trim pinned, self-seeded (`baseline_all.out`):

| corner | f | f_err | verdict |
|---|---|---|---|
| tt 27 C 1.2 V | 600.603 MHz | +0.0005 % | **locks** |
| tt 125 C 1.2 V | 600.653 | +0.0089 % | **locks** |
| ff 125 C 1.32 V | 600.630 | +0.0050 % | **locks** |
| tt -40 C 1.2 V | 600.621 | +0.0035 % | **locks, from its own lock point** (before the balanced clock it only locked when seeded from above) |
| **ff -40 C 1.32 V** | 685.6 | +14.15 % | **no lock** |

0101 with the coarse loop free: ss/125 C/1.08 V 571.4 MHz and ss/-40 C/1.08 V 561.9 MHz --
**both still acquiring, not settled**: the coarse search runs at ~19 mV/us over a ~1 V range,
so it needs ~50 us against a 2.5 us window, and at ss/-40 C the search had wrapped (vcoarse
back at 1.06 V) when the window closed.  Judge these two only with a long run or a seed that
needs no search.

**The one real failure is ff/-40 C/1.32 V**, and the loaded ring data says why: with the trim
off the ring is at 654 MHz at vctrl 0.60 (`ring_loaded_ff.log`), so the baud rate sits at
vctrl ~0.55 on a ~1100 MHz/V slope. The trim only speeds the ring up, so the coarse loop
cannot move that corner off the steep part.

## Running unattended (started 2026-09-17 02:07) -- read this first

`sim/runners/overnight.sh` (detached, sequential, resumable; **measurement only, it changes
no design file**), then `sim/runners/after_overnight.sh`. Watch:

    tail -f sim/results/overnight.out
    cat sim/results/overnight_summary.txt     # written at the end
    cat sim/results/overnight_choice.txt      # the sizes the rules picked

Steps: finish the ring grid (11/12/13 kohm x trim 4/6 um, vctrl 0.55-1.05 V at ff/-40 C and
ss/125 C) -> the clean pump charge grid -> `tools/pick_ring_sizing.py` and
`tools/pick_pump_sizing.py` -> a 27-corner bracket check of the chosen ring sizing
(`ring_bracket.spice`) -> **the two corners never tested closed loop** (ss/125 C/1.08 V and
ss/-40 C/1.08 V, dual loop with vcoarse free) -> summary. Then the current-steering pump
measurement (`cp_steer.spice`) for comparison against the switched one.

**To apply the result afterwards** (a human decision, not the script's): edit `SIZING` in
`tools/port_from_sky130.py` (`("ring_inverter","R1")` Rload and `TRIM_W`), re-run
`tools/port_from_sky130.py --src ... --dst xschem --cells ring_inverter`, then
`tools/netlist.sh`, `python3 -m pytest -q test/`, and the closed-loop runs at the extremes.

## Where the design stands (2026-09-17 02:10)

Adopted on this branch, all verified: folded coarse pull-up, self-biased clock stage
(`sb_inverter`), pump bias from `ibias` (`cp_bias`), pump current halved and loop-filter
caps x3. Closed loop on PRBS7 with the trim pinned off: **nominal 600.632 MHz (ripple
15.1 mV), tt/125 C 600.419, ff/125 C/1.32 V 600.604, tt/-40 C 600.510** (seeded above its
lock point). **ff/-40 C/1.32 V does not lock** -- 677 MHz, vctrl climbing.

Two causes, both measured, neither fixed yet:
1. **Ring slope.** At ff/-40 C with the trim off the ring runs ~1200 MHz/V at the vctrl
   where it hits the baud rate, against 260 MHz/V at tt/125 C. The trim can only speed the
   ring up, so it cannot move that corner off the steep part. The ring grid says
   11 kohm/6 um or 12 kohm/4 um puts the baud rate at ~0.63-0.64 V on a ~300 MHz/V slope
   instead -- a 4x improvement -- **and the slow corner (ss/125 C/1.08 V) is the binding
   constraint on how far that can go** (only 10 k/4 um cleared the baud rate there in the
   first grid; a 8 um trim stops the ring oscillating).
2. **Pump charge imbalance.** An up decision and a down decision do not deliver equal and
   opposite charge: 0.43 fC worst case, ~130 nA at the baud rate, against the +77 nA
   phase-average that runs the corner away. Switch width and inverter ratio cannot fix it
   (0.43 -> 0.42 fC across the whole grid), so the switched topology is the limit; the
   current-steering variant is queued.

## Corner status after the detached run (2026-09-16 00:37)

Closed loop, PRBS7, **trim pinned off**, sb stage + cp_bias in the netlist:

| corner | f | f_err | vctrl s1 / s2 / s3 | verdict |
|---|---|---|---|---|
| tt 27 C 1.2 V | 600.756 MHz | +0.026 % | 0.600 / 0.598 / 0.599 | **locks** |
| tt 125 C 1.2 V | 600.419 MHz | -0.030 % | 0.605 / 0.603 / 0.600 | **locks** |
| ff 125 C 1.32 V | 600.604 MHz | +0.0006 % | 0.492 / 0.492 / 0.494 | **locks** |
| **tt -40 C 1.2 V** | 625.9 MHz | +4.20 % | 0.745 / 0.784 / 0.791 | **no lock**, vctrl climbing (seed 0.637) |
| **ff -40 C 1.32 V** | 687.0 MHz | +14.39 % | 0.805 / 0.865 / 0.904 | **no lock**, vctrl climbing (seed 0.546) |
| ss 125 C 1.08 V | - | - | - | trim-off ring too slow; needs the dual loop |
| ss -40 C 1.08 V | - | - | - | trim-off ring too slow; needs the dual loop |

Logs: `e2e_prbs_ffm40_132.log`, `e2e_prbs_ttm40_12.log`, seeds in
`vco_ct_seed_*.log`. The cold failures are the same upward-runaway signature the hot
corners had before cp_bias, and the clock is healthy there (swing 1.34-1.42 V), so it is
a loop problem, not a clock one. Cause **not yet identified**. What is measured so far:

- **Pump balance is not it.** With cp_bias at tt/-40 C/1.2 V the pump is +0.3 % at vout
  0.60 V and -2.6 % at 0.70 V; at ff/-40 C/1.32 V it is -4.1 % / -8.3 % (slightly
  *down*-heavy, i.e. pushing the way opposite the observed climb)
  (`cp_ibias_pvt2_*.log`, Lm 8 / Wp2 1.45).
- **Ring gain at 600.6 MHz** (from `vco_ct_seed_*.log`): tt/125 C 260 MHz/V (locks),
  ff/125 C/1.32 V 721 MHz/V (locks), tt/-40 C/1.2 V 600 MHz/V (fails),
  ff/-40 C/1.32 V 1249 MHz/V (fails). **Gain alone does not separate pass from fail**:
  ff/125 C locks at a higher ring gain than tt/-40 C fails at, with pump currents within
  6 % (783 vs 833 nA). A cold-specific second term is likely -- the loop filter's `rhigh`
  resistor rises as it cools, so each detector decision kicks the frequency harder
  (proportional path). **Not measured.**
- Running: `e2e_prbs_ttm40_halfgain.spice` (cp_bias mirror L 8 -> 16 um, ~half pump
  current, sim-only override) at tt/-40 C/1.2 V. Locks -> loop gain; still fails -> not gain.
  **Result** (`e2e_prbs_ttm40_halfgain.log`, override confirmed): **still no lock.**
  616.0 MHz (+2.56 %) against 625.9 MHz (+4.20 %) at full current; vctrl
  0.672 / 0.692 / 0.694 V, so the climb slows from 46 mV to 22 mV across the windows but
  does not stop. **Loop gain contributes; it is not the cause.**

**Next suspect: the pump's switching (not DC) balance.** The up path carries an extra
inverter (`inv_cp` makes `upb`), so up and down pulses are skewed; gate delays move with
temperature, so each decision can deliver unequal charge even with matched DC currents.
`cp_dyn.spice` drives up and down with equal alternating 600.6 MHz pulses and measures
the net average current into the output -- the dynamic equivalent of run_cp_cur.out.

**Result** (`cp_dyn_{tt,ss,ff}.log`): the net charge is **not a fixed offset -- it is a
function of vctrl**, crossing zero near 0.65-0.70 V at every corner. tt/-40 C/1.2 V:
+142.6 / +52.6 / -28.8 nA at vout 0.50 / 0.60 / 0.70. tt/125 C/1.2 V: +125.2 / +28.3 /
-67.1 nA. ff/-40 C/1.32 V: +176.0 / +72.7 / -25.7. That is +-12 % of the 800 nA pump,
matching the DC numbers, and **it is not cold-specific** -- the same shape appears at the
corners that lock. So switching balance does not explain the cold failures either.

**Better candidate, being tested: inverted detector sense from clock delay.** The
self-biased stage (sb_inverter) adds delay to the recovered clock. The cold corners are
where the ring is fastest, i.e. the UI is shortest: ring gain 600 MHz/V at tt/-40 C and
1249 at ff/-40 C. If the added delay pushes the sampling point past half a UI, the
detector's correction inverts and the loop drives the wrong way -- which is what both cold
runs show. The severity order fits: ff/-40 C worst (+14.4 %), tt/-40 C milder (+4.2 %),
hot corners (slowest rings) lock. Test: `pd_probe_ttm40.spice` -- up-dominant while the
ring is above baud means inverted.

**Result: inconclusive, and the reasoning was wrong.** `pd_probe_ttm40.log` (200-400 ns):
up 0.287 V vs dn 0.193 V (up-dominant), latch healthy (internal swing 1.15 V, outputs
full rail). But vctrl dips below its seed early (as it did at tt/125 C), so up-dominant
may simply be the correct response to a momentarily slow ring -- the window doesn't say
which. **And a pure clock delay sits inside the loop**, which absorbs it by shifting
phase; only the mismatch between rclk+ and rclk- (one inverter, ~2-3 % of a UI) escapes
that, far too little for a 14 % error. Delay is not a good explanation.

**Plainer possibility: the cold corners may never have worked.** No closed-loop run at
-40 C exists on this branch or on main -- before today main had no 125 C run either.
Two tests running (`sim/runners/cold_ab.sh`):
- A: `e2e_prbs_ttm40_nosb.spice` -- sb_inverter replaced (sim-only) by a plain DC-coupled
  inverter, i.e. the pre-change clock path, which does work at -40 C
  (clkraw 0.28-1.25 V there). Still fails -> the stage is not implicated.
- B: `e2e_prbs_ttm40_early.spice` -- vctrl every 100 ns over the first 1 us, plus the CSV:
  does it ever sit at the lock point?

**Results, and they point at the testbench.**
- A (`e2e_prbs_ttm40_nosb.log`, override confirmed): with the **pre-change clock path** tt/-40 C
  also does not lock -- 576.0 MHz (**-4.09 %**), vctrl parked at 0.6938 / 0.6949 / 0.6951 V,
  ripple 12.5 mV, clock 1.328 V. Drifts the other way, but no lock either. **The sb stage is
  not the cause of the cold failures.**
- B (`e2e_prbs_ttm40_early.log`): vctrl climbs monotonically 0.638 -> 0.725 V over the first
  1 us (~90 mV/us, about 39 nA into the ~436 fF filter) and never sits anywhere.

**RESOLVED: tt/-40 C locks; it is the direction of approach, not the seed value.**
`e2e_prbs_ttm40_seed080.log` (seed 0.80 V): **600.510 MHz, -0.015 %**, vctrl
0.6362 / 0.6357 / 0.6368 V, ripple 32.1 mV, clock 1.336 V.

**It settles at 0.636 V -- essentially the 0.637 V the bare-ring sweep predicted**, so the
seed was right and the "macro loading makes the seed wrong" reasoning above is
**retracted**. What matters is which side you start from: seeded *at* the lock point the
loop drifted up and never captured; seeded *above* it, it came down and locked.

That matches `cp_dyn_*.log`: the pump's net charge pushes vctrl **up** below ~0.66 V and
**down** above it. With a lock point at 0.636 V the pump opposes capture from below and
aids it from above. The hot corners lock from below because their lock points
(0.49-0.60 V) sit where the pump's push is smaller relative to the detector's authority --
**not verified**, and the cold-from-below case is a real acquisition limit worth
recording whatever the mechanism.

**ff/-40 C/1.32 V from 0.70 V: still runs away** (`e2e_prbs_ffm40_seed070.log`):
687.6 MHz (+14.49 %), vctrl 0.845 / 0.881 / 0.912 V (min 0.821, max 0.949), ripple
48.4 mV, clock 1.417 V. Approach-from-above explains tt/-40 C but **not** this corner: at
0.70 V the pump should already be pulling down (cp_dyn zero-crossing ~0.67 V there), yet
vctrl rose to 0.91 V and stayed. Something holds it high.

Candidate: above ~0.7 V the pump's down-side device runs short of headroom, the net
charge turns positive again, and the loop has a **second, false resting point**. cp_dyn
only measured to 0.70 V. Running: `cp_dyn2.spice` (vout to 1.00 V).

**No second resting point** (`cp_dyn2_*.log`, vout to 1.00 V): the net charge keeps
falling monotonically. ff/-40 C/1.32 V: +176.0 / +72.7 / -25.7 / -100.6 / -174.8 / -251.6 nA
at vout 0.50 / 0.60 / 0.70 / 0.80 / 0.90 / 1.00. **At 0.90 V, where the loop actually sits,
the pump pulls DOWN 175 nA** -- so the detector must be commanding up hard enough to
overcome that. Theory retracted.

**The data path is healthy there too**: ctle_swing 0.522 V at ff/-40 C (the largest of any
corner; 0.454 nominal, 0.387-0.390 at the 125 C corners), input swing identical at 0.195 V
everywhere. So the detector sees good data and still commands up.

Running: `clkcmp_ffm40.spice` -- ring frequency and clkoutp frequency measured in the same
run. The 687 MHz is read at the output buffer; if the ring is near 600 MHz while clkoutp
reads 687, the clock path is double-pulsing at this corner (fastest process, cold, high
supply) and the detector is being fed a mangled clock.

**No double-pulsing** (`clkcmp_ffm40.log`, 100-400 ns): ring 664.01 MHz, clkoutp
663.94 MHz, sb-stage output 663.95 MHz -- identical to four digits; ring swing 2.07 V,
clock 1.417 V, vctrl 0.646 V in that window. **The clock is a faithful copy of the ring**;
the ring really is running fast while the loop pushes it faster. Theory retracted.

**Current best explanation: up/down PULSE-WIDTH asymmetry at the pump.** The detector's
up and down outputs are not equally active: up_avg / dn_avg is 0.382 / 0.175 V at tt/125 C
(locks) and 0.287 / 0.193 V at tt/-40 C (`pd_probe_*.log`). The pump's up and down
*currents* are matched, so unequal widths mean each up decision delivers more charge than
each down decision. The pump's `up` input passes through `inv_cp` and `down` does not, so
their widths differ, and the difference is largest where gates are fastest -- ff/-40 C.
The loop then settles where the pump's own current imbalance cancels the width bias: at
ff/-40 C that is vctrl ~0.91 V (pump -175 nA), which is 687 MHz, not 600.6.
Test: `pd_probe_ffm40.log` -- up_avg / dn_avg 0.2597 / 0.1597 V at 1.32 V, i.e. duty
19.7 % / 12.1 %, ratio **1.63**. At tt/125 C (which locks) the ratio is 2.18 (31.8 / 14.6 %)
and at tt/-40 C 1.49. **ff/-40 C is not the most asymmetric corner, so this does not
separate pass from fail either. Theory retracted.** (Caveat: these are measured in
different loop states, so they are not strictly comparable.)

**Stopping the one-hypothesis-at-a-time approach.** Five mechanisms have now been
proposed and refuted for ff/-40 C: pump DC balance, loop gain, pump switching balance,
clock-path double-pulsing, up/down pulse-width asymmetry. The systematic measurement
instead: **the loop's correction curve.** `loop_scurve_{tt125,ffm40}.spice` replaces the
loop filter (sim-only) with a link to a forced global node, holds vctrl at 0.50-0.95 V in
0.05 V steps, and measures the net current the detector and pump deliver into it, plus the
ring frequency at each point. i > 0 means the loop pushes the ring faster. Zero crossings
are equilibria and the slope says whether they are stable. That explains lock or no-lock at
any corner without guessing a mechanism. tt/125 C is run alongside as the reference that locks.

**RESULT (`loop_scurve_{tt125,ffm40}.log`, both overrides confirmed). The ff/-40 C failure
is the ring's tuning slope at that corner, not a subtle loop defect.**

Ring frequency vs held vctrl, trim pinned off:

| vctrl | tt/125 C | ff/-40 C/1.32 V |
|---|---|---|
| 0.50 | 558.1 MHz | 541.1 MHz |
| 0.55 | 587.6 | **602.8** |
| 0.60 | 600.5 | 651.4 |
| 0.65 | 606.3 | 669.6 |
| 0.70 | 609.4 | 677.7 |
| 0.80 | 612.8 | 685.2 |
| 0.95 | 615.2 | 689.8 |

At ff/-40 C the ring crosses 600.6 MHz at ~0.546 V on a **~1200 MHz/V** slope: 25 mV of
control-voltage error is 30 MHz (5 %). The loop's own ripple is 30-50 mV there
(48.4 mV measured in `e2e_prbs_ffm40_seed070.log`), i.e. **+-35 to 60 MHz of frequency
modulation -- wider than any capture window.** At tt/125 C the slope is ~260 MHz/V, so
61 mV of ripple is 16 MHz (2.6 %), and that corner locks. tt/-40 C sits between
(~600 MHz/V) and locks only when seeded above its lock point.

Net current (same runs) is positive across most of the range at both corners, i.e. when
not phase-locked the loop drifts **up** until the pump's vctrl-dependent imbalance cancels
it -- tt/125 C balances at ~0.77 V (611 MHz), ff/-40 C above 0.90 V (689 MHz). Those are
exactly the park points seen closed loop. Caveat: near lock these currents are
phase-dependent (the 200 ns window catches one phase of a ~10 us beat), so treat the
near-lock values as indicative; the frequency column is solid.

**Consequence:** with the trim pinned off, the fast-cold corner forces the fine loop to sit
at the steep bottom of the ring's tuning curve. The coarse trim can only make the ring
*faster* (RING_DUAL_LOOP.md section 10.1), so it cannot move that corner to a gentler part
of the curve. Options for the user: lower pump current (less ripple; halving it at tt/-40 C
moved 625.9 -> 616.0 MHz), a bigger loop-filter capacitor, or a trim that can also slow the
ring.

**ss/-40 C/1.08 V centring** (`vco_ct_centre_ssm40_108.log`), MHz at vctrl 0.50 / 0.60 / 0.70 V:
vcoarse 1.20: 386.8 / 525.6 / 557.2; 0.85: 385.3 / 523.0 / 554.7; 0.65: 375.5 / 522.0 / 554.3;
0.45: (no swing) / 531.3 / 581.4; 0.30: - / 564.4 / 637.4; 0.15: - / 632.2 / **700.6**.
Here the trim is worth +26 % at vctrl 0.70 V, far more than at ss/125 C (+4.5 %).
A dual-loop run should seed near vcoarse 0.30 V, vctrl ~0.65 V.

## In flight at shutdown (2026-09-15 19:22) -- restart here

State: design on `ring-coarse-tune` = dual loop + folded coarse pull-up + self-biased
clock stage (sb_inverter) + pump bias from ibias (cp_bias). PRBS7 locks closed loop,
trim pinned off, at tt/27 C/1.2 V, tt/125 C/1.2 V and ff/125 C/1.32 V (table above).

Corner chain results so far (`sim/runners/prbs_corner.sh`, trim pinned off):
- ss/125 C/1.08 V: **not bracketed** -- the trim-off ring doesn't give 600.6 MHz with
  usable swing (`vco_ct_seed_ss125_108.log`), so no closed-loop run. Needs a vcoarse-free run.
- ss/-40 C/1.08 V: **not bracketed** (`vco_ct_seed_ssm40_108.log`), same.
- ff/-40 C/1.32 V: seed 0.546, closed-loop run was IN PROGRESS at shutdown -- killed, re-run.
- tt/-40 C/1.2 V: not started.

Before anything: `tools/netlist.sh` (blocks.inc is gitignored and generated), then check
`grep -c "^x14 Vdd Vss vbias bias_n bias_p cp_bias" sim/netlists/blocks.inc` = 1 and
`grep -c "^x13 Vdd Vss clkraw- clkraw_sb sb_inverter" sim/netlists/blocks.inc` = 1.

Restart, detached so a session ending cannot kill it (two runs have been lost that way):

    setsid nohup sim/runners/finish_corners.sh > sim/results/finish_corners.out 2>&1 &

That does ff/-40 C/1.32 V, then tt/-40 C/1.2 V (both `prbs_corner.sh`, trim pinned off),
then the ss/-40 C/1.08 V centring sweep, one ngspice at a time, ~35 min total. Watch
`sim/results/finish_corners.out` for "### ALL DONE".

Why the ss corners don't bracket: **the trim-off ring is too slow** there. ss/125 C/1.08 V
peaks at 571.6 MHz at vctrl 0.65 V (472-572 MHz over 0.45-0.65 V); ss/-40 C/1.08 V peaks at
541.9 MHz (386-542 MHz over 0.50-0.65 V; below 0.5 V there is no swing, and those fosc numbers are
noise). This is what the coarse trim is for (trim-on ceiling at ss/125 C/1.08 V is 638.2 MHz,
section 7.1 of RING_DUAL_LOOP.md). Next: run those corners with vcoarse free (dual loop),
e.g. e2e_dual.spice retargeted to the corner and seeded with vcoarse low enough to bracket.

**ss/125 C/1.08 V centring sweep** (`vco_ct_centre_ss125_108.log`), MHz at vctrl
0.50 / 0.60 / 0.70 V:
vcoarse 1.20: 516.4 / 564.3 / 576.2; 0.85: 514.4 / 562.6 / 574.5; 0.65: 504.4 / 562.6 / 575.4;
0.45: 478.2 / 563.5 / 581.5; 0.30: 465.6 / 566.6 / 589.4; 0.15: (no swing) / 577.1 / **602.7**.
So at this corner the trim is worth only ~+4.5 % at vctrl 0.70 V, and 600.6 MHz is
reached only with the trim fully on. This does not contradict the 638.2 MHz trim-on
ceiling in RING_DUAL_LOOP.md section 7.1: that is measured at vctrl = VDD (1.08 V), while
this sweep stops at 0.70 V. A dual-loop run here has to be seeded near
vcoarse 0.15-0.30 V with vctrl above 0.70 V; the exact point is **not measured**.

## In flight at last checkpoint (2026-09-15)

Five jobs, serialised on the ngspice lock. If the machine went down, rerun the
ones without results, in this order:

| what | how to rerun | answers |
|---|---|---|
| branch PRBS7 at ff/125 °C/1.32 V, **ideal pump bias** | `cd sim/decks && ../../tools/safe_ngspice.sh e2e_prbs_ff125_idealbias.spice ../results/e2e_prbs_ff125_idealbias.log 2500 5400 2000` | is the pump's reference the cause of the ff/125 °C death? Log must contain `redefinition of .subckt tiny_pll_bias_gen, ignored` or the result is void |
| slow-end floor at ff/125 °C with `vcoarse` at 1.32/0.90/0.85/0.80 V | `cd sim/decks && ../../tools/safe_ngspice.sh vco_ct_floor_clamp.spice ../results/vco_ct_floor_clamp.log 2500 2400 2000` | does the top-rail clamp cost the slow-end margin? |
| folded pull-up: top-rail sink | `cd sim/decks && ../../tools/safe_ngspice.sh coarse_clamp_fold.spice ../results/coarse_clamp_fold.log 1500 600 2000` | does folding remove the sink above ~0.85 V? |
| folded pull-up: null/search/span | `cd sim/decks && ../../tools/safe_ngspice.sh coarse_tb_fold.spice ../results/coarse_tb_fold.log 2000 1800 2000` | does the fix keep the null at 0.600 V and the 19.6 mV/µs search? |
| **main** PRBS7 at ff/125 °C/1.32 V | `sim/runners/main_prbs_ff125.sh` (self-seeding; writes nothing into main) | is the corner death inherited from main, or introduced by the branch? |

The folded pull-up lives in `sim/decks/coarse_loop_fold.inc` (subckt
`coarse_loop_fold`) and is **not** in the design record.

## Before trusting anything after the reboot

The runner scripts edit `tools/port_from_sky130.py` in place and restore it at
the end. One was interrupted, so:

```bash
git -C /home/ttuser/ssh_analog/ct-worktree diff tools/port_from_sky130.py
git -C /home/ttuser/ssh_analog/ct-worktree status --short
python3 -m pytest test -q
tools/netlist.sh           # blocks.inc may be mid-edit
```

`git checkout -- tools/port_from_sky130.py` returns the design record to
10500 Ω, which is what the last commit intends.

## Not affected by any of this

`main` at `/home/ttuser/ssh_analog/ihp-analog-equalizer` — clean, locking, and
the thing to lay out. `docs/LAYOUT.md` and `mag/` are ready and design
independent; `docs/CHIPALOOZA_SLOT.md` has slot 2 and the pin budget.
