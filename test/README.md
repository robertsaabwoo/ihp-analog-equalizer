# Tests

```console
$ pip install -r test/requirements.txt
$ pytest test/
```

No PDK, no ngspice, no network. The suite runs in well under a second and is
safe to run on every push, which is the point: the failures it catches are all
**silent** ones that the simulation flow would otherwise carry forward as
plausible wrong answers.

One test does use xschem if it happens to be installed
(`test_coarse_loop.test_netlist_matches_include`) and skips otherwise, so the
promise above still holds on a bare checkout.

## What each file is for

**`test_device_set.py` — the design must be manufacturable on SG13CMOS5L.**

This is the test that earns its place. SG13CMOS5L is the CMOS-only member of
the SG13 family: no MIM capacitor, no HBTs, no inductors, no deep n-well, no
Schottky diodes. But its PDK is an *overlay* on SG13G2, and the SG13G2 symbol
library sits on `XSCHEM_LIBRARY_PATH`, so a `cap_cmim` dropped into a schematic
resolves, netlists, and simulates perfectly against the shared models — and is
unbuildable. Nothing else in the flow catches it. ngspice does not know what
mask set you are targeting.

It also checks that no sky130 reference survived the port, and that the PDK
symbols are referenced through `sg13cmos5l_pr` rather than `sg13g2_pr` — the
same symbol files either way, but that path is the line in the schematic that
says which process this design is for.

**`test_hierarchy.py` — every symbol resolves, and the design is still the
design.**

xschem resolves a missing symbol silently: it emits a truncated netlist and
exits zero, and that netlist is what LVS and every simulation then trust. This
checks that every locally referenced symbol exists, that every hierarchical
symbol has a schematic behind it, and that the blocks that make this a receiver
— the CTLE, the phase detector, the charge pump, the loop filter, the ring, the
startup precharge — are still instantiated.

It also pins two things that are part of the frequency plan rather than
implementation detail: the ring has **five** stages (the period is ten stage
delays), and **both** recovered-clock phases are buffered (driving one leg of a
differential oscillator skews its duty cycle).

**`test_device_geometry.py` — every device inside the model's validated range.**

The PSP model header states its range: `L = (0.13 - 10) um`, `W = (0.15 - 10)
um`, and the W there is **per finger** — the device subcircuit computes its
diffusion areas from `w/ng`. ngspice will evaluate a 30 µm single-finger
transistor perfectly happily and hand back extrapolated numbers, and nothing
else in the flow objects.

This caught three real devices: the CTLE's input pair at 30 µm and its tail at
40 µm, all drawn at `ng=1` after being re-sized for 1.2 V. They are now
fingered to 5 µm per finger, which is also simply what a 30 µm transistor looks
like in layout.

**`test_port_tool.py` — the port arithmetic.**

Passives are converted by *value*: the tool takes the sky130 resistance or
capacitance and solves the IHP geometry from the PDK's own expressions. If that
is wrong, every resistor in the design is wrong by the same factor — which
looks like a working circuit with the wrong numbers, the hardest kind of bug to
notice.

One of these tests exists because the bug it checks for happened: the capacitor
solver had a stray factor of 10⁶ and produced a 22 picometre capacitor. It
simulated without complaint and simply showed no peaking at all.

It also checks the instance-transform arithmetic against xschem's own rotation
convention, because that transform is what places the bulk-pin label when a
three-terminal sky130 FET becomes a four-terminal IHP one. Get it wrong and the
label lands where the pin is not, the bulk floats, and the netlist is still
structurally valid.

## What is not tested here

Anything that needs a simulator. The CTLE gain, the VCO tuning range and the
loop's behaviour are measured by the decks in `sim/decks/` and recorded in
`sim/results/`; they take minutes to hours and need the PDK. CI runs the port
against the sky130 source and checks the committed schematics match, which is
the closest thing to a cheap regression test this design has.

**`test_coarse_loop.py` — the coarse loop's schematic must not drift from the
include it was designed in.**

`sim/decks/coarse_loop.inc` is where the coarse frequency loop was designed and
debugged, because every question it raised is answered by a transient that
takes seconds and redrawing a thirty-device schematic between iterations would
have been the slow part of each one.  `xschem/coarse_loop.sch` is *generated*
from it by `tools/gen_coarse_loop.py`.

That arrangement fails in two directions and this file tests both: the include
changes and nobody re-runs the generator, so the schematic -- which is what
gets fabricated -- is a circuit nobody simulated; or somebody edits the
schematic by hand and the next generator run silently reverts it.  Same hazard
as the ported cells in CLAUDE.md section 4, same answer.

It also pins two things that measurement decided and that would be easy to
undo: that no MOS capacitor appears on the `vcoarse` node (773 pA of gate
leakage on 384 um2, which is 184 mV/ms on that node -- see
`docs/RING_DUAL_LOOP.md` section 5), and that the `Ksweep` simulation-only
current scaling is committed as 1, since any other value would make every
silicon number in the docs wrong.
