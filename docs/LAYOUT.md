# Layout, from a standing start

How to get this design into Magic, with no prior layout experience. Written
after setting the flow up and running it end to end on a real cell from this
design, so every command below has been executed, not recalled.

The companion document is `docs/HANDBOOK.md`, which is the design itself.

---

## 0. Before anything: your Magic could not read this PDK

**This was broken and is now fixed**, but you need to know about it, because of
*how* it was broken.

The SG13CMOS5L tech file requires **magic 8.3.657** or newer. The machine had
**8.3.463**. When Magic hits a tech file it cannot parse it does not refuse to
start — it prints a wall of `Illegal keyword` lines, falls back to a built-in
dummy technology called `minimum`, and **opens normally**. You get a working
layout editor with *zero process layers in it*. Every rectangle you draw is
meaningless, DRC passes because there are no rules, and extraction produces
nothing.

Magic has been rebuilt at **8.3.683** and the tech now loads. Check it yourself
any time with:

```bash
magic --version          # want >= 8.3.657
echo "puts TECH:[tech name]; quit -noprompt" | \
  magic -dnull -noconsole -rcfile \
  $PDK_ROOT/ihp-sg13cmos5l/libs.tech/magic/ihp-sg13cmos5l.magicrc 2>&1 | grep TECH:
```

It must print `TECH:ihp-sg13cmos5l`. **If it prints `TECH:minimum`, stop** —
nothing you do afterwards means anything.

<details><summary>if you ever need to rebuild Magic</summary>

```bash
cd ~/magic && git checkout master && git pull
make distclean && ./configure --prefix=/usr/local
make -j3 && sudo make install
```

Two things that went wrong doing it this time: some files in the tree were
owned by `root` from a previous `sudo` build (`sudo chown -R ttuser:ttuser
~/magic` fixes it), and an incremental build produced a binary that started and
then died with `undefined symbol: mallocMagic` — hence the `make distclean`.
</details>

---

## 1. The mental model

Layout is drawing the physical shapes that become masks. In Magic you paint
rectangles of process layers and place instances of other cells.

**You will almost never draw a transistor by hand.** The PDK has parameterised
device generators: you ask for an nmos at W = 3 µm, L = 0.7 µm and it builds a
cell with correct diffusion, poly, contacts, well and implants. You place that.

Better still, this PDK's Magic support includes `magic::netlist_to_layout`,
which reads a SPICE netlist and **generates every device in it, correctly
sized, with the ports already labelled**. So you do not start from a blank
canvas. You start from a pile of correct devices in a row, and your job is:

1. **arrange** them sensibly
2. **wire** them with metal1/metal2
3. **DRC** until clean
4. **LVS** until it matches the schematic
5. move up one level and use that cell as a building block

The Magic cell hierarchy should mirror the schematic hierarchy exactly. Do that
and LVS works at every level, and you never debug the whole chip at once.

### The golden rule

**Verify every cell before you build anything on top of it.** A mistake in a
leaf cell instantiated ten times is ten faults at the next level up, where
netgen reports them as a mismatch in the parent and they are far harder to
read. `make check CELL=<name>` before you move on. Always.

---

## 2. Setup

```bash
export PDK_ROOT=/home/ttuser/pdk
cd mag
make cells          # every cell, leaves first, with device counts
```

`make cells` is the plan. It lists leaves before anything that depends on them.

---

## 3. The flow

Everything is in `mag/`:

| command | what it does |
|---|---|
| `make gen CELL=x` | generate a starting layout from the schematic netlist |
| `make edit CELL=x` | open it in the GUI |
| `make drc CELL=x` | design rule check, prints the count and the reasons |
| `make lvs CELL=x` | layout versus schematic |
| `make check CELL=x` | drc then lvs |
| `make cells` | list every cell, leaves first |

**`make gen` is the step worth understanding.** It pulls just that cell out of
`sim/netlists/blocks.inc` (via `tools/cell_netlist.py`) and hands it to Magic's
generator. On `robs_xor` — a real cell from this design, 4 nmos and 4 pmos — it
produces 8 correctly-sized device instances and all 7 ports, in about a second.

Immediately after generating, `make check` reports **DRC errors and an LVS
mismatch**, and that is the correct answer. The devices are dumped in a row,
overlapping, with nothing connected. LVS will say:

