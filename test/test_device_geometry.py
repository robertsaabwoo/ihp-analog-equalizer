"""Every device must be inside the PDK model's validated geometry range.

The SG13 PSP models state their range in the header of
`sg13g2_moslv_mod.lib`:

    Valid range for model:  L = (0.13 - 10) um
                            W = (0.15 - 10) um

and W there is the width of **one finger**, not the total: the subcircuit
computes its diffusion areas from `w/ng`. ngspice will happily evaluate a
30 µm-wide single-finger device and return numbers, but they are extrapolated
outside the fit, and nobody draws a 30 µm transistor as one finger anyway --
the gate resistance and the drain capacitance would both be wrong in layout.

This is the kind of error that never surfaces in simulation. It surfaces at
the review where someone asks why a device is outside the model range.

Reads the generated netlist if it is present (the authoritative answer, since
it is what ngspice sees), and otherwise the schematics directly, so it still
does something useful in CI where there is no PDK to netlist against.
"""
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
NETLIST = ROOT / "sim" / "netlists" / "blocks.inc"
XSCHEM = ROOT / "xschem"

L_MIN, L_MAX = 0.13, 10.0     # um
W_MIN, W_MAX = 0.15, 10.0     # um, per finger


def microns(value: str) -> float:
    """'0.13u' or '1.3e-07' -> microns."""
    value = value.strip()
    if value.endswith("u"):
        return float(value[:-1])
    return float(value) * 1e6


def devices_from_netlist():
    text = re.sub(r"\n\+\s*", " ", NETLIST.read_text())
    for line in text.splitlines():
        line = line.strip()
        if not line[:1].lower() == "x" or "sg13_lv_" not in line:
            continue
        params = dict(t.split("=", 1) for t in line.split() if "=" in t)
        yield line.split()[0], params


def devices_from_schematics():
    block = re.compile(r"^C \{sg13cmos5l_pr/sg13_lv_[np]mos\.sym\}[^{]*\{(.*?)\}",
                       re.M | re.S)
    for sch in sorted(XSCHEM.glob("*.sch")):
        for m in block.finditer(sch.read_text()):
            params = dict(t.split("=", 1) for t in m.group(1).split() if "=" in t)
            yield f"{sch.stem}.{params.get('name', '?')}", params


def all_devices():
    if NETLIST.exists():
        yield from devices_from_netlist()
    else:
        yield from devices_from_schematics()


def test_there_are_devices_to_check():
    assert list(all_devices()), "found no lv MOSFETs -- the check would pass vacuously"


def test_channel_lengths_are_in_range():
    bad = []
    for name, p in all_devices():
        length = microns(p["l"])
        if not (L_MIN <= length <= L_MAX):
            bad.append(f"{name}: l = {length:g} um")
    assert not bad, ("channel lengths outside the PSP model's 0.13-10 um range:\n  "
                     + "\n  ".join(bad))


def test_finger_widths_are_in_range():
    """W in the model header is per finger: the subcircuit uses w/ng."""
    bad = []
    for name, p in all_devices():
        w = microns(p["w"])
        ng = int(float(p.get("ng", 1)))
        per_finger = w / ng
        if not (W_MIN <= per_finger <= W_MAX):
            bad.append(f"{name}: w = {w:g} um / ng = {ng} "
                       f"-> {per_finger:g} um per finger")
    assert not bad, (
        "finger widths outside the PSP model's 0.15-10 um range.\n"
        "Add fingers (ng) so that w/ng stays in range -- a 30 um device is\n"
        "drawn as several fingers in layout regardless:\n  " + "\n  ".join(bad))


@pytest.mark.skipif(not NETLIST.exists(),
                    reason="needs a netlist: run tools/netlist.sh")
def test_resistor_and_capacitor_widths_are_sane():
    """Passives get their geometry solved by the port tool, so check the answer."""
    text = re.sub(r"\n\+\s*", " ", NETLIST.read_text())
    bad = []
    for line in text.splitlines():
        line = line.strip()
        if not line[:1].lower() == "x":
            continue
        if "rhigh" not in line and "cap_cmomf" not in line:
            continue
        p = dict(t.split("=", 1) for t in line.split() if "=" in t)
        w, length = microns(p["w"]), microns(p["l"])
        if not (0.3 <= w <= 200) or not (0.3 <= length <= 500):
            bad.append(f"{line.split()[0]}: w = {w:g} um, l = {length:g} um")
    assert not bad, ("passive geometry looks implausible -- check the solver "
                     "in tools/port_from_sky130.py:\n  " + "\n  ".join(bad))
