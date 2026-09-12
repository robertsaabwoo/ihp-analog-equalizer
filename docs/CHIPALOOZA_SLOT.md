# The Chipalooza slot

What the harness actually gives a project, measured from
[`RTimothyEdwards/sg13cmos5l_ocd_chipalooza`](https://github.com/RTimothyEdwards/sg13cmos5l_ocd_chipalooza)
at commit dated 2026-09-08, cloned to `~/ssh_analog/sg13cmos5l_ocd_chipalooza`.

Read with `docs/LAYOUT.md` — this is the box the top-level layout has to fit in.

> **This project is slot 2, with 2 dedicated pins.** Assigned by email from
> Tim Edwards, listing all eighteen slots; schematic review is complete and
> this design is **green-lighted to start layout**. The assignment is not in
> the repository — `config.txt` there is still the generic template with
> `project_id: 20260908` — so §3's per-slot pad counts are the repo's, and the
> email supersedes them. **No deadline was given** in that email or anywhere
> searched (§5).

---

## 1. Size

**Every one of the eighteen slots is identical: 537.15 × 273.00 µm =
146 642 µm².**

Measured by loading each `magic/slotN_wrapper.mag` and reading its bounding
box, not taken from a document.

For scale, this design's drawn device area is **3094 µm²** — about **2 %** of
the slot. Area is not going to be the constraint. What will be is routing the
CTLE's 35.3 µm-square degeneration capacitor and 46 long poly resistors without
coupling anything into the ring.

## 2. What every slot connects to

Read out of the labels in `slotN_wrapper.mag`. Identical across all eighteen
except for the dedicated analog pads (§3).

| group | signals | count |
|---|---|---|
| 1.2 V supply | `vdd_1v2`, `vss_1v2` | 2 |
| 3.3 V supply | `vdd_3v3`, `vss_3v3` | 2 |
| bias | `vbias`, `ibias[0]`, `ibias[1]` | 3 |
| shared analog bus | `analog_bus[0..3]` | 4 |
| **digital in** | **`dig_in[0..23]`** | **24** |
| **digital out** | **`dig_out[0..11]`** | **12** |
| control | `clk`, `enable` | 2 |

The digital lines come from the harness's housekeeping SPI and sequencer, so
they are chip-internal control and readback, not package pins. Every slot gets
all 36 of them whether it uses them or not.

## 3. Dedicated analog pads, per slot

These are real package pins and they are the scarce resource. From the slot
wrappers:

| pads | slots |
|---|---|
| **3** | 5, 10, 14 |
| **2** | 1, 2, 3, 6, 7, 12, 13, 16, 17, 18 |
| **1** | 4, 8, 11, 15 |
| **0** | 9 |

**`config.txt` and the layout disagree about slot 9**: the config file lists
`s9_an[0..2]` and `slot9_wrapper.mag` has no analog pad labels at all. The
README says something different again — *"1 to 16 (there are 18 total slots;
the last two have no dedicated pads)"* — while slots 17 and 18 do have two
each. The repository is four days old and its own README opens with *"These
instructions are currently very incomplete"*, so treat all three as provisional
and confirm before relying on a pad count.

Slot 2 has `s2_an[0]` and `s2_an[1]`, each with an ESD tap
(`s2_an_0_esd`, `s2_an_1_esd`), plus the full shared set in §2.

## 4. The pin budget for slot 2, and the one problem in it

| need | goes to | status |
|---|---|---|
| `vinp`, `vinm` — 200 mVpp differential at 600 Mb/s | **both dedicated pads** | settled |
| `ibias` — 40 µA reference | `ibias[0]` or `ibias[1]` | settled, no pad |
| supply | `vdd_1v2` / `vss_1v2` | settled |
| **recovered clock, 600.6 MHz** | ? | **see below** |

The two dedicated pads are spoken for and not negotiable. The input is the most
bandwidth-critical and most sensitive signal in the design — 200 mV
differential at 600 Mb/s — and it gets the best path available. That leaves
nothing dedicated for the output.

### 4.1 A 600 MHz clock cannot leave this chip the obvious way

Neither remaining route carries it:

* **The shared analog bus** is explicitly ruled out by the assignment email —
  a switch of under 5 Ω, but the line is common to all eighteen slots and
  carries their eighteen switch capacitances. Tim's words: *"output drivers
  with sufficient drive and minimal bandwidth requirements should have no
  problem"*. 600 MHz is not a minimal bandwidth requirement.

* **The digital outputs** are better than feared but still not good enough.
  Tracing `verilog/rtl/router.v`, `dig_out` reaches a pin through a purely
  **combinational** 12-way mux — `assign io_out[i] = ...`, not registered and
  not clocked by the SPI, so there is no architectural ceiling. But the path is
  a synthesised route from the slot, across the chip to the central router,
  through that mux, into an `IOPadOut16mA`-class pad, a bondwire and a package
  pin. A 600 MHz square wave through all of that is at best badly degraded, and
  every part of it is shared infrastructure outside this project's control.

