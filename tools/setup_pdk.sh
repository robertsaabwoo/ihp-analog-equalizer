#!/bin/bash
# Install everything needed to netlist and simulate this design.
#
#   tools/setup_pdk.sh            installs into ${PDK_ROOT:-$HOME/pdk}
#
# There are three pieces, and each one fails in a way that is easy to
# misdiagnose if it is missing:
#
# 1. ihp-sg13cmos5l -- the Chipalooza process.  It is an *overlay*: roughly
#    500 of its files are relative symlinks into a sibling ihp-sg13g2
#    checkout, including every ngspice model library and most xschem symbols.
#    Clone it alone and the links dangle; ngspice then says "could not find a
#    valid modelname", which reads like a deck problem rather than a missing
#    PDK.
#
# 2. ihp-sg13g2 -- what those symlinks point at.  Only libs.tech is needed.
#
# 3. The MOS models are PSP 103.6 written in Verilog-A, and are loaded through
#    OSDI at simulation time.  They are not built into ngspice.  Without the
#    compiled .osdi files ngspice reports "Unknown model type psp103va -
#    ignored" as a *warning*, then fails on the first transistor with "could
#    not find a valid modelname".
#
# The Verilog-A compiler needs care.  ngspice 42 implements OSDI 0.3.
# OpenVAF-Reloaded's current binaries (openvaf-r) emit OSDI 0.4 and link
# against libLLVM.so.18, which Ubuntu 22.04 does not ship.  The last
# statically linked OpenVAF that emits OSDI 0.3 is 23.5.0, which is what this
# script fetches.  If you are on ngspice 44 or newer, openvaf-r is the better
# choice -- set OPENVAF to point at it and this script will use it.
set -eu

PDK_ROOT="${PDK_ROOT:-$HOME/pdk}"
mkdir -p "$PDK_ROOT"
cd "$PDK_ROOT"

echo "==> installing into $PDK_ROOT"

# ---------------------------------------------------------------- SG13G2 base
if [ ! -d ihp-sg13g2/libs.tech ]; then
    echo "==> fetching ihp-sg13g2 (libs.tech only)"
    rm -rf .g2tmp
    git clone --depth 1 --filter=blob:none --sparse \
        https://github.com/IHP-GmbH/IHP-Open-PDK.git .g2tmp
    ( cd .g2tmp && git sparse-checkout set ihp-sg13g2/libs.tech )
    rm -rf ihp-sg13g2
    mv .g2tmp/ihp-sg13g2 ihp-sg13g2
    rm -rf .g2tmp
else
    echo "==> ihp-sg13g2 already present"
fi

# ------------------------------------------------------------- SG13CMOS5L PDK
if [ ! -d ihp-sg13cmos5l/libs.tech ]; then
    echo "==> fetching ihp-sg13cmos5l"
    rm -rf .c5tmp
    git clone --depth 1 --filter=blob:none \
        https://github.com/IHP-GmbH/ihp-sg13cmos5l.git .c5tmp
    rm -rf .c5tmp/.git
    rm -rf ihp-sg13cmos5l
    mv .c5tmp ihp-sg13cmos5l
else
    echo "==> ihp-sg13cmos5l already present"
fi

broken=$(cd ihp-sg13cmos5l && find . -xtype l | wc -l)
if [ "$broken" -gt 20 ]; then
    echo "warning: $broken dangling symlinks in ihp-sg13cmos5l." >&2
    echo "         It overlays ihp-sg13g2; check that both are under $PDK_ROOT." >&2
fi

# ----------------------------------------------------------------- Verilog-A
if [ -z "${OPENVAF:-}" ]; then
    if [ -x "$PDK_ROOT/openvaf/openvaf" ]; then
        OPENVAF="$PDK_ROOT/openvaf/openvaf"
    elif command -v openvaf-r >/dev/null 2>&1; then
        OPENVAF="$(command -v openvaf-r)"
    elif command -v openvaf >/dev/null 2>&1; then
        OPENVAF="$(command -v openvaf)"
    else
        echo "==> fetching OpenVAF 23.5.0 (statically linked, emits OSDI 0.3)"
        curl -sSL -o openvaf.tar.gz \
          https://openva.fra1.cdn.digitaloceanspaces.com/openvaf_23_5_0_linux_amd64.tar.gz
        mkdir -p openvaf && tar xzf openvaf.tar.gz -C openvaf && rm -f openvaf.tar.gz
        chmod +x "$PDK_ROOT/openvaf/openvaf"
        OPENVAF="$PDK_ROOT/openvaf/openvaf"
    fi
fi
echo "==> Verilog-A compiler: $OPENVAF"

# The two PDKs share the Verilog-A sources through symlinks, so building into
# the SG13G2 tree lights up both.  cap_cmomi and cap_cmomf live in the CMOS5L
# tree as real files and are built there.
build_osdi() {   # $1 pdk dir  $2 model file  $3 source subdir
    local pdk="$1" model="$2" dir="$3"
    local out="$PDK_ROOT/$pdk/libs.tech/ngspice/osdi"
    mkdir -p "$out"
    ( cd "$PDK_ROOT/$pdk/libs.tech/verilog-a/$dir" \
      && "$OPENVAF" "$model.va" --output "$out/$model.osdi" >/dev/null 2>&1 ) \
      && echo "    $pdk/$model.osdi" \
      || echo "    FAILED: $pdk/$model" >&2
}

echo "==> compiling Verilog-A models"
build_osdi ihp-sg13g2 psp103     psp103
build_osdi ihp-sg13g2 psp103_nqs psp103
build_osdi ihp-sg13g2 r3_cmc     r3_cmc
build_osdi ihp-sg13g2 mosvar     mosvar
build_osdi ihp-sg13cmos5l cap_cmomi cap_cmomi
build_osdi ihp-sg13cmos5l cap_cmomf cap_cmomf

echo
echo "==> done.  Add to your shell, or just '. ./env.sh' in this repo:"
echo "      export PDK_ROOT=$PDK_ROOT"
echo "      export PDK=ihp-sg13cmos5l"
echo
echo "==> checking the install"
missing=0
for f in "$PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/osdi/psp103.osdi" \
         "$PDK_ROOT/ihp-sg13cmos5l/libs.tech/ngspice/models/cornerMOSlv.lib" \
         "$PDK_ROOT/ihp-sg13cmos5l/libs.tech/xschem/sg13cmos5l_pr/sg13_lv_nmos.sym"; do
    if [ -e "$f" ]; then echo "    ok  $f"; else echo "    MISSING  $f"; missing=1; fi
done
exit $missing
