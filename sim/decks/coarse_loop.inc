* coarse_loop.inc -- the coarse frequency loop for the CDR ring.
*
* Three measurements shaped this circuit and none of them was predictable from
* the schematic.  docs/RING_DUAL_LOOP.md has them in full; in short:
*
*  1. Out of band, vctrl ramps *up* whether the ring is 4 % too slow or 12 %
*     too fast, so there is no sign information in it and a plain bidirectional
*     trim cannot acquire.  It can only hold.
*  2. Locked, vctrl is flat to half a millivolt per microsecond and does carry
*     the sign -- it is exactly the error the fine loop is correcting.  So a
*     bidirectional trim is right for holding, and only for holding.
*  3. A MOS capacitor cannot hold this node at all: 384 um2 of moscap_n leaks
*     773 pA of gate tunnelling current, which is 184 mV/ms on its own 4.19 pF.
*
* So the loop is one integrator driven by a window comparator, plus a wrap:
*
*   vctrl > VH  -> sink from Ccoarse -> vcoarse falls -> the trim pMOS across
*                  each ring load turns on harder -> the ring speeds up
*   vctrl < VL  -> source into Ccoarse -> the ring slows down
*   in between  -> both pairs steered to their dump branch, no net current
*   vcoarse at the bottom -> retrace to the top in tens of ns and continue
*
* The same pull-down branch does two jobs.  Out of band it is an acquisition
* sweep: vctrl is railed high, so it ramps vcoarse continuously and the wrap
* turns that ramp into a repeating search of the whole coarse range.  In lock
* it is half of a window trim that keeps vctrl off the rails and cancels the
* leakage the capacitor and switches still have.  Nothing has to switch between
* the two modes because the direction the pull-down wants out of band is the
* same direction it wants when the ring is merely a little slow.
*
* -------------------------------------------------------------------------
* Why the search runs slow-to-fast
*
* While unlocked, vctrl is railed at the *top* of the fine loop's range, so
* capture happens at the instant the ring can just reach the baud rate at
* maximum tail current -- with vctrl still high.  The search must then keep
* going in the direction that lets the fine loop *reduce* vctrl to hold lock.
* Searching slow-to-fast does that.  Searching fast-to-slow would capture at
* the same railed vctrl and then need headroom above the rail, which does not
* exist, so lock would break immediately.  The pull-down branch ramps vcoarse
* down, the trim turns on, the ring speeds up: slow to fast.
* -------------------------------------------------------------------------
*
* Why the two halves of the window comparator are not symmetric
*
* The pull-UP is a bare pMOS pair.  A pMOS pair steers toward the *lower* gate,
* so with vctrl on one input and VL on the other, vctrl < VL puts the tail
* current straight onto vcoarse.  No mirror.
*
* The pull-DOWN cannot be the mirror image.  A bare nMOS pair's output device
* has its source at vctrl - Vgs, so it stops sinking once vcoarse falls to
* about 0.55 V -- and the bottom of the range is exactly where a ring that
* cannot reach the baud rate needs to go.  So it folds through a pMOS mirror
* and then an nMOS mirror whose output device sits on VSS and keeps sinking
* down to a hundred millivolts.  Four devices to buy back the range.
*
* The wrap comparator has a pMOS input pair for the same reason read the other
* way: its trip point is at the bottom of the vcoarse range, where an nMOS pair
* has no common-mode room at all.

.param Wres=0.5u
* R = 1360*L/(W - 0.04u) + 1.6e-4/W, from the PDK's own expression at b=0.
.func Lr(rv) '(rv - 1.6e-4/Wres) * (Wres - 0.04u) / 1360'

* Window: VH = 0.70 V, VL = 0.52 V.  Locked vctrl is 0.599 V (e2e_lock_tt.log)
* and the worst measured ripple is 65 mV pp on PRBS7 (e2e_prbs.log), so +-33 mV
* about 0.599 clears both edges by about 70 mV.
.param Rlk_t=175000            $ VDD .. vh
.param Rlk_m=45000             $ vh  .. vl
.param Rlk_b=180000            $ vl  .. VSS
* Wrap: trips at 0.15 V, retraces to 0.85 V.
.param Rwr_t=350000            $ VDD .. vw
.param Rwr_b=50000             $ vw  .. VSS
.param Rwr_h=21900             $ VDD .. retrace switch, in parallel with Rwr_t

* Ccoarse is cap_cmomf, not a MOS capacitor.  See the header: a MOS capacitor
* of the same value drifts 184 mV/ms on its own leakage, which walks the whole
* 0.7 V trim range in four milliseconds.  cap_cmomf is 1.29 fF/um2 against
* 12.7, so this costs 1000 um2 -- comparable to the CTLE's degeneration
* capacitor, which is already the largest object in the design.
.param Ccrs_S=28.5u            $ 28.5 um square = 812 um2 = 1.05 pF

* Both branches of the window comparator run at 20 nA, which with 1.05 pF is
* 19 mV/us and a full 0.7 V search in 37 us.  Ksweep scales that for
* simulation: a closed-loop transient long enough to show a real acquisition
* would cost hours on this machine, so the closed-loop decks raise it and the
* open-loop deck checks the real value.  Ksweep is a *simulation* knob and must
* be 1 in anything that claims a silicon number.
.param Ksweep=1
.param Wsrc='0.2u*Ksweep'

