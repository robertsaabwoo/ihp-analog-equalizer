* dff_p.inc -- the CML D latch and flip-flop of xschem/d_latch.sch and
* d_flip_flop.sch, parameterised so the tail and the load can be swept.
*
* The latch is a current-mode-logic master/slave pair:
*
*      VDD --[Rload]-- n1        n2 --[Rload]-- VDD
*                       |         |
*   vip --|M1           |         |          M4|-- vim      (data pair)
*                       n3        |
*            M3|--n1    |         |   n2--|M5             (cross-coupled hold)
*                       n5 -------+
*         clkp --|M6            M7|-- clkm               (clock steering)
*                       |         |
*                       +--- n4 --+
*                            |
*                  vbias --|M2 Wtail/Ltail
*                            |
*                           VSS
*
* and n1/n2 then drive two CMOS inverters to give logic-level outputs.
*
* Two things about this cell do not survive the move to 1.2 V, and they are the
* same two that broke diff_amp_inv:
*
*   1. The tail.  It is drawn at L = 0.13 um, and its gate comes from vbias --
*      which on sky130 was 0.9 V against a 0.7 V threshold, and here is the
*      current-mirror node at about 0.43 V against a threshold that is *higher*
*      at 0.13 um than at 0.3 um in this process (0.314 V measured at 0.30 um;
*      the roll-off runs the other way).  Overdrive is a few tens of millivolts
*      and the tail barely conducts.  Making it a long-channel replica of the
*      mirror reference (L = 1 um, like MREF) both fixes the overdrive and
*      makes the ratio predictable.
*
*   2. The swing into the output inverters.  The CML nodes sit at VDD - I*R and
*      swing by I*R.  The inverters they drive switch near 0.55 V, so the low
*      excursion has to get below that: I*R > ~0.65 V.  At the ported 2.24 kohm
*      that needs 290 uA per latch, which is a lot for eight latches; raising
*      Rload gets there at a sane current instead.

.param Wtail=8 Ltail=1.0 Ngtail=1
.param Rload=2239
.param Wres=1u
.param Lload='(Rload - 1.6e-4/Wres) * (Wres - 0.04u) / 1360'

.subckt d_latch_p vop vom vip vim VDD VSS clkp clkm vbias
XM1 n1 vip n3 VSS sg13_lv_nmos w=5u l=0.13u ng=1 m=1 mm_ok=1
XM4 n2 vim n3 VSS sg13_lv_nmos w=5u l=0.13u ng=1 m=1 mm_ok=1
XM3 n2 n1  n5 VSS sg13_lv_nmos w=5u l=0.13u ng=1 m=1 mm_ok=1
XM5 n1 n2  n5 VSS sg13_lv_nmos w=5u l=0.13u ng=1 m=1 mm_ok=1
XM6 n3 clkp n4 VSS sg13_lv_nmos w=5u l=0.13u ng=1 m=1 mm_ok=1
XM7 n5 clkm n4 VSS sg13_lv_nmos w=5u l=0.13u ng=1 m=1 mm_ok=1
XM2 n4 vbias VSS VSS sg13_lv_nmos w='Wtail*1u' l='Ltail*1u' ng='Ngtail' m=1 mm_ok=1
XR3 VDD n1 sub! rhigh w='Wres' l='Lload' m=1 b=0 mm_ok=1
XR1 VDD n2 sub! rhigh w='Wres' l='Lload' m=1 b=0 mm_ok=1
XM8  vop n1 VDD VDD sg13_lv_pmos w=3u l=0.13u ng=1 m=1 mm_ok=1
XM9  vop n1 VSS VSS sg13_lv_nmos w=1u l=0.13u ng=1 m=1 mm_ok=1
XM10 vom n2 VDD VDD sg13_lv_pmos w=3u l=0.13u ng=1 m=1 mm_ok=1
XM11 vom n2 VSS VSS sg13_lv_nmos w=1u l=0.13u ng=1 m=1 mm_ok=1
.ends

* Master/slave, with the master clocked on the opposite phase -- the same
* wiring as d_flip_flop.sch.
.subckt d_flip_flop_p Vdd Vss Q Qn vip clkp clkm vim vbias
x1 m1 m2 vip vim Vdd Vss clkm clkp vbias d_latch_p
x2 Q  Qn m1 m2  Vdd Vss clkp clkm vbias d_latch_p
.ends
