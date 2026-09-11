# Automatic band selection, instead of external config bits

**Branch `ring-coarse-tune`. Design note — not built.**

`RING_COARSE_TUNE.md` specifies a two-bit coarse control that would take the
ring from locking at 8 of 27 PVT corners to all of them. That note assumes the
two bits come from outside. This one asks whether the chip can set them itself,
which matters because the harness's per-slot control-line budget **is not
defined anywhere in the published repository** — `chipalooza_frame_wrapper.v`
carries only the dedicated analog pads, and the README says the slot interface
"has not yet been formalized."

If the block calibrates itself, the question does not arise.

## The detector, and why it works without a reference

This is a **reference-less** CDR. There is no reference clock, so nothing can
directly measure whether the ring's frequency is right. What is observable is
the control voltage, and it says everything needed:

- a band that **cannot reach** the data rate → the detector pumps up every
  update → `vctrl` rails **high** and the ring is still too slow;
- a band that **cannot go slow enough** → pumps down → `vctrl` rails **low**.

Normal locked ripple is 26 mV on 0101 and 65 mV on PRBS7, and the usable
control range is roughly 0.5–0.75 V, so thresholds near 0.52 V and 0.85 V sit
far outside anything the loop does in lock. The detector is one window
comparator on one node.

That is what makes this tractable: a reference-less loop cannot measure its own
frequency error, but it announces a *band* error by railing.

## The sequencer

1. Start in the middle band, with the existing startup precharge seeding
   `vctrl`.
2. Wait for the loop to settle. Measured settling is under 1.5 µs on both
   patterns, so a timer of about 5 µs is comfortable.
3. Sample the window comparator.
   - inside → done, stop stepping;
   - railed high → step one band faster;
   - railed low → step one band slower.
4. On any step, **re-arm the startup precharge** (see the risk below) and
   return to 2.
5. Stop after one pass; do not hunt.

A 2-bit up/down counter, a three-way decision, a timer and a stop bit.

## The timer, which the design already has most of

There is no reference clock to count, and two options avoid needing one:

- divide the recovered clock, which is present as soon as the ring runs even
  when it is nowhere near the data rate — but a ÷4096 is twelve flip-flops,
  bulky to draw by hand;
- an RC one-shot. `xschem/vctrl_precharge.sch` **already is one**: a 240 kΩ
  resistor into an 8 × 8 µm MOS capacitor, two inverters, and a switch that
  removes itself afterwards, measured releasing at 76 ns. Scaling it to 5 µs
  is a resistor value.

The second reuses a cell that is already drawn, ported and verified in the loop.

## The risk, which is specific and known

**The low-side failure is self-destructive.** Below about 0.45 V the ring stops
oscillating altogether — measured, `vctrl` went to 13.7 µV and never recovered,
because with no clock the detector is blind and the charge pump never fires
again. If `vctrl` reaches the low rail before the sequencer notices, the signal
it depends on disappears at the moment it is needed.

Two consequences:

- the low threshold must sit **above** the oscillation floor — 0.52 V, not
  0.45 V — so the detector fires while the ring is still running;
- a band step must also **re-arm the startup precharge**, so a ring that has
  already stopped is restarted into the new band. The proposal contemplates
  this as `RST`, and the cell exists.

Note what is *not* proposed: an analog clamp holding `vctrl` above the floor.
The sky130 project built one and **permanently abandoned it** — near-vertical
subthreshold transfer, 28 mV of gate voltage moving the floor from 0.53 V to
1.0 V, no manufacturable landing in the window, and it fought the locked loop.
A digital band step plus a precharge re-arm sidesteps that, which is a
substantive argument for this approach over the analog one.

## Verilog or transistors

The harness supports synthesised blocks inside a slot: run through LibreLane,
take the `.pnl.v` for LVS and the `.mag` from stream-out.

For this FSM I would not. It is a 2-bit counter, a comparator and a timer — of
order a hundred devices — and drawing it keeps the slot all-custom. The
synthesis route drags a standard-cell library, a second LVS path and a
place-and-route flow into a block that has none of them, to save perhaps a day
of schematic work.

The one argument the other way: a synthesised FSM is easier for someone else to
read and change than a hand-drawn one, and this repository is meant to be
picked up by other people.

## What has to be true before building it

The architecture rests on the rail signal being real and stable, so that is
measured rather than assumed: `sim/results/e2e_band_{8460,6400}.log` run the
full loop with the ring deliberately 15 % too slow and 13 % too fast.

- If both rail cleanly, the sequencer above is straightforward.
- If the fast-side case kills the ring before railing, the precharge re-arm is
  not an optimisation but load-bearing, and the detector's timing has to be
  designed around how fast `vctrl` falls.
