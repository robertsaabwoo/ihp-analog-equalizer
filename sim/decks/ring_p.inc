* ring_p.inc -- the five-stage CML ring of xschem/ring_oscillator.sch,
* parameterised so the tuning range can be swept in one ngspice run.
*
* One stage:
*
*      VDD --[Rload]-- vo+        vo- --[Rload]-- VDD
*                       |          |
*      vin+ --|M1 Win/Lin          Win/Lin M4|-- vin-
*                       +---- st ---+
*                             |
*                    vctrl --|M5 Wtail/Ltail
*                             |
*                            VSS
*
* Five stages in a ring with one inversion (the last stage's outputs cross
* over), so the oscillation period is ten stage delays.
*
* The stage delay is set by Rload against the capacitance on the output node,
* and by how much current the tail lets through.  At low vctrl the ring is
* current-starved and the frequency follows vctrl; above the point where the
* stage can charge its own load in less than an RC, more vctrl buys nothing
* and the frequency flattens.  That ceiling is the whole design problem here:
* a bang-bang phase detector has no frequency acquisition, so a ring that
* cannot reach the baud rate never locks, at any control voltage.
*
* The sky130 original reached 514-621 MHz at tt/27 C.  Ported unchanged to
* 1.2 V it reaches 424-554 MHz -- below the 600.6 Mb/s baud rate, so it does
* not lock at all.  Both the load resistance and the input pair's 1 um
* channel length are sky130 choices that do not transfer: 1 um is 7.7 times
* the minimum here rather than 6.7 times, and more to the point it puts a
* large gate capacitance on the node whose RC sets the ceiling.

.param Win=3 Lin=1.0
.param Wtail=9 Ltail=0.13
.param Rload=7355
.param Wres=1u
.param Lload='(Rload - 1.6e-4/Wres) * (Wres - 0.04u) / 1360'

.subckt ring_inv_p VDD VSS vin+ vo+ vin- vo- vctrl
XM1 vo+ vin+ st  VSS sg13_lv_nmos w='Win*1u'   l='Lin*1u'   ng=1 m=1 mm_ok=1
XM4 vo- vin- st  VSS sg13_lv_nmos w='Win*1u'   l='Lin*1u'   ng=1 m=1 mm_ok=1
XM5 st  vctrl VSS VSS sg13_lv_nmos w='Wtail*1u' l='Ltail*1u' ng=1 m=1 mm_ok=1
XR1 VDD vo+ sub! rhigh w='Wres' l='Lload' m=1 b=0 mm_ok=1
XR2 VDD vo- sub! rhigh w='Wres' l='Lload' m=1 b=0 mm_ok=1
.ends

* Same wiring as ring_oscillator.sch: five stages, the last one crossed over,
* then the diff_amp_inv output stage (taken from the schematic netlist, not
* parameterised -- it is a buffer, not part of the frequency plan).
.subckt ring_p Vdd Vss vctrl vo+ vo-
x1 Vdd Vss net7 net1 net8 net2  vctrl ring_inv_p
x2 Vdd Vss net1 net4 net2 net3  vctrl ring_inv_p
x3 Vdd Vss net4 net5 net3 net6  vctrl ring_inv_p
x5 Vdd Vss net5 net9 net6 net10 vctrl ring_inv_p
x4 Vdd Vss net9 net7 net10 net8 vctrl ring_inv_p
x6 Vdd Vss vo- vo+ net7 net8 Vdd diff_amp_inv
.ends
