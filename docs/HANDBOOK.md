# Handbook

Everything about this design in one place: what it is, why every number is the
number it is, how to run it, what is proven and what is not. Written for
someone who has never seen the project. The other documents go deeper on single
topics and are linked where they do.

> **State, 2026-09-12.** `main` is a verified port that locks. The
> `ring-coarse-tune` branch adds a coarse frequency loop that fixes the port's
> one accepted limitation, and **its closed loop does not lock yet** — see §11.
> Numbers below are labelled with which of the two they belong to.

---

## 1. What the circuit is

A **receiver front end for a serial link**: it takes a differential data
stream that has been degraded by a lossy channel, undoes some of that
degradation, and recovers a clock from the data so the bits can be sampled.

```
   differential           ┌────────┐        ┌──────────────────────────┐
   data in, 200 mVpp ────►│  CTLE  ├───────►│           CDR            ├──► recovered
   through 500 Ω / 5 pF   └────────┘  eq_p  │  (phase detector, pump,  │    clock
                                       eq_m │   filter, ring VCO)      │    (2 phases)
                                            └──────────────────────────┘
```

Two pieces, and the second one is the interesting one.

**CTLE — continuous-time linear equalizer.** The channel is a low-pass: 500 Ω
in series with 5 pF to ground gives a pole at 63.7 MHz, which costs 13.7 dB at
the 300 MHz Nyquist frequency of 600.6 Mb/s data. A CTLE is an amplifier
deliberately built with *more* gain at high frequency than at low, so the two
responses cancel and the eye reopens. It is a differential pair whose source
degeneration is an RC rather than a resistor: at dc the resistor sets the gain,
and as frequency rises the capacitor shorts the resistor out and the gain
climbs. The ratio of the two is the **boost**.

**CDR — clock and data recovery, reference-less.** There is no crystal, no PLL
reference, no clock pin anywhere in the block. The only periodic thing
available is the data itself, and the loop has to build a clock from it that
lands in the middle of each bit. That constraint is responsible for most of
what is difficult here, and §4 is about why.

### Specification

| | |
|---|---|
| data rate | 600.6 Mb/s (UI = 1.665 ns) |
| input | 200 mV pk-pk differential, 0.70 V common mode |
| channel | 500 Ω series, 5 pF shunt, per leg |
| supply | 1.2 V single rail |
| process | IHP SG13CMOS5L, 130 nm |
| target | Chipalooza analog design challenge |

---

## 2. Where it came from

