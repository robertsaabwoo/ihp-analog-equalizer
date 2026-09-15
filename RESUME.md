# Resume here

Written mid-run as the machine was powering off. Session
`ring-coarse-tune`, all work pushed.

## One-line state

`main` locks and is untouched (600.614 MHz on 0101, 600.581 on PRBS7, 8 of 27
ring corners). The branch has a ring that **locks on 0101 and fails PRBS7**,
and a coarse loop that has never been tested closed-loop on a configuration
that locks.

## The story, shortest form

Re-sizing the ring for corner coverage (0.9 → 0.7 µm pair, 7355 → 9000 Ω)
broke the lock. Six hypotheses were wrong — precharge, `diff_amp_inv`, charge
pump bias, loop gain, pump current, ceiling at 12000 Ω — and two of those were
my own measurement errors, not circuit faults.

The cause is **where the baud rate sits relative to the ring's ceiling**:

| Rload | ceiling | baud/ceiling | Kvco | 0101 | PRBS7 |
|---|---|---|---|---|---|
| 9000 | 681.3 | 88 % | 844 | no | — |
| **10000** | 639.9 | 94 % | 720 | **600.660 MHz ✓** | **609.96 MHz ✗** |
| 10500 | 621.5 | 97 % | 302 | **612.19 MHz ✗** (+1.93 %) | not run — pointless |
| 11000 | 604.4 | 99 % | 27 | no headroom | — |
| main 0.9/7355 | 632.9 | 95 % | 522 | 600.614 ✓ | 600.581 ✓ |

Past the knee the loop has margin against the pump's 11 % current mismatch; on
the steep rise a 40 mV startup kick is a 50 MHz error, outside the bang-bang
capture range.

## Pick up here (updated 2026-09-15, later)

**10000 Ω + charge-pump up-source trimmed 2.0 → 1.8 µm locks on both patterns
at tt / 27 °C / 1.2 V** — the first branch configuration to do so:

| | 0101 | PRBS7 |
|---|---|---|
| main 0.9 µm / 7355 Ω | 600.614 MHz ✓ | 600.581 MHz ✓ |
| branch 10000 Ω, pump 2.0 µm | 600.660 ✓ | 609.96 ✗ |
| **branch 10000 Ω, pump 1.8 µm** | **600.554 ✓** | **600.541 ✓** |

(`sim/results/e2e_lock_pump18.log`, `e2e_prbs_pump18.log`)

**The trim does NOT hold across corners at DC.** `cp_mismatch_pvt.spice`,
mismatch % with the 1.8 µm trim, `vout` at ~VDD/2 (where the coarse loop's
window centres `vctrl`):

| | 1.08 V | 1.20 V | 1.32 V |
|---|---|---|---|
| tt −40 °C | +2.2 | +2.9 | +6.6 |
| tt 27 °C | +1.1 | +2.1 | +11.6 |
| tt 125 °C | +3.4 | +15.1 | **+35.3** |
| ss (all temps) | −2.3 … −1.1 | −1.3 … +1.3 | +3.5 … +6.7 |
| ff −40 °C | +5.7 | +11.2 | **+39.7** |
| ff 27 °C | +9.8 | +29.7 | **+57.9** |
| ff 125 °C | +33.7 | +53.2 | **+71.7** |

Two explanations were tried and are **retracted**:

1. *Channel-length modulation at the pump sources.* It would make mismatch depend
   strongly on `vout`. At ff it barely does (76 → 72 % over 0.50 → 0.70 V) while
   depending enormously on supply (+6 → +49 % at −40 °C, 1.08 → 1.32 V).
2. *VDD tracking symmetrises it.* Reading at `vout` = VDD/2 instead of a fixed
   0.60 V changes the numbers by a few points, not the picture.

**Mechanism confirmed: the bias generator** (`cp_mismatch_pvt2.spice`,
currents and bias nodes, 1.8 µm trim, `vout` = 0.60 V):

