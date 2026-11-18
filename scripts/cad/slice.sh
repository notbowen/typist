#!/usr/bin/env bash
# Slice an STL with PrusaSlicer (headless) to prove it is printable and get
# time/filament estimates.
#   scripts/cad/slice.sh part.stl [profile.ini]   -> part.gcode next to the STL
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
STL="$1"; INI="${2:-$ROOT/config/prusa-pla-0.2.ini}"
OUT="${STL%.stl}.gcode"
prusa-slicer --info "$STL" | grep -Ei "manifold|size|volume|facets" || true
prusa-slicer --load "$INI" --center 110,110 --export-gcode -o "$OUT" "$STL" > "${OUT%.gcode}.slice.log" 2>&1 \
  || { tail -20 "${OUT%.gcode}.slice.log" >&2; exit 1; }
grep -E "^; (estimated printing time \(normal mode\)|total filament used \[g\]|filament used \[mm\]) =" "$OUT"
