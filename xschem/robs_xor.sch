v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
N 1120 -260 1260 -260 {
lab=VDD}
N 1120 -110 1260 -110 {
lab=xor_out}
N 1120 -200 1120 -170 {
lab=#net1}
N 1260 -200 1260 -170 {
lab=#net2}
N 1200 -280 1200 -260 {
lab=VDD}
N 1120 -230 1170 -230 {
lab=VDD}
N 1170 -260 1170 -230 {
lab=VDD}
N 1210 -260 1210 -230 {
lab=VDD}
N 1210 -230 1260 -230 {
lab=VDD}
N 1120 -140 1160 -140 {
lab=VDD}
N 1160 -230 1160 -140 {
lab=VDD}
N 1220 -230 1220 -140 {
lab=VDD}
N 1220 -140 1260 -140 {
lab=VDD}
N 1120 20 1120 40 {
lab=#net3}
N 1270 20 1270 40 {
lab=#net4}
N 1120 -40 1270 -40 {
lab=xor_out}
N 1120 100 1270 100 {
lab=VSS}
N 1180 100 1180 140 {
lab=VSS}
N 1180 140 1200 140 {
lab=VSS}
N 1120 70 1160 70 {
lab=VSS}
N 1160 70 1160 100 {
lab=VSS}
N 1240 70 1240 100 {
lab=VSS}
N 1240 70 1270 70 {
lab=VSS}
N 1240 -10 1270 -10 {
lab=VSS}
N 1120 -10 1160 -10 {
lab=VSS}
N 1190 -110 1190 -40 {
lab=xor_out}
N 1240 -10 1240 70 {
lab=VSS}
N 1160 -10 1160 70 {
lab=VSS}
N 1190 -80 1230 -80 {
lab=xor_out}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} 1100 -230 0 0 {name=M5
l=0.13u
w=2u
ng=1
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 1100 -10 0 0 {name=M6
l=0.13u
w=2u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 1200 -280 0 0 {name=p23 sig_type=std_logic lab=VDD}
C {devices/opin.sym} 1230 -80 0 0 {name=p24 lab=xor_out}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} 1100 -140 0 0 {name=M1
l=0.13u
w=2u
ng=1
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} 1280 -230 0 1 {name=M2
l=0.13u
w=2u
ng=1
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_pmos.sym} 1280 -140 0 1 {name=M3
l=0.13u
w=2u
ng=1
m=1
mm_ok=1
model=sg13_lv_pmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 1100 70 0 0 {name=M4
l=0.13u
w=2u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 1290 -10 0 1 {name=M7
l=0.13u
w=2u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 1290 70 0 1 {name=M8
l=0.13u
w=2u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 1200 140 0 1 {name=p25 sig_type=std_logic lab=VSS}
C {devices/lab_wire.sym} 1300 -230 0 1 {name=p28 sig_type=std_logic lab=A-}
C {devices/lab_wire.sym} 1300 -140 0 1 {name=p30 sig_type=std_logic lab=B}
C {devices/lab_wire.sym} 1310 -10 0 1 {name=p31 sig_type=std_logic lab=A}
C {devices/ipin.sym} 1080 -230 0 0 {name=p7 lab=A
}
C {devices/ipin.sym} 1080 -140 0 0 {name=p1 lab=B-
}
C {devices/ipin.sym} 1080 -10 0 0 {name=p2 lab=A-
}
C {devices/ipin.sym} 1310 70 0 1 {name=p4 lab=B
}
C {devices/lab_wire.sym} 1080 70 0 0 {name=p3 sig_type=std_logic lab=B-}
C {devices/iopin.sym} 810 -160 0 0 {name=p5 lab=VDD


}
C {devices/iopin.sym} 810 -130 0 0 {name=p6 lab=VSS


}
