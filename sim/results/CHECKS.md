# Check run — 2026-09-12 15:34:09

- branch `ring-coarse-tune` at `adeca5f`  **(working tree dirty)**
- invocation: `tools/run_checks.py --sims`

| stage | result | time | what |
|---|---|---|---|
| `repo-tests` | pass | 1.8 s | 48 consistency tests: manufacturable device set, channel geometry inside the PSP models' range, hierarchy, the port's passive arithmetic, and the generated coarse-loop schematic against its include |
| `toolchain` | pass | 0 s | Is there a PDK, were the Verilog-A models compiled to OSDI, and is the netlist newer than the schematics it came from?  Nothing simulates without the OSDI build, and a stale netlist is the quiet way to measure last week's circuit |
| `char-caps` | pass | 3.1 s | Passive densities |
| `cap-leak` | pass | 3 s | Gate leakage of the candidate hold capacitors |
| `trim-r` | pass | 3.1 s | The coarse trim leg measured as a dc resistance |
| `cp-current` | pass | 6.1 s | Charge pump and loop filter |
| `vco-rsweep` | pass | 138.9 s | Ring frequency against load resistance, at the top of the fine range |
| `coarse-tb` | pass | 6.1 s | The coarse loop open-loop, with vctrl driven by hand: cold start, search rate, wrap span, and the null |
| `vco-ct-centre` | pass | 330.9 s | Where the coarse trim has to sit at nominal |

## repo-tests — pass

48 consistency tests: manufacturable device set, channel geometry inside the PSP models' range, hierarchy, the port's passive arithmetic, and the generated coarse-loop schematic against its include.  No PDK, no simulator, no network.

- ................................................                         [100%]
- 48 passed in 0.94s

## toolchain — pass

Is there a PDK, were the Verilog-A models compiled to OSDI, and is the netlist newer than the schematics it came from?  Nothing simulates without the OSDI build, and a stale netlist is the quiet way to measure last week's circuit.

- PDK: /home/ttuser/pdk/ihp-sg13cmos5l
- OSDI: 4/4 present
- ngspice: /usr/local/bin/ngspice
- xschem: /usr/local/bin/xschem
- blocks.inc is newer than every schematic

## char-caps — pass

Passive densities.  Every geometry the port solves comes from these, so a wrong constant here is a wrong constant in every resistor and capacitor in the design.


<details><summary>measured</summary>

    ccmomf               1.287e-13
    ccmomi               1.00155e-13
    cmoscapn06           1.17803e-12
    cmoscapn12           1.26717e-12
    cmoscapp06           3.89329e-13
    rh                   14326.9
    rp                   2654.53
    rs                   78.3077

</details>

## cap-leak — pass

Gate leakage of the candidate hold capacitors.  This is the measurement that disqualified moscap_n from the coarse loop's integrator: I/C is volts per second of drift and does not improve by scaling the capacitor.


<details><summary>measured</summary>

    c_hvn                5.01434e-13
    c_mom                4.94414e-13
    c_mosn               4.18703e-12
    c_mosp               1.2004e-12
    i_hvn                -0
    i_mom                4.2e-13
    i_mosn               7.73463e-10
    i_mosp               1.36993e-11

</details>

## trim-r — pass

The coarse trim leg measured as a dc resistance.  Pairs with 'vco-ct': the leg matches the hand arithmetic to 1 % here and delivers 43 % of it in the ring, because a pMOS is only a resistor while it stays in triode.


<details><summary>measured</summary>

    r_alone              -8000.06
    reff                 -1801.01
    vg_v                 0
    w_um                 8

</details>

## cp-current — pass

Charge pump and loop filter.  The 11.0 % up/down mismatch this measures is what drives vctrl one-signed when the loop is out of band, which is the entire reason the coarse loop has to search rather than trim (docs/RING_DUAL_LOOP.md section 2).


<details><summary>measured</summary>

    bias_n               0.286808
    bias_p               0.769898
    c_filt               5.59534e-13
    i_down               -7.96512e-07
    i_leak               1.97153e-11
    i_up                 8.95195e-07
    t_hi                 2.19294e-08
    t_lo                 1.07388e-08

</details>

## vco-rsweep — pass

Ring frequency against load resistance, at the top of the fine range.  Splits the stage delay into the part the coarse trim can move and the part it cannot: 61.0 ps + 13.100 ps per kilohm.


<details><summary>measured</summary>

    fosc                 9.58158e+08
    p_rload              3500
    ring_swing           0.8233
    rmax                 1.13891
    rmin                 0.315605
    t1                   6.292e-09
    t2                   2.71654e-08

</details>

## coarse-tb — pass

The coarse loop open-loop, with vctrl driven by hand: cold start, search rate, wrap span, and the null.  Seconds per question where the closed-loop equivalent is hours.


<details><summary>measured</summary>

    d_520                2.39271
    d_560                0.768504
    d_600                0.0594857
    d_640                -0.666382
    d_680                -2.46103
    n52a                 0.272886
    n52b                 0.339882
    n56a                 0.226311
    n56b                 0.247829
    n60a                 0.217509
    n60b                 0.219174
    n64a                 0.237729
    n64b                 0.21907
    n68a                 0.319252
    n68b                 0.250343
    search_mv_us         20.1376
    search_span          1.07809
    v_park               1.10026
    vc_a                 0.901631
    vc_b                 0.700255
    vc_hi                1.20071
    vc_lo                0.122618

</details>

## vco-ct-centre — pass

Where the coarse trim has to sit at nominal.  Also says whether the trim is centred -- one whose nominal is at either end has its range on one side only, and the corner sweep would still pass while half the silicon fell off the end.


<details><summary>measured</summary>

    fosc                 7.94764e+08
    p_vcrs               0.15
    p_vctrl              0.7
    swing                0.972722
    t1                   7.58521e-09
    t2                   3.27499e-08
    vmax                 1.16573
    vmin                 0.193012

</details>

