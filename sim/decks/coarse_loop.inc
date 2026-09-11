* coarse_loop.inc -- the coarse frequency-acquisition loop for the CDR ring.
*
* A gated sweep, not a trim.  docs/RING_DUAL_LOOP.md section 2 has the
* measurement that forces this: out of band, vctrl ramps *up* whether the ring
* is 4 % too slow or 12 % too fast, so there is no sign information in it and a
* bidirectional window trim cannot work.  What vctrl is very good at is saying
* locked or not locked -- flat to 0.5 mV/us locked, climbing at 107-167 mV/us
* out of band.
*
*   unlocked (vctrl above threshold) -> 20 nA discharges Ccoarse
*                                    -> vcoarse falls
*                                    -> the trim pMOS in each ring stage turns
*                                       on harder, the load falls, the ring
*                                       sweeps *upward* in frequency
*   vcoarse reaches the bottom        -> the wrap comparator charges Ccoarse
*                                       back to the top in a few ns and the
*                                       sweep restarts from the slow end
*   locked (vctrl below threshold)    -> the sweep current is gated off and
*                                       vcoarse holds
*
* -------------------------------------------------------------------------
* Why the sweep runs slow-to-fast and not fast-to-slow
*
* This is not arbitrary and it is easy to get backwards.  While unlocked,
* vctrl is railed at the *top* of the fine loop's range.  Capture therefore
* happens at the instant the ring can just reach the baud rate with vctrl at
* its maximum -- that is, with vctrl still high, still above any sensible lock
* threshold.  The sweep must keep running a little longer, and it must run in
* the direction that lets the fine loop *reduce* vctrl to hold lock.  Sweeping
* the ring slow-to-fast does exactly that: after capture the ring keeps
* speeding up, the fine loop backs vctrl down, and the sweep stops itself when
* vctrl crosses the threshold from above.
*
* Sweeping fast-to-slow would capture at the same railed vctrl and then demand
* that the fine loop raise vctrl further to keep up.  There is no headroom
* there, and lock would break immediately.
* -------------------------------------------------------------------------
*
* Hysteresis: the loop starts sweeping when vctrl rises past ~0.85 V and stops
* when it falls past ~0.65 V.  Two separate thresholds, because one threshold
* would have to sit above the fine loop's worst ripple (65 mV pp on PRBS7) and
* below the value at which the sweep must stop, and those two constraints
* leave no room.  The hysteresis is made by switching the divider tap rather
* than by feeding the comparator output back into its own input pair, which
* keeps the comparator itself a plain five-transistor cell.

.param Wres=0.5u
* R = 1360*L/(W - 0.04u) + 1.6e-4/W, from the PDK's own expression at b=0.
.func Lr(rv) '(rv - 1.6e-4/Wres) * (Wres - 0.04u) / 1360'

.param Rlk_t=117000            $ VDD .. vh      -> vh = 0.85 V
.param Rlk_b=283000            $ vh  .. VSS
.param Rlk_h=271000            $ vh  .. hysteresis switch -> vh = 0.65 V
.param Rwr_t=283000            $ VDD .. vw      -> vw = 0.30 V
.param Rwr_b=97000             $ vw  .. VSS
.param Rwr_h=36500             $ VDD .. hysteresis switch -> vw = 0.90 V

.param Ccrs_W=8u
.param Ccrs_L=8u
.param Ccrs_m=6                $ 8 x 8 x 6 = 384 um2 at 12.7 fF/um2 = 4.9 pF

