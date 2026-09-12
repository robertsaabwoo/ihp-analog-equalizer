# Runner scripts

Ad-hoc scripts driving the investigation in `docs/HANDBOOK.md` §11, copied out
of the session scratchpad so they survive a reboot. Each re-ports the design
with a different `SIZING`, re-netlists, and runs one or more closed-loop decks.

**They edit `tools/port_from_sky130.py` in place and restore it at the end.**
If one is interrupted the design record is left mid-edit — check
`git diff tools/port_from_sky130.py` before trusting anything after a crash.

| script | what it was for |
|---|---|
| `chain9k.sh` | corner + floor + centring sweeps at 9000 Ω |
| `bisect.sh` / `fastbisect.sh` | four-way split of the lock failure (superseded) |
| `decisive.sh` | the run with a control that isolated the ring as the cause |
| `auto.sh` | widen the seed sweep, then the two closed-loop tests |
| `gain.sh` | reduced charge pump current — did not fix it |
| `ceil.sh` | 12000 Ω, undershot because the sweep lacked trim legs |
| `r10k.sh` | **10000 Ω — the one that locks on 0101** |
| `r105.sh` | 10500 Ω, both patterns — running at last checkpoint |
