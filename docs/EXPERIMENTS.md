# Experiment log and testing method

Every closed-loop run of this receiver costs 9-20 minutes, only one ngspice may
run at a time (CLAUDE.md §2), and a bang-bang CDR fails in ways that all look
alike from the outside: the clock is wrong and the control voltage is drifting.
On the night of 2026-09-15/16 that combination cost **five wrong explanations in
a row** for one corner, each one a full run to refute.

This file is the response to that. Part 1 is how to test this design so a
question costs seconds instead of a quarter of an hour. Part 2 is the log: what
each experiment asked, how it was measured, what came back, and what it settled.

---

## Part 1 — Method

### 1.1 Cheap measurements, in order of cost

| what | deck | cost | answers |
|---|---|---|---|
| a resistor or bias current vs temperature | `rhigh_tc.spice`, `cp_ibias_check.spice` | **seconds** (DC `op`) | is a device where I think it is? |
| pump currents, 27 corners | `cp_ibias_pvt*.spice` | ~1 min | balance and spread |
| pump charge per decision | `cp_dyn*.spice` | ~2 min | net charge the loop integrates |
| ring frequency vs a knob | `vco_ct_*.spice` | 1-3 min | tuning slope, ceiling, floor |
| one block open loop, 27 corners | `clkpath_*.spice` | ~10 min | does this stage work at every corner? |
| the loop's correction curve | `loop_scurve_*.spice` | ~7 min/corner | every equilibrium and its stability |
| closed loop, one corner | `e2e_prbs*.spice` | 9-20 min | the answer that counts |

**Work up this table, not down it.** Four of the five wrong explanations below
would have been refuted by a measurement above the line I actually used.

### 1.2 The screen that predicts lock

A bang-bang loop holds lock only if the frequency wobble from its own ripple is
small against its capture range. Both terms are measurable cheaply:

```
ripple_pp  ~=  I_pump * R_filter          (the step each decision kicks)
             + I_pump * N * UI / C_filter (a run of N same-direction decisions)
wobble_MHz  =  ripple_pp * Kvco
```

`N` = 7 for PRBS7 (its longest run), `UI` = 1.665 ns, `C_filter` = cap1 + cap2.
`I_pump` from `cp_ibias_check.spice`, `R_filter` from `rhigh_tc.spice`, `Kvco`
from any `vco_ct_*` sweep. Calibration against five measured closed-loop runs
(2026-09-16): nominal predicted 33 mV against 34.1 measured; tt/-40 C 37 against
32.1; the hot corners come out ~2x low, so **treat this as an order-of-magnitude
screen, not a number to quote**. What it gets right is the ranking:

| corner | Kvco MHz/V | wobble | closed loop |
|---|---|---|---|
| tt 125 C 1.2 V | 260 | 16 MHz | locks |
| ff 125 C 1.32 V | 721 | 36 MHz | locks |
| tt -40 C 1.2 V | 600 | 22 MHz | locks only when seeded from above |
| ff -40 C 1.32 V | **1200** | **58 MHz** | **does not lock** |

### 1.3 Rules that came out of the wrong turns

1. **Measure the transfer curve before theorising about a mechanism.**
   `loop_scurve` (hold vctrl, measure net current and ring frequency) explained
   in one run what five mechanism guesses had not.
2. **A metric that does not separate pass from fail is not the cause.** Twice a
   quantity looked damning at the failing corner until the passing corners were
   checked and were worse (pulse-width asymmetry: 1.63 at the failure, 2.18
   where it locks).
3. **Compare against a corner that works**, in the same deck, in the same run.
4. **State what a run cannot show.** A 200 ns average of a beat whose period is
   10 us is one phase, not an average.
5. **`save` gates `meas`.** ngspice keeps only saved vectors; a `meas` on an
   unsaved node fails and takes the whole `print` with it.
6. **Detach long runs** (`setsid nohup`). Two 15-minute runs were lost to
   sessions ending mid-transient before this became a habit.
7. **Let the unit tests catch geometry.** `test_device_geometry` rejected an
   L = 16 um mirror (PSP is characterised to 10 um) before it reached a netlist.

---

## Part 2 — The log

Each entry: **question**, deck, method, result, verdict. Logs are in
`sim/results/`; every number here is traceable to one.

### 2.1 The recovered clock dies at 125 C

