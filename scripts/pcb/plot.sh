#!/usr/bin/env bash
# 2D plot of a board (outline, copper, silk, fab, user drawings) to SVG + PNG.
#   scripts/pcb/plot.sh board.kicad_pcb out_dir [layers]
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PCB="$1"; OUT="$2"
LAYERS="${3:-Edge.Cuts,F.Cu,B.Cu,F.Silkscreen,F.Fab,Dwgs.User,F.Courtyard}"
mkdir -p "$OUT"
name="$(basename "$PCB" .kicad_pcb)"
"$ROOT/scripts/kicad-cli" pcb export svg --mode-single --page-size-mode 2 \
  --exclude-drawing-sheet -l "$LAYERS" -o "$OUT/$name-2d.svg" "$PCB" >/dev/null
"$ROOT/.venv/bin/python" - "$OUT/$name-2d.svg" "$OUT/$name-2d.png" <<'PY'
import sys, cairosvg
cairosvg.svg2png(url=sys.argv[1], write_to=sys.argv[2], output_width=1600, background_color="white")
PY
echo "$OUT/$name-2d.png"
