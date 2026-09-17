* cp_bias -- charge-pump bias from the chip's ibias reference (option 1, chosen by
* the user 2026-09-15).  Replaces tiny_pll_bias_gen in CDR.
*
* Why: tiny_pll_bias_gen is a self-biased reference whose current -- and so the
* loop's integral gain -- rises 2.3x at tt/125 C and ~10x at ff/125 C/1.32 V
* (run_cp_cur.out: pump current 398-5684 nA across corners, mismatch to +74 %).
* With ideal nominal currents instead, tt/125 C locks at 600.550 MHz
* (e2e_prbs_tt125_idealbias.log).
*
* How: vbias is the gate of ibias_mirror's W4/L1 diode carrying the 40 uA
* reference.  XMN1 (W 0.25 / L 8 um) mirrors a small fraction into bias_p's pMOS
* diode; XMP2 (W 1.45 um) copies part of that into bias_n's nMOS diode.
*
* W 0.5 um.  0.25 um (half current) was tried to cut ripple: it did not help ff/-40 C and
* it cost tt/125 C its lock, because acquisition slows in proportion (EXPERIMENTS 2.18).  L stays 8 um
* -- L 16 um was tried first and test_device_geometry rejected it, PSP is characterised
* only to 10 um (the same trap that caught a 15 um device in the coarse loop).  At ff/-40 C/1.32 V
* the ring runs ~1200 MHz/V (loop_scurve_ffm40.log), so the loop's 48 mV of ripple was
* +-58 MHz -- wider than any capture window.  See docs/EXPERIMENTS.md.
* Sizing at L 8 um (cp_ibias_pvt2_{tt,ss,ff}.log, 27 corners x vout 0.5/0.6/0.7 V):
*   tt/27 C/1.2 V/0.6 V: up 790 nA, down 806 nA
*   all corners: up 715-894 nA, down 697-959 nA, mismatch -13.4 .. +10.3 %
* Lm 7 / 7.5 / 8 and XMP2 1.45 / 1.55 / 1.65 were swept; 1.45 centres the
* mismatch, whose ~24-point width is the pump's own output-voltage and
* temperature dependence.  Sweep 1 (cp_ibias_pvt_*.log, XMP2 1.8): Lm 6 gave
* ~1015 nA and -7 .. -27 %.
.subckt cp_bias VDD VSS vbias bias_n bias_p
XMN1 bias_p vbias  VSS VSS sg13_lv_nmos w=0.5u  l=8u ng=1 m=1 mm_ok=1
XMPD bias_p bias_p VDD VDD sg13_lv_pmos w=2u    l=1u ng=1 m=1 mm_ok=1
XMP2 bias_n bias_p VDD VDD sg13_lv_pmos w=1.45u l=1u ng=1 m=1 mm_ok=1
XMND bias_n bias_n VSS VSS sg13_lv_nmos w=1u    l=1u ng=1 m=1 mm_ok=1
.ends