| corner | up nA | down nA | mis % | bias_n | VDD − bias_p |
|---|---|---|---|---|---|
| tt −40 °C 1.08 V | 457 | 479 | −4.7 | 0.307 | 0.428 |
| tt −40 °C 1.32 V | 630 | 571 | +9.8 | 0.314 | 0.442 |
| tt 125 °C 1.08 V | 1279 | 1295 | −1.2 | 0.255 | 0.411 |
| tt 125 °C 1.20 V | 1862 | 1601 | +15.1 | 0.273 | 0.447 |
| tt 125 °C 1.32 V | **3137** | **2142** | **+37.7** | 0.299 | **0.507** |

At 125 °C the pMOS bias `VDD − bias_p` grows with supply; at −40 °C it is flat;
`bias_n` barely moves anywhere. The up path loses regulation hot and high, the
down path does not. And a second problem the percentages hid: **total pump
current is ~4× nominal at tt/125 °C/1.32 V**, a 4× loop-gain swing across
corners, independent of mismatch.

**Lengthening the bias generator makes it worse** — retracted as a fix
(`bg_lsweep.spice`, all 27 corners, Wp 1.8 µm):

| Lb | worst mismatch | pump current across corners | spread |
|---|---|---|---|
| 1 µm | +73.8 % | 398 … 5684 nA | 14.3× |
| 2 µm | +77.5 % | 401 … 6224 nA | 15.5× |
| 4 µm | +81.4 % | 392 … 6856 nA | 17.5× |

So channel-length modulation in its mirrors is not the mechanism either. The
underlying problem is the reference itself: a **14× spread in pump current**
across corners. Candidate direction, not yet tried: derive the pump current from
the harness's bandgap-referenced `ibias` (already feeding the CTLE) instead of the
self-biased `tiny_pll_bias_gen` — the same lesson as the port's bias fix,
HANDBOOK §6.1. Before redesigning, the cause is being tested: the failing
ff/125 °C PRBS7 run repeated with ideal nominal pump bias
(`e2e_prbs_ff125_idealbias.spice`).

At ff it is worse — `cp_mismatch_pvt2.spice`, ff, trimmed pump, `vout` 0.60 V:
**7782 nA up vs 3586 nA down at 125 °C / 1.32 V**, about 10× nominal up
current, `VDD − bias_p` = 0.594 V.

**Ground truth at the worst corner: FAIL — but possibly not a circuit death (see below).** Closed-loop
PRBS7 at ff / 125 °C / 1.32 V, trim off, seeded at that corner's lock point
(0.489 V) (`sim/results/e2e_prbs_ff125.log`):
- recovered clock swing **49 nV** — the ring stopped
- `vctrl` walked **down** 0.373 → 0.338 → 0.303 V, below the ring's oscillation
  floor at that corner (swing 0.235 V at 0.325, none at 0.300)
- CTLE output 361 mV, so the data path is fine; it is the loop

**Cause test: the pump reference is NOT the cause.** The same run with
`tiny_pll_bias_gen` replaced by ideal nominal currents
(`e2e_prbs_ff125_idealbias.spice`; the log confirms the override took) fails
**identically to four digits**:

| | `vctrl` s1 | s2 | s3 | clock |
|---|---|---|---|---|
| self-biased pump | 0.3725 | 0.3381 | 0.3032 | 49 nV |
| ideal pump bias | 0.3722 | 0.3376 | 0.3026 | 49 nV |

If the pump were acting, cutting its current from ~7.8 µA to 0.8 µA would change
the drift. It does not move at all — so the phase detector and pump are not
participating, and `vctrl` is decaying on its own. That is the signature of a
ring that **never started** at this corner. The standalone seed sweep shows the
ring *can* oscillate there (0.91 V swing at `vctrl` 0.475–0.500 V), so this may
be a full-chip startup failure, possibly a testbench artefact of the kind found
in bring-up (HANDBOOK §6.2), rather than the receiver dying. **Unresolved**; an
early-time diagnostic is running, and `main` at the same corner will show
whether the same signature appears there.

The pump reference's 14× current spread across corners is still real and still
a problem for loop gain — it just is not what stops this run.

**So the branch holds both patterns at tt only; at ff / 125 °C / 1.32 V it
fails, cause unresolved.** `main` has not been tested closed-loop at that corner
either, so this is not yet a comparison against a known-good.

