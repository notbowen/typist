#!/usr/bin/env bash
# Build + verify the case for one half.
#   scripts/cad/check.sh build/pcb/left.geom.json build/cad/left
# Steps: build123d case + fit check, mesh printability checks, PrusaSlicer
# slice, renders. Exit 1 if any gate fails.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
GEOM="$1"; OUT="$2"
PY="$ROOT/.venv/bin/python"
rc=0
"$PY" "$ROOT/cad/build.py" "$GEOM" "$OUT" || rc=1
"$PY" "$ROOT/scripts/cad/verify_mesh.py" "$OUT/case.stl" --json "$OUT/mesh.json" >/dev/null \
  && echo "mesh: OK ($(python3 -c "import json;d=json.load(open('$OUT/mesh.json'));print(d['size_mm'],'mm, wall p01',d['wall']['p01'],'mm, overhang',d['overhang']['area_mm2'],'mm2')"))" \
  || { echo "mesh: FAIL"; python3 -c "import json;print(json.load(open('$OUT/mesh.json'))['fails'])"; rc=1; }
"$ROOT/scripts/cad/slice.sh" "$OUT/case.stl" | grep '^;' || rc=1
"$PY" "$ROOT/scripts/cad/plot2d.py" "$GEOM" "$OUT/plot2d.png" >/dev/null
A="$OUT/assembly"
specs=("$OUT/case.stl:#b9b1a3")
for f in "$A"/*.stl; do
  case "$(basename "$f")" in
    solid-pcb.stl) c="#2f6b3a" ;;
    solid-switches.stl) c="#e8e8e8" ;;
    solid-mcu_*) c="#3060a0" ;;
    solid-battery.stl) c="#c0c4cc" ;;
    solid-jst_*|solid-pwr_*) c="#202020" ;;
    solid-under_pcb.stl) c="#d0a030" ;;
    keepout-keycap_travel.stl) continue ;;   # hides everything; render separately if needed
    keepout-*) c="#ff4040:0.4" ;;
    *) c="#a0a0a0" ;;
  esac
  specs+=("$f:$c")
done
"$PY" "$ROOT/scripts/cad/render.py" "$OUT/assembly.png" "${specs[@]}" >/dev/null
"$PY" "$ROOT/scripts/cad/render.py" "$OUT/case.png" "$OUT/case.stl:#b9b1a3" --views iso,top,back,under >/dev/null
echo "renders: $OUT/assembly.png $OUT/case.png $OUT/plot2d.png"
exit $rc
