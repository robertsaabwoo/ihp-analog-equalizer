"""The design must only use devices that exist on SG13CMOS5L.

This is the test that earns its place. SG13CMOS5L is the CMOS-only member of
the SG13 family and it does *not* have a MIM capacitor, HBTs, inductors, deep
n-well or Schottky diodes. But its PDK is an overlay on SG13G2, and the SG13G2
symbol library sits on XSCHEM_LIBRARY_PATH, so a `cap_cmim` dropped into a
schematic will resolve, netlist, and simulate correctly against the shared
models -- and then be unmanufacturable.

Nothing else in the flow catches that. ngspice does not know what mask set you
are targeting.
"""
import re
from pathlib import Path

import pytest

XSCHEM = Path(__file__).resolve().parent.parent / "xschem"

# Devices available on SG13CMOS5L, from the symbol library
# $PDK_ROOT/ihp-sg13cmos5l/libs.tech/xschem/sg13cmos5l_pr/.
ALLOWED_PR = {
    "sg13_lv_nmos", "sg13_lv_pmos", "sg13_hv_nmos", "sg13_hv_pmos",
    "sg13_lv_rf_nmos", "sg13_lv_rf_pmos", "sg13_hv_rf_nmos", "sg13_hv_rf_pmos",
    "sg13_svaricap",
    "rhigh", "rsil", "rppd",
    "cap_cmomi", "cap_cmomf",
    "moscap_n", "moscap_p",
    "nmoscl_2", "nmoscl_4",
    "ntap1", "ptap1", "sub", "pnpMPA",
    "dantenna", "dpantenna", "bondpad",
    "diodevdd_2kv", "diodevdd_4kv", "diodevss_2kv", "diodevss_4kv",
    "annotate_fet_params", "gallery",
}

# Present in the SG13G2 library, which is on the search path, and absent from
# SG13CMOS5L. Named explicitly so the failure message can say what is wrong
# rather than just "not in the allowed set".
SG13G2_ONLY = {
    "cap_cmim": "SG13CMOS5L has no MIM capacitor -- use cap_cmomf",
    "cap_rfcmim": "SG13CMOS5L has no MIM capacitor",
    "cap_cpara": "not in the SG13CMOS5L symbol library",
    "inductor": "SG13CMOS5L has no inductors",
    "inductor3": "SG13CMOS5L has no inductors",
    "isolbox": "SG13CMOS5L has no deep n-well",
    "schottky_nbl1": "SG13CMOS5L has no Schottky diodes",
    "npn13G2": "SG13CMOS5L is CMOS only -- no HBTs",
    "npn13G2l": "SG13CMOS5L is CMOS only -- no HBTs",
    "npn13G2v": "SG13CMOS5L is CMOS only -- no HBTs",
    "npn13G2_5t": "SG13CMOS5L is CMOS only -- no HBTs",
    "npn13G2l_5t": "SG13CMOS5L is CMOS only -- no HBTs",
    "npn13G2v_5t": "SG13CMOS5L is CMOS only -- no HBTs",
}

INSTANCE = re.compile(r"^C\s*\{([^}]+)\}", re.M)


def instantiated_symbols():
    """Every symbol referenced by any schematic, as (schematic, library, cell)."""
    for sch in sorted(XSCHEM.glob("*.sch")):
        for m in INSTANCE.finditer(sch.read_text()):
            ref = m.group(1)
            lib, _, cell = ref.rpartition("/")
            yield sch.name, lib, cell.removesuffix(".sym")


def test_no_sg13g2_only_devices():
    bad = []
    for sch, _lib, cell in instantiated_symbols():
        if cell in SG13G2_ONLY:
            bad.append(f"{sch} uses {cell}: {SG13G2_ONLY[cell]}")
    assert not bad, "devices not available on SG13CMOS5L:\n  " + "\n  ".join(bad)


def test_no_sky130_devices_remain():
    """The port is complete: nothing still refers to the source process."""
    bad = [f"{sch}: {lib}/{cell}"
           for sch, lib, cell in instantiated_symbols()
           if "sky130" in lib]
    assert not bad, "sky130 references survived the port:\n  " + "\n  ".join(bad)


def test_pdk_devices_are_in_the_allowed_set():
    """Anything from the PDK library must be a real SG13CMOS5L device."""
    bad = []
    for sch, lib, cell in instantiated_symbols():
        if lib.endswith("_pr") and cell not in ALLOWED_PR:
            bad.append(f"{sch}: {lib}/{cell}")
    assert not bad, ("PDK devices not in the SG13CMOS5L set:\n  "
                     + "\n  ".join(bad))


def test_pdk_library_is_sg13cmos5l_not_sg13g2():
    """Symbols are referenced through the CMOS5L library path.

    Both libraries exist and the symbols behind them are often literally the
    same files, so referring to sg13g2_pr works. It is still wrong: it is the
    line in the schematic that says which process this design is for.
    """
    bad = [f"{sch}: {lib}/{cell}"
           for sch, lib, cell in instantiated_symbols()
           if lib == "sg13g2_pr"]
    assert not bad, ("referenced through sg13g2_pr rather than sg13cmos5l_pr:\n  "
                     + "\n  ".join(bad))


@pytest.mark.skipif(not (XSCHEM / "CTLE.sch").exists(), reason="no schematics")
def test_ctle_still_has_its_degeneration_capacitor():
    """The one component whose absence would leave a working-looking design.

    Without the degeneration capacitor the CTLE is a plain differential
    amplifier: it still biases, still has gain, still simulates, and provides
    no equalisation at all. That is exactly the state the sky130 original was
    found in.
    """
    text = (XSCHEM / "CTLE.sch").read_text()
    assert "cap_cmomf" in text, "CTLE.sch has no degeneration capacitor"
