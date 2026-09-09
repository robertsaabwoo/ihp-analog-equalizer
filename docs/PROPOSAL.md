# Equalizing serial-link receiver front end with reference-less CDR

**Chipalooza design proposal — IHP SG13CMOS5L**

This revises the proposal written against the sky130 prototype
([`chipalooza-proposal`](https://github.com/robertsaabwoo/ttsky-analog-equalizer/blob/chipalooza-proposal/PROPOSAL.md)
on the source repository) to match what has actually been built and measured on
SG13CMOS5L. Where that document projected, this one cites a run. Where a number
is still projected, it says so.

*Contains no personal or institutional details. Designer CV and test-equipment
list are submitted separately, per the challenge rules.*

---

## 1. Type of IP block

A **mixed-signal serial-link receiver front end**: a continuous-time linear
equalizer (CTLE) followed by a **reference-less bang-bang (Alexander)
clock-and-data-recovery loop**. It accepts a degraded differential NRZ stream,
equalizes the loss of the path in front of it, and recovers a clock
synchronous with the data — with **no external reference clock**.

This is a SERDES-RX / programmable-filter class block, self-contained, and
useful to any SoC that has to receive serial data over a lossy path.

## 2. Functional description

**Signal path:** differential input → CTLE → Alexander phase detector → charge
pump + loop filter → ring VCO → recovered clock → output buffers.

- **CTLE.** A source-degenerated NMOS differential pair with poly load
  resistors. The degeneration RC sets a transfer zero that boosts high
  frequencies to cancel the channel's pole. A single bridging capacitor across
  the two source nodes gives twice the effective degeneration capacitance for
  half the area of two capacitors to the tail — which matters here, because
  SG13CMOS5L has **no MIM capacitor** and the densest linear option
  (`cap_cmomf`, measured at 1.29 fF/µm²) is already 1.55× the area of the
  sky130 MIM for the same value.

- **CDR.** Reference-less and bang-bang. The recovered clock comes from a
  five-stage CML ring oscillator whose tail current is set by the loop's
  control voltage; there is no reference clock and no phase-frequency
  detector. Because a bang-bang detector corrects **phase only**, frequency is
  established by centring the ring and by a **self-timed startup precharge**
  that seeds the control voltage above the oscillation threshold at power-up,
  making cold start independent of the data polarity at that instant.

- **Bias.** One bandgap-referenced current in, mirrored on-chip. This replaced
  a bias *voltage* in the prototype for a measured reason: on 1.2 V, a fixed
  gate voltage on a tail device gives a 15 dB spread in CTLE gain across PVT
  and an outright collapse at the fast corner. See §5.

- **Devices.** 1.2 V core CMOS (`sg13_lv_nmos`/`sg13_lv_pmos`), `rhigh` poly
  resistors, `cap_cmomf` metal-fringe capacitors. No MIM, no HBT, no inductor,
  no deep n-well — nothing outside the SG13CMOS5L device set, enforced by a
  test in CI.

## 3. Resources used

**Supply.** The **1.2 V** rail only. The 3.3 V rail is not used, and no level
shifting is needed because the recovered clock leaves the block at 1.2 V
logic levels.

**Analog I/O**

| Name | Dir | Description |
|---|---|---|
| `vinp`, `vinm` | in | Differential NRZ data, two dedicated analog pads. AC coupling recommended; input common mode set internally at 0.70 V. |

**Bias**

| Name | Dir | Description |
|---|---|---|
| `ibias` | in | One bandgap-referenced current, 25 µA nominal. Sets the CTLE tail through a 10:1 mirror and the CML tail bias. |

**Digital outputs (1.2 V)**

| Name | Dir | Description |
|---|---|---|
| `clkout_p`, `clkout_n` | out | Recovered clock, both phases. Both are buffered deliberately: driving only one leg of a differential ring loads it asymmetrically and skews the duty cycle. |

Total: 2 analog pads, 1 current bias, 2 digital outputs. Well inside the ≤ 16
control and test lines a slot is allocated.

**Test and observability — planned, not yet built.** A buffered tap on the CTLE
output (`EQ_MON`) for eye and frequency-response measurement, a tap on the
loop-filter voltage (`VCTRL_MON`) for acquisition observability, and a divided
recovered clock (`TCLK_DIV`, ÷8) for low-bandwidth jitter capture. These are in
the sky130 proposal and are **not** in the current netlist.

## 4. Target specification

Values marked **measured** cite a run in this repository. Values marked
*target* are design intent that has not been demonstrated on this process.

| Parameter | Min | Typ | Max | Status |
|---|---|---|---|---|
| Data rate (NRZ) | — | 600.6 Mb/s | — | single-rate by design; UI = 1.665 ns |
| Supply | 1.08 V | 1.2 V | 1.32 V | ±10 %, simulated |
| Operating temperature | 0 °C | 27 °C | 110 °C | committed range; −40…125 °C simulated |
| Input amplitude, differential pp | 50 mV *target* | 200 mV | 400 mV | ≤ 400 mVpp keeps the CTLE linear |
| Input common mode | — | 0.70 V | — | set internally; AC coupling recommended |
| Channel loss compensated at Nyquist | — | 13.7 dB | — | 500 Ω / 5 pF, a 63.7 MHz pole |
| CTLE gain at Nyquist | +9.4 dB | **+13.2 dB** | +15.5 dB | **measured**, 27 corners |
| CTLE boost (Nyquist − DC) | +4.9 dB | +6.4 dB | +7.9 dB | **measured**, 27 corners |
| Channel + CTLE at Nyquist | −4.4 dB | **−0.7 dB** | +1.6 dB | **measured**, 27 corners |
| Ring VCO range, tt/27 °C | 538 MHz | — | 630 MHz | **measured** |
| CTLE supply current | — | 351 µA | — | **measured** at 1.2 V |
| Total block current | — | — | — | *not measured* |
| Recovered-clock RMS jitter | — | 0.7 % UI *target* | 2 % UI *target* | *not measured on this process* |
| Lock / acquisition time | — | — | 2 µs *target* | *not measured on this process* |
| CID tolerance | 15 UI *target* | — | — | *not measured on this process* |
| Recovered-data BER | — | < 1e-9 *target* | — | *not measured* |

The jitter, lock-time and CID targets are the sky130 prototype's **measured**
results carried over as targets. They are not results on SG13CMOS5L and are not
presented as such.

## 5. What the port established, and what it cost

Three findings are worth a reviewer's attention because they are measurements,
not expectations.

**A bias voltage is not a bias current.** Holding the tail gate at a fixed
0.45 V gives a CTLE Nyquist gain of +14.2 dB at ss/−40 °C/1.32 V and −1.3 dB at
ff/−40 °C/1.08 V — a 15 dB spread, with the stage collapsed at the fast corner
because a fixed gate voltage asks for more current than a 1.2 V stack has
headroom for. Replacing it with a current mirror from the harness's bandgap
reference cuts the spread to 6.1 dB and holds the tail current within 2.5 %
across ±10 % of supply. **This is the single most valuable thing the harness
provides to this block.**

**1.2 V costs about 3 dB of CTLE gain, and the load resistance buys it back.**
The gain is `(gm/Id) · ΔVload`, and ΔVload is bounded by the input pair's
saturation. Current was swept from 65 µA to 620 µA and moved the Nyquist gain
by 2 dB; the load resistance moved it by 5 dB. Final: 3.5 kΩ, 351 µA,
+13.17 dB — matching the 1.8 V prototype's +13.32 dB.

**The ring oscillator had to be re-sized, or the block does not work at all.**
A bang-bang detector has no frequency acquisition. Ported unchanged the ring
reaches 424–554 MHz against a 600.6 MHz baud rate. Shortening the input pair
from 1.0 µm to 0.9 µm gives 538–630 MHz, putting the baud rate at
vctrl = 0.60 V. The tuning range is only 1.3:1 because above the starting point
the ring is RC-limited by its own load resistor rather than current-starved,
and **that narrowness is the block's main open risk** — see §7.

## 6. Test plan

Bench: a pattern generator/BERT drives differential NRZ through a calibrated
channel (defined series R and shunt C, optionally an additional lossy trace); a
sampling oscilloscope and the BERT capture the outputs; a temperature chamber
and programmable supplies cover PVT.

1. **CTLE frequency response** — swept-sine or PRBS at `EQ_MON`; extract DC
   gain, peak boost and −3 dB bandwidth.
2. **Eye diagrams** — at `EQ_MON` and reconstructed from the recovered clock;
   eye height and width against channel loss.
3. **BER / bathtub** — against channel loss and input amplitude; horizontal and
   vertical bathtub curves.
4. **Recovered-clock jitter** — from `clkout_p` and `TCLK_DIV`; RMS and
   peak-to-peak in UI, in lock.
5. **Acquisition and robustness** — lock time from power-up for both data
   polarities, observed on `VCTRL_MON`; CID tolerance on PRBS7, PRBS15 and
   8b/10b; lock range.
6. **PVT** — the core measurements over 0–110 °C and ±10 % supply.

All stimuli, decks and analysis scripts are in this public repository, and the
verification runs entirely on open-source tools: xschem, ngspice with the IHP
open PDK, and the PSP 103.6 Verilog-A models compiled with OpenVAF.

## 7. Known risks, stated plainly

**The ring oscillator's tuning range is 1.3:1 and has only been measured at one
corner.** That is the risk that decides the block. The sky130 prototype had the
same architecture, the same narrowness, and failed at 125 °C and at low supply;
that project characterised the limitation and accepted it. This port has
re-centred the ring so it reaches the baud rate at nominal, which the direct
port did not, but the corner measurement is in progress and a 1.3:1 range is
narrow against a PVT spread that will be wider.

If it proves insufficient, the fix is coarse tuning, and there are two
candidates: a switchable load-resistor leg per stage under one digital control
bit — the harness provides the control lines — or diode-connected pMOS loads in
place of the poly resistors, whose small-signal resistance follows the tail
current and so widens the range without a control pin. Neither has been
simulated.

**The loop has not been closed in simulation on this process.** Everything
above is block-level. Acquisition, eye and jitter on SG13CMOS5L are not yet
measured, and the repository says so in every place a number would otherwise
appear.

**Single-rate by design.** The frequency plan — ring centre, loop filter,
precharge release timing — is chosen for one baud rate. Supporting others means
instantiating additional frequency-set cores and multiplexing under digital
control, reusing the CTLE, phase detector and startup cell unchanged. That is a
planned optional extension, not part of a v1 commitment.
