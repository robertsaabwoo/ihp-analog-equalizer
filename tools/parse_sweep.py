#!/usr/bin/env python3
"""Turn an ngspice `print`-per-point sweep log into a table.

ngspice prints one scalar per line inside a foreach loop, and the loop
variables have to be printed as vectors too because a `shell echo` label is
buffered on a different stream and lands somewhere else in the file entirely.
This collects the scalars back into rows.

    parse_sweep.py <log> <key1,key2,...> [--last KEY]

A row is emitted every time KEY (default: the last key given) is seen.  Keys
not seen since the previous row carry forward, which is what makes a two-print
point -- operating point first, ac results second -- come out as one row.

Pure stdlib, like every analysis script here: the VM this runs on has no numpy
and must not get one (see CLAUDE.md).
"""
import re
import sys

NUM = r"(-?(?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)"


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    path, keys = sys.argv[1], sys.argv[2].split(",")
    last = keys[-1]
    if "--last" in sys.argv:
        last = sys.argv[sys.argv.index("--last") + 1]

    pat = re.compile(r"\b(" + "|".join(re.escape(k) for k in keys) + r")\s*=\s*" + NUM)
    rows, cur = [], {}
    for m in pat.finditer(open(path).read()):
        cur[m.group(1)] = float(m.group(2))
        if m.group(1) == last:
            rows.append(dict(cur))

    print("".join(f"{k:>10}" for k in keys))
    for r in rows:
        print("".join(f"{r.get(k, float('nan')):10.4g}" for k in keys))
    print(f"\n{len(rows)} points")
    return 0


if __name__ == "__main__":
    sys.exit(main())
