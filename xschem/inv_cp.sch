v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N -60 0 -20 0 {
lab=A}
N -20 -40 -20 40 {
lab=A}
N 20 -10 20 10 {
lab=Y}
N 20 0 60 0 {
lab=Y}
C {devices/ipin.sym} -60 0 0 0 {name=p1 lab=A}
C {devices/opin.sym} 60 0 0 0 {name=p2 lab=Y}
C {devices/iopin.sym} -140 -60 0 0 {name=p3 lab=VPWR}
C {devices/iopin.sym} -140 -30 0 0 {name=p4 lab=VGND}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} 0 -40 0 0 {name=MP
l=0.13u
w=2u
ng=1
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 0 40 0 0 {name=MN
l=0.13u
w=1u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 20 -70 0 0 {name=p5 sig_type=std_logic lab=VPWR}
C {devices/lab_wire.sym} 20 -40 0 0 {name=p6 sig_type=std_logic lab=VPWR}
C {devices/lab_wire.sym} 20 70 0 0 {name=p7 sig_type=std_logic lab=VGND}
C {devices/lab_wire.sym} 20 40 0 0 {name=p8 sig_type=std_logic lab=VGND}
