# The dual-loop ring trim

## 1. The problem this solves

The receiver's ring oscillator, ported and re-tuned, reaches the 600.6 MHz
baud rate at 8 of the 27 PVT corners swept.  A bang-bang (Alexander) phase
detector is *phase*-only: it has no frequency acquisition, so a ring that
cannot reach the baud rate never locks, at any control voltage.  Covering all
27 corners needs the ring's centre frequency moved by **+15.2 % / −8.1 %**
of its nominal value, and the fine loop's own control range is only 1.166:1
and is spent on tracking, not on centring.

Three ways of supplying that were considered and two rejected:

| approach | why not |
|---|---|
| external band-select pins | the Chipalooza slot has 1–3 analog pads; spending two on trim bits is not affordable, and the user was clear the pins are not available |
| a clocked FSM that sweeps bands | needs a clock the receiver does not have before it locks, plus digital area and a reset strategy |
| **an analog coarse loop** | ~30 devices, no clock, no pins — adopted |

## 2. What vctrl actually reports

The coarse loop's only possible error signal is `vctrl`, because this is a
reference-less CDR: there is no second frequency in the chip to compare the
ring against.  The theory was that a band which cannot reach the data rate
rails `vctrl` high and one that cannot go slow enough rails it low — a signed
error, which a window comparator could turn into a bidirectional trim.

Theory was not sufficient, and it was wrong.  `tools/band_probe.sh` re-ports
the design with the ring load resistor moved out of band and runs the full
closed-loop 1.5 µs transient, reading `vctrl` in three windows:

| ring load | f reached | f error | vctrl @ 1.0–1.1 µs | @ 1.3–1.4 µs | @ 1.4–1.5 µs | drift |
|---|---|---|---|---|---|---|
| 7355 Ω (nominal, locks) | 600.614 MHz | +0.0023 % | 0.5992 V | 0.5990 V | 0.5990 V | −0.5 mV/µs |
| 8460 Ω (too slow) | 576.43 MHz | −4.02 % | 0.7101 V | 0.7395 V | 0.7531 V | **+107 mV/µs** |
| 6400 Ω (too fast) | 673.52 MHz | +12.14 % | 0.7557 V | 0.8054 V | 0.8223 V | **+167 mV/µs** |

The good news is that `vctrl` is an excellent *lock* detector.  Locked, it is
flat to half a millivolt per microsecond and sits at 0.599 V.  Out of band, in
either direction, it climbs at a hundred times that rate and is already 140–220
mV away before 1.5 µs is up.  A single threshold at ~0.70 V separates the three
cases cleanly.

The bad news is the column that matters for a bidirectional trim: **both wrong
bands drive `vctrl` the same way — up.**  There is no sign information in it at
all, and the window-comparator architecture sketched for §4 is dead.

Two mechanisms explain it, and both are inherent rather than fixable:

* A bang-bang phase detector has, by construction, *no* frequency
  discrimination.  With a frequency error the sampling phase slips
  continuously, early and late are each asserted for half of every beat
  period, and the average phase-detector output over a slip cycle is zero
  whichever side of the baud rate the ring is on.
* What is left when the phase term averages out is the charge pump's own
  up/down mismatch, measured at **11.0 %** (`sim/results/cp_current.log`).
  That is a one-signed current, so an unlocked loop integrates it into a
  one-signed drift.  The 6400 Ω case, being three times further out of band,
  drifts *faster* — consistent with a purely mismatch-driven ramp, since the
  further out it is the less of the pump's charge the phase term recovers.

Trimming the pump mismatch would not rescue the sign; it would only replace a
clean upward ramp with an aimless random walk, which is a worse detector.  The
architecture has to stop asking `vctrl` which way to go.

(Logs: `sim/results/e2e_band_8460.log`, `sim/results/e2e_band_6400.log`,
`sim/results/e2e_lock_tt.log`.)

## 3. The architecture the measurements force

Read §2 and §5 together and the circuit is almost determined:

* out of band `vctrl` has no sign, so the loop cannot simply trim — it has to
  **search**;
