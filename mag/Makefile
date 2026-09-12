# Layout flow for ihp-analog-equalizer.  See ../docs/LAYOUT.md.
#
#   make gen CELL=robs_xor     generate a starting layout from the netlist
#   make edit CELL=robs_xor    open it in the GUI
#   make drc CELL=robs_xor     design rule check
#   make lvs CELL=robs_xor     layout versus schematic
#   make check CELL=robs_xor   drc then lvs
#   make cells                 list every cell, leaves first
PDK_ROOT ?= /home/ttuser/pdk
PDK      := $(PDK_ROOT)/ihp-sg13cmos5l
RC       := $(PDK)/libs.tech/magic/ihp-sg13cmos5l.magicrc
MAGIC    := magic -rcfile $(RC)
CELL     ?=

.PHONY: gen edit drc lvs check cells netlist clean
guard:
	@test -n "$(CELL)" || { echo "set CELL=<name>; 'make cells' lists them"; exit 1; }

$(CELL).spice: guard
	python3 ../tools/cell_netlist.py --flat $(CELL) > $@

gen: $(CELL).spice
	$(MAGIC) -dnull -noconsole tcl/gen.tcl $(CELL)

edit: guard
	$(MAGIC) -d XR $(CELL).mag

drc: guard
	$(MAGIC) -dnull -noconsole tcl/drc.tcl $(CELL)

lvs: guard
	./lvs_cell.sh $(CELL)

check: drc lvs

cells:
	@python3 ../tools/cell_netlist.py --list

clean:
	rm -f *.ext *.lvs.spice *.sch.spice
