# Why the Alexander detector's UP and DOWN windows are unequal

Analysis of `sim/netlists/blocks.inc` against the measured logs, plus the isolated deck
that settles it (`sim/decks/pd_pulsewidth.spice`).

Starting point (`docs/EXPERIMENTS.md` 2.10): the detector's phase-average is **+77.1 nA**
at ff/-40 C/1.32 V (`sim/results/pd_phase_ffm40.log`, ten phases: -335, -332, -257, +197,
+420, +415, +408, +412, +170, -328 nA) against **+10.4 nA** at tt/125 C
(`sim/results/pd_phase_tt125.log`: -345, -165, -51, +310, +311, +309, +175, +54, -150,
-344 nA). The up lobe spans ~0.5 UI and reaches +420 nA; the down lobe ~0.4 UI and -335 nA.

---

## 1. How the two pulses are actually produced

### 1.1 `d_latch` (blocks.inc:460) — transparent on `clk+`

`XM6 net3 clk+ net4` steers the tail into the **input pair** (`XM1`/`XM4`, gates `vin+`/
`vin-`, W 5 um / L 0.13 um, sources on `net3`); `XM7 net5 clk- net4` steers it into the
**cross-coupled pair** (`XM3`/`XM5`, sources on `net5`). So the cell tracks while `clk+`
is high and regenerates while `clk-` is high.

The internal nodes `net1`/`net2` are loaded by `XR3`/`XR1`, `rhigh` W 1 um / L 4.122 um =
**~5.6 kohm** (1360 ohm/sq, `cornerRES.lib` line 20, x 4.12 squares). Each output then
passes through a **CMOS inverter**: `XM8`/`XM9` (pMOS 3 um, nMOS 1 um) on `vout+`,
`XM10`/`XM11` on `vout-`. The inverter re-inverts, so `vout+` follows `vin+`.

### 1.2 `d_flip_flop` (blocks.inc:421) — positive-edge triggered on `clk+`

```
x1 net1 net2 vin+ vin- Vdd Vss clk- clk+ vbias d_latch   <- master, clk+ pin = DFF clk-
x2 Q    Qn   net1 net2 Vdd Vss clk+ clk- vbias d_latch   <- slave,  clk+ pin = DFF clk+
```

Master transparent while `clk+` is LOW, slave while `clk+` is HIGH: `Q` samples `vin` on
the **rising edge of `clk+`**.

### 1.3 `alexander_phase_detector` (blocks.inc:144) — who feeds what

```
x5 VDD VSS net1 net2 vin+ clk+ clk- vin- vbias d_flip_flop   D = raw data,  clk = clk+
x1 VDD VSS net3 net4 vin+ clk- clk+ vin- vbias d_flip_flop   D = raw data,  clk = clk-
x2 VDD VSS net5 net6 net1 clk+ clk- net2 vbias d_flip_flop   D = net1,      clk = clk+
x3 VDD VSS B+   B-   net3 clk+ clk- net4 vbias d_flip_flop   D = net3,      clk = clk+
x6 net1 VDD B- VSS down net2 B+ robs_xor
x7 net5 VDD B- VSS up   net6 B+ robs_xor
```

`robs_xor` ports are `A VDD B- VSS xor_out A- B`, so:

| | XOR port A | XOR port B | meaning |
|---|---|---|---|
| `down` = x6 | `net1`/`net2` (x5) | `B+`/`B-` (x3) | `D_k  XOR E` |
| `up`   = x7 | `net5`/`net6` (x2) | `B+`/`B-` (x3) | `D_k-1 XOR E` |

Writing the rising clock edges as t_k: at t_k+, `net1 = D_k` (data sampled now),
`net5 = D_k-1` (the same sample delayed one UI by x2), `B+ = E`, the edge sample taken by
x1 on the previous **rising `clk-`** and re-timed by x3. Textbook Alexander, and the port
assignment is identical in both XORs (data sample on A, edge sample on B).

Three structural facts fall out of this and drive everything below:

1. **`x5`, `x2` and `x3` fire on rising `clk+`; only `x1` fires on rising `clk-`.** `clk-`
   is not an independent phase: in `CDR` (blocks.inc:56) `x12 Vdd Vss rclk+ rclk-
   single_inverter` makes it by inverting `rclk+`. So x1's sampling instant sits at
   (clk+ high time) + (one inverter delay) after x5's — **not at UI/2 unless `rclk+` is
   exactly 50 % duty**.
2. **`x5` is the only flip-flop whose D is the raw analog data.** x2's and x3's D inputs
   (`net1`/`net2`, `net3`/`net4`) are full-swing CMOS from a `d_latch` output inverter.
