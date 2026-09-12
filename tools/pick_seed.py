#!/usr/bin/env python3
"""Read sim/results/ring_seed.log and report, per ring, the vctrl that puts it
at the baud rate.

    tools/pick_seed.py                 # table
    tools/pick_seed.py 0.7 9000        # just that one, bare number, for scripts

A closed-loop deck seeded anywhere but its own ring's lock point starts the
ring out of band, and a bang-bang detector has no frequency acquisition -- so
the run measures the seed, not the circuit.  That has already cost one run
(docs/HANDBOOK.md section 11) and inflated another's error from 11 % to 23 %.
"""
import re
import sys
from pathlib import Path

LOG = Path(__file__).resolve().parent.parent / "sim" / "results" / "ring_seed.log"
BAUD = 600.60


def parse(text):
    cfgs, cur = {}, None
    pend = {}
    for line in text.splitlines():
        m = re.search(r"CONFIG Lin=([0-9.]+) Rload=(\d+)", line)
        if m:
            cur = (float(m.group(1)), int(m.group(2)))
            cfgs[cur] = []
            pend = {}
            continue
        m = re.match(r"^(p_vctrl|fosc|swing) = ([-+0-9.eE]+)", line)
        if m and cur:
            pend[m.group(1)] = float(m.group(2))
            if len(pend) == 3:
                cfgs[cur].append((pend["p_vctrl"], pend["fosc"] / 1e6, pend["swing"]))
                pend = {}
    return cfgs


def seed_for(pts, f=BAUD):
    """Linear interpolation onto the baud rate, using only usable points.

    'Usable' is ring-node swing above 0.15 V single-ended -- the 300 mV
    differential threshold used everywhere else in this project.  A meas on a
    barely-moving node still returns a number (trap 2.14), and interpolating
    through one of those invents a lock point that is not there.
    """
    good = [(v, fr) for v, fr, sw in pts if sw >= 0.15]
    good.sort()
    for (v1, f1), (v2, f2) in zip(good, good[1:]):
        if min(f1, f2) <= f <= max(f1, f2):
            return v1 + (f - f1) * (v2 - v1) / (f2 - f1), (f2 - f1) / (v2 - v1)
    return None, None


def main():
    if not LOG.exists():
        sys.exit(f"{LOG} missing -- run sim/decks/ring_seed.spice first")
    cfgs = parse(LOG.read_text())
    if len(cfgs) > 1 and len({tuple(v) for v in cfgs.values()}) == 1:
        sys.exit("every configuration returned the SAME curve -- the sweep did "
                 "not actually sweep (trap 2.21).  Refusing to report seeds.")
    if len(sys.argv) == 3:
        key = (float(sys.argv[1]), int(sys.argv[2]))
        v, _ = seed_for(cfgs.get(key, []))
        print(f"{v:.3f}" if v else "")
        return 0
    print(f"{'Lin':>5} {'Rload':>7} {'seed V':>8} {'Kvco MHz/V':>11}   usable range")
    for (lin, rl), pts in sorted(cfgs.items()):
        v, k = seed_for(pts)
        good = [(a, b) for a, b, sw in pts if sw >= 0.15]
        rng = f"{min(b for _, b in good):.0f}-{max(b for _, b in good):.0f} MHz" if good else "none"
        print(f"{lin:>5} {rl:>7} {v:>8.3f} {k:>11.0f}   {rng}"
              if v else f"{lin:>5} {rl:>7} {'--':>8} {'--':>11}   {rng}  (baud not reachable)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
