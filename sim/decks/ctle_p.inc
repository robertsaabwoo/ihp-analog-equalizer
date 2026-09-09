* ctle_p.inc -- the CTLE of xschem/CTLE.sch, parameterised for tuning.
*
* Identical topology to the schematic; the point of this file is that the
* sizes are .param so one ngspice run can sweep them with alterparam, instead
* of one run per size.  Anything settled here goes back into CTLE.sch and the
* schematic is then the source of truth again.
*
*   VDD --[Rload]-- outp              outm --[Rload]-- VDD
*                    |                 |
*   inp --|M1 Win/Lin|                 |Win/Lin M4|-- inm
*                    sp ---[Ccap]--- sm
*                    |                 |
*               [Rdeg]                 [Rdeg]
*                    |                 |
*                    +------- st ------+
*                              |
*                     vbias --|M2 Wtail/Ltail
*                              |
*                             VSS
*
* One bridging capacitor across sp--sm rather than two to the tail node:
* differentially it looks like 2*Ccap from each source to the virtual ground,
* so it buys twice the effective degeneration capacitance for half the area.
* That mattered on sky130's MIM and matters more here, because SG13CMOS5L has
* no MIM at all and cap_cmomf is 1.29 fF/um^2 against sky130's 2.0.
*
* Sizes are given as the quantities that actually set the transfer function --
* two resistances and a capacitance -- and the geometry is solved from the
* PDK's own expressions, so retuning does not mean redoing arithmetic:
*
*   rhigh:      R = 1.6e-4/w + 1360*l/(w - 0.04u)      (b=0)
*   cap_cmomf:  C = 1.287 fF/um^2, measured in char/caps.spice
*
* Differential transfer, with Zdeg = Rdeg || 1/(s*2*Ccap):
*   A(s) = gm*Rload * (1 + s*2*Ccap*Rdeg) / (1 + gm*Rdeg + s*2*Ccap*Rdeg)
*   zero  at 1/(2*pi*2*Ccap*Rdeg)
*   pole  at (1 + gm*Rdeg) * zero
*   boost  = 1 + gm*Rdeg

.param Win=20 Lin=0.3
.param Wtail=20 Ltail=0.5
.param Rload=6400
.param Rdeg=1600
.param Ccap=648f
.param Mload=1 Mdeg=1 Mcap=1

* Solve rhigh length from the target resistance, at w = 1 um.
.param Wres=1u
.param Lload='(Rload - 1.6e-4/Wres) * (Wres - 0.04u) / 1360'
.param Ldeg ='(Rdeg  - 1.6e-4/Wres) * (Wres - 0.04u) / 1360'
* Solve the MOM capacitor side from the target capacitance.  The density is
* written in F/m^2 (1.287 fF/um^2 = 1.287e-3 F/m^2) so the square root comes
* out in metres directly -- no unit conversion afterwards, which is where the
* first version of this line lost a factor of a million and produced a 22 pm
* capacitor that simulated perfectly happily and showed no peaking at all.
.param Scap='sqrt(Ccap / 1.287e-3)'

.subckt ctle_p outp outm inp inm VDD VSS vbias
XM1 outp inp sp   VSS sg13_lv_nmos w='Win*1u'   l='Lin*1u'   ng=1 m=1 mm_ok=1
XM4 outm inm sm   VSS sg13_lv_nmos w='Win*1u'   l='Lin*1u'   ng=1 m=1 mm_ok=1
XM2 st   vbias VSS VSS sg13_lv_nmos w='Wtail*1u' l='Ltail*1u' ng=1 m=1 mm_ok=1
XR1 VDD outp sub! rhigh w='Wres' l='Lload' m='Mload' b=0 mm_ok=1
XR2 VDD outm sub! rhigh w='Wres' l='Lload' m='Mload' b=0 mm_ok=1
XR3 st  sp   sub! rhigh w='Wres' l='Ldeg'  m='Mdeg'  b=0 mm_ok=1
XR4 st  sm   sub! rhigh w='Wres' l='Ldeg'  m='Mdeg'  b=0 mm_ok=1
XCS sp  sm   cap_cmomf w='Scap' l='Scap' mmin=1 mmax=4 subblock=0 m='Mcap' mm_ok=1
.ends
