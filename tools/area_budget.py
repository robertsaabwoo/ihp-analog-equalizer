#!/usr/bin/env python3
"""Flatten the design and report device count and drawn device area.

    tools/area_budget.py [sim/netlists/blocks.inc] [top]

Area here is *drawn device* area -- gate area for transistors, the resistor
body, the capacitor plate -- not layout area. Real layout is several times
this once wells, spacing, contacts and routing are counted. It is useful for
two things: knowing whether a block is dominated by one component (this one is
-- the CTLE's degeneration capacitor is 40 % of the total), and sanity-checking
against a slot budget before drawing anything.

Pure stdlib.
"""
import re
import sys
from collections import Counter
from pathlib import Path

CMOMF_DENSITY = 1.287e-15  # F/um^2, measured in char/caps.spice


def parse(path):
    """Return {subckt: [(model, params)]} plus instance lists."""
    text = re.sub(r"\n\+\s*", " ", Path(path).read_text())
    subs, cur = {}, None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        low = line.lower()
        if low.startswith(".subckt"):
            cur = line.split()[1]
            subs[cur] = []
            continue
        if low.startswith(".ends"):
            cur = None
            continue
        if cur is None or line[0] not in "xX":
            continue
        toks = line.split()
        params = {}
        model = None
        for t in toks[1:]:
            if "=" in t:
                k, v = t.split("=", 1)
                params[k] = v
            elif not t.startswith("sub!"):
                model = t
        subs[cur].append((model, params))
    return subs


def flatten(subs, top, counts, area, depth=0):
    if depth > 20:
        raise RuntimeError("hierarchy too deep -- recursive subcircuit?")
    for model, params in subs.get(top, []):
        if model in subs:
            flatten(subs, model, counts, area, depth + 1)
            continue
        counts[model] += 1
        try:
            if model in ("sg13_lv_nmos", "sg13_lv_pmos"):
                w = float(params["w"].rstrip("u")) * (1e-6 if params["w"].endswith("u") else 1)
                length = float(params["l"].rstrip("u")) * (1e-6 if params["l"].endswith("u") else 1)
                area[model] += w * length * 1e12 * int(float(params.get("m", 1)))
            elif model == "rhigh":
                w, length = float(params["w"]), float(params["l"])
                area[model] += w * length * 1e12 * int(float(params.get("m", 1)))
            elif model == "cap_cmomf":
                w, length = float(params["w"]), float(params["l"])
                area[model] += w * length * 1e12 * int(float(params.get("m", 1)))
        except (KeyError, ValueError):
            pass


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "sim/netlists/blocks.inc"
    top = sys.argv[2] if len(sys.argv) > 2 else "ctle_cdr_rx"
    subs = parse(path)
    if top not in subs:
        print(f"no subcircuit '{top}' in {path}; have: {sorted(subs)}")
        return 2
    counts, area = Counter(), Counter()
    flatten(subs, top, counts, area)

    print(f"{top} flattened\n")
    print(f"{'device':<16}{'count':>7}{'drawn area /um2':>18}")
    for model in sorted(counts):
        print(f"{model:<16}{counts[model]:>7}{area[model]:>18.1f}")
    print(f"{'total':<16}{sum(counts.values()):>7}{sum(area.values()):>18.1f}")

    if area.get("cap_cmomf"):
        c = area["cap_cmomf"] * CMOMF_DENSITY * 1e15
        share = 100 * area["cap_cmomf"] / sum(area.values())
        print(f"\ncap_cmomf: {c:.0f} fF over {area['cap_cmomf']:.0f} um2 "
              f"({share:.0f} % of drawn device area).")
        print("SG13CMOS5L has no MIM, so the CTLE's degeneration capacitor is")
        print("the largest single object in the design.  See docs/PORTING.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
