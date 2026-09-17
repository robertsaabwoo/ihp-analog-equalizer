#!/usr/bin/env python3
"""Pick the charge pump's switch width and up-inverter ratio from cp_charge logs.

    tools/pick_pump_sizing.py [tt-log ss-log ff-log]

An up decision and a down decision must deliver equal and opposite charge, or an unlocked
loop integrates the difference and drifts -- measured as +77 nA of phase-average at
ff/-40 C against +10 nA at tt/125 C (docs/EXPERIMENTS.md 2.10).  cp_charge.spice fires one
up pulse and one down pulse into a held output and integrates each, pump alone.

Figure of merit: the WORST |q_up + q_dn| over all 27 corners, because the loop has to work
at all of them.  Mean net is printed too: a large mean with a small worst is a systematic
offset (trimmable), the reverse is corner spread (not).
Measurement only -- changes nothing.
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

NUM = r'(-?\d\.\d+e[-+]\d{2})'
KEYS = ('p_wn', 'p_ivp', 'p_temp', 'p_vdd', 'q_up_fc', 'q_dn_fc')
ROOT = Path(__file__).resolve().parent.parent


def rows(paths):
    pat = re.compile(r'^(' + '|'.join(KEYS) + r') = ' + NUM + r'\s*$', re.I)
    out = []
    for p in paths:
        if not Path(p).exists():
            continue
        cur = {}
        for line in open(p):
            m = pat.match(line.strip())
            if m:
                cur[m.group(1).lower()] = float(m.group(2))
            elif line.startswith('ROWEND'):
                if len(cur) == len(KEYS):
                    cur['corner'] = Path(p).stem.split('_')[-1]
                    out.append(cur)
                cur = {}
    return out


def main():
    logs = sys.argv[1:] or [ROOT / f'sim/results/cp_charge_{c}.log' for c in ('tt', 'ss', 'ff')]
    rs = rows(logs)
    if not rs:
        print("no parsable rows")
        return 1
    by = defaultdict(list)
    for r in rs:
        by[(r['p_wn'], r['p_ivp'])].append(r)
    print(f"parsed {len(rs)} rows, {len(by)} sizings\n")
    print(f"{'Wnsw':>5} {'invP':>5} | {'worst |net|':>11} {'mean net':>9} {'q_up':>8} {'q_dn':>8} | worst corner")
    best = None
    for k in sorted(by):
        v = by[k]
        nets = [r['q_up_fc'] + r['q_dn_fc'] for r in v]
        worst_i = max(range(len(nets)), key=lambda i: abs(nets[i]))
        w = v[worst_i]
        worst = abs(nets[worst_i])
        mean = sum(nets) / len(nets)
        print(f"{k[0]:5.2f} {k[1]:5.2f} | {worst:11.2f} {mean:+9.2f} "
              f"{w['q_up_fc']:8.2f} {w['q_dn_fc']:8.2f} | "
              f"{w['corner']} {w['p_temp']:.0f}C {w['p_vdd']:.2f}V  (n={len(v)})")
        if best is None or worst < best[1]:
            best = (k, worst, mean)
    (wn, ivp), worst, mean = best
    asbuilt = by.get((0.5, 2.0))
    print()
    if asbuilt:
        nets = [r['q_up_fc'] + r['q_dn_fc'] for r in asbuilt]
        print(f"as built (Wnsw 0.50, invP 2.00): worst |net| {max(abs(x) for x in nets):.2f} fC, "
              f"mean {sum(nets)/len(nets):+.2f} fC")
    print(f"CHOSEN: Wnsw {wn:.2f} um, up-inverter pMOS {ivp:.2f} um "
          f"-> worst |net| {worst:.2f} fC, mean {mean:+.2f} fC")
    print("Sanity check before adopting: a net charge of q fC per decision pair at the baud")
    print("rate is q*600.6e6 nA of average current if every UI carries a decision --")
    print("compare against the +77 nA that runs ff/-40 C away (2.10).")
    return 0


if __name__ == '__main__':
    sys.exit(main())
