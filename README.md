# Sweep-style split keyboard

One reversible PCB (order one design, flip a board for the right half) for a wireless 34-key split that keeps the Ferris Sweep 2
shape (key positions and outline from the open-source
[Sweep](https://github.com/davidphilipbarr/Sweep), Solderpad Hardware License 2.1),
with a Seeed XIAO nRF52840 per half, 4 status LEDs per half, a plug-in LiPo cell under the controller,
Choc v1 hotswap sockets (Kailh Choc Sunset switches, blank white MBK caps) and ZMK firmware. No case:
the bare board stands on rubber feet. Comes with a headless design-and-verify toolchain.

```sh
make setup   # toolchain: Python venv, ergogen, KiCad 9 + JRE docker images, Freerouting
make all     # layout -> PCB (DRC, plots)
make fab     # build/fab/sweep-gerbers.zip for JLCPCB (2 layers, 1.6 mm; 5 boards = 2 keyboards)
make viewer  # interactive 3D model of both halves + spec sheet, BOM, build guide (build/artifact/)
```

- `ergogen/config.yaml` — key layout, board outlines, footprints and nets
- `pcb/` — hand-edited / routed boards (take precedence over generated ones)
- `scripts/` — KiCad wrappers, routing, DRC gate, plots, fab outputs, viewer
- `firmware/zmk-config/` — ZMK shield (`sweep_xiao_left` / `_right`) and starter keymap

See [CLAUDE.md](CLAUDE.md) for the pipeline, outputs and gotchas.
