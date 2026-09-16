# Resume here

Written mid-run as the machine was powering off. Session
`ring-coarse-tune`, all work pushed.

## One-line state

`main` locks and is untouched (600.614 MHz on 0101, 600.581 on PRBS7, 8 of 27
ring corners). The branch has a ring that **locks on 0101 and fails PRBS7**,
and a coarse loop that has never been tested closed-loop on a configuration
that locks.

## The story, shortest form

Re-sizing the ring for corner coverage (0.9 → 0.7 µm pair, 7355 → 9000 Ω)
broke the lock. Six hypotheses were wrong — precharge, `diff_amp_inv`, charge
pump bias, loop gain, pump current, ceiling at 12000 Ω — and two of those were
my own measurement errors, not circuit faults.

The cause is **where the baud rate sits relative to the ring's ceiling**:

| Rload | ceiling | baud/ceiling | Kvco | 0101 | PRBS7 |
|---|---|---|---|---|---|
| 9000 | 681.3 | 88 % | 844 | no | — |
| **10000** | 639.9 | 94 % | 720 | **600.660 MHz ✓** | **609.96 MHz ✗** |
| 10500 | 621.5 | 97 % | 302 | **612.19 MHz ✗** (+1.93 %) | not run — pointless |
| 11000 | 604.4 | 99 % | 27 | no headroom | — |
| main 0.9/7355 | 632.9 | 95 % | 522 | 600.614 ✓ | 600.581 ✓ |

Past the knee the loop has margin against the pump's 11 % current mismatch; on
the steep rise a 40 mV startup kick is a 50 MHz error, outside the bang-bang
capture range.

## Pick up here (updated 2026-09-15, later)

**10000 Ω + charge-pump up-source trimmed 2.0 → 1.8 µm locks on both patterns
at tt / 27 °C / 1.2 V** — the first branch configuration to do so:

| | 0101 | PRBS7 |
|---|---|---|
| main 0.9 µm / 7355 Ω | 600.614 MHz ✓ | 600.581 MHz ✓ |
| branch 10000 Ω, pump 2.0 µm | 600.660 ✓ | 609.96 ✗ |
| **branch 10000 Ω, pump 1.8 µm** | **600.554 ✓** | **600.541 ✓** |

(`sim/results/e2e_lock_pump18.log`, `e2e_prbs_pump18.log`)

**The trim does NOT hold across corners at DC.** `cp_mismatch_pvt.spice`,
mismatch % with the 1.8 µm trim, `vout` at ~VDD/2 (where the coarse loop's
window centres `vctrl`):

| | 1.08 V | 1.20 V | 1.32 V |
|---|---|---|---|
| tt −40 °C | +2.2 | +2.9 | +6.6 |
| tt 27 °C | +1.1 | +2.1 | +11.6 |
| tt 125 °C | +3.4 | +15.1 | **+35.3** |
| ss (all temps) | −2.3 … −1.1 | −1.3 … +1.3 | +3.5 … +6.7 |
| ff −40 °C | +5.7 | +11.2 | **+39.7** |
| ff 27 °C | +9.8 | +29.7 | **+57.9** |
| ff 125 °C | +33.7 | +53.2 | **+71.7** |

Two explanations were tried and are **retracted**:

1. *Channel-length modulation at the pump sources.* It would make mismatch depend
   strongly on `vout`. At ff it barely does (76 → 72 % over 0.50 → 0.70 V) while
   depending enormously on supply (+6 → +49 % at −40 °C, 1.08 → 1.32 V).
2. *VDD tracking symmetrises it.* Reading at `vout` = VDD/2 instead of a fixed
   0.60 V changes the numbers by a few points, not the picture.

**Mechanism confirmed: the bias generator** (`cp_mismatch_pvt2.spice`,
currents and bias nodes, 1.8 µm trim, `vout` = 0.60 V):

| corner | up nA | down nA | mis % | bias_n | VDD − bias_p |
|---|---|---|---|---|---|
| tt −40 °C 1.08 V | 457 | 479 | −4.7 | 0.307 | 0.428 |
| tt −40 °C 1.32 V | 630 | 571 | +9.8 | 0.314 | 0.442 |
| tt 125 °C 1.08 V | 1279 | 1295 | −1.2 | 0.255 | 0.411 |
| tt 125 °C 1.20 V | 1862 | 1601 | +15.1 | 0.273 | 0.447 |
| tt 125 °C 1.32 V | **3137** | **2142** | **+37.7** | 0.299 | **0.507** |

At 125 °C the pMOS bias `VDD − bias_p` grows with supply; at −40 °C it is flat;
`bias_n` barely moves anywhere. The up path loses regulation hot and high, the
down path does not. And a second problem the percentages hid: **total pump
current is ~4× nominal at tt/125 °C/1.32 V**, a 4× loop-gain swing across
corners, independent of mismatch.

**Lengthening the bias generator makes it worse** — retracted as a fix
(`bg_lsweep.spice`, all 27 corners, Wp 1.8 µm):

