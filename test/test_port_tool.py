"""The port tool's arithmetic and its structural guarantees.

The port converts passives by *value*: it takes the sky130 resistance or
capacitance and solves the IHP geometry from the PDK's own expressions. If that
arithmetic is wrong, every resistor in the design is wrong by the same factor,
which is exactly the kind of error that produces a plausible-looking circuit.

One of these tests exists because the bug it checks for actually happened: the
capacitor solver had a stray 1e-6 and produced a 22 pm capacitor. It simulated
perfectly and showed no peaking at all.
"""
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import port_from_sky130 as port  # noqa: E402


def rhigh_resistance(w_m, l_m):
    """The PDK's own expression for rhigh at b=0, as a check on the inverse."""
    return port.IHP_RHIGH_RC / w_m + port.IHP_RHIGH_SHEET * l_m / (w_m - port.IHP_RHIGH_DW)


@pytest.mark.parametrize("ohms", [900, 2500, 3500, 7355, 30000, 240000])
def test_resistor_solver_round_trips(ohms):
    kv = [("W", "1"), ("L", str(ohms / port.SKY_RSH_HIGH_PO)), ("mult", "1")]
    new_kv, target = port.port_res("cell", "R1", kv, "sky130_fd_pr/res_high_po.sym")
    assert target == pytest.approx(ohms, rel=1e-6)
    w = float(dict(new_kv)["w"])
    length = float(dict(new_kv)["l"])
    assert rhigh_resistance(w, length) == pytest.approx(ohms, rel=1e-6)


@pytest.mark.parametrize("farads", [121e-15, 648e-15, 1600e-15])
def test_capacitor_solver_gives_a_sane_geometry(farads):
    kv = [("W", "1"), ("L", str(farads / port.SKY_MIM_DENSITY)), ("MF", "1")]
    new_kv, target = port.port_cap("cell", "C1", kv)
    assert target == pytest.approx(farads, rel=1e-6)
    side = float(dict(new_kv)["w"])
    # Metres, not microns, and not micro-metres-squared-by-mistake.  A 648 fF
    # cap_cmomf is a 22 um square: 2.2e-5 m.  The bug this guards against
    # produced 2.2e-11.
    assert 1e-6 < side < 1e-3, f"{side} m is not a plausible capacitor side"
    assert side ** 2 * port.IHP_CMOMF_DENSITY * 1e12 == pytest.approx(
        farads, rel=1e-6), "area times density does not give the target"


def test_minimum_length_is_remapped_not_kept():
    """sky130's Lmin is 0.15 um; IHP's is 0.13 um."""
    kv = [("L", "0.15"), ("W", "8"), ("nf", "4"), ("mult", "1")]
    new_kv, _ = port.port_fet("cell", "M1", kv, True, False)
    assert dict(new_kv)["l"] == "0.13u"


def test_longer_lengths_are_preserved():
    """A device drawn longer than minimum asked for that length on purpose."""
    for drawn in ("0.3", "0.5", "1", "2", "8"):
        kv = [("L", drawn), ("W", "3"), ("nf", "1"), ("mult", "1")]
        new_kv, _ = port.port_fet("cell", "Mx", kv, True, False)
        assert dict(new_kv)["l"] == port.um(float(drawn))


def test_finger_count_and_multiplier_carry_over():
    kv = [("L", "0.15"), ("W", "16"), ("nf", "8"), ("mult", "2")]
    new_kv, _ = port.port_fet("cell", "M1", kv, False, False)
    d = dict(new_kv)
    assert d["ng"] == "8" and d["m"] == "2" and d["w"] == "16u"
    assert d["model"] == "sg13_lv_pmos"


def test_three_pin_fet_reports_its_body_net():
    """The bulk must come back so the caller can put a label on the new B pin."""
    kv = [("L", "1"), ("W", "1"), ("nf", "1"), ("mult", "1"), ("body", "VNB")]
    _, body = port.port_fet("cell", "MNSRC", kv, True, True)
    assert body == "VNB"


def test_four_pin_fet_reports_no_body():
    kv = [("L", "1"), ("W", "1"), ("nf", "1"), ("mult", "1")]
    _, body = port.port_fet("cell", "M1", kv, True, False)
    assert body is None


@pytest.mark.parametrize("rot,flip,expected", [
    (0, 0, (20, 0)),
    (1, 0, (0, 20)),
    (2, 0, (-20, 0)),
    (3, 0, (0, -20)),
    (0, 1, (-20, 0)),
    (2, 1, (20, 0)),
])
def test_instance_transform_matches_xschem(rot, flip, expected):
    """The bulk-pin coordinate must be computed the way xschem computes it.

    Get this wrong and the label lands somewhere the pin is not, the bulk
    floats, and the netlist is still structurally valid.
    """
    assert port.transform(20, 0, 0, 0, rot, flip) == expected


def test_every_sizing_override_names_a_real_cell():
    schematics = {p.stem for p in (ROOT / "xschem").glob("*.sch")}
    unknown = {cell for cell, _inst in port.SIZING if cell not in schematics}
    assert not unknown, f"SIZING refers to cells that do not exist: {unknown}"


