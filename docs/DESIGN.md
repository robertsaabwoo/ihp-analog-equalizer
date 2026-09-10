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
| CDR closed loop | does the ring run, and does the clock reach the pin? | `sim/decks/e2e_lock.spice`, `e2e_diag*.spice` | 5-30 min |
| CDR acquisition | does the loop *lock*? | blocked -- see §5 | 7-20 min |
| end-to-end eye and jitter | is there an eye at the sampling instant? | blocked -- see §5 | 20-25 min |

The last two rows are the honest state of this repository. See §6.

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

### The tuning range does not cover PVT: 8 corners out of 24

`sim/results/vco_pvtf_{tt,ss,ff}.log` — 3 process x 3 temperature x 3 supply,
usable points only (differential swing above 300 mV, because a `meas` on a node
that is barely moving still returns a number).

| corner | usable range | 600.6 MHz |
|---|---|---|
| tt / −40 °C / 1.08…1.32 V | 501–617 … 525–680 MHz | reachable |
| tt / +27 °C / 1.08 V | 531 – **602** MHz | reachable, 0.3 % margin |
| tt / +125 °C / 1.20 V | 557 – 595 MHz | **too slow** |
| ss / +27 °C / 1.32 V | 443 – 590 MHz | **too slow** |
| ss / +125 °C / 1.08 V | 481 – **521** MHz | **too slow**, by 15 % |
| ff / −40 °C / 1.32 V | **626** – 765 MHz | **cannot go slow enough** |
| ff / +27 °C / 1.08 V | 619 – 673 MHz | **cannot go slow enough** |

**8 of 24 corners can reach the baud rate.** The sky130 original passed 6 of
11, so this is not a regression — it is the same wall, measured more
completely.

The failures point in *opposite directions*, and that is the part that settles
the question. At the slow corners the ring cannot reach 600.6 MHz; at the fast
corners its slowest usable frequency is already 620–650 MHz, so it cannot come
*down* to the baud rate either. No amount of re-centring fixes both: moving the
curve up to rescue ss pushes ff further out of reach. A ring whose tuning range
is 1.2:1 cannot span a corner box that needs 1.54:1.

That last number is the specification for the fix, and it comes straight out of
the table:

- worst slow corner, ss/125 °C/1.08 V: ceiling 521 MHz, needs **+15.3 %**
- worst fast corner, ff/−40 °C/1.32 V: floor 626 MHz, needs **−4.1 %**

So a coarse control that moves the ring's centre by about +16 %/−5 % in two or
three steps covers the whole box. Two digital bits.

### What would fix it, and what was not done

Coarse tuning. Two candidates, neither built:

- **A switchable load-resistor leg per stage**, under one digital control bit.
  The frequency is set by the load resistance, so paralleling a second resistor
  roughly doubles the reachable range. The Chipalooza harness gives every slot
  digital control lines, so the pin is free. The cost is plumbing one signal
  through four levels of hierarchy and ten devices, and it is the lower-risk
  option because the stage topology does not change.
- **Diode-connected pMOS loads** in place of the poly resistors. A diode load's
  small-signal resistance is 1/gm, and gm follows the tail current, so the
  delay falls as the current rises and the range widens with no control pin at
  all. A first attempt is in `sim/decks/ring_pm.inc` and did not oscillate: the
  stage gain of a CML pair with a diode load is roughly
  √(µn(W/L)n / µp(W/L)p), and a 2 µm/0.13 µm pMOS load makes it about 1, below
  the ≈1.24 a five-stage ring needs. The load has to be *weaker* — a longer
  channel — and that sweep has not been run.

## 5. The CDR: the ring runs, the clock does not reach the pin

The first closed-loop run reported a recovered clock of 55 nanovolts at the
output pin while the CTLE equalised correctly and the control voltage settled.
`sim/decks/e2e_diag*.spice` walks the chain to find out where it is lost, over
300 ns rather than 1500 ns so each attempt costs four minutes instead of thirty.

`sim/results/e2e_diag2.log`, differential where the signal is differential:

| probe | node | pk-pk |
|---|---|---|
| ring, stage 1 output | `x1.x2.x1.net1/net2` | **1.84 V** |
| ring's buffered output | `x1.x2.net4/net5` | **1.93 V** |
| inside `inverter_buffer` | `x1.x2.x11.net1` | 11.8 mV, sitting at 1.1999 V |
| inside the output `inverter_chain` | `x1.x3.net1` | 18 µV |
| the pin | `clkoutp` | 67 nV |

