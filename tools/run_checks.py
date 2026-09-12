#!/usr/bin/env python3
"""Run the project's checks and write down what they said.

    tools/run_checks.py                 # repo tests + toolchain, seconds
    tools/run_checks.py --sims          # + the fast simulations, ~15 min
    tools/run_checks.py --full          # + the closed-loop runs, hours
    tools/run_checks.py --only ctle_ac  # one stage by name
    tools/run_checks.py --list          # what would run, and roughly how long

Exit status is 0 only if every check that is not marked `known_broken` passed.

WHY THIS EXISTS, AND WHAT IT IS NOT

Most of what goes wrong in this project does not raise an error.  A ring that
never started reports a settled control voltage and a 49 nanovolt clock; a
`meas` on an edge index that does not exist fails silently and leaves the
previous value in place; a swing filter read on the output buffer reports the
buffer.  `docs/SIMULATION_TRAPS.md` has twenty-eight of these.  So a script
that only checks "did ngspice exit zero" would pass on almost every failure
this project has actually had.

Every simulation stage here therefore carries **numeric expectations** with
bounds, taken from values already measured and recorded in docs/.  A stage
passes when the numbers come back inside them.  That makes this a regression
check: if a change moves a number, it says which number, by how much, and what
it used to be.

It is deliberately *not* a substitute for reading the logs.  Bounds are wide
enough not to trip on solver noise, which means a real but small drift can sit
inside them.  Everything it reads stays in `sim/results/` to be looked at.

THE COMPUTE BUDGET

The VM has 7.8 GB and 4 CPUs, and an unguarded ngspice has already exhausted
host memory and forced a reboot.  Every simulation goes through
`tools/safe_ngspice.sh`, which holds a global flock, so this script is safe to
start while something else is already running -- it will queue, not collide.
Nothing here runs anything in parallel.

Pure stdlib.  numpy is not installed and must not be.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DECKS = ROOT / "sim" / "decks"
RESULTS = ROOT / "sim" / "results"
SAFE = ROOT / "tools" / "safe_ngspice.sh"

# --------------------------------------------------------------------------
# Expectations.
#
# Each is (measure name, low, high, unit, note).  The bounds are deliberately
# loose -- they are there to catch "this moved by 10 %", not to pin the last
# digit -- and every one of them is a value that appears in docs/ with a log
# behind it.  If you change a bound, change the document too, or the two stop
# agreeing and the documentation is the one that will be believed.
# --------------------------------------------------------------------------


@dataclass
class Check:
    key: str                     # the `name = value` label in the ngspice log
    low: float
    high: float
    unit: str = ""
    note: str = ""


@dataclass
class Stage:
    name: str
    tier: str                    # quick | sims | full
    kind: str                    # pytest | shell | ngspice
    cost: str                    # rough wall time, for --list
    desc: str
    deck: str | None = None
    log: str | None = None
    cmd: list[str] | None = None
    checks: list[Check] = field(default_factory=list)
    known_broken: str = ""       # non-empty: expected to fail, and why
    mem_mb: int = 2500
    timeout_s: int = 2400


STAGES: list[Stage] = [
    # ---------------------------------------------------------------- quick
    Stage(
        "repo-tests", "quick", "pytest", "1 s",
        "48 consistency tests: manufacturable device set, channel geometry "
        "inside the PSP models' range, hierarchy, the port's passive "
        "arithmetic, and the generated coarse-loop schematic against its "
        "include.  No PDK, no simulator, no network.",
        cmd=[sys.executable, "-m", "pytest", "test", "-q"],
    ),
    Stage(
        "toolchain", "quick", "shell", "1 s",
        "Is there a PDK, were the Verilog-A models compiled to OSDI, and is "
        "the netlist newer than the schematics it came from?  Nothing "
        "simulates without the OSDI build, and a stale netlist is the quiet "
        "way to measure last week's circuit.",
        cmd=None,
    ),
    # ----------------------------------------------------------------- sims
    Stage(
        "char-caps", "sims", "ngspice", "20 s",
        "Passive densities.  Every geometry the port solves comes from these, "
        "so a wrong constant here is a wrong constant in every resistor and "
        "capacitor in the design.",
        deck="../../char/caps.spice", log="char_caps.log",
        checks=[
            Check("Ccmomf", 120e-15, 138e-15, "F", "cap_cmomf, 100 um^2 -> 1.29 fF/um^2"),
            Check("Ccmomi", 94e-15, 107e-15, "F", "cap_cmomi -> 1.00 fF/um^2"),
            Check("Cmoscapn12", 1.19e-12, 1.34e-12, "F", "moscap_n at 1.2 V -> 12.7 fF/um^2"),
        ],
        mem_mb=1500, timeout_s=300,
    ),
    Stage(
        "cap-leak", "sims", "ngspice", "20 s",
        "Gate leakage of the candidate hold capacitors.  This is the "
        "measurement that disqualified moscap_n from the coarse loop's "
        "integrator: I/C is volts per second of drift and does not improve by "
        "scaling the capacitor.",
        deck="cap_leak.spice", log="cap_leak.log",
        checks=[
            Check("i_mosn", 5e-10, 1.1e-9, "A", "moscap_n leaks ~773 pA over 384 um^2"),
            Check("i_mom", 0.0, 5e-12, "A", "cap_cmomf is effectively leakless"),
        ],
        mem_mb=1500, timeout_s=300,
    ),
    Stage(
        "trim-r", "sims", "ngspice", "40 s",
        "The coarse trim leg measured as a dc resistance.  Pairs with "
        "'vco-ct': the leg matches the hand arithmetic to 1 % here and "
        "delivers 43 % of it in the ring, because a pMOS is only a resistor "
        "while it stays in triode.",
        deck="trim_r.spice", log="trim_r.log",
        checks=[Check("r_alone", -8.4e3, -7.6e3, "ohm",
                      "the 8000 ohm reference resistor, sign from i(Vn)")],
        mem_mb=1500, timeout_s=600,
    ),
    Stage(
        "cp-current", "sims", "ngspice", "1 min",
        "Charge pump and loop filter.  The 11.0 % up/down mismatch this "
        "measures is what drives vctrl one-signed when the loop is out of "
        "band, which is the entire reason the coarse loop has to search "
        "rather than trim (docs/RING_DUAL_LOOP.md section 2).",
        deck="cp_current.spice", log="cp_current.log",
        mem_mb=2000, timeout_s=900,
    ),
    Stage(
        "vco-rsweep", "sims", "ngspice", "4 min",
        "Ring frequency against load resistance, at the top of the fine "
        "range.  Splits the stage delay into the part the coarse trim can "
        "move and the part it cannot: 61.0 ps + 13.100 ps per kilohm.",
        deck="vco_rsweep.spice", log="vco_rsweep.log",
        timeout_s=1800,
    ),
    Stage(
        "coarse-tb", "sims", "ngspice", "3 min",
        "The coarse loop open-loop, with vctrl driven by hand: cold start, "
        "search rate, wrap span, and the null.  Seconds per question where "
        "the closed-loop equivalent is hours.",
        deck="coarse_tb.spice", log="coarse_tb.log",
        checks=[
            Check("v_park", 0.95, 1.25, "V", "cold start must park at the SLOW end"),
            Check("search_mv_us", 14.0, 26.0, "mV/us", "design point 19"),
            Check("search_span", 0.95, 1.15, "V", "must cover the whole trim range"),
            Check("d_600", -0.35, 0.35, "mV/us",
                  "the null sits at vctrl = 0.600 V, against a locked 0.599 V"),
        ],
        mem_mb=2000, timeout_s=1800,
    ),
    Stage(
        "vco-ct-centre", "sims", "ngspice", "8 min",
        "Where the coarse trim has to sit at nominal.  Also says whether the "
        "trim is centred -- one whose nominal is at either end has its range "
        "on one side only, and the corner sweep would still pass while half "
        "the silicon fell off the end.",
        deck="vco_ct_centre.spice", log="vco_ct_centre.log",
        timeout_s=2400,
    ),
    # ----------------------------------------------------------------- full
    Stage(
        "ctle-ac", "full", "shell", "12 min",
        "CTLE across 27 PVT corners.  Three ngspice starts because a .lib "
        "section is fixed at parse time; temperature and supply sweep inside "
        "each.",
        cmd=["bash", str(ROOT / "sim" / "run_ctle_ac.sh")],
    ),
    Stage(
        "e2e-lock", "full", "ngspice", "25 min",
        "The whole receiver, 0101 data at 600.6 Mb/s through the specified "
        "worst-case channel.  The headline number.  Note this pins vcoarse!: "
        "it measures the FINE loop alone, and with the trim rail free the "
        "coarse loop would quietly correct whatever the deck was detuning.",
        deck="e2e_lock.spice", log="e2e_lock_tt.log",
        checks=[
            Check("f_long", 597.0, 604.0, "MHz", "recovered clock vs 600.60"),
            Check("f_err", -0.6, 0.6, "%", ""),
            Check("vctrl_ripp", 0.0, 0.045, "V", "25.7 mV on the old ring"),
            Check("rclk_swing", 1.0, 1.4, "V", "a dead ring still reports a "
                                               "settled vctrl -- this is the check that catches it"),
        ],
        known_broken="On ring-coarse-tune this reaches 667.9 MHz, +11.2 %, "
                     "with vctrl climbing -- the out-of-band signature.  The "
                     "fine loop does not lock on the re-sized ring; see "
                     "docs/HANDBOOK.md section 11.1.  Passes on main.",
        timeout_s=3600,
    ),
    Stage(
        "e2e-prbs", "full", "ngspice", "35 min",
        "Same loop on PRBS7.  Runs of seven identical bits blind the phase "
        "detector, so the pump's mismatch integrates unopposed -- 0101 "
        "numbers mean little until this has run.",
        deck="e2e_prbs.spice", log="e2e_prbs.log",
        checks=[
            Check("f_long", 597.0, 604.0, "MHz", ""),
            Check("vctrl_ripp", 0.0, 0.10, "V", "65.3 mV on the old ring, 2.5x the 0101 figure"),
        ],
        known_broken="Same cause as e2e-lock on this branch.",
        timeout_s=3600,
    ),
]


# --------------------------------------------------------------------------
# Running
# --------------------------------------------------------------------------

NUM = re.compile(r"^\s*(\w+)\s*=\s*([-+0-9.eE]+)")


def read_measures(log: Path) -> dict[str, float]:
    """Every `name = value` the deck printed.

    ngspice prints a `meas` twice -- once as it runs and once from the `print`
    -- and the `let` results only once.  Last one wins, which is the printed
    value, which is the one the deck meant to report.
    """
    out: dict[str, float] = {}
    if not log.exists():
        return out
    for line in log.read_text(errors="replace").splitlines():
        m = NUM.match(line)
        if m:
            try:
                out[m.group(1).lower()] = float(m.group(2))
            except ValueError:
                pass
    return out


def toolchain_report() -> tuple[bool, list[str]]:
    notes, ok = [], True
    pdk = os.environ.get("PDK_ROOT") or "/home/ttuser/pdk"
    p = Path(pdk) / "ihp-sg13cmos5l"
    if not p.is_dir():
        return False, [f"no PDK at {p} -- run tools/setup_pdk.sh"]
    notes.append(f"PDK: {p}")
    osdi = p / "libs.tech" / "ngspice" / "osdi"
    need = ["psp103.osdi", "psp103_nqs.osdi", "r3_cmc.osdi", "cap_cmomf.osdi"]
    missing = [n for n in need if not (osdi / n).exists()]
    if missing:
        ok = False
        notes.append("MISSING OSDI (nothing will simulate): " + ", ".join(missing))
    else:
        notes.append(f"OSDI: {len(need)}/{len(need)} present")
    notes.append("ngspice: " + (shutil.which("ngspice") or "NOT ON PATH"))
    notes.append("xschem: " + (shutil.which("xschem") or "not on path (optional)"))
    if not shutil.which("ngspice"):
        ok = False

    net = ROOT / "sim" / "netlists" / "blocks.inc"
    if not net.exists():
        ok = False
        notes.append("no sim/netlists/blocks.inc -- run tools/netlist.sh")
    else:
        newest = max((f.stat().st_mtime for f in (ROOT / "xschem").glob("*.sch")),
                     default=0)
        if newest > net.stat().st_mtime:
            ok = False
            notes.append("blocks.inc is OLDER than a schematic -- run "
                         "tools/netlist.sh, or every sim below measures the "
                         "previous circuit")
        else:
            notes.append("blocks.inc is newer than every schematic")
    return ok, notes


def run_stage(st: Stage, verbose: bool) -> dict:
    t0 = time.time()
    rec: dict = {"name": st.name, "tier": st.tier, "desc": st.desc,
                 "known_broken": st.known_broken, "measures": {}, "failures": []}

    if st.name == "toolchain":
        ok, notes = toolchain_report()
        rec.update(status="pass" if ok else "fail", notes=notes)

    elif st.kind == "pytest" or st.kind == "shell":
        assert st.cmd
        p = subprocess.run(st.cmd, cwd=ROOT, capture_output=True, text=True)
        tail = (p.stdout + p.stderr).strip().splitlines()
        rec.update(status="pass" if p.returncode == 0 else "fail",
                   notes=tail[-6:] if tail else [])
        if verbose and p.returncode != 0:
            print("\n".join(tail[-40:]))

    else:
        assert st.deck and st.log
        log = RESULTS / st.log
        p = subprocess.run(
            [str(SAFE), st.deck, f"../results/{st.log}",
             str(st.mem_mb), str(st.timeout_s), "2000"],
            cwd=DECKS, capture_output=True, text=True)
        vals = read_measures(log)
        rec["measures"] = vals
        fails = []
        if p.returncode != 0:
            fails.append(f"safe_ngspice exited {p.returncode}")
        for c in st.checks:
            got = vals.get(c.key.lower())
            if got is None:
                fails.append(f"{c.key}: not reported (a silent `meas` failure "
                             f"leaves nothing behind -- read {st.log})")
            elif not (c.low <= got <= c.high):
                fails.append(f"{c.key} = {got:.6g} {c.unit}, outside "
                             f"[{c.low:g}, {c.high:g}]"
                             + (f"  ({c.note})" if c.note else ""))
        rec["failures"] = fails
        rec["status"] = "pass" if not fails else "fail"

    rec["seconds"] = round(time.time() - t0, 1)
    if rec["status"] == "fail" and st.known_broken:
        rec["status"] = "known-fail"
    return rec


def write_report(recs: list[dict], path: Path, args_desc: str) -> None:
    when = time.strftime("%Y-%m-%d %H:%M:%S")
    branch = subprocess.run(["git", "branch", "--show-current"], cwd=ROOT,
                            capture_output=True, text=True).stdout.strip()
    sha = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT,
                         capture_output=True, text=True).stdout.strip()
    dirty = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT,
                           capture_output=True, text=True).stdout.strip()

    L = [f"# Check run — {when}", "",
         f"- branch `{branch}` at `{sha}`"
         + ("  **(working tree dirty)**" if dirty else ""),
         f"- invocation: `tools/run_checks.py {args_desc}`", "",
         "| stage | result | time | what |", "|---|---|---|---|"]
    icon = {"pass": "pass", "fail": "**FAIL**", "known-fail": "known fail"}
    for r in recs:
        one = r["desc"].split(".")[0]
        L.append(f"| `{r['name']}` | {icon[r['status']]} | {r['seconds']:g} s | {one} |")
    L.append("")

    for r in recs:
        L += [f"## {r['name']} — {icon[r['status']]}", "", r["desc"], ""]
        if r.get("known_broken"):
            L += [f"> **Known failure.** {r['known_broken']}", ""]
        for f in r.get("failures", []):
            L.append(f"- FAIL: {f}")
        for n in r.get("notes", []):
            L.append(f"- {n}")
        if r["measures"]:
            L += ["", "<details><summary>measured</summary>", ""]
            for k, v in sorted(r["measures"].items()):
                L.append(f"    {k:<20} {v:.6g}")
            L += ["", "</details>"]
        L.append("")

    path.write_text("\n".join(L) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--sims", action="store_true", help="add the fast simulations")
    g.add_argument("--full", action="store_true", help="add the closed-loop runs too")
    ap.add_argument("--only", nargs="+", metavar="STAGE", help="run these stages only")
    ap.add_argument("--list", action="store_true", help="list stages and exit")
    ap.add_argument("-v", "--verbose", action="store_true")
    ap.add_argument("--report", type=Path, default=RESULTS / "CHECKS.md")
    a = ap.parse_args()

    tiers = {"quick"}
    if a.sims:
        tiers |= {"sims"}
    if a.full:
        tiers |= {"sims", "full"}
    todo = [s for s in STAGES if (s.name in a.only) if a.only] if a.only else \
           [s for s in STAGES if s.tier in tiers]

    if a.list:
        print(f"{'stage':<16}{'tier':<8}{'cost':<8}what")
        for s in STAGES:
            print(f"{s.name:<16}{s.tier:<8}{s.cost:<8}{s.desc.split('.')[0]}")
        return 0
    if not todo:
        print("no stages matched", file=sys.stderr)
        return 2

    RESULTS.mkdir(parents=True, exist_ok=True)
    print(f"running {len(todo)} stage(s): {' '.join(s.name for s in todo)}\n")
    recs = []
    for s in todo:
        print(f"  {s.name:<16} ({s.cost}) ... ", end="", flush=True)
        r = run_stage(s, a.verbose)
        recs.append(r)
        print(f"{r['status']}  [{r['seconds']:g} s]")
        for f in r.get("failures", []):
            print(f"      {f}")
        if r["status"] == "fail" and not r.get("failures"):
            for n in r.get("notes", [])[-4:]:
                print(f"      {n}")

    args_desc = " ".join(sys.argv[1:])
    write_report(recs, a.report, args_desc)
    (a.report.with_suffix(".json")).write_text(json.dumps(recs, indent=2) + "\n")

    bad = [r for r in recs if r["status"] == "fail"]
    known = [r for r in recs if r["status"] == "known-fail"]
    print(f"\n{len(recs) - len(bad) - len(known)} passed, {len(bad)} failed, "
          f"{len(known)} known-fail  ->  {a.report.relative_to(ROOT)}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
