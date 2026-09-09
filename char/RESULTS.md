# SG13CMOS5L device characterisation

Every process constant used by `tools/port_from_sky130.py` and by the
parameterised decks in `sim/decks/` is measured here rather than taken from a
datasheet, so that a wrong constant shows up as a wrong measurement instead of
propagating quietly into every sizing decision.

Reproduce with:

```bash
. ./env.sh
cd char && ngspice -b caps.spice && ngspice -b mos.spice
```

## Passives — `caps.spice`

Resistors, W = 1 µm, L = 10 µm, measured as V/I at 1 V:

| device | measured | Ω/sq | sky130 counterpart |
|---|---|---|---|
| `rhigh` | 14.327 kΩ | ≈ 1416 (1360 sheet + contacts) | `res_high_po`, 320 Ω/sq |
| `rppd` | 2.655 kΩ | ≈ 260 | — |
| `rsil` | 78.3 Ω | ≈ 7 | — |

`rhigh` is 4.3× denser than sky130's high-sheet poly, which is the one place
this process is more generous than the original. The port solves the length
from the PDK's own expression, `R = 1.6e-4/w + 1360·l/(w − 0.04µ)` at b = 0,
rather than scaling geometry.

Capacitors, 10 µm × 10 µm = 100 µm², measured as |I|/ω at 1 GHz with 1 V ac:

| device | measured | density | note |
|---|---|---|---|
| `cap_cmomi` | 100.2 fF | **1.00 fF/µm²** | metal fringe, mmin 1 mmax 4 |
| `cap_cmomf` | 128.7 fF | **1.29 fF/µm²** | metal fringe, denser variant |
| `moscap_n` @ 0.6 V | 1.178 pF | 11.8 fF/µm² | voltage dependent |
| `moscap_n` @ 1.2 V | 1.267 pF | 12.7 fF/µm² | 7.6 % more than at 0.6 V |
| `moscap_p` @ 0.6 V | 389 fF | 3.9 fF/µm² | in depletion here |

**There is no MIM capacitor on this process.** sky130's `cap_mim_m3_1` is
2.0 fF/µm², so the densest *linear* option here, `cap_cmomf`, needs 1.55× the
area for the same capacitance.

The MOS capacitors are six times denser and are not used. The two capacitors in
this design are the CTLE degeneration capacitor and the loop filter, and both
need a capacitance that does not move with the voltage across it — the 7.6 %
swing measured on `moscap_n` between 0.6 V and 1.2 V is a *lower* bound on
that, because it is measured well into inversion; near threshold it is far
worse. The CTLE's degeneration node sits at roughly 0.3 V, which is exactly
where a MOS capacitor is at its most nonlinear.

## Transistors — `mos.spice`

Low-voltage devices, 1.2 V nominal, Lmin 0.13 µm, Wmin 0.15 µm.

| quantity | measured |
|---|---|
| NMOS Vth, L = 0.30 µm | 0.314 V |
| NMOS Vth, L = 1.0 µm | 0.241 V |
| PMOS \|Vth\|, L = 0.13 µm | 0.463 V |
| PMOS \|Vth\|, L = 0.30 µm | 0.432 V |
| PMOS \|Id\| at \|Vgs\| = 1.2 V, W = 1 µm, L = 0.13 µm | 173 µA/µm |
| PMOS \|Id\| at \|Vgs\| = 1.2 V, W = 1 µm, L = 0.30 µm | 79.8 µA/µm |

The high-voltage 3.3 V devices (`sg13_hv_nmos` / `sg13_hv_pmos`, Lmin 0.45 µm)
exist on this process and are **not** used: this build is single-rail on the
1.2 V core devices. See `docs/DESIGN.md` for what that costs and what it buys.

## Threshold extraction

Vth is extracted by constant current at 300 nA × W/L, which is a convention and
not a physical constant — a different convention moves these numbers by tens of
millivolts. They are used here only for headroom arithmetic, where that is
immaterial; nothing in the design is sized against them directly.