.subckt coarse_loop VDD VSS ibias vctrl vcoarse
*
* === bias ================================================================
* ibias is the gate of the chip's 40 uA diode-connected reference (W=4 L=1).
* 20 nA is 1:2000 of that.  One stage would want a 25 um channel; two stages of
* 1:40 and 1:50 cost two devices and no area.
XMB1 nb1 ibias VSS VSS sg13_lv_nmos w=0.5u   l=5u ng=1 m=1 mm_ok=1   $ 1 uA
XMB2 nb1 nb1   VDD VDD sg13_lv_pmos w=2u     l=1u ng=1 m=1 mm_ok=1
XMB3 nb2 nb1   VDD VDD sg13_lv_pmos w='Wsrc' l=5u ng=1 m=1 mm_ok=1   $ 20 nA
XMB4 nb2 nb2   VSS VSS sg13_lv_nmos w='Wsrc' l=5u ng=1 m=1 mm_ok=1
*
* === window thresholds ===================================================
* A divider off VDD, ~3 uA.  The thresholds track the supply, which is right:
* the locked vctrl scales with the supply too.
XRLT VDD vh  sub! rhigh w='Wres' l='Lr(Rlk_t)' m=1 b=0 mm_ok=1
XRLM vh  vl  sub! rhigh w='Wres' l='Lr(Rlk_m)' m=1 b=0 mm_ok=1
XRLB vl  VSS sub! rhigh w='Wres' l='Lr(Rlk_b)' m=1 b=0 mm_ok=1
*
* === pull-up: vctrl < VL, ring too fast, slow it down =====================
XMTU spu nb1   VDD VDD sg13_lv_pmos w='Wsrc' l=5u ng=1 m=1 mm_ok=1
XMU1 vcoarse vctrl spu VDD sg13_lv_pmos w=2u l=1u ng=1 m=1 mm_ok=1
XMU2 VSS     vl    spu VDD sg13_lv_pmos w=2u l=1u ng=1 m=1 mm_ok=1
*
* === pull-down: vctrl > VH, ring too slow (or not locked), speed it up ====
XMTD snd nb2   VSS VSS sg13_lv_nmos w='Wsrc' l=5u ng=1 m=1 mm_ok=1
XMD1 nd  vctrl snd VSS sg13_lv_nmos w=2u l=1u ng=1 m=1 mm_ok=1
XMD2 VDD vh    snd VSS sg13_lv_nmos w=2u l=1u ng=1 m=1 mm_ok=1
XMP1 nd  nd    VDD VDD sg13_lv_pmos w=1u l=2u ng=1 m=1 mm_ok=1
XMP2 ne  nd    VDD VDD sg13_lv_pmos w=1u l=2u ng=1 m=1 mm_ok=1
XMN1 ne  ne    VSS VSS sg13_lv_nmos w=0.5u l=2u ng=1 m=1 mm_ok=1
XMN2 vcoarse ne VSS VSS sg13_lv_nmos w=0.5u l=2u ng=1 m=1 mm_ok=1
*
* === wrap ================================================================
XRWT VDD vw  sub! rhigh w='Wres' l='Lr(Rwr_t)' m=1 b=0 mm_ok=1
XRWB vw  VSS sub! rhigh w='Wres' l='Lr(Rwr_b)' m=1 b=0 mm_ok=1
XRWH nwh vw  sub! rhigh w='Wres' l='Lr(Rwr_h)' m=1 b=0 mm_ok=1
XMWH nwh rstn VDD VDD sg13_lv_pmos w=2u l=0.3u ng=1 m=1 mm_ok=1
*
* pMOS input pair: the trip point is at the bottom of the vcoarse range, where
* an nMOS pair has no common-mode room.  nwk goes HIGH when vcoarse < vw.
XMWT swk nb1 VDD VDD sg13_lv_pmos w=2u l=1u ng=1 m=1 mm_ok=1        $ 1 uA tail
XMW1 nwk vcoarse swk VDD sg13_lv_pmos w=4u l=0.3u ng=1 m=1 mm_ok=1
XMW2 nw2 vw      swk VDD sg13_lv_pmos w=4u l=0.3u ng=1 m=1 mm_ok=1
XMWN1 nw2 nw2 VSS VSS sg13_lv_nmos w=2u l=0.3u ng=1 m=1 mm_ok=1
XMWN2 nwk nw2 VSS VSS sg13_lv_nmos w=2u l=0.3u ng=1 m=1 mm_ok=1
* Square it up and invert: rstn is LOW while retracing.
XMI1N rstn nwk VSS VSS sg13_lv_nmos w=1u l=0.13u ng=1 m=1 mm_ok=1
XMI1P rstn nwk VDD VDD sg13_lv_pmos w=2u l=0.13u ng=1 m=1 mm_ok=1
* The retrace device.  W is deliberately small: against ~1 pF the retrace still
* takes only tens of nanoseconds, and a strong device would couple its own
* switching edge into vcoarse.
XMRST vcoarse rstn VDD VDD sg13_lv_pmos w=2u l=0.3u ng=1 m=1 mm_ok=1
*
* === the integrator ======================================================
XCC vcoarse VSS cap_cmomf w='Ccrs_S' l='Ccrs_S' mmin=1 mmax=4 subblock=0 m=1 mm_ok=1
.ends
