# The Chipalooza slot

What the harness actually gives a project, measured from
[`RTimothyEdwards/sg13cmos5l_ocd_chipalooza`](https://github.com/RTimothyEdwards/sg13cmos5l_ocd_chipalooza)
at commit dated 2026-09-08, cloned to `~/ssh_analog/sg13cmos5l_ocd_chipalooza`.

Read with `docs/LAYOUT.md` — this is the box the top-level layout has to fit in.

> **Not found: which slot is ours.** The harness repository contains only the
> generic template — `config.txt` has all eighteen slots set to plain analog
> pads and `project_id: 20260908`, which is a placeholder date, not an
> assignment. There are no participant names, no issues and no discussions in
> it, nothing in this repository or the sky130 one, and nothing on
> opencircuitdesign.com. **Also not found: a deadline.** See §5.

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

### What this design needs

| need | from |
|---|---|
| `vinp`, `vinm` differential input | **2 dedicated analog pads** |
| `ibias` 40 µA reference | `ibias[0]` or `ibias[1]` — no pad needed |
| `clkout_p`, `clkout_n` recovered clock | 2 of the 12 `dig_out` — no pad needed |
| supply | `vdd_1v2` / `vss_1v2` |

So **two analog pads**, which rules out slots 4, 8, 9, 11 and 15 and leaves
thirteen candidates. Nothing else this design needs is scarce.

Taking the recovered clock out on `dig_out` rather than a pad is worth
checking rather than assuming: 600 MHz through the housekeeping path may not be
observable, in which case the clock wants a real pad and the requirement
becomes three — which leaves slots 5, 10 and 14. **Not investigated.**

## 4. This corrects a design decision

`docs/DESIGN.md` §9 and `docs/RING_DUAL_LOOP.md` §1 both reject a
digitally-selected coarse frequency trim on the grounds that *the Chipalooza
slot has 1–3 analog pads and the pins are not available*.

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

## 5. Deadline: not found

Searched: the harness repository, its GitHub page for issues and discussions,
opencircuitdesign.com, and the web generally.

What is established is that the 2024 Chipalooza ran on sky130 under Efabless,
and that **Efabless ceased operations in March 2025**, so whoever is running an
SG13CMOS5L round is doing it under different sponsorship. The harness repo is
Tim Edwards' and was last committed 2026-09-08, four days ago, which says the
round is live and early rather than closing.

**If you have a slot number or a date, tell me and I will write them into this
document and the floorplan.** They most plausibly came from an email, a Slack
or Matrix channel, or a signup form — none of which I can reach.

## 6. Reproducing this

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
