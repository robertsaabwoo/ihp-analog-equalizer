* bg_p.inc -- tiny_pll_bias_gen with its four mirror/diode devices lengthened
* by Lb (W scaled with it, so W/L and every mirror ratio are unchanged).
*
* At tt/125C the pMOS bias VDD - bias_p rises 0.411 -> 0.507 V over 1.08 ->
* 1.32 V supply while bias_n barely moves, so the up current runs away (3137 vs
* 2142 nA) and total pump current reaches ~4x nominal.  A Vds-sensitivity
* problem in the reference, so the first thing to try is channel length.
* The pump sources (cp_p.inc) are lengthened by the same factor via Ls.
.param Lb=1
.subckt bg_p VGND VNB VPWR VPB bias_n en enb bias_p
*.iopin VNB
*.iopin VGND
*.iopin VPB
*.iopin VPWR
*.opin bias_n
*.ipin enb
*.ipin en
*.opin bias_p
XMNMIR bias_p bias_n VGND VNB sg13_lv_nmos w='1*Lb*1u' l='Lb*1u' ng=1 m=1 mm_ok=1
XMNDIO bias_n bias_n VGND VNB sg13_lv_nmos w='1*Lb*1u' l='Lb*1u' ng=1 m=1 mm_ok=1
XMPDIO bias_p bias_p VPWR VPB sg13_lv_pmos w='2*Lb*1u' l='Lb*1u' ng=1 m=1 mm_ok=1
XMPMIR bias_n bias_p res_bot VPB sg13_lv_pmos w='2*Lb*1u' l='Lb*1u' ng=1 m=2 mm_ok=1
* noconn VPB
XMNEN1 bias_n enb VGND VNB sg13_lv_nmos w=0.5u l=0.13u ng=1 m=1 mm_ok=1
XMPEN1 bias_p en VPWR VPB sg13_lv_pmos w=0.5u l=0.13u ng=1 m=1 mm_ok=1
XRES VGND VNB VPWR VPB VPWR res_bot tiny_pll_bias_gen_res
XMNSU1 kick bias_n VGND VNB sg13_lv_nmos w=1u l=1u ng=1 m=1 mm_ok=1
XMNSU2 bias_p kick kick_sw VNB sg13_lv_nmos w=0.5u l=0.13u ng=1 m=1 mm_ok=1
XMNEN2 kick_sw en VGND VNB sg13_lv_nmos w=0.5u l=0.13u ng=1 m=1 mm_ok=1
XMPEN2 kick en VPWR VPB sg13_lv_pmos w=0.5u l=0.13u ng=1 m=1 mm_ok=1
XMPSU2 kick kick dio_mid VPB sg13_lv_pmos w=0.5u l=0.13u ng=1 m=1 mm_ok=1
XMPSU1 dio_mid dio_mid VPWR VPB sg13_lv_pmos w=0.5u l=0.13u ng=1 m=1 mm_ok=1
.ends