| Lb | worst mismatch | pump current across corners | spread |
|---|---|---|---|
| 1 µm | +73.8 % | 398 … 5684 nA | 14.3× |
| 2 µm | +77.5 % | 401 … 6224 nA | 15.5× |
| 4 µm | +81.4 % | 392 … 6856 nA | 17.5× |

So channel-length modulation in its mirrors is not the mechanism either. The
underlying problem is the reference itself: a **14× spread in pump current**
across corners. Candidate direction, not yet tried: derive the pump current from
the harness's bandgap-referenced `ibias` (already feeding the CTLE) instead of the
self-biased `tiny_pll_bias_gen` — the same lesson as the port's bias fix,
HANDBOOK §6.1. Before redesigning, the cause is being tested: the failing
ff/125 °C PRBS7 run repeated with ideal nominal pump bias
(`e2e_prbs_ff125_idealbias.spice`).

At ff it is worse — `cp_mismatch_pvt2.spice`, ff, trimmed pump, `vout` 0.60 V:
**7782 nA up vs 3586 nA down at 125 °C / 1.32 V**, about 10× nominal up
current, `VDD − bias_p` = 0.594 V.

**Ground truth at the worst corner: FAIL — but possibly not a circuit death (see below).** Closed-loop
PRBS7 at ff / 125 °C / 1.32 V, trim off, seeded at that corner's lock point
(0.489 V) (`sim/results/e2e_prbs_ff125.log`):
- recovered clock swing **49 nV** — the ring stopped
- `vctrl` walked **down** 0.373 → 0.338 → 0.303 V, below the ring's oscillation
  floor at that corner (swing 0.235 V at 0.325, none at 0.300)
- CTLE output 361 mV, so the data path is fine; it is the loop

**Cause test: the pump reference is NOT the cause.** The same run with
`tiny_pll_bias_gen` replaced by ideal nominal currents
(`e2e_prbs_ff125_idealbias.spice`; the log confirms the override took) fails
**identically to four digits**:

| | `vctrl` s1 | s2 | s3 | clock |
|---|---|---|---|---|
| self-biased pump | 0.3725 | 0.3381 | 0.3032 | 49 nV |
| ideal pump bias | 0.3722 | 0.3376 | 0.3026 | 49 nV |

If the pump were acting, cutting its current from ~7.8 µA to 0.8 µA would change
the drift. It does not move at all — so the phase detector and pump are not
participating, and `vctrl` is decaying on its own. That is the signature of a
ring that **never started** at this corner. The standalone seed sweep shows the
ring *can* oscillate there (0.91 V swing at `vctrl` 0.475–0.500 V), so this may
be a full-chip startup failure, possibly a testbench artefact of the kind found
in bring-up (HANDBOOK §6.2), rather than the receiver dying. **Unresolved**; an
early-time diagnostic is running, and `main` at the same corner will show
whether the same signature appears there.

The pump reference's 14× current spread across corners is still real and still
a problem for loop gain — it just is not what stops this run.

**So the branch holds both patterns at tt only; at ff / 125 °C / 1.32 V it
fails, cause unresolved.** `main` has not been tested closed-loop at that corner
either, so this is not yet a comparison against a known-good.

**The coarse loop, closed-loop, on this configuration** (`sim/runners/dualloop.sh`):

| run | start | recovered | error | `vctrl` | `vcoarse` |
|---|---|---|---|---|---|
| `e2e_dual` | trim off, 1.20 V | 600.661 MHz | +0.010 % | 0.6007 → 0.6013 | 1.20 → 0.914 V |
| `e2e_dual_walk` | trim on, 0.55 V | 600.724 MHz | +0.021 % | 0.5747 → 0.5739 | −8 mV |

Established: with both loops closed the receiver locks from both starting
points, and the coarse loop does not disturb the fine loop.

**Not established: the handover itself.** Near the null the coarse loop moves
~0.5 mV/µs, so a 2.5 µs run shows ~1 mV of walk — the deck's expectation of
47 mV used the railed search rate. Observing it needs the loop sped up
(`Ksweep`), and the generated schematic bakes widths as literals, so that means
overriding the subckt in a deck — being checked.

Unexpected, two items:
- `e2e_dual_walk` locked with the baud rate at 91 % of the ceiling (Kvco
  1005 MHz/V), where the untrimmed pump did not. Suggests pump mismatch was part
  of the steep-side failure all along. A lead only.
- `e2e_dual`'s `vcoarse` fell 286 mV with `vctrl` at the null. Harmless above
  ~0.8 V (trim off), cause not yet known.

## Results landed after the checkpoint (2026-09-15)

**Top-rail clamp costs no slow-end margin.** `vco_ct_floor_clamp.spice`,
ff/125 °C/1.32 V, lowest ring frequency with swing >= 0.15 V, `vcoarse` at
1.32 / 0.90 / 0.85 / 0.80 V: 470.5 / 464.2 / 456.0 / 449.2 MHz, i.e. -21.7 to
-25.2 % below baud. The corner table's "-5.2 %" there was read at fixed
vctrl 0.45 V, not the floor (corrected in RING_DUAL_LOOP.md §7).

**Folded pull-up (`coarse_loop_fold.inc`) removes the sink; not adopted yet.**
`coarse_clamp_fold.spice`, current into `vcoarse` at vctrl = VDD/2:

