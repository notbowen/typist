Routed / hand-edited boards live here as `left.kicad_pcb` and `right.kicad_pcb`.
When present they replace `build/ergogen/pcbs/<side>.kicad_pcb` in every make target.

Current boards: `make route SIDE=<side>` output (Freerouting, then GND pours on both
layers), 0 DRC errors, fully routed. On the right board, 4 Freerouting 0.1 mm
neck-downs were widened to 0.15 mm for JLCPCB's standard 2-layer process.
If you change placement in `ergogen/config.yaml`, re-run `make route` for both
halves and copy the results here again, since ergogen output is unrouted.
