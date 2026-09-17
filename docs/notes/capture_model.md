# A quantitative model of loop capture

Built entirely from measurements already in `sim/results/`. **No simulation was run
for this note.** Every number below is either (M) read from a log, or (D) derived by
arithmetic from logged numbers — each row says which.

The question: at ff/-40 C/1.32 V the fine loop drifts up and never captures, while
tt/27 C, tt/125 C, ff/125 C, tt/-40 C and ss/-40 C all lock. What is the dimensionless
quantity that separates them?

---

## 0. Inputs and where they come from

| quantity | symbol | value | source | M/D |
|---|---|---|---|---|
| bit period | `T_b` | 1.665 ns (600.60 MHz) | design constant | M |
| loop filter capacitance | `C` | 1134 fF + 174 fF = **1308 fF** | design constant (caps x3, EXPERIMENTS 2.9) | M |
| filter resistor vs temperature | `R(T)` | 17452.9 / 15000.0 / 11921.5 ohm at -40 / 27 / 125 C | `rhigh_tc.log` | M |
| pump current vs (T, VDD, vout) | `I_pump` | 396-476 nA over 27 (T,VDD,vout) points; **~430 nA** typical | `cp_ibias_check.log` | M |
| ring tuning slope | `K_vco` | per corner, see §2 | `loop_scurve_*.log`, `vco_ct_seed_*.log`, `vco_ct_walkseed.log` | M/D |
| detector characteristic vs phase | `I(phi)` | 10 phases over 1 UI, ideal clock at the baud rate | `pd_phase_{tt125,ffm40}.log` | M |
| phase-average of that curve | `I_avg` | **+10.4 nA** (tt/125 C), **+77.1 nA** (ff/-40 C) | same logs, arithmetic mean of the ten | D |

`I_pump` is taken as the mean of `i_up_na` and `i_dn_na` at the (T, VDD) of the corner
and the `p_vout` point nearest that corner's vctrl. **`cp_ibias_check.log` has no
process split** — its 27 rows are 3 temperatures x 3 supplies x 3 output voltages at one
process corner — so the `I_pump` used at ff and ss corners is a tt-process number. That
is the single largest unquantified input in this model.

Verification of the `I_avg` arithmetic (both averages recomputed from the ten logged
`i_net_na` values, not copied from EXPERIMENTS):

```
tt/125 C  -344.855 -164.519  -50.815 +309.929 +310.592 +309.082 +175.038  +54.025 -150.249 -344.003  -> +10.42 nA
ff/-40 C  -335.147 -331.713 -256.835 +197.399 +419.707 +415.429 +408.143 +412.305 +170.019 -328.199  -> +77.11 nA
```

---

## 1. The model

### 1.1 Drift — what an unlocked loop integrates

A slipping loop sweeps every clock phase uniformly, so what it integrates is the
**phase-average** of the detector characteristic, not any single point on it. That
current charges the whole filter capacitance:

```
dV/dt = I_avg / C                      [V/s]        (drift in control voltage)
df/dt = K_vco * I_avg / C              [Hz/s]       (drift in ring frequency)
```

`dV/dt` is `K_vco`-free; only the frequency drift carries `K_vco`.

### 1.2 Capture window — how far off the loop may be

A bang-bang detector carries no frequency information. Its only instantaneous authority
is the proportional step: one decision drives `I_pump` through `R` and moves vctrl by

```
dV_step  = I_pump * R                  [V]          (proportional step, per decision)
df_cap   = K_vco * I_pump * R          [Hz]         (capture window, half-width)
```

The loop is captured when its frequency error is inside `+/-df_cap`, because only then
can a single decision's proportional kick reverse the sign of the error.

### 1.3 Time available

The window expressed in vctrl is `+/-dV_step`; the drift crosses it at `I_avg/C`:

```
t_avail  = dV_step * C / I_avg = I_pump * R * C / I_avg        [s]  (half-window transit)
N_UI     = t_avail / T_b                                        (decisions available)
```

