# Verification: what was measured, how, and what each number means

Cheap checks before expensive ones, every pass criterion written in code rather
than judged by eye, and a clear line between "measured" and "not measured". The
methodology is inherited from the sky130 original; the numbers are not.

Every figure in `README.md` traces to a log in `sim/results/` produced by a
deck in `sim/decks/`. Where a number is *not* measured, this document says so
rather than estimating it.

---

## 1. The measurement stack

| stage | question it answers | deck | cost |
|---|---|---|---|
| device characterisation | what are the actual sheet resistances and capacitor densities? | `char/caps.spice`, `char/mos.spice` | seconds |
| netlist equivalence | is the ported circuit the same circuit? | `tools/check_port_equivalence.py` | instant |
| CTLE operating point | does the stage bias at 1.2 V at all? | `sim/decks/ctle_bias.spice` | seconds |
| CTLE sizing search | what is the best achievable Nyquist gain? | `sim/decks/ctle_tune*.spice` | minutes |
| CTLE PVT | does it hold across 27 corners? | `sim/decks/ctle_ac.spice` via `sim/run_ctle_ac.sh` | ~10 min |
| VCO tuning range | can the ring reach the baud rate? | `sim/decks/vco_range.spice` | ~10 min |
| charge pump and loop filter | how much charge per update, into how much capacitance? | `sim/decks/cp_current.spice` | seconds |
| CDR chain | does the ring run, and does the clock reach the pin? | `sim/decks/e2e_diag*.spice` | ~5 min |
| CDR acquisition | does the loop lock, and at what frequency? | `sim/decks/e2e_lock.spice` | ~25 min |
| end-to-end eye and jitter | is there an eye at the sampling instant? | not run | 20-25 min |

The last row is the honest state of this repository. See §6.

## 2. The netlist-equivalence check

A port between processes is exactly the kind of change that looks right and is
wrong, because **xschem connects by coordinate**. A symbol whose pins sit one
grid step from the symbol it replaces rewires the schematic, netlists without
complaint, and simulates something else entirely.

`tools/check_port_equivalence.py` compares the sky130 netlist and the IHP
netlist as graphs — for every subcircuit, the pin list, the instance set, and
the net attached to each *named terminal*, matched by terminal role rather than
by netlist column since the two PDKs declare their symbol pins in different
orders. Auto-generated net names are matched up to a consistent one-to-one
renaming.

It does not compare device sizes or model names: this is a port, those are
supposed to differ. It answers "is it the same circuit". Result:

```
Port is structurally identical to the sky130 source:
21 subcircuits, 121 instances, every terminal on the same net.
```

Deliberate design changes are listed explicitly in the tool
(`EXPECTED_NEW_CELLS`) so that a *new* difference cannot hide among them.

## 3. The CTLE at 1.2 V

### The constraint

The gain of a resistively loaded differential pair is

    gm · Rload  =  (gm/Id) · (Id · Rload)  =  (gm/Id) · ΔVload

where ΔVload is the DC drop across the load resistor. The supply buys ΔVload,
and there is a hard ceiling on it: the output common mode cannot fall more than
a threshold below the input common mode, or the input pair enters triode. It
does not lose gain gracefully there — it collapses.

sky130 at 1.8 V spent up to 0.65 V on ΔVload. At 1.2 V there is about 0.45 V
available with margin.

### What was searched, and what did not work

Roughly 200 operating points, all in `sim/decks/ctle_tune*.spice`:

- **Current.** Swept 65 µA to 620 µA. The Nyquist gain moved by 2 dB across
  the whole range. More current buys gm as √I and costs ΔVload linearly, and
  the two nearly cancel. *Not the lever.*
- **Input width.** 20 µm to 60 µm. Wider gives better gm/Id and worse Miller
  capacitance at the output; the two cancel above about 30 µm. *Marginal.*
- **Input channel length.** 0.13, 0.2, 0.3 µm. Changed the Nyquist gain by less
  than 0.3 dB. *Not the lever.*
- **Input common mode.** Raising it to 0.85-0.95 V to give the tail headroom
  *reduced* the gain, because it pushes the input pair into triode from the
  other side. There is a narrow window and it is near 0.70 V.
- **Load resistance.** This *is* the lever, and only in combination with a
  current bias. 2.5 kΩ → 3.5 kΩ took the Nyquist gain from +11.9 dB to
  +13.2 dB and the channel-plus-CTLE residual from −1.9 dB to −0.71 dB.
