v {xschem version=3.4.5 file_version=1.2
}
G {}
K {}
V {}
S {}
E {}
T {ibias_mirror -- turn the harness's bandgap-referenced current into the
tail-bias voltage the CTLE and the CML latches run on.

This cell does not exist in the sky130 original, where vbias was a voltage
brought in from a pin.  On 1.8 V that was survivable.  On 1.2 V it is not:
with vbias held at a fixed 0.45 V the CTLE's Nyquist gain measured +14.2 dB
at ss/-40C/1.32V and -1.3 dB at ff/-40C/1.08V -- a 15 dB spread, because a
fixed gate voltage on a tail device asks for a current that moves with
threshold voltage, mobility and temperature all at once, and at the fast
corner the answer is more current than the stack has headroom for.  The
stage does not lose gain gracefully there; the input pair leaves saturation
and the gain collapses.

MREF is a diode-connected replica of the CTLE tail at one tenth the width,
so a reference current of ~43 uA sets the CTLE tail to ~430 uA.  The bias
node self-adjusts: at the fast corner the same current needs less gate
voltage, which is exactly the correction the fixed bias could not make.

The reference current is a resource the challenge harness provides -- each
slot gets bandgap-referenced current sources -- so this costs one pin and
one transistor, and no on-chip reference.

MREF's length matches the CTLE tail's 1 um.  The CML tails in the phase
detector are shorter and so do not mirror in a fixed ratio; they still
benefit, because the bias node now moves the right way over PVT.} -420 -260 0 0 0.35 0.35 {}
N -60 0 -20 0 {
lab=bias}
N -60 -60 -60 0 {
lab=bias}
N -60 -60 20 -60 {
lab=bias}
N 20 -60 20 -30 {
lab=bias}
N 20 30 60 30 {
lab=VGND}
N 60 0 60 30 {
lab=VGND}
C {devices/iopin.sym} -60 0 0 0 {name=p1 lab=bias}
C {devices/iopin.sym} 60 0 0 0 {name=p2 lab=VGND}
C {sg13cmos5l_pr/sg13_lv_nmos.sym} 0 0 0 0 {name=MREF
l=1u
w=4u
ng=1
m=1
mm_ok=1
model=sg13_lv_nmos
spiceprefix=X}
C {devices/lab_wire.sym} 20 0 0 0 {name=p3 sig_type=std_logic lab=VGND}
