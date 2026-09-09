# Source this before running anything in this repository:  . ./env.sh
#
# PDK_ROOT must hold BOTH IHP PDKs side by side.  ihp-sg13cmos5l is an overlay:
# roughly 500 of its files are relative symlinks into ../ihp-sg13g2, including
# every ngspice model library and most xschem symbols.  Check it out alone and
# the links dangle silently -- ngspice then reports "could not find a valid
# modelname" rather than "your PDK is incomplete".
#
#   $PDK_ROOT/ihp-sg13cmos5l   <- the Chipalooza process
#   $PDK_ROOT/ihp-sg13g2       <- what CMOS5L symlinks into
#
# tools/setup_pdk.sh will fetch and build both, including the OSDI models.

export PDK_ROOT="${PDK_ROOT:-$HOME/pdk}"
# PDK is set unconditionally, not defaulted.  A shell that has been used for
# sky130 work exports PDK=sky130A, and inheriting that puts the wrong symbol
# library on XSCHEM_LIBRARY_PATH -- at which point xschem resolves nothing,
# says nothing, and writes a truncated netlist.  See docs/SIMULATION_TRAPS.md.
export PDK=ihp-sg13cmos5l

export IHP_MODELS="$PDK_ROOT/$PDK/libs.tech/ngspice/models"
export IHP_OSDI="$PDK_ROOT/$PDK/libs.tech/ngspice/osdi"

# Repo root, resolved from this file so it works from any working directory.
IHP_EQ_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
export IHP_EQ_ROOT

if [ ! -d "$PDK_ROOT/ihp-sg13cmos5l" ]; then
    echo "warning: $PDK_ROOT/ihp-sg13cmos5l not found -- run tools/setup_pdk.sh" >&2
elif [ ! -d "$PDK_ROOT/ihp-sg13g2" ]; then
    echo "warning: $PDK_ROOT/ihp-sg13g2 not found -- ihp-sg13cmos5l symlinks into it," >&2
    echo "         so models and symbols will be silently missing." >&2
elif [ ! -f "$IHP_OSDI/psp103.osdi" ]; then
    echo "warning: $IHP_OSDI/psp103.osdi not found -- the MOS models are PSP103" >&2
    echo "         Verilog-A and must be compiled.  Run tools/setup_pdk.sh." >&2
fi
