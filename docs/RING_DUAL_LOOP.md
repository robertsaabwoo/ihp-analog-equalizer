# The dual-loop ring trim

## 1. The problem this solves

The receiver's ring oscillator, ported and re-tuned, reaches the 600.6 MHz
baud rate at 8 of the 27 PVT corners swept.  A bang-bang (Alexander) phase
detector is *phase*-only: it has no frequency acquisition, so a ring that
cannot reach the baud rate never locks, at any control voltage.  Covering all
27 corners needs the ring's centre frequency moved by **+15.2 % / −8.1 %**
of its nominal value, and the fine loop's own control range is only 1.166:1
and is spent on tracking, not on centring.

Three ways of supplying that were considered and two rejected:

| approach | why not |
|---|---|
| external band-select pins | the Chipalooza slot has 1–3 analog pads; spending two on trim bits is not affordable, and the user was clear the pins are not available |
| a clocked FSM that sweeps bands | needs a clock the receiver does not have before it locks, plus digital area and a reset strategy |
| **an analog coarse loop** | ~30 devices, no clock, no pins — adopted |

## 2. What vctrl actually reports

The coarse loop's only possible error signal is `vctrl`, because this is a
reference-less CDR: there is no second frequency in the chip to compare the
ring against.  The theory was that a band which cannot reach the data rate
rails `vctrl` high and one that cannot go slow enough rails it low — a signed
error, which a window comparator could turn into a bidirectional trim.

Theory was not sufficient, and it was wrong.  `tools/band_probe.sh` re-ports
the design with the ring load resistor moved out of band and runs the full
closed-loop 1.5 µs transient, reading `vctrl` in three windows:

| ring load | f reached | f error | vctrl @ 1.0–1.1 µs | @ 1.3–1.4 µs | @ 1.4–1.5 µs | drift |
|---|---|---|---|---|---|---|
| 7355 Ω (nominal, locks) | 600.614 MHz | +0.0023 % | 0.5992 V | 0.5990 V | 0.5990 V | −0.5 mV/µs |
| 8460 Ω (too slow) | 576.43 MHz | −4.02 % | 0.7101 V | 0.7395 V | 0.7531 V | **+107 mV/µs** |
| 6400 Ω (too fast) | 673.52 MHz | +12.14 % | 0.7557 V | 0.8054 V | 0.8223 V | **+167 mV/µs** |

The good news is that `vctrl` is an excellent *lock* detector.  Locked, it is
flat to half a millivolt per microsecond and sits at 0.599 V.  Out of band, in
either direction, it climbs at a hundred times that rate and is already 140–220
mV away before 1.5 µs is up.  A single threshold at ~0.70 V separates the three
cases cleanly.

The bad news is the column that matters for a bidirectional trim: **both wrong
bands drive `vctrl` the same way — up.**  There is no sign information in it at
all, and the window-comparator architecture sketched for §4 is dead.

Two mechanisms explain it, and both are inherent rather than fixable:

* A bang-bang phase detector has, by construction, *no* frequency
  discrimination.  With a frequency error the sampling phase slips
  continuously, early and late are each asserted for half of every beat
  period, and the average phase-detector output over a slip cycle is zero
  whichever side of the baud rate the ring is on.
* What is left when the phase term averages out is the charge pump's own
  up/down mismatch, measured at **11.0 %** (`sim/results/cp_current.log`).
  That is a one-signed current, so an unlocked loop integrates it into a
  one-signed drift.  The 6400 Ω case, being three times further out of band,
  drifts *faster* — consistent with a purely mismatch-driven ramp, since the
  further out it is the less of the pump's charge the phase term recovers.

Trimming the pump mismatch would not rescue the sign; it would only replace a
clean upward ramp with an aimless random walk, which is a worse detector.  The
architecture has to stop asking `vctrl` which way to go.

(Logs: `sim/results/e2e_band_8460.log`, `sim/results/e2e_band_6400.log`,
`sim/results/e2e_lock_tt.log`.)

## 3. The architecture the measurement forces

If the error signal is unsigned, the coarse loop cannot be a trim.  It has to
be a **sweep, halted by a lock detector** — which is the standard answer for a
reference-less CDR with no frequency detector, and is cheaper here than the
bidirectional version would have been because the detector needs one threshold
instead of two.