So **the ring oscillates, and it oscillates properly**: 1.84 V pk-pk, sustained
across three separated windows (5-25 ns, 150-200 ns, 250-300 ns), with the
startup precharge released and the control voltage at 0.614 V. The oscillator,
the loop filter, the precharge cell and the CTLE all work.

The clock dies at the **differential-to-single-ended stage in the CDR** — the
second `diff_amp_inv`, whose bias pin is tied to VDD. `inverter_buffer`'s first
inverter output sits at 1.1999 V, i.e. hard at the rail, which means its input
`clkraw+` is stuck below the inverter's switching threshold. A 1.93 V pk-pk
differential goes in and a static level comes out.

Two things about this are worth recording rather than tidying away.

**The first hypothesis was wrong.** Working the stage out on paper said its
first-stage load resistors would drop 0.9 V at 1.2 V and strand the second
stage's input pair below ground. Measured — `sim/decks/d2s_size.spice` — the
stage delivers a healthy 1.05 V differential output at a 0.85 V input common
mode. The arithmetic identified the right stage for the wrong reason, which is
the sort of thing that only shows up if you measure the block you suspect
instead of only the system.

**`clkraw+` cannot be measured directly.** Its name contains a `+`, which
ngspice's expression parser treats as an operator, so `v(x1.x2.clkraw+)` yields
nothing at all — no error. The probes above sit on the internal nodes either
side of it. The first attempt to work around that with a unity-gain source
referencing the hierarchical node failed differently and worse; see
`docs/SIMULATION_TRAPS.md` 2.8b.

### The cause: the stage cannot be cascaded with itself at 1.2 V

Probing inside the stage (`sim/results/e2e_diag3.log`) answers the puzzle of
why an *identical* `diff_amp_inv`, with the same VDD-tied bias, works one level
up as the ring's own output buffer:

| quantity | measured |
|---|---|
| ring's buffered output, common mode | **0.336 V** |
| ring's buffered output, swing per leg | 0.967 V pk-pk |
| next stage's first-stage tail node | 0.111 V |
| next stage's second-stage tail node | 0.033 V |

The next stage's input pair therefore has Vgs = 0.336 − 0.111 = **0.225 V**,
below threshold. It is off for most of the cycle.

The first instance works because its input is the *ring's internal nodes*,
whose common mode is high — the ring's load resistors pull toward VDD. The
second instance is driven by the first one's output, which is 0.34 V, and
starves. **The cell's output common mode is far below its own input
common-mode requirement, so it cannot drive a copy of itself.** At 1.8 V the
same mismatch still left enough Vgs to conduct.

### The fix, and why it took two attempts

The output common mode is set by the drop across the load resistors, so both
tails shrink. From `sim/decks/d2s_size.spice`, at an 0.85 V input common mode:

| tails | single-ended output swing | common mode |
|---|---|---|
| W=2, W=8/L=0.13 (as ported) | 0.07 – 1.13 V | 0.34 V |
| W=1, W=1/L=1.0 | 0.57 – 1.20 V | 0.885 V |
| W=1, W=2/L=1.0 | 0.35 – 1.17 V | 0.758 V |

There are **two** conditions and the first attempt met only one. The output has
to sit high enough to keep the next copy of the cell conducting — the cascade
condition, which the ported sizing failed. It also has to cross the switching
threshold of the CMOS inverter it eventually drives, near 0.5 V here.
`W=1, W=1` fixed the first and broke the second: common mode 0.88 V with the
low excursion stopping at 0.57 V, so the inverter downstream moved 151 mV and
never switched — the same static output as before, now stuck at the opposite
rail. `W=1, W=2` meets both.

Measured through the whole chain afterwards, closed loop, 250–300 ns:

| probe | pk-pk |
|---|---|
| ring, stage 1 output | 1.84 V differential |
| ring's buffered output | 0.75 V per leg, common mode 0.684 V |
| inside `inverter_buffer` | **1.19 V**, switching about 0.546 V |
| inside the output `inverter_chain` | 1.26 V |
| the pin | **1.30 V** |

### With the clock out, the loop still does not lock

`sim/results/e2e_lock_tt.log`, the full 1.5 µs run on 0101 data at 600.6 Mb/s:

| quantity | measured | what it should be |
|---|---|---|
| recovered clock at the pin | **1.31 V pk-pk** | a real clock — this is now right |
| recovered-clock frequency | **616.33 MHz** | 600.60 MHz — **+2.6 % off** |
| control voltage | 0.661 V | — |
| control-voltage ripple | **0.98 mV pk-pk** | tens of mV (sky130: 33.7 mV on this pattern) |
| control voltage, 1.0–1.1 µs vs 1.4–1.5 µs | 0.6573 → 0.6614 V | flat, if settled |
| CTLE, in → out | 62.9 mV → 271 mV | as designed |
| precharge release | 76 ns | as designed |