3. **`net1` bounds only the `down` pulse; `net5` bounds only the `up` pulse; `B+` bounds
   both.** Work an isolated 0->1 data transition through:

   * clock late (**up** decision): at t_k `net1` and `B+` both toggle -> `up` **rises on
     `B+`**; at t_k+1 only `net5` toggles -> `up` **falls on `net5`**.
     `W_up = UI + [tcq(x2) + t_A,fall] - [tcq(x3) + t_B,rise]`
   * clock early (**down** decision): at t_k only `net1` toggles -> `down` **rises on
     `net1`**; at t_k+1 `net5` and `B+` toggle -> `down` **falls on `B+`**.
     `W_dn = UI + [tcq(x3) + t_B,fall] - [tcq(x5) + t_A,rise]`

   With `tcq(x2) = tcq(x3)` (identical cells, identical CMOS-level D, same clock):

   **`W_up - W_dn = [tcq(x5) - tcq(x3)] + (t_A,rise + t_A,fall) - (t_B,rise + t_B,fall)`**

   The same derivation for a 1->0 transition swaps every polarity, so over a balanced
   pattern the d_latch's own rise/fall stretch is common to both and cancels.

### 1.4 `tiny_pll_charge_pump` (blocks.inc:108) — the up path has one more gate

```
XMNSW out down  src_n VNB nmos w=0.5u l=0.13u      <- `down` drives the switch directly
XMPSW out upb   src_p VPB pmos w=1u   l=0.13u
XINV  up  upb   VPWR VGND inv_cp                   <- `up` goes through an inverter
```
`inv_cp` (blocks.inc:335) is pMOS 2 um / nMOS 1 um, L 0.13 um. Gate loads on the detector's
two outputs therefore differ ~6:1: `up` sees (2+1) x 0.13 um^2 ~ **6 fF**, `down` sees
0.5 x 0.13 um^2 ~ **1 fF**.

---

## 2. Ranked causes

### Rank 1 — the recovered clock is not 50 % duty, so the decision REGIONS are unequal

This is the big one and it is already measured.

`sim/results/clkpath_sb_pvt_ff.log` and `..._tt.log` report the duty of `rclkp` (the same
node as `CDR`'s `rclk+`: ring -> `diff_amp_inv` -> `sb_inverter` -> `inverter_buffer`,
identical instancing in both):

| corner | duty of `rclk+` |
|---|---|
| ff / -40 C / 1.32 V | **0.5952**, 0.5952, 0.5771 (three ring settings) |
| ff / -40 C / 1.08 V | 0.5695, 0.5668, 0.5445 |
| tt / 125 C / 1.20 V | **0.5486**, 0.5536, 0.5576 |
| tt / 125 C / 1.32 V | 0.5529, 0.5526, 0.5546 |

By 1.3 fact 1, x1 samples `dcy * UI` after x5 instead of `0.5 * UI`. A slipping loop sweeps
the data phase uniformly, so the **up decision region is `dcy` of a UI wide and the down
region `1 - dcy`**. Put the measured duty through the measured lobe plateaus:

| corner | prediction | measured |
|---|---|---|
| ff/-40 C/1.32 V | 0.595 x 420 - 0.405 x 335 = **+114 nA** | +77.1 nA |
| tt/125 C/1.20 V | 0.554 x 311 - 0.446 x 345 = **+18 nA** | +10.4 nA |

Same sign, same order, and **the same 0.66x dilution at both corners** — which is exactly
what a flat-plateau model should over-predict, because ~0.2 UI of each cycle is spent in
the S-curve's two transition regions where |i| is well below the plateau. One number
explains both corners *and* their 7:1 ratio. Nothing else found here does that.

Measured lobe widths agree too: EXPERIMENTS 2.10 puts the zero crossings near 0.25 and
0.85 UI, i.e. an up region of 0.60 UI against a down region of 0.40 UI, against the
0.595/0.405 the duty predicts.

Where the duty error comes from is **consistent with, not proven by, these logs.** The
same file shows `diff_amp_inv`'s single-ended output swinging [0.252, 1.214] V at
ff/-40 C/1.32 V (a 0.96 V swing) against [0.638, 1.114] V at tt/125 C/1.20 V (0.48 V), and
the duty error tracks that swing across all 27 rows — which is what a resistor-loaded stage
should do, its rising edge being a `rhigh` RC (`XR1`/`XR2`, 1 x 3.838 um) and its falling
edge current-driven, so the two crossings of the next stage's trip are not half a period
apart. The accumulated trip-point offset of the three p-weak inverters in the chain
(`sb_inverter` 2/1, `inverter_buffer` 16/8 after 6/7, `single_inverter` 16/8, all
W_p/W_n <= 2 against a pMOS ~2.5x less mobile) would push the duty the *other* way, so it
is not the dominant term. Localising this properly is a separate, cheap measurement.