* in lock `vctrl` does have a sign, so the loop should **not** simply search —
  a search that stops is an open-circuit hold, and §5 shows this node cannot be
  held open;
* both facts point the same way when the ring is *slow*, which is what makes
  one branch able to do both jobs.

```
    vctrl ──┬── [ pMOS pair: vctrl vs VL ] ──────────────┐
            └── [ nMOS pair: vctrl vs VH ] ── 2 mirrors ─┤
                                                         ├── vcoarse ──> 10 trim gates
              [ wrap: vcoarse < 0.15 V ? ] ── retrace ───┤
                                                      Ccoarse (cap_cmomf)
                                                         │
                                                        VSS
```

* `vctrl > VH` → the pull-down branch sinks from `Ccoarse` → `vcoarse` falls →
  the trim pMOS across each ring load turns on harder → the ring speeds up.
* `vctrl < VL` → the pull-up branch sources into `Ccoarse` → the ring slows.
* `VL < vctrl < VH` → both pairs are steered to their dump branch and
  `vcoarse` holds.  **The dead zone is the point**: without it the coarse loop
  chases the fine loop's ripple.
* `vcoarse` at the bottom → the wrap comparator retraces it to the top in tens
  of nanoseconds and the search continues from the slow end.

The pull-down branch does two jobs and needs no mode switch to do them.  Out of
band `vctrl` is railed high, so it ramps `vcoarse` continuously and the wrap
turns that ramp into a repeating search of the whole coarse range.  In lock it
is half of a window trim.  The direction it wants in both cases is the same —
"vctrl is high, make the ring faster" — which is why one branch covers both.

`VH = 0.70 V`, `VL = 0.52 V`, from a poly divider off VDD.  Locked `vctrl` is
0.599 V and the worst measured ripple is 65 mV pp on PRBS7, so ±33 mV about
0.599 clears both edges by about 70 mV.  The thresholds track VDD, which is
right: the locked `vctrl` scales with the supply too.

### 3.1 Why the search runs slow-to-fast

This is easy to get backwards and the circuit does not work at all if it is.

While unlocked, `vctrl` is railed at the **top** of the fine loop's range.
Capture therefore happens at the instant the ring can just reach the baud rate
at maximum tail current — that is, with `vctrl` still high, still above any
sensible threshold.  The search has to keep running a little longer, and it has
to run in the direction that lets the fine loop *reduce* `vctrl` to hold lock.

Slow-to-fast does that: after capture the ring keeps speeding up, the fine loop
backs `vctrl` down, and the search stops itself when `vctrl` re-enters the
window from above.  Fast-to-slow would capture at the same railed `vctrl` and
then demand that the fine loop raise `vctrl` further to keep up.  There is no
headroom there and lock would break immediately.

### 3.2 How slow the search must be

The fine loop settles in under 1.5 µs.  The search must move the ring by much
less than the fine loop's capture range during that settling time, or it sweeps
straight through lock.  A full coarse range of 142 MHz (§4) traversed in 37 µs
is 3.8 MHz/µs, so during a 1.5 µs acquisition the target moves 5.8 MHz — about
1 % of the baud rate.  **The fine loop's capture range has not been measured**,
which is the open question this number depends on; §6 lists it.

That is the design point: 20 nA into a 1.05 pF `Ccoarse`, 19 mV/µs — measured
at 19.6 (§6).

Two corrections to that arithmetic, one in each direction.  The coarse knob's
authority at tt / 27 °C / 1.2 V is not 142 MHz but about 356 MHz (534 → 890 MHz
across the range, §7), so the search moves the ring at **9.2 MHz/µs**, and
during a 1.5 µs acquisition the target moves 2.3 % rather than 1 %.

Against that, the search **decelerates as it approaches lock**, and by a lot.
The pull-down current is not constant: it falls as `vctrl` comes down toward
`VH`, and the null table in §6 measures the shape — 19.6 mV/µs with `vctrl`
railed, 2.48 mV/µs at `vctrl` = 0.68 V, 0.69 mV/µs at 0.64 V.  So the moment the
fine loop begins to pull `vctrl` down, the thing it is chasing slows by nearly
an order of magnitude.  That is a property of using the same branch for the
search and the trim, and it was not designed in; it falls out of the window
comparator being soft.

