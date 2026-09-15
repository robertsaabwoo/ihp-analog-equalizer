* sb_inverter -- AC-coupled, self-biased inverter in front of the recovered-clock
* buffer (option 3, 2026-09-15).
*
* Why: clkraw (CDR x4 diff_amp_inv output) is a resistor-loaded swing whose low
* level rises with temperature -- 0.23-0.48 V at -40/27 C, 0.60-0.70 V at 125 C
* (clkpath_pvt_*.log) -- while inverter_buffer's switching point sits at
* 0.50-0.615 V (inv_trip_*.log).  At 125 C the buffer never switches and the
* clock is dead at every process corner.  No fixed threshold can work: the
* lowest high level (0.621 V, ff/-40C/1.08V) is below the highest low level
* (0.700 V, ss/125C/1.32V).
*
* How: Cc blocks clkraw's DC level; Rfb from the output back to the input holds
* the input at this inverter's own switching point, so the input is centred on
* the threshold at every corner and only the swing (>= 0.34 V measured) matters.
*   Cc  100 fF  (cap_cmomf, 8.8 um square, 1.29 fF/um2)
*   Rfb 100 kohm (rhigh W 1 um L 70 um, ~1.43 kohm/um)
*   tau = Rfb*(Cc+Cg) ~ 10 ns: corner ~16 MHz against a ring >= ~450 MHz
* Fed from clkraw- so its inversion restores clkraw+ polarity at rclk+.
.subckt sb_inverter VDD VSS in out
XCC  in   sbin cap_cmomf w=8.8u l=8.8u mmin=1 mmax=4 subblock=0 m=1 mm_ok=1
XRFB sbin out  sub! rhigh w=1.000000e-06 l=7.000000e-05 m=1 b=0 mm_ok=1
XMP  out  sbin VDD VDD sg13_lv_pmos w=2u l=0.13u ng=1 m=1 mm_ok=1
XMN  out  sbin VSS VSS sg13_lv_nmos w=1u l=0.13u ng=1 m=1 mm_ok=1
.ends