**`K_vco` cancels exactly.** The window and the drift are both proportional to `K_vco`,
so the *time* the loop spends inside its own capture window does not depend on the
tuning slope at all. This is the first non-obvious result of the model and it is why the
existing ripple screen (EXPERIMENTS 1.2) could not settle the question: that screen
compares `K_vco * ripple` against `K_vco * I_pump * R`, and `K_vco` cancels there too.

### 1.4 The condition

`K_vco` re-enters only through a quantity with a fixed frequency scale, and the only
fixed frequency scale in the system is the decision rate `1/T_b`. Define

```
Phi = df_cap * T_b = K_vco * I_pump * R_filter * T_b            [UI per decision]
```

**`Phi` is the fraction of a unit interval the recovered clock's phase moves per
decision when the loop is at the edge of its own capture window** — the loop's phase
slew authority per decision, measured against the thing it is trying to resolve.
A bang-bang detector resolves phase in units of UI; if one proportional kick throws the
sampling phase a large fraction of the way across the corrective lobe of the S-curve,
the loop slews through its own capture window instead of settling inside it.

Second factor, the drift normalised to the pump:

```
D = I_avg / I_pump                                              [dimensionless]
```

the fraction of the pump's full current that the slipping loop integrates as net DC
runaway. The full condition is the product:

```
Psi = Phi * D = K_vco * R_filter * I_avg * T_b   <   Psi_crit
```

`Psi` has a direct reading: `K_vco * R * I_avg` is the frequency offset the runaway
current produces through the filter's resistor alone, and `Psi` is the phase, in UI,
that this offset slips per decision.

`Phi` is computable at every corner (it needs only `K_vco`, `I_pump`, `R`). `D` needs
`I_avg`, which exists at only two corners. The two are therefore reported separately as
well as multiplied.

---

## 2. Per-corner numbers

`K_vco` is the local tuning slope at the corner's own operating vctrl. Sources:
`loop_scurve_*.log` where it exists (the ring measured *inside* the receiver — the best
source); otherwise the 25 mV-grid ring sweeps `vco_ct_seed_*.log` / `vco_ct_walkseed.log`.
Where both exist they agree: at ff/-40 C, `loop_scurve_ffm40.log` gives
(602.79-541.11)/0.05 = 1234 MHz/V and `vco_ct_seed_ffm40_132.log` gives
(605.18-573.95)/0.025 = 1249 MHz/V.

| corner | K_vco MHz/V | src | I_pump nA | R ohm | dV_step mV | df_cap MHz | **Phi** (1e-3 UI/dec) | closed loop |
|---|---|---|---|---|---|---|---|---|
| tt 125 C 1.20 V | 259 | `loop_scurve_tt125.log` (M) | 426.0 | 11922 | 5.079 | 1.315 | **2.19** | locks, `e2e_prbs_tt125_cpbias.log` |
| ss 125 C 1.08 V | 358 | `vco_ct_seed_ss125_108.log` (D) | 420.9 | 11922 | 5.018 | 1.796 | **2.99** | no lock in 2.5 us, see §6 |
| ss -40 C 1.08 V | 343 | `vco_ct_seed_ssm40_108.log` (D) | 432.7 | 17453 | 7.552 | 2.590 | **4.31** | locks, `e2e_dual_ssm40_108.log` |
| tt 27 C 1.20 V | 516 | `vco_ct_walkseed.log` (D) | 433.3 | 15000 | 6.499 | 3.351 | **5.58** | locks, `e2e_prbs_lr.log` |
| ff 125 C 1.32 V | 721 | `vco_ct_seed_ff125_132.log` (D) | 418.8 | 11922 | 4.992 | 3.599 | **5.99** | locks, `e2e_prbs_ff125_cpbias.log` |
| tt -40 C 1.20 V | 600 | `vco_ct_seed_ttm40_12.log` (D) | 439.4 | 17453 | 7.669 | 4.601 | **7.66** | locks *only seeded from above*, `e2e_prbs_ttm40_seed080.log` |
| **ff -40 C 1.32 V** | **1234** | `loop_scurve_ffm40.log` (M) | 440.5 | 17453 | 7.688 | 9.483 | **15.79** | **never captures**, `e2e_prbs_ffm40_lowripple_lr.log` |

