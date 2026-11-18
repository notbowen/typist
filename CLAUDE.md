# Sweep-style split keyboard — PCB + 3D-printed case

Design and verify the PCBs and printed case for a wireless Ferris-Sweep-style
34-key split: Sweep 2.2 key positions + outline (open source, Solderpad 2.1),
Choc v1 hotswap, Seeed XIAO nRF52840 per half (SMD, flat), 4x5 diode matrix,
plug-in LiPo (JST-SH) under the controller tab, side power switch, ZMK BLE split
(no TRRS). Everything runs headless; every design change should be verified with
the commands below and by **looking at the rendered PNGs** (Read them).

## Pipeline

```
ergogen/config.yaml ──ergogen──► build/ergogen/pcbs/{left,right}.kicad_pcb   (unrouted)
                                        │  (copy to pcb/<side>.kicad_pcb once you hand-edit/route;
                                        │   pcb/ wins over ergogen output everywhere)
                                        ▼
                     kicad-cli DRC, plots, renders ──► build/pcb/<side>-*.png, -drc.json
                     pcbnew export_geometry.py ──► build/pcb/<side>.geom.json
                                        ▼
cad/ (build123d) case from the real PCB outline ──► build/cad/<side>/case.{step,stl}
   fit check (case ∩ PCB/parts/keep-outs = 0) ─ mesh checks ─ PrusaSlicer slice ─ renders
```

## Commands

| | |
|---|---|
| `make setup` | install/verify toolchain (idempotent) |
| `make all` | ergogen → PCB checks → case build/verify for both halves (~2.5 min) |
| `make ergogen` | regenerate layout; outlines in `build/ergogen/outlines/`, points in `build/ergogen/points/` |
| `make pcb` / `make pcb-strict` | DRC gate (+ unrouted fails with strict), 2D/3D plots, geometry export |
| `make route SIDE=left` | Freerouting, then GND pour (~5 min) → `build/pcb/left-routed.kicad_pcb` |
| `make fab` | gerbers+drill zip, pos csv, board STEP → `build/fab/` |
| `make case` | case build + fit check + mesh checks + slice + renders |
| `make verify` | release gate: `pcb-strict` + `case` |
| `SIDES=left make case` | limit to one half |
| `make viewer` | interactive HTML viewer + spec sheet → `build/artifact/sweep-xiao.html` (needs `make pcb case` outputs) |

Look at after changes:
- `build/pcb/<side>-2d.png` — outline, pads, tracks, silk (fastest PCB sanity view)
- `build/pcb/<side>-3d-{top,bottom}.png` — KiCad 3D render
- `build/cad/<side>/plot2d.png` — case walls vs PCB vs under-board parts vs cable keep-outs
- `build/cad/<side>/assembly.png`, `case.png` — 3D renders
- `build/cad/<side>/fit.json`, `mesh.json`, `build/pcb/<side>-drc.json` — machine-readable results

## Tools and where they live

- **KiCad 9** runs in Docker (`kicad/kicad:9.0`; Debian 12 only has KiCad 6, which lacks `kicad-cli`).
  `scripts/kicad-cli …` is a drop-in wrapper; `scripts/kicad python3 script.py` runs pcbnew
  scripts. The repo is mounted at the same absolute path, but **only the repo** — /tmp
  files are not visible inside, so keep inputs/outputs under the repo (e.g. `build/`).
  The base image has no 3D component models, so KiCad renders/STEP show bare boards.
- **Ergogen 4.2.1** (`npx ergogen`) — layout, outlines, PCB scaffolding (kicad8 template).
  Its outline `expand` maths (makerjs) sometimes emits self-intersecting arcs; DRC reports
  `invalid_outline` — change the expand value (4 works for the reference layout).
- **Freerouting 2.5.0** jar in `tools/` run with Java 25 in Docker (`eclipse-temurin:25-jre`).
  The native `freerouting-cli` 2.5.0 build crashes (GraalVM serialization error) — don't use it.
- **build123d** (OpenCascade) for CAD, **shapely** for 2D, **trimesh** for mesh checks,
  **PyVista/VTK** offscreen via OSMesa for renders, **PrusaSlicer 2.5** CLI for slicing
  (`config/prusa-pla-0.2.ini`, 220×220 bed). Python lives in `.venv/`.
- System packages `prusa-slicer`, `libosmesa6` are in the Lapiz project environment.

## Conventions / gotchas

- CAD frame: mm, x right, **y up** (KiCad y is flipped by `export_geometry.py`),
  z = 0 at PCB bottom. `case.stl` is exported in print orientation (bottom on z=0).
- `cad/components.py` holds part envelopes (`DIMS`) — Choc v1 + hotswap sockets, SOD-123 diodes,
  XIAO nRF52840 + USB-C, MSK12C02 switch, JST-SH socket, 301230 LiPo — and keep-outs (keycap
  travel, USB-C plug, switch finger notch, mated battery plug). Case openings are cut
  from the same keep-outs, so fit check and case can't disagree. Update `DIMS` for real parts.
- `cad/case.py` `CaseParams`: wall, clearance, floor, under-PCB gap (3.5: LiPo 3.1 thick), ledge,
  wall height, M2 screw bosses (at the mounting holes), battery locating fence.
- Outline: `scripts/ergogen/sweep_outline.py` converts the Sweep 2.2 Edge.Cuts into the ergogen
  polygon in `config.yaml` (controller tab widened 1.8 mm for the XIAO). Socket orientation per
  column follows the Sweep Bling LP (sockets face away from board edges).
- Custom footprints live in `ergogen/footprints/` (XIAO, SOD-123, JST-SH, mounting hole).
- The XIAO is not mirrored on the right half (it's a top-mounted module), so its BAT pads, the
  battery cell (always on the XIAO's +x side) and the right JST (`jst_x_r`) are placed explicitly.
- Matrix pins: cols D0-D4, rows D5/D8/D9/D10 (D6/D7 = UART left free). Must match
  `firmware/zmk-config/config/boards/shields/sweep_xiao/sweep_xiao.dtsi`.
- `boardgeom.prism()` always extrudes +Z; shapely rings can be clockwise and build123d's
  `extrude` follows the face normal — never call `extrude` on shapely-derived faces directly.
- Fresh ergogen boards are unrouted: `make pcb` allows unconnected items, `make pcb-strict` doesn't.
  `silk_over_copper` warnings come from ergogen's footprints and are harmless.
- Ergogen regenerates boards from scratch (routing lost). Once routed/edited, the board belongs
  in `pcb/<side>.kicad_pcb` (committed); re-sync layout changes by hand or re-route.
- Freerouting does not know KiCad's copper-to-edge clearance (0.5 mm); `specctra.py export` adds a
  temporary keep-out ring along Edge.Cuts to the DSN (0.9 mm — narrower rings were not fully
  respected). The GND pour uses solid pad connections (edge pads starve thermal spokes).
- `make pcb-strict` must pass before fab.
- `build/`, `.venv/`, `node_modules/`, `tools/` are gitignored and reproducible via `make setup`.
