#!/usr/bin/env python3
"""Generate xschem/coarse_loop.{sch,sym} from sim/decks/coarse_loop.inc.

The coarse loop was designed and debugged as a SPICE include, because every
question it raised -- does the wrap fire, where is the null, how fast does the
search run -- is answered by a transient that takes seconds, and redrawing a
thirty-device schematic between iterations would have been the slow part of
every one of them.

Having settled it, the schematic has to exist and has to agree with the
include, and typing it twice is how the two diverge.  So this generates the
schematic from the include.  `test/test_coarse_loop.py` then netlists the
schematic and compares it back against the include, terminal by terminal,
which is the same trick `tools/check_port_equivalence.py` plays against the
sky130 source and for the same reason: **xschem connects by coordinate**, and
a symbol placed forty units off is a different circuit that looks identical.

Connectivity here is by *label*, not by wire: every pin gets a `lab_wire`
placed exactly on it.  That is legal xschem, it is what the generated cells
already do for supplies, and it means the layout of the drawing carries no
information that the netlist does not -- which is the property that makes
generating it safe.

    tools/gen_coarse_loop.py [--inc sim/decks/coarse_loop.inc] [--out xschem]
"""
import argparse
import math
import re
import sys
from pathlib import Path

# Pin offsets, read out of the PDK symbols.  Order matches the netlist order
# each symbol's `format` string produces.
PINS = {
    "sg13_lv_nmos": [("D", 20, -30), ("G", -20, 0), ("S", 20, 30), ("B", 20, 0)],
    "sg13_lv_pmos": [("D", 20, 30), ("G", -20, 0), ("S", 20, -30), ("B", 20, 0)],
    "rhigh":        [("P", 0, -30), ("M", 0, 30)],
    "cap_cmomf":    [("c0", 0, -30), ("c1", 0, 30)],
}
# Attributes each symbol needs beyond the ones taken from the instance line.
EXTRA = {
    "rhigh":     {"body": "sub!", "b": "0"},
    "cap_cmomf": {"mmin": "1", "mmax": "4", "subblock": "0"},
}

PORTS = [("VDD", "iopin"), ("VSS", "iopin"), ("ibias", "ipin"),
         ("vctrl", "ipin"), ("vcoarse", "opin")]


def parse_params(text):
    """Evaluate the .param / .func lines at the top of the include.

    They are ordinary arithmetic with one helper (`Lr`, the PDK's resistance
    expression solved for length), so they evaluate in Python once SPICE's
    engineering suffixes are turned into exponents.
    """
    env = {"__builtins__": {}}
    funcs = {}
    for line in text.splitlines():
        m = re.match(r"\.func\s+(\w+)\(([^)]*)\)\s+'(.*)'", line.strip())
        if m:
            funcs[m.group(1)] = (m.group(2).split(","), m.group(3))
            continue
        m = re.match(r"\.param\s+(\w+)\s*=\s*(.+?)(?:\s+\$.*)?$", line.strip())
        if not m:
            continue
        env[m.group(1)] = _ev(m.group(2), env, funcs)
    return env, funcs


