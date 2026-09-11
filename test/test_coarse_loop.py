"""The coarse loop's schematic must not drift from the include it came from.

`sim/decks/coarse_loop.inc` is where the circuit was designed and debugged --
every question it raised is answered by a transient that takes seconds, and
redrawing a thirty-device schematic between iterations would have been the slow
part of each one.  `xschem/coarse_loop.sch` is generated from it.  Two ways
that arrangement goes wrong, and one test for each:

  * the include changes and nobody re-runs the generator, so the schematic --
    which is what gets fabricated -- is a circuit nobody simulated;
  * somebody edits the schematic by hand, and the next generator run silently
    reverts it.  This is the same hazard CLAUDE.md section 4 documents for the
    ported cells, and the same answer: the generated file is not the source.

Needs no PDK and no simulator, in keeping with the rest of test/.  The stronger
check -- netlist the schematic with xschem and compare terminal by terminal
against the include -- is in `test_netlist_matches_include`, which skips when
xschem is not on the path.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

INC = ROOT / "sim" / "decks" / "coarse_loop.inc"
SCH = ROOT / "xschem" / "coarse_loop.sch"
SYM = ROOT / "xschem" / "coarse_loop.sym"


def instances_from_inc(text):
    """{name: (model, [nodes], {w, l})} for the include's subcircuit body."""
    import gen_coarse_loop as g
    env, funcs = g.parse_params(text)
    _, insts = g.parse_instances(text, env, funcs)
    return {n: (m, nodes, {k: v for k, v in a.items() if k in ("w", "l")})
            for n, m, nodes, a in insts}


def instances_from_netlist(text):
    out = {}
    for line in text.splitlines():
        if not line[:1] in ("X", "x"):
            continue
        t = line.split()
        model = next((x for x in t if x.startswith(("sg13_", "rhigh", "cap_"))), None)
        if model is None:
            continue
        mi = t.index(model)
        nodes = t[1:mi]
        attrs = dict(x.split("=", 1) for x in t[mi + 1:] if "=" in x)
        if model == "rhigh":
            nodes = nodes[:2]
        out[t[0][1:]] = (model, nodes,
                         {k: v for k, v in attrs.items() if k in ("w", "l")})
    return out


class TestCoarseLoopGenerated(unittest.TestCase):
    def test_files_exist(self):
        for p in (INC, SCH, SYM):
            self.assertTrue(p.exists(), f"{p} is missing")

    def test_schematic_is_up_to_date(self):
        """Re-run the generator into a scratch directory and diff."""
        import gen_coarse_loop as g
        with tempfile.TemporaryDirectory() as d:
            r = subprocess.run(
                [sys.executable, str(ROOT / "tools" / "gen_coarse_loop.py"),
                 "--inc", str(INC), "--out", d],
                capture_output=True, text=True, cwd=ROOT)
            self.assertEqual(r.returncode, 0, r.stderr)
            fresh = (Path(d) / "coarse_loop.sch").read_text()
        self.assertEqual(
            fresh, SCH.read_text(),
            "xschem/coarse_loop.sch does not match what tools/gen_coarse_loop.py\n"
            "produces from sim/decks/coarse_loop.inc.  Either the include changed\n"
            "and the generator was not re-run, or the schematic was hand-edited.\n"
            "Re-run: tools/gen_coarse_loop.py")

    def test_every_pin_is_labelled(self):
        """Connectivity here is by label, so a missing one is a floating pin."""
        import gen_coarse_loop as g
        text = SCH.read_text()
        insts = instances_from_inc(INC.read_text())
        for name, (model, nodes, _) in insts.items():
            for pin, _, _ in g.PINS[model]:
                self.assertIn(f"name={name}_{pin} ", text,
                              f"{name}.{pin} has no lab_wire")

    def test_only_manufacturable_devices(self):
        """Same rule as test_device_set.py: CMOS5L has no MIM and no HBT."""
        allowed = {"sg13_lv_nmos", "sg13_lv_pmos", "rhigh", "cap_cmomf"}
        used = set(re.findall(r"model=(\S+)", SCH.read_text()))
        self.assertTrue(used <= allowed, f"unexpected devices: {used - allowed}")

    def test_no_moscap(self):
        """cap_leak.spice measured 773 pA of gate leakage on 384 um2 of
        moscap_n, which is 184 mV/ms on this node.  It must not come back."""
        self.assertNotIn("moscap", SCH.read_text())
        self.assertNotIn("moscap", INC.read_text().split(".subckt")[1])

    def test_ksweep_is_one(self):
        """Ksweep scales the loop current so a closed-loop acquisition fits in
        an affordable transient.  A committed value other than 1 would make
        every silicon number in the docs wrong."""
        m = re.search(r"^\.param Ksweep=(\S+)", INC.read_text(), re.M)
        self.assertIsNotNone(m, "Ksweep parameter is gone")
        self.assertEqual(m.group(1), "1")

    @unittest.skipUnless(shutil.which("xschem") and os.environ.get("PDK_ROOT"),
                         "needs xschem and PDK_ROOT")
    def test_netlist_matches_include(self):
        with tempfile.TemporaryDirectory() as d:
            # env.sh is what sets XSCHEM_LIBRARY_PATH; without it xschem
            # exits zero having found no symbols at all, which is trap 1.1.
            r = subprocess.run(
                ["bash", "-c",
                 ". ./env.sh >/dev/null && cd xschem && "
                 f"xschem -n -s -x -q --rcfile ./xschemrc -o {d} coarse_loop.sch"],
                capture_output=True, text=True, cwd=ROOT)
            net = Path(d) / "coarse_loop.spice"
            self.assertTrue(net.exists(), r.stderr)
            got = instances_from_netlist(net.read_text())
        want = instances_from_inc(INC.read_text())
        self.assertEqual(set(got), set(want), "instance names differ")
        for name in want:
            wm, wn, wa = want[name]
            gm, gn, ga = got[name]
            self.assertEqual(gm, wm, f"{name}: model")
            self.assertEqual(gn, wn, f"{name}: terminals")
            for k in ("w", "l"):
                if k in wa:
                    self.assertAlmostEqual(
                        float(ga[k]), float(wa[k]), delta=float(wa[k]) * 1e-6,
                        msg=f"{name}: {k}")


if __name__ == "__main__":
    unittest.main()