| vcoarse | original 27 °C/1.2 V | folded 27 °C/1.2 V | folded 125 °C/1.32 V |
|---|---|---|---|
| 0.90 V | +9.63 nA | +0.33 nA | -0.03 nA |
| 1.00 V | +239 nA | +0.64 nA | +0.72 nA |
| 1.20 V | +4296 nA | +2.40 nA | (1.32 V) +12.2 nA |

The 125 °C/1.10 V folded point reads -7268 nA and the original's reads -6204 nA:
both are the same outlier and most likely a DC-convergence artefact. Not
chased.

`coarse_tb_fold.spice` against the original: parks at 1.202 V (was 1.100),
span 0.123-1.201 V (was 0.134-1.201), search rate 18.4 mV/us (original 17.6),
both taken as the median of 2 us windows over `coarse_tb*.csv`. The deck's own
`search_mv_us` printed -88 because the 60-70 us window straddles a retrace.
That is a measurement artefact, and `run_checks.py` would flag it.
Null: d_600 +0.137 against +0.016, interpolated zero at vctrl ~0.606 V against
0.600. Pull-up slope is ~1.75x the original (d_560 1.22 against 0.70 mV/us)
while pull-down is ~1.2x. **Open:** scale the folded mirror (XMUP2) down to
restore symmetry, re-run both decks, then adopt.

**ff/125 °C/1.32 V PRBS7 failure: the ring runs, the clock path does not.**
`e2e_ff125_early.spice`: ring core differential p-p 1.906 / 1.906 / 1.904 /
1.770 / 1.720 V over 1-300 ns, but `clkoutp` p-p 43-56 nV and PD up/down p-p
2-13 uV. Precharge releases at 75.9 ns. So the break is between the ring core
and `rclk` (ring-internal diff_amp_inv -> CDR x4 diff_amp_inv -> inverter_buffer).
Those cells are unchanged from main.

**Main fails identically** (`sim/runners/main_prbs_ff125.sh`, `run_main_ff125.out`):
main ring seeded at 0.564, `rclk_swing` 49.6 nV, `vctrl` 0.366 -> 0.330 -> 0.293.
The failure is inherited from main, not introduced by the dual loop.

**Stage probe** (`e2e_ff125_stages.spice`, 20-60 ns, avg / p-p):
ring core net7/8 0.678 / 0.939 V; ring out net3/4 0.869 / 0.545 V;
`clkraw+` 0.872 / 0.533 V, `clkraw-` 0.877 / 0.574 V; `clkoutp` 20 uV / 56 nV.
(`rclk±` probes used the CDR port names and did not resolve; they need re-probing
as `x1.rclk_p`.) `clkraw` never goes below ~0.60 V, so the working hypothesis is
that `inverter_buffer`'s trip point at ff/125 C sits below 0.60 V and it reads a
constant high. Trip-point sweep (`sim/runners/inv_trip.sh`, `inv_trip_*.log`, DC, input for output = VDD/2):

| corner | trip |
|---|---|
| tt 27 C 1.20 V | 0.560 V |
| tt 27 C 1.32 V | 0.608 V |
| ff 27 C 1.20 V | 0.555 V |
| ff 125 C 1.32 V | **0.592 V** |
| ff -40 C 1.32 V | 0.615 V |
| ss -40 C 1.08 V | 0.517 V |
| ss 125 C 1.08 V | 0.502 V |

At ff/125 C/1.32 V `clkraw+` bottoms at ~0.605 V (avg - p-p/2) against a 0.592 V
trip, so it never crosses. That supports the hypothesis, but the miss is only
~13 mV, so any corner with a high trip and a high `clkraw` common mode is exposed.
The next check is `clkraw` min/max across PVT, open loop.

`sim/run_corners.sh` bug found on the way: its sed matched `cornerMOSlv.lib mos_`
with ONE space, and `coarse_tb_pvt.spice` has two. The sed matched nothing, so every
"corner" would have run tt. Fixed with `+` plus a hard fail on no match. Checked: the eight
decks with a double space (`coarse_tb`, `coarse_tb_pvt`, `coarse_startup`,
`coarse_clamp`, `coarse_clamp_fold`, `coarse_tb_fold`, `coarse_tb_fold2`, `cap_leak`)
never ran under `run_corners` (no `_tt/_ss/_ff` logs, no references), so no
earlier result is affected.

**Clock path open loop across PVT (`clkpath_pvt.spice`, ring_ct -> diff_amp_inv ->
inverter_buffer -> single_inverter; pt1 vctrl 0.45 trim off, pt2 vctrl 0.60 trim off,
pt3 vctrl VDD trim on):**
- tt, -40 C and 27 C, all supplies: `clkraw+` min 0.23-0.48 V, `rclk` full swing.
- **tt, 125 C, every supply and every knob setting: `rclk` swing 0.000-0.002 V.**
  `clkraw+` min 0.620-0.678 V, above the buffer trip. So the ff/125 C failure is
  not ff-specific: the recovered clock is dead at 125 C even in tt.