- **Question:** why does PRBS7 fail at ff/125 C/1.32 V with a 49 nV clock?
- `e2e_ff125_early.spice`, then `e2e_ff125_stages.spice`: measure each stage
  from ring core to output, early in the run.
- **Result:** the ring oscillates at 1.9 V differential the whole time;
  `clkraw` (the diff-amp output feeding the buffer) sits 0.62-0.68 V at 125 C
  against an `inverter_buffer` threshold of 0.50-0.615 V (`inv_trip_*.log`).
- **Verdict:** the buffer never switches. Confirmed across all 27 corners
  (`clkpath_pvt_*.log`): **`rclk` swing 0-2 mV at every 125 C combination**, at
  tt, ss and ff. `main` fails identically, and no closed-loop run at 125 C had
  ever been done before. Inherited, not caused by the dual loop.

### 2.2 No fixed threshold can fix it

- **Question:** can the buffer be resized, or the diff amp shifted, instead of
  adding a cell?
- Read `clkpath_pvt_*.log` across corners: lowest high level vs highest low level.
- **Result:** lowest high 0.621 V (ff/-40 C/1.08 V); highest low 0.700 V
  (ss/125 C/1.32 V).
- **Verdict:** the low level at one corner is *above* the high level at another,
  so no fixed switching point lies inside the swing everywhere. Resizing is
  ruled out by arithmetic, before any simulation of a candidate.

### 2.3 Self-biased clock stage (`sb_inverter`)

- **Question:** does an AC-coupled, self-biased inverter fix every corner?
- `clkpath_sb_pvt.spice`: the same open-loop chain with the stage inserted,
  27 corners x 3 ring settings.
- **Result:** `rclk` swings 1.10-1.40 V at **every point where the ring
  oscillates**, including all 27 at 125 C. Duty 0.51-0.60. Worst input swing
  0.287 V. Idle current 1.8-78.3 uA (`sb_idle_*.log`).
- **Verdict:** adopted. Closed loop at nominal: 600.633 MHz, +0.0055 %.

### 2.4 The coarse loop's top rail (folded pull-up)

- **Question:** the coarse trim's pull-up pMOS reverse-conducts onto `vcoarse`
  (4.3 uA at 1.2 V, `coarse_clamp.log`). Does folding it through mirrors help?
- `coarse_clamp_fold.spice` (leak), `coarse_tb_fold*.spice` (null, search),
  `coarse_null_*_pvt_*.log` (27 corners).
- **Result:** leak at 1.0 V 239 nA -> 0.64 nA. Null at 0.600 V restored, slopes
  symmetric at XMP2 0.7 um. **At 125 C the original has no null at all** (it
  sinks at every vctrl from 0.54 to 0.74 V) and runs the trim to the rail at
  ff/125 C; the folded cell has a null at every 125 C corner (0.55-0.69 V).
- **Verdict:** adopted (37 devices, was 33).

### 2.5 The 125 C lock failure: four runs to find the bias generator

All at tt/125 C/1.2 V, PRBS7, trim pinned off:

| run | result | verdict |
|---|---|---|
| as built (`e2e_prbs_tt125_12.log`) | 615 MHz, vctrl -> 1.0 V | clock now alive, but no lock |
| `pd_probe_tt125.log` | latch nodes cross their threshold, outputs full swing | detector is fine |
| `e2e_prbs_tt125_wp155.log` (pump mismatch nulled, sim-only) | 612 MHz, still no lock | mismatch is not it |
| **`e2e_prbs_tt125_idealbias.log`** (ideal nominal currents, sim-only) | **600.550 MHz, -0.0084 %** | **the bias generator is the cause** |

`tiny_pll_bias_gen` is self-biased: its current, and so the loop gain, is
2.3x nominal at tt/125 C and ~10x at ff/125 C/1.32 V (`run_cp_cur.out`).

### 2.6 `cp_bias`: pump bias from the chip's `ibias`

- **Question:** what sizes reproduce the ideal currents from the 40 uA reference?
- `cp_ibias_pvt.spice` then `cp_ibias_pvt2.spice`: DC, 27 corners x 3 output
  voltages, sweeping the mirror length and the bias_n mirror width. **Two sweeps,
  ~2 minutes, nine candidate sizings** -- the alternative was a closed-loop run
  per guess.
