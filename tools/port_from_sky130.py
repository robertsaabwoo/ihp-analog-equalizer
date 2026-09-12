#!/usr/bin/env python3
"""Port xschem schematics from sky130 (Tiny Tapeout) to IHP SG13CMOS5L (Chipalooza).

The source design is https://github.com/robertsaabwoo/ttsky-analog-equalizer —
a CTLE + reference-less bang-bang CDR receiver drawn in sky130 at 1.8 V.
This script rewrites the xschem source files onto the SG13CMOS5L device set at
1.2 V.  It is deliberately a *script* and not a one-off hand edit, because:

  * the transform has to be re-runnable when the sky130 side changes;
  * every sizing decision then lives in one auditable table (SIZING below)
    instead of being scattered through 22 schematic files;
  * a mechanical transform cannot silently rewire a schematic, which a hand
    edit of xschem's coordinate-based netlisting very easily can.

Why the transform is safe
-------------------------
xschem connects instances by *geometry*: a pin connects to whatever wire or
label sits at its absolute coordinate.  Swapping a symbol therefore rewires the
circuit unless the new symbol's pins sit at the same offsets.  They do:

    sky130_fd_pr/nfet_01v8   D(20,-30) G(-20,0) S(20,30) B(20,0)
    sg13cmos5l_pr/sg13_lv_nmos   D(20,-30) G(-20,0) S(20,30) B(20,0)   identical
    sky130_fd_pr/pfet_01v8   D(20,30)  G(-20,0) S(20,-30) B(20,0)
    sg13cmos5l_pr/sg13_lv_pmos   D(20,30)  G(-20,0) S(20,-30) B(20,0)  identical
    sky130_fd_pr/cap_mim_m3_1  c0(0,-30) c1(0,30)
    sg13cmos5l_pr/cap_cmomf    c0(0,-30) c1(0,30)                      identical
    sky130_fd_pr/res_high_po   P(0,-30) M(0,30) B(-20,0)
    sg13cmos5l_pr/rhigh        P(0,-30) M(0,30)      B becomes a parameter

Two cases need more than a name swap and are handled explicitly:

  * ``nfet3_01v8``/``pfet3_01v8`` are 3-pin symbols whose bulk is the ``body=``
    *parameter*.  The IHP symbol has a real B pin at (20,0), so the script
    emits a ``lab_wire`` at that pin's transformed coordinate carrying the old
    ``body=`` net.  Connectivity is preserved, not guessed.
  * ``res_high_po``'s B pin disappears (IHP carries the body as ``body=sub!``).
    Any label left at that coordinate is harmless — it is VSS, which is the
    substrate — so it is left in place rather than risk deleting a label that
    something else touches.

Run:  python3 tools/port_from_sky130.py --src <ttsky repo>/xschem --dst xschem
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

# --------------------------------------------------------------------------
# Process constants, all measured on this machine, not taken from datasheets.
# See char/ for the decks and char/RESULTS.md for the runs these came from.
# --------------------------------------------------------------------------

SKY_RSH_HIGH_PO = 319.8  # ohm/sq, sky130 res_high_po
SKY_MIM_DENSITY = 2.0e-15  # F/um^2, sky130 cap_mim_m3_1

# IHP rhigh, from char/caps.spice: W=1u L=10u measured 14.327 kohm.
# The PDK's own expression is R = 1.6e-4/w + 1360*l/(w - 0.04u) for b=0.
IHP_RHIGH_SHEET = 1360.0  # ohm/sq
IHP_RHIGH_DW = 0.04e-6  # m, width bias
IHP_RHIGH_RC = 1.6e-4  # ohm*m, contact term

# IHP cap_cmomf, from char/caps.spice: 10u x 10u measured 128.70 fF.
IHP_CMOMF_DENSITY = 1.287e-15  # F/um^2 at mmin=1 mmax=4

MIN_L_LV = 0.13  # um
MIN_W_LV = 0.15  # um

# --------------------------------------------------------------------------
# Sizing overrides.
#
# The first pass of this port kept every W and L exactly as drawn in sky130,
# which is the honest starting point but not the answer: the supply drops from
# 1.8 V to 1.2 V, so a device that had 1.35 V of overdrive now has 0.75 V, and
# every stage that was sized for a current is delivering roughly half of it.
#
# Each entry below is a deliberate re-size with a reason.  Anything not listed
# is ported unchanged apart from the Lmin remap.  Keyed by (cell, instance).
# --------------------------------------------------------------------------

# The coarse trim leg, one pMOS across each ring load resistor.  See
# add_coarse_trim() below and docs/RING_DUAL_LOOP.md section 4.1: the width was
# swept in the ring (vco_ct.spice) rather than computed, because a pMOS across
# the load is only a resistor while it stays in triode.  W = 4 um gives
# 1.292:1 of centre-frequency range against the 1.254:1 the corner sweep asks
# for, and keeps the ring node swinging 0.93-1.01 V at every setting.
TRIM_W = 4.0
TRIM_L = 1.0

SIZING: dict[tuple[str, str], dict] = {

    # ---------------------------------------------------------------- CTLE
    # Measured in sim/decks/ctle_tune*.spice; the search and its conclusion
    # are written up in docs/DESIGN.md "The CTLE at 1.2 V".
    #
    # The short version.  The gain of a resistively loaded differential pair is
    #
    #     gm * Rload  =  (gm/Id) * (Id * Rload)  =  (gm/Id) * dVload
    #
    # and dVload -- the DC drop across the load resistor -- is what the supply
    # buys you.  sky130 spent up to 0.65 V of its 1.8 V on it.  On 1.2 V there
    # is about 0.45 V available before the input pair's drain falls below its
    # gate by a threshold and the pair enters triode, at which point the gain
    # does not degrade gracefully, it collapses.  Current is not the lever:
    # swept from 65 uA to 620 uA it moved the Nyquist gain by 2 dB.  The load
    # resistance is, and only together with a current bias -- 2.5k to 3.5k took
    # it from 11.9 dB to 13.2 dB.  The final figure is 12.79 dB against
    # sky130's 13.32 dB (see the fingering note below for the last half dB).
    #
    # What also changed materially is the tail.  At the sky130 sizes the tail
    # device sat in triode at every bias -- drain at 30-135 mV -- so it was a
    # resistor, not a current source, and the bias current was set by the input
    # pair rather than by vbias.  Halving its width and doubling its length
    # makes it a current source again; the input common mode that goes with
    # this sizing is 0.70 V, and raising it further only pushes the pair into
    # triode from the other side.
    # Fingered so that w/ng stays inside the PSP model's validated width range,
    # 0.15-10 um -- W in that header is per finger, because the device
    # subcircuit computes its diffusion areas from w/ng.  ngspice evaluates a
    # 30 um single-finger device perfectly happily and returns extrapolated
    # numbers; nothing in the flow objects.  test_device_geometry.py does.
    # Fingering is also simply what a 30 um transistor looks like in layout.
    ("CTLE", "M1"): {"W": 30, "L": 0.2, "nf": 6},   # input pair, 5 um/finger
    ("CTLE", "M4"): {"W": 30, "L": 0.2, "nf": 6},
    ("CTLE", "M2"): {"W": 40, "L": 1.0, "nf": 8},   # tail, 5 um/finger
    ("CTLE", "R1"): {"R": 3500},             # load; sets dVload with Itail/2
    ("CTLE", "R2"): {"R": 3500},
    ("CTLE", "R3"): {"R": 900},              # degeneration; sets the boost
    ("CTLE", "R4"): {"R": 900},
    # Degeneration capacitor.  Bigger than the scaled sky130 value because the
    # zero has to sit on the channel pole at 63.7 MHz and Rdeg came down:
    # f_zero = 1/(4*pi*Ccap*Rdeg) = 1/(4*pi*1.6p*900) = 55 MHz.
    # 1.6 pF of cap_cmomf is 1243 um^2, which is the price of having no MIM.
    ("CTLE", "CS"): {"C": 1600e-15},

    # ------------------------------------------------------- ring oscillator
    # Measured in sim/decks/vco_range.spice and vco_tune*.spice; written up in
    # docs/DESIGN.md "The ring oscillator".
    #
    # This is the one change the port could not avoid making.  A bang-bang
    # phase detector is phase-only -- it has no frequency acquisition -- so a
    # ring that cannot reach the baud rate never locks, at any control voltage.
    # The tuning range is a functional requirement, not a performance number.
    #
    # sky130 reached 514-621 MHz at tt/27 C against 600.6 Mb/s: 3 % of margin,
    # which is why it failed at 125 C and at low supply, and which that project
    # characterised and accepted.  Ported unchanged to 1.2 V the same ring
    # reaches 424-554 MHz -- below the baud rate, so it does not lock at all.
    #
    # The frequency is set by the load resistance against the capacitance on
    # the output node, and that capacitance is dominated by the input pair's
    # gate: sweeping vctrl over its whole range moves the frequency by only
    # 1.3:1, because above the point where oscillation starts the ring is
    # RC-limited rather than current-starved.  Shortening the input pair from
    # 1.0 um to 0.9 um moves the whole curve from 424-554 MHz to 538-630 MHz,
    # which puts 600.6 MHz at vctrl = 0.60 V -- near the middle of the usable
    # range instead of above the top of it.
    #
    # 0.9 um rather than something shorter because the range is narrow either
    # way and centring matters more than headroom: 0.8 um gives 613-723 MHz,
    # which puts the baud rate below the point where the ring starts at all.
    #
    # That reasoning was right for a ring with one knob and is wrong for a ring
    # with two.  With the coarse trim (add_coarse_trim below) centring is the
    # coarse loop's job, and what the pair's length buys instead is the part of
    # the stage delay the trim cannot reach.  vco_rsweep.spice splits it:
    #
    #     stage delay = 61.0 ps + 13.100 ps per kilohm of load
    #
    # and at tt / 125 C / 1.08 V two thirds of the delay is that fixed 61 ps,
    # which is why the trimmed 0.9 um ring still reached only 573.7 MHz there
    # against a 600.6 MHz baud rate.  ring_lin.spice sweeps the length at the
    # two binding corners -- hot and low-supply with the trim on, cold and
    # high-supply with the trim off:
    #
    #     Lin       hot/low, trim ON    cold/high, trim OFF
    #     0.9 um       573.7 MHz             367.5 MHz
    #     0.7 um       710.4                 462.7
    #     0.5 um       960.6                 601.2
    #     0.13 um     1925.5                 962.2
    #
    # The ring has to bracket 600.6 MHz from both sides.  0.9 um cannot reach
    # it from below at the hot corner; 0.5 um and shorter cannot get *under* it
    # at the cold corner, where with the trim entirely off the ring is already
    # at 601 MHz.  0.7 um is the only swept value that clears both, and it does
    # so by 18 % at the top and 23 % at the bottom.
    ("ring_inverter", "M1"): {"W": 3, "L": 0.7},
    ("ring_inverter", "M4"): {"W": 3, "L": 0.7},

    # The load is 10000 ohm, and the number that set it is not the one that
    # first looked decisive.
    #
    # It went to 9000 for the reasons below -- the trim leg only speeds the ring
    # up, so the poly resistor must sit at the slow end of the span, and the
    # ring's floor goes as 1/R.  Both are still true.  What 9000 also did was
    # put the baud rate at 88 % of the ring's ceiling, on the steep rise of the
    # tuning curve, and there the closed loop does not hold: measured 667.9 MHz
    # with vctrl walking away, for two days of wrong hypotheses.
    #
    # Where the baud rate sits relative to the CEILING is the thing that
    # decides whether the loop locks (ring_ct_ceiling.spice, trim legs present,
    # trim off):
    #
    #     Rload    ceiling   baud/ceiling   vctrl    Kvco      closed loop
    #      9000    681.3       88 %         0.546    844       does NOT lock
    #     10000    639.9       94 %         0.595    720       LOCKS
    #     10500    621.5       97 %         0.642    302       (untested)
    #     11000    604.4       99 %         0.870     27       no headroom left
    #    (main's 0.9um/7355:  632.9, 95 %,  0.595,   522,      locks)
    #
    # 10000 reproduces main's operating profile almost exactly -- ceiling within
    # 1 %, the same 0.595 V lock point -- and measures 600.660 MHz, +0.0101 %.
    # Past the knee the loop has margin against the charge pump's 11 % current
    # mismatch; on the steep rise it does not, and a 40 mV startup kick becomes
    # a 50 MHz frequency error, outside the bang-bang capture range.
    #
    # The two reasons the load was raised in the first place:
    #
    # The trim leg only ever speeds the ring up, so the poly resistor has to
    # sit at the *slow* end of the span -- vcoarse = VDD then means the trim is
    # absent and the ring is the untrimmed circuit, and there is no state in
    # which the trim makes things worse.
    #
    # And the load alone sets how slow the ring can be held.  At low tail
    # current the ring is current-starved, the stage delay is C*swing/I with
    # swing = I*R, and the frequency is 1/RC -- independent of the current.
    # What stops it going slower is the swing dying, below about 0.15 V
    # single-ended.  So the floor goes as 1/R.  At 8000 ohm that floor was
    # 606.4 MHz at ss / 125 C / 1.32 V, 1.0 % *above* the baud rate: the one
    # corner in 27 the coarse loop could not cover was one where the ring could
    # not be made slow *enough*.  vco_ct_centre.spice agreed from the other
    # side -- at tt / 27 C / 1.2 V with the trim off the ring was already at
    # 685.6 MHz at vctrl = 0.60, so nominal sat at the slow rail.
    ("ring_inverter", "R1"): {"R": 10500},
    ("ring_inverter", "R2"): {"R": 10500},

    # ------------------------------ differential-to-single-ended converter
    # diff_amp_inv is instantiated twice: once as the ring oscillator's own
    # output stage, and once in the CDR to turn that differential output into
    # a single-ended clock.  Its bias pin is tied to VDD in both places, which
    # on 1.8 V was crude and survivable.
    #
    # On 1.2 V it breaks the second instance, and the reason is that the cell
    # cannot be cascaded with itself.  Measured in the closed loop
    # (sim/results/e2e_diag3.log):
    #
    #   ring's buffered output   common mode 0.336 V, 0.967 V pk-pk per leg
    #   the next stage's tail    0.111 V
    #   -> input pair Vgs = 0.336 - 0.111 = 0.225 V, below threshold
    #
    # So the stage that must convert 1.93 V of differential swing into a clock
    # has its input pair switched off for most of the cycle, and its output
    # sits static.  Everything downstream -- inverter_buffer, the output
    # inverter chain, the pin -- is then a static level: 67 nV at the pin
    # while the ring is happily oscillating at 1.84 V pk-pk behind it.
    #
    # The cell's own output common mode is what has to move.  It is set by the
    # drop across its load resistors, so shrinking both tails raises it.  From
    # sim/decks/d2s_size.spice, at an 0.85 V input common mode:
    #
    #   Wt1=2, Wt2=8/L=0.13   (as ported)  swings 0.07 - 1.13, CM 0.34 V
    #   Wt1=1, Wt2=1/L=1.0                 swings 0.57 - 1.20, CM 0.885 V
    #   Wt1=1, Wt2=2/L=1.0                 swings 0.35 - 1.17, CM 0.758 V
    #
    # There are two conditions to satisfy at once, and the first attempt met
    # only one of them.  The cell's output has to sit high enough to keep the
    # *next* copy of the same cell conducting -- that is the cascade condition,
    # and it is what the ported sizing failed.  But it also has to cross the
    # switching threshold of the CMOS inverter it eventually drives, roughly
    # 0.55 V at this supply.  Wt1=1/Wt2=1 fixed the first and broke the second:
    # the output common mode went to 0.88 V and its low excursion only reached
    # 0.57 V, so the inverter downstream moved 151 mV and never switched --
    # the same static output as before, now stuck at the other rail.
    #
    # Wt1=1/Wt2=2 meets both: 0.35 - 1.17 V crosses 0.55 V with margin at each
    # end, and 0.758 V of common mode still leaves the next input pair alive.
    #
    # One change fixes both instances, and it helps the first one too: with
    # less tail current its own input pair sees more Vgs, not less.
    ("diff_amp_inv", "M3"): {"W": 1, "L": 1.0},            # first-stage tail
    ("diff_amp_inv", "M4"): {"W": 2, "L": 1.0, "nf": 1},   # second-stage tail

    # ------------------------------------------------- CML latch (d_latch)
    # The Alexander detector is eight of these.  Measured in the closed loop,
    # its outputs -- the charge pump's up and down inputs -- sat at 1.2000 V
    # with 1.6 mV and 4.5 mV of movement: both switches held on, the pump
    # delivering only its own mismatch current, the loop open.
    #
    # Two causes, and they are the two that broke diff_amp_inv:
    #
    #   The tail was drawn at L = 0.13 um with its gate on vbias.  On sky130
    #   that was 0.9 V against a 0.7 V threshold.  Here vbias is the mirror
    #   node at 0.43 V, against a threshold that is *higher* at 0.13 um than
    #   at 0.3 um in this process -- char/mos.spice measures 0.314 V at
    #   0.30 um and 0.241 V at 1.0 um, so the roll-off runs the opposite way
    #   to the usual intuition.  A few tens of millivolts of overdrive.
    #   L = 1.0 um makes it a replica of the mirror reference MREF and gives
    #   it real overdrive at the same 0.43 V.
    #
    #   The CML nodes drive CMOS inverters that switch near 0.55 V, and the
    #   nodes sit at VDD - I*R.  The low excursion has to get below that.
    #
    # sim/decks/dff_tune.spice sweeps both against the drive the latch really
    # sees -- clock at the ring's measured levels, data at the CTLE's -- and
    # the boundary is sharp:
    #
    #   Wtail  Rload   CML low   output swing
    #      8   2239     1.068 V    4.8 mV      dead
    #      8   6000     0.842 V    5.6 mV      dead
    #     16   4000     0.664 V     155 mV     marginal
    #     16   6000     0.462 V    1.221 V     works
    #     24   4000     0.432 V    1.232 V     works
    #     24   6000     0.227 V    1.231 V     works, most margin
    #
    # 24/6000 is chosen for the margin rather than the current: 0.227 V leaves
    # 320 mV below the inverter threshold, against 88 mV for 16/6000, and
    # margin over PVT is exactly what every failure in this port has been
    # short of.  It costs about 166 uA per latch, 1.3 mA for the detector.
    #
    # The tail still sits at 0.114 V, i.e. in triode, so it does not mirror in
    # a clean ratio.  For a latch that matters less than for an amplifier --
    # it needs enough current, not a precise current -- but it is the obvious
    # thing to improve if the detector ever needs PVT margin of its own.
    # Fingered to stay inside the model's 10 um per-finger width range; the
    # geometry test catches this, and it caught this one.
    ("d_latch", "M2"): {"W": 24, "L": 1.0, "nf": 4},  # tail: MREF's length
    ("d_latch", "R1"): {"R": 6000},           # CML load; sets the swing
    ("d_latch", "R3"): {"R": 6000},

    # ------------------------------------------- charge pump bias reference
    # Measured, not estimated (sim/decks/cp_current.spice): with the ported
    # 3.6 kohm reference the pump delivers 7.56 uA up and 7.49 uA down into a
    # 147.5 fF loop filter, so each bang-bang update moves the control voltage
    # by I*UI/C = 84.7 mV.  sky130's proven design moved it 17.5 mV.
    #
    # 85 mV per update against a VCO slope near 300 MHz/V is 25 MHz of
    # frequency step per unit interval.  No loop settles on that: measured, the
    # control voltage goes 0.880 V at 80 ns, 0.486 at 100, 0.964 at 120, 0.447
    # at 150, and 0.3 mV by 200 ns -- at which point the ring has stopped and
    # the startup precharge, which fires once at power-up, has long released.
    #
    # The fix is to weaken the reference rather than enlarge the filter: it
    # costs no area and no power, and it lands on the update quantum sky130
    # demonstrated to be stable with almost the same capacitance.
    # The instance is an xschem *vector* -- one symbol expanding to three
    # resistors -- so its name is literally "R[2..0]", not R0/R1/R2.  A
    # SIZING key that matches nothing is silently ignored, which is exactly
    # what happened first time: the sweep ran four resistor values and
    # reported the same current four times.
    ("tiny_pll_bias_gen_res", "R[2..0]"): {"R": 24000},

    # ------------------------------------------------------- loop filter
    # The filter is vctl --[R 30k]-- cap_plus --[C1]-- gnd, with C2 straight
    # from vctl to ground.  The charge pump drives vctl, so on the timescale
    # of a single bang-bang update C1 is hidden behind the series resistor and
    # only C2 absorbs the charge:
    #
    #     ripple = I * UI / C2
    #
    # Both capacitors are MOS caps, so their ratio is the ratio of their gate
    # areas: cap1 is 4 x 0.6 um x 6 = 14.4 um2 and cap2 is 1.1 x 2 = 2.2 um2,
    # which splits the 147.5 fF measured across the whole filter into 128 fF
    # and 19.5 fF.  That predicts 76.7 mV of ripple against 77.9 mV measured
    # -- 1.5 % -- so the mechanism is settled, and it is C2 that sets it.
    #
    # This matters because it is *not* what the earlier reading suggested. The
    # ripple came out at about 7.7 update quanta at all three pump settings,
    # which looks exactly like a limit cycle whose amplitude is set by loop
    # latency.  It is not: 7.7 is just UI/C2 divided by UI/C_total, and the
    # remedy a latency story would have pointed at -- damping, or shortening
    # the path around the loop -- would have been a great deal of work for
    # nothing.
    #
    # So both capacitors scale by three, keeping their ratio so the loop's
    # damping is unchanged: C2 goes to 58 fF and the ripple should fall to
    # about 26 mV, below the sky130 original's 33.7 mV.  The cost is 43 um2 of
    # extra MOS capacitor, which is nothing next to the 1243 um2 the CTLE's
    # degeneration capacitor already occupies.
    ("tiny_pll_loop_filter_res", "R"): {"R": 15000},
    ("tiny_pll_loop_filter_cap1", "MCAP"): {"m": 18},
    ("tiny_pll_loop_filter_cap2", "MCAP"): {"m": 3},
    #
    # Why 12 kohm, and why not simply copy sky130's update quantum.  What a
    # bang-bang loop cares about is the *phase* step per update:
    #
    #     dphi = 2*pi * Kvco * dV * UI
    #
    # sky130 was stable at 17.5 mV with a 357 MHz/V oscillator -- 3.7 degrees
    # per unit interval -- and matching that phase step here wants about 20 mV,
    # which 12 kohm gives.  That reasoning got the loop locking; it did not get
    # the best answer.  Three full lock runs settled it:
    #
    #   Rbias   quantum   frequency    error     ripple
    #   12 k    20.5 mV   600.42 MHz   -0.031 %   177 mV
    #   24 k    10.1 mV   600.59 MHz   -0.002 %    78 mV
    #   36 k     7.0 mV   600.36 MHz   -0.040 %    57 mV
    #
    # 24 kohm is chosen: the frequency error is -0.002 % against sky130's
    # +0.006 %, and the dither is less than half what the phase-step argument
    # predicted was acceptable.  Going further to 36 kohm buys 20 mV less
    # ripple and costs frequency accuracy and acquisition time, because the
    # loop is then correcting more slowly than the run is long.
    #
    # The remaining ripple is not a loop-delay limit cycle, which is what the
    # constant 7.7-quanta ratio first suggested.  It is simpler than that, and
    # the loop filter says so: see the cap1/cap2 entries below.
}

# Devices whose L is at the sky130 minimum get the IHP minimum instead.
# Everything else keeps its drawn L: those lengths were chosen for output
# resistance or matching, not for speed, and 130 nm is not 150 nm's problem.

SYMBOL_MAP = {
    "sky130_fd_pr/nfet_01v8.sym": "sg13cmos5l_pr/sg13_lv_nmos.sym",
    "sky130_fd_pr/pfet_01v8.sym": "sg13cmos5l_pr/sg13_lv_pmos.sym",
    "sky130_fd_pr/nfet3_01v8.sym": "sg13cmos5l_pr/sg13_lv_nmos.sym",
    "sky130_fd_pr/pfet3_01v8.sym": "sg13cmos5l_pr/sg13_lv_pmos.sym",
    "sky130_fd_pr/res_high_po.sym": "sg13cmos5l_pr/rhigh.sym",
    "sky130_fd_pr/res_high_po_0p69.sym": "sg13cmos5l_pr/rhigh.sym",
    "sky130_fd_pr/res_xhigh_po_0p35.sym": "sg13cmos5l_pr/rhigh.sym",
    "sky130_fd_pr/cap_mim_m3_1.sym": "sg13cmos5l_pr/cap_cmomf.sym",
    # The taped-out charge pump used one sky130 standard-cell inverter.  There
    # is no reason to drag a whole standard-cell library into an all-custom
    # analog macro for a single gate, so it becomes a local two-transistor
    # cell.  inv_cp.sym is drawn with A and Y at exactly inv_1's coordinates,
    # (-40,0) and (40,0), so the swap cannot move a connection; it adds real
    # VPWR/VGND pins where inv_1 carried its supplies as properties, and the
    # port emits labels for those.
    "sky130_stdcells/inv_1.sym": "inv_cp.sym",
}

# Symbols whose supplies were properties on the sky130 side and are pins on the
# IHP side: {symbol: [(property, pin_x, pin_y)]}
SUPPLY_PROP_TO_PIN = {
    "sky130_stdcells/inv_1.sym": [("VPWR", 0, -30), ("VGND", 0, 30)],
}

THREE_PIN_FETS = {
    "sky130_fd_pr/nfet3_01v8.sym",
    "sky130_fd_pr/pfet3_01v8.sym",
}

# sky130 resistor symbols whose sheet differs from res_high_po.
SKY_RES_SHEET = {
    "sky130_fd_pr/res_high_po.sym": 319.8,
    "sky130_fd_pr/res_high_po_0p69.sym": 319.8,
    "sky130_fd_pr/res_xhigh_po_0p35.sym": 2000.0,
}


# --------------------------------------------------------------------------
# xschem file parsing
# --------------------------------------------------------------------------

# A component line is:  C {symbol} x y rot flip {properties}
# The property block may span many lines and may contain braces inside quotes.
C_HEAD = re.compile(r"^C\s*\{([^}]*)\}\s*"
                    r"(-?[\d.]+)\s+(-?[\d.]+)\s+(\d)\s+(\d)\s*\{")


def split_components(text: str):
    """Yield (kind, payload) where kind is 'C' for a component block.

    Returns the file as a list of chunks so non-component lines survive
    byte-for-byte.  Component property blocks are brace-balanced, which is why
    this cannot be done line by line.
    """
    out = []
    i = 0
    n = len(text)
    while i < n:
        line_end = text.find("\n", i)
        if line_end == -1:
            line_end = n
        line = text[i:line_end]
        m = C_HEAD.match(line)
        if not m:
            out.append(("raw", text[i:line_end + 1]))
            i = line_end + 1
            continue
        # Walk forward to the matching close brace of the property block.
        start_prop = i + m.end() - 1  # index of the '{' that opens properties
        depth = 0
        j = start_prop
        while j < n:
            if text[j] == "{":
                depth += 1
            elif text[j] == "}":
                depth -= 1
                if depth == 0:
                    break
            j += 1
        end = j + 1
        if end < n and text[end] == "\n":
            end += 1
        out.append(("C", text[i:end], m))
        i = end
    return out


def parse_props(block: str) -> tuple[str, list[tuple[str, str]]]:
    """Split a property block '{name=x\nL=1\n...}' into ordered key/value pairs.

    xschem property blocks are whitespace-separated key=value pairs, except
    that a value may be quoted and contain spaces.  Ordering is preserved so
    the output diffs cleanly against the input.
    """
    inner = block[block.index("{") + 1: block.rindex("}")]
    pairs = []
    tok = ""
    quote = False
    for ch in inner:
        if ch == '"':
            quote = not quote
            tok += ch
        elif ch.isspace() and not quote:
            if tok:
                pairs.append(tok)
                tok = ""
        else:
            tok += ch
    if tok:
        pairs.append(tok)
    kv = []
    for p in pairs:
        if "=" in p:
            k, v = p.split("=", 1)
            kv.append((k, v))
        else:
            kv.append((p, None))
    return inner, kv


def props_get(kv, key, default=None):
    for k, v in kv:
        if k == key:
            return v
    return default


# xschem's instance transform.  Taken from xschem's ROTATION macro; a symbol
# point (x, y) placed at (x0, y0) with rotation rot and flip flip lands at:
def transform(x, y, x0, y0, rot, flip):
    if flip == 0:
        rx, ry = [(x, y), (-y, x), (-x, -y), (y, -x)][rot]
    else:
        rx, ry = [(-x, y), (y, x), (x, -y), (-y, -x)][rot]
    return rx + x0, ry + y0


# --------------------------------------------------------------------------
# Device parameter transforms
# --------------------------------------------------------------------------

def um(value: float) -> str:
    """Format a micron value the way the IHP symbols expect (metres, 'u')."""
    s = f"{value:.4f}".rstrip("0").rstrip(".")
    return f"{s}u"


def metres(value_um: float) -> str:
    """Format a micron value as a plain metre literal (IHP passives use these)."""
    return f"{value_um * 1e-6:.6e}"


def port_fet(cell, inst, kv, is_nmos, three_pin):
    """sky130 FET properties -> IHP lv FET properties."""
    L = float(props_get(kv, "L", "0.15"))
    W = float(props_get(kv, "W", "1"))
    nf = int(float(props_get(kv, "nf", "1")))
    mult = int(float(props_get(kv, "mult", props_get(kv, "m", "1"))))

    # sky130's minimum is 150 nm, IHP's is 130 nm.  A device drawn at the
    # process minimum was asking for "as fast as this process goes", so it gets
    # the new process's minimum.  A device drawn longer than minimum was asking
    # for a specific length, and keeps it.
    if abs(L - 0.15) < 1e-9:
        L = MIN_L_LV

    over = SIZING.get((cell, inst), {})
    L = over.get("L", L)
    W = over.get("W", W)
    nf = over.get("nf", nf)
    mult = over.get("m", mult)

    W = max(W, MIN_W_LV * nf)
    L = max(L, MIN_L_LV)

    model = "sg13_lv_nmos" if is_nmos else "sg13_lv_pmos"
    out = [
        ("name", inst),
        ("l", um(L)),
        ("w", um(W)),
        ("ng", str(nf)),
        ("m", str(mult)),
        ("mm_ok", "1"),
        ("model", model),
        ("spiceprefix", "X"),
    ]
    body = props_get(kv, "body") if three_pin else None
    return out, body


def port_res(cell, inst, kv, symbol):
    """sky130 poly resistor -> IHP rhigh of the same nominal resistance."""
    W = float(props_get(kv, "W", "1"))
    L = float(props_get(kv, "L", "1"))
    mult = int(float(props_get(kv, "mult", props_get(kv, "m", "1"))))
    sheet = SKY_RES_SHEET.get(symbol, SKY_RSH_HIGH_PO)
    r_target = sheet * L / W

    over = SIZING.get((cell, inst), {})
    r_target = over.get("R", r_target)
    w_um = over.get("W", 1.0)

    # Invert the PDK's own rhigh expression for l, at the chosen w:
    #   R = RC/w + sheet * l / (w - dW)
    w_m = w_um * 1e-6
    l_m = (r_target - IHP_RHIGH_RC / w_m) * (w_m - IHP_RHIGH_DW) / IHP_RHIGH_SHEET
    l_um = max(l_m * 1e6, 0.5)

    return [
        ("name", inst),
        ("w", metres(w_um)),
        ("l", metres(l_um)),
        ("model", "rhigh"),
        ("body", "sub!"),
        ("spiceprefix", "X"),
        ("b", "0"),
        ("m", str(mult)),
        ("mm_ok", "1"),
    ], r_target


def port_cap(cell, inst, kv):
    """sky130 MIM -> IHP MOM fringe capacitor of the same nominal value.

    SG13CMOS5L has no MIM at all, which is the one device substitution in this
    port that is forced rather than chosen.  cap_cmomf is the linear option:
    a MOS capacitor would be six times denser but its capacitance depends on
    the voltage across it, and both places this design uses a capacitor — the
    CTLE degeneration and the loop filter — need a capacitor whose value does
    not move with the signal or the control voltage.
    """
    W = float(props_get(kv, "W", "1"))
    L = float(props_get(kv, "L", "1"))
    mf = int(float(props_get(kv, "MF", props_get(kv, "m", "1"))))
    c_target = SKY_MIM_DENSITY * W * L

    over = SIZING.get((cell, inst), {})
    c_target = over.get("C", c_target)

    area_um2 = c_target / IHP_CMOMF_DENSITY
    side = area_um2 ** 0.5

    return [
        ("name", inst),
        ("model", "cap_cmomf"),
        ("w", metres(side)),
        ("l", metres(side)),
        ("mmin", "1"),
        ("mmax", "4"),
        ("subblock", "0"),
        ("m", str(mf)),
        ("mm_ok", "1"),
        ("spiceprefix", "X"),
    ], c_target


# --------------------------------------------------------------------------

def render_props(kv) -> str:
    return "{" + "\n".join(f"{k}={v}" if v is not None else k for k, v in kv) + "}"


def port_file(src: Path, dst: Path, report: list):
    text = src.read_text()
    cell = src.stem
    chunks = split_components(text)
    out = []
    extra_labels = []
    label_n = 9000

    for chunk in chunks:
        if chunk[0] == "raw":
            out.append(chunk[1])
            continue
        _, raw, m = chunk
        symbol = m.group(1)
        x0, y0 = float(m.group(2)), float(m.group(3))
        rot, flip = int(m.group(4)), int(m.group(5))
        prop_block = raw[raw.index("{", raw.index("}") + 1):]
        _, kv = parse_props(prop_block)
        inst = props_get(kv, "name", "?")

        if symbol not in SYMBOL_MAP:
            out.append(raw)
            continue

        new_symbol = SYMBOL_MAP[symbol]
        three_pin = symbol in THREE_PIN_FETS

        if "fet" in symbol:
            is_nmos = "nfet" in symbol
            new_kv, body = port_fet(cell, inst, kv, is_nmos, three_pin)
            if body:
                # The IHP symbol has a real bulk pin at (20, 0); the sky130
                # 3-pin symbol carried the bulk as a property.  Put a label on
                # the new pin so the connection survives the swap.
                bx, by = transform(20, 0, x0, y0, rot, flip)
                label_n += 1
                extra_labels.append(
                    f"C {{devices/lab_wire.sym}} {bx:g} {by:g} 0 0 "
                    f"{{name=p{label_n} sig_type=std_logic lab={body}}}\n")
                report.append(f"  {cell}.{inst}: bulk '{body}' rewired to the "
                              f"new B pin at ({bx:g},{by:g})")
            report.append(f"  {cell}.{inst}: {symbol.split('/')[-1]} -> "
                          f"{new_kv[6][1]} w={new_kv[2][1]} l={new_kv[1][1]} "
                          f"ng={new_kv[3][1]}")
        elif "res_" in symbol:
            new_kv, r = port_res(cell, inst, kv, symbol)
            report.append(f"  {cell}.{inst}: {symbol.split('/')[-1]} -> rhigh "
                          f"w={new_kv[1][1]} l={new_kv[2][1]}  ({r:.0f} ohm)")
        elif "cap_" in symbol:
            new_kv, c = port_cap(cell, inst, kv)
            report.append(f"  {cell}.{inst}: cap_mim_m3_1 -> cap_cmomf "
                          f"w=l={new_kv[2][1]}  ({c * 1e15:.1f} fF)")
        elif symbol in SUPPLY_PROP_TO_PIN:
            new_kv = [("name", inst)]
            for prop, px, py in SUPPLY_PROP_TO_PIN[symbol]:
                net = props_get(kv, prop)
                if net is None:
                    continue
                sx, sy = transform(px, py, x0, y0, rot, flip)
                label_n += 1
                extra_labels.append(
                    f"C {{devices/lab_wire.sym}} {sx:g} {sy:g} 0 0 "
                    f"{{name=p{label_n} sig_type=std_logic lab={net}}}\n")
                report.append(f"  {cell}.{inst}: supply '{prop}'='{net}' "
                              f"becomes a pin at ({sx:g},{sy:g})")
            report.append(f"  {cell}.{inst}: {symbol.split('/')[-1]} -> "
                          f"{new_symbol.split('/')[-1]}")
        else:
            out.append(raw)
            continue

        head = f"C {{{new_symbol}}} {x0:g} {y0:g} {rot} {flip} "
        out.append(head + render_props(new_kv) + "\n")

    result = "".join(out)
    if extra_labels:
        result = result.rstrip("\n") + "\n" + "".join(extra_labels)
    dst.write_text(result)


# --------------------------------------------------------------------------
# Design changes applied on top of the mechanical port.
#
# These are edits the port makes deliberately, not translations.  They live
# here rather than as hand edits to the generated schematics so that re-running
# the port does not silently undo them.
# --------------------------------------------------------------------------

def add_bias_mirror(text: str) -> str:
    """Top level: take a reference current in, not a bias voltage.

    The sky130 macro brought `vbias` in from a pin as a voltage and fed it
    straight to the CTLE tail and the CML tails.  Measured across PVT at
    1.2 V that gives a 15 dB spread in the CTLE's Nyquist gain and an outright
    collapse at the fast corner (see xschem/ibias_mirror.sch for the numbers).
    A gate voltage does not specify a current once threshold voltage and
    mobility move.

    So the pin becomes `ibias`, a current the harness's bandgap-referenced
    source pushes in, and a diode-connected replica turns it into whatever
    gate voltage that current needs at this corner.  Nothing inside CTLE or
    CDR changes: they still see a bias voltage on the same node.
    """
    text = text.replace("lab=vbias", "lab=ibias")
    text = text.rstrip("\n") + "\n"
    text += (
        "C {ibias_mirror.sym} -600 220 0 0 {name=x5}\n"
        "C {devices/lab_wire.sym} -640 220 0 0 "
        "{name=p90 sig_type=std_logic lab=ibias}\n"
        "C {devices/lab_wire.sym} -560 220 0 0 "
        "{name=p91 sig_type=std_logic lab=VGND}\n"
    )
    return text


def add_coarse_trim(text: str) -> str:
    """ring_inverter: a pMOS trim leg across each poly load resistor.

    The fine loop drives the ring's tail current, and above the point where a
    stage can charge its own load faster than its RC, more tail current buys
    nothing -- the load resistor sets the ceiling, and that ceiling is what
    fails at temperature.  The untrimmed ring reaches the 600.6 MHz baud rate at
    8 of 27 corners.  So the coarse loop moves the *load*: one pMOS across each
    of the ten load resistors, all gates on a single `vcoarse!` rail.

    The resistor sits at the slow end of the span and the pMOS only ever speeds
    the ring up, so with vcoarse at VDD the trim is absent and the ring is the
    ported design with a slightly larger load.  There is no state in which the
    trim makes things worse than the untrimmed circuit.

    Two things about this that are not obvious:

    * `vcoarse!` is a **global** net, like `sub!`.  It is a quasi-dc bias rail
      distributed to ten gates, which is what a global is for, and the
      alternative -- a new pin on ring_inverter, ring_oscillator, CDR and their
      symbols -- would change the port list of four cells that
      check_port_equivalence.py is comparing against the sky130 source, and
      bury the one real change among four bookkeeping ones.

    * connectivity is by label, not by wire.  xschem connects by coordinate, so
      appending geometry to a schematic whose layout you did not compute is how
      a symbol lands forty units off and silently rewires the circuit.  A
      lab_wire placed exactly on a pin cannot do that.

    Sizing is measured, not calculated: see docs/RING_DUAL_LOOP.md section 4.1.
    A pMOS is only a resistor while it stays in triode, and at the bottom of the
    ring's swing it becomes a current source and stops helping the rising edge,
    which is the edge the ceiling is made of -- about 43 % as effective as the
    resistance it imitates.  W was swept in the ring instead.
    """
    if "name=T1\n" in text:
        return text                      # already applied; the port is re-run
    text = text.rstrip("\n") + "\n"
    for name, (x, out) in {"T1": (60, "vo+"), "T2": (-480, "vo-")}.items():
        text += (
            "C {sg13cmos5l_pr/sg13_lv_pmos.sym} %d 240 0 0 {name=%s\n"
            "l=%gu\nw=%gu\nng=1\nm=1\nmm_ok=1\n"
            "model=sg13_lv_pmos\nspiceprefix=X}\n"
            % (x, name, TRIM_L, TRIM_W))
        # Named by *pin*, not by net: source and bulk are both VDD, and two
        # labels called T1_VDD is a duplicate instance name in xschem.
        for pin, dx, dy, lab in (("S", 20, -30, "VDD"), ("D", 20, 30, out),
                                 ("G", -20, 0, "vcoarse!"), ("B", 20, 0, "VDD")):
            text += ("C {devices/lab_wire.sym} %d %d 0 0 "
                     "{name=%s_%s sig_type=std_logic lab=%s}\n"
                     % (x + dx, 240 + dy, name, pin, lab))
    return text


def add_coarse_loop(text: str) -> str:
    """CDR: instantiate the coarse loop next to the loop filter.

    It goes here rather than at the top level because both of its inputs are
    already local nets at this level -- `vctrl` is the loop filter's output and
    `vbias` is the reference the charge pump and the latches run on -- so the
    only thing that has to cross a hierarchy boundary is `vcoarse!`, which is a
    global.  Instantiating it a level up would need vctrl brought out as a pin
    on CDR for no reason.

    The loop filter's output is an unnamed net in the sky130 original (xschem
    calls it #net1).  Labelling it `vctrl` is deliberate: it is the node every
    measurement in docs/ refers to by that name, and it is about to have a
    second consumer.
    """
    if "{coarse_loop.sym}" in text:
        return text                      # already applied; the port is re-run
    text = text.rstrip("\n") + "\n"
    text += ("C {devices/lab_wire.sym} 2030 100 0 0 "
             "{name=pCTL sig_type=std_logic lab=vctrl}\n")
    text += "C {coarse_loop.sym} 1000 900 0 0 {name=x30}\n"
    for dx, dy, lab in ((-60, -20, "Vdd"), (-60, 0, "Vss"), (-60, 20, "vbias"),
                        (60, 0, "vctrl"), (60, 20, "vcoarse!")):
        text += ("C {devices/lab_wire.sym} %d %d 0 0 "
                 "{name=pCL%s sig_type=std_logic lab=%s}\n"
                 % (1000 + dx, 900 + dy, lab.strip("!"), lab))
    return text


POST_PORT_EDITS = {
    "ctle_cdr_rx.sch": add_bias_mirror,
    "ring_inverter.sch": add_coarse_trim,
    "CDR.sch": add_coarse_loop,
    # The LVS wrapper and the symbol only need the pin renamed to match.
    "ctle_cdr_rx_lvs.sch": lambda t: t.replace("lab=vbias", "lab=ibias"),
    "ctle_cdr_rx.sym": lambda t: t.replace("name=vbias", "name=ibias"),
    "ctle_cdr_rx_lvs.sym": lambda t: t.replace("name=vbias", "name=ibias"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", required=True, type=Path)
    ap.add_argument("--dst", required=True, type=Path)
    ap.add_argument("--cells", nargs="*", default=None)
    args = ap.parse_args()

    args.dst.mkdir(parents=True, exist_ok=True)
    report = []
    files = sorted(args.src.glob("*.sch"))
    if args.cells:
        want = set(args.cells)
        files = [f for f in files if f.stem in want]
    for f in files:
        report.append(f"{f.name}:")
        port_file(f, args.dst / f.name, report)
    for f in sorted(args.src.glob("*.sym")):
        if args.cells and f.stem not in set(args.cells):
            continue
        (args.dst / f.name).write_text(f.read_text())

    for name, edit in POST_PORT_EDITS.items():
        target = args.dst / name
        if not target.exists():
            continue
        target.write_text(edit(target.read_text()))
        report.append(f"{name}: design change applied ({edit.__name__ if hasattr(edit, '__name__') else 'inline'})")

    print("\n".join(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
