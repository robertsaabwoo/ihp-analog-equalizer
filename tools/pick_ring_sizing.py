#!/usr/bin/env python3
"""Pick (Rload, Wtr) for the ring from the ring_centre2 sweeps, by rule.

    tools/pick_ring_sizing.py [ff-log] [ss-log]

The rule, in order:
  1. At ff/-40 C/1.32 V the baud rate must be reachable with the trim OFF, at a vctrl
     inside the swept range and with usable swing -- that is what stops the fine loop
     being dragged to the steep bottom of the tuning curve.
  2. At ss/125 C/1.08 V it must still be reachable with the trim ON, with usable swing,
     by at least MARGIN_MIN MHz.  Without a floor here the rule picks 12 k/4 um, whose
     margin is +0.1 MHz -- no margin at all (2026-09-17).
     This is the binding constraint: the trim is the only thing that can speed the ring
     up there, and a wide trim stops it oscillating (docs/EXPERIMENTS.md 2.12).
  3. Among survivors, prefer the gentlest slope at the ff/-40 C crossing: the loop's
     ripple times that slope is the frequency wobble it has to live with (2.8, 1.2).
Prints every candidate with its numbers, then the winner.  Measurement only -- it changes
nothing.
"""
import re
import sys
from pathlib import Path

BAUD = 600.6
SWING_MIN = 0.15
MARGIN_MIN = 8.0  # MHz at ss/125 C/1.08 V, ~1.3 %: below this there is nothing to trim with
NUM = r'(-?\d\.\d+e[-+]\d{2})'
KEYS = ('p_rl', 'p_wt', 'p_trim', 'p_vc', 'f_mhz', 'swing')
ROOT = Path(__file__).resolve().parent.parent


def rows(path):
    pat = re.compile(r'^(' + '|'.join(KEYS) + r') = ' + NUM + r'\s*$', re.I)
    out, cur = [], {}
    for line in open(path):
        m = pat.match(line.strip())
        if m:
            cur[m.group(1).lower()] = float(m.group(2))
        elif line.startswith('ROWEND'):
            if len(cur) == len(KEYS):
                out.append(cur)
            cur = {}
    return out


def crossing(pts):
    """(vctrl, slope MHz/V) where a monotone f(vctrl) list crosses BAUD, else None."""
    pts = sorted(pts)
    for (v1, f1), (v2, f2) in zip(pts, pts[1:]):
        if min(f1, f2) <= BAUD <= max(f1, f2) and f2 != f1:
            return v1 + (BAUD - f1) * (v2 - v1) / (f2 - f1), (f2 - f1) / (v2 - v1)
    return None


def main():
    ff = sys.argv[1] if len(sys.argv) > 1 else ROOT / 'sim/results/ring_centre2_ffm40.log'
    ss = sys.argv[2] if len(sys.argv) > 2 else ROOT / 'sim/results/ring_centre2_ss125.log'
    for f in (ff, ss):
        if not Path(f).exists():
            print(f"missing {f}")
            return 1
    rf, rs = rows(ff), rows(ss)
    if not rf or not rs:
        print(f"no parsable rows (ff {len(rf)}, ss {len(rs)})")
        return 1
    sizings = sorted({(r['p_rl'], r['p_wt']) for r in rf} & {(r['p_rl'], r['p_wt']) for r in rs})
    print(f"{'Rload':>6} {'Wtr':>4} | ff/-40C trim OFF: vctrl@baud  slope | ss/125C trim ON: max f  margin | verdict")
    best = None
    for rl, wt in sizings:
        # 1. ff/-40 C, trim off (the higher vcoarse value in the sweep)
        off = [r for r in rf if (r['p_rl'], r['p_wt']) == (rl, wt) and r['p_trim'] > 0.5
               and r['swing'] >= SWING_MIN]
        cross = crossing([(r['p_vc'], r['f_mhz']) for r in off])
        # 2. ss/125 C, trim on (vcoarse = 0)
        on = [r for r in rs if (r['p_rl'], r['p_wt']) == (rl, wt) and r['p_trim'] < 0.5
              and r['swing'] >= SWING_MIN]
        fmax = max((r['f_mhz'] for r in on), default=float('nan'))
        margin = fmax - BAUD
        ok = cross is not None and margin >= MARGIN_MIN
        note = []
        if cross is None:
            note.append('baud not reachable with trim off at ff/-40C')
        if not (margin >= MARGIN_MIN):
            note.append(f'slow-corner margin {margin:+.1f} MHz < {MARGIN_MIN:.0f} MHz floor')
        verdict = 'OK' if ok else '; '.join(note)
        cs = f"{cross[0]:9.3f} {cross[1]:7.0f}" if cross else f"{'-':>9} {'-':>7}"
        print(f"{rl:6.0f} {wt:4.0f} | {cs} | {fmax:9.1f} {margin:+8.1f} | {verdict}")
        if ok and (best is None or cross[1] < best[2][1]):
            best = ((rl, wt), margin, cross)
    print()
    if best is None:
        print("NO CANDIDATE satisfies both extremes in this grid -- widen the grid or")
        print("reconsider the approach (docs/EXPERIMENTS.md 2.12).")
        return 2
    (rl, wt), margin, cross = best
    print(f"CHOSEN: Rload {rl:.0f} ohm, Wtr {wt:.0f} um")
    print(f"  ff/-40C: baud at vctrl {cross[0]:.3f} V with the trim OFF, slope {cross[1]:.0f} MHz/V")
    print(f"           (today's 10000/4: 1200 MHz/V at vctrl ~0.546 -- loop_scurve_ffm40.log)")
    print(f"  ss/125C: trim ON reaches {cross and margin + BAUD:.1f} MHz, margin {margin:+.1f} MHz")
    return 0


if __name__ == '__main__':
    sys.exit(main())