Whether 2.3 % is inside the fine loop's capture range is still unmeasured, and
the closed-loop run is the direct test.

A closed-loop transient long enough to contain a real acquisition is 40 µs of
simulated time, and the 1.5 µs lock run already costs a quarter of an hour on
this machine.  So `coarse_loop.inc` carries a `Ksweep` parameter that scales
the bias currents: the closed-loop decks raise it so an acquisition fits in a
few microseconds, and `coarse_tb.spice` checks the real, unscaled rate
open-loop.  **`Ksweep` must be 1 in anything that claims a silicon number**, and
what a scaled run demonstrates is the mechanism and the polarity, not the
capture margin.

## 4. The knob, and what it is worth

The fine loop drives the ring's *tail current*.  Above the point where a stage
can charge its own load faster than its RC, more tail current buys nothing: the
load resistor sets the ceiling, and the ceiling is what fails at temperature.
So the coarse knob has to move the *load*, not the current.

`sim/decks/vco_rsweep.spice` measures what that is worth, sweeping the ring's
load resistance directly at `vctrl` = 1.10 V — the top of the fine range,
because the corner failures all happen at maximum tail current:

| Rload | f | stage delay |
|---|---|---|
| 9000 Ω | 565.3 MHz | 176.9 ps |
| 8000 Ω | 603.7 MHz | 165.7 ps |
| 7355 Ω (shipped) | 632.4 MHz | 158.1 ps |
| 6500 Ω | 677.0 MHz | 147.7 ps |
| 5500 Ω | 742.2 MHz | 134.7 ps |
| 4500 Ω | 829.6 MHz | 120.5 ps |
| 3500 Ω | 958.2 MHz | 104.4 ps |

Straight line, to better than a picosecond over the whole span:

    stage delay = 61.0 ps + 13.100 ps per kilohm

So 61 ps of the stage delay is not the load at all — it is the pair's own
transit time and the tail node — and the rest is RC.  At the shipped 7355 Ω
the load is 61 % of the delay, which makes it a strong knob: the
+15.2 % / −8.1 % the corner sweep asks for is 561–703 MHz, which is

    561 MHz -> 8951 Ω        703 MHz -> 6203 Ω

a 1.44:1 range on the load resistance.  That is a modest thing to ask of a
trim leg.

### 4.1 The trim leg is a pMOS, and a pMOS is not a resistor

    VDD --+--[Rload poly, 9000 Ω]--+-- vo+
          |                        |
          +---|MTR pMOS------------+        gate = vcoarse (global)

one pMOS across each of the ten ring load resistors, all ten gates tied to a
single global `vcoarse`.  The poly resistor sits at the *slow* end of the span
and the pMOS only ever speeds the ring up, so at `vcoarse = VDD` the trim is
entirely absent and the ring is the ported design with a slightly larger load.
There is no state in which the trim can make things worse than the untrimmed
circuit.

This is not the diode-connected-load idea that was tried and rejected.  There
the transistor *was* the load, so its process spread was the ring's spread and
5 of 24 swept points stopped oscillating.  Here the poly resistor is still the
load and the pMOS is a correction, so the pMOS's own spread is attenuated by
the parallel ratio.

The first sizing pass got this wrong in an instructive way.  A W = 0.5 µm,
L = 1 µm leg across an 8000 Ω load was predicted to give −21 % on the load
resistance; `sim/decks/trim_r.spice` measured **6339 Ω, −20.8 %** — the hand
arithmetic was right to 1 %.  But the ring moved only **+5.6 %**, where the
table above says a real 6339 Ω resistor is worth about +13 %.

The pMOS is only a resistor while it stays in triode.  At the bottom of the
ring's swing its source-drain voltage approaches its overdrive, it becomes a
current source, and it stops helping the rising edge — which is precisely the
edge the RC ceiling is made of.  Measured against a real resistor of the same
dc-equivalent value it is about 43 % as effective.  So the leg has to be sized
by sweeping the width in the ring, not by computing a resistance:
`sim/decks/vco_ct.spice` does that.

