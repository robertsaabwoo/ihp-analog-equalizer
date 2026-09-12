# On-chip self-test: proving the receiver works without a 600 MHz pin

**Decision: the analog macro is not changed.** It keeps the interface it has —
`clkout_p` / `clkout_n` at 600.6 MHz — and the self-test is a separate Verilog
block inside slot 2, to be built later. Nothing below asks for an edit to the
receiver.

This document is therefore reference material for whoever writes that Verilog:
what the harness supplies, what the macro already exposes, and what the risks
are. Read §4 before sizing the block.

---

## 1. Why this is the right call

The recovered clock **is** a digital signal and belongs on `dig_out`. The
objection in `docs/CHIPALOOZA_SLOT.md` §4.1 was never about it being digital —
it was about **600 MHz**, and specifically about a path this project does not
own: a synthesised route from slot 2 across the chip to the central router,
through a 12-way combinational mux, into an `IOPadOut16mA`-class pad, a
bondwire and a package pin.

Testing on chip deletes that problem instead of working around it. It also
produces something the project has never had: **the recovered bits themselves**,
and a frequency measurement good to one count rather than to whatever a scope
probe on a degraded pad can resolve.

And it keeps the analog side frozen, which is the point: the receiver is
green-lit, and the dividing and counting move into logic that can be written,
simulated and changed without touching a transistor.

## 2. What the harness gives, and what it does not

