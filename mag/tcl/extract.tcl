# Extract one cell to a SPICE netlist suitable for LVS.
#   magic ... -dnull -noconsole mag/tcl/extract.tcl <cell>
# `ext2spice lvs` sets the options netgen expects: no parasitics, subcircuit
# ports in the order the layout declares them, device names left alone.
# Magic puts its own options in $argv too (-nowrapper and friends), so the
# cell name is the LAST argument, not the first.
set cell [lindex $argv end]
load $cell
select top cell
extract no all
extract do local
extract unique
extract all
ext2spice lvs
# `-o` matters: without it ext2spice writes <cell>.spice, which is the same
# name the generator input uses, and the layout would silently overwrite the
# netlist it was built from.
ext2spice -o ${cell}.lvs.spice
puts "EXTRACT $cell -> ${cell}.lvs.spice"
quit -noprompt
