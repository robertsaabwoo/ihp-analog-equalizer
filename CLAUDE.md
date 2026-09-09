# ihp-analog-equalizer — working notes for contributors

An IHP SG13CMOS5L port of a sky130 CTLE + reference-less bang-bang CDR
receiver, for the Chipalooza analog design challenge. xschem + ngspice.

This file is the operating manual for anyone — human or agent — working in this
repository. It exists because the compute environment has hard limits that are
not obvious, and because the toolchain has several failure modes that produce a
plausible wrong answer rather than an error.

**Read [`docs/SIMULATION_TRAPS.md`](docs/SIMULATION_TRAPS.md) before writing a
deck.** Most of what will waste your day is in there.

---

## 1. Getting the toolchain up

```bash
tools/setup_pdk.sh      # both IHP PDKs + the Verilog-A models, ~15 min
. ./env.sh              # PDK_ROOT, PDK, and a sanity check
tools/netlist.sh        # schematics -> sim/netlists/blocks.inc
```

`setup_pdk.sh` installs **two** PDKs. That is not redundancy: `ihp-sg13cmos5l`
is an overlay whose model libraries and symbols are symlinks into a sibling
`ihp-sg13g2` checkout. It also compiles the PSP 103.6 Verilog-A models to OSDI,
without which no transistor simulates.

## 2. Compute budget — this constraint overrides convenience

The development VM has **7.8 GB of RAM and 4 CPUs**, and an unguarded ngspice
has previously exhausted host memory and forced a reboot. The rules below are
not stylistic:

- **Never run two ngspice processes at once.** Strictly sequential.
- **Always wrap ngspice in `tools/safe_ngspice.sh`** — it applies a hard
  `ulimit -v`, a wall-clock `timeout`, a `/proc/meminfo` watchdog and `nice`.
  `safe_ngspice.sh <deck> <log> [mem_mb] [timeout_s] [floor_mb]`
- **Never use a bare `write foo.raw`.** It stores every node at every
  timepoint, which is what exhausted memory. `save` an explicit vector list
  first, and pass an explicit vector list to `write`.
- A full CDR transient costs 7-20 minutes; a 6 µs run costs 20-25. Confirm
  before starting anything in that class.
- No parameter sweeps in the "launch N simulations" sense. Sweep *inside* one
  ngspice run with `alter`/`alterparam` and a `foreach` loop. The exception is
  the process corner, which is fixed by a `.lib` line at parse time and
  genuinely needs one run each — see `sim/run_ctle_ac.sh`.
- **numpy is not installed, and must not be.** Analysis scripts are pure
  stdlib.

## 3. Netlisting from the shell

```bash
. ./env.sh
cd xschem
xschem -n -s -x -q --rcfile ./xschemrc -o ../sim/netlists ctle_cdr_rx_lvs.sch
```

or just `tools/netlist.sh`, which does that and then checks the result.

`-r` is `--no_readline`, **not** an rcfile flag. Passing it silently produces a
truncated netlist with "Symbol not found" for everything, and exits zero.

## 4. The schematics are generated, not hand-edited

`xschem/*.sch` are produced by `tools/port_from_sky130.py` from the sky130
original. **Editing them directly will be undone the next time the port runs.**

To change a device size, edit the `SIZING` table in that script and re-run it.
The table is the design record: every entry carries the measurement that
justifies it. To make a structural change, add it to `POST_PORT_EDITS`.

Two cells are native to this repository and are not generated:
`xschem/inv_cp.*` (replaces a sky130 standard cell) and
`xschem/ibias_mirror.*` (new — the current-mirror bias, see §6).

After any port run, re-check that the circuit did not move:

```bash
tools/netlist.sh
tools/check_port_equivalence.py <sky130 netlist> sim/netlists/ctle_cdr_rx_lvs.spice
```

That compares the two netlists as graphs — terminal by terminal, allowing for
auto-generated net renaming — and is the only thing standing between a symbol
swap and a silently rewired schematic. xschem connects by *coordinate*.

## 5. What must not be used

SG13CMOS5L is CMOS-only with four thin metals and one thick. It has **no MIM
capacitor, no HBTs, no inductors, no deep n-well and no Schottky diodes.** The
SG13G2 symbol library is on the search path (CMOS5L symlinks into it), so it is
entirely possible to draw a `cap_cmim` that simulates correctly and cannot be
manufactured. The allowed device set is whatever has a symbol in
`$PDK_ROOT/ihp-sg13cmos5l/libs.tech/xschem/sg13cmos5l_pr/`.

`test/test_device_set.py` enforces this.

## 6. Layout of the repo

| path | what |
|---|---|
| `xschem/` | the design — 24 cells, `ctle_cdr_rx.sch` is the top |
| `xschem/ctle_cdr_rx_lvs.sch` | one-instance wrapper; netlist THIS to get a `.subckt` |
| `tools/port_from_sky130.py` | the port, and the sizing table that is the design record |
| `tools/check_port_equivalence.py` | netlist-graph comparison against the sky130 source |
| `tools/setup_pdk.sh` | toolchain install, including the Verilog-A build |
| `tools/safe_ngspice.sh` | the resource guard. Use it. |
| `char/` | device characterisation — where the process constants come from |
| `sim/decks/` | testbenches; `*_p.inc` are parameterised copies for sweeping |
| `sim/results/` | logs the numbers in the README were read out of |
| `docs/DESIGN.md` | what was measured, how, and what each number means |
| `docs/SIMULATION_TRAPS.md` | read this first |
| `docs/PORTING.md` | what changed from sky130 and why |
| `test/` | repository-consistency tests; no PDK or simulator needed |

## 7. Conventions

- Commit and push as you go — work has been lost to a crash on this machine
  before.
- Record *negative* results. Several dead ends in the sky130 original were
  re-attempted across sessions because the failure had not been written down.
  The CTLE search in `docs/DESIGN.md` is written up including the three
  directions that did not work.
- Any number in `README.md` or `docs/` must be traceable to a log in
  `sim/results/` or a deck in `sim/decks/`. If you cannot point at the run,
  do not write the number down.
- If a measurement is not done, say "not measured" rather than estimating.
  The sky130 project's most valuable habit was distinguishing the two.