This is a **port**. The original is
[`ttsky-analog-equalizer`](https://github.com/robertsaabwoo/ttsky-analog-equalizer)
— the same receiver in SkyWater sky130 at **1.8 V**, built for Tiny Tapeout.
This repository moves it to IHP SG13CMOS5L at **1.2 V**.

Two thirds of the supply voltage is the fact that dominates the port. The gain
of a resistively loaded differential pair is `(gm/Id)·ΔV_load`, and `ΔV_load` is
what the supply buys: the output common mode cannot fall more than a threshold
below the *input* common mode without the input pair leaving saturation, at
which point the gain does not degrade gracefully, it collapses. sky130 could
spend up to 0.65 V on `ΔV_load`. 1.2 V affords about 0.45 V.

**Everything in `xschem/` except three cells is generated**, by
`tools/port_from_sky130.py`, from the sky130 schematics. Editing a generated
schematic by hand is undone the next time the port runs. The three native cells
are `inv_cp` (replaces a sky130 standard cell), `ibias_mirror` (§6.1) and
`coarse_loop` (§10, branch only).

---

## 3. The process, and what it forbids

SG13CMOS5L is the **CMOS-only** member of IHP's SG13 family. Four thin metals
and one thick. It has:

**no MIM capacitor · no HBTs · no inductors · no deep n-well · no Schottky
diodes**

The trap is that its PDK is an *overlay* on SG13G2, whose symbol library sits on
`XSCHEM_LIBRARY_PATH`. So a `cap_cmim` dropped into a schematic finds a symbol,
finds a model, simulates beautifully, and cannot be manufactured.
`test/test_device_set.py` exists for exactly this and fails the build if a
device outside the allowed set appears.

### Measured device constants

Everything the port's arithmetic uses is measured in `char/`, not taken from a
datasheet, so a wrong constant shows up as a wrong measurement instead of
propagating silently.

| passive | measured | note |
|---|---|---|
| `rhigh` | 14.327 kΩ at W=1 µm, L=10 µm | ≈1416 Ω/sq; **4.3× denser than sky130's high-sheet poly** — the one place this process is more generous |
| `rppd` | 2.655 kΩ | ≈260 Ω/sq |
| `rsil` | 78.3 Ω | ≈7 Ω/sq |
| `cap_cmomi` | **1.00 fF/µm²** | metal fringe |
| `cap_cmomf` | **1.29 fF/µm²** | denser fringe variant — the densest *linear* option |
| `moscap_n` | 12.7 fF/µm² at 1.2 V | 7.6 % less at 0.6 V; leaks (§10.4) |
| `moscap_p` | 3.9 fF/µm² at 0.6 V | in depletion there |

sky130's `cap_mim_m3_1` is 2.0 fF/µm², so the densest linear capacitor here
needs **1.55× the area** for the same value.

| transistor (LV, 1.2 V, Lmin 0.13 µm, Wmin 0.15 µm) | measured |
|---|---|
| NMOS Vth, L = 0.30 µm | 0.314 V |
| NMOS Vth, L = 1.0 µm | 0.241 V |
| PMOS \|Vth\|, L = 0.13 µm | 0.463 V |
| PMOS \|Vth\|, L = 0.30 µm | 0.432 V |
| PMOS \|Id\| at \|Vgs\| = 1.2 V, L = 0.13 µm | 173 µA/µm |
| PMOS \|Id\| at \|Vgs\| = 1.2 V, L = 0.30 µm | 79.8 µA/µm |

Vth is extracted at a constant current of 300 nA·W/L, which is a *convention*
and not a physical constant — a different convention moves these by tens of
millivolts. They are used only for headroom arithmetic.

The 3.3 V devices (`sg13_hv_nmos`/`sg13_hv_pmos`, Lmin 0.45 µm) exist and are
**not used**: this is a single-rail 1.2 V build.

The MOS models are **PSP 103.6 delivered as Verilog-A**, compiled to OSDI by
`tools/setup_pdk.sh`. Nothing simulates until that build succeeds. They are
characterised over **L = 0.13–10 µm**, and a longer channel extrapolates
silently — `test/test_device_geometry.py` catches it, and did (§10.6).

---

## 4. Why a reference-less CDR is hard

This is the conceptual core. Everything in §9 and §10 follows from it.

The phase detector is an **Alexander (bang-bang) detector**. It samples the
data three times per bit — on the two clock edges bracketing a transition and
in the middle — and from those three samples it says only **early** or **late**.
Not "how early". One bit of information per data transition.

Three consequences, and they are all load-bearing:

1. **It has no frequency acquisition at all.** With a frequency error the
   sampling phase slips continuously; early and late are each asserted for half
   of every beat period; the *average* detector output over a slip cycle is zero
   whichever side of the baud rate the VCO is on. A ring that cannot reach the
   baud rate never locks, at any control voltage, and it does not fail loudly —
   it produces a settled-looking control voltage and a plausible clock.
2. **It is blind during runs.** No data transition, no comparison. PRBS7 has
   runs of seven identical bits, so whatever the charge pump does when neither
   phase should fire gets integrated for seven unit intervals at a stretch.
   This is why 0101 data is the easy case and why every number measured on 0101
   needs a PRBS7 run before it means anything.
3. **The loop never settles, it dithers.** A bang-bang loop has no zero-error
   state; it hunts around the lock point by one update quantum. The control
   voltage ripple is `I·UI/C₂` plus the proportional step `I·R`, and the
   frequency measured over a short window is the dither, not the frequency.

### The loop, block by block

```
   eq_p/eq_m ──►│ Alexander PD │──► up/down ──►│ charge pump │──► ±0.90 µA
                     ▲                                              │
                     │                                       ┌──────┴──────┐
                     │                                       │ loop filter │
                     │                                       │ R 15 kΩ     │
                     │                                       │ C1 378 fF   │
                     │                                       │ C2  58 fF   │
                     │                                       └──────┬──────┘
                     │                                              │ vctrl
                 recovered                ┌──────────────────┐      │
                 clock     ◄──────────────┤ 5-stage CML ring │◄─────┘
                                          └──────────────────┘
```

Measured directly (`sim/decks/cp_current.spice`): **0.90 µA per phase**, 436 fF
of loop filter of which 58 fF is the bypass C2, a 15 kΩ series resistor, and
therefore **10.1 mV per bang-bang update**. The pump's up/down **mismatch is
11.0 %** — a number that turns out to matter enormously in §10.2.

The loop filter is `vctrl —[R]— cap_plus —[C1]— gnd` with C2 straight to ground.
Getting that topology backwards changes what the ripple is made of.

---

## 5. The blocks, and the sizing that is the design record

`tools/port_from_sky130.py` holds a `SIZING` dict. **That dict is the design
record**: every entry carries the measurement that justifies it, and changing a
device size means editing it and re-running the port, not touching a schematic.

### 5.1 CTLE

| device | size | why |
|---|---|---|
| M1, M4 input pair | W 30 µm, L 0.2 µm, 6 fingers | gm/Id at the available headroom |
| M2 tail | W 40 µm, L 1.0 µm, 8 fingers | mirrors `ibias`; long for output resistance |
| R1, R2 load | 3500 Ω | sets `ΔV_load` inside the 0.45 V the supply affords |
| R3, R4 degeneration | 900 Ω | sets dc gain, hence boost |
| CS degeneration | 1.6 pF `cap_cmomf` | **35.3 µm square, 1243 µm²** |

That capacitor is **58 % of the drawn device area of the whole design on
`main`**, and it is the single largest object in it. That is the no-MIM tax.

It also must not be a MOS capacitor, for a reason separate from leakage: a
degeneration network's value must not move with the voltage across it, and the
degeneration node sits at roughly 0.3 V, which is where a MOS capacitor is at
its most nonlinear.

**Fingering bites.** Splitting the tail into fingers changed the mirror ratio —
tail current fell 351 → 253 µA and gain 13.17 → 12.10 dB. Recovered to
12.79 dB by raising the reference current 25 → 40 µA. PSP's width-dependent
terms and the diffusion geometry both follow `w/ng`, not `w`.

### 5.2 Ring oscillator

Five CML stages in a ring with one inversion, so the period is ten stage
delays, plus a `diff_amp_inv` buffer hanging off it (not in the loop, but it
loads one stage).

```
    VDD --[Rload]-- vo+        vo- --[Rload]-- VDD
                     |          |
    vin+ --|M1                       M4|-- vin-
                     +---- st ---+
                           |
                  vctrl --|M5   W 9 µm / L 0.13 µm
                           |
                          VSS
```

| | `main` | `ring-coarse-tune` |
|---|---|---|
| M1/M4 input pair | W 3 µm, **L 0.9 µm** | W 3 µm, **L 0.7 µm** |
| R1/R2 load | **7355 Ω** | **9000 Ω** |
| trim leg | — | pMOS W 4 µm / L 1 µm across each load |

The delay splits into two parts, measured (`sim/decks/vco_rsweep.spice`), a
straight line from 3500 to 9000 Ω:

```
    stage delay = 61.0 ps + 13.100 ps per kilohm of load
```

61 ps is the pair's own transit time, which no load trimming touches. The rest
is RC. At 7355 Ω the load is 61 % of the delay. **This one equation explains
most of §9 and §10.**

### 5.3 Phase detector, pump, filter

| cell | detail |
|---|---|
| `alexander_phase_detector` | four `d_flip_flop` + two `robs_xor` |
| `d_latch` | M2 tail W 24 µm L 1 µm 4 fingers; R1/R3 6000 Ω |
| `tiny_pll_bias_gen_res` | R[2..0] 24 kΩ each |
| `tiny_pll_loop_filter_res` | 15 kΩ |
| `tiny_pll_loop_filter_cap1` | MOS cap, m = 18 → 378 fF |
| `tiny_pll_loop_filter_cap2` | MOS cap, m = 3 → 58 fF |
| `vctrl_precharge` | one-shot RC startup pull-up, releases at 76 ns |

Those two loop-filter capacitors *are* MOS capacitors, inherited from the
original. They sit on the same node the coarse loop later found unusable for a
MOS capacitor (§10.4); the difference is that they are 8× smaller and the fine
loop actively regulates the node, so their leakage is inside the loop rather
than integrated by it. That is an argument, not a measurement.

---

## 6. What the port changed, and why

The mechanical port — same topology, devices translated, passives solved by
*value* rather than scaled by geometry — was proven correct and then did not
work. Five faults, all the same shape: **a stage biased for 1.8 V whose margin
does not exist at 1.2 V.** None announced itself; each simulated cleanly and
returned a plausible static answer, and **each was invisible until the one
before it was fixed**. `docs/DESIGN.md` §5 has them in full.

### 6.1 The bias stopped being a voltage

The sky130 macro took `vbias` in as a *voltage* and fed it to the CTLE tail and
the CML tails. At 1.2 V that gives a **15 dB spread** in Nyquist gain across
corners: +14.2 dB at ss/−40 °C/1.32 V and **−1.3 dB** at ff/−40 °C/1.08 V, where
the input pair leaves saturation and the gain collapses.

A gate voltage does not specify a current once threshold voltage and mobility
move. So the pin became `ibias`, a **current** that the Chipalooza harness's
bandgap-referenced source pushes in, and `ibias_mirror` — one diode-connected
replica — turns it into whatever gate voltage that current needs at that corner.
Measured afterwards: tail current holds within **1.4 % across ±10 % of supply**.

One pin, one transistor, no on-chip reference.

### 6.2 The ring never started (testbench, not circuit)

First closed-loop run: control voltage settled at 0.661 V with 1 mV of ripple,
CTLE equalising correctly, recovered clock **49 nanovolts**. Three of those four
numbers are what a working receiver looks like.

The ring was not oscillating. All five stages at the same voltage is a valid dc
solution and the simulator has no noise to leave it with. The control voltage
was quiet *because* there was no clock for the detector to compare against, so
the pump never fired. `.ic` on two ring nodes fixed it — but only once the
control voltage was *also* seeded, because until the precharge releases at
76 ns the ring has no tail current and the asymmetry has decayed by then.

**A settled control voltage is not evidence of lock.** Every closed-loop deck
here measures clock swing and frequency separately because of this.

### 6.3 `diff_amp_inv` could not drive a copy of itself

The cell is instantiated twice — once as the ring's output stage, once in the
CDR to make the differential clock single-ended — with its bias pin tied to VDD
in both places. At 1.8 V that was crude and survivable. At 1.2 V the second
instance sees 11.8 mV of swing sitting at 1.1999 V while the ring itself is
swinging 1.84 V differential.

---

## 7. Verification: how the port was proven

`tools/check_port_equivalence.py` compares the sky130 netlist and the IHP
netlist **as graphs, terminal by terminal**, allowing for auto-generated net
renaming, and ignoring the things that are supposed to differ (device names,
geometry). It answers exactly one question: *is it the same circuit?*

Result on `main`: **21 subcircuits, 121 instances, every terminal on the same
net.**

This matters more than it sounds, because **xschem connects by coordinate**. A
symbol swapped for another whose pins sit forty units apart produces a netlist
that is silently a different circuit and a schematic that looks identical. A
list of expected new cells is maintained so a *real* difference cannot hide
among the intended ones.

`test/` holds 48 tests that need no PDK, no simulator and no network, and run
in under a second:

| file | what it prevents |
|---|---|
| `test_device_set.py` | a device that cannot be manufactured on CMOS5L |
| `test_device_geometry.py` | a channel length or width outside the PSP models' range |
| `test_hierarchy.py` | a cell that is defined but never instantiated, or vice versa |
| `test_port_tool.py` | the port's passive-value arithmetic, and that the two dual-loop schematic edits attach where they claim |
| `test_coarse_loop.py` | the generated coarse-loop schematic drifting from the include it came from |

---

## 8. Measured results (`main`)

Every number traces to a log in `sim/results/` produced by a deck in
`sim/decks/`. **Anything not measured says so** — that habit was the sky130
project's single most valuable one.

### The loop, locked, 0101 data

| quantity | this design | sky130 original |
|---|---|---|
| recovered clock | **600.614 MHz** | 600.64 MHz |
| frequency error | **+0.0023 %** | +0.006 % |
| control-voltage ripple | **25.7 mV pk-pk** | 33.7 mV pk-pk |
| control voltage at lock | 0.599 V | 0.792 V |
| settled? (1.0–1.1 µs vs 1.4–1.5 µs) | 0.5992 / 0.5990 V | — |
| recovered clock at the pin | 1.30 V pk-pk | — |
| CTLE input → output | 63 mV → 248 mV | 63.7 mV → 299 mV |

### PRBS7

| | |
|---|---|
| recovered clock | **600.581 MHz** |
| frequency error | **−0.0032 %** |
| control-voltage ripple | **65.3 mV pk-pk** |
| settled | under 1.5 µs |

2.5× the ripple of 0101, which is the detector going blind through runs of
seven and the pump's 11.0 % mismatch integrating while it does. Frequency
accuracy and settling both hold.

### CTLE across 27 PVT corners

3 process × 3 temperature (−40/27/125 °C) × 3 supply (1.08/1.2/1.32 V), with
resistor and capacitor corners moved *with* the MOS corner.

| quantity | this design (1.2 V) | sky130 (1.8 V) |
|---|---|---|
| Nyquist gain, nominal | **+12.79 dB** | +13.32 dB |
| Nyquist gain, 27 corners | +9.35 … +15.10 dB | +11.71 … +14.40 dB |
| boost (Nyquist − dc) | +5.05 … +7.80 dB | +6.30 … +7.90 dB |
| channel + CTLE, nominal | **−1.03 dB** | ≈ −0.4 dB |
| channel + CTLE, 27 corners | −4.45 … +1.26 dB | −2.03 … +0.66 dB |
| supply current | 336 µA (0.40 mW) | not published |

Half a dB below the original at nominal: the honest cost of two thirds of the
supply. The corner spread is wider and it is **temperature** — Nyquist gain
falls about 2.4 dB at 125 °C.

### Area

| device | count | drawn area |
|---|---|---|
| `cap_cmomf` | 1 | 1243 µm² |
| `rhigh` | 43 | 386 µm² |
| `sg13_lv_nmos` | 136 | 466 µm² |
| `sg13_lv_pmos` | 45 | 35 µm² |
| **total** | **225** | **2131 µm²** |

---

## 9. The one accepted limitation on `main`

`sim/results/vco_pvtf_{tt,ss,ff}.log`, usable points only (differential swing
above 300 mV, because a `meas` on a barely-moving node still returns a number).

| corner | usable range | 600.6 MHz |
|---|---|---|
| tt / −40 °C | 505–620 … 527–683 MHz | reachable |
| tt / +27 °C / 1.08 V | 534 – **604** MHz | reachable, 0.6 % margin |
| tt / +125 °C / 1.20 V | 559 – 599 MHz | **too slow** |
| ss / +27 °C / 1.32 V | 444 – 593 MHz | **too slow** |
| ss / +125 °C / 1.08 V | 482 – **521** MHz | **too slow, by 15 %** |
| ff / −40 °C / 1.32 V | **631** – 769 MHz | **cannot go slow enough** |
| ff / +125 °C / 1.32 V | **654** – 686 MHz | **cannot go slow enough** |

**8 of 27 corners can reach the baud rate.** (The sky130 original passed 6 of
11 — the same wall, measured more completely.)

The failures point in **opposite directions**, and that is what settles it. No
re-centring fixes both: moving the curve up to rescue ss pushes ff further out
of reach. A ring with a 1.2:1 tuning range cannot span a corner box that needs
1.54:1. The specification for a fix falls straight out of the table:

- worst slow corner, ss/125 °C/1.08 V: ceiling 521 MHz → needs **+15.2 %**
- worst fast corner, ff/125 °C/1.32 V: floor 654 MHz → needs **−8.1 %**

So: a coarse control spanning **1.25:1**.

Two candidates were rejected before the third was built. **Switchable
resistor legs under a digital control bit** — rejected on the grounds that the
Chipalooza slot has 1–3 analog pads and the pins were not available. **That
reasoning was wrong**: a band select would not use an analog pad, and every
slot has 24 dedicated digital inputs from the housekeeping registers
(`docs/CHIPALOOZA_SLOT.md` §4). The analog loop is still preferable — it needs
no configuration and no per-chip calibration — but this candidate is a live
fallback, not a closed door. **Diode-connected
pMOS loads** in place of the poly resistors — swept and rejected: 5 of 24
points stopped oscillating and the reachable range came out at **1.08:1**,
*narrower* than the resistor's 1.166:1, because with the transistor as the load
its process spread becomes the ring's spread.

---

## 10. The dual loop (`ring-coarse-tune`)

A **second, analog control loop**: a pMOS trim leg across each of the ten ring
load resistors, all gates on one global `vcoarse!` rail, driven by an integrator
fed from a window comparator on `vctrl`. No pins, no clock, no digital logic.
33 devices. Full write-up in `docs/RING_DUAL_LOOP.md`; this is the shape of it
and the four measurements that each refuted the design before it.

### 10.1 The knob has to be the load, not the current

The fine loop drives the ring's *tail current*. Above the point where a stage
can charge its own load faster than its RC, more tail current buys nothing —
the load resistor sets the ceiling, and the ceiling is what fails at
temperature. So the coarse knob moves the **load**.

The poly resistor sits at the *slow* end of the span and the pMOS only ever
speeds the ring up, so at `vcoarse = VDD` the trim is entirely absent and the
ring is the untrimmed circuit. There is no state in which the trim can make
things worse.

### 10.2 `vctrl` carries no sign, so the loop must search

The coarse loop's only possible error signal is `vctrl`, because there is no
second frequency in the chip to compare the ring against. The theory was that a
band which cannot reach the data rate rails `vctrl` high and one that cannot go
slow enough rails it low. **It was measured and it is wrong.**

`tools/band_probe.sh` re-ports the design with the ring load moved out of band
and runs the full closed loop:

| ring load | f reached | error | `vctrl` @1.0–1.1 µs | @1.4–1.5 µs | drift |
|---|---|---|---|---|---|
| 7355 Ω (locks) | 600.614 MHz | +0.002 % | 0.5992 V | 0.5990 V | −0.5 mV/µs |
| 8460 Ω (too slow) | 576.43 MHz | −4.02 % | 0.7101 V | 0.7531 V | **+107 mV/µs** |
| 6400 Ω (too fast) | 673.52 MHz | +12.14 % | 0.7557 V | 0.8223 V | **+167 mV/µs** |

Both wrong bands drive `vctrl` the **same way — up**. Two mechanisms, both
inherent: a bang-bang detector has no frequency discrimination (§4), and what
is left when the phase term averages out is the pump's one-signed **11.0 %
mismatch**. Trimming the mismatch would not rescue the sign; it would replace a
clean ramp with an aimless random walk, which is a *worse* detector.

The good news in the same table: `vctrl` is an **excellent lock detector** —
flat to half a millivolt per microsecond locked, a hundred times that out of
band, with one threshold separating all three cases.

So the loop is a **search halted by a window comparator**, and the same
pull-down branch serves as both the acquisition search and half the holding
trim, because the direction it wants in both cases is the same.

### 10.3 The search runs slow-to-fast, and that is not arbitrary

While unlocked, `vctrl` is railed at the **top** of the fine loop's range.
Capture therefore happens with `vctrl` still high, and the search must keep
going in the direction that lets the fine loop *reduce* `vctrl` to hold lock.
Slow-to-fast does that. Fast-to-slow would capture at the same railed `vctrl`
and then need headroom above the rail, which does not exist.

### 10.4 A MOS capacitor cannot hold this node

The first open-loop testbench showed `vcoarse` drifting 0.17 mV/µs while it was
supposed to be holding. Rebuilding the series switch changed it by 0.6 mV.
`sim/decks/cap_leak.spice` found the rest, all at 384 µm² and 0.42 V:

| capacitor | dc gate current | C | drift = I/C |
|---|---|---|---|
| `moscap_n` | **773 pA** | 4.19 pF | **184 mV/ms** |
| `moscap_p` | 13.7 pA | 1.20 pF | 11.4 mV/ms |
| `cap_cmomf` | 0.42 pA | 0.49 pF | 0.85 mV/ms |

`I/C` is volts per second of drift and does **not** improve by scaling the
capacitor, because the leakage scales with it. 184 mV/ms walks the whole trim
range in four milliseconds. `Ccoarse` is `cap_cmomf`, 1.05 pF, 812 µm².

### 10.5 A pMOS is not worth its own resistance

`trim_r.spice` confirmed the hand arithmetic to 1 % — a W 0.5 µm leg across
8000 Ω gives 6339 Ω, predicted −21 %, measured −20.8 %. In the ring the same leg
was worth **+5.6 %** of frequency where a real resistor of that value is worth
about +13 %.

A pMOS is only a resistor while it stays in triode. At the bottom of the swing
its source-drain voltage approaches its overdrive, it becomes a current source,
and it stops helping the **rising** edge — which is the edge the RC ceiling is
made of. About **43 % as effective** as the resistance it imitates. The width
was therefore swept in the ring, not calculated: **W = 4 µm**.

### 10.6 Measured behaviour of the loop itself

Open loop, `vctrl` driven by hand (`sim/decks/coarse_tb.spice`) — seconds per
question instead of the hours a closed-loop equivalent would cost:

| | tt / 27 °C / 1.2 V |
|---|---|
| cold start | retraces and parks at **1.185 V**, the slow end |
| search rate | **19.6 mV/µs** |
| search span | 0.134 → 1.201 V — the whole trim range |
| wrap | fires and restarts, repeatedly |
| **null** | **0.600 V** |

The window is **not a dead zone**: at 20 nA the input pairs are in weak
inversion and steer over ~130 mV, so between the thresholds both are partly on
and the loop settles where they balance. So "does `vcoarse` hold at
`vctrl` = 0.599 V?" has no good answer — it holds at whatever `vctrl` the null
is at. The null at 0.600 V against a locked `vctrl` of 0.599 V means the coarse
loop **regulates `vctrl` to the middle of the fine loop's range** rather than
merely tolerating it, with a restoring slope of ~28 (µV/µs) per mV. That also
disposes of the leakage question: it is a closed loop with a stable
equilibrium, not a capacitor left open.

Across its own nine corners the low wrap trip moves 0.023 → 0.205 V, the high
trip tracks VDD exactly, and the rate is flat to ±5 %. The null moves from
0.600 V at 27 °C/1.32 V to below 0.54 V at 125 °C — the nMOS pull-down and pMOS
pull-up pairs drifting against each other — and it drifts the *helpful* way,
because at 125 °C the fine loop wants a lower `vctrl` anyway.

Two things the toolchain caught on the way in. `Lsrc` was **15 µm**, outside
PSP's 0.13–10 µm characterisation: it simulates perfectly by extrapolation
while corresponding to nothing the foundry has measured. And the retrace pMOS
pulled ~150 µA, which killed the −40 °C run outright with *"Timestep too small,
trouble with node ibias"* — it had no reason to be fast, only fast compared to a
14 mV/µs search.

### 10.7 The ring the coarse loop needs

The trimmed ring at the original 0.9 µm pair still failed at tt/125 °C/1.08 V —
573.7 MHz against a 600.6 MHz baud rate, because two thirds of the stage delay
there is the 61 ps the trim cannot reach. `ring_lin.spice` swept the pair's
length at both binding corners:

| Lin | hot/low, trim ON | cold/high, trim OFF |
|---|---|---|
| 0.9 µm | 573.7 MHz | 367.5 MHz |
| **0.7 µm** | **710.4** | **462.7** |
| 0.5 µm | 960.6 | 601.2 |
| 0.13 µm | 1925.5 | 962.2 |

The ring must bracket 600.6 MHz from **both** sides. 0.9 µm cannot reach it from
below at the hot corner; 0.5 µm and shorter cannot get *under* it at the cold
corner. 0.7 µm is the only swept value that clears both.

The load went 7355 → 9000 Ω for a reason that only shows up in the floor. At low
tail current the ring is current-starved: stage delay is `C·swing/I` with
`swing = I·R`, so the frequency is `1/RC` and **stops depending on the current
entirely**. What stops it going slower is the swing dying. So the floor is set
by the load resistance alone and goes as **1/R** — which is also why nothing
done to the tail device could have moved it.

### 10.8 All 27 corners

**Fast end** (trim on, `vctrl` at VDD), MHz — worst **662.3 at ss/125 °C/1.08 V,
+10.3 %**:

| | −40 °C | 27 °C | 125 °C |
|---|---|---|---|
| tt | 886.6–1065.8 | 790.0–930.8 | 681.5–782.5 |
| ss | 839.0–1020.9 | 756.3–900.6 | **662.3**–765.6 |
| ff | 931.7–1104.3 | 819.9–954.7 | 697.7–794.8 |

**Slow end** (floor with usable swing), MHz — worst **566.3, −5.7 %**:

| | −40 °C | 27 °C | 125 °C |
|---|---|---|---|
| tt | 439.6–517.9 | 461.2–494.4 | 519.2–527.1 |
| ss | 425.8 | 481.5–504.5 | 549.0–**566.3** |
| ff | 428.6–469.6 | 450.7–483.7 | 510.0–516.4 |

Every corner brackets the baud rate. **As a ring characterisation this is
solved.** §11 is why that is not yet the same as a working receiver.

Costs, recorded rather than buried: the fast-end margin fell from 15.2 % to
10.3 %, and the design is **off-centre at nominal** — at tt/27 °C/1.2 V the fine
loop locks at about `vctrl` = 0.55 V with the trim at its slow rail, so the
coarse range is spent entirely on corners needing the ring faster. Centring
would need ~10000 Ω and take the worst ceiling to ~617 MHz; 2.8 % is not enough
margin to spend on centring.

Area on the branch: **268 devices, 3094 µm²** (up from 225 / 2131).

---

## 11. What is not working, and what is not known

### 11.1 The branch does not lock

The closed loop on the new ring reaches **667.9 MHz, +11.2 %**, with `vctrl`
climbing at ~75 mV/µs — §10.2's out-of-band signature.

Critically, that is `e2e_lock` with the **coarse loop pinned off**. So it is not
a coarse-loop bug; the fine loop alone does not lock on the new ring.

Reseeding `vctrl` from the old ring's 0.62 V to the new ring's 0.55 V did not
fix it. The evidence points at the **startup precharge**: `vctrl_precharge`
pulls `vctrl` up and releases at 76 ns, and on the old ring that was harmless
because the whole tuning range topped out around 597–620 MHz — even fully
precharged the ring was inside the capture range. The new ring reaches
**863 MHz at `vctrl` = 1.2 V**, ~44 % above the baud rate, from which a
bang-bang detector cannot recover.

If that is right, it is a real design change (the precharge must release near
the new lock point) and not a testbench fix. **It has not been directly
measured** — the run that would show it is the next thing to do.

### 11.2 The fine loop's capture range

One bound only: it does **not** capture a 2.7 % step from cold. That bounds the
*step* response. The swept case is different and is what the dual loop actually
relies on — a search at 0.44 %/µs dwells within ±1 % of target for four and a
half microseconds, three acquisition times. `e2e_dual_walk.spice` tests it and
has not completed.

### 11.3 Never measured, anywhere

- **eye diagram, jitter, BER** — the sky130 project's most informative result
  (0.120 UI RMS sampling-phase error against ±0.175 UI of worst-corner margin)
  has no counterpart here
- **PRBS15**, or any pattern but 0101 and PRBS7
- **cold-start acquisition** — every lock deck seeds `vctrl`, which bypasses the
  precharge, which §11.1 now suspects
- **Monte Carlo / mismatch** — nowhere in this design, including the ten trim
  legs, whose mismatch is deterministic jitter on the recovered clock
- **Kvco-driven jitter** — the new ring's control-line slope at its lock point
  is several times the old ring's, which converts control-line noise to jitter
  proportionately
- **layout** — no DRC, no LVS against a layout, no GDS.  The *flow* is now set
  up and proven end to end (`docs/LAYOUT.md`, `mag/`), but nothing has been
  drawn.

### 11.4 Known-stale documentation

`README.md` still carries the pre-coarse-loop framing, and at least one number
in it (charge-pump mismatch as 6.7 %) was later measured at **11.0 %**.

---

## 12. Running it

```bash
tools/setup_pdk.sh        # both IHP PDKs + the Verilog-A build, ~15 min
. ./env.sh                # PDK_ROOT, PDK, and a sanity check
tools/netlist.sh          # schematics -> sim/netlists/blocks.inc
python3 -m pytest test    # 48 tests, no PDK needed, under a second
```

`setup_pdk.sh` installs **two** PDKs, which is not redundancy:
`ihp-sg13cmos5l` is an overlay whose model libraries and symbols are ~500
relative symlinks into a sibling `ihp-sg13g2` checkout.

### The compute budget is a hard constraint

The development VM has **7.8 GB of RAM and 4 CPUs**, and an unguarded ngspice
has already exhausted host memory and forced a reboot.

- **Never run two ngspice processes at once.** `tools/safe_ngspice.sh` holds a
  global `flock` and enforces this; it also applies `ulimit -v`, a wall-clock
  `timeout`, a `/proc/meminfo` watchdog and `nice`.
- **Never use a bare `write foo.raw`** — it stores every node at every timepoint.
  `save` an explicit vector list.
- Sweep **inside** one ngspice run with `alter`/`alterparam` and `foreach`. The
  exception is the process corner, fixed by a `.lib` line at parse time, which
  genuinely needs one run each — `sim/run_corners.sh`.
- A full CDR transient costs 7–20 minutes; 6 µs costs 20–25.
- **numpy is not installed and must not be.** Analysis scripts are pure stdlib.

### Making a change

1. Edit `SIZING` in `tools/port_from_sky130.py` (device sizes) or
   `POST_PORT_EDITS` (structure). **Not the schematics** — they are generated.
2. `tools/netlist.sh`
3. `tools/check_port_equivalence.py <sky130 netlist> sim/netlists/ctle_cdr_rx_lvs.spice`
4. `python3 -m pytest test`

On the branch, `tools/apply_dual_loop.sh` does all of that as one step under the
ngspice lock, because doing the port without migrating the decks leaves a tree
where `e2e_lock.spice` still runs, still reports a lock, and is measuring a
different circuit than it claims.

---

## 13. The traps

`docs/SIMULATION_TRAPS.md` has twenty-eight, each of which produced a
*plausible wrong answer* rather than an error. The ones that cost the most:

| | |
|---|---|
| **xschem's `-r`** is `--no_readline`, not an rcfile flag — passing it gives a truncated netlist full of "Symbol not found" and **exit status zero** |
| **A ring started from a symmetric state never starts**, and looks like a broken circuit rather than a broken testbench |
| **A PWL source holds its last value forever** — run past the pattern and you measure the data source running out |
| **A short measurement window reports the bang-bang dither**, not the frequency |
| **A `meas` on an edge index that does not exist fails silently** |
| **`.ic` accepts a quoted expression, ignores it, and says nothing** |
| **`tran 20p 'tend'` with a `.param`** gives TSTOP zero and a wall of "RHS invalid" that never names the cause |
| **A swing filter on a buffered output measures the buffer** — it is rail-to-rail whatever the ring does |
| **A sizing key that matches nothing is silently ignored** (the instance was an xschem *vector*, `R[2..0]`, not `R0`/`R1`/`R2`) |
| **Units in a `.param`** — a stray `1e-6` produced a 22 pm capacitor that simulated fine and showed no peaking |
| **A differential pair does not steer on an input smaller than its overdrive** — a comparator sat at 586 mV, just under the following inverter's trip, and the stage it gated never fired |

---

## 14. Chipalooza

The harness is
[`sg13cmos5l_ocd_chipalooza`](https://github.com/RTimothyEdwards/sg13cmos5l_ocd_chipalooza):
an eighteen-slot analog frame in a Caravel-style openframe padframe ported to
SG13CMOS5L. Each slot gets 3.3 V and 1.2 V supplies through a pMOS power
switch, 1–3 dedicated analog pads, bandgap-referenced voltage and current
biases, shared analog lines, and digital control and status lines.

**There is no 1.8 V rail.** That is why this is a 1.2 V build and why §2 is the
whole story.

**This project is slot 2, with two dedicated pins**, assigned by email; the
schematic review is complete and it is green-lighted to start layout. No
deadline was given.

Both dedicated pins go to the differential input, which leaves **no pin for the
600.6 MHz recovered clock** — the shared analog bus is explicitly not for that
bandwidth, and the digital-output path crosses the chip through a synthesised
mux and an I/O pad. The answer is an on-chip **÷8 divider** to 75.1 MHz, built
from the CML latch this design already runs at 600 MHz. That is a schematic
change and it is not yet made. `docs/CHIPALOOZA_SLOT.md` §4 has the reasoning
and the rest of the pin plan.

Measured from the harness layout (`docs/CHIPALOOZA_SLOT.md`): every slot is
**537.15 × 273.00 µm = 146 642 µm²** — this design's 3094 µm² of drawn devices
is about 2 % of it — and every slot carries `vdd_1v2`/`vss_1v2`,
`vdd_3v3`/`vss_3v3`, `vbias`, `ibias[0..1]`, `analog_bus[0..3]`,
**`dig_in[0..23]`**, **`dig_out[0..11]`**, `clk` and `enable`.

Dedicated analog pads are the scarce resource and vary by slot: three on slots
5, 10 and 14; two on ten others; one on 4, 8, 11 and 15; none on 9.

This block needs **two analog pads** for the differential input, one of the
`ibias` lines, two of the twelve `dig_out` for the recovered clock, and the
1.2 V rail — so thirteen of the eighteen slots would take it.

---

## 15. Repository map

| path | what |
|---|---|
| `xschem/` | the design — 25 schematics, `ctle_cdr_rx.sch` is the top |
| `xschem/ctle_cdr_rx_lvs.sch` | one-instance wrapper; netlist **this** to get a `.subckt` |
| `tools/port_from_sky130.py` | the port, and the `SIZING` table that is the design record |
| `tools/check_port_equivalence.py` | netlist-graph comparison against the sky130 source |
| `tools/gen_coarse_loop.py` | generates the coarse-loop schematic from its SPICE include |
| `tools/apply_dual_loop.sh` | port + netlist + deck migration + tests, atomically |
| `tools/safe_ngspice.sh` | the resource guard. Use it. |
| `char/` | device characterisation — where the process constants come from |
| `sim/decks/` | testbenches; `*_p.inc` are parameterised copies for sweeping |
| `sim/results/` | the logs every number traces to |
| `docs/DESIGN.md` | what was measured, how, and what each number means |
| `docs/PORTING.md` | what changed from sky130 and why |
| `docs/RING_DUAL_LOOP.md` | the coarse loop in full |
| `docs/SIMULATION_TRAPS.md` | read this before writing a deck |
| `docs/LAYOUT.md` | getting into Magic from a standing start |
| `docs/CHIPALOOZA_SLOT.md` | the slot footprint and what it connects to |
| `mag/` | the layout flow: generate, DRC, LVS |
| `test/` | 48 repository-consistency tests |

---

## 16. Conventions worth keeping

- **Commit and push as you go.** Work has been lost to a crash on this machine.
- **Record negative results.** Several dead ends in the sky130 original were
  re-attempted across sessions because the failure had not been written down.
  The CTLE search in `docs/DESIGN.md` is written up *including* the three
  directions that did not work, and so are the two rejected coarse-tune
  candidates in §9.
- **Any number in a document must trace to a log or a deck.** If you cannot
  point at the run, do not write the number down.
- **If a measurement was not done, say "not measured"** rather than estimating.
  Distinguishing the two is the single most valuable habit this project
  inherited.
