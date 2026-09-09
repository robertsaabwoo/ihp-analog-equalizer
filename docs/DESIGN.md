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

Measured effect: tail current holds within **2.5 % across ±10 % of supply** and
within ±19 % across all 27 corners, and the Nyquist-gain spread falls from
15 dB to 6.1 dB.

### Final sizing and result

| parameter | value |
|---|---|
| input pair | W = 30 µm, L = 0.2 µm |
| tail | W = 40 µm, L = 1.0 µm, mirrored 10:1 from a 25 µA reference |
| load resistors | 3.5 kΩ (`rhigh`, W = 1 µm, L = 2.36 µm) |
| degeneration resistors | 900 Ω each |
| degeneration capacitor | 1.6 pF `cap_cmomf`, 35.3 µm square |
| input common mode | 0.70 V |
| supply current | 351 µA at 1.2 V (0.42 mW) |

`sim/results/ctle_ac_{tt,ss,ff}.log`, 27 corners: 3 process × 3 temperature
(−40/27/125 °C) × 3 supply (1.08/1.2/1.32 V), with the resistor and capacitor
corners moved *with* the MOS corner rather than left typical.

| quantity | this design | sky130 original |
|---|---|---|
| CTLE gain at Nyquist, nominal | **+13.17 dB** | +13.32 dB |
| CTLE gain at Nyquist, 27 corners | +9.39 … +15.51 dB | +11.71 … +14.40 dB |
| Boost (Nyquist − DC) | +4.9 … +7.9 dB | +6.30 … +7.90 dB |
| Channel + CTLE at Nyquist, nominal | **−0.71 dB** | ≈ −0.4 dB |
| Channel + CTLE at Nyquist, 27 corners | −4.44 … +1.60 dB | −2.03 … +0.66 dB |

The nominal number matches. The corner spread is wider, and it is temperature,
not process or supply: at 125 °C the Nyquist gain falls about 2.5 dB. The
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
and the "frequency" reported there is not a usable oscillation.)

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