- **Fingering, afterwards.** Splitting the wide devices into fingers to stay
  inside the PSP model's validated width range changed the mirror ratio, since
  PSP's width-dependent terms and the diffusion geometry both follow `w/ng`
  rather than `w`. At the same reference current the tail fell from 351 µA to
  253 µA. Raising the reference from 25 µA to 40 µA recovers most of it —
  12.10 dB back up to 12.79 dB — but not all, because the tail drain drops to
  0.12 V as the current rises and the tail enters triode, so the current stops
  tracking the reference. That last half dB is the price of the correction and
  it is the right price to pay.

### The bias had to stop being a voltage

With `vbias` held at a fixed 0.45 V, the CTLE's Nyquist gain across 27 corners
spanned **15 dB**, from +14.2 dB at ss/−40 °C/1.32 V to −1.3 dB at
ff/−40 °C/1.08 V. A gate voltage does not specify a current once threshold
voltage and mobility move.

`xschem/ibias_mirror.sch` — one diode-connected replica of the CTLE tail at one
tenth the width — turns a reference current into whatever gate voltage that
current needs at the corner in question. The Chipalooza harness provides
bandgap-referenced current sources to every slot, so this costs one pin and one
transistor.

Measured effect: tail current holds within **1.4 % across ±10 % of supply** and
within ±25 % across all 27 corners, and the Nyquist-gain spread falls from
15.5 dB to 5.8 dB.

### Final sizing and result

| parameter | value |
|---|---|
| input pair | W = 30 µm, L = 0.2 µm, 6 fingers |
| tail | W = 40 µm, L = 1.0 µm, 8 fingers, mirrored from a 40 µA reference |
| load resistors | 3.5 kΩ (`rhigh`, W = 1 µm, L = 2.36 µm) |
| degeneration resistors | 900 Ω each |
| degeneration capacitor | 1.6 pF `cap_cmomf`, 35.3 µm square |
| input common mode | 0.70 V |
| supply current | 336 µA at 1.2 V (0.40 mW); 247-409 µA over 27 corners |

`sim/results/ctle_ac_{tt,ss,ff}.log`, 27 corners: 3 process × 3 temperature
(−40/27/125 °C) × 3 supply (1.08/1.2/1.32 V), with the resistor and capacitor
corners moved *with* the MOS corner rather than left typical.

| quantity | this design | sky130 original |
|---|---|---|
| CTLE gain at Nyquist, nominal | **+12.79 dB** | +13.32 dB |
| CTLE gain at Nyquist, 27 corners | +9.35 … +15.10 dB | +11.71 … +14.40 dB |
| Boost (Nyquist − DC) | +5.05 … +7.80 dB | +6.30 … +7.90 dB |
| Channel + CTLE at Nyquist, nominal | **−1.03 dB** | ≈ −0.4 dB |
| Channel + CTLE at Nyquist, 27 corners | −4.45 … +1.26 dB | −2.03 … +0.66 dB |

Nominal is half a dB below the original. The corner spread is wider, and it is
temperature, not process or supply: at 125 °C the Nyquist gain falls about
2.4 dB. The
Chipalooza proposal commits to 0–110 °C, not −40…125 °C; the wider range is
simulated here because that is what the sky130 numbers were quoted over and a
comparison has to be like for like.

## 4. The ring oscillator

This is where the port stops being a translation.

The five stages are CML: an NMOS pair with poly load resistors and a tail
device whose gate is `vctrl`. A bang-bang phase detector is **phase-only** — it
has no frequency acquisition — so a ring that cannot reach the baud rate never
locks, at any control voltage. The tuning range is not a performance number,
it is a functional requirement.

The sky130 ring reached 514–621 MHz at tt/27 °C against a 600.6 Mb/s baud rate:
3 % of margin. That is why it failed at 125 °C and at low supply, and the
sky130 project characterised it, understood it, and accepted it.

**Ported unchanged to 1.2 V it reaches 424–554 MHz** (`sim/results/`,
`vco_range.spice`) — below the baud rate, so it does not lock at all. That is
not a limitation to accept, it is a broken port, and it had to be fixed.

### What sets the frequency

The measurement that matters: sweeping `vctrl` from 0.35 V to 1.2 V moves the
frequency by only 1.3:1, and most of that is in the first 100 mV above the
point where oscillation starts. Above that the ring is **RC-limited by its own
load resistor**, not current-starved — the same conclusion the sky130 project
reached. Raising the control voltage buys almost nothing.

