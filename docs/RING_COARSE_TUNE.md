# Coarse frequency tuning for the ring — design note

**Branch `ring-coarse-tune`. Not merged: it adds pins to the chip's
interface, which is a decision for the submitter, not for me.**

## The problem, quantified

`sim/results/vco_pvtf_{tt,ss,ff}.log`: the ring reaches 600.6 Mb/s at **8 of
27 PVT corners**. The failures point in opposite directions —

| corner | usable range | needs |
|---|---|---|
| ss / 125 °C / 1.08 V | 482 – 521 MHz | centre **+15.2 %** |
| ff / 125 °C / 1.32 V | 654 – 686 MHz | centre **−8.1 %** |

so no single sizing works: moving the centre up to rescue `ss` pushes `ff`
further out of reach. The required span of centre adjustment is
1.152 × 1.088 = **1.25:1**.

## How many bits

Not two, for the reason it first looks like. Each coarse state carries its own
`vctrl` tuning range — 542–632 MHz at tt/27 °C/1.2 V, a ratio of **1.166** —
so the coarse steps only have to *tile* the 1.25:1 centre range, not span it
point by point. Continuous coverage needs the step ratio `s ≤ 1.166`, and

    s^(n-1) >= 1.25   with s <= 1.166   ->   n >= 2.5

**Three states minimum; four (two bits) with margin**, spaced by
1.25^(1/3) = 1.078.

One bit is not enough, and it is worth seeing why, because the arithmetic
above makes it look close. Two states far enough apart to span 1.25:1 are
spaced 1.25, wider than the 1.166 each one covers, so they leave a hole: at
tt/27 °C/1.2 V the slow state would reach 493–575 MHz and the fast state
650–758 MHz, and 600.6 falls in the gap between them.

## The circuit

The ring is RC-limited by its own load resistor above the point where
oscillation starts, so the frequency is set by that resistance. Switching
parallel legs in and out moves it:

    state 00   8002 Ω              slowest
    state 01   8002 ‖ 102 kΩ = 7418 Ω
    state 10   8002 ‖  49 kΩ = 6877 Ω
    state 11   8002 ‖  33 kΩ = 6444 Ω   fastest

Each leg is a `rhigh` resistor in series with a **pMOS** switch from VDD. pMOS
and not nMOS: the ring's output node swings up to VDD, so an nMOS switch in
series would have `Vgs` collapse to zero exactly when the node is high and the
leg is most needed. The switch is sized so its `Ron` is under 5 % of the leg
resistance it is in series with.

Ten output nodes (five stages, two legs each) × two switchable legs = 20
resistors and 20 switches, so the design grows from 225 devices to about 265,
and by roughly 60 µm² of drawn area against the 2131 µm² it already occupies.

## Where it goes, and why not inside the stage

The legs attach to the ring's output nodes, which are visible at the
`ring_oscillator` level as `net1…net10`. Putting them there rather than inside
`ring_inverter` means the stage cell is untouched and stays a mechanical port
of the sky130 original — the netlist-equivalence check keeps working on it —
and the whole addition is contained in one schematic plus two new pins.

The cost is that it depends on xschem's auto-generated net names, which are
assigned in drawing order and are not stable across an edit. That is
`docs/SIMULATION_TRAPS.md` 2.3 waiting to happen, so a test asserts those ten
nets still exist and still carry five `ring_inverter` instances between them.

## Pins

Two active-low digital inputs, `fsel0b` and `fsel1b`, at 1.2 V logic levels,
plumbed through `ring_oscillator` → `CDR` → `ctle_cdr_rx`. Active low because
the switches are pMOS and an inverter per bit per stage would cost more than
stating the polarity in the datasheet.

The harness gives every slot digital control and status lines, so these cost
nothing but the decision to spend two of them.

## What has to be re-verified

Everything downstream of the ring, because the nominal load resistance changes
from 7355 Ω to 8002 Ω in state 00:

- VCO tuning range at all 27 corners, in all four states — the measurement
  that justifies the whole exercise;
- the lock test, since the nominal operating point moves;
- **not** the CTLE, which is not in this path.