## 5. The hold capacitor cannot be a MOS capacitor

The first open-loop testbench showed `vcoarse` drifting 30 mV in the 180 µs it
was supposed to be holding — 0.17 mV/µs, which walks the whole trim range in
under four milliseconds and would make the receiver re-acquire forever.
Replacing the sweep switch with two long devices in series changed it by
0.6 mV, which ruled the switch out.  `sim/decks/cap_leak.spice` measured the
candidates directly, all at 384 µm² and at the 0.42 V hold point:

| capacitor | dc gate current | C | drift = I/C |
|---|---|---|---|
| `moscap_n` | **773 pA** | 4.19 pF | **184 mV/ms** |
| `moscap_p` | 13.7 pA | 1.20 pF | 11.4 mV/ms |
| `sg13_hv_nmos` as a cap | 0 (not modelled) | 0.50 pF | — |
| `cap_cmomf` | 0.42 pA | 0.49 pF | 0.85 mV/ms |

The measured 184 mV/ms accounts for the observed 171 mV/ms on its own, so that
is the whole of it.  `docs/DESIGN.md` already ruled MOS capacitors out of this
design for a different reason — their value moves 7.6 % between 0.6 V and 1.2 V
— and §3 of this note had argued that objection did not apply to an integrator
that only sets a rate.  It does not.  This one does.

So `Ccoarse` is `cap_cmomf`: 1.05 pF in a 28.5 µm square, 812 µm².  That is
comparable to the CTLE's degeneration capacitor, which is already the largest
object in the design, and it takes the total drawn device area from 2131 µm² to
about 2940 µm².

The `sg13_hv_nmos` row is not a recommendation.  Its zero is the model
declining to report a gate current rather than a measurement of one, and the
0.50 pF is a *depletion* value — at a 0.42 V gate bias a 3.3 V device is below
threshold, so that number says nothing about its oxide capacitance.  It is here
because it was tried.

## 6. What the loop does, open-loop

`sim/decks/coarse_tb.spice` drives `vctrl` by hand and watches `vcoarse`.  No
ring and no CDR: a closed-loop transient long enough to contain a real
acquisition is tens of microseconds, the 1.5 µs lock run already costs a
quarter of an hour on this machine, and every question would be confounded with
every other.  Driven open-loop each one is answered in a few seconds.

| what | measured (tt / 27 °C / 1.2 V) |
|---|---|
| cold start, `Ccoarse` at 0 V | retraces and parks at **1.185 V** — the slow end, which is where a search has to start |
| search rate | **19.6 mV/µs** (design point 19) |
| search span | 0.136 → 1.202 V, **1.066 V**, the whole trim range |
| wrap | fires and restarts the search, repeatedly, over 150 µs of railed `vctrl` |

And the measurement that matters most, which took two attempts to even ask
correctly.  The window is **not** a dead zone: at 20 nA the input pairs are in
weak inversion and steer over about 130 mV, so between the thresholds both are
partly on and the loop settles where they balance.  "Does `vcoarse` hold at
`vctrl` = 0.599 V?" therefore has no good answer — `vcoarse` holds at whatever
`vctrl` the null is at and drifts everywhere else, which is the loop working,
not failing.  The question worth asking is where the null is, because in the
closed loop that is the `vctrl` the receiver ends up sitting at:

| `vctrl` held at | d`vcoarse`/dt |
|---|---|
| 0.680 V | −2.48 mV/µs |
| 0.640 V | −0.69 mV/µs |
| **0.600 V** | **+0.024 mV/µs** |
| 0.560 V | +0.71 mV/µs |
| 0.520 V | +2.26 mV/µs |

The null is at **0.600 V**, and the fine loop's measured locked `vctrl` is
0.599 V.  So the coarse loop does not merely tolerate the fine loop's operating
point — it regulates `vctrl` to the middle of the fine loop's range and holds
it there, with a restoring slope of about 28 (µV/µs) per millivolt.  That is
also what makes leakage a non-issue: this is a closed loop with a stable
equilibrium, not a capacitor left open-circuit.

