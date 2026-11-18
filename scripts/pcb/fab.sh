#!/usr/bin/env bash
# Manufacturing outputs for one board (JLCPCB/PCBWay-style zip).
#   scripts/pcb/fab.sh board.kicad_pcb out_dir
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PCB="$1"; OUT="$2"
name="$(basename "$PCB" .kicad_pcb)"
K="$ROOT/scripts/kicad-cli"
g="$OUT/$name-gerbers"
rm -rf "$g"; mkdir -p "$g"
"$K" pcb export gerbers -o "$g/" \
  -l F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts "$PCB" >/dev/null
"$K" pcb export drill -o "$g/" --format excellon --excellon-separate-th --generate-map --map-format gerberx2 "$PCB" >/dev/null
"$K" pcb export pos -o "$OUT/$name-pos.csv" --format csv --units mm "$PCB" >/dev/null
"$K" pcb export step --force --include-tracks --include-pads --include-zones -o "$OUT/$name.step" "$PCB" >/dev/null 2>&1 \
  || echo "warning: STEP export failed" >&2
(cd "$g" && rm -f "../$name-gerbers.zip" && zip -q "../$name-gerbers.zip" ./*)
echo "$name: $(ls "$g" | wc -l) fab files -> $OUT/$name-gerbers.zip, $OUT/$name.step"