The signal path is now intact end to end: the channel attenuates 200 mVpp to
63 mV, the CTLE equalises it back to 271 mV, the ring oscillates, and a
full-swing clock comes out of the pin. **What is not happening is locking.**
The ring is free-running 2.6 % above the data rate, and the control voltage is
drifting upward at about 10 mV/µs rather than dithering about a lock point.

The 0.98 mV of ripple is the diagnostic. A bang-bang loop in lock corrects
every UI, and each correction moves the control voltage by a quantum — sky130
measured 17 mV per update and 33.7 mV pk-pk of resulting dither on exactly this
pattern. One millivolt means **the charge pump is delivering almost nothing**,
so the loop is open somewhere between the recovered clock and the loop filter:
the Alexander phase detector, or the charge pump's own bias.

The Alexander detector is the immediate suspect, and for the same reason as the
last two failures. Its CML latches are biased from `vbias`, which is now the
current-mirror node at about 0.43 V, where the sky130 design fed them 0.9 V.
Every failure in this port so far has been the same shape — a stage whose
operating point was set for 1.8 V and does not survive the supply drop — and
this one fits the pattern. `sim/decks/pd_diag.spice` measures the detector's
up/down outputs and the charge pump's bias to confirm or refute it.

### The phase detector: the same failure, twice over

Reading `d_latch` at 1.2 V before simulating it, there are two problems, and
they are the same two that broke `diff_amp_inv`:

**The tail is starved.** M2 is drawn at L = 0.13 µm with its gate on `vbias`.
On sky130 that was 0.9 V against a 0.7 V threshold — 0.2 V of overdrive. Here
`vbias` is the current-mirror node at about 0.43 V, against a threshold that is
*higher* at 0.13 µm than at 0.3 µm in this process: `char/mos.spice` measures
0.314 V at L = 0.30 µm and 0.241 V at L = 1.0 µm, so the roll-off runs the
opposite way to the usual short-channel intuition. Overdrive is a few tens of
millivolts and the tail barely conducts.

**The CML swing cannot reach the output inverters.** Nodes n1/n2 sit at
VDD − I·R and drive CMOS inverters that switch near 0.55 V, so the low
excursion has to get below that: I·R > ~0.65 V. At the ported 2.24 kΩ that
needs 290 µA per latch, and there are eight latches in the detector.

The fix follows the same shape as the D2S one: make the tail a **long-channel
replica of the mirror reference** — L = 1 µm, matching `MREF` — so that it both
conducts at 0.43 V and mirrors in a predictable ratio, and raise the load
resistance so the swing crosses the inverter threshold at a sane current.
`sim/decks/dff_tune.spice` sweeps both against realistic drive: the clock at
the ring's measured output levels (common mode 0.684 V, 0.75 V per leg) and the
data at the CTLE's (common mode 0.70 V, 271 mV differential), with the pass
criteria written into the deck rather than judged afterwards.

### The structural point, which is worth more than the fix

Three of the four failures in this port are the same failure. A stage was
biased for 1.8 V — a gate voltage, a tail length, a resistor value chosen so
that the swing comfortably cleared some threshold — and at 1.2 V the margin it
was relying on is simply not there. The CTLE tail sat in triode; the D2S stage
could not drive a copy of itself; the CML latch tail barely conducts and its
swing cannot reach a CMOS gate. None of them announce themselves: each one
simulates cleanly and produces a plausible static answer.

That is the general lesson of this port, and it is worth more than any of the
individual fixes: **porting an analog design to a lower supply is not a
translation, it is a re-establishment of every operating point.** The netlist
comparison proves the circuit is the same circuit. It says nothing about
whether any transistor in it is still in saturation.

The D2S stage has a second, sharper problem on top of that one.
One cell is doing two incompatible jobs. As the ring's output stage it must
hand a *high* common mode to an identical stage; as the CDR's stage it must
hand a *mid-rail crossing* to CMOS logic. At 1.8 V both fit one sizing
comfortably, which is why the sky130 design never had to separate them. At
1.2 V they barely coexist, and the honest recommendation is to split
`diff_amp_inv` into two cells — one tuned for cascading, one for the CMOS
interface — rather than keep squeezing a single sizing between two
constraints that are moving apart as the supply falls.

## 5. Not measured

Stated plainly, because the difference between "measured" and "expected" is the
most valuable thing the sky130 project's logs carried:

- **CDR acquisition.** The loop has been simulated and does **not** lock,
  because the recovered clock never reaches the phase detector's output stage —
  see §5. The ring itself is verified oscillating inside the closed loop.
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