**Note this is a decision-REGION effect, not a pulse-WIDTH effect**: each individual up or
down pulse is still about one UI wide. It changes how often each fires as the loop slips,
which is precisely what the phase-average integrates.

### Rank 2 — `x12 single_inverter` adds its delay to `clk-` only

`rclk- = single_inverter(rclk+)` (blocks.inc:56, cell at blocks.inc:223, pMOS 16 um ng=8 /
nMOS 8 um ng=4). Its output drives 8 clock gates of W 5 um / L 0.13 um inside the detector
(two per `d_flip_flop` x four) ~ **80 fF**, so tens of ps. That delay lands on x1's
sampling edge only, pushing the edge sample *later* — the **same direction** as the duty
error, adding perhaps another 0.02-0.04 UI to the up region. Rank 1 and rank 2 have a
single joint fix.

### Rank 3 — the `d_latch` tail cannot be a current source, which makes the timing swing with corner

`XM2 net4 vbias VSS VSS nmos w=24u l=1u ng=4` mirrors `ibias_mirror`'s W 4 um / L 1 um
diode (blocks.inc:98) carrying the chip's 40 uA, i.e. **6:1 -> 240 uA nominal**. Through the
5.6 kohm `rhigh` load that demands **1.34 V** of swing, more than any supply in the range
1.08-1.32 V. The tail therefore sits in triode, the latch node slams to a level set by a
resistor/device divider, its **falling edge is device-driven and fast while its rising edge
is a 5.6 kohm RC** (~60 ps with ~10 fF), and the p-skewed output inverter (3 um / 1 um, i.e.
pull-up ~1.2x the pull-down, trip above VDD/2) converts that asymmetric edge into a
duty-biased CMOS signal. By the 1.3 derivation this stretch is common to `net1`, `net5` and
`B+` and cancels in `W_up - W_dn` over a balanced pattern — but it is the main reason the
whole answer moves with VDD and temperature, and it sets the size of the runts in rank 5.

### Rank 4 — `tcq(x5) - tcq(x3)`: the one flip-flop that samples the raw data

The only term that survives in `W_up - W_dn` (1.3). `x5` is the sole flip-flop whose D is
the CTLE output (~0.28 V differential; `ctle_swing 0.2773 V`, EXPERIMENTS 2.6) rather than a
rail-to-rail CMOS node, **and** its master's transparent window is `(1 - dcy) * UI` — the
*short* half, 0.405 UI at ff/-40 C/1.32 V. Any excess resolution time in x5 subtracts
directly from the down pulse and leaves the up pulse untouched, because `net1` bounds only
`down`. This is the genuine pulse-*width* term, and the one `pd_pulsewidth.spice` measures
by comparing rail-to-rail data against CTLE-level data. Expect tens of ps, i.e. a few per
cent of a UI — real, and an order of magnitude short of rank 1.

### Rank 5 — hazard runts: each decision glitches the *other* output

From 1.3: on an up decision `net1` and `B+` toggle on the same clock edge, so `down` gets a
runt of width `|tcq(x5) - tcq(x3)| + |t_A - t_B|`; on a down decision `net5` and `B+` toggle
together, so `up` gets a runt of width `|t_A - t_B|` only. The down runt is the bigger one
(it carries the rank-4 term), so the runts push the average **down** — the wrong sign to be
the cause, but real charge that belongs in the budget and that partly explains why rank 1
over-predicts.

### Rank 6 — unequal load on the two XOR A-side signals (the real content of "gate counts")

The `up` path passes through one more `d_flip_flop` (x2) than `down`, which sounds like an
extra delay and **is not**: x2 is re-clocked, so `net5` transitions on the same clock edge
as `net1`. What the extra flip-flop does cost is **input capacitance on `net1`**:

| node | loads | approx C |
|---|---|---|
| `net1` | x6's A-port gates (`XM5` pMOS 2 um + `XM7` nMOS 2 um) **plus** x2's CML input `XM1` (5 um) | ~18 fF |
| `net5` | x7's A-port gates only | ~8 fF |

