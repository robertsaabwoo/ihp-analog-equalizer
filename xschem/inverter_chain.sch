v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 80 -50 80 -10 {
lab=#net1}
N 40 -80 40 20 {
lab=weak_in}
N 40 -80 40 20 {
lab=weak_in}
N 80 -140 80 -110 {
lab=VDD}
N 80 -80 160 -80 {
lab=VDD}
N 160 -140 160 -80 {
lab=VDD}
N 80 -140 160 -140 {
lab=VDD}
N 80 20 150 20 {
lab=VSS}
N 150 20 150 50 {
lab=VSS}
N 150 50 150 70 {
lab=VSS}
N 80 70 150 70 {
lab=VSS}
N 80 50 80 70 {
lab=VSS}
N -10 -30 40 -30 {
lab=weak_in}
N 80 -20 220 -20 {
lab=#net1}
N 310 -40 310 0 {
lab=#net2}
N 270 -70 270 30 {
lab=#net1}
N 270 -70 270 30 {
lab=#net1}
N 310 -130 310 -100 {
lab=VDD}
N 310 -70 390 -70 {
lab=VDD}
N 390 -130 390 -70 {
lab=VDD}
N 310 -130 390 -130 {
lab=VDD}
N 310 30 380 30 {
lab=VSS}
N 380 30 380 60 {
lab=VSS}
N 380 60 380 80 {
lab=VSS}
N 310 80 380 80 {
lab=VSS}
N 310 60 310 80 {
lab=VSS}
N 220 -20 270 -20 {
lab=#net1}
N 530 -30 530 10 {
lab=STRONG_OUT}
N 490 -60 490 40 {
lab=#net2}
N 490 -60 490 40 {
lab=#net2}
N 530 -120 530 -90 {
lab=VDD}
N 530 -60 610 -60 {
lab=VDD}
N 610 -120 610 -60 {
lab=VDD}
N 530 -120 610 -120 {
lab=VDD}
N 530 40 600 40 {
lab=VSS}
N 600 40 600 70 {
lab=VSS}
N 600 70 600 90 {
lab=VSS}
N 530 90 600 90 {
lab=VSS}
N 530 70 530 90 {
lab=VSS}
N 530 0 670 0 {
lab=STRONG_OUT}
N 310 -10 490 -10 {
lab=#net2}
C {devices/iopin.sym} -260 -90 0 0 {name=p1 lab=VDD


}
C {devices/iopin.sym} -260 -60 0 0 {name=p2 lab=VSS


}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} 60 -80 0 0 {name=M1
l=0.13u
w=2u
ng=1
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 60 20 0 0 {name=M2
l=0.13u
w=1u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 80 -140 0 0 {name=p3 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 80 70 0 0 {name=p4 sig_type=std_logic lab=VSS}
C {devices/ipin.sym} -10 -30 0 0 {name=p9 lab=weak_in
}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} 290 -70 0 0 {name=M3
l=0.13u
w=6u
ng=4
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 290 30 0 0 {name=M4
l=0.13u
w=3u
ng=2
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 310 -130 0 0 {name=p5 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 310 80 0 0 {name=p6 sig_type=std_logic lab=VSS}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} 510 -60 0 0 {name=M5
l=0.13u
w=16u
ng=8
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 510 40 0 0 {name=M6
l=0.13u
w=8u
ng=4
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 530 -120 0 0 {name=p7 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 530 90 0 0 {name=p8 sig_type=std_logic lab=VSS}
C {devices/opin.sym} 670 0 0 0 {name=p10 lab=STRONG_OUT}