- **Result:** L 8 um / XMP2 1.45 um: nominal 790/806 nA; **715-894 nA across 27
  corners (1.25x, against 398-5684 nA for the generator)**; mismatch -13.4..+10.3 %
  (was up to +74 %).
- **Verdict:** adopted. Closed loop: nominal 600.756 MHz, tt/125 C 600.419 MHz,
  ff/125 C/1.32 V 600.604 MHz -- **both hot corners lock for the first time.**

### 2.7 ff/-40 C: five refuted explanations

| # | claim | test | why it was wrong |
|---|---|---|---|
| 1 | pump DC balance | `cp_ibias_pvt2_*.log` | +0.3 % at tt/-40 C, -4 % at ff/-40 C -- the wrong sign for the observed climb |
| 2 | loop gain | `e2e_prbs_ttm40_halfgain.log` | halving the current slowed the climb (46 -> 22 mV) but did not stop it |
| 3 | pump switching balance | `cp_dyn*.log` | net charge is a function of vctrl, same shape at corners that lock; and at 0.90 V, where the loop sat, it pulls **down** 175 nA |
| 4 | clock-path double-pulsing | `clkcmp_ffm40.log` | ring 664.01 MHz vs clkoutp 663.94 MHz -- faithful to four digits |
| 5 | up/down pulse-width asymmetry | `pd_probe_ffm40.log` | ratio 1.63 at the failure, 2.18 at tt/125 C which locks |

Also refuted on the way: that the seeds were wrong (tt/-40 C settles at 0.636 V,
which is what the bare-ring sweep predicted), and that a clock delay could invert
the detector (a delay inside the loop is absorbed by it).

### 2.8 The measurement that answered it: the loop's correction curve

- **Question, finally asked properly:** where are the loop's equilibria and are
  they stable?
- `loop_scurve_{tt125,ffm40}.spice`: replace the loop filter (sim-only) with a
  link to a forced node, hold vctrl at 0.50-0.95 V, and measure the net current
  into it and the ring frequency at each point.
- **Result:**

  | vctrl | tt/125 C | ff/-40 C/1.32 V |
  |---|---|---|
  | 0.50 | 558.1 MHz | 541.1 MHz |
  | 0.55 | 587.6 | **602.8** |
  | 0.60 | 600.5 | 651.4 |
  | 0.70 | 609.4 | 677.7 |
  | 0.95 | 615.2 | 689.8 |

- **Verdict:** at ff/-40 C the ring crosses the baud rate at ~0.546 V on a
  **~1200 MHz/V** slope, so the loop's own 48 mV of ripple is +-58 MHz -- wider
  than any capture window. At tt/125 C the slope is 260 MHz/V and 61 mV of ripple
  is 16 MHz, and it locks. Not a defect in any block: the fast-cold corner forces
  the fine loop onto the steep bottom of the tuning curve, and the coarse trim can
  only make the ring *faster* (RING_DUAL_LOOP.md §10.1), so it cannot move it off.
  Unlocked, the loop drifts up until the pump's vctrl-dependent imbalance cancels
  the drift -- 0.77 V (611 MHz) at tt/125 C, >0.90 V (689 MHz) at ff/-40 C, which
  are exactly the park points seen closed loop.

### 2.9 The two ripple fixes (in flight)

- **Question:** does cutting ripple bring ff/-40 C inside its capture range?
- Screen first (§1.2), then simulate: pump current halved (`cp_bias` mirror
  W 0.5 -> 0.25 um; **L 16 um was rejected by `test_device_geometry`**, PSP stops
  at 10 um) and the loop-filter capacitors tripled (m 18 -> 54, m 3 -> 9,
  +86 um2 in a 146,641 um2 slot).
- **Measured immediately (seconds):** pump currents 401-458 nA across corners,
  against 749-890 before (`cp_ibias_check.log`). Predicted wobble at ff/-40 C
  falls from 58 MHz to ~14 MHz, below tt/125 C's 16 MHz, which locks.
  **Side effect to watch:** the pump's balance at 0.6 V moved from -2 % to -8 %
  (down-heavy), because the narrower mirror shifts the operating point; XMP2 can
  be retrimmed if it matters.
- **Caution:** the loop is now ~5x slower to acquire (current down, capacitance
  up). Read `vctrl_s1..s3` for drift before calling a run locked or not, and
  lengthen the transient rather than declaring failure.
