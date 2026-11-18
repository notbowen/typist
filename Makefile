# Sweep-style split keyboard: one reversible PCB for both halves.
# `make help` for targets. SIDES selects boards (default: the single reversible `sweep`).

SIDES ?= sweep
PY    := .venv/bin/python
ERGO  := build/ergogen/pcbs

# A board in pcb/ (hand-edited / routed, committed) wins over fresh ergogen output.
pcb_src = $(if $(wildcard pcb/$(1).kicad_pcb),pcb/$(1).kicad_pcb,$(ERGO)/$(1).kicad_pcb)

.PHONY: help setup ergogen pcb pcb-strict fab route all verify viewer clean

help:
	@echo "make setup        install/verify toolchain (venv, npm, docker images, freerouting)"
	@echo "make ergogen      regenerate layout, outlines, unrouted PCBs from ergogen/config.yaml"
	@echo "make pcb          DRC (unrouted allowed) + 2D/3D plots + geometry export (viewer input)"
	@echo "make pcb-strict   same, but unrouted connections fail"
	@echo "make route SIDE=sweep  Freerouting + GND pour -> build/pcb/<side>-routed.kicad_pcb"
	@echo "make fab          gerbers/drill zip, pos, STEP per side"
	@echo "make all          ergogen pcb"
	@echo "make verify       pcb-strict (release gate)"
	@echo "make viewer       interactive 3D viewer + spec sheet -> build/artifact/sweep-xiao.html"
	@echo "Boards: pcb/<side>.kicad_pcb if present, else $(ERGO)/<side>.kicad_pcb"

setup:
	scripts/setup.sh

ergogen:
	rm -rf build/ergogen
	npx ergogen ergogen -o build/ergogen --debug
	@if ls pcb/*.kicad_pcb >/dev/null 2>&1; then echo "NOTE: pcb/ boards exist and take precedence; ergogen output is in $(ERGO)/"; fi

$(ERGO)/%.kicad_pcb:
	$(MAKE) ergogen

pcb: $(foreach s,$(SIDES),$(call pcb_src,$(s)))
	@rc=0; for s in $(SIDES); do \
	  src=$$( [ -f pcb/$$s.kicad_pcb ] && echo pcb/$$s.kicad_pcb || echo $(ERGO)/$$s.kicad_pcb ); \
	  echo "== $$s ($$src)"; scripts/pcb/check.sh $$src build/pcb $(STRICT) || rc=1; done; exit $$rc

pcb-strict:
	$(MAKE) pcb STRICT=--strict

route:
	@test -n "$(SIDE)" || { echo "usage: make route SIDE=sweep"; exit 2; }
	mkdir -p build/pcb
	# route GND as real tracks first, then pour: pours added before routing fragment
	# into islands once Freerouting treats GND as a plane
	scripts/pcb/autoroute.sh $(call pcb_src,$(SIDE)) build/pcb/$(SIDE)-tracks.kicad_pcb
	scripts/kicad python3 scripts/pcb/add_zones.py build/pcb/$(SIDE)-tracks.kicad_pcb build/pcb/$(SIDE)-routed.kicad_pcb GND
	scripts/pcb/check.sh build/pcb/$(SIDE)-routed.kicad_pcb build/pcb || true
	@echo "Review build/pcb/$(SIDE)-routed-2d.png; if good: cp build/pcb/$(SIDE)-routed.kicad_pcb pcb/$(SIDE).kicad_pcb"

fab:
	@for s in $(SIDES); do scripts/pcb/fab.sh $$( [ -f pcb/$$s.kicad_pcb ] && echo pcb/$$s.kicad_pcb || echo $(ERGO)/$$s.kicad_pcb ) build/fab; done

all: ergogen pcb

verify: pcb-strict

viewer:
	@[ -f build/pcb/sweep.geom.json ] || $(MAKE) pcb
	$(PY) scripts/artifact/build_viewer.py build/artifact/sweep-xiao.html

clean:
	rm -rf build
