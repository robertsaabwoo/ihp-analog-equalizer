* cp_bias_p.inc -- charge-pump bias from the chip's ibias reference (option 1,
* chosen by the user 2026-09-15).  Parameterised copy for sizing; cp_bias.inc is
* the fixed-size cell once Lm is chosen.
*
* Replaces tiny_pll_bias_gen, a self-biased reference whose current rises 2.3x at
* tt/125 C and ~10x at ff/125 C/1.32 V (run_cp_cur.out).  That loop gain is what
* stopped lock at 125 C: with ideal nominal currents in its place tt/125 C locks
* at 600.550 MHz (e2e_prbs_tt125_idealbias.log).  This cell reproduces that ideal
* bias from a mirror of the 40 uA reference instead:
*   vbias is the gate of ibias_mirror's W4/L1 diode carrying 40 uA.
*   XMN1 mirrors ~1/45 of it (target 889 nA) into bias_p's pMOS diode (W2/L1),
*     so the pump's 1.8 um up source gives ~800 nA.
*   XMP2 (W1.8/L1) copies 0.9x of that into bias_n's nMOS diode (W1/L1), so
*     the pump's W1/L1 down source also gives ~800 nA.
.param Wm=0.5 Lm=5 Wp2=1.8
.subckt cp_bias VDD VSS vbias bias_n bias_p
XMN1 bias_p vbias  VSS VSS sg13_lv_nmos w='Wm*1e-6' l='Lm*1e-6' ng=1 m=1 mm_ok=1
XMPD bias_p bias_p VDD VDD sg13_lv_pmos w=2u   l=1u ng=1 m=1 mm_ok=1
XMP2 bias_n bias_p VDD VDD sg13_lv_pmos w='Wp2*1e-6' l=1u ng=1 m=1 mm_ok=1
XMND bias_n bias_n VSS VSS sg13_lv_nmos w=1u   l=1u ng=1 m=1 mm_ok=1
.ends