- **Closed-loop result** (`e2e_prbs_lr.log`, `e2e_prbs_ffm40_lowripple_lr.log`):

  | corner | f | f_err | vctrl s1/s2/s3 | ripple |
  |---|---|---|---|---|
  | tt 27 C 1.2 V | 600.632 MHz | +0.0053 % | 0.5970 / 0.5981 / 0.5966 | **15.1 mV** (was 34.1) |
  | ff -40 C 1.32 V | 677.1 MHz | +12.73 % | 0.6824 / 0.7002 / 0.7161 | **15.5 mV** (was 48.4) |

  **The fixes do what they were meant to -- and ff/-40 C still does not lock.** Ripple is
  down 3x at both corners, nominal is unharmed, and the wobble at ff/-40 C is now
  ~19 MHz against tt/125 C's 16 MHz, which locks. **So ripple was not the blocker.**
  vctrl still climbs there at ~57 mV/us, which needs ~74 nA of net up current into the
  1308 fF filter, while the pump at that voltage supplies about -13 nA. The push is
  coming from the detector's decisions, not from the pump.

### 2.10 The detector's characteristic vs phase (in flight)

- **Question, asked the cheap way:** at ff/-40 C, is there *any* clock phase at which the
  loop is in balance? If not, no amount of ripple or gain work can make it lock.
- `pd_phase_{tt125,ffm40}.spice`: the ring is replaced (sim-only) by an **ideal clock at
  exactly the baud rate** with a settable phase, vctrl is held by the forced-node filter
  override, and the net current is measured at ten phases across one UI. No frequency
  offset, so there is no beat to average away -- the flaw that made the near-lock points of
  `loop_scurve` unreliable (§1.3 rule 4).
- **Reading it:** a zero crossing with the right slope is a lock phase. A curve that never
  crosses zero means the loop cannot balance at that corner at any phase.
- **Result** (`pd_phase_{tt125,ffm40}.log`, ring override confirmed in both), net nA into
  vctrl vs clock phase in UI:

  | phase | 0.0 | 0.1 | 0.2 | 0.3 | 0.4 | 0.5 | 0.6 | 0.7 | 0.8 | 0.9 |
  |---|---|---|---|---|---|---|---|---|---|---|
  | tt/125 C | -345 | -165 | -51 | +310 | +311 | +309 | +175 | +54 | -150 | -344 |
  | ff/-40 C | -335 | -332 | -257 | +197 | +420 | +415 | +408 | +412 | +170 | -328 |

