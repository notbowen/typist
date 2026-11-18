# Sweep-style split keyboard — one reversible PCB

Design and verify ONE reversible PCB (`sweep`) for a wireless Ferris-Sweep-style 34-key
split: the right half is the same board flipped over, so a single JLCPCB order covers
both halves. Sweep 2.2 key positions + outline (open source, Solderpad 2.1; pinky edge,
inner notch, controller tab and thumb diagonal grown ~2 mm for double-sided pads),
Choc v1 hotswap (Kailh Choc Sunset switches, blank white MBK caps — the parts the owner
bought from SplitKB), Seeed XIAO nRF52840 per half (SMD, flat), 4x5 diode matrix,
4 status LEDs, plug-in LiPo (JST-SH) under the controller tab, side power switch,
ZMK BLE split (no TRRS). **No case**: the bare PCB stands on feet (M2 standoff + bumpon in the
3 mounting holes, plus 3 adhesive feet); the old 3D-printed case pipeline is gone.
Everything runs headless; every design change should be verified with
the commands below and by **looking at the rendered PNGs** (Read them).

## Pipeline

```
ergogen/config.yaml ──ergogen──► build/ergogen/pcbs/sweep.kicad_pcb   (unrouted)
                                        │  (copy to pcb/sweep.kicad_pcb once you hand-edit/route;
                                        │   pcb/ wins over ergogen output everywhere)
                                        ▼
                     kicad-cli DRC, plots, renders ──► build/pcb/sweep-*.png, -drc.json
                     pcbnew export_geometry.py ──► build/pcb/sweep.geom.json
                                        ▼
scripts/artifact/build_viewer.py (parts list, feet placement) + viewer_template.html (three.js)
   ──► build/artifact/sweep-xiao.html   (both halves, spec sheet; published as a Lapiz artifact)
```

## Commands

| | |
|---|---|
| `make setup` | install/verify toolchain (idempotent) |
| `make all` | ergogen → PCB checks |
| `make ergogen` | regenerate layout; outlines in `build/ergogen/outlines/`, points in `build/ergogen/points/` |
| `make pcb` / `make pcb-strict` | DRC gate (+ unrouted fails with strict), 2D/3D plots, geometry export |
| `make route SIDE=sweep` | Freerouting, then GND pour (~10 min) → `build/pcb/sweep-routed.kicad_pcb` |
| `make fab` | gerbers+drill zip, pos csv, board STEP → `build/fab/` |
| `make verify` | release gate: `pcb-strict` |
| `make viewer` | interactive HTML viewer + spec sheet → `build/artifact/sweep-xiao.html` (needs `make pcb` outputs) |

Look at after changes:
- `build/pcb/sweep-2d.png` — outline, pads, tracks, silk (fastest PCB sanity view)
- `build/pcb/sweep-3d-{top,bottom}.png` — KiCad 3D render (bottom = how the right half looks from above)
- `build/pcb/sweep-drc.json` — machine-readable DRC result (the viewer's verification block reads it)
- `build/artifact/sweep-xiao.html` — serve it (`python3 -m http.server -d build/artifact`) and check it
  with the browser tool: both halves, Under view, LED toggle, explode, mobile width

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
- Python (`.venv/`, `requirements.txt`): **shapely** (outline maths in `sweep_outline.py` and the
  viewer's foot placement), **CairoSVG** (KiCad SVG → PNG). `prusa-slicer` / `libosmesa6` in the
  Lapiz project environment were only for the removed case pipeline.
- The viewer is plain three.js 0.160 from jsDelivr (import map), everything else is inlined.

## Conventions / gotchas

- Geometry frame (`geom.json`, viewer): mm, x right, **y up** (KiCad y is flipped by
  `export_geometry.py`), z = 0 at PCB bottom.
- Viewer (`scripts/artifact/`): `build_viewer.py` `DIMS` holds the part envelopes (socket boxes,
  SOD-123, XIAO + USB-C, MSK12C02, JST-SH, 301230 cell + tape, LEDs, feet); update them for real
  parts. It places the cell under the tab and picks the adhesive-foot spots automatically (clear
  of sockets/posts/diodes/JST/cell on *both* faces, so the spots are the same on both halves) and
  checks that the feet enclose the board centroid. The template builds everything procedurally:
  the right half is the same board group rotated 180° about Y (a real flip, so the B texture ends
  up on top), parts sit in per-face groups (`+z` = away from that face). LED colours there are only
  a suggestion; meaning is the firmware's.
- Outline: `scripts/ergogen/sweep_outline.py` converts the Sweep 2.2 Edge.Cuts into the ergogen
  polygon in `config.yaml` (controller tab widened 1.8 mm for the XIAO). Socket orientation per
  column follows the Sweep Bling LP (sockets face away from board edges).
- Custom footprints live in `ergogen/footprints/`, all reversible (pads on both faces):
  `choc_rev` (Kailh hotswap both faces, narrowed inner pads clear the opposite socket hole),
  `xiao_nrf52840` (`reversible: true`: F pads at the normal spot + B pads mirrored, same net per
  XIAO pin, so both halves share one pin map; BAT±/NFC pads by plated through-holes on both
  sides), `diode_sod123`, `jst_sh2`, `power_switch_rev` (MSK12C02), `led_0805` (LED + series R).
  Pads at the same x/y on opposite faces may carry different nets (XIAO) — they are SMD, so this
  is fine as long as nothing puts a via there.
- Left half: switches/XIAO/LEDs/power switch on F, sockets/diodes/JST on B. Right half: flipped.
- Pins (all 11 GPIO + both NFC pads used): cols D0-D4, rows D5/D8/D9/D10, LEDs D6, D7, P0.09,
  P0.10. Must match `firmware/zmk-config/config/boards/shields/sweep_xiao/sweep_xiao.dtsi`.
- Socket orientation: pinky column and the outer thumb rot 0, the rest rot 180 — checked so no
  face's pads hit an edge with the grown outline (see `sweep_outline.py`).
- Fresh ergogen boards are unrouted: `make pcb` allows unconnected items, `make pcb-strict` doesn't.
  `silk_over_copper` warnings come from ergogen's footprints and are harmless.
- Ergogen regenerates boards from scratch (routing lost). Once routed/edited, the board belongs
  in `pcb/<side>.kicad_pcb` (committed); re-sync layout changes by hand or re-route.
- Freerouting does not know KiCad's copper-to-edge clearance (0.5 mm); `specctra.py export` adds a
  temporary keep-out ring along Edge.Cuts to the DSN (0.9 mm — narrower rings were not fully
  respected). The GND pour uses solid pad connections (edge pads starve thermal spokes).
- `make pcb-strict` must pass before fab. Routed board lives in `pcb/sweep.kicad_pcb`.
- `build/`, `.venv/`, `node_modules/`, `tools/` are gitignored and reproducible via `make setup`.