So the frequency is set by the load resistance and the capacitance on the
output node, and the capacitance is dominated by the input pair's gate. The
sky130 pair is drawn at L = 1 µm, and shortening it moves the whole curve:

| input pair L | load R | frequency range at tt/27 °C |
|---|---|---|
| 1.0 µm (as ported) | 7.36 kΩ | 424 – 554 MHz |
| 0.7 µm | 7.36 kΩ | 707 – 842 MHz |
| 0.7 µm | 5.50 kΩ | 819 – 992 MHz |
| 0.6 µm | 5.50 kΩ | 959 – 1174 MHz |
| 0.3 µm | 5.50 kΩ | 1701 – 2163 MHz |

(Below about 0.3 µm the ring runs at 3–5 GHz with a swing under 100 mV: it is
past the point where a stage has enough gain to sustain oscillation cleanly,
and the "frequency" reported there is not a usable oscillation. That is why
every measurement here is filtered on differential swing above 300 mV — a
`meas` on a node that is barely moving still returns a number.)

L = 0.9 µm was chosen over anything shorter because the range is narrow either
way and **centring matters more than headroom**: 0.8 µm gives 613–723 MHz,
which puts the baud rate below the point where the ring starts oscillating at
all, and a ring that cannot run slowly enough fails just as completely as one
that cannot run fast enough.

### The tuning range does not cover PVT: 8 corners out of 27

`sim/results/vco_pvtf_{tt,ss,ff}.log` — 3 process x 3 temperature x 3 supply,
usable points only (differential swing above 300 mV, because a `meas` on a node
that is barely moving still returns a number).

| corner | usable range | 600.6 MHz |
|---|---|---|
| tt / −40 °C / 1.08…1.32 V | 505–620 … 527–683 MHz | reachable |
| tt / +27 °C / 1.08 V | 534 – **604** MHz | reachable, 0.6 % margin |
| tt / +125 °C / 1.20 V | 559 – 599 MHz | **too slow** |
| ss / +27 °C / 1.32 V | 444 – 593 MHz | **too slow** |
| ss / +125 °C / 1.08 V | 482 – **521** MHz | **too slow**, by 15 % |
| ff / −40 °C / 1.32 V | **631** – 769 MHz | **cannot go slow enough** |
| ff / +125 °C / 1.32 V | **654** – 686 MHz | **cannot go slow enough** |

**8 of 27 corners can reach the baud rate.** The sky130 original passed 6 of
11, so this is not a regression — it is the same wall, measured completely.

The failures point in *opposite directions*, and that is the part that settles
the question. At the slow corners the ring cannot reach 600.6 MHz; at the fast
corners its slowest usable frequency is already 620–650 MHz, so it cannot come
*down* to the baud rate either. No amount of re-centring fixes both: moving the
curve up to rescue ss pushes ff further out of reach. A ring whose tuning range
is 1.2:1 cannot span a corner box that needs 1.54:1.

That last number is the specification for the fix, and it comes straight out of
the table:

- worst slow corner, ss/125 °C/1.08 V: ceiling 521 MHz, needs **+15.2 %**
- worst fast corner, ff/125 °C/1.32 V: floor 654 MHz, needs **−8.1 %**

So a coarse control spanning 1.25:1 in two or three steps covers the whole box.
Two digital bits, which the harness supplies.

### What would fix it, and what was not done

Coarse tuning. Two candidates, neither built:

- **A switchable load-resistor leg per stage**, under one digital control bit.
  The frequency is set by the load resistance, so paralleling a second resistor
  roughly doubles the reachable range. The Chipalooza harness gives every slot
  digital control lines, so the pin is free. The cost is plumbing one signal
  through four levels of hierarchy and ten devices, and it is the lower-risk
  option because the stage topology does not change.
- **Diode-connected pMOS loads** in place of the poly resistors. **Tried, and
  it is worse on every axis** — see below.

### The pin-free option does not work, measured

The attraction of a diode-connected pMOS load is that its resistance is `1/gm`
and `gm` follows the tail current, so the delay would fall as the current rises
and the tuning range would widen with no control signal at all.

`sim/decks/vco_pm2.spice`, sweeping the load's length from 0.5 to 2 µm and its
width over 1.5 and 3 µm (the first attempt used 0.13 µm and did not oscillate
at all, because a short-channel pMOS is a *strong* load however narrow it is):

| Lpl | Wpl | vctrl | frequency | swing |
|---|---|---|---|---|
| 0.5 µm | 1.5 µm | 0.50 V | 313 MHz | 0.219 V |
| 0.5 µm | 1.5 µm | 0.90 V | 340 MHz | 0.153 V |

