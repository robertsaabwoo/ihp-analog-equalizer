#!/usr/bin/env python3
"""Generate a PRBS7 NRZ pattern as an ngspice PWL source.

    tools/gen_prbs.py <out.inc> <duration_s> [--ui 1.665e-9] [--edge 10e-12]

PRBS7 is x^7 + x^6 + 1: a 127-bit maximal-length sequence whose longest run of
identical bits is seven. That run length is the point of the exercise. An
Alexander phase detector is *blind* during a run — there is no data transition
to compare the clock against — so whatever the charge pump does when neither
phase should be firing gets integrated for up to seven unit intervals at a
time. On alternating 0101 data that never happens, which is why 0101 is the
easy case and why every closed-loop number measured on it needs this run
before it means anything.

Two traps this script exists to avoid, both of which cost the sky130 project
real time:

  * **A PWL source holds its last value forever.** Run a 6 µs transient
    against a 3 µs pattern and the back half is flat DC: the detector goes
    blind, the loop wanders, and the run produces a "jitter" number that is
    really a measurement of the data source running out. This script takes the
    transient duration as an argument and generates past the end of it, and
    prints the bit count so the deck can be checked against it.

  * **The bit rate is not the square-wave rate.** 0101 data at 600.6 Mb/s is a
    300.3 MHz square wave. Getting that factor of two wrong cost three
    sessions on the original project. Here the UI is the bit period, full stop.

Pure stdlib; the VM this runs on has no numpy and must not get one.
"""
import argparse
import sys


def prbs7(n):
    """n bits of PRBS7 (x^7 + x^6 + 1), MSB-first from an all-ones seed."""
    reg = 0x7F
    out = []
    for _ in range(n):
        bit = ((reg >> 6) ^ (reg >> 5)) & 1
        reg = ((reg << 1) | bit) & 0x7F
        out.append(bit)
    return out


def longest_run(bits):
    best = run = 1
    for a, b in zip(bits, bits[1:]):
        run = run + 1 if a == b else 1
        best = max(best, run)
    return best


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("out")
    ap.add_argument("duration", type=float, help="transient length in seconds")
    ap.add_argument("--ui", type=float, default=1.665e-9)
    ap.add_argument("--edge", type=float, default=10e-12)
    ap.add_argument("--margin", type=float, default=1.10,
                    help="generate this much more than the transient needs")
    a = ap.parse_args()

    nbits = int(a.duration * a.margin / a.ui) + 8
    bits = prbs7(nbits)

    # PWL of a 0/1 logical waveform; the deck scales it to real levels with a
    # behavioural source, so the amplitude and common mode stay in the deck
    # where they can be swept.
    pts, prev = [(0.0, float(bits[0]))], bits[0]
    for i, b in enumerate(bits[1:], start=1):
        if b != prev:
            t = i * a.ui
            pts.append((t - a.edge / 2, float(prev)))
            pts.append((t + a.edge / 2, float(b)))
            prev = b
    pts.append((nbits * a.ui, float(prev)))

    with open(a.out, "w") as f:
        f.write(f"* PRBS7, {nbits} bits at UI = {a.ui:g} s "
                f"= {nbits * a.ui * 1e6:.3f} us of data.\n")
        f.write(f"* Longest run of identical bits: {longest_run(bits)}.\n")
        f.write(f"* Generated for a {a.duration * 1e6:.3f} us transient with "
                f"{(a.margin - 1) * 100:.0f} % margin -- a PWL source holds its\n")
        f.write("* last value forever, so running past the end of the pattern\n")
        f.write("* measures the data source running out, not the circuit.\n")
        f.write("Vdraw draw 0 PWL\n")
        for t, v in pts:
            f.write(f"+ {t:.6e} {v:.1f}\n")

    print(f"{a.out}: {nbits} bits = {nbits * a.ui * 1e6:.3f} us, "
          f"longest run {longest_run(bits)}, {len(pts)} PWL points")
    return 0


if __name__ == "__main__":
    sys.exit(main())