- ss pt1 (vctrl 0.45): `clkraw` flat, i.e. the ring itself is not oscillating
  there (below its floor). Not a clock-path result.
- ss 27 C 1.08 V: pt2 swing 0.653 V, pt3 0.028 V (marginal / failing with the
  ring running, `clkraw+` min 0.457 V). Ring-level causes not separated.
- **ss 125 C and ff 125 C, every supply and knob: `rclk` swing 0.000-0.002 V.**
  The clock is dead at 125 C at all three process corners.
- **No fixed switching point can work.** Lowest high level of `clkraw+` with the
  ring running: 0.621 V (ff/-40 C/1.08 V, pt2). Highest low level: 0.700 V
  (ss/125 C/1.32 V, pt3). The low level at one corner is above the high level at
  another, so resizing the buffer (option 2) cannot cover PVT. A fixed downward
  shift of x4's output (option 1) meets the same wall unless it also changes the
  swing. That points to an AC-coupled, self-biased buffer (option 3). Options as
  explained to the user: diff-amp resize / buffer resize / self-biased buffer.
Mechanism, as far as measured: `clkraw`'s low level rises with temperature
(0.23-0.31 V at -40 C, 0.37-0.48 V at 27 C, 0.62-0.68 V at 125 C at tt) until it
no longer crosses the buffer's switching point. The cells are unchanged from main.
Changing the clock path needs the user's decision ("no editing the clock").

**Option 3 chosen by the user: self-biased clock stage** (`sim/decks/sb_inverter.inc`:
100 fF cap_cmomf, 100 kohm rhigh feedback, 2/1 um inverter, fed from `clkraw-`
ahead of `inverter_buffer`). Open loop, 27 corners x 3 ring settings
(`clkpath_sb_pvt_{tt,ss,ff}.log`):
- **Every point where the ring oscillates switches: `rclk` swing 1.098-1.396 V,
  including all nine 125 C combinations at tt, ss and ff** (0-2 mV before).
- Duty cycle 0.514-0.595. Worst sb input swing 0.287 V (ss/125 C/1.08 V), still
  full-rail output. sb node average tracks the inverter threshold, 0.53-0.75 V.
- No-clock supply current of the stage (`sb_idle_*.log`): tt 6.5-52.2 uA, ss 1.8-32.2 uA,
  ff 15.4-78.3 uA (worst ff/125 C/1.32 V).
- Only zero-swing rows: ss pt1 (vctrl 0.45 V), where `clkraw` is flat. The ring
  isn't oscillating there, the same as before the change; not a clock-path result.
**Closed loop, nominal tt/27 C/1.2 V PRBS7, stage in the netlist**
(`e2e_prbs_sb.log`, seed 0.595): **600.633 MHz, +0.0055 %**, vctrl
0.5971 / 0.5974 / 0.5968 V across the three windows, ripple 36.6 mV pp, clock swing
1.307 V. Before the stage it was 600.541 MHz (-0.0099 %), ripple 36.7 mV
(`e2e_prbs_pump18.log`). Locks; the ~55 % duty cycle costs nothing measurable here.
**tt/125 C/1.2 V PRBS7, stage in the netlist, vcoarse PINNED at VDD (trim off)**
(`e2e_prbs_tt125_12.log`, seed 0.593): **the clock is alive, swing 1.277 V** (it was
0-2 mV at 125 C before the stage), but **it does not lock**. 615.0 MHz (+2.40 %),
with vctrl climbing 0.773 -> 0.954 -> 0.997 V, ripple 87.6 mV. That's the out-of-band
signature (the bang-bang detector has no frequency discrimination). With the trim
pinned off, 600.6 MHz sits at 99 % of this ring's top speed (608.1 MHz at vctrl
0.65 V, `vco_ct_seed_tt125_12.log`), beyond the ~94 % that has locked before. This
run removes exactly what the coarse loop is for. The real test at this corner is the
dual loop with vcoarse free: to do.

Centring sweep at tt/125 C/1.2 V (`vco_ct_centre_tt125.log`), MHz at vctrl 0.50 / 0.60 / 0.70:
vcoarse 1.20: 559.6 / 602.3 / 611.3; 0.85: 557.9 / 602.0 / 611.1; 0.65: 553.9 / 609.3 / 620.3;
0.45: 548.0 / 623.4 / 638.7; 0.30: 559.4 / 635.9 / 654.6; 0.15: (swing 0.136) / 652.2 / 672.8.
The trim does almost nothing above vcoarse 0.85 V here. 600.6 MHz needs vctrl ~0.595 V
at vcoarse >= 0.85 V, ~0.57 V at 0.45 V, ~0.55 V at 0.30 V. **Concern (not measured
closed-loop):** fold2's coarse null at tt/125 C/1.2 V is ~0.63 V (`coarse_null_fold2_pvt_tt.log`),
above every one of those lock points. So the coarse loop would push vcoarse back
toward the rail (trim off), which is the pinned state that did not lock. The vctrl
runaway in the pinned run also has to be checked against the charge pump's DC
up/down mismatch at this corner, which could produce it on its own.

