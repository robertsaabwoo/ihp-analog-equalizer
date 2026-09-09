"""Every symbol the design instantiates must resolve, and the blocks that make
it the design it claims to be must still be there.

xschem resolves a missing symbol **silently**: it emits a truncated netlist and
exits zero. That netlist is what LVS and every simulation would then trust, so
a broken hierarchy is not a loud failure, it is a quiet wrong answer. This runs
without the PDK or a simulator, so CI catches it on every push.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
XSCHEM = ROOT / "xschem"

INSTANCE = re.compile(r"^C\s*\{([^}]+)\}", re.M)

# Libraries that are resolved from outside this repository.
EXTERNAL_LIBS = {"devices", "sg13cmos5l_pr", "sg13cmos5l_stdcells"}


def local_symbols():
    return {p.stem for p in XSCHEM.glob("*.sym")}


def references():
    for sch in sorted(XSCHEM.glob("*.sch")):
        for m in INSTANCE.finditer(sch.read_text()):
            lib, _, cell = m.group(1).rpartition("/")
            yield sch, lib, cell.removesuffix(".sym")


def test_every_local_symbol_reference_resolves():
    have = local_symbols()
    missing = []
    for sch, lib, cell in references():
        if lib in EXTERNAL_LIBS or lib.startswith("sg13"):
            continue
        if lib == "" and cell not in have:
            missing.append(f"{sch.name} -> {cell}.sym")
    assert not missing, ("symbols not found in xschem/ (xschem would fail "
                         "silently on these):\n  " + "\n  ".join(missing))


def test_every_local_symbol_has_a_schematic():
    """A symbol with no schematic netlists as an empty subcircuit."""
    orphans = []
    for sym in sorted(XSCHEM.glob("*.sym")):
        text = sym.read_text()
        # Primitive symbols carry their own SPICE format string; hierarchical
        # ones are type=subcircuit and need a .sch behind them.
        if "type=subcircuit" in text and not (XSCHEM / f"{sym.stem}.sch").exists():
            orphans.append(sym.name)
    assert not orphans, "subcircuit symbols with no schematic:\n  " + "\n  ".join(orphans)


def test_top_level_instantiates_the_whole_signal_path():
    top = (XSCHEM / "ctle_cdr_rx.sch").read_text()
    for block in ("CTLE.sym", "CDR.sym", "inverter_chain.sym", "ibias_mirror.sym"):
        assert block in top, f"{block} missing from ctle_cdr_rx.sch"
    # Both recovered-clock phases are buffered so the ring sees a symmetric
    # load; driving only one leg skews the duty cycle of a differential
    # oscillator.
    assert top.count("C {inverter_chain.sym}") == 2, (
        "expected two output buffers, one per recovered-clock phase")


def test_cdr_contains_its_loop():
    cdr = (XSCHEM / "CDR.sch").read_text()
    for block in ("alexander_phase_detector.sym", "tiny_pll_charge_pump.sym",
                  "tiny_pll_loop_filter.sym", "ring_oscillator.sym",
                  "vctrl_precharge.sym"):
        assert block in cdr, f"{block} missing from CDR.sch -- the loop is open"


def test_ring_has_five_stages():
    """Five inverting stages, not four or six.

    The oscillation period is ten stage delays, so the stage count is part of
    the frequency plan. Changing it silently retargets the whole design.
    """
    ring = (XSCHEM / "ring_oscillator.sch").read_text()
    assert ring.count("C {ring_inverter.sym}") == 5, (
        "the ring is not five stages -- the frequency plan assumes it is")


def test_bias_is_a_current_input():
    """The top-level bias pin is ibias, not vbias.

    A voltage bias into a tail device does not specify a current across PVT;
    measured at 1.2 V it gave a 15 dB spread in the CTLE's Nyquist gain and a
    collapse at the fast corner. See docs/PORTING.md 4.1.
    """
    top = (XSCHEM / "ctle_cdr_rx.sch").read_text()
    assert "lab=ibias" in top
    assert "lab=vbias" not in top, (
        "a vbias net survived at the top level -- the bias must be a current")