### Drift, where it is measured (answers Q1)

| corner | I_avg nA | src | M/D | dV/dt mV/us | df/dt MHz/us | D = I_avg/I_pump | t_avail ns | N_UI |
|---|---|---|---|---|---|---|---|---|
| tt 125 C 1.20 V | +10.42 | `pd_phase_tt125.log`, mean of 10 phases at vctrl 0.60 | M/D | **7.97** | **2.06** | 2.45 % | 638 | 383 |
| ff -40 C 1.32 V | +77.11 | `pd_phase_ffm40.log`, mean of 10 phases at vctrl 0.60 | M/D | **58.95** | **72.72** | 17.51 % | 130 | 78 |
| ss 125 C 1.08 V | +17.30 | `run_dual_ss125_108.out` vctrl_e1/e2, closed loop | D | **13.23** | **4.74** | 4.11 % | 379 | 228 |
| ff -40 C 1.32 V (closed loop, vctrl 0.68-0.72 V) | +36.72 | `e2e_prbs_ffm40_lowripple_lr.log` vctrl_s1..s3 | D | 28.07 | 34.63 | 8.3 % | 273 | 164 |
| tt 27 C / ff 125 C / tt -40 C / ss -40 C | ~0 | their own locked runs | D | -0.37 / +1.09 / +0.54 / -1.09 | — | — | — | — |

**`I_avg` is not measured at the four corners that lock.** A locked run reports only the
residual drift, which is zero by definition of lock; it says nothing about what the loop
would have integrated while slipping. `pd_phase` exists at exactly two corners. This is
the model's principal gap.

Two corrections to the numbers in EXPERIMENTS, both recomputed here from the logs:

- **EXPERIMENTS 2.9 says vctrl at ff/-40 C climbs at "~57 mV/us, which needs ~74 nA".**
  The deck's windows (`e2e_prbs_ffm40_lowripple.spice` lines 152-154) are centred at
  1600, 2200 and 2800 ns, so s1 to s3 spans **1200 ns, not 600**:
  (0.7160819 - 0.6823970)/1.2 us = **28.07 mV/us = 36.7 nA**. The "74 nA" is a factor-2
  window slip. It does not change any conclusion in 2.9 — the push is still from the
  detector, not the pump — but the agreement it claims with `pd_phase`'s +77.1 nA is not
  real.
- The closed-loop drift (36.7 nA at vctrl 0.68-0.72 V) is legitimately *lower* than the
  `pd_phase` average (77.1 nA at vctrl 0.60 V), because the pump's own imbalance grows
  more down-heavy with vout: `cp_ibias_check.log` at -40 C/1.32 V gives net
  -21 nA at vout 0.60 and -37 nA at vout 0.70. 77.1 - 16 = 61 nA against 36.7 measured —
  the right direction, not the right size. **Capture happens near the crossing at
  0.546 V, so the model uses the `pd_phase` value.**

---

## 3. The condition, tested against all six measured corners (answers Q3)

### 3.1 `Phi < ~1e-2 UI per decision`

Ordering by `Phi`, current design (pump ~430 nA, C 1308 fF):

```
tt/125C  2.19  locks
ss/125C  2.99  (capture-capable; fails on time, §6)
ss/-40C  4.31  locks
tt/27C   5.58  locks
ff/125C  5.99  locks
tt/-40C  7.66  locks, but only when seeded from above  <-- the marginal corner
---------------------------------------------------------- threshold lies here
ff/-40C  15.79 does not lock                            <-- the only failure
```

**Six for six.** Every corner that locks is below 8e-3; the only corner that does not is
at 1.6e-2, a factor 2.06 above the worst corner that locks. The corner the log describes
as marginal ("locks only when seeded from above") is the one sitting immediately below
the boundary. The threshold is bracketed at `7.7e-3 < Phi_crit < 1.58e-2`.

### 3.2 `Psi = Phi * D`, where `D` exists

| corner | Phi | D | **Psi** | outcome |
|---|---|---|---|---|
| tt 125 C | 2.19e-3 | 2.45 % | **5.36e-5** | locks |
| ss 125 C | 2.99e-3 | 4.11 % | **1.23e-4** | capture-capable, time-limited |
| ff -40 C | 1.58e-2 | 17.51 % | **2.76e-3** | fails |

