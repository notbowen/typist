The routed, committed board lives here as `sweep.kicad_pcb` (one reversible PCB: the
right half is the same board flipped). When present it replaces
`build/ergogen/pcbs/sweep.kicad_pcb` in every make target.

It is `make route SIDE=sweep` output (Freerouting, then GND pours on both layers).
If you change placement in `ergogen/config.yaml`, re-run `make route SIDE=sweep` and
copy `build/pcb/sweep-routed.kicad_pcb` here again; ergogen output is unrouted.
