#!/usr/bin/env python3
"""Apply a ring sizing (load resistance, trim width) to the design, in one auditable step.

    tools/apply_ring_sizing.py <Rload_ohm> <Wtr_um> [--dry-run]

Edits `SIZING` (ring_inverter R1/R2) and `TRIM_W` in tools/port_from_sky130.py, re-ports
`ring_inverter`, regenerates sim/netlists/blocks.inc, runs the unit tests, and prints the
resulting devices.  Also keeps sim/decks/ring_ct.inc -- the standalone ring used by every
cheap sweep -- in step with the design, or the sweeps stop describing the circuit.

Why this exists: the sizing is chosen by measurement (tools/pick_ring_sizing.py from the
ring_centre2 grid), and the application has four steps that must all happen together.
Doing them by hand at 3 a.m. is how a netlist and its sweeps drift apart.
"""
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = "/home/ttuser/ssh_analog/ttsky-analog-equalizer/xschem"


def edit(path, subs):
    text = path.read_text()
    for pat, repl in subs:
        new, n = re.subn(pat, repl, text, flags=re.M)
        if n != 1:
            raise SystemExit(f"{path}: {n} matches for {pat!r}, expected 1")
        text = new
    path.write_text(text)


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd))
    return subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True, **kw)


def main():
    if len(sys.argv) < 3:
        raise SystemExit(__doc__)
    rl, wt = int(float(sys.argv[1])), float(sys.argv[2])
    dry = "--dry-run" in sys.argv
    print(f"ring sizing -> Rload {rl} ohm, trim width {wt} um" + (" (dry run)" if dry else ""))
    if dry:
        return 0

    edit(ROOT / "tools/port_from_sky130.py", [
        (r'^\(\s*"ring_inverter", "R1"\): \{"R": \d+\},',
         f'("ring_inverter", "R1"): {{"R": {rl}}},') if False else
        (r'^    \("ring_inverter", "R1"\): \{"R": \d+\},',
         f'    ("ring_inverter", "R1"): {{"R": {rl}}},'),
        (r'^    \("ring_inverter", "R2"\): \{"R": \d+\},',
         f'    ("ring_inverter", "R2"): {{"R": {rl}}},'),
        (r'^TRIM_W = [\d.]+', f'TRIM_W = {wt}'),
    ])
    # the standalone ring used by every cheap sweep must match the design
    edit(ROOT / "sim/decks/ring_ct.inc", [
        (r'^\.param Rload=\d+', f'.param Rload={rl}'),
        (r'^\.param Wtr=[\d.]+ Ltr=([\d.]+)', rf'.param Wtr={wt} Ltr=\1'),
    ])

    r = run(["python3", "tools/port_from_sky130.py", "--src", SRC, "--dst", "xschem",
             "--cells", "ring_inverter"])
    print(r.stdout.strip()[-400:] or r.stderr.strip()[-400:])
    if r.returncode:
        raise SystemExit("port failed")
    r = run(["bash", "tools/netlist.sh"])
    print((r.stdout or r.stderr).strip().splitlines()[-1])
    if r.returncode:
        raise SystemExit("netlist failed")
    r = run(["python3", "-m", "pytest", "-q", "test/"])
    print((r.stdout or r.stderr).strip().splitlines()[-1])
    if r.returncode:
        raise SystemExit("tests failed")

    blocks = (ROOT / "sim/netlists/blocks.inc").read_text()
    body = blocks[blocks.index(".subckt ring_inverter "):]
    body = body[:body.index(".ends")]
    print("\nring_inverter now:")
    for line in body.splitlines():
        if line.startswith(("XR", "XT")):
            print("  " + line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
