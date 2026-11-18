#!/usr/bin/env bash
# Verify one board: DRC gate, 2D plot, 3D renders, CAD geometry export.
#   scripts/pcb/check.sh board.kicad_pcb out_dir [--strict]
# Without --strict, unrouted connections are reported but allowed (fresh
# ergogen output is unrouted). With --strict they fail the check.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PCB="$1"; OUT="$2"; STRICT="${3:-}"
name="$(basename "$PCB" .kicad_pcb)"
mkdir -p "$OUT"
K="$ROOT/scripts/kicad-cli"

"$K" pcb drc --format json --severity-all -o "$OUT/$name-drc.json" "$PCB" >/dev/null
allow=(--allow-unrouted); [ "$STRICT" = "--strict" ] && allow=()
set +e
"$ROOT/.venv/bin/python" "$ROOT/scripts/pcb/drc_summary.py" "$OUT/$name-drc.json" "${allow[@]}"
drc=$?
set -e

"$ROOT/scripts/pcb/plot.sh" "$PCB" "$OUT" >/dev/null
for side in top bottom; do
  "$K" pcb render --side "$side" --width 1600 --height 1200 --quality basic \
    -o "$OUT/$name-3d-$side.png" "$PCB" >/dev/null
done
"$ROOT/scripts/kicad" python3 "$ROOT/scripts/pcb/export_geometry.py" "$PCB" "$OUT/$name.geom.json"
echo "$name: plots in $OUT/ ($name-2d.png, $name-3d-top.png, $name-3d-bottom.png)"
exit $drc
