* ring_ct.inc -- the ring with a coarse trim leg, for the dual-loop CDR.
*
* The fine loop is the existing bang-bang CDR: it drives vctrl, which sets the
* ring's tail current, and it tunes over only 1.166:1 because with a resistive
* load the *rising* edge is RC-limited whatever the tail current does.  That
* range covers 8 of 27 PVT corners.  The coarse loop drives vcoarse, which sits
* on the gate of a small pMOS in parallel with each poly load resistor:
*
*      VDD --+--[Rload 9000]--+-- vo+
*            |                |
*            +--|MTR (pMOS)---+          gate = vcoarse
*
* The load resistance is what sets the RC limit, so this knob has authority
* where vctrl does not.  vco_rsweep.spice measured how much:
*
*      stage delay = 61.0 ps + 13.100 ps per kilohm   (at vctrl = 1.10 V)
*
* -- 61 ps of transit time that the load cannot touch, and the rest RC.  At the
* shipped 7355 ohm the load is 61 % of the delay.
*
* The poly resistor sits at the *slow* end of the span and the pMOS only ever
* speeds the ring up, so at vcoarse = VDD the trim is absent and the ring is the
* ported design with a slightly larger load.  There is no state in which the
* trim makes things worse than the untrimmed circuit.
*
* This is not the diode-connected-load idea that was tried and rejected.  There
* the transistor *was* the load, so its process spread was the ring's spread and
* 5 of 24 swept points stopped oscillating.  Here the poly resistor is still the
* load and the pMOS is a correction.
*
* -------------------------------------------------------------------------
* The input pair is 0.7 um, not the shipped 0.9 um
*
* The first corner sweep of the trimmed ring failed at tt / 125 C / 1.08 V:
* trim fully on, tail at maximum, 573.7 MHz against a 600.6 MHz baud rate.  Two
* thirds of the stage delay at that corner is the 61 ps transit term that no
* amount of load trimming touches, and that term is set by the input pair's
* channel length -- 0.9 um, inherited from sky130's 1.0 um, seven times the
* minimum here, and sitting on the very node whose RC sets the ceiling, so it
* costs twice.  ring_lin.spice sweeps it at both binding corners (hot and
* low-supply with the trim on; cold and high-supply with the trim off):
*
*      Lin     hot/low, trim ON     cold/high, trim OFF
*      0.9 um     573.7 MHz              367.5 MHz
*      0.7 um     710.4                  462.7
*      0.5 um     960.6                  601.2
*      0.35 um   1275.3                  743.8
*      0.13 um   1925.5                  962.2
*
* The ring has to bracket 600.6 MHz from both sides.  0.9 um cannot reach it
* from below at the hot corner; 0.5 um and shorter cannot get *under* it at the
* cold corner, where even with the trim entirely off the ring is already at
* 601 MHz.  0.7 um clears both with 18 % at the top and 23 % at the bottom, and
* it is the only value swept that does.  (tt only -- the three-process sweep is
* vco_ct_pvt.spice.)
* -------------------------------------------------------------------------
*
* The load is 9000 ohm, and the number that set it is the *floor*
*
* At low tail current the ring is current-starved, the stage delay is
* C*swing/I with swing = I*R, and the frequency is therefore 1/RC -- it stops
* depending on the current at all.  What stops it going slower is the swing
* dying: below about 0.15 V single-ended the measurement (and the buffer after
* it) stops meaning anything.  So the lowest frequency the ring can be held at
* is set by the load resistance and nothing else, and it goes as 1/R.
*
* At 8000 ohm that floor was 606.4 MHz at ss / 125 C / 1.32 V -- 1.0 % *above*
* the baud rate, so the one corner in 27 the coarse loop could not cover was a
* corner where the ring could not be made slow enough.  vco_ct_centre.spice
* said the same thing from the other side: at tt / 27 C / 1.2 V with the trim
* entirely off the ring was already at 685.6 MHz at vctrl = 0.60, so nominal
* sat at the slow rail with nothing in reserve.  Both are the base resistor
* being too small for the shorter input pair.
*
* Sizing the leg: why it was swept and not calculated
*
* The first attempt sized it by arithmetic.  W = 0.5 um, L = 1 um across an
* 8000 ohm load was predicted to give -21 % on the load resistance, and
* trim_r.spice measured 6339 ohm, -20.8 % -- the arithmetic was right to 1 %.
* The ring then moved +5.6 %, where the table above says a real 6339 ohm
* resistor is worth about +13 %.
*
* A pMOS is only a resistor while it stays in triode.  At the bottom of the
* ring's swing its source-drain voltage approaches its overdrive, it turns into
* a current source, and it stops helping the rising edge -- which is exactly
* the edge the RC ceiling is made of.  Measured against a real resistor of the
* same dc-equivalent value it is about 43 % as effective.  So the width was
* swept in the ring instead (vco_ct.spice, Rload = 9000, vctrl = 1.10 V):
*
*      Wtr   vcoarse=VDD   0.5 V    0.0 V     span
*      1 um    553.4       564.1    614.8    1.111:1
*      2 um    542.2       561.7    642.7    1.185:1
*      4 um    521.2       556.8    673.5    1.292:1
*      8 um    483.9       545.5    692.0    1.430:1
*
* The corner sweep asks for +15.2 % / -8.1 % about centre, which is 1.254:1.
* W = 4 um clears that with margin to spare and keeps the ring node swinging
* 0.93-1.01 V at every setting; W = 8 um buys more range but costs 38 MHz at
* the untrimmed end (the leg's own drain capacitance loads the ring node even
* when it is off) and its swing falls to 0.73 V at the strongest setting.
* -------------------------------------------------------------------------

.param Win=3 Lin=0.7
.param Wtail=9 Ltail=0.13
.param Rload=9000
.param Wtr=4 Ltr=1.0
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
