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
| CDR acquisition | does the loop lock? | not yet run | 7-20 min |
| end-to-end eye and jitter | is there an eye at the sampling instant? | not yet run | 20-25 min |

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

## 5. Not measured

Stated plainly, because the difference between "measured" and "expected" is the
most valuable thing the sky130 project's logs carried:

- **CDR acquisition.** The loop has not been closed in simulation on this
  process. The testbench pattern from the original is portable and the harness
  is in place; the run has not been done.
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