### 6.1 The coarse loop's own corners

`sim/decks/coarse_tb_pvt.spice` runs the same thing at nine temperature/supply
points, because §3 makes a claim about the wrap that needed checking: its two
trip points are *transistor thresholds* rather than references, and the
argument is that this is fine because they sit at the rails of the `vcoarse`
range, so what moves over temperature is how much dead travel the search does
at each end and not whether it covers the middle.

| temp / VDD | park | search low | search high | rate |
|---|---|---|---|---|
| −40 °C / 1.08 V | 0.835 V | 0.205 V | 1.081 V | — |
| 27 °C / 1.08 V | 0.809 | 0.137 | 1.081 | 13.7 mV/µs |
| 27 °C / 1.20 V | 0.862 | 0.136 | 1.202 | 14.4 |
| 27 °C / 1.32 V | 0.915 | 0.135 | 1.322 | 14.9 |
| 125 °C / 1.08 V | 0.748 | 0.025 | 1.082 | 13.5 |
| 125 °C / 1.20 V | 0.803 | 0.024 | 1.202 | 14.1 |
| 125 °C / 1.32 V | 0.853 | 0.023 | 1.322 | 14.5 |

The claim holds.  The low trip moves 0.023 → 0.205 V and the high trip tracks
VDD exactly, so the search covers essentially the whole range at every corner,
and the rate is flat to ±5 % across the box.  (The −40 °C rate is blank because
a retrace happened inside the sampling window; the two remaining −40 °C rows
failed a `meas` and are still to be chased.)

**The null does move**, and this is the part that was not designed:

| | 0.660 V | 0.600 V | 0.540 V | null |
|---|---|---|---|---|
| 27 °C / 1.32 V | −0.50 | +0.006 | +0.23 | ≈ 0.600 V |
| 27 °C / 1.20 V | −1.91 | −0.22 | +1.09 | ≈ 0.59 V |
| 27 °C / 1.08 V | −7.83 | −1.99 | −0.06 | ≈ 0.539 V |
| 125 °C / 1.20 V | −5.59 | −2.82 | −0.94 | below 0.54 V |

(d`vcoarse`/dt in mV/µs at each held `vctrl`.)

Two things are moving it.  The divider is ratiometric so the window tracks VDD
by design — that is the 0.539 → 0.600 V column.  Temperature is different: the
pull-down is an nMOS pair and the pull-up a pMOS pair, they drift against each
other, and no divider corrects that.

It happens to drift the right way.  At 125 °C the tail device's threshold is
lower, so the fine loop locks at a *lower* `vctrl` anyway — about 0.52 V at
125 °C against 0.60 V at −40 °C, from §7.2's floor data.  The null follows that
demand, at smaller magnitude, and the trim covers the difference.  Making the
two branches symmetric (an nMOS pair on both sides, the pull-up folded through
a pMOS mirror) would cost two devices to correct a drift that is already
pointing the right way, so it has not been done.

## 7. The 27 corners

`sim/decks/vco_ct_pvt.spice` and `vco_ct_floor.spice`, each run once per process
corner by `sim/run_corners.sh`.  The question is whether 600.6 MHz lies between
the fastest the ring can be made (trim fully on, tail at maximum) and the
slowest it can be *held* — and the ring is monotonic in both knobs, so two
points settle a corner rather than a tuning curve.

### 7.1 The fast end: all 27 clear, worst margin 10.3 %

Trim fully on, `vctrl` at VDD, MHz:

| | −40 °C | | | 27 °C | | | 125 °C | | |
|---|---|---|---|---|---|---|---|---|---|
| **VDD** | 1.08 | 1.20 | 1.32 | 1.08 | 1.20 | 1.32 | 1.08 | 1.20 | 1.32 |
| tt | 886.6 | 980.6 | 1065.8 | 790.0 | 863.3 | 930.8 | 681.5 | 733.6 | 782.5 |
| ss | 839.0 | 934.3 | 1020.9 | 756.3 | 831.2 | 900.6 | **662.3** | 715.4 | 765.6 |
| ff | 931.7 | 1022.5 | 1104.3 | 819.9 | 890.3 | 954.7 | 697.7 | 748.0 | 794.8 |

