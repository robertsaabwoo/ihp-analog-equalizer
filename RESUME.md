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

Current suspicion, **untested**: the bias generator. Its two diode currents set
up and down separately and their ratio may drift with VDD at ff.
`cp_mismatch_pvt2.spice` prints the currents and `bias_n`/`bias_p` to test it.

The DC percentage is a proxy. Ground truth is closed-loop PRBS7 at
ff / 125 °C / 1.32 V: `sim/runners/prbs_ff125.sh` (seeds itself first).

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
