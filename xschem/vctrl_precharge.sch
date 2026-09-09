v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {vctrl startup precharge (POR one-shot)

  R1+MCPOR : RC power-on ramp.  nrc starts at 0 (cap discharged at power-up)
             and charges to VDD -> sets the precharge HOLD TIME.
  INV_A/B  : nrc -> pre (HIGH during hold), pre -> preb (LOW during hold).
  MBP+MBD  : enabled current source into a diode-connected NMOS =>
             nbias = Vgs(MBD) ~ 0.79 V.  MBD is an M5 (ring tail) replica,
             so the seed TRACKS the VCO dead-zone cliff over PVT.
  MSW      : switch that holds VCTL at nbias, then opens and leaves the
             loop filter completely alone (gate hard at 0 V).

  MSW opens BEFORE the bias branch collapses (INV_B delay) so the
  release is glitch-free.} 40 -320 0 0 0.4 0.4 {}
N 0 -70 0 -30 {
lab=VDD}
N 0 30 0 70 {
lab=nrc}
N -20 0 -80 0 {
lab=VSS}
N 180 0 120 0 {
lab=nrc}
N 220 -30 300 -30 {
lab=VSS}
N 220 30 300 30 {
lab=VSS}
N 380 -100 320 -100 {
lab=nrc}
N 420 -130 500 -130 {
lab=VDD}
N 420 -100 500 -100 {
lab=VDD}
N 420 -70 500 -70 {
lab=pre}
N 380 100 320 100 {
lab=nrc}
N 420 70 500 70 {
lab=pre}
N 420 100 500 100 {
lab=VSS}
N 420 130 500 130 {
lab=VSS}
N 680 -100 620 -100 {
lab=pre}
N 720 -130 800 -130 {
lab=VDD}
N 720 -100 800 -100 {
lab=VDD}
N 720 -70 800 -70 {
lab=preb}
N 680 100 620 100 {
lab=pre}
N 720 70 800 70 {
lab=preb}
N 720 100 800 100 {
lab=VSS}
N 720 130 800 130 {
lab=VSS}
N 980 -100 920 -100 {
lab=preb}
N 1020 -130 1100 -130 {
lab=VDD}
N 1020 -100 1100 -100 {
lab=VDD}
N 1020 -70 1100 -70 {
lab=nbias}
N 980 100 920 100 {
lab=nbias}
N 1020 70 1100 70 {
lab=nbias}
N 1020 100 1100 100 {
lab=VSS}
N 1020 130 1100 130 {
lab=VSS}
N 1280 0 1220 0 {
lab=pre}
N 1320 -30 1400 -30 {
lab=nbias}
N 1320 0 1400 0 {
lab=VSS}
N 1320 30 1400 30 {
lab=VCTL}
C {devices/iopin.sym} -200 -220 0 0 {name=p1 lab=VDD}
C {devices/iopin.sym} -200 -180 0 0 {name=p2 lab=VSS}
C {devices/iopin.sym} -200 -140 0 0 {name=p3 lab=VCTL}
C {sg13cmos5l_pr/rhigh.sym} 0 0 0 0 {name=R1
w=1.000000e-06
l=1.692988e-04
model=rhigh
body=sub!
spiceprefix=X
b=0
m=1
mm_ok=1}
C {devices/lab_wire.sym} 0 -70 0 0 {name=l1 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 0 70 0 0 {name=l2 sig_type=std_logic lab=nrc}
C {devices/lab_wire.sym} -80 0 0 0 {name=l3 sig_type=std_logic lab=VSS}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 200 0 0 0 {name=MCPOR
l=8u
w=8u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 120 0 0 0 {name=l4 sig_type=std_logic lab=nrc}
C {devices/lab_wire.sym} 300 -30 0 0 {name=l5 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 300 30 0 0 {name=l6 sig_type=std_logic lab=VSS}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} 400 -100 0 0 {name=MP1
l=1u
w=1u
ng=1
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {devices/lab_wire.sym} 320 -100 0 0 {name=l7 sig_type=std_logic lab=nrc}
C {devices/lab_wire.sym} 500 -130 0 0 {name=l8 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 500 -100 0 0 {name=l9 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 500 -70 0 0 {name=l10 sig_type=std_logic lab=pre}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 400 100 0 0 {name=MN1
l=1u
w=0.5u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 320 100 0 0 {name=l11 sig_type=std_logic lab=nrc}
C {devices/lab_wire.sym} 500 70 0 0 {name=l12 sig_type=std_logic lab=pre}
C {devices/lab_wire.sym} 500 100 0 0 {name=l13 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 500 130 0 0 {name=l14 sig_type=std_logic lab=VSS}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} 700 -100 0 0 {name=MP2
l=0.13u
w=2u
ng=1
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {devices/lab_wire.sym} 620 -100 0 0 {name=l15 sig_type=std_logic lab=pre}
C {devices/lab_wire.sym} 800 -130 0 0 {name=l16 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 800 -100 0 0 {name=l17 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 800 -70 0 0 {name=l18 sig_type=std_logic lab=preb}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 700 100 0 0 {name=MN2
l=0.13u
w=1u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 620 100 0 0 {name=l19 sig_type=std_logic lab=pre}
C {devices/lab_wire.sym} 800 70 0 0 {name=l20 sig_type=std_logic lab=preb}
C {devices/lab_wire.sym} 800 100 0 0 {name=l21 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 800 130 0 0 {name=l22 sig_type=std_logic lab=VSS}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} 1000 -100 0 0 {name=MBP
l=1u
w=6u
ng=1
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {devices/lab_wire.sym} 920 -100 0 0 {name=l23 sig_type=std_logic lab=preb}
C {devices/lab_wire.sym} 1100 -130 0 0 {name=l24 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 1100 -100 0 0 {name=l25 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 1100 -70 0 0 {name=l26 sig_type=std_logic lab=nbias}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 1000 100 0 0 {name=MBD
l=0.13u
w=6u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 920 100 0 0 {name=l27 sig_type=std_logic lab=nbias}
C {devices/lab_wire.sym} 1100 70 0 0 {name=l28 sig_type=std_logic lab=nbias}
C {devices/lab_wire.sym} 1100 100 0 0 {name=l29 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 1100 130 0 0 {name=l30 sig_type=std_logic lab=VSS}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 1300 0 0 0 {name=MSW
l=0.6u
w=8u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 1220 0 0 0 {name=l31 sig_type=std_logic lab=pre}
C {devices/lab_wire.sym} 1400 -30 0 0 {name=l32 sig_type=std_logic lab=nbias}
C {devices/lab_wire.sym} 1400 0 0 0 {name=l33 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 1400 30 0 0 {name=l34 sig_type=std_logic lab=VCTL}
C {devices/lab_wire.sym} 220 0 0 0 {name=p9001 sig_type=std_logic lab=VSS}