A 52x separation between the corner that locks and the corner that does not, against
7.2x for `Phi` alone — but on two data points. `Psi_crit` is bracketed only as
`5.4e-5 < Psi_crit < 2.8e-3`, a factor of 51. **`Psi` is the physically complete
condition; `Phi` is the part of it that can actually be measured at every corner.**

### 3.3 Candidate conditions tested and refuted

These are recorded so they are not re-derived:

1. **Beat cycles inside the window**, `N_beat = t_avail * df_cap = K_vco C (I_pump R)^2 / I_avg`
   — "does the loop get at least one full phase slip while crossing its window?"
   Computes to 0.84 at tt/125 C (locks), 1.24 at ff/-40 C (fails), 0.68 at ss/125 C.
   **Ranks ff/-40 C as the *best* of the three. Refuted by the data.** Root cause: `K_vco`
   enters this group with the wrong sign, because a steeper slope widens the window in Hz
   faster than it speeds the drift.
2. **The ripple screen of EXPERIMENTS 1.2**, wobble `K_vco * V_ripple` against the capture
   range. `K_vco` cancels between the two sides, and the measured ripple is itself
   ~2 x `I_pump * R` (ff/-40 C: 2 x 7.69 = 15.4 mV predicted against 15.47 mV measured,
   `e2e_prbs_ffm40_lowripple_lr.log`; tt/27 C: 13.0 against 15.10, `e2e_prbs_lr.log`), so
   the screen compares a quantity against itself. Using each run's own measured ripple,
   ff/125 C scores 6.0e-2 and locks while ff/-40 C scores 3.2e-2 and fails. **Refuted**,
   consistent with EXPERIMENTS 2.9's own conclusion that ripple was not the blocker.
3. **Linearised loop dynamics from the measured S-curve slope.** `pd_phase` gives the
   detector gain directly: 3610 nA/UI at tt/125 C (rising crossing, -51 -> +310 nA over
   0.1 UI) and 4540 nA/UI at ff/-40 C (-257 -> +197). With `zeta*w_n = R*K_pd*K_vco/2`
   this makes ff/-40 C the *faster and better damped* loop (7.8 MHz, zeta 0.75) against
   tt/125 C (0.89 MHz, zeta 0.21). **Refuted** — every linear-loop criterion says the
   failing corner should acquire more easily.
4. **Pump charge asymmetry** (`cp_charge_*.log`): ff/-40 C is net -0.55 fC, *down*-heavy,
   the opposite sign to the drift. Already refuted in EXPERIMENTS 2.13; re-confirmed here
   as unusable for `I_avg`.
5. **Up/down duty ratio** (`pd_probe_*.log`): 1.63 at ff/-40 C against 2.19 at tt/125 C
   which locks. Wrong sign. Already refuted in EXPERIMENTS 2.7 #5.

---

## 4. Where the condition fails to predict

It is right six times out of six on lock/no-lock, and wrong or silent about four things:

1. **Seed dependence.** tt/-40 C locks from a 0.80 V seed
   (`e2e_prbs_ttm40_seed080.spice` line 135, `.ic v(vctrl)=0.80` -> 600.510 MHz) and not
   from the 0.637 V seed taken off the ring-alone sweep
   (`e2e_prbs_ttm40_12.spice` line 128 -> 625.85 MHz, +4.2 %). `Phi` is a single number
   per corner and cannot express that. Same for ff/-40 C, which fails from a 0.546 V seed
   (`..._lowripple_lr`) and from a 0.70 V seed (`..._seed070`, 687.6 MHz) alike — the
   model says it fails from everywhere, which happens to be right, but not because it
   modelled the seed.
2. **Acquisition time.** `Phi` says ss/125 C should capture easily (2.99e-3) and it did not
   lock in 2.5 us. That is a separate failure mode and needs the separate model in §6.