```
    vctrl ──> [ lock detector: vctrl > VH ? ] ──> sweep_en
                                                    │ gates
                    20 nA ──────────────────────────┴──> Ccoarse ──> vcoarse
                                                          │   │
                              [ wrap: vcoarse > Vtop ] ────┘   └──> 10 trim gates
                                          │ dumps Ccoarse back to Vbot
```

* **Unlocked** — `vctrl` above threshold — a 20 nA source charges `Ccoarse`,
  `vcoarse` ramps up, the trim pMOS turns progressively off, the ring load
  rises and the ring sweeps *monotonically downward in frequency*.
* When `vcoarse` reaches the top of its range the wrap comparator dumps
  `Ccoarse` back to the bottom in a few nanoseconds and the sweep restarts from
  the fast end.  The retrace is far too fast for the fine loop to catch, which
  is correct: it is a retrace, not a search.
* **Locked** — `vctrl` back inside the window — the source is gated off and
  `vcoarse` holds.  Leakage on a 5 pF node over a data frame is negligible
  compared with the fine loop's own tracking range.
* If the loop later falls out of lock (temperature, supply), `vctrl` rises, the
  sweep resumes from wherever it stopped and wraps as needed.  Nothing is stuck
  at a rail, which is the failure the one-way-no-wrap version would have had.

### 3.1 How slow the sweep must be

The fine loop settles in under 1.5 µs.  The sweep must move the ring by much
less than the fine loop's capture range during that settling time, or it will
sweep straight through lock.  A full coarse range of 25 % — 150 MHz — traversed
in 200 µs is 0.75 MHz/µs, so during a 1.5 µs acquisition the target moves
0.19 %.  That is the design point: **20 nA into a 5 pF `Ccoarse`**, 4 mV/µs, a
0.5 V ramp in 125 µs.

5 pF is 394 µm² as a MOS capacitor at the measured 12.7 fF/µm².
`docs/DESIGN.md` rules MOS capacitors out for the other two capacitors in this
design, because their value moves 7.6 % between 0.6 V and 1.2 V and far more
near threshold.  That objection does not apply to this one: it sets a sweep
*rate*, not a pole, and the rate is allowed to vary by an order of magnitude as
long as it stays far slower than the fine loop.  In exchange it is six times
denser than `cap_cmomf` — 394 µm² instead of 2400 µm².

## 4. The knob

The fine loop drives the ring's *tail current*.  Above the point where a stage
can charge its own load faster than its RC, more tail current buys nothing: the
load resistor sets the ceiling, and the ceiling is what fails at temperature.
So the coarse knob must move the *load*, not the current.

    VDD --+--[Rload poly]--+-- vo+
          |                |
          +---|MTR pMOS----+        gate = vcoarse (global)

one pMOS across each of the ten load resistors, all ten gates tied to a single
global `vcoarse`.  The poly resistor sits at the *slow* end of the required
span and the pMOS only ever speeds the ring up, so at `vcoarse = VDD` the trim
is entirely absent and the ring is the ported design with a slightly larger
load — there is no state in which the trim can make things worse than the
untrimmed circuit.

This is not the diode-connected-load idea that was tried and rejected.  There
the transistor *was* the load, so its process spread was the ring's spread, and
5 of 24 swept points stopped oscillating.  Here the poly resistor is still the
load and the pMOS is a correction of order 20 %, so the pMOS's own spread is
attenuated by the parallel ratio.

`sim/decks/vco_ct.spice` sweeps `vcoarse` against `vctrl` to measure what range
the leg actually delivers and whether the ring still swings at every setting.

## 5. Status

- [x] band signature measured — refuted the bidirectional trim, justified the
      single-threshold sweep (§2)
- [ ] trim-leg range sweep (`sim/decks/vco_ct.spice`) — running
- [ ] lock detector: threshold, hysteresis, behaviour against 65 mV of ripple
- [ ] sweep source and wrap comparator
- [ ] closed dual loop, in-band (must not disturb the locked numbers)
- [ ] closed dual loop, acquiring from a wrong band
- [ ] PVT corner sweep of the dual loop
