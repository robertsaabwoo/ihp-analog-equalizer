v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 170 -10 170 30 {
lab=OUT}
N 130 -40 130 60 {
lab=IN}
N 30 10 130 10 {
lab=IN}
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
lab=OUT}
C {devices/iopin.sym} -100 -70 0 0 {name=p1 lab=VDD
}
C {devices/iopin.sym} -100 -40 0 0 {name=p2 lab=VSS
}
C {devices/ipin.sym} 30 10 0 0 {name=p9 lab=IN
}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} 150 -40 0 0 {name=M1
l=0.13u
w=16u
ng=8
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 150 60 0 0 {name=M2
l=0.13u
w=8u
ng=4
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 170 -100 0 0 {name=p7 sig_type=std_logic lab=VDD}
C {devices/lab_wire.sym} 170 110 0 0 {name=p8 sig_type=std_logic lab=VSS}
C {devices/opin.sym} 310 20 0 0 {name=p10 lab=OUT}
