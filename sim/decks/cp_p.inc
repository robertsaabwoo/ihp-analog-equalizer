* cp_p.inc -- tiny_pll_charge_pump with its current-source geometry exposed.
*
* Measured mismatch at vout = 0.6 V: up 895.2 nA, down 796.5 nA, 12.4 %.  During
* PRBS7's seven-bit blind runs the phase detector says nothing and that
* difference integrates unopposed; the resulting frequency walk scales with
* Kvco.  At 10000 ohm that took the recovered clock to 609.96 MHz (+1.56 %).
*
* The source devices mirror diodes in tiny_pll_bias_gen that sit at fixed Vds
* (|Vgs|: 0.43 V pMOS, 0.29 V nMOS) while the sources themselves see Vds set by
* vctrl.  So the mismatch is a channel-length-modulation effect and moves with
* vctrl.  Wp trims the up current; Ls lengthens both sources (W scaled to keep
* W/L) to cut the Vds sensitivity itself.
.param Wp=2 Wn=1 Ls=1
.subckt cp_p VPWR VPB VGND VNB out up down bias_n bias_p
XMNSRC src_n bias_n VGND VNB sg13_lv_nmos w='Wn*Ls*1u' l='Ls*1u' ng=1 m=1 mm_ok=1
XMNSW out down src_n VNB sg13_lv_nmos w=0.5u l=0.13u ng=1 m=1 mm_ok=1
XMPSW out upb src_p VPB sg13_lv_pmos w=1u l=0.13u ng=1 m=1 mm_ok=1
XMPSRC src_p bias_p VPWR VPB sg13_lv_pmos w='Wp*Ls*1u' l='Ls*1u' ng=1 m=1 mm_ok=1
XINV up upb VPWR VGND inv_cp
.ends