# --------------------------------------------------------------- dual loop
#
# The two POST_PORT_EDITS that carry the coarse loop into the design.  Both
# attach by label rather than by drawn geometry, which is the whole reason they
# are safe to append to a schematic whose layout the tool did not compute --
# xschem connects by *coordinate*, so a symbol appended forty units off is a
# different circuit that looks identical.  These tests check the properties
# that make the label trick work, because the failure mode if one breaks is a
# netlist with a floating gate, not an error.

def _labels(text):
    """{(x, y): net} for every lab_wire in a schematic."""
    import re
    out = {}
    for m in re.finditer(r"C \{devices/lab_wire\.sym\} (-?\d+) (-?\d+) 0 0 "
                         r"\{name=(\S+).*?lab=(\S+?)\}", text):
        out[(int(m.group(1)), int(m.group(2)))] = m.group(4)
    return out


def _instances(text):
    """{name: (symbol, x, y)} for every component placed in a schematic."""
    import re
    out = {}
    for m in re.finditer(r"C \{(\S+?)\.sym\} (-?\d+) (-?\d+) 0 0 \{name=(\w+)",
                         text):
        out[m.group(4)] = (m.group(1), int(m.group(2)), int(m.group(3)))
    return out


PMOS_PINS = {"D": (20, 30), "G": (-20, 0), "S": (20, -30), "B": (20, 0)}


def test_trim_legs_land_on_their_own_pins():
    """Every trim pMOS pin must have a lab_wire exactly on it."""
    src = (ROOT / "xschem" / "ring_inverter.sch").read_text()
    out = port.add_coarse_trim(src)
    labels, insts = _labels(out), _instances(out)
    for name, expect_drain in (("T1", "vo+"), ("T2", "vo-")):
        assert name in insts, f"{name} was not placed"
        sym, x, y = insts[name]
        assert sym == "sg13cmos5l_pr/sg13_lv_pmos"
        want = {"D": expect_drain, "G": "vcoarse!", "S": "VDD", "B": "VDD"}
        for pin, (dx, dy) in PMOS_PINS.items():
            got = labels.get((x + dx, y + dy))
            assert got == want[pin], (
                f"{name}.{pin} at ({x+dx},{y+dy}): expected {want[pin]}, got {got}")


def test_trim_legs_do_not_land_on_existing_geometry():
    """A label dropped onto an existing pin rewires that pin silently."""
    src = (ROOT / "xschem" / "ring_inverter.sch").read_text()
    before = set(_labels(src))
    added = set(_labels(port.add_coarse_trim(src))) - before
    assert added, "no labels were added at all"
    assert not (added & before), f"trim labels reuse existing points: {added & before}"


def test_trim_leg_is_a_correction_not_the_load():
    """The rejected diode-load experiment made the transistor *be* the load and
    5 of 24 swept points stopped oscillating.  Here the poly resistor stays."""
    src = (ROOT / "xschem" / "ring_inverter.sch").read_text()
    out = port.add_coarse_trim(src)
    assert out.count("model=rhigh") == src.count("model=rhigh") == 2


def test_coarse_loop_is_instantiated_in_the_cdr():
    src = (ROOT / "xschem" / "CDR.sch").read_text()
    out = port.add_coarse_loop(src)
    insts = _instances(out)
    name = next(n for n, (s, _, _) in insts.items() if s == "coarse_loop")
    _, x, y = insts[name]
    labels = _labels(out)
    want = {(-60, -20): "Vdd", (-60, 0): "Vss", (-60, 20): "vbias",
            (60, 0): "vctrl", (60, 20): "vcoarse!"}
    for (dx, dy), net in want.items():
        got = labels.get((x + dx, y + dy))
        assert got == net, f"coarse_loop pin at ({dx},{dy}): expected {net}, got {got}"


def test_loop_filter_output_gets_named_vctrl():
    """It is the node every measurement in docs/ calls vctrl, and it is about
    to have a second consumer.  The label has to land on the existing net."""
    import re
    src = (ROOT / "xschem" / "CDR.sch").read_text()
    out = port.add_coarse_loop(src)
    x, y = next((p for p, n in _labels(out).items()
                 if n == "vctrl" and p not in _labels(src)), (None, None))
    assert x is not None, "no vctrl label was added"
    # The point must sit on a wire segment that xschem already calls net1.
    on_net1 = False
    for m in re.finditer(r"^N (-?\d+) (-?\d+) (-?\d+) (-?\d+) \{\nlab=#net1\}",
                         src, re.M):
        x1, y1, x2, y2 = (int(g) for g in m.groups())
        if (x1 == x2 == x and min(y1, y2) <= y <= max(y1, y2)) or \
           (y1 == y2 == y and min(x1, x2) <= x <= max(x1, x2)):
            on_net1 = True
    assert on_net1, f"the vctrl label at ({x},{y}) is not on the loop filter's net"