Charge-pump DC mismatch, current design (Wp 1.8 um; `cp_mismatch_pvt2.spice` ->
`run_cp_cur.out`), (I_up - I_dn)/mean at vout 0.50 / 0.60 / 0.70 V:
tt 27 C 1.2 V +7.7 / +2.1 / -1.6 %; **tt 125 C 1.2 V +19.2 / +15.1 / +12.0 %**
(up 1862 nA, dn 1601 nA at 0.60); ss 125 C 1.2 V +2.9 / -1.3 / -3.8 %;
ff 125 C 1.2 V +56.5 / +53.2 / +50.5 %; **ff 125 C 1.32 V +76.4 / +73.8 / +71.7 %**.
Reasoning, not yet verified: out of lock the detector's up/down decisions average
out and the net charge is this mismatch, so vctrl rises whatever the frequency
is. That matches the pinned tt/125 C run (vctrl -> 1.0 V at 615 MHz). In lock a
+15 % mismatch needs ~54 % down decisions (~69 % at ff/125 C/1.32 V) to hold. Whether
the tt/125 C run captured and then lost lock, or never captured, is not known from
the three window averages.

**ff/125 C/1.32 V PRBS7, stage in the netlist, vcoarse pinned at VDD**
(`e2e_prbs_ff125_132.log`, seed 0.489): **clock alive, swing 1.391 V** (49 nV
before the stage), **not locked**. 644.5 MHz (+7.31 %), vctrl 1.207 / 1.161 / 1.162 V
in the three windows (min 1.070, max 1.263 over 1.5-3 us), ripple 147 mV. That's the
same runaway signature as tt/125 C, stronger, at the corner with the largest pump
mismatch (+74 %). Here 600.6 MHz is well inside the ring's range (seed 0.489 V), so
the ring ceiling can't be the cause at this corner. Pump mismatch is the leading
suspect; the tt/125 C mismatch-nulled run (`e2e_prbs_tt125_wp155.spice`) tests it.

**tt/125 C early-window diagnostic** (`e2e_prbs_tt125_early.log`, vctrl CSV in
`e2e_prbs_tt125_early_vctrl.csv`, not committed, 5.6 MB): **never captured.**
vctrl averages 0.531 (20-100 ns), 0.554 (100-300), 0.656 (300-600), 0.702 (600-1000),
0.730 V (1000-1500 ns). From 50 ns bins: 0.53-0.55 V for 0-300 ns (below the 0.593
seed; ring ~589 MHz), through 0.594 V at 300-350 ns without stopping, then a staircase:
plateau ~0.69-0.70 V over 600-1000 ns, ~0.75 V over 1200-1600 ns, ~1.0 V from 2.5 us.
Ripple 41-106 mV pp in every bin. The ring is above baud from vctrl ~0.60 V
(>= 611 MHz at 0.70 V), yet vctrl keeps rising. That's consistent with net up
charge from pump mismatch overpowering the detector; not proven until the wp155 run.
Unexplained: the initial 0.53 V below the seed. Not checked; the precharge
release at 76 ns is a candidate.

**tt/125 C with the pump mismatch nulled (sim-only MPSRC 1.55 um; override confirmed
by "redefinition of .subckt tiny_pll_charge_pump, ignored")**
(`e2e_prbs_tt125_wp155.log`): **still not locked.** 612.2 MHz (+1.93 %), vctrl
0.762 / 0.751 / 0.795 V (min 0.700, max 0.852 over 1.5-3 us), ripple 92.9 mV, clock
1.278 V. Nulling the mismatch kept vctrl lower (~0.75-0.80 V against ~1.0 V), but
the loop still sits with the ring above baud and doesn't pull back. At vctrl 0.70 V
this pump is ~3 % down-heavy (1850*1.55/1.8 = 1593 nA up vs 1640 nA down), so
**pump mismatch is not the whole cause.** The phase detector's behaviour at 125 C
is the next suspect: its d_latch cells are resistor-loaded CML like the diff amp
that killed the clock. Next: measure up/down pulse activity in closed loop at
tt/125 C against nominal.

**Phase-detector probe, 200-400 ns closed loop** (`pd_probe_nom.log`, `pd_probe_tt125.log`),
avg / p-p in V:

| node | tt 27 C (locks) | tt 125 C |
|---|---|---|
| data latch internal net1 / net2 | 0.693 / 1.082, 0.679 / 1.082 | 0.736 / 0.980, 0.731 / 0.975 |
| data latch output | 0.548 / 1.289 | 0.519 / 1.282 |
| data / edge flip-flop Q | 0.611 / 1.278, 0.571 / 1.288 | 0.601 / 1.284, 0.561 / 1.282 |
| pump up / down inputs | 0.188 / 1.341, 0.322 / 1.344 | 0.382 / 1.260, 0.175 / 1.269 |

Latch output inverter trip: 0.639 V at 27 C, 0.650 V at 125 C (`latinv_trip.log`).
**The detector works at 125 C:** the latch nodes still cross the trip and every output is
full swing. At 125 C in that window it is up-dominant, which is correct while vctrl
was 0.53-0.59 V and the ring slow.

