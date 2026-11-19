The routed, committed board lives here as `sweep.kicad_pcb` (one reversible PCB: the
right half is the same board flipped). When present it replaces
`build/ergogen/pcbs/sweep.kicad_pcb` in every make target.

It is `make route SIDE=sweep` output (Freerouting, then GND pours on both layers) with the
GND pours removed again: the board is black-core FR-4 under a clear mask, and only tracks
should show. GND is fully routed as tracks, so the pours were never needed for connectivity.
If you change placement in `ergogen/config.yaml`, re-run `make route SIDE=sweep` and
copy `build/pcb/sweep-routed.kicad_pcb` here again; ergogen output is unrouted.