- **Verdict: the detector is fine at both corners** -- a proper bang-bang S-curve with zero
  crossings near 0.25 and 0.85 UI, so a balanced lock phase exists at ff/-40 C too.
  **But the phase-AVERAGE is what an unlocked loop integrates**, because a slipping loop
  sweeps all phases uniformly:

  | corner | phase-average | closed loop |
  |---|---|---|
  | tt/125 C | **+10.4 nA** | captures and locks |
  | ff/-40 C | **+77.1 nA** | drifts up, never captures |

  That matches the ~74 nA drift measured closed loop (§2.9). (An earlier note in this file
  said +57 nA for ff/-40 C: that was an arithmetic slip on the same ten numbers; the
  correct average is +77.1 nA, confirmed independently by `pd_trim_ffm40.log`.) The cause is the S-curve's
  asymmetry: at ff/-40 C the up lobe reaches +420 nA while the down lobe only reaches
  -335 nA, so slipping integrates **upward** and the loop escapes before it can catch. The
  earlier "pulse-width asymmetry" guess (§2.7 #5) was the right family of cause measured
  the wrong way -- duty at one operating point says nothing; the phase-average does.

### 2.11 Trimming the pump against the phase-average (in flight)

- **Question:** what bias_n mirror width makes the phase-average ~0 at the worst corner
  without breaking the corner that works?
- `pd_trim_{ffm40,tt125}.spice`: the §2.10 measurement with XMP2 swept 1.00-1.45 um
  (sim-only parameterised `cp_bias` override), ten phases per width.
- **Why this is the right metric:** it predicts runaway directly and needs no closed-loop
  run. (Cost in practice: ~40 min per corner, not the ~5 min estimated -- 40 phase points
  x 300 ns each. Still cheaper than one closed-loop run per candidate size, and it answers
  a question a closed-loop run cannot.)
- **Direction:** wider XMP2 = more down current = a more negative average, so the null is
  **above** 1.45 um. A first sweep went the wrong way (1.00-1.45) and was killed.
- **Partial result** (`pd_trim_ffm40.log`): +77.1 nA at 1.45 um, +66.7 nA at 1.60 um --
  about **-10 nA per 0.15 um**, while the lobe extremes barely move (+420/-335 ->
  +419/-357). Reaching tt/125 C's +10 nA would need XMP2 ~2.45 um. **This knob is too weak
  and the asymmetry is not mainly set by the bias current**; the next candidates are the
  pump switches themselves (charge injection, and the up path's extra inverter).

### 2.12 Option 1: can the ring be centred so the trim works both ways?

- **Question:** which (load resistance, trim width) puts 600.6 MHz *inside* the trim's range
  at both extremes, so the coarse loop can push the ring either way and the fine loop can
  sit mid-range instead of against an end stop?
- `ring_centre_{ffm40,ss125}.spice`: **ring only**, a 3x3 grid of Rload (10/12/14 kohm) x
  trim width (4/8/12 um), frequency and swing with the trim off and fully on. ~4 min per
  corner. No closed-loop run, no receiver.
- **Result at ff/-40 C/1.32 V** (the corner that fails): today's 10 k / 4 um gives 654 MHz
  with the trim *off* at vctrl 0.60 -- above the target, which is why the fine loop is
  dragged to the steep bottom. 12 k / 8 um gives 537-557 MHz off and ~1000 MHz on, so the
  target sits inside the range.
- **Result at ss/125 C/1.08 V** (the slow extreme), and it is the binding constraint:

  | sizing | trim off | trim ON | verdict |
  |---|---|---|---|
  | 10 k / 4 um (today) | 564-576 MHz | **607-625 MHz** | only candidate that clears 600.6 |
  | 12 k / 4 um | 507-517 | 567-589 | short of the target |
  | 12 k / 8 um | 461-471 | **swing 0.000** | **the ring stops oscillating** |

- **Two things this settled without a single end-to-end run:**
  1. **A wide trim is unusable at ss/125 C/1.08 V**: fully on, it shunts the load hard
     enough to stop oscillation. The usable trim range is bounded by swing, not frequency.
  2. **Widening the trim slows the ring even when it is OFF** (654 -> 597 MHz at ff/-40 C
     going 4 -> 8 um), because the wider device loads the ring node. Trim width is two
     knobs at once, so the pair has to be chosen together.
- **Flaw in this sweep, corrected in sweep 2:** vctrl was capped at 0.70 V. At the slow
  corner the loop legitimately runs vctrl high (0.9-1.05 V), where the ring is flat and the
  high Kvco that breaks the fast corner is not a problem. Candidates were therefore being
  scored against an artificially narrow window. `ring_centre2_*.spice` sweeps vctrl
  0.55-1.05 V over a finer grid (11/12/13 kohm x 4/6 um), dropping the widths that killed
  oscillation.

### 2.13 Option 3, isolated: charge per up decision vs per down decision

- **Question:** the detector characteristic's phase-average is +77 nA at ff/-40 C against
  +10 nA at tt/125 C (§2.10). That means an up decision and a down decision do not deliver
  equal and opposite charge. Which device sizes fix it?
- **Isolated by construction** (`cp_charge.spice`): the pump and its bias only -- no ring,
  no detector, no loop. Fire one up pulse a UI wide, then one down pulse, and integrate the
  charge into a held output. An ideal pump gives `q_up + q_dn = 0`.
- **Swept:** nMOS switch width 0.4-0.7 um x the up-path inverter's P/N ratio (1.0/1.5/2.0),
  at all nine temperature/supply points per process corner. Each point is a 25 ns
  transient: **the whole grid costs less than one closed-loop run.**
- **Why these two parameters:** the up path passes through that inverter and the down path
  does not, so the inverter's rise/fall asymmetry sets the up pulse's width, and the switch
  widths set how much charge each injects.
- **RETRACTED FIRST READING.** The first pass of this analysis was run while the ff log was
  still being written, and reported `q_dn = +0.05 fC` at ff/-40 C -- "the down decision
  delivers no charge" -- which looked like the whole answer. The completed log says
  **-1.21 fC**. Parsing a log mid-write is precisely what rule 4 of 1.3 warns about, and it
  cost a wrong conclusion that was committed before it was checked (6200cec).

- **Result** (`cp_charge_*.log`, complete: 108 rows per corner = 12 sizings x 9 T/VDD):

  | corner | q_up | q_dn | net |
  |---|---|---|---|
  | tt 125 C 1.20 V | +0.60 fC | -0.84 fC | -0.25 fC |
  | **ff -40 C 1.32 V** (the corner that fails) | +0.66 fC | **-1.21 fC** | **-0.55 fC** |
  | **ss -40 C 1.32 V** | +0.82 fC | **-0.06 fC** | **+0.76 fC** |

  **The pump does not explain the ff/-40 C failure**: there it is slightly *down*-heavy,
  the opposite sign to the drift that breaks the corner.

  **But the collapsed down branch is real at ss/-40 C/1.32 V**, where the down decision
  delivers essentially nothing. That corner has never been run closed loop; this predicts
  it will drift up the way ff/-40 C does. Worst |net| over the whole size grid is
  0.75-1.08 fC and rises with switch width, so resizing does not fix it.

  **What does drive ff/-40 C up** is in the detector curve (2.10): its up lobe spans about
  0.5 UI and its down lobe about 0.4 UI, so a slipping loop spends more time being pushed
  up. Decision *windows*, not pump charge.

- **Mechanism at ss/-40 C, to be confirmed:** in the switched pump each current source is turned off
  between decisions, so its source node (src_n/src_p) discharges; on the next decision the
  source must recharge that node before it can deliver current. If recovery is slower than
  the 1.665 ns a decision lasts, the charge never arrives. `cp_width.spice` tests it by
  sweeping the decision width (0.5/1/2/4 UI): charge appearing at longer widths means
  recovery time; charge never appearing means the branch is starved and the bias is at
  fault. `cp_steer.spice` (2.14) is the fix that follows if it is recovery.

### 2.14 Current-steering pump: measured and REJECTED

- **Question:** does keeping both current sources conducting and steering their current to a
  dump node beat switching them off and on?
- `cp_steer.spice`, identical harness and measurement to `cp_charge.spice`, 27 corners x 12
  sizings, dump node held at the output's dc by a testbench source (the best case -- a real
  one needs a replica bias).
- **Result:** worst |q_up + q_dn| **0.99 fC against 0.87 fC** for the switched pump as built;
  best-in-grid 0.92 against 0.75. **Worse, not better.** Rejected.
- Cost of finding out: a few minutes on an isolated deck, against a night of closed-loop
  runs had it been tried in the receiver.

### 2.15 Ring re-sizing: the 27-corner bracket check

- **Question:** with the load resistors at 11 kohm (trim width unchanged at 4 um), is the
  baud rate still between the slowest and fastest the ring can be made, at every corner?
- `ring_bracket.spice` (built by the overnight chain from `vco_ct_pvt.spice` with the chosen
  sizing), ring only, 27 corners x 2 knob extremes.
- **Result: bracketed at 24 of 27 corners outright.** The three ss rows flagged otherwise
  (ss/-40 C/1.08 V, ss/-40 C/1.32 V, ss/27 C/1.08 V) have **zero swing at the slow test
  point**, i.e. the ring is slower than the measurement can see -- the comfortable direction,
  and the convention RING_DUAL_LOOP.md 7.2 already uses. Every corner's fast end clears the
  baud rate with healthy swing (618-1064 MHz).
- Worst fast-end margin: **ss/125 C/1.08 V at 618.1 MHz, +2.9 %** -- still the binding corner.

### 2.16 The dual loop locks at ss/-40 C/1.08 V

- First closed-loop run ever at an ss corner, and the first with **vcoarse free** rather than
  pinned (`run_dual_ssm40_108.out`, 0101 stimulus, seeds vctrl 0.65 / vcoarse 0.30):
  **600.596 MHz, -0.0006 %**, vctrl 0.645 V, ripple 8.0 mV, clock 1.323 V, vcoarse settling
  at 0.287-0.289 V (the trim partly on, which is what the coarse loop is for).
- **ss/125 C/1.08 V did not reach lock in the window** (560.0 MHz, -6.8 %) -- but vctrl was
  still climbing (0.580 -> 0.588 V) with the trim already driven fully on. At ~13 mV/us it
  needs ~30 us to reach its lock point and the run is 2.5 us. **That is a consequence of the
  ripple fixes** (pump current halved, filter capacitors tripled) which slowed acquisition
  ~5x. Re-running seeded at 0.85 V.
