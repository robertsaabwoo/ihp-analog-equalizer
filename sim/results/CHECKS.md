# Check run — 2026-09-12 15:25:47

- branch `ring-coarse-tune` at `f425530`  **(working tree dirty)**
- invocation: `tools/run_checks.py `

| stage | result | time | what |
|---|---|---|---|
| `repo-tests` | pass | 1.8 s | 48 consistency tests: manufacturable device set, channel geometry inside the PSP models' range, hierarchy, the port's passive arithmetic, and the generated coarse-loop schematic against its include |
| `toolchain` | pass | 0 s | Is there a PDK, were the Verilog-A models compiled to OSDI, and is the netlist newer than the schematics it came from?  Nothing simulates without the OSDI build, and a stale netlist is the quiet way to measure last week's circuit |

## repo-tests — pass

48 consistency tests: manufacturable device set, channel geometry inside the PSP models' range, hierarchy, the port's passive arithmetic, and the generated coarse-loop schematic against its include.  No PDK, no simulator, no network.

- ................................................                         [100%]
- 48 passed in 1.08s

## toolchain — pass

Is there a PDK, were the Verilog-A models compiled to OSDI, and is the netlist newer than the schematics it came from?  Nothing simulates without the OSDI build, and a stale netlist is the quiet way to measure last week's circuit.

- PDK: /home/ttuser/pdk/ihp-sg13cmos5l
- OSDI: 4/4 present
- ngspice: /usr/local/bin/ngspice
- xschem: /usr/local/bin/xschem
- blocks.inc is newer than every schematic

