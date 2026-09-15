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

## Pick up here (updated 2026-09-15)

10500 Ω **failed even on 0101** (612.19 MHz, `vctrl` walked to 0.792) — only
3 % of headroom under its ceiling. Dead end.

The live test is **10000 Ω + the charge pump's up-source trimmed 2.0 → 1.8 µm**
(`sim/runners/pump18.sh`, both patterns). PRBS7 failed at 10000 Ω because its
seven-bit blind runs let the pump mismatch integrate; `cp_mismatch.spice`
measured that mismatch moving with `vctrl` and showed 1.8 µm nulls it at the
lock point:

| Wp | @0.60 V | @0.65 V |
|---|---|---|
| 2.0 (was) | 11.7 % | 9.5 % |
| **1.8** | **2.1 %** | **−0.1 %** |

Results land in `sim/results/run_pump18.out`. If PRBS7 locks: re-measure the 27
corners, then the coarse loop closed-loop (`e2e_dual.spice`), which has still
never run on a locking configuration. If it does not: the mismatch was
measured at tt only and at one bias; check it at the PRBS7 run's actual `vctrl`.

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