Both are driven by the identical `d_latch` output inverter (3 um / 1 um), so `net1` is
roughly 2x slower. That delays `a_net1`, which narrows `down` (1.3) and leaves `up` alone —
same sign as rank 4, smaller. Tens of ps at most.

### Rank 7 — `inv_cp`'s rise/fall asymmetry (pMOS 2 um / nMOS 1 um)

`up` passes through it and `down` does not. Its nMOS (1 um) beats its pMOS (2 um, ~2.5x less
mobile, so effectively ~0.8x), so `upb` falls faster than it rises **and** its trip sits
below VDD/2: both widen the pMOS switch's ON window relative to the incoming `up` pulse,
by roughly its tpLH - tpHL into the ~2 fF of `XMPSW` gate. Direction: up-heavy. But it is
**already bounded by measurement** — `sim/results/cp_charge_ff.log`, with equal ideal
one-UI pulses on both inputs at Wnsw 0.5 / Winvp 2.0 (the as-built sizing), gives
q_up **+0.660 fC** against q_dn **-1.211 fC** at -40 C/1.32 V and +0.597/-0.845 fC at
125 C/1.20 V in `cp_charge_tt.log`. The pump is **down**-heavy, the opposite sign to the
drift, so this cannot be the cause.

**Caveat worth acting on:** `cp_charge.spice` drives `u` with an ideal 20 ps-edge `PULSE`,
while in the receiver `up` is driven by a `robs_xor` into `inv_cp`'s ~6 fF. The real edge is
much slower, so the true widening is larger than `cp_charge` reports. Re-running that deck
with a realistic edge rate is a ten-minute job and would tighten this bound.

### Rank 8 — XOR input ordering: measured out, and it cancels

In `robs_xor` (blocks.inc:399) the A port gates the **VDD-side** pMOS (`XM5`/`XM2`) and the
**output-adjacent** nMOS (`XM6`/`XM7`), while the B port gates the **output-adjacent** pMOS
(`XM1`/`XM3`) and the **VSS-side** nMOS (`XM4`/`XM8`). So A is slow when it pulls the output
high (an internal node has to charge first) and fast when it pulls it low; B is the reverse.
Both XORs use the identical assignment (x6: A = `net1`, B = `B+`; x7: A = `net5`, B = `B+`),
so the internal-node penalty appears **once in each** of `W_up` and `W_dn` and cancels in
the difference (1.3). It skews both pulses' edges equally and is not a cause. Recording it
here so it stops being re-suspected.

---

## 3. Proposed fixes

### Fix 1 (primary) — build `rclk-` from the ring's other phase instead of by inverting `rclk+`

Kills ranks 1 and 2 together. Today (blocks.inc:56):

```
x4  Vdd Vss clkraw- clkraw+ net3 net4 Vdd diff_amp_inv   <- clkraw+ is UNUSED
x13 Vdd Vss clkraw- clkraw_sb sb_inverter
x11 Vdd Vss clkraw_sb rclk+   inverter_buffer
x12 Vdd Vss rclk+    rclk-    single_inverter            <- delete
```

Replicate `x13`+`x11` on the idle `clkraw+` to make `rclk-`, and delete `x12`. Each phase
then reaches the detector through an **identical** chain from a **differential** source, so
whatever duty distortion the chain has becomes common-mode: `rclk-`'s rising edge lands
exactly half a ring period after `rclk+`'s, which is the only thing x1 needs. This is robust
to *which* stage causes the distortion — the point on which the logs are suggestive rather
than conclusive.

**Device cost:** +1 `sb_inverter` (2 MOS: pMOS 2 um, nMOS 1 um, L 0.13 um; plus its
`cap_cmomf` 8.8 x 8.8 um = 77 um^2 and its `rhigh` 1 x 70 um = 70 um^2) and +1
`inverter_buffer` (4 MOS: pMOS 6 um ng=4, nMOS 7 um ng=2, pMOS 16 um ng=8, nMOS 8 um ng=4),
minus 1 `single_inverter` (2 MOS: pMOS 16 um ng=8, nMOS 8 um ng=4).
**Net +4 MOSFETs, +1 MOM cap, +1 poly resistor, ~+150 um^2** in a 146,641 um^2 slot (0.1 %).

Residual: each phase still has its own duty error, which shortens x5's master transparency
window to `(1-dcy)*UI` (rank 4). That is a second-order cost and is what Fix 2 and the deck
address.

### Fix 2 (cheap, second-order) — match the load on `net5`/`net6` to `net1`/`net2`

Targets rank 6. Add two dummy devices whose gates sit on `net5` and `net6` with
source/drain/bulk on VSS, sized to replicate x2's CML input pair so both A-side signals see
the same capacitance and `a_net1 = a_net5`.

