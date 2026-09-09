v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N -50 -20 -50 20 {
lab=#net1}
N -90 -50 -90 50 {
lab=#net2}
N -90 -50 -90 50 {
lab=#net2}
N -50 -110 -50 -80 {
lab=VDD}
N -50 -50 30 -50 {
lab=VDD}
N 30 -110 30 -50 {
lab=VDD}
N -50 -110 30 -110 {
lab=VDD}
N -50 50 20 50 {
lab=VSS}
N 20 50 20 80 {
lab=VSS}
N 20 80 20 100 {
lab=VSS}
N -50 100 20 100 {
lab=VSS}
N -50 80 -50 100 {
lab=VSS}
N -140 0 -90 0 {
lab=#net2}
N 170 -10 170 30 {
lab=STRONG_OUT}
N 130 -40 130 60 {
lab=#net1}
N 130 -40 130 60 {
lab=#net1}
N 170 -100 170 -70 {
lab=VDD}
N 170 -40 250 -40 {
lab=VDD}
N 250 -100 250 -40 {
lab=VDD}
N 170 -100 250 -100 {
lab=VDD}
N 170 60 240 60 {
lab=VSS}
N 240 60 240 90 {
lab=VSS}
N 240 90 240 110 {
lab=VSS}
N 170 110 240 110 {
lab=VSS}
N 170 90 170 110 {
lab=VSS}
N 170 20 310 20 {
lab=STRONG_OUT}
N -50 10 130 10 {
lab=#net1}
C {devices/iopin.sym} -620 -70 0 0 {name=p1 lab=VDD


}
C {devices/iopin.sym} -620 -40 0 0 {name=p2 lab=VSS


}
C {devices/ipin.sym} -140 0 0 0 {name=p9 lab=weak_in
}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} -70 -50 0 0 {name=M3
l=0.13u
w=6u
ng=4
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} -70 50 0 0 {name=M4
l=0.13u
w=7u
ng=2
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} -50 -110 0 0 {name=p5 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} -50 100 0 0 {name=p6 sig_type=std_logic lab=VSS}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} 150 -40 0 0 {name=M5
l=0.13u
w=16u
ng=8
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 150 60 0 0 {name=M6
l=0.13u
w=8u
ng=4
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 170 -100 0 0 {name=p7 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 170 110 0 0 {name=p8 sig_type=std_logic lab=VSS}
C {devices/opin.sym} 310 20 0 0 {name=p10 lab=STRONG_OUT}
