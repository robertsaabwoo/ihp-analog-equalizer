# Tests

```console
$ pip install -r test/requirements.txt
$ pytest test/
```

No PDK, no ngspice, no xschem, no network. The suite runs in well under a
second and is safe to run on every push, which is the point: the failures it
catches are all **silent** ones that the simulation flow would otherwise carry
forward as plausible wrong answers.

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
