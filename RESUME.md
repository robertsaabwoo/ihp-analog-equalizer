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
| 10500 | 621.5 | 97 % | **302** | *running* | *running* |
| 11000 | 604.4 | 99 % | 27 | no headroom | — |
| main 0.9/7355 | 632.9 | 95 % | 522 | 600.614 ✓ | 600.581 ✓ |

Past the knee the loop has margin against the pump's 11 % current mismatch; on
the steep rise a 40 mV startup kick is a 50 MHz error, outside the bang-bang
capture range.

## Pick up here

1. **Re-run 10500 Ω, both patterns** — it was in flight and is the current best
   hope, because its Kvco of 302 MHz/V is *lower than main's* 522, so it should
   be more PRBS7-robust than the design that works today.
   ```bash
   cd /home/ttuser/ssh_analog/ct-worktree && sim/runners/r105.sh
   ```
2. If PRBS7 locks at 10500 Ω, **re-measure the 27 corners** (`sim/run_corners.sh
   vco_ct_pvt.spice vco_ctpvt`). Expect ~+3.2 % at the worst fast corner instead
   of the +6.3 % measured at 10000 Ω.
3. If PRBS7 does not lock at 10500 Ω either, the remaining lever is the charge
   pump's **11 % up/down mismatch** itself — that is what integrates during
   PRBS7's seven-bit blind runs. Nothing has been tried there yet.
4. Still never done on any locking configuration: **the coarse loop closed-loop**
   (`e2e_dual.spice`, `e2e_dual_walk.spice`).

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
