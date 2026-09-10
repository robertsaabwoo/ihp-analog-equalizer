![tests](../../workflows/test/badge.svg)

# Equalizing serial-link receiver front end — IHP SG13CMOS5L

A continuous-time linear equalizer (CTLE) feeding a **reference-less bang-bang
clock-and-data-recovery loop**, for the Chipalooza analog design challenge on
IHP's SG13CMOS5L 130 nm process. There is no reference clock anywhere in the
block: the recovered clock is generated from the data itself.

This is a port of
[**ttsky-analog-equalizer**](https://github.com/robertsaabwoo/ttsky-analog-equalizer),
which is the same receiver in sky130 at 1.8 V for Tiny Tapeout. The circuit is
the same circuit — proven so at netlist level, not by eye — running on a
different process at 1.2 V.

- **[docs/PORTING.md](docs/PORTING.md)** — what changed and why. Start here if
  you know the sky130 design.
- **[docs/DESIGN.md](docs/DESIGN.md)** — what was measured, how, and what each
  number means. Start here if you want to check the claims.
- **[docs/SIMULATION_TRAPS.md](docs/SIMULATION_TRAPS.md)** — the IHP toolchain's
  silent failure modes. Start here if you are about to write a deck.

## Status, in one table

| | |
|---|---|
| **Ported and verified** | All 22 cells translated to the SG13CMOS5L device set, netlist-compared against the sky130 source: 21 subcircuits, 121 instances, **every terminal on the same net**. |
| **Re-designed and measured** | The CTLE, re-sized for 1.2 V and re-biased from a reference current, across 27 PVT corners. The ring oscillator, re-sized so it can reach the baud rate at all. |
| **Not measured** | **The loop has not been closed in simulation on this process.** No lock, no eye, no jitter, no BER. Every such number in the sky130 README is a sky130 number and none of them are reproduced here. |
| **Not started** | Layout. No DRC, no LVS against a layout, no GDS. |

That third row is the important one. What exists here is a verified port and
two re-designed blocks, not a characterised receiver.

## What the process forced

SG13CMOS5L is the CMOS-only member of the SG13 family: four thin metals and one
thick, **no MIM capacitor, no HBTs, no inductors, no deep n-well**. Two
consequences shaped this port.

**The degeneration capacitor.** The CTLE's degeneration RC is what makes it an
equalizer. sky130 built it from a MIM at 2.0 fF/µm²; the densest *linear*
option here is `cap_cmomf` at 1.29 fF/µm² (measured — `char/RESULTS.md`). The
MOS capacitors are six times denser and unusable: a capacitor whose value moves
with the voltage across it is exactly what a degeneration network must not
have. So the 1.6 pF capacitor is a 35 µm square and **68 % of the design's
drawn device area**.

**The supply.** 1.2 V instead of 1.8 V. The gain of a resistively loaded
differential pair is `(gm/Id) · ΔVload`, and ΔVload is what the supply buys —
the output common mode cannot fall more than a threshold below the input common
mode without the input pair entering triode, at which point the gain does not
degrade, it collapses. sky130 spent up to 0.65 V on ΔVload; 1.2 V affords
about 0.45 V.

## Measured results

Every number below comes from a log in `sim/results/`, produced by a deck in
`sim/decks/`. Numbers that were *not* measured say so.

### CTLE, 27 PVT corners

3 process × 3 temperature (−40/27/125 °C) × 3 supply (1.08/1.2/1.32 V), with
the resistor and capacitor corners moved *with* the MOS corner. Driven through
the specified worst-case channel: 500 Ω series, 5 pF shunt — a 63.7 MHz pole
costing 13.7 dB at the 300 MHz Nyquist frequency of 600.6 Mb/s data.

| quantity | this design (SG13CMOS5L, 1.2 V) | sky130 original (1.8 V) |
|---|---|---|
| CTLE gain at Nyquist, nominal | **+12.79 dB** | +13.32 dB |
| CTLE gain at Nyquist, 27 corners | +9.35 … +15.10 dB | +11.71 … +14.40 dB |
| Boost (Nyquist − DC), 27 corners | +5.05 … +7.80 dB | +6.30 … +7.90 dB |
| Channel + CTLE at Nyquist, nominal | **−1.03 dB** | ≈ −0.4 dB |
| Channel + CTLE at Nyquist, 27 corners | −4.45 … +1.26 dB | −2.03 … +0.66 dB |
| CTLE supply current | 336 µA at 1.2 V (0.40 mW) | not published |

Nominal lands half a dB below the original — the honest cost of two thirds of
the supply, after the load resistance and the reference current were both
trimmed for it. The corner spread is wider, and it is **temperature**: at
125 °C the Nyquist gain falls about 2.4 dB. The Chipalooza
proposal commits to 0–110 °C; −40…125 °C is simulated here because that is the
range the sky130 numbers were quoted over, and a comparison has to be like for
like.

### The bias had to stop being a voltage

The sky130 macro took `vbias` in as a voltage and fed it to the CTLE tail and
the CML tails. At 1.2 V that gives a **15 dB spread** in Nyquist gain across
corners — +14.2 dB at ss/−40 °C/1.32 V, **−1.3 dB** at ff/−40 °C/1.08 V, where
the stage has collapsed outright. A gate voltage does not specify a current
once threshold voltage and mobility move.

The top-level pin is now `ibias`, and one diode-connected replica
(`xschem/ibias_mirror.sch`) turns a reference current into whatever gate
voltage that current needs at the corner in question — a resource the challenge
harness gives every slot.

| | fixed voltage bias | current mirror |
|---|---|---|
| Nyquist gain spread, 27 corners | 15.5 dB | **5.8 dB** |
| Tail current over ±10 % supply | — | **±1.4 %** |
| Tail current over all 27 corners | — | ±25 % |

### Ring oscillator

A bang-bang phase detector is phase-only: it has **no frequency acquisition**,
so a ring that cannot reach the baud rate never locks at any control voltage.
The tuning range is a functional requirement, not a performance number.

| ring | range at tt/27 °C/1.2 V | 600.6 MHz reachable? |
|---|---|---|
| sky130 original at 1.8 V | 514 – 621 MHz | yes, 3 % margin |
| this design, ported unchanged to 1.2 V | 424 – 554 MHz | **no** |
| this design, input pair re-sized to L = 0.9 µm | **538 – 630 MHz** | yes, at vctrl = 0.60 V |

Sweeping `vctrl` across its whole range moves the frequency by only 1.3:1,
because above the point where oscillation starts the ring is **RC-limited by
its own load resistor** rather than current-starved — the same conclusion the
sky130 project reached. The frequency is therefore set by the load resistance
against the capacitance on the output node, and that capacitance is dominated
by the input pair's gate. Shortening the pair from 1.0 µm to 0.9 µm moves the
whole curve up by about 100 MHz and puts the baud rate inside the usable range
instead of above the top of it.

**That is enough at nominal and it is not enough over PVT.** The full corner
sweep (`sim/results/vco_pvtf_{tt,ss,ff}.log`, 3 process x 3 temperature x
3 supply, usable points only) says so plainly: **8 of 24 corners can reach
600.6 Mb/s.**

| corner | usable range | 600.6 MHz |
|---|---|---|
| tt / −40 °C / 1.20 V | 513 – 650 MHz | reachable |
| tt / +27 °C / 1.08 V | 531 – **602** MHz | reachable, 0.3 % margin |
| tt / +125 °C / 1.20 V | 557 – 595 MHz | **too slow** |
| ss / +125 °C / 1.08 V | 481 – **521** MHz | **too slow by 15 %** |
| ff / −40 °C / 1.32 V | **626** – 765 MHz | **cannot go slow enough** |
| ff / +27 °C / 1.08 V | 619 – 673 MHz | **cannot go slow enough** |

The sky130 original passed 6 of 11 corners, so this is not a regression — it is
the same wall, measured more completely. And the failures point in **opposite
directions**, which is what settles the question: at the slow corners the ring
cannot reach the baud rate, and at the fast corners its slowest usable
frequency is already 620–650 MHz, so it cannot come down to the baud rate
either. Re-centring cannot fix both. A ring tuning over 1.2:1 cannot span a
corner box that needs 1.54:1.

The table also specifies the fix. The worst slow corner needs **+15.3 %** and
the worst fast corner needs **−4.1 %**, so a coarse control that shifts the
ring's centre by about +16 %/−5 % in two or three steps covers the whole box:
two digital bits, which the harness supplies.

The fix is coarse tuning, and it has not been built. Two candidates: a
switchable load-resistor leg per stage under one digital control bit — the
harness provides the control lines — or diode-connected pMOS loads in place of
the poly resistors, whose small-signal resistance follows the tail current and
would widen the range without needing a control pin at all.

### Size

`tools/area_budget.py`, flattened from `ctle_cdr_rx`:

| device | count | drawn area |
|---|---|---|
| `sg13_lv_nmos` | 136 | 250 µm² |
| `sg13_lv_pmos` | 45 | 35 µm² |
| `rhigh` | 43 | 311 µm² |
| `cap_cmomf` | 1 | 1243 µm² |
| **total** | **225** | **1839 µm²** |

Drawn device area, not layout area — real layout is several times this. The
sky130 design flattened to 224 devices; the extra one is the bias mirror.

## The port is reproducible, and checked

`xschem/*.sch` are **generated** by `tools/port_from_sky130.py` from the sky130
source. Editing them by hand will be undone the next time the port runs; device
sizes live in that script's `SIZING` table, where each entry carries the
measurement that justifies it. CI re-runs the port on every push and fails if
the result differs from what is committed.

This matters because **xschem connects by coordinate**. A symbol whose pins sit
one grid step from the symbol it replaces rewires the schematic, netlists
without complaint, and simulates something else. So the port is checked as a
graph:

```console
$ tools/check_port_equivalence.py ttsky.spice sim/netlists/ctle_cdr_rx_lvs.spice
Port is structurally identical to the sky130 source:
21 subcircuits, 121 instances, every terminal on the same net.
```

It compares, per subcircuit, the pin list, the instance set, and the net on
every *named terminal* — matched by terminal role rather than netlist column,
since the two PDKs declare their symbol pins in different orders. It ignores
device sizes and models, which are supposed to differ. Deliberate design
changes are listed by name in the tool, so a new difference cannot hide among
them.

## Getting it running

```console
$ tools/setup_pdk.sh       # both IHP PDKs + the Verilog-A models
$ . ./env.sh
$ tools/set_pdk_paths.sh   # point the decks at your PDK_ROOT
$ tools/netlist.sh         # schematics -> sim/netlists/blocks.inc
$ sim/run_ctle_ac.sh       # 27 corners, ~10 minutes
```

`setup_pdk.sh` installs **two** PDKs, which is not redundancy: `ihp-sg13cmos5l`
is an overlay whose model libraries and symbols are symlinks into a sibling
`ihp-sg13g2` checkout. It also compiles the PSP 103.6 Verilog-A models to OSDI,
without which no transistor simulates — and the way ngspice reports their
absence is a warning, not an error.

Simulations must go through `tools/safe_ngspice.sh`, which caps memory and wall
time and watches `/proc/meminfo`. That is not a style preference: an unguarded
ngspice has OOM-crashed the development machine once already.

## Tests

```console
$ pip install -r test/requirements.txt
$ pytest test/
```

No PDK, no simulator, no network; the suite runs in well under a second. It
covers the things that fail *silently*:

- **the device set** — SG13CMOS5L has no MIM capacitor, but its PDK is an
  overlay on SG13G2 and the SG13G2 symbol library is on the search path, so a
  `cap_cmim` will resolve, netlist and simulate correctly, and be
  unmanufacturable. Nothing else in the flow catches that;
- **the hierarchy** — xschem resolves a missing symbol silently and emits a
  truncated netlist, which is then what LVS and every simulation trusts;
- **device geometry** — the PSP models are fitted over `L = 0.13…10 µm` and
  `W = 0.15…10 µm`, and that W is **per finger**. ngspice evaluates a 30 µm
  single-finger transistor without complaint and returns extrapolated numbers.
  This caught three: the CTLE's input pair and tail, after being re-sized for
  1.2 V;
- **the port arithmetic** — passives are converted by *value*, solving the IHP
  geometry from the PDK's own expressions. One of these tests exists because
  the capacitor solver had a stray factor of 10⁶ and produced a 22 pm
  capacitor, which simulated perfectly and showed no peaking at all.

## What comes next, in order

1. **Close the loop.** The CDR has not been simulated on this process. Until it
   locks, the ring-oscillator centring above is a necessary condition and not a
   demonstrated one.
2. **VCO tuning range over PVT.** Measured at tt/27 °C only. The 1.3:1 range is
   narrow against a corner spread that will be wider, and this is the number
   most likely to force a design change — a switchable load-resistor leg, or
   diode-connected loads in place of the poly resistors, would widen it.
3. **End-to-end eye and jitter**, which is where the sky130 project found the
   result worth reading: sampling-phase error of 0.120 UI RMS against ±0.175 UI
   of worst-corner margin.
4. **Layout**, against the Chipalooza slot footprint.

## Chipalooza

The challenge harness is
[`sg13cmos5l_ocd_chipalooza`](https://github.com/RTimothyEdwards/sg13cmos5l_ocd_chipalooza):
an eighteen-slot analog frame inside a Caravel-style openframe padframe ported
to SG13CMOS5L. Each slot gets its 3.3 V and 1.2 V supplies through a pMOS power
switch, dedicated pads, bandgap-referenced voltage and current biases, shared
analog lines, and digital control and status lines.

This block uses the 1.2 V rail, two dedicated analog pads for the differential
input, one bandgap-referenced current for `ibias`, and two digital outputs for
the recovered clock phases.

## Licence

Apache 2.0, matching the source design and the Chipalooza reference IP.