3. **Design-revision portability.** Three of the six lock results
   (`e2e_prbs_tt125_cpbias.log`, `e2e_prbs_ff125_cpbias.log`,
   `e2e_prbs_ttm40_seed080.log`) predate the ripple fixes and ran with ~2x the pump
   current (749-890 nA, EXPERIMENTS 2.9). Scored against *their own* pump they would sit
   at `Phi` = 4.4e-3, 1.2e-2 and 1.5e-2 — and all three locked, which pushes the upper
   bracket on `Phi_crit` from 1.58e-2 to ">= 1.5e-2" and leaves ff/-40 C's 1.58e-2 with
   essentially no margin. **`Phi` orders the corners of one fixed design correctly; it is
   not calibrated across changes to `I_pump`.** The full `Psi` does not have this problem
   in principle, because halving `I_pump` doubles `D` and `Psi` is invariant — but `Psi`
   cannot be evaluated on those three runs.
4. **The ss corners' `K_vco`.** `vco_ct_seed_ss*` are trim-*off* ring sweeps, while both
   closed-loop ss runs have the coarse trim engaged (vcoarse 0.288 at ss/-40 C, fully on
   at ss/125 C). The `K_vco` used for the two ss rows is therefore a proxy, and both ss
   rows sit comfortably inside the locking band, so the conclusion does not turn on them —
   but their exact `Phi` should not be quoted.

**What the model cannot support at all**, and should not be asked to:

- Any statement about a corner's drift that is not tt/125 C or ff/-40 C. `pd_phase` is
  a ~40 min measurement per corner; four of the six have never had it.
- Any process dependence of `I_pump`, because `cp_ibias_check.log` has none.
- Any absolute prediction of `Phi_crit` or `Psi_crit`. Both are bracketed by outcomes,
  not derived. A model that brackets a threshold by a factor of 2 (`Phi`) or 51 (`Psi`)
  can rank corners; it cannot certify a new one.
- Anything about jitter, BER or tracking once locked. This is a capture model only.

---

## 5. What `K_vco` at ff/-40 C would be enough (answers Q4)

At ff/-40 C, `dV_step = I_pump * R = 440.5 nA * 17452.9 = 7.688 mV`, so

```
Phi(ff/-40C) = K_vco[Hz/V] * 1.2801e-11
```

| K_vco MHz/V | Phi (1e-3) | verdict against the bracket |
|---|---|---|
| 1234 (today, `loop_scurve_ffm40.log`) | 15.79 | fails, as observed |
| **879 (after Rload 10k -> 11k)** | **11.25** | **still above every corner that locks** |
| 782 | 10.01 | at the middle of the bracket |
| 598 | 7.66 | equal to tt/-40 C, the worst corner that does lock |
| 436 | 5.58 | equal to tt/27 C, a comfortable locker |

**879 MHz/V is not enough.** It is 1.47x better than today, but it lands at 1.13e-2 —
above the worst corner ever observed to lock (7.66e-3) and only 1.40x below the value
that fails. It sits inside the bracket where the model cannot call the result, with no
margin at all, and the bracket's upper edge moves up to >= 1.5e-2 once §4.3 is taken into
account.

**What is needed:** `K_vco <= ~600 MHz/V` to be no worse than the worst corner that
locks, and `<= ~440 MHz/V` for the margin tt/27 C has. The ring re-sizing delivers about
half of the first target.

Since `Phi = K_vco * I_pump * R * T_b`, the same result is reachable without further ring
work. At `K_vco` = 879 MHz/V, `Phi <= 7.66e-3` needs `I_pump * R <= 5.23 mV`, a 32 % cut
from 7.69 mV — i.e. **pump 440 -> 300 nA at R = 17.45 k, or R 17.45 k -> 11.9 k at
440 nA**. Note the pump cut costs acquisition time in proportion (§6) and the second
option requires a resistor whose -40 C value is what 125 C gives today.