Worst case **662.3 MHz at ss / 125 °C / 1.08 V — 10.3 % above the baud rate.**

This is the end that failed before.  Untrimmed, 19 of 27 corners could not reach
600.6 MHz at any control voltage, and a bang-bang detector has no frequency
acquisition, so a ring that cannot reach the baud rate never locks.  None of
them fails now.

### 7.2 The slow end, and why the load resistor is 9000 Ω

The first pass read the slow end at a fixed `vctrl` of 0.45 V, which is a
convention and a bad one.  It sits near the tail device's threshold, and where
that threshold is moves a couple of hundred millivolts across process and
temperature — so the same number means "comfortably above the floor" at one
corner and "the ring is dead" at another.  That showed up in both directions at
once: every ss point failed to oscillate at 0.45 V (so those corners looked
unmeasured while actually being the most comfortable), and six tt and ff points
read above the baud rate on a control voltage that was simply not their floor.

`sim/decks/vco_ct_floor.spice` sweeps `vctrl` instead and reads the lowest
frequency that still has a usable ring swing — 0.15 V single-ended, the 300 mV
differential threshold `docs/DESIGN.md` filters on everywhere else, and read on
the ring node rather than the buffered output for the reason in trap 2.14.

**At 8000 Ω that found the one corner in 27 the coarse loop could not cover,
and it was the opposite of the failure this branch started from**: at
ss / 125 °C / 1.32 V the ring bottomed out at **606.4 MHz**, 1.0 % *above* the
baud rate, and below that `vctrl` the swing collapsed and it stopped
oscillating.  It could not be made slow *enough*.  `vco_ct_centre.spice` agreed
from the other side — at tt / 27 °C / 1.2 V with the trim entirely off the ring
was already at 685.6 MHz at `vctrl` = 0.60 V.

Both are the load resistor being too small for the shorter input pair, and the
floor is the quantity that identifies it.  At low tail current the ring is
current-starved: the stage delay is `C·swing/I` with `swing = I·R`, so the
frequency is `1/RC` and stops depending on the current at all.  What stops it
going slower is the swing dying.  **The floor is set by the load resistance and
nothing else, and it goes as 1/R** — which is also why no amount of work on the
tail device could have moved it.

At 9000 Ω, the floor of every corner, MHz (and the `vctrl` it occurs at):

| | −40 °C | | 27 °C | | 125 °C | |
|---|---|---|---|---|---|---|
| **VDD** | 1.08 | 1.32 | 1.08 | 1.32 | 1.08 | 1.32 |
| tt | 517.9 | 439.6 | 494.4 | 461.2 | 527.1 | **519.2** |
| ss | see below | 425.8 | 481.5 | 504.5 | 549.0 | **566.3** |
| ff | 469.6 | 428.6 | 483.7 | 450.7 | 516.4 | 510.0 |

Every one is below 600.6 MHz, the worst by 5.7 %.  The corner that failed at
8000 Ω now floors at 566.3 MHz.

One cell is still open: at **ss / −40 °C / 1.08 V** the ring has no usable swing
anywhere in the 0.30–0.50 V the sweep covered — it runs at 406.6 MHz at 0.50 V
with only 90 mV of swing.  The floor there is at a *higher* control voltage than
at the hot corners, which is the same threshold-tracking effect that made a
fixed 0.45 V the wrong convention to begin with.  The grid has been extended to
0.65 V and that corner is re-running.

### 7.3 What 9000 Ω costs, and why not more

The fast end paid for it: the worst ceiling went from 692.1 MHz (15.2 % of
margin) to 662.3 MHz (10.3 %).  That is the whole trade, and it is why the
resistor is not larger still.

It also leaves the design **off-centre at nominal**.  At tt / 27 °C / 1.2 V with
the trim entirely off the ring reaches 641.6 MHz at `vctrl` = 0.60 V and
562.1 MHz at 0.50 V, so the fine loop locks at about `vctrl` = 0.55 V with the
coarse trim at its slow rail — the coarse loop has no slow-side authority left
at nominal, and rests there.  That is a stable, locked state and not a failure
(the trim only ever speeds the ring up, so its slow rail is the untrimmed
circuit), but it means the coarse range is spent entirely on the corners that
need the ring *faster*.

