# Simulation traps: IHP SG13CMOS5L, xschem and ngspice

Every item here cost real time on this project, and almost every one of them
**fails silently** — you get a plausible number, or a warning buried in a
thousand lines of model noise, rather than an error.

The list is in two parts. The first is specific to the IHP open PDK and is new
to this repository. The second carries over from the sky130 original
([ttsky-analog-equalizer](https://github.com/robertsaabwoo/ttsky-analog-equalizer)),
because those traps are properties of ngspice and of CDR measurement, not of
any one process, and they will bite here exactly as hard.

---

## Part 1 — IHP-specific

### 1.1 `ihp-sg13cmos5l` is an overlay on `ihp-sg13g2`, not a standalone PDK

About 500 files in the CMOS5L tree are relative symlinks into a *sibling*
`ihp-sg13g2` checkout — every ngspice model library, most xschem symbols, the
Verilog-A sources. Clone CMOS5L on its own and those links dangle.

**Symptom:** ngspice reports `could not find a valid modelname`, which reads
like a broken deck. `find $PDK_ROOT/ihp-sg13cmos5l -xtype l | wc -l` tells you
the truth; a healthy install has fewer than ten (the leftovers are Xyce plugins
and an SRAM library that is genuinely absent).

`tools/setup_pdk.sh` installs both, side by side, which is the arrangement the
symlinks assume.

### 1.2 The MOS models are Verilog-A and must be compiled before anything works

SG13's transistors are PSP 103.6, distributed as Verilog-A and loaded through
OSDI at run time. They are **not** built into ngspice.

**Symptom:** a *warning* — `Unknown model type psp103va - ignored` — repeated
once per device, and then a hard error on the first transistor. The warning is
the real message and it is easy to scroll past.

```
.control
pre_osdi $PDK_ROOT/$PDK/libs.tech/ngspice/osdi/psp103.osdi
.endc
```

`pre_osdi` rather than `osdi` because the load has to happen before the netlist
is parsed. Every deck in `sim/decks/` carries these lines itself rather than
relying on a `.spiceinit`, so a deck can be handed to someone else and still
run.

Four modules are needed, and each one is missed differently:

| module | needed by | symptom if missing |
|---|---|---|
| `psp103.osdi` | every transistor | `Unknown model type psp103va` |
| `psp103_nqs.osdi` | nothing this design instantiates | a screenful of `pspnqs103va` warnings that look alarming and are not |
| `r3_cmc.osdi` | `rhigh`, `rsil`, `rppd` | `could not find a valid modelname` on a *resistor* |
| `cap_cmomf.osdi` | the CTLE degeneration cap | `unknown subckt` — with the parameters parsed as node names |

### 1.3 OSDI has versions, and ngspice 42 is not on the current one

ngspice 42 implements OSDI **0.3**. OpenVAF-Reloaded's current binaries
(`openvaf-r`, v24.x) emit OSDI **0.4**, and link against `libLLVM.so.18`, which
Ubuntu 22.04 does not package. The last statically linked compiler that emits
0.3 is OpenVAF 23.5.0. `tools/setup_pdk.sh` fetches that one, and prefers
`openvaf-r` if you have already put it on `PATH` — which is right if you are on
ngspice 44 or newer.

### 1.4 `sub!` is a global net that xschem does not declare

`rhigh`, `rsil`, `rppd` and the MOM capacitors carry their body terminal on the
node `sub!`. xschem emits it as an ordinary node name and emits no `.global`,
so inside every subcircuit it is a *local* floating node.

**Symptom:** `Warning: singular matrix: check node sub!`, then gmin stepping,
then an operating point that is wrong rather than absent.

Every testbench needs:

```spice
.global sub!
Vsub sub! 0 0
```

### 1.5 `.include` on a corner library pulls in every corner at once

`cornerMOSlv.lib` is a *library* of `.LIB` sections. Including it rather than
selecting a section gives you `Warning: redefinition of .subckt sg13_lv_nmos,
ignored` a few dozen times and then
`unimplemented dot command '.lib'`. Always name the section:

```spice
.lib .../cornerMOSlv.lib mos_tt
```

The section names are not uniform across the three files, which is its own
small trap: MOS uses `mos_tt` / `mos_ss` / `mos_ff`, resistors use
`res_typ` / `res_wcs` / `res_bcs`, capacitors `cap_typ` / `cap_wcs` / `cap_bcs`,
and the MOS-capacitor file uses `moscap_tt` — not `moscap_typ`.

### 1.6 SG13CMOS5L has no MIM capacitor

The `cap_cmim` symbol exists in the SG13G2 symbol library and **not** in
`sg13cmos5l_pr`. A schematic that uses it will netlist against SG13G2 models
and simulate perfectly, and then be unmanufacturable on the Chipalooza process.
The available capacitors are `cap_cmomi` (1.00 fF/µm²), `cap_cmomf`
(1.29 fF/µm²) and the MOS capacitors `moscap_n` (11.8 fF/µm² at 0.6 V) and
`moscap_p` — all measured in `char/caps.spice`. Nor are there HBTs, inductors,
deep n-well or Schottky diodes.

### 1.6b A sizing key that matches nothing is silently ignored

Not an ngspice trap, a project one, and it wasted a sweep. `tools/port_from_sky130.py`
keys its `SIZING` table on `(cell, instance)`. xschem lets one symbol expand to
several devices as a *vector*, and its instance name is then literally
`R[2..0]` — not `R0`, `R1`, `R2`. Keying on the latter matches nothing, the
port applies no override, and the sweep that follows reports **the same result
for every value it thinks it is sweeping**.

Four resistor values, four identical currents, and no error anywhere. Check the
port log — it echoes the instance name it actually matched — before trusting a
sweep that comes back flat.

### 1.7 `PDK` inherited from a sky130 shell breaks netlisting without saying so

If your shell exports `PDK=sky130A` — which it does if you have been doing
sky130 work — then `PDK_ROOT/$PDK/libs.tech/xschem` puts the *wrong* symbol
library on `XSCHEM_LIBRARY_PATH`. xschem then resolves no device symbol at all,
says nothing, and writes a structurally valid netlist with no transistors in it.

`env.sh` sets `PDK` unconditionally rather than defaulting it, and
`tools/netlist.sh` fails the build if the netlist contains fewer than 60
MOSFETs.

---

## Part 2 — ngspice and measurement

### 2.1 `shell echo` and ngspice's own output are buffered separately

A `foreach` loop that labels each point with `shell echo "#PT $x"` and prints
the data with `print` produces **all the labels first and all the data after**.
The first version of `ctle_bias.spice` emitted 21 headers followed by 21
unlabelled results, which is worse than no labels at all because it looks
correct at a glance.

Print the loop variable as a vector instead:

```
let p_vcm = $vc
print p_vcm voutcm gnyq
```

### 2.2 Vectors defined against the operating point vanish after `ac` or `tran`

Each analysis opens a new plot. `let itail = -i(vdd)` after `op`, then `ac`,
then `print itail` gives `vector itail is not available or has zero length` —
as a warning, with the rest of the print silently dropped. Print the operating
point before starting the next analysis.

### 2.3 One bad node name kills the whole `print`, not just that vector

`let vst = v(x1.st)` where the node is actually called `net2` does not report
an unknown node. It makes the vector unavailable, and then `print a b vst c`
emits *nothing at all*. A sweep that should have produced 27 rows produced
zero, and the log looked like the simulation had not run.

Unnamed nodes are auto-numbered by xschem in drawing order, so `net2` is not a
stable name either — check it against `sim/netlists/blocks.inc` after any
schematic edit, or label the node in the schematic.

### 2.4 An include file that instantiates something instantiates it everywhere

`sim/netlists/blocks.inc` must define subcircuits and instantiate nothing. The
xschem LVS wrapper emits one top-level instance line; `tools/netlist.sh` strips
it. When the bias pin was renamed `vbias` → `ibias`, the strip — which matched
the full line text — silently stopped matching, and every testbench from then
on elaborated a second complete copy of the receiver named `x1`.

ngspice's report of that was `device already exists, bail out`, naming a device
four levels down a hierarchy the testbench never mentioned. The script now
matches by shape and asserts that nothing is instantiated at depth zero.

### 2.5 `altervalue` is not an ngspice command

It is `alter <source> dc = <value>`. `altervalue` produces
`no such command available in ngspice` per iteration and the loop otherwise
runs to completion, so a sweep of 21 points quietly measures the same point 21
times.

### 2.6 A ring oscillator started from a symmetric state never starts

All nodes equal is a valid DC solution and the simulator has no noise to break
it. Real silicon starts on thermal noise; the simulator has none unless you ask.
Kick one node:

```spice
.ic v(vop)=1.0 v(vom)=0.4
```

**Inside a closed loop this does not look like a dead oscillator, it looks like
a locked one.** The first end-to-end run of `e2e_lock.spice` finished cleanly
and reported:

```
vctrl_lock  = 0.6608 V        control voltage settled
vctrl_ripp  = 0.0010 V        one millivolt of ripple -- beautifully quiet
ctle_swing  = 0.2773 V        CTLE equalising correctly, 63 mV in
rclk_swing  = 4.9e-08 V       ... the recovered clock is 49 nanovolts
```

Three of those four numbers are what a working receiver looks like. The control
voltage is quiet *because* there is no clock for the phase detector to compare
against, so the charge pump never fires and nothing perturbs the loop filter.

The lesson generalises past ring oscillators: **a settled control voltage is
not evidence of lock.** Measure the clock's amplitude and its frequency as
separate criteria, and treat any one of the three agreeing on its own as
meaningless.

### 2.7 `.op` treats a capacitor as an open circuit

Any power-on-reset or startup circuit is dead on arrival in a deck that begins
from an operating point. The `vctrl` precharge one-shot never fires without
`.ic v(...nrc)=0`. **Symptom:** everything frozen and a "recovered clock" of a
few millivolts — it looks like a broken circuit, not a broken testbench.

### 2.8 `let clkp = v(clk+)` silently produces nothing

ngspice parses the `+` in a node name as an operator, and the vector never
appears — no error, no warning. Copy the node through a unity-gain source
first: `Eclkp clkp 0 clk+ 0 1`. This design has `vo+`, `rclk+`, `B+` and
several others, so it comes up constantly.

### 2.8b An element cannot reference a subcircuit-internal node

`save`, `print` and `meas` accept hierarchical paths. **Element node fields do
not.** This looks like a reasonable way to get a `+`-named internal node onto a
probeable name:

```spice
Erclkp rclkp 0 x1.x2.rclk+ 0 1
```

and what ngspice actually does is create a *new top-level node* literally named
`x1.x2.rclk+`, connected to nothing but that source. The operating point then
fails with

```
Warning: singular matrix:  check node x1.x2.rclk+
Error: Transient op failed, timestep too small
```

naming a node the circuit does not contain, in a deck where every other line is
fine. There is no way to bridge a hierarchy boundary with an element; probe
internal nodes whose names have no `+` or `-` in them, or label the node in the
schematic so it becomes reachable.

### 2.9 A `.measure` on an edge index that does not exist fails silently

A 3 µs run at 600 Mb/s looks like it contains 1802 UI, so `RISE=1800` seems
safe — but the recovered clock does not start until the startup precharge
releases, so there are fewer edges than that, and the measurement and every
`let` derived from it quietly did not happen. Derive the index from
`(t_end − t_release)/UI`, and leave margin.

### 2.10 A PWL source holds its last value forever

Run a 6 µs transient against a 3 µs pattern file and the back half of the
simulation is flat DC: the CDR goes blind, the loop wanders, and the run
produces a "jitter" number that is really a measurement of the data source
running out.

### 2.10b A short measurement window reports the dither, not the frequency

The first locked run measured 602.0 MHz on 600.6 Mb/s data — a 0.23 % error
that looked like a real frequency offset and would have sent the next hour
into the loop dynamics. It was the measurement. 60 cycles cannot average out
177 mV of control-voltage dither on a 310 MHz/V oscillator; the window reports
a *sample* of the instantaneous frequency, not its mean.

The same deck over 350 cycles, entirely inside the settled region, gave
600.42 MHz — a −0.03 % error. The loop had been locked the whole time.

Rule: make the frequency baseline long compared with the loop's own dither
period, and quote that one.

### 2.11 Measuring a loop before it has settled measures the settling

The sky130 project reported 33.8 % UI RMS of phase error from a window in which
`vctrl` was still drifting. Prove settling *inside the deck*, with two or three
separated averaging windows that must agree, before quoting any jitter number.

Related: a best-fit constant-period clock is the wrong reference for a CDR —
the recovered clock is supposed to track the data, so the reference is the
ideal bit grid. A bang-bang loop has unbounded low-frequency phase wander by
construction, so measure over a bounded window or the answer gets arbitrarily
worse the longer you look.

### 2.12 xschem's `-r` is `--no_readline`, not an rcfile flag

Passing it produces a truncated netlist full of `Symbol not found`, with a zero
exit status. The rcfile flag is `--rcfile`.

### 2.13 Units in a `.param` expression

`sqrt(Ccap / 1.287e-3)` where the density is written in F/m² returns metres.
Multiplying that by `1e-6` "to convert to microns" gives a 22 pm capacitor,
which ngspice simulates without complaint — it just shows no peaking at all,
and the first hour goes into looking for the mistake in the topology.