**Hypothesis (not verified): loop gain.** Pump current at vout 0.60 V is 813 nA at tt/27 C,
1862 nA at tt/125 C (2.3x) and 7782 nA at ff/125 C/1.32 V (~10x) (`run_cp_cur.out`). The
bias generator's spread sets the loop's integral gain. The tt/125 C trace crossed the
lock point at ~0.7 mV/ns without stopping, consistent with overshoot past pull-in, then
cycle slips averaging to no net correction. That would also explain why nulling the
mismatch didn't help. Test: tt/125 C with an ideal nominal-current pump bias
(`e2e_prbs_tt125_idealbias.spice`).

**CONFIRMED: tt/125 C locks with an ideal nominal-current pump bias**
(`e2e_prbs_tt125_idealbias.log`; override confirmed by "redefinition of .subckt
tiny_pll_bias_gen, ignored"): **600.550 MHz, -0.0084 %**, vctrl 0.6024 / 0.6014 /
0.6022 V, ripple 51.9 mV, clock 1.278 V. Early windows 0.527 / 0.517 / 0.540 / 0.589 /
0.602 V, i.e. a smooth approach and settle, against the runaway to 1.0 V with the real
bias. **The 125 C lock failure is the pump bias generator**: its current, and so the
loop gain, rises 2.3x at tt/125 C and ~10x at ff/125 C/1.32 V. This test also changes the
pump's mismatch, so it doesn't separate gain from mismatch completely; the wp155 run
(mismatch nulled, real bias) still failed, which points at gain. Fix options go to the user
before any design change.

**ff/125 C/1.32 V with the same ideal nominal pump bias** (`e2e_prbs_ff125_132_idealbias.log`,
override confirmed, seed 0.489): **603.87 MHz, +0.55 %**, vctrl 0.4916 / 0.4928 /
**0.5182 V** (last window drifting up), min 0.456, max 0.557, ripple 83.6 mV, clock
1.385 V. Far better than the 644.5 MHz runaway with the real generator, but **not a
clean lock** (locked runs read ~0.01 % with a flat vctrl). Fixed pump currents remove the
runaway; something else at ff still pulls. Pump up/down balance at ff with nominal
currents is the next suspect; `cp_ibias_pvt_ff.log` will show it.

**cp_bias sizing sweep 1** (`cp_ibias_pvt_{tt,ss,ff}.log`, W 0.5 um mirror, XMP2 1.8 um,
27 corners x vout 0.5/0.6/0.7):

| Lm | up nA (all corners) | dn nA | mismatch | tt/27 C/1.2 V/0.6 V up / dn |
|---|---|---|---|---|
| 4 um | 1294-1637 | 1428-1952 | -24.8 .. -5.6 % (all Lm) | 1434 / 1655 |
| 5 um | 1071-1352 | 1212-1643 | | 1187 / 1393 |
| 6 um | 916-1153 | 1053-1425 | -26.7 .. -7.4 % | 1015 / 1209 |

(per corner: Lm=6 tt -23.9..-10.6, ss -19.9..-7.4, ff -26.7..-13.6 %.)
**Spread collapses: up 916-1153 nA at Lm 6 um (1.26x) against 398-5684 nA (14x) for
tiny_pll_bias_gen.** Two problems to trim: current ~25 % above the 800 nA the ideal-bias
lock used, and the pump is down-heavy by 7-27 %. XMP2 carries more than 0.9x, likely
from its larger Vds than the diode's. Sweep 2: Lm 7/7.5/8 x XMP2 1.45/1.55/1.65 um.

**Sizing sweep 2** (`cp_ibias_pvt2_{tt,ss,ff}.log`; 27 points per corner = 3 T x 3 VDD x
3 vout; 711 of 729 rows parsed, 18 lost to banner corruption):

| Lm | XMP2 | up nA | dn nA | mismatch | nominal up/dn |
|---|---|---|---|---|---|
| 7 | 1.45 | 802-1007 | 775-1067 | -11.8 .. +10.9 % | 888 / 896 |
| 7 | 1.55 | 802-1007 | 821-1123 | -16.9 .. +5.1 % | 888 / 946 |
| 7 | 1.65 | 802-1007 | 866-1179 | -21.7 .. -0.4 % | 888 / 996 |
| 7.5 | 1.45 | 756-947 | 734-1010 | -12.6 .. +10.6 % | 836 / 848 |
| 7.5 | 1.55 | 756-943 | 777-1063 | -17.7 .. +4.7 % | 836 / 896 |
| 7.5 | 1.65 | 756-947 | 820-1098 | -22.5 .. -0.7 % | (row lost) |
| **8** | **1.45** | **715-894** | **697-959** | **-13.4 .. +10.3 %** | **790 / 806** |
| 8 | 1.55 | 715-894 | 738-1010 | -18.5 .. +4.4 % | (row lost) |
| 8 | 1.65 | 715-894 | 779-1060 | -23.2 .. -1.0 % | 790 / 896 |

**Chosen: Lm 8 um, XMP2 1.45 um** (`sim/decks/cp_bias.inc`). Nominal matches the
800 nA the ideal-bias lock used; current spread is 1.25x across 27 corners (was 14x);
mismatch is centred (was up to +74 %).

**CLOSED LOOP WITH cp_bias IN THE NETLIST: all three corners lock** (PRBS7, sb stage +
cp_bias, vcoarse pinned at VDD, no overrides):

| corner | f | f_err | vctrl s1 / s2 / s3 | ripple | clock | log |
|---|---|---|---|---|---|---|
| tt 27 C 1.2 V | 600.756 MHz | +0.026 % | 0.5999 / 0.5978 / 0.5988 | 34.1 mV | 1.308 V | `e2e_prbs_cpbias.log` |
| tt 125 C 1.2 V | 600.419 MHz | -0.030 % | 0.6051 / 0.6031 / 0.5997 | 60.9 mV | 1.277 V | `e2e_prbs_tt125_cpbias.log` |
| ff 125 C 1.32 V | 600.604 MHz | +0.0006 % | 0.4923 / 0.4922 / 0.4936 | 50.4 mV | 1.388 V | `e2e_prbs_ff125_cpbias.log` |

Before: tt/125 C ran away to 615 MHz and ff/125 C to 644.5 MHz (real generator), and ff/125 C
with ideal bias drifted at 603.9 MHz. tt/125 C vctrl still eases down 5 mV across the
windows. Next: the remaining extremes closed loop (ss/125 C/1.08 V, ss/-40 C/1.08 V,
ff/-40 C/1.32 V, tt/-40 C/1.2 V) with `sim/runners/prbs_corner.sh`; then the dual loop at a
corner where the trim-off ring can't reach baud.

**Incident, 2026-09-15 (fixed): duplicate bias mirror in the netlist.** A
`port_from_sky130.py --cells CDR` run re-applied every POST_PORT_EDIT regardless
of `--cells`, and `add_bias_mirror` had no already-applied guard, so
`ctle_cdr_rx.sch` got a second x5 `ibias_mirror`. blocks.inc carried both. The
first closed-loop PRBS7 attempt with the sb stage (`e2e_prbs_sb.log`) died at
parse ("Error on line:"), so no wrong number came out of it, and the chain was
killed before any other run used that netlist. Fixed: schematic restored, edits
scoped to `--cells`, guard added, `test_post_port_edits_are_idempotent`, and
`netlist.sh` now fails on duplicate instance names.

**Nominal PRBS seed:** `e2e_prbs.spice` is committed back to 0.595. The 0.642
committed in f379502 came from the abandoned 10500 ohm experiment. The
600.541 MHz PRBS7 result was run with 0.595 (`sim/runners/pump18.sh`).

**Folded pull-up, XMUP2 0.7 um (`coarse_loop_fold2.inc`):** park 1.202 V,
span 0.122-1.201 V, search 18.40 mV/us, d_680/640/600/560/520 =
-2.96 / -0.84 / +0.019 / +0.87 / +2.80 mV/us. Original (`coarse_tb.log`):
-2.46 / -0.67 / +0.059 / +0.77 / +2.39. Symmetric, null at 0.600 V. Passes nominal;
PVT run (`coarse_tb_fold2_pvt.spice`) queued before adoption.

First fold2 PVT run: **ss/ff invalid.** All three logs have identical numbers.
`run_corners.sh` was edited while bash was executing it, and the ss/ff passes ran
the tt models. Re-run queued (`results/fold2_pvt.out`). The tt block is valid,
because the deck was tt throughout. tt, d_660 / d_600 / d_540 mV/us at the
temperature/supply points:

| T, VDD | original (`coarse_tb_pvt.log`) | fold2 | v_park orig -> fold2 |
|---|---|---|---|
| -40, 1.08 | -7.60 / -1.25 / +0.04 | -8.72 / -1.46 / +0.03 | 0.834 -> 1.078 |
| -40, 1.20 | -1.02 / -0.02 / +0.87 | -1.33 / -0.12 / +1.02 | 0.888 -> 1.199 |
| -40, 1.32 | -0.08 / +0.48 / +4.40 | -0.35 / +0.45 / +5.35 | 0.942 -> 1.318 |
| 27, 1.08 | -7.82 / -1.99 / -0.07 | -9.12 / -2.29 / -0.04 | 0.807 -> 1.079 |
| 27, 1.20 | -1.92 / -0.23 / +1.09 | -2.60 / -0.46 / +1.20 | 0.859 -> 1.198 |
| 27, 1.32 | -0.49 / +0.08 / +0.30 | -1.64 / -0.22 / +3.62 | 0.912 -> 1.317 |
| 125, 1.08 | **-10.06 / -4.95 / -2.46** | -0.66 / +0.64 / +1.45 | 0.758 -> 1.071 |
| 125, 1.20 | **-6.23 / -3.57 / -1.66** | -0.15 / +1.27 / +2.81 | 0.865 -> 1.191 |
| 125, 1.32 | -5.16 / -2.69 / +0.06 | +1.24 / +2.54 / +5.44 | 0.986 -> 1.308 |

At 125 C the original has no null between vctrl 0.54 and 0.66: it sinks at every
point, which is the top-rail leak, and it would walk the trim fully on. Fold2
restores a null (~0.65 V at 125 C/1.2 V) and parks at the rail everywhere.
At 125 C/1.32 V fold2's null is above 0.66 V: not measured further out. In both
cells the null does not track VDD/2 (27 C/1.32 V null ~0.59 V against the 0.66 V
divider midpoint); pre-existing, not chased. Fold2 vc_hi at 125 C is
1.00 / 1.12 / 1.23 V, below VDD.

Fold2 PVT re-run, valid (`coarse_tb_fold2_pvt_{ss,ff}.log`, different from tt),
d_660 / d_600 / d_540 mV/us:

| T, VDD | ss | ff |
|---|---|---|
| -40, 1.08 | -6.79 / -1.13 / -0.04 | -14.17 / -2.25 / +0.15 |
| -40, 1.20 | -0.53 / -0.35 / +0.01 | -3.40 / -0.86 / +1.09 |
| -40, 1.32 | -0.01 / +0.51 / +3.85 | +0.37 / +1.62 / +9.87 |
| 27, 1.08 | (+50.3 wrap) / -2.10 / -0.16 | (+48.7 wrap) / -5.16 / -0.86 |
| 27, 1.20 | -0.95 / +0.08 / +1.22 | -2.06 / +0.27 / +2.70 |
| 27, 1.32 | +0.05 / +0.91 / +4.03 | +0.08 / +1.88 / +8.25 |
| 125, 1.08 | -4.12 / -1.07 / +0.52 | +0.24 / +1.14 / +2.48 |
| 125, 1.20 | -1.11 / +0.34 / +1.79 | +2.09 / +2.90 / +4.42 |
| 125, 1.32 | +0.30 / +1.50 / +4.07 | +4.30 / +4.78 / +7.55 |

Park is at the rail at every corner (1.049-1.320 V). The two +50 readings are
the sample window straddling a wrap. **ff/125 C: positive at every step, so the
null is above 0.66 V; not located.** vc_hi there 0.94-1.14 V. The original cell
was only ever run at tt, so there's no ss/ff comparison yet. Next: vctrl past 0.66 V
at 125 C, both cells.

**Null staircase 0.54 -> 0.74 V, both cells, 27 corners** (`coarse_null_pvt_*.log`,
`coarse_null_fold2_pvt_*.log`). Readings of +30 to +57 mV/us are wraps inside a
sample window and are excluded. Null = sign change between adjacent steps.

| corner | original null | fold2 null |
|---|---|---|
| tt 125 C 1.08 / 1.20 / 1.32 V | **none** (sinks at every step) | ~0.58 / ~0.63 / ~0.69 V |
| ss 125 C 1.08 / 1.20 / 1.32 V | **none** / ~0.59 / ~0.64 V | ~0.55 / ~0.61 / ~0.67 V |
| ff 125 C 1.08 / 1.20 / 1.32 V | vcoarse pinned at 0.002-0.004 V (runaway; d~0 is saturation) | ~0.58 / ~0.64 / ~0.69 V |
| -40 C and 27 C, 1.20 / 1.32 V | 0.54-0.66 V | 0.54-0.67 V |
| -40 C and 27 C, 1.08 V | at or just below 0.54 V (\|d_540\| <= 2.5) | at or just below 0.54 V (\|d_540\| <= 0.3) |

Parks: original 0.75-1.08 V, fold2 1.05-1.32 V. Fold2 has a null at every corner
where one was measurable. The original loses it at tt/125 C and ss/125 C/1.08 V
and runs away at ff/125 C. **Fold2 meets the adoption criterion.**

**ADOPTED (2026-09-15):** folded pull-up with XMUP2 0.7 um is now in
`sim/decks/coarse_loop.inc` (37 devices, was 33). `xschem/coarse_loop.sch` is
regenerated by `tools/gen_coarse_loop.py`, `sim/netlists/blocks.inc` by
`tools/netlist.sh` (107 MOSFETs), and all 48 unit tests pass.
`coarse_tb.spice`'s search rate is now timed 0.9 -> 0.5 V on the second fall
after 10 us, instead of sampled at 60/70 us. `coarse_tb.spice` on the adopted cell **passes every run_checks bound**:
v_park 1.202 V, search 18.96 mV/us (new 0.9 -> 0.5 V timing), span 1.078 V,
d_600 +0.019 mV/us, d_680/640/560/520 -2.96 / -0.84 / +0.87 / +2.80. That's
identical to `coarse_tb_fold2.log`. Closed-loop `e2e_dual.spice` at nominal on the adopted cell
(`e2e_dual.log`): **600.635 MHz, f_err +0.0059 %**, vctrl_lock 0.5978 V, ripple
31.0 mV pp, clock swing 1.305 V, vcoarse 1.1954 -> 1.1942 V (walk -5.8 mV over
1.8-2.5 us, creep -1.1 mV in the last 100 ns). Locks; vcoarse stays at the slow end,
as at nominal before.
Neither result is in yet; don't quote the adopted cell's closed-loop numbers until
they are.

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
Test running: `pd_probe_ffm40.spice`. **Not yet confirmed.**

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