def _num(tok):
    """SPICE number with an optional engineering suffix."""
    suf = {"t": 1e12, "g": 1e9, "meg": 1e6, "k": 1e3, "m": 1e-3,
           "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15}
    m = re.fullmatch(r"([0-9.]+(?:[eE][-+]?\d+)?)([a-zA-Z]*)", tok)
    if not m:
        return None
    v, s = float(m.group(1)), m.group(2).lower()
    if s == "":
        return v
    for k in ("meg", "t", "g", "k", "m", "u", "n", "p", "f"):
        if s.startswith(k):
            return v * suf[k]
    return None


def _ev(expr, env, funcs):
    expr = expr.strip().strip("'")
    # A bare number, possibly suffixed.
    v = _num(expr)
    if v is not None:
        return v
    # Inline the one helper function rather than defining it in the eval
    # namespace, so the namespace stays empty of anything callable.
    for name, (args, body) in funcs.items():
        for m in reversed(list(re.finditer(rf"\b{name}\(([^()]*)\)", expr))):
            sub = body
            for a, val in zip(args, m.group(1).split(",")):
                sub = re.sub(rf"\b{a.strip()}\b", f"({val.strip()})", sub)
            expr = expr[:m.start()] + f"({sub})" + expr[m.end():]
    # Suffix every remaining bare token.
    def rep(m):
        v = _num(m.group(0))
        return repr(v) if v is not None else m.group(0)
    expr = re.sub(r"\b[0-9][0-9.]*(?:[eE][-+]?\d+)?[a-zA-Z]*\b", rep, expr)
    return eval(expr, dict(env), {})            # noqa: S307 - closed namespace


def parse_instances(text, env, funcs):
    body = text.split(".subckt coarse_loop")[1].split(".ends")[0]
    ports = body.splitlines()[0].split()
    insts = []
    for raw in body.splitlines()[1:]:
        line = raw.split("$")[0].strip()
        if not line or line.startswith("*"):
            continue
        toks = line.split()
        name = toks[0]
        assert name[0] in "Xx", f"not a subcircuit instance: {raw}"
        model = next(t for t in toks if t in PINS)
        mi = toks.index(model)
        nodes = toks[1:mi]
        attrs = {}
        for t in toks[mi + 1:]:
            if "=" not in t:
                continue
            k, v = t.split("=", 1)
            attrs[k] = v
        npin = len(PINS[model])
        if model == "rhigh":                      # body is an attribute, not a pin
            assert len(nodes) == 3, raw
            nodes, attrs["body"] = nodes[:2], nodes[2]
        assert len(nodes) == npin, f"{raw}: {len(nodes)} nodes, want {npin}"
        for k in ("w", "l"):
            if k in attrs:
                attrs[k] = "%.6e" % _ev(attrs[k], env, funcs)
        insts.append((name[1:], model, nodes, attrs))
    return ports, insts


def emit(ports, insts, env, header):
    cols = 6
    dx, dy = 140, 160
    out = ["v {xschem version=3.4.5 file_version=1.2\n}", "G {}", "K {}",
           "V {}", "S {}", "E {}"]
    out.append("T {" + header + "} -260 -200 0 0 0.3 0.3 {}")

    n = 0
    for name, model, nodes, attrs in insts:
        x = (n % cols) * dx
        y = (n // cols) * dy
        n += 1
        props = [f"name={name}"]
        for k in ("l", "w", "ng", "m", "mmin", "mmax", "subblock", "b"):
            if k in attrs:
                props.append(f"{k}={attrs[k]}")
        for k, v in EXTRA.get(model, {}).items():
            if k not in attrs:
                props.append(f"{k}={v}")
        if model == "rhigh":
            props.append(f"body={attrs['body']}")
        props += [f"model={model}", "mm_ok=1", "spiceprefix=X"]
        out.append("C {sg13cmos5l_pr/%s.sym} %d %d 0 0 {%s}"
                   % (model, x, y, "\n".join(props)))
        for (pin, ox, oy), net in zip(PINS[model], nodes):
            out.append("C {devices/lab_wire.sym} %d %d 0 0 "
                       "{name=%s_%s sig_type=std_logic lab=%s}"
                       % (x + ox, y + oy, name, pin, net))

    py = ((n + cols - 1) // cols) * dy + 60
    for i, (net, kind) in enumerate(PORTS):
        assert net in ports, f"{net} is not a port of the subcircuit"
        out.append("C {devices/%s.sym} %d %d 0 0 {name=P%d lab=%s}"
                   % (kind, i * dx, py, i, net))
    return "\n".join(out) + "\n"


SYM = """v {xschem version=3.4.5 file_version=1.2}
K {type=subcircuit
format="@name @pinlist @symname"
template="name=x1"
}
T {@symname} -75 -66 0 0 0.25 0.25 {}
T {@name} -75 54 0 0 0.2 0.2 {}
L 4 -70 -50 70 -50 {}
L 4 -70 50 70 50 {}
L 4 -70 -50 -70 50 {}
L 4 70 -50 70 50 {}
L 4 -70 -20 -60 -20 {}
L 4 -70 0 -60 0 {}
L 4 -70 20 -60 20 {}
L 4 60 0 70 0 {}
L 4 60 20 70 20 {}
B 5 -62.5 -22.5 -57.5 -17.5 {name=VDD dir=inout}
T {VDD} -54 -30 0 0 0.2 0.2 {}
B 5 -62.5 -2.5 -57.5 2.5 {name=VSS dir=inout}
T {VSS} -54 -10 0 0 0.2 0.2 {}
B 5 -62.5 17.5 -57.5 22.5 {name=ibias dir=in}
T {ibias} -54 10 0 0 0.2 0.2 {}
B 5 57.5 -2.5 62.5 2.5 {name=vctrl dir=in}
T {vctrl} 20 -10 0 0 0.2 0.2 {}
B 5 57.5 17.5 62.5 22.5 {name=vcoarse dir=out}
T {vcoarse} 8 10 0 0 0.2 0.2 {}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inc", default="sim/decks/coarse_loop.inc", type=Path)
    ap.add_argument("--out", default="xschem", type=Path)
    a = ap.parse_args()

    text = a.inc.read_text()
    env, funcs = parse_params(text)
    ports, insts = parse_instances(text, env, funcs)

    # The name in the header has to be stable wherever the tool is run from,
    # because test_coarse_loop.py regenerates into a scratch directory and
    # compares byte for byte.
    header = ("coarse_loop -- GENERATED by tools/gen_coarse_loop.py from\n"
              "sim/decks/coarse_loop.inc.  Do not edit: edit the include and\n"
              "re-run.  Connectivity is by label, one lab_wire on every pin.\n"
              "%d devices.  See docs/RING_DUAL_LOOP.md." % len(insts))
    (a.out / "coarse_loop.sch").write_text(emit(ports, insts, env, header))
    (a.out / "coarse_loop.sym").write_text(SYM)
    print(f"coarse_loop.sch: {len(insts)} devices, ports {' '.join(ports)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
