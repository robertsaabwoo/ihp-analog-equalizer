# Generate a starting layout for one cell from its SPICE netlist.
#   make gen CELL=<name>
#
# Devices come out correctly sized and every port is already labelled; they are
# laid out in a row and arranging and wiring them is the actual work.
# Re-running on an existing cell does not duplicate what is already there.
#
# Magic puts its own options in $argv too (-nowrapper and friends), so the cell
# name is the LAST argument, not the first.
set cell [lindex $argv end]

# Two things about this call that both fail silently if you get them wrong:
#
#   * netlist_to_layout loads and saves the cell itself.  Do NOT load or save
#     around it -- doing so replaces the generated cell with an empty one of
#     the same name, and it looks like the generator produced nothing.
#
#   * the netlist FILE NAME must match the cell name.  The generator decides
#     what to generate by comparing each .subckt against the file's root name;
#     call the file robs_xor.gen.spice and it concludes robs_xor is somebody
#     else's cell, prints "already contains layout", and skips it.
magic::netlist_to_layout ${cell}.spice sg13cmos5l

# netlist_to_layout saves the PARENT cell only.  The device cells it generated
# -- sg13_lv_nmos_S6LAQ4 and friends -- exist in memory and are never written,
# so the next command to open the parent reports "couldn't be read" for every
# one of them and extraction quietly produces nothing.  writeall saves the lot.
writeall force
puts "GEN $cell done"
quit -noprompt
