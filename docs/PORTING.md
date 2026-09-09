# Porting a sky130 analog design to IHP SG13CMOS5L

What actually had to change, and what turned out not to. Written while doing
it, so the reasoning is the reasoning that was used rather than a tidy account
of it afterwards.

The source is
[ttsky-analog-equalizer](https://github.com/robertsaabwoo/ttsky-analog-equalizer):
a CTLE plus reference-less bang-bang CDR receiver, drawn in xschem for sky130
at 1.8 V, targeting Tiny Tapeout's custom-GDS analog flow.

---

## 1. The three things that make this port non-trivial

**The supply drops from 1.8 V to 1.2 V.** This is the one that costs. Nothing
in a resistively loaded differential stage cares about the process node as much
as it cares about how many volts it has to drop across the load resistor, and a
third of them are gone.

**SG13CMOS5L has no MIM capacitor.** The CTLE's degeneration capacitor is the
component that makes the equaliser an equaliser, and the densest linear
capacitor available is `cap_cmomf` at 1.29 fF/µm² against sky130's MIM at
2.0 fF/µm². The MOS capacitors are six times denser still and are not usable
here — a capacitor whose value moves with the voltage across it is exactly what
a degeneration network must not have.

**The transistors are faster.** 130 nm at 1.2 V against 150 nm at 1.8 V is a
gain, not a loss, everywhere that speed rather than headroom is the constraint.
That is the ring oscillator, and it is where this port improves on the original.

## 2. What did not have to change: the circuit

The port is mechanical, done by `tools/port_from_sky130.py`, and
`tools/check_port_equivalence.py` confirms that the result is the same graph:
21 subcircuits, 121 instances, every terminal on the same net.

That matters more than it sounds, because **xschem connects by coordinate**. A
symbol whose pins sit one grid step away from the symbol it replaces rewires the
schematic, netlists without complaint, and simulates something else. The port is
safe only because the pin geometry happens to line up exactly:

```
sky130_fd_pr/nfet_01v8       D(20,-30) G(-20,0) S(20,30) B(20,0)
sg13cmos5l_pr/sg13_lv_nmos   D(20,-30) G(-20,0) S(20,30) B(20,0)
sky130_fd_pr/cap_mim_m3_1    c0(0,-30) c1(0,30)
sg13cmos5l_pr/cap_cmomf      c0(0,-30) c1(0,30)
```

Both symbol libraries descend from the same xschem conventions. Do not assume
this for other PDK pairs — check, and check with a netlist comparison rather
than by eye.

Three cases needed more than a name swap:

- `nfet3_01v8` / `pfet3_01v8` are three-pin symbols carrying the bulk as a
  `body=` **parameter**. The IHP symbol has a real B pin at (20,0), so the port
  emits a label at that pin's transformed coordinate carrying the old `body`
  net. Connectivity is preserved rather than guessed, and the port log names
  every one of the 20 devices this happened to.
- `res_high_po`'s bulk pin disappears — IHP carries the body as `body=sub!`.
- One sky130 **standard cell**, `sky130_fd_sc_hd__inv_1`, sat inside the charge
  pump. Rather than drag a standard-cell library into an otherwise all-custom
  analog macro for a single gate, it becomes `xschem/inv_cp.sch`, two
  transistors, drawn with its A and Y pins at exactly `inv_1`'s coordinates.

## 3. Device substitutions

| sky130 | SG13CMOS5L | note |
|---|---|---|
| `nfet_01v8`, `nfet3_01v8` | `sg13_lv_nmos` | 1.2 V core device, Lmin 0.13 µm |
| `pfet_01v8`, `pfet3_01v8` | `sg13_lv_pmos` | |
| `res_high_po` (320 Ω/sq) | `rhigh` (1360 Ω/sq) | 4.3× denser; length solved from the PDK's own resistance expression |
| `res_xhigh_po_0p35`, `res_high_po_0p69` | `rhigh` | same |
| `cap_mim_m3_1` (2.0 fF/µm²) | `cap_cmomf` (1.29 fF/µm²) | **forced** — no MIM on this process |
| `sky130_fd_sc_hd__inv_1` | `inv_cp` (local) | |

Resistors and capacitors are ported by *value*, not by geometry: the target
resistance or capacitance is computed from the sky130 sheet/density, and the
IHP geometry is solved from the PDK's own expressions. Sheet resistances and
capacitor densities were measured rather than read off a datasheet — see
`char/`.

Channel lengths at the sky130 minimum (0.15 µm) map to the IHP minimum
(0.13 µm). Anything longer keeps its drawn length, because those lengths were
chosen for output resistance or matching and 130 nm does not change that
argument. Widths carry over unchanged and are then re-tuned per block; every
re-size is an entry in the script's `SIZING` table with the measurement that
justifies it.

## 4. The design changes, and why each was necessary

### 4.1 The bias becomes a current, not a voltage

The sky130 macro brought `vbias` in from a pin as a **voltage** and fed it
straight to the CTLE tail and to the CML tails in the phase detector.

Measured across 27 PVT corners at 1.2 V, that gives a **15 dB spread** in the
CTLE's Nyquist gain, and at the fast corner an outright collapse: +14.2 dB at
ss/−40 °C/1.32 V, −1.3 dB at ff/−40 °C/1.08 V. A gate voltage does not specify a
current once threshold voltage and mobility move, and at the fast corner it asks
for more current than the 1.2 V stack has headroom for. The stage does not lose
gain gracefully there — the input pair leaves saturation and the gain falls off
a cliff.

So the top-level pin becomes `ibias`, and `xschem/ibias_mirror.sch` — one
diode-connected replica of the CTLE tail at one tenth the width — turns it into
whatever gate voltage that current needs at this corner. The Chipalooza harness
gives every slot bandgap-referenced current sources, so this costs one pin and
one transistor and no on-chip reference.

Result: tail current holds within ±19 % across all 27 corners and within 2.5 %
across ±10 % of supply, and the Nyquist gain spread falls from 15 dB to 6 dB.

### 4.2 The CTLE is re-sized around what 1.2 V can afford

See `docs/DESIGN.md`. The short version is that the gain of the stage is

    gm · Rload  =  (gm/Id) · (Id · Rload)  =  (gm/Id) · ΔVload

and ΔVload is what the supply buys. The final sizing gives +13.17 dB at Nyquist
nominally, against the sky130 original's +13.32 dB.

### 4.3 The ring oscillator is re-sized, because the ported one cannot lock

Covered in `docs/DESIGN.md`. The sky130 ring reached 514–621 MHz at tt/27 °C —
3 % of margin over the 600.6 MHz baud rate, which is why it failed at 125 °C
and at low supply, and which the sky130 project accepted as a known limitation.
Ported unchanged to 1.2 V it reaches 424–554 MHz, which is not a limitation but
a non-starter: a bang-bang phase detector has no frequency acquisition, so a
ring that cannot reach the baud rate never locks at any control voltage.

The fix is available because the devices are faster, and it is the one place
this port is unambiguously ahead of the original.

## 5. What the port does not carry over

- **The Tiny Tapeout wrapper**: `info.yaml`, `src/project.v`, the `tt` GDS
  flow. Chipalooza's harness is a different shape — an eighteen-slot analog
  frame with per-slot power switches, bandgap-referenced biases and dedicated
  pads, assembled by the scripts in
  [`sg13cmos5l_ocd_chipalooza`](https://github.com/RTimothyEdwards/sg13cmos5l_ocd_chipalooza).
- **The magic layout work.** Nothing was drawn in the sky130 project beyond one
  pathfinder cell, and SG13CMOS5L layout starts from the IHP tech files rather
  than from those.
- **The behavioural model.** `model/rx_cdr_rnm.sv` is a real-number model of
  the *architecture*, and its constants are sky130 measurements. It is worth
  re-fitting to the IHP numbers; that has not been done.

## 6. The channel

The sky130 design existed because of a specific channel: Tiny Tapeout's shared
analog pin path, specified at under 500 Ω and under 5 pF, which is a 63.7 MHz
pole and costs 13.7 dB at the 300 MHz Nyquist frequency of 600 Mb/s data. It
closes the eye completely at the pad.

Chipalooza gives each slot **dedicated** analog pads, so that particular
channel is gone. The same 500 Ω / 5 pF model is kept here as the specification
anyway, for two reasons: it makes every number directly comparable with the
sky130 results, and it is a fair model of what the block is actually for — a
receiver behind a lossy path, whether that path is a mux, a package, or a
board trace. On Chipalooza the loss is external and under the tester's control,
which makes it *easier* to characterise, not harder.