### 4.2 What to do instead: divide the clock on chip

This is standard for a CDR test chip and it costs very little.

A **÷8** puts the output at **75.1 MHz**, which a digital pad handles without
argument, and it proves lock exactly as well: if the divided output sits at
precisely one eighth of the baud rate, the loop is locked. ÷16 → 37.5 MHz is
even safer.

The first stage has to run at 600 MHz, and this design already contains a
proven building block for that — `d_latch`, the CML latch in the phase
detector, which is already doing 600 MHz work. A CML ÷2 built from two of them,
followed by two ordinary CMOS ÷2 stages, gives ÷8 for well under twenty
devices.

Two things to preserve while doing it:

* `clkout_n` exists partly to **load the ring symmetrically** — the sky130
  layout handoff says in as many words *"do not delete"*. A divider must be
  driven from a buffered copy, not by unbalancing the existing output pair.
* Keeping the **undivided** clock on a second `dig_out` as well costs one pin
  and nothing else, and if the path turns out better than expected it is free
  information. It should not be the primary measurement.

**Superseded — see `docs/BIST.md`.** The decision taken is not to send the
clock off chip at all, but to verify the receiver with logic inside the slot: a
frequency counter gated by the harness's external `clk` pin, and a capture of
the recovered bits read out statically.  That removes the 600 MHz output path
rather than working around it, and produces the recovered *bits*, which a
divided clock never would.  A divider is still needed — it is the front of the
frequency counter — but nothing fast leaves the slot.

### 4.3 The shared analog pins are useful for something else

The shared bus is poor for 600 MHz and excellent for exactly what this design
most needs to observe: **`vctrl`**, and **`vcoarse`** if the dual loop survives.
Both are quasi-dc nodes, both are the difference between a chip that is locked
and a chip that is asleep (`docs/DESIGN.md` §5.1: a settled control voltage is
not evidence of lock), and both are how a part that fails would be diagnosed.
Bringing them out through the switch costs no dedicated pin.

### 4.4 Twenty-four digital inputs are available, and worth spending

The email confirms 24 digital inputs, drivable at run time from constants, the
sequencer, or the pattern generator. This design currently uses none. Three
things are worth taking:

* a bit to **disable the coarse loop**, so the fine loop can be characterised
  alone on silicon exactly as `e2e_lock.spice` does in simulation;
* a few bits to **force `vcoarse`** to known settings, which turns the ring's
  tuning curve into something measurable on a real die;
* and, if the dual loop cannot be made to lock (`docs/HANDBOOK.md` §11), those
  same bits are the **switched-leg band select** that §1 wrongly believed was
  unaffordable.

## 5. This corrects a design decision

`docs/DESIGN.md` §9 and `docs/RING_DUAL_LOOP.md` §1 both reject a
digitally-selected coarse frequency trim on the grounds that *the Chipalooza
slot has 1–3 analog pads and the pins are not available*. Slot 2 has exactly
two, so the premise is now confirmed — and the conclusion is still wrong.

**The pad count is right and the conclusion drawn from it is wrong.** A band
select would not have used an analog pad. Every slot has **24 dedicated digital
inputs**, driven from the housekeeping registers, which is exactly what a
two-bit band select wants, and they cost nothing because they are there whether
used or not.

That does not make the analog coarse loop the wrong choice — a loop that
centres itself needs no configuration, no per-chip calibration and no knowledge
of which corner a die landed on, and that is a better result than a trim
somebody has to set. But it was chosen against a constraint that does not
exist, and the documents say so now.

It also means a **fallback exists**: if the dual loop cannot be made to lock
(`docs/HANDBOOK.md` §11), the 24 digital inputs make the switched-resistor-leg
version available after all, and it is the lower-risk circuit because the stage
topology does not change.

## 6. Deadline: not found

Searched: the harness repository, its GitHub page for issues and discussions,
opencircuitdesign.com, and the web generally.

What is established is that the 2024 Chipalooza ran on sky130 under Efabless,
and that **Efabless ceased operations in March 2025**, so whoever is running an
SG13CMOS5L round is doing it under different sponsorship. The harness repo is
Tim Edwards' and was last committed 2026-09-08, four days ago, which says the
round is live and early rather than closing.

The slot assignment arrived by email and contained no date. If a schedule
exists it is presumably in the same channel.

## 7. Reproducing this

```bash
git clone --depth 1 https://github.com/RTimothyEdwards/sg13cmos5l_ocd_chipalooza
cd sg13cmos5l_ocd_chipalooza/magic
# slot size
echo 'load slot1_wrapper -silent; select top cell; box values; quit -noprompt' | \
  magic -dnull -noconsole -rcfile \
  $PDK_ROOT/ihp-sg13cmos5l/libs.tech/magic/ihp-sg13cmos5l.magicrc
# slot interface (internal units: divide by 200 for microns)
grep -E '^(r|f)label' slot1_wrapper.mag | awk '{print $NF}' | sort -u
```