**The coarse loop, closed-loop, on this configuration** (`sim/runners/dualloop.sh`):

| run | start | recovered | error | `vctrl` | `vcoarse` |
|---|---|---|---|---|---|
| `e2e_dual` | trim off, 1.20 V | 600.661 MHz | +0.010 % | 0.6007 → 0.6013 | 1.20 → 0.914 V |
| `e2e_dual_walk` | trim on, 0.55 V | 600.724 MHz | +0.021 % | 0.5747 → 0.5739 | −8 mV |

Established: with both loops closed the receiver locks from both starting
points, and the coarse loop does not disturb the fine loop.

**Not established: the handover itself.** Near the null the coarse loop moves
~0.5 mV/µs, so a 2.5 µs run shows ~1 mV of walk — the deck's expectation of
47 mV used the railed search rate. Observing it needs the loop sped up
(`Ksweep`), and the generated schematic bakes widths as literals, so that means
overriding the subckt in a deck — being checked.

Unexpected, two items:
- `e2e_dual_walk` locked with the baud rate at 91 % of the ceiling (Kvco
  1005 MHz/V), where the untrimmed pump did not. Suggests pump mismatch was part
  of the steep-side failure all along. A lead only.
- `e2e_dual`'s `vcoarse` fell 286 mV with `vctrl` at the null. Harmless above
  ~0.8 V (trim off), cause not yet known.

## In flight at last checkpoint (2026-09-15)

Five jobs, serialised on the ngspice lock. If the machine went down, rerun the
ones without results, in this order:

| what | how to rerun | answers |
|---|---|---|
| branch PRBS7 at ff/125 °C/1.32 V, **ideal pump bias** | `cd sim/decks && ../../tools/safe_ngspice.sh e2e_prbs_ff125_idealbias.spice ../results/e2e_prbs_ff125_idealbias.log 2500 5400 2000` | is the pump's reference the cause of the ff/125 °C death? Log must contain `redefinition of .subckt tiny_pll_bias_gen, ignored` or the result is void |
| slow-end floor at ff/125 °C with `vcoarse` at 1.32/0.90/0.85/0.80 V | `cd sim/decks && ../../tools/safe_ngspice.sh vco_ct_floor_clamp.spice ../results/vco_ct_floor_clamp.log 2500 2400 2000` | does the top-rail clamp cost the slow-end margin? |
| folded pull-up: top-rail sink | `cd sim/decks && ../../tools/safe_ngspice.sh coarse_clamp_fold.spice ../results/coarse_clamp_fold.log 1500 600 2000` | does folding remove the sink above ~0.85 V? |
| folded pull-up: null/search/span | `cd sim/decks && ../../tools/safe_ngspice.sh coarse_tb_fold.spice ../results/coarse_tb_fold.log 2000 1800 2000` | does the fix keep the null at 0.600 V and the 19.6 mV/µs search? |
| **main** PRBS7 at ff/125 °C/1.32 V | `sim/runners/main_prbs_ff125.sh` (self-seeding; writes nothing into main) | is the corner death inherited from main, or introduced by the branch? |

The folded pull-up lives in `sim/decks/coarse_loop_fold.inc` (subckt
`coarse_loop_fold`) and is **not** in the design record.

## Before trusting anything after the reboot

The runner scripts edit `tools/port_from_sky130.py` in place and restore it at
the end. One was interrupted, so:

```bash
git -C /home/ttuser/ssh_analog/ct-worktree diff tools/port_from_sky130.py
git -C /home/ttuser/ssh_analog/ct-worktree status --short
python3 -m pytest test -q
tools/netlist.sh           # blocks.inc may be mid-edit
```

`git checkout -- tools/port_from_sky130.py` returns the design record to
10500 Ω, which is what the last commit intends.

## Not affected by any of this

`main` at `/home/ttuser/ssh_analog/ihp-analog-equalizer` — clean, locking, and
the thing to lay out. `docs/LAYOUT.md` and `mag/` are ready and design
independent; `docs/CHIPALOOZA_SLOT.md` has slot 2 and the pin budget.
