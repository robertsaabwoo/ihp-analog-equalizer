#!/usr/bin/env python3
"""Bring the existing decks forward to the dual-loop netlist.

Two things change under the coarse loop, and both of them break a deck by
silently measuring the wrong node rather than by failing:

  * the CDR's loop filter output stops being the anonymous `net1` and becomes
    `vctrl`, because `add_coarse_loop` labels it -- the coarse loop is its
    second consumer and the node every measurement in docs/ already calls by
    that name.  A deck that still asks for `v(x1.x2.net1)` gets ngspice's
    "no such vector", which kills the whole `print` and not just that vector
    (trap 2.3), so at least this one is loud.

  * `vcoarse!` becomes a live node.  A deck written to measure the *fine* loop
    alone -- every existing e2e_* deck, and tools/capture_range.sh -- has to
    pin it, or the coarse loop quietly corrects whatever detuning the deck was
    applying and every point passes.  That one is silent, which is why it is
    done here by script and not by hand.

    tools/migrate_decks.py [--check]
"""
import argparse
import re
import sys
from pathlib import Path

DECKS = Path(__file__).resolve().parent.parent / "sim" / "decks"
PIN = """
* Pin the coarse trim.  This deck measures the fine loop on its own, and with
* vcoarse! free the coarse loop corrects whatever this deck is detuning --
* silently, and every point passes.  1.20 V is the trim fully OFF, which is
* where the coarse loop rests at nominal (docs/RING_DUAL_LOOP.md section 7.3).
.global vcoarse!
Vcrs vcoarse! 0 1.20
"""


# Renaming the loop filter output to `vctrl` did not just rename one net -- it
# renumbered every anonymous net in CDR after it, because xschem numbers them in
# order.  A deck that still says x1.x2.net2 now reads `up` where it used to read
# `down`, and x1.x2.net5 names a node that no longer exists.  One of those is
# silent and one kills the whole print (trap 2.3); neither is a good way to
# debug a loop that will not lock.
#
#   main            branch        what it is
#   x1.x2.net1  ->  x1.x2.vctrl   loop filter output
#   x1.x2.net2  ->  x1.x2.net1    charge pump `up`
#   x1.x2.net3  ->  x1.x2.net2    charge pump `down`
#   x1.x2.net4  ->  x1.x2.net3    ring output +
#   x1.x2.net5  ->  x1.x2.net4    ring output -
#
# Deeper paths (x1.x2.x1.netN, inside ring_oscillator) are untouched, and the
# literal "x1.x2.net" prefix cannot match them.
CDR_NETS = [("x1.x2.net1", "x1.x2.vctrl"),
            ("x1.x2.net2", "x1.x2.net1"),
            ("x1.x2.net3", "x1.x2.net2"),
            ("x1.x2.net4", "x1.x2.net3"),
            ("x1.x2.net5", "x1.x2.net4")]


def migrate(text):
    # Two passes through a placeholder, or net2->net1 would then be caught by
    # net1->vctrl and the whole chain would collapse onto one node.
    for i, (old, _) in enumerate(CDR_NETS):
        text = text.replace(old, f"@@{i}@@")
    for i, (_, new) in enumerate(CDR_NETS):
        text = text.replace(f"@@{i}@@", new)
    if "vcoarse!" not in text:
        text = re.sub(r"^(Vsub sub! 0 0\n)", r"\1" + PIN.lstrip("\n"),
                      text, count=1, flags=re.M)
    return text


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="report what would change and exit non-zero if any")
    a = ap.parse_args()
    dirty = []
    for f in sorted(DECKS.glob("e2e_*.spice")) + sorted(DECKS.glob("pd_*.spice")) \
            + sorted(DECKS.glob("vctrl_*.spice")):
        if f.name == "e2e_dual.spice":
            continue                      # written against the new netlist
        old = f.read_text()
        new = migrate(old)
        if new == old:
            continue
        dirty.append(f.name)
        if not a.check:
            f.write_text(new)
    if a.check:
        print("would change:", " ".join(dirty) or "nothing")
        return 1 if dirty else 0
    print("migrated:", " ".join(dirty) or "nothing")
    return 0


if __name__ == "__main__":
    sys.exit(main())
