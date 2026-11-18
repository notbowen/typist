# Sweep-style split keyboard

PCB + 3D-printed case for a wireless 34-key split that keeps the Ferris Sweep 2
shape (key positions and outline from the open-source
[Sweep](https://github.com/davidphilipbarr/Sweep), Solderpad Hardware License 2.1),
with a Seeed XIAO nRF52840 per half, a plug-in LiPo cell under the controller,
Choc v1 hotswap sockets and ZMK firmware — plus a headless design-and-verify toolchain.

```sh
make setup   # toolchain: Python venv, ergogen, KiCad 9 + JRE docker images, Freerouting
make all     # layout -> PCBs (DRC, plots) -> case (fit check, mesh checks, slice, renders)
make fab     # gerbers / drill / STEP in build/fab/ (JLCPCB: 2 layers, 1.6 mm)
make viewer  # interactive 3D viewer + spec/compatibility sheet (build/artifact/)
```

- `ergogen/config.yaml` — key layout, board outlines, footprints and nets
- `pcb/` — hand-edited / routed boards (take precedence over generated ones)
- `cad/` — build123d case model driven by the exported PCB geometry
- `scripts/` — KiCad wrappers, routing, DRC gate, mesh checks, slicing, renders, viewer
- `firmware/zmk-config/` — ZMK shield (`sweep_xiao_left` / `_right`) and starter keymap

See [CLAUDE.md](CLAUDE.md) for the pipeline, outputs and gotchas.