**5 of 24 swept points oscillated at all**, and the one configuration that did
gives 313–340 MHz — half the required frequency — with a tuning range of
**1.08:1**, *narrower* than the 1.166:1 the poly resistor already delivers, and
a swing of 150–220 mV where the resistive ring gives 1.8 V.

The reason is worth keeping, because it rules out the whole family of
load-material substitutions. Two requirements fight:

- **oscillation needs gain**, `√(µn(W/L)n / µp(W/L)p) ≥ 1.24` for five stages,
  which wants a *weak* load — a long channel;
- **speed needs a small resistance**, which wants a *strong* load — a short one.

With a poly resistor those two are set independently: the resistance fixes the
delay and the input pair fixes the gain. With a diode load they are the same
device, and at 1.2 V there is no sizing that satisfies both.

### Why no load change can widen the range

More fundamentally: with any resistive load the **rising** edge is RC-limited
whatever the tail current is doing. The current sets the falling edge and the
swing; the rise is `R·C` regardless. So the control voltage only ever governs
half the delay, and only weakly — which is exactly the 1.166:1 measured, and
why swapping what the load is made of does not help.

Wide tuning needs *both* edges current-controlled, which means a
current-starved CMOS inverter ring — a different oscillator, not a component
substitution. That is a larger change than adding two control bits, and it
would end this cell's status as a mechanical port of the sky130 original.

So the options are: two control bits, a different oscillator, or accept the
limitation as the sky130 project did.

## 5. The CDR: five faults, one shape

The closed loop did not work when the port was mechanically correct, and
getting it to lock took five fixes. Every one of them was the same fault:
a stage biased for 1.8 V whose margin does not exist at 1.2 V. None announced
itself — each simulated cleanly and returned a plausible static answer.

They are recorded in the order they were found, with the measurement that
found each, because the *sequence* is the point: each fix exposed the next
fault, and none of them was visible until the one before it was fixed.

### 5.1 The ring did not start (testbench, not circuit)

First run: control voltage settled at 0.661 V with 1 mV of ripple, CTLE
equalising correctly, recovered clock **49 nanovolts**. Three of those four
numbers are what a working receiver looks like.

The ring was never oscillating. All five stages at the same voltage is a valid
DC solution and the simulator has no noise to leave it with. The control
voltage was quiet *because* there was no clock for the detector to compare
against, so the charge pump never fired. `.ic` on two ring nodes fixed it —
but only once the control voltage was *also* seeded, because until the startup
precharge releases at 76 ns the ring has no tail current and the kick has
decayed by then.

**A settled control voltage is not evidence of lock.**

### 5.2 `diff_amp_inv` could not drive a copy of itself

With the ring running, the clock still did not reach the pin. Walking the chain
(`sim/decks/e2e_diag*.spice`) localised it precisely:

| probe | pk-pk |
|---|---|
| ring, stage 1 output | 1.84 V differential |
| ring's buffered output | 1.93 V differential |
| inside `inverter_buffer` | 11.8 mV, sitting at 1.1999 V |
| the pin | 67 nV |

The differential-to-single-ended stage had an output common mode of 0.336 V
while the next copy of the same cell needs about 0.9 V — Vgs of 0.225 V, below
threshold. The first instance works because the ring's internal nodes sit high;
the second is fed by the first and starves.

Fixing it needed **two** conditions met at once, and the first attempt met only
one: the output must sit high enough to cascade, *and* it must cross the
switching threshold of the CMOS inverter it eventually drives. Shrinking the
second tail to W = 1 µm fixed the cascade and broke the interface — common mode
0.88 V, low excursion stopping at 0.57 V, the inverter moving 151 mV and never
switching. W = 2 µm swings 0.35–1.17 V and meets both.

**One cell doing two incompatible jobs.** At 1.8 V both fitted one sizing
comfortably. Splitting it in two is the better answer if it ever needs margin.

### 5.3 The phase detector's latches were starved

Clock at the pin, loop still open: the charge pump's up and down inputs both
measured **1.2000 V** with 1.6 mV and 4.5 mV of movement. Both switches held
on, the pump delivering only its own mismatch current.

Same two causes. The CML tail was drawn at L = 0.13 µm with its gate on
`vbias` — 0.9 V against a 0.7 V threshold on sky130, 0.43 V here against a
threshold that is *higher* at 0.13 µm than at 0.3 µm in this process
(`char/mos.spice`: 0.314 V at 0.30 µm, 0.241 V at 1.0 µm — the roll-off runs
the opposite way to the usual intuition). And the CML nodes drive CMOS
inverters switching near 0.55 V, which at the ported 2.24 kΩ load needs 290 µA
per latch across eight latches.