.subckt coarse_loop VDD VSS ibias vctrl vcoarse
*
* === bias ================================================================
* ibias is the gate of the chip's 40 uA diode-connected reference (W=4 L=1).
* The sweep needs 20 nA, which is 1:2000.  One stage of that would want a 25 um
* channel; two stages of 1:40 and 1:50 cost two devices and no area.
XMB1 nb1 ibias VSS VSS sg13_lv_nmos w=0.5u l=5u ng=1 m=1 mm_ok=1   $ 1 uA
XMB2 nb1 nb1   VDD VDD sg13_lv_pmos w=2u   l=1u ng=1 m=1 mm_ok=1
XMB3 nb2 nb1   VDD VDD sg13_lv_pmos w=0.2u l=5u ng=1 m=1 mm_ok=1   $ 20 nA
XMB4 nb2 nb2   VSS VSS sg13_lv_nmos w=0.2u l=5u ng=1 m=1 mm_ok=1   $ nb2 = 20 nA
*                                                                     n-side bias
* === lock detector =======================================================
XRLT VDD vh  sub! rhigh w='Wres' l='Lr(Rlk_t)' m=1 b=0 mm_ok=1
XRLB vh  VSS sub! rhigh w='Wres' l='Lr(Rlk_b)' m=1 b=0 mm_ok=1
XRLH vh  nlh sub! rhigh w='Wres' l='Lr(Rlk_h)' m=1 b=0 mm_ok=1
XMLH nlh swp VSS VSS sg13_lv_nmos w=1u l=0.3u ng=1 m=1 mm_ok=1
*
* Five-transistor comparator.  nlk goes LOW when vctrl > vh.
XMLT slk ibias VSS VSS sg13_lv_nmos w=0.5u l=5u ng=1 m=1 mm_ok=1   $ 1 uA tail
XML1 nl1 vh    slk VSS sg13_lv_nmos w=4u l=0.3u ng=1 m=1 mm_ok=1
XML2 nlk vctrl slk VSS sg13_lv_nmos w=4u l=0.3u ng=1 m=1 mm_ok=1
XMLP1 nl1 nl1 VDD VDD sg13_lv_pmos w=4u l=0.3u ng=1 m=1 mm_ok=1
XMLP2 nlk nl1 VDD VDD sg13_lv_pmos w=4u l=0.3u ng=1 m=1 mm_ok=1
* One inverter squares nlk up: swp is HIGH while unlocked.
XMI1N swp nlk VSS VSS sg13_lv_nmos w=1u l=0.13u ng=1 m=1 mm_ok=1
XMI1P swp nlk VDD VDD sg13_lv_pmos w=2u l=0.13u ng=1 m=1 mm_ok=1
* and a second restores the polarity the sweep switch needs (LOW = sweeping).
XMI2N swpn swp VSS VSS sg13_lv_nmos w=1u l=0.13u ng=1 m=1 mm_ok=1
XMI2P swpn swp VDD VDD sg13_lv_pmos w=2u l=0.13u ng=1 m=1 mm_ok=1
*
* === the sweep current ===================================================
* 20 nA out of vcoarse, in series with a switch.  The switch is below the
* current source so the source keeps its drain voltage and stays in saturation.
XMSW vcoarse swp   nsw VSS sg13_lv_nmos w=1u   l=0.13u ng=1 m=1 mm_ok=1
XMSI nsw     nb2   VSS VSS sg13_lv_nmos w=0.2u l=5u    ng=1 m=1 mm_ok=1
*
* === wrap ================================================================
* vw is 0.30 V normally and 0.90 V while the reset is asserted, so the reset
* runs from 0.30 up to 0.90 and then releases -- a relaxation retrace, not a
* comparator sitting on its own trip point.
XRWT VDD vw  sub! rhigh w='Wres' l='Lr(Rwr_t)' m=1 b=0 mm_ok=1
XRWB vw  VSS sub! rhigh w='Wres' l='Lr(Rwr_b)' m=1 b=0 mm_ok=1
XRWH nwh vw  sub! rhigh w='Wres' l='Lr(Rwr_h)' m=1 b=0 mm_ok=1
XMWH nwh rstn VDD VDD sg13_lv_pmos w=2u l=0.3u ng=1 m=1 mm_ok=1
*
* nwk goes LOW when vcoarse < vw.
XMWT swk ibias VSS VSS sg13_lv_nmos w=0.5u l=5u ng=1 m=1 mm_ok=1   $ 1 uA tail
XMW1 nw1 vcoarse swk VSS sg13_lv_nmos w=4u l=0.3u ng=1 m=1 mm_ok=1
XMW2 nwk vw      swk VSS sg13_lv_nmos w=4u l=0.3u ng=1 m=1 mm_ok=1
XMWP1 nw1 nw1 VDD VDD sg13_lv_pmos w=4u l=0.3u ng=1 m=1 mm_ok=1
XMWP2 nwk nw1 VDD VDD sg13_lv_pmos w=4u l=0.3u ng=1 m=1 mm_ok=1
* rst is HIGH while retracing.  Both switches it drives are pMOS, so what
* they actually need is rstn, and the second inverter is there for that.
XMI3N rst  nwk VSS VSS sg13_lv_nmos w=1u l=0.13u ng=1 m=1 mm_ok=1
XMI3P rst  nwk VDD VDD sg13_lv_pmos w=2u l=0.13u ng=1 m=1 mm_ok=1
XMI4N rstn rst VSS VSS sg13_lv_nmos w=1u l=0.13u ng=1 m=1 mm_ok=1
XMI4P rstn rst VDD VDD sg13_lv_pmos w=2u l=0.13u ng=1 m=1 mm_ok=1
* The retrace device.  W is deliberately small: the retrace still takes only
* tens of nanoseconds against 5 pF, and a strong device would couple its own
* switching edge into vcoarse.
XMRST vcoarse rstn VDD VDD sg13_lv_pmos w=2u l=0.3u ng=1 m=1 mm_ok=1
*
* === the integrator ======================================================
* Two pins: gate, substrate.  Needs cornerMOSCAP.lib in the deck.
XCC vcoarse VSS sg13_moscap_n w='Ccrs_W' l='Ccrs_L' m='Ccrs_m' mm_ok=1
.ends