**The caveat that matters more than the number.** `Phi` is only one factor of `Psi`.
`D = 17.5 %` at ff/-40 C against 2.45 % at tt/125 C, and no change to `K_vco` touches `D`.
If `Psi_crit` is anywhere near tt/125 C's 5.4e-5, closing the 52x gap on `K_vco` alone
would need `K_vco` ~ 24 MHz/V, which is not a circuit. The evidence brackets `Psi_crit`
too loosely to say which of these is binding, but the conservative reading is:
**re-sizing the ring buys margin, it does not by itself make ff/-40 C lock. The
phase-average asymmetry `I_avg` has to come down as well.** The two knobs measured so
far both fall short — the pump-bias trim gives about -10 nA per 0.15 um of XMP2 and would
need ~2.45 um to reach tt/125 C's +10 nA (`pd_trim_ffm40.log`: +77.1 nA at 1.45 um,
+66.7 nA at 1.60 um; the 1.75 um row in that log has only 9 of 10 phases and its average
must not be used), and current steering was measured worse (EXPERIMENTS 2.14).

---

## 6. Sanity check: ss/125 C/1.08 V (answers Q5)

Measured (`run_dual_ss125_108.out`, `e2e_dual_ss125_108.log`): `f_long` = 560.025 MHz
(-6.76 %), vctrl 0.5800 -> 0.5879 V across windows 600 ns apart, ripple 10.1 mV, coarse
trim already driven fully on. The run is 2.5 us.

The model's two verdicts are separate, and that is the point of the check:

1. **Capture:** `Phi` = 2.99e-3, third-lowest of the seven corners, well inside the
   locking band. The model says this corner is *not* capture-limited.
2. **Acquisition time:** its drift is +13.23 mV/us (D), i.e. `I_avg` = +17.3 nA into
   1308 fF — and unlike ff/-40 C the drift points *toward* the lock point (the ring is
   too slow, rising vctrl makes it faster). The time to arrive is a ramp, not a capture
   problem:

```
t_acq = (delta_f / K_vco_eff) / (dV/dt)     delta_f = 600.60 - 560.02 = 40.58 MHz
```

| K_vco_eff MHz/V | vctrl to cover | t_acq |
|---|---|---|
| 358 (`vco_ct_seed_ss125_108.log` slope at 0.55-0.60, trim off) | 113 mV | 8.6 us |
| 159 (same log, slope at 0.60-0.65) | 255 mV | 19.3 us |
| ~100 (extrapolated into the flat top) | 406 mV | 30.7 us |

The correct number is at the low-`K_vco` end: `ring_bracket.out` puts this corner's fast
end at **618.1 MHz** with the trim fully on, so at 560 MHz the ring is already at 91 % of
its ceiling and sitting on the flat part of the curve. **The model predicts 19-31 us, and
predicts non-lock in a 2.5 us window** — which is what happened, and it agrees with the
~30 us estimated independently in EXPERIMENTS 2.16. The check passes: the model separates
"cannot capture" (ff/-40 C) from "has not yet arrived" (ss/125 C), which are the two
failures that look identical from outside.

A testable consequence: the planned re-run seeded at 0.85 V moves vctrl +264 mV from
0.586, which covers the 255 mV case but not the 406 mV one. **If the effective `K_vco`
near the ceiling is at the low end, a 0.85 V seed will still fall short and a ~0.95-1.00 V
seed is needed.** That is a prediction this note makes and does not verify.

---

## 7. Summary

```
capture window        df_cap  = K_vco * I_pump * R                      [Hz]
drift                 df/dt   = K_vco * I_avg / C                       [Hz/s]
time available        t_avail = I_pump * R * C / I_avg                  [s]   -- K_vco cancels
condition (measurable) Phi    = K_vco * I_pump * R * T_b   <  ~1e-2 UI/decision
condition (complete)   Psi    = Phi * I_avg / I_pump       <  Psi_crit in (5.4e-5, 2.8e-3)
```

- `Phi` separates all six measured corners: every locker <= 7.7e-3, ff/-40 C alone at 1.58e-2.
- **879 MHz/V is not enough.** It gives `Phi` = 1.13e-2, still above every corner that locks.
- **~600 MHz/V** matches the worst corner that locks; **~440 MHz/V** matches tt/27 C.
- Reducing `K_vco` alone does not touch `D` = 17.5 %, and if `Psi_crit` sits near the
  locking corners' value it is `D`, not `K_vco`, that is binding.
