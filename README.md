# Sweep-style split keyboard

PCB + 3D-printed case for a 34-key Ferris-Sweep-style split keyboard, with a
headless design-and-verify toolchain.

```sh
make setup   # toolchain: Python venv, ergogen, KiCad 9 + JRE docker images, Freerouting
make all     # layout -> PCBs (DRC, plots) -> case (fit check, mesh checks, slice, renders)
make fab     # gerbers / drill / STEP in build/fab/
```

- `ergogen/config.yaml` — key layout, board outlines, footprints and nets
- `pcb/` — hand-edited / routed boards (take precedence over generated ones)
- `cad/` — build123d case model driven by the exported PCB geometry
- `scripts/` — KiCad wrappers, routing, DRC gate, mesh checks, slicing, renders

See [CLAUDE.md](CLAUDE.md) for the pipeline, outputs and gotchas.