```
Device classes robs_xor and robs_xor are equivalent.     <- right devices
Cell pin lists are equivalent.                            <- right ports
Final result: Netlists do not match.                      <- not wired yet
```

That is your starting position, and it is a good one: the devices and the ports
are already provably right, so every remaining error is wiring.

### In the GUI

`make edit CELL=x` opens it. The command line is at the bottom; commands start
with `:`.

- **left mouse** sets one corner of the box, **right mouse** the other,
  **middle** paints the current layer
- `:grid 0.1um` — a sane grid
- `:paint metal1`, `:erase metal1`
- `:label vdd` then `:port make` — a wire becomes a pin. **A label is not a
  port until you say `port make`**, and LVS will not see it.
- `:writeall` — save every modified cell. Use this, not `:save`; it is easy to
  lose a subcell edit otherwise.
- `:drc why` — with the box over an error, says which rule and why

---

## 4. What to lay out, and in what order

`make cells` prints this, but here it is with commentary. Leaves first — none
of these contains another cell of yours, so each can be finished in isolation.

### Warm-up (learn the tool on something trivial)

| cell | devices | why first |
|---|---|---|
| `single_inverter` | 2 | one nmos, one pmos, four wires. Do this one twice. |
| `ibias_mirror` | 1 | a single diode-connected device. |
| `inv_cp` | 2 | same shape as `single_inverter`. |

### Tier 1 — the rest of the leaves

| cell | devices | note |
|---|---|---|
| `inverter_buffer` | 4 | |
| `inverter_chain` | 6 | three stages, each bigger than the last |
| `robs_xor` | 8 | all FETs, no passives — the easiest real cell |
| `tiny_pll_loop_filter_cap1/2` | 1 each | a MOS capacitor, `m=18` and `m=3` |
| `tiny_pll_loop_filter_res` | 1 | one long poly resistor |
| `tiny_pll_bias_gen_res` | 3 | three 24 kΩ resistors |
| `vctrl_precharge` | 9 | |
| `diff_amp_inv` | 10 | 4 resistors + 6 nmos |
| `d_latch` | 13 | the CML latch — **match the two halves carefully** |
| `CTLE` | 8 | small count, **large devices** — see §5 |

### Tier 2 and up — built from Tier 1

```
d_flip_flop              = 2x d_latch
alexander_phase_detector = 4x d_flip_flop + 2x robs_xor
tiny_pll_charge_pump     = 4 devices + inv_cp
tiny_pll_bias_gen        = 12 devices + tiny_pll_bias_gen_res
tiny_pll_loop_filter     = 2 caps + res
ring_oscillator          = 5x ring_inverter + diff_amp_inv
CDR                      = phase detector + pump + bias gen + filter
                           + ring + diff_amp_inv + buffers + precharge
ctle_cdr_rx              = CTLE + CDR + ibias_mirror + 2x inverter_chain
```

### Do NOT start on these yet

`ring_inverter`, `ring_oscillator`, `CDR`, `coarse_loop`.

The ring is **actively being changed** — `docs/HANDBOOK.md` §11 — and the
closed loop does not lock on the current version. Its input pair length, its
load resistance and whether it carries a trim leg at all are all still moving.
Laying it out now is work you will throw away.

Everything in the two tiers above is stable between `main` and the branch, and
that is most of the design. Start there.

---

## 5. Things specific to *this* design

**The CTLE's degeneration capacitor is the biggest object on the chip.**
1.6 pF of `cap_cmomf` is a **35.3 µm square** — 1243 µm², more than half the
drawn device area of the whole design. Plan the floorplan around it. It is a
metal fringe capacitor, so it occupies metal layers rather than silicon, and
what goes under it needs thinking about.

**There are a lot of long poly resistors.** 43 `rhigh` instances. At
1416 Ω/sq a 24 kΩ resistor is ~17 µm of 1 µm-wide poly. They fold, and folding
them well is most of the area you will save.

**The CML cells must be symmetric.** `d_latch`, `diff_amp_inv`, `ring_inverter`
and the CTLE are all differential. Mismatch between the two halves is offset,
and in the ring it is deterministic jitter on the recovered clock. Lay the two
halves out as mirror images, match the wiring lengths, and put dummies at the
ends of device rows.