**Device cost: 2 MOSFETs, nMOS W 5 um / L 0.13 um each (~1.3 um^2 of gate), no routing
outside the detector.** Worth tens of ps of the down pulse — do it only alongside Fix 1, it
will not move +77 nA on its own.

### Explicitly NOT recommended — trimming the pump against the phase-average

EXPERIMENTS 2.11 swept `cp_bias` `XMP2` and got about -10 nA per 0.15 um, needing
XMP2 ~ 2.45 um to reach tt/125 C's +10 nA. The analysis above says why that knob is the
wrong one: it corrects a fixed **current** ratio, while the error is a **phase-region**
ratio that itself moves with corner (0.595 at ff/-40 C/1.32 V against 0.554 at
tt/125 C/1.20 V, section 2 rank 1). A static pump trim cannot track it, and centring one
corner would de-centre the other.

---

## 4. The deck

`sim/decks/pd_pulsewidth.spice` — written, **queued but NOT YET RUN**. See section 5.

* Detector alone, driven by two ideal `PULSE` clock sources and two ideal `PULSE` data
  sources. No ring, no CTLE, no loop filter, no channel.
* The `tiny_pll_charge_pump` is instantiated **purely as the load** on `up`/`down`, with
  `out` held at 0.546 V, so the 6:1 gate-load ratio of rank 7 is present rather than
  idealised away. `vbias` comes from `ibias_mirror` at 40 uA and `cp_bias`, as in `CDR`.
* Data is **1100** (the data `PULSE` has period 2*UI), not 0101: at a plateau phase 0101
  makes one output assert continuously and leaves no pulse edge to measure.
* Sweep: `dcy` 0.50 (ideal clock) and 0.595 (the duty measured at ff/-40 C/1.32 V) x
  temperature -40 / 125 C x supply 1.08 / 1.20 / 1.32 V x data phase 0.25 / 0.75 UI =
  **24 points**, each a 100 ns transient at 5 ps.
* Reports per point: `f_clk` (self-check that `alterparam` took), `f_up` and `f_dn` (the
  fraction of time each output is asserted — these never fail and say which lobe the phase
  landed in), `q_net_fC`, and `w_up1/w_up2`, `w_dn1/w_dn2` (two pulse widths ~33 ns apart
  that must agree).

**What it decides.** If `w_up ~ w_dn` at both `dcy` values while `f_up/f_dn` tracks `dcy`,
rank 1 is confirmed, the detector's intrinsic width asymmetry is small, and the fix belongs
in the clock path (Fix 1) rather than in the detector. If instead `w_up - w_dn` is tens of
ps even at `dcy = 0.50`, rank 4/6 are larger than estimated and Fix 2 grows in value. The
header also documents the one-line change (`damp`/`dcm`) that re-runs it at the CTLE's
0.28 V data swing, which isolates the rank-4 `tcq(x5)` term by difference.

Traps observed, with the deck's line-level comments: 2.24 (every swept quantity is a
`.param` set by `alterparam` + `reset`, because `alter` cannot set a `PULSE` list), 2.19
(`.param` does not reach into `.control`, so `meas` FROM/TO are literals and the 50 %
threshold arrives as the loop variable `$vh`, with the supply set to `2*$vh`), 2.9 (the
width `meas` are in their **own** `print` statements, so a phase at which one output never
pulses blanks one line instead of the row), 2.3 (explicit `save` list covering every node
any `meas` touches), 2.1 (loop variables printed as vectors), 2.21 (numeric loops only),
2.22 (`ROWEND` after each print; 24 rows x 4 lines expected), 1.4 (`.global sub!` + `Vsub`
for the `rhigh` latch loads), 1.6b (`f_clk` proves the sweep actually varies).

## 5. Status

Written, queued, **never ran**. `tools/safe_ngspice.sh` serialises every ngspice behind a
global lock, and `ring_loaded.spice` held it for the whole window (762 s elapsed of its
2400 s cap when the 5-minute budget expired). The queued parse check was cancelled rather
than left to fire unattended. **The deck is unverified — ngspice has not parsed it, so
assume a first run will need a syntax pass.** Run it, or at minimum let one point complete,
before reading anything into it:

```
cd sim/decks && ../../tools/safe_ngspice.sh pd_pulsewidth.spice \
    ../results/pd_pulsewidth_ff.log 2500 2400 2000
```

Sections 1-3 do not depend on the deck: they come from `sim/netlists/blocks.inc` and from
logs already in `sim/results/`.