Centring it would need about 10000 Ω, and that takes the worst ceiling to
roughly 617 MHz — 2.8 % of margin at ss / 125 °C / 1.08 V, which is not enough
to spend on centring.  9000 Ω is the compromise and the asymmetry is deliberate.

## 8. What this loop is not, and what has not been checked

The repository's habit is to distinguish "measured" from "not measured" rather
than estimate, so:

**Trim-leg mismatch is not modelled.** Ten pMOS legs share one gate rail, which
is the good case for matching, but mismatch between them makes the ring's ten
stage delays unequal and that is deterministic jitter on the recovered clock.
The instances carry `mm_ok=1` so the PDK's mismatch models *can* be turned on;
no Monte Carlo has been run, here or anywhere else in this design.

**Link-down behaviour is reasoned, not simulated.** With no data the phase
detector is blind, the pump integrates its own 11 % mismatch, `vctrl` rails
high and the coarse loop searches and wraps indefinitely — which is the correct
thing for it to do, and it re-acquires when data returns. That is the expected
behaviour of the measured pieces, not an observation.

**The startup precharge is not a factor, by arithmetic.** `vctrl_precharge`
holds `vctrl` for 76 ns before releasing; at 19.6 mV/µs the coarse loop moves
1.5 mV in that time.

**The wrap trip points move with threshold voltage.** They are transistor
thresholds, not references — roughly 165 mV of movement across −40 to 125 °C.
That is deliberate (§3, the wrap paragraph): both trips sit at the rails of the
`vcoarse` range, so what moves is how much dead travel the search does at each
end, not whether it covers the middle. It is not acceptable for the *window*
thresholds, which is why those still come from a divider.

**`Ksweep` exists and must stay at 1.** It scales the loop's bias currents so a
closed-loop acquisition can be made to fit in an affordable transient. Anything
committed with `Ksweep` other than 1 makes every silicon number here wrong;
`test/test_coarse_loop.py` pins it.

**The area is not free.** `cap_cmomf` at 1.05 pF is 812 µm², against a total
drawn device area of 2131 µm² before the coarse loop. The loop roughly doubles
the design's passive area, and the CTLE's degeneration capacitor was already
the largest single object in it.

## 9. Status

- [x] band signature measured — refuted the bidirectional-only trim, and
      justified the search (§2)
- [x] ring load leverage measured: 61.0 ps + 13.1 ps/kΩ (§4)
- [x] trim leg measured as a resistance, and found to be 43 % as effective as
      that resistance in the ring (§4.1)
- [x] hold capacitor: MOS ruled out by measurement, `cap_cmomf` chosen (§5)
- [x] trim-leg width sweep in the ring: W = 4 µm, 1.292:1 (§4.1)
- [x] input pair shortened to 0.7 µm — the only swept value that brackets the
      baud rate from both sides (`ring_lin.spice`)
- [x] open-loop: cold start, search rate, wrap, and the null (§6)
- [x] schematic capture: `xschem/coarse_loop.{sch,sym}` generated from the
      include and checked against it by `test/test_coarse_loop.py`; trim legs
      and the `coarse_loop` instance wired in through `POST_PORT_EDITS`
- [x] 27-corner sweep, fast end: worst 692.1 MHz, 15.2 % of margin (§7.1)
- [ ] 27-corner sweep, slow end: `vco_ct_floor.spice` running (§7.2)
- [ ] fine loop capture range — **not measured**, and §3.2 depends on it
      (`tools/capture_range.sh` is written and is an overnight job)
- [ ] closed dual loop, in-band: must not disturb the locked numbers
- [ ] closed dual loop, capturing
- [ ] re-run the closed-loop numbers with the 0.7 µm input pair — the existing
      600.614 MHz / 25.7 mV / 600.581 MHz / 65.3 mV were measured on the 0.9 µm
      ring and do not carry over
