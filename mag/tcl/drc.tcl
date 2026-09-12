# DRC one cell and print the count and the first errors.
#   magic ... -dnull -noconsole mag/tcl/drc.tcl <cell>
# Magic puts its own options in $argv too (-nowrapper and friends), so the
# cell name is the LAST argument, not the first.
set cell [lindex $argv end]
load $cell
select top cell
drc euclidean on
drc style drc(full)
drc check
drc catchup
set n [drc list count total]
puts "DRC $cell: $n error(s)"
if {$n > 0} { puts [drc listall why] }
quit -noprompt
