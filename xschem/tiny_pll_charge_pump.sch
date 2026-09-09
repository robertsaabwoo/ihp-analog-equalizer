v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 0 -480 0 -400 {
lab=src_p}
N 0 -340 0 -260 {
lab=out}
N 0 -200 0 -120 {
lab=src_n}
N -220 -370 -180 -370 {
lab=up}
N -100 -370 -40 -370 {
lab=upb}
N -100 -230 -40 -230 {
lab=down}
N -100 -90 -40 -90 {
lab=bias_n}
N 0 -60 0 0 {
lab=VGND}
N -100 -510 -40 -510 {
lab=bias_p}
N 0 -600 0 -540 {
lab=VPWR}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} -20 -90 0 0 {name=MNSRC
l=1u
w=1u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} -20 -230 0 0 {name=MNSW
l=0.13u
w=0.5u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} -20 -370 0 0 {name=MPSW
l=0.13u
w=1u
ng=1
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} -20 -510 0 0 {name=MPSRC
l=1u
w=2u
ng=1
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {devices/lab_wire.sym} 0 -600 3 0 {name=p1 sig_type=std_logic lab=VPWR}
C {devices/lab_wire.sym} -100 -90 0 1 {name=p3 sig_type=std_logic lab=bias_n}
C {devices/lab_wire.sym} -100 -510 0 1 {name=p4 sig_type=std_logic lab=bias_p}
C {inv_cp.sym} -140 -370 0 0 {name=XINV}
C {devices/lab_wire.sym} -100 -230 0 1 {name=p6 sig_type=std_logic lab=down}
C {devices/lab_wire.sym} -60 -370 0 0 {name=p7 sig_type=std_logic lab=upb}
C {devices/lab_wire.sym} 0 -320 3 0 {name=p8 sig_type=std_logic lab=out}
C {devices/ipin.sym} 0 -720 0 0 {name=p29 lab=up}
C {devices/ipin.sym} 0 -700 0 0 {name=p34 lab=down}
C {devices/iopin.sym} 0 -760 0 1 {name=p37 lab=VNB}
C {devices/iopin.sym} 0 -780 0 1 {name=p38 lab=VGND}
C {devices/iopin.sym} 0 -800 0 1 {name=p39 lab=VPB}
C {devices/iopin.sym} 0 -820 0 1 {name=p40 lab=VPWR}
C {devices/opin.sym} 40 -720 0 0 {name=p46 lab=out}
C {devices/ipin.sym} 0 -680 0 0 {name=p10 lab=bias_n}
C {devices/lab_wire.sym} 0 0 3 1 {name=p2 sig_type=std_logic lab=VGND}
C {devices/lab_wire.sym} 0 -180 3 0 {name=p5 sig_type=std_logic lab=src_n}
C {devices/lab_wire.sym} -220 -370 0 1 {name=p9 sig_type=std_logic lab=up}
C {devices/ipin.sym} 0 -660 0 0 {name=p11 lab=bias_p}
C {devices/lab_wire.sym} 0 -460 3 0 {name=p12 sig_type=std_logic lab=src_p}
C {devices/lab_wire.sym} 0 -90 0 0 {name=p9001 sig_type=std_logic lab=VNB}
C {devices/lab_wire.sym} 0 -230 0 0 {name=p9002 sig_type=std_logic lab=VNB}
C {devices/lab_wire.sym} 0 -370 0 0 {name=p9003 sig_type=std_logic lab=VPB}
C {devices/lab_wire.sym} 0 -510 0 0 {name=p9004 sig_type=std_logic lab=VPB}
C {devices/lab_wire.sym} -140 -400 0 0 {name=p9005 sig_type=std_logic lab=VPWR}
C {devices/lab_wire.sym} -140 -340 0 0 {name=p9006 sig_type=std_logic lab=VGND}