**It does not store your results.** The harness has a 1024 × 8 SRAM, and it is
*stimulus only* — written over the housekeeping SPI, read by the pattern
generator to drive `dig_in[16:23]`. There is no write path from a user project
into it (`verilog/rtl/pattern.v`: *"The sequencer only reads from SRAM, and only
provides the address"*). So the results have to live in registers inside the
slot, and be read out through `dig_out`.

That is not a problem, because **readout is static**. Hold the result in a
register, select a 12-bit slice with a few `dig_in` bits, and read `dig_out` at
whatever rate the SPI manages. Nothing on the output path ever has to be fast.

**What it does give:**

| | |
|---|---|
| `clk` | a **top-level chip pin** — an external, known-frequency reference, in every slot |
| `dig_in[0..15]` | from the sequencer/counter |
| `dig_in[16..23]` | arbitrary bytes from the SRAM pattern generator |
| `dig_out[0..11]` | combinational path to a pin; static readout is trivial |
| `enable` | per-slot |

An external reference clock in the slot is exactly what a frequency counter
needs, and it arrives free.

## 3. Two signals the CDR already has

Neither needs new analog design.

**The recovered clock** is `clkout_p` / `clkout_n` at the macro boundary.

**The retimed data already exists inside the phase detector.** An Alexander
detector samples each bit three times — on the two clock edges bracketing a
transition, and in the middle. The *middle* sample is the recovered data, and
in `alexander_phase_detector` it is the pair `B+` / `B-`, the output of the
flip-flop `x3`. It is used today only to make `up`/`down`, and it is never
brought out of the macro.

**Bringing it out would be a macro edit, so it is not being done now.** Noted
because it is nearly free if the Verilog ever wants the recovered *data* rather
than just the clock — the tier 2 and 3 tests below need it, tier 1 does not.

So with the macro as it stands, the self-test block's inputs are: the 600 MHz
recovered clock, the harness `clk`, and control bits.

## 4. The risks, before the design

These are the reasons to stage this rather than build all of it.

**Digital switching noise next to a 200 mV analog input.** This is the serious
one. The receiver's input is 200 mV pk-pk differential and its ring is a
sensitive oscillator; a counter toggling at hundreds of megahertz a few tens of
microns away couples through the substrate and the supply. Mitigations exist
and the slot has room for them — the design uses about **2 %** of
537 × 273 µm — so the digital block goes at the far end of the slot, with its
own supply routing, guard rings, and physical separation. But "there is room"
is not "it is solved", and nothing here is simulated.

**Anything at 600 MHz in standard cells is not free.** A 130 nm standard-cell
flip-flop will toggle at 600 MHz, but with margin that has to be verified, not
assumed. Every tier below is arranged so the *smallest possible* amount of
logic runs at full rate.

**It makes this a mixed-signal project.** Digital logic means synthesis and
place-and-route (the harness ships `librelane`) or hand layout, and an LVS flow
that spans both. That is new work on top of a layout flow that has drawn
nothing yet.

**The schematic review is already done.** This adds a block after a green
light. Tim should hear about it before it is drawn, not after.

## 5. Staged proposal

### Tier 1 — frequency counter. Needs only the clock the macro already gives.

Proves the loop is locked to the data rate, exactly, and it is the whole of
what tier 1 needs:

```
clkout_p ──► ÷N ──► [ counter ] ──► dig_out
  600 MHz    in Verilog      gate from the harness clk pin
```

Count recovered-clock edges over a gate of N `clk` periods. Locked, the count
is exactly `600.6 MHz × N / f_clk`, divided by whatever ÷N the front end uses.
One number, read out statically, and it settles the question the whole project
turns on.

**The one thing to verify rather than assume:** the first divider stage sees
600 MHz in standard cells. A 130 nm flop will do it, but with margin that has
to be shown in STA and simulation, not taken on faith. If it will not close,
the fallback is a CML ÷2 built from `d_latch` — the latch this design already
runs at 600 MHz in the phase detector — but that is a macro change and is
explicitly out of scope today.

### Tier 2 — capture the recovered bits. Needs `B+`/`B-` brought out (§3).

A shift register that captures **128 consecutive recovered bits** on a trigger,
then stops. Read them out 12 at a time over `dig_out`, and check the pattern in
software off chip.

128 bits is one full PRBS7 period, so the captured word either is a rotation of
the PRBS7 sequence or it is not — and if it is not, you have the actual bits to
look at, which a pass/fail counter would never have told you.

This is deliberately *not* a checker. Putting the comparison off chip means the
on-chip logic is a shift register, a trigger and a readout mux, and it means
the test is not limited to the one pattern somebody anticipated.

**Cost:** 128 flops, of which all 128 shift at 600 MHz during the capture
window only, and are static before and after. The capture window is ~213 ns.
Consider 32 bits instead if the noise budget is tight.

### Tier 3 — PRBS checker and error counter. Only if the schedule allows.

Self-synchronising PRBS7 checker: predict each bit from the previous seven,
compare, count mismatches, alongside a total-bit counter. Gives **BER**
directly — the headline number for a receiver, which this project has never
measured (`docs/HANDBOOK.md` §11.3).

The honest objection is that Tier 2 gets most of this for a fraction of the
full-rate logic, because software can do the checking. Tier 3 earns its place
only when you want to run for seconds and count rare errors, which is the real
BER measurement and is genuinely worth having — later.

**Cost:** a 7-bit shift register, an XOR, a comparator and two counters, all at
full rate, or half that at half rate after a 1:2 demux.

## 6. Control and readout budget

Well inside what slot 2 has.

| `dig_in` | |
|---|---|
| 1 | run / halt |
| 1 | capture trigger |
| 1 | counter reset |
| 4 | readout slice select |
| 1 | **disable the coarse loop** — characterise the fine loop alone on silicon, as `e2e_lock.spice` does in simulation |
| 4 | **force `vcoarse`** — makes the ring's tuning curve measurable on a real die, and is the switched-leg band select if the dual loop cannot be made to lock |
| **12 of 24** | |

| `dig_out` | |
|---|---|
| 12 | the selected result slice |

And from `docs/CHIPALOOZA_SLOT.md` §4.3, the shared analog bus should still
carry **`vctrl`** and **`vcoarse`** — quasi-dc, no pin cost, and the difference
between a die that is locked and a die that is asleep.

## 7. Open, for whoever writes the Verilog

1. **Does the 600 MHz divider close timing** in standard cells? Everything else
   in tier 1 is slow and easy; this is the only hard constraint.
2. **Tier 2 and 3 need `B+`/`B-` out of the macro** (§3). Tier 1 does not. That
   is the decision point at which the analog side has to be reopened.
3. **Tell Tim** if a digital block is added, since the schematic is green-lit.
4. **The ring still does not lock** on `ring-coarse-tune`
   (`docs/HANDBOOK.md` §11.1). Self-test logic verifies a receiver; it does not
   fix one. That is still the critical path, and it is analog.
