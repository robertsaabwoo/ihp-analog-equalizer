* ring_ct.inc -- the ring with a coarse trim leg, for the dual-loop CDR.
*
* The fine loop is the existing bang-bang CDR: it drives vctrl, which sets the
* ring's tail current, and it tunes over only 1.166:1 because with a resistive
* load the *rising* edge is RC-limited whatever the tail current does.  That
* range covers 8 of 27 PVT corners.
*
* The coarse loop drives vcoarse, which sits on the gate of a small pMOS in
* parallel with each poly load resistor.  The load resistance is what sets the
* RC limit, so this knob has authority where vctrl does not:
*
*      VDD --+--[Rload 8000]--+-- vo+
*            |                |
*            +--|MTR (pMOS)---+          gate = vcoarse
*
* The poly resistor sits at the *slow* end and the pMOS only ever speeds the
* ring up, so with vcoarse at VDD the trim is completely absent and the ring is
* exactly the ported design with a slightly larger load.
*
* Sizing, before simulating (char/mos.spice gives uCox(p) = 87.4 uA/V^2):
*
*   Ron = 1 / (uCox (W/L) Vov)   at Vov = 1.2 - 0.46 = 0.74 V
*   W=0.5 L=1.0 -> 30.9 kohm -> 8000 || 30.9k = 6355 ohm, -21 %
*
* which is the +15.2 % / -8.1 % the corner sweep asked for, with margin at both
* ends.  A W = 0.5 um device is also small enough that its own process spread
* is attenuated by the parallel ratio -- the poly resistor still dominates.
* That is the objection that killed the diode-load idea, and it does not apply
* here because this pMOS is a correction, not the load.

.param Win=3 Lin=0.9
.param Wtail=9 Ltail=0.13
.param Rload=8000
.param Wtr=0.5 Ltr=1.0
.param Wres=1u
.param Lload='(Rload - 1.6e-4/Wres) * (Wres - 0.04u) / 1360'

.subckt ring_inv_ct VDD VSS vin+ vo+ vin- vo- vctrl vcoarse
XM1 vo+ vin+ st  VSS sg13_lv_nmos w='Win*1u'   l='Lin*1u'   ng=1 m=1 mm_ok=1
XM4 vo- vin- st  VSS sg13_lv_nmos w='Win*1u'   l='Lin*1u'   ng=1 m=1 mm_ok=1
XM5 st  vctrl VSS VSS sg13_lv_nmos w='Wtail*1u' l='Ltail*1u' ng=1 m=1 mm_ok=1
XR1 VDD vo+ sub! rhigh w='Wres' l='Lload' m=1 b=0 mm_ok=1
XR2 VDD vo- sub! rhigh w='Wres' l='Lload' m=1 b=0 mm_ok=1
XT1 vo+ vcoarse VDD VDD sg13_lv_pmos w='Wtr*1u' l='Ltr*1u' ng=1 m=1 mm_ok=1
XT2 vo- vcoarse VDD VDD sg13_lv_pmos w='Wtr*1u' l='Ltr*1u' ng=1 m=1 mm_ok=1
.ends

.subckt ring_ct Vdd Vss vctrl vcoarse vo+ vo-
x1 Vdd Vss net7 net1 net8 net2  vctrl vcoarse ring_inv_ct
x2 Vdd Vss net1 net4 net2 net3  vctrl vcoarse ring_inv_ct
x3 Vdd Vss net4 net5 net3 net6  vctrl vcoarse ring_inv_ct
x5 Vdd Vss net5 net9 net6 net10 vctrl vcoarse ring_inv_ct
x4 Vdd Vss net9 net7 net10 net8 vctrl vcoarse ring_inv_ct
x6 Vdd Vss vo- vo+ net7 net8 Vdd diff_amp_inv
.ends
