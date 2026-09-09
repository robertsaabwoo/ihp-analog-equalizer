#!/usr/bin/env python3
"""Check that the IHP port is the same circuit as the sky130 original.

A device-for-device port is exactly the kind of change that looks right and
is wrong: xschem connects by coordinate, so a symbol whose pins sit a grid
step away from the old one rewires the schematic and still netlists cleanly.
The only way to know the port did not move a connection is to compare the two
netlists as graphs.

What is compared
----------------
For every subcircuit: the pin list, the set of instances, and for each
instance the net attached to each *named terminal* -- drain, gate, source,
bulk, the two ends of a resistor, the two plates of a capacitor.  Comparison
is by terminal role, not by netlist column, because the two PDKs declare
their symbol pins in different orders.

What is deliberately NOT compared
---------------------------------
Device sizes and models.  This is a port between processes; every W, L and
model name is expected to differ.  This tool answers "is it the same circuit",
and the simulations in sim/ answer "does it still work".

Auto-generated net names (net1, net2, ...) are matched up to a consistent
one-to-one renaming, since xschem numbers unnamed nets in drawing order and
the port adds labels that can shift that numbering.

Usage:  tools/check_port_equivalence.py <sky130.spice> <ihp.spice>
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

AUTO_NET = re.compile(r"^net\d+$")

# Terminal roles by model, in the order the netlist emits them.
ROLES = {
    # sky130
    "sky130_fd_pr__nfet_01v8": ["D", "G", "S", "B"],
    "sky130_fd_pr__pfet_01v8": ["D", "G", "S", "B"],
    "sky130_fd_pr__res_high_po": ["M", "P", "RB"],
    "sky130_fd_pr__res_high_po_0p69": ["M", "P", "RB"],
    "sky130_fd_pr__res_xhigh_po_0p35": ["M", "P", "RB"],
    "sky130_fd_pr__cap_mim_m3_1": ["c0", "c1"],
    "sky130_fd_sc_hd__inv_1": ["A", "VGND", "VNB", "VPB", "VPWR", "Y"],
    # IHP SG13CMOS5L
    "sg13_lv_nmos": ["D", "G", "S", "B"],
    "sg13_lv_pmos": ["D", "G", "S", "B"],
    "rhigh": ["P", "M", "RB"],
    "cap_cmomf": ["c0", "c1"],
    "inv_cp": ["A", "Y", "VPWR", "VGND"],
}

# Roles that exist on one side only, and why it is legitimate.
#   RB   the sky130 poly resistor has a bulk pin; IHP carries the body as the
#        'body=sub!' parameter, so the terminal disappears.  Both are the
#        substrate.
#   VNB/VPB  the sky130 standard-cell inverter has separate bulk pins; the
#        replacement two-transistor cell ties bulks to its own rails.
IGNORED_ROLES = {"RB", "VNB", "VPB"}

# Cells that exist on the IHP side only, with the reason.  A new cell here is
# a deliberate substitution, not an accident, so each one has to be listed.
EXPECTED_NEW_CELLS = {
    "inv_cp": "replaces the sky130 standard cell sky130_fd_sc_hd__inv_1",
}


def read_netlist(path: Path):
    """Return {subckt: (pins, {inst: (model, {role: net})})}."""
    text = path.read_text()
    # Join SPICE continuation lines.
    text = re.sub(r"\n\+\s*", " ", text)
    # Two passes: xschem emits the top level first and its children after, so
    # an instance is read before the subcircuit it instantiates is defined.
    # Collect every pin list first, then resolve instances against it.
    subckts = {}
    for line in text.splitlines():
        line = line.strip()
        if line.lower().startswith(".subckt"):
            parts = line.split()
            subckts[parts[1]] = (parts[2:], {})
    cur = None
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("*"):
            continue
        low = line.lower()
        if low.startswith(".subckt"):
            cur = line.split()[1]
            continue
        if low.startswith(".ends"):
            cur = None
            continue
        if cur is None or not line[0] in "xX":
            continue
        # x<name> net net ... <model_or_subckt> [params]
        toks = line.split()
        inst = toks[0]
        rest = toks[1:]
        # The model name is the last token that has no '=' in it and is not
        # itself a net; walk from the left until we hit a known model, else
        # take the last bare token.
        model = None
        idx = None
        for i, t in enumerate(rest):
            if t in ROLES or t in subckts:
                model, idx = t, i
                break
        if model is None:
            bare = [i for i, t in enumerate(rest) if "=" not in t and "'" not in t]
            if not bare:
                continue
            idx = bare[-1]
            model = rest[idx]
        nets = rest[:idx]
        roles = ROLES.get(model)
        if roles is None:
            # A subcircuit instance: roles are that subcircuit's pin names.
            roles = subckts.get(model, ([], {}))[0]
        mapping = {}
        for r, n in zip(roles, nets):
            mapping[r] = n
        if len(roles) != len(nets):
            mapping["__ARITY__"] = f"{len(nets)} nets for {len(roles)} pins"
        subckts[cur][1][inst] = (model, mapping)
    return subckts


def compare(a, b):
    """a = sky130, b = IHP.  Returns a list of human-readable differences."""
    diffs = []
    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))
    for s in only_a:
        diffs.append(f"subcircuit only in sky130: {s}")
    for s in only_b:
        if s in EXPECTED_NEW_CELLS:
            continue
        diffs.append(f"subcircuit only in IHP: {s}")

    for name in sorted(set(a) & set(b)):
        pins_a, insts_a = a[name]
        pins_b, insts_b = b[name]
        if pins_a != pins_b:
            diffs.append(f"{name}: pin list differs\n  sky130 {pins_a}\n  IHP    {pins_b}")
        ia, ib = set(insts_a), set(insts_b)
        for i in sorted(ia - ib):
            diffs.append(f"{name}: instance missing from IHP: {i}")
        for i in sorted(ib - ia):
            diffs.append(f"{name}: instance added in IHP: {i}")

        # Net-name mapping is resolved per subcircuit: named nets must match
        # exactly, auto-generated ones must map one-to-one.
        fwd, rev = {}, {}
        pending = []
        for i in sorted(ia & ib):
            ma, na = insts_a[i]
            mb, nb = insts_b[i]
            roles = (set(na) | set(nb)) - IGNORED_ROLES - {"__ARITY__"}
            if "__ARITY__" in na or "__ARITY__" in nb:
                diffs.append(f"{name}.{i}: pin/net count mismatch "
                             f"({na.get('__ARITY__', 'ok')} / {nb.get('__ARITY__', 'ok')})")
            for r in sorted(roles):
                va, vb = na.get(r), nb.get(r)
                if va is None or vb is None:
                    diffs.append(f"{name}.{i}: terminal {r} present on one side only "
                                 f"(sky130={va}, IHP={vb})")
                    continue
                if AUTO_NET.match(va) or AUTO_NET.match(vb):
                    pending.append((i, r, va, vb))
                elif va != vb:
                    diffs.append(f"{name}.{i}.{r}: sky130 '{va}' vs IHP '{vb}'")
        for i, r, va, vb in pending:
            if va in fwd and fwd[va] != vb:
                diffs.append(f"{name}.{i}.{r}: net '{va}' maps to both "
                             f"'{fwd[va]}' and '{vb}' -- connectivity changed")
            elif vb in rev and rev[vb] != va:
                diffs.append(f"{name}.{i}.{r}: nets '{rev[vb]}' and '{va}' both map to "
                             f"'{vb}' -- two nets were merged")
            else:
                fwd[va] = vb
                rev[vb] = va
    return diffs


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    a = read_netlist(Path(sys.argv[1]))
    b = read_netlist(Path(sys.argv[2]))
    diffs = compare(a, b)
    n_sub = len(set(a) & set(b))
    n_inst = sum(len(v[1]) for v in b.values())
    if diffs:
        print(f"{len(diffs)} difference(s) between the sky130 source and the IHP port:\n")
        for d in diffs:
            print("  " + d)
        return 1
    print(f"Port is structurally identical to the sky130 source: "
          f"{n_sub} subcircuits, {n_inst} instances, every terminal on the same net.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