`sim/decks/dff_tune.spice` found a sharp boundary — at Wtail 16 µm / 4 kΩ the
output moves 15 mV; at 24 µm / 6 kΩ it is rail to rail. Fingering the tail to
stay inside the model's width range *moved* that boundary, so the sweep was
re-run rather than assumed to carry over. It had not carried over for the CTLE.

### 5.4 The charge pump was five times too strong

The loop finally acted, and slammed the control voltage rail to rail: 0.880 V
at 80 ns, 0.486 at 100, 0.964 at 120, 0.447 at 150, 0.3 mV by 200 — at which
point the ring stops and the precharge has long released.

Measured (`sim/decks/cp_current.spice`): 7.56 µA up and 7.49 µA down into
147.5 fF, so `I·UI/C` = **84.7 mV per update** against sky130's proven 17.5 mV.
On a 310 MHz/V oscillator that is 25 MHz of frequency step per unit interval.

Three full lock runs settled the reference resistor:

| Rbias | quantum | frequency | error | ripple |
|---|---|---|---|---|
| 12 kΩ | 20.5 mV | 600.42 MHz | −0.031 % | 177 mV |
| 24 kΩ | 10.1 mV | 600.59 MHz | −0.002 % | 78 mV |
| 36 kΩ | 7.0 mV | 600.36 MHz | −0.040 % | 57 mV |

Not sky130's voltage, deliberately: a bang-bang loop cares about the *phase*
step, `2π·Kvco·ΔV·UI`, and 17.5 mV at 357 MHz/V is 3.7° per UI. This ring is
310 MHz/V, so the same phase step wants ~20 mV. Copying the voltage would have
been 15 % out.

### 5.5 The ripple was the loop filter, not the loop

At 24 kΩ the loop locked with 78 mV of ripple against sky130's 33.7 mV. The
ratio of ripple to update quantum was 7.7 at *every* pump setting — 177/20.5,
78/10.1, 57/7.0 — which looks exactly like a limit cycle whose amplitude is set
by loop latency.

**It is not, and that reading would have cost a great deal of work.** The
filter is `vctl —[R]— cap_plus —[C1]— gnd` with C2 straight from `vctl` to
ground. On the timescale of one update C1 is hidden behind the series resistor
and only C2 absorbs the charge:

    ripple = I · UI / C2

Both capacitors are MOS caps, so their ratio is their gate-area ratio: 14.4 µm²
and 2.2 µm² split the measured 147.5 fF into 128 fF and 19.5 fF, predicting
**76.7 mV against 77.9 mV measured** — 1.5 %. The mechanism is settled, and the
7.7 was just `C_total/C2`.

Tripling both capacitors (keeping the ratio, so damping is unchanged) took the
ripple to 43.9 mV — against 25.8 mV predicted. The remainder is the
**proportional step**: the same current also flows through the series resistor,
and `I·R` = 27 mV lands on `vctl` instantly where C2 cannot absorb it. Halving
R to 15 kΩ took the total to **25.7 mV**, below the original.

### The result

| quantity | this design | sky130 original |
|---|---|---|
| recovered clock | **600.614 MHz** | 600.64 MHz |
| frequency error | **+0.0023 %** | +0.006 % |
| control-voltage ripple | **25.7 mV** | 33.7 mV |
| control voltage at lock | 0.599 V | 0.792 V |
| recovered clock at the pin | 1.30 V pk-pk | — |

One pattern, one corner, one operating point. The sky130 project measured a
great deal more than that.

## 6. PRBS7, and what the charge-pump mismatch actually does

`sim/results/e2e_prbs.log` — 3 µs transient, PRBS7 at 600.6 Mb/s, 200 mVpp
through the same worst-case channel, tt / 27 °C / 1.2 V.

| quantity | PRBS7 | 0101 | sky130 (PRBS7) |
|---|---|---|---|
| recovered clock | **600.581 MHz** | 600.614 MHz | — |
| frequency error | **−0.0032 %** | +0.0023 % | — |
| control voltage at lock | 0.59883 V | 0.59896 V | 0.799-0.802 V |
| control-voltage ripple | **65.3 mV** | 25.7 mV | 93.8 mV |
| ripple, PRBS7 / 0101 | **2.54×** | — | 2.78× |
| peak excursion, 1.5-3.0 µs | 68.8 mV | — | — |
| settled by | **< 1.5 µs** | — | ~3 µs |