**`ibias` is a current, not a voltage** (§6.1 of the handbook), and it feeds
mirrors all over the chip. Route it as a quiet, shielded net and keep it away
from the ring.

**Five of the 25 cells are not in the schematic hierarchy** the way you might
expect: `ctle_cdr_rx_lvs` is a one-instance wrapper that exists only so
netlisting produces a `.subckt`. You do not lay it out.

---

## 6. IHP layer names

Magic uses historical names, not IHP's. The essential mapping:

| IHP | Magic |
|---|---|
| Activ | `ndiff` |
| Activ + pSD + NWell | `pdiff` |
| NWell | `nwell` |
| GatPoly | `poly` |
| GatPoly + Cont | `pc` |
| Metal1…Metal4 | `metal1`…`metal4` |
| **TopMetal1** | **`metal5`** |

Implant and marker layers (nSD block, pSD, SalBlock, ThickGateOx) are **not
drawn** — Magic infers them from device types and generates them on GDS output.
See them with `:cif see <name>`.

This process has **four thin metals and one thick**, and no MIM capacitor, no
inductors, no deep n-well. `test/test_device_set.py` enforces the device side
of that; nothing enforces it in layout, so do not paint a layer because it
exists in the SG13G2 symbol library.

---

## 7. Traps, all of which happened while setting this up

**Magic's own options are in `$argv`.** A script that does
`set cell [lindex $argv 0]` gets `-nowrapper`, not your cell name. Use
`[lindex $argv end]`.

**The netlist filename must match the cell name.** `netlist_to_layout` decides
what to generate by comparing each `.subckt` against the file's root name.
Name the file `robs_xor.gen.spice` and it concludes `robs_xor` belongs to
someone else, prints *"already contains layout. Skipping generation."*, and
produces an empty cell.

**`netlist_to_layout` loads and saves the cell itself.** Wrapping it in your
own `load`/`save` replaces the generated cell with an empty one of the same
name, and it looks exactly like the generator silently doing nothing.

**It saves the parent cell only.** The device cells it generated
(`sg13_lv_nmos_S6LAQ4` and friends) live in memory and are never written, so
the next command to open the parent reports *"couldn't be read"* for every one
and extraction produces nothing. `writeall force` after generating.

**`ext2spice` without `-o` writes `<cell>.spice`** — the same name the
generator input uses. The extracted layout silently overwrites the schematic
netlist it was built from.

**A label is not a port.** `:label foo` puts text on a wire. LVS only sees it
after `:port make`.

---

## 8. A reasonable first session

Two to three hours, and finish with something verified.

1. Check `TECH:ihp-sg13cmos5l` prints. (§0)
2. `cd mag && make cells` — read the list.
3. `make gen CELL=single_inverter && make edit CELL=single_inverter`.
   Look at what the generator gave you. Pan, zoom, click a device, press `i`
   to see its parameters.
4. Wire it: source of the pmos to VDD, source of the nmos to VSS, drains
   together to the output, gates together to the input. Label and `port make`
   all four.
5. `make check CELL=single_inverter` until DRC is 0 and LVS says
   **`Circuits match uniquely`**.
6. Then do it again from scratch without looking at your first attempt. The
   second one will be a third of the area and you will have learned more from
   that than from anything written here.

Then `robs_xor` — 8 devices, no passives, and a cell you can lay out as two
mirrored halves.

---

## 9. What this does not cover yet

- **The Chipalooza slot** is now measured and written up in
  `docs/CHIPALOOZA_SLOT.md`: **537.15 × 273.00 µm**, identical for all
  eighteen, against 3094 µm² of drawn devices here — about 2 %. What is *not*
  known is which slot is ours. Build the top level inside
  `magic/slotN_wrapper.mag` from the harness repo once that is settled.
- **Fill and seal ring, and density checks.** The PDK ships
  `generate_fill.py`, `generate_seal.py` and `check_density.py` in its magic
  directory. They matter at tapeout and not before.
- **Antenna rules** and **parasitic extraction for re-simulation.** The sky130
  version had targets for both; they have not been ported.
- **The GDS write itself.** `:gds write` with the CIF output style the PDK
  defines. Untested here.