Settling is proved rather than assumed: three separated averaging windows —
1.5-1.7, 2.1-2.3 and 2.7-2.9 µs — agree to **1.11 mV**, so any systematic
drift is below 0.93 mV/µs across the measurement.

The ripple ratio, 2.54× against sky130's 2.78×, is the expected result and for
the expected reason: PRBS7 has a transition density of about 0.5 against 0101's
1.0, so the detector updates half as often, the effective loop bandwidth
halves, and the dither grows. The absolute figure is lower than the original's
because the update quantum is (25.7/33.7 of it).

### The mismatch: 11 %, and it does not matter

The pump measures **0.895 µA up against 0.797 µA down — 11.0 % mismatch**,
where the sky130 original had 1.6 %. That looked like the thing PRBS7 would
expose, because mismatch is what integrates while the detector is blind.

It does not, and the reason is a number worth measuring rather than assuming:
**the both-switches-off leakage is 19.7 pA, not nanoamps.** During a run of
identical bits an Alexander detector deasserts both phases, so the pump sits in
that state, and over PRBS7's longest run — seven unit intervals — the control
voltage moves

    7 × 1.665 ns × 19.7 pA / 57.7 fF  =  4.0 µV

against 65 mV of ordinary dither. The mismatch cannot accumulate during a run
because the pump is not running during a run.

What the mismatch does instead is bias the up/down duty cycle in lock, which a
bang-bang loop absorbs as a static phase offset rather than a drift. Two
measurements say it is absorbed: the three settling windows agree to 1.11 mV,
and the PRBS7 lock point sits at 0.59883 V against 0101's 0.59896 V — **0.13 mV
apart**, on patterns whose transition densities differ by a factor of two.

The prediction written down before the run was that a detector holding one
phase through a seven-UI run would move the control voltage 182 mV, and that
mismatch alone would move it 10 mV. Neither happened, and the reason is that
both hypotheses assumed the pump was doing *something* during a blind run. It
is not. Predicting two outcomes and measuring a third is the useful case: it
was the assumption common to both that was wrong.

### One number that is not comparable

`ctle_swing` and `cin_swing` read 462 mV and 195 mV on PRBS7 against 248 mV and
63 mV on 0101, and that is not a fourfold improvement in anything. They are
peak-to-peak over a 200 ns window, and PRBS7 contains runs long enough for the
channel to settle to the full 200 mVpp input, which 0101 at 300 MHz never
does. The 0101 numbers are the ones that describe the channel's high-frequency
loss; these describe its low-frequency pass-through. Comparing them would be
comparing two different measurements that happen to share a name.

## 5. Not measured

Stated plainly, because the difference between "measured" and "expected" is the
most valuable thing the sky130 project's logs carried:

- **Any data pattern but 0101 and PRBS7.** PRBS15, 8b/10b and longer
  consecutive-identical-digit runs are not run. PRBS7's longest run is seven
  UI; the sky130 design was checked to 15.
- **Acquisition from a cold start.** The lock runs seed the control voltage at
  0.62 V so the ring is running while the symmetry-breaking kick is still
  present. That deliberately bypasses the startup precharge cell, whose
  45-corner cold-start result is a sky130 result and is not reproduced here.
- **The loop at any corner but tt/27 °C/1.2 V.**
- **End-to-end eye and jitter.** No eye height, no eye width, no jitter number
  on IHP. Every jitter figure in the sky130 README is a sky130 measurement and
  none of them are reproduced here.
- **VCO tuning range over PVT.** Measured at tt/27 °C only.
- **Startup precharge over PVT.** The cell is ported and netlist-verified; its
  45-corner cold-start result is a sky130 result.
- **Layout.** Nothing drawn. No DRC, no LVS against a layout.
- **Noise and mismatch.** The PDK ships mismatch and statistical model sections
  (`mos_tt_mismatch`, `mos_tt_stat`) and neither has been exercised.

## 6. Why the expensive runs have not been done

A full CDR transient costs 7-20 minutes on the development VM and a 6 µs
end-to-end run costs 20-25, on a machine with 7.8 GB of RAM where an unguarded
ngspice has already forced a reboot once. Those runs are worth doing and are
the obvious next step; they are not worth doing before the ring oscillator's
sizing is settled, because every one of them would have to be repeated.

The order is deliberate: AC before transient, block before loop, open-loop VCO
reach before closed-loop acquisition.
