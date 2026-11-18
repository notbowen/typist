#!/usr/bin/env bash
# Autoroute a board with Freerouting.
#   scripts/pcb/autoroute.sh in.kicad_pcb out.kicad_pcb [max_passes]
# Existing tracks are kept; Freerouting routes the remaining connections.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
IN="$(realpath "$1")"; OUT="$(realpath -m "$2")"; PASSES="${3:-100}"
JAR="$ROOT/tools/freerouting.jar"
JRE_IMAGE="${JRE_IMAGE:-eclipse-temurin:25-jre}"
[ -f "$JAR" ] || { echo "missing $JAR - run scripts/setup.sh" >&2; exit 1; }
mkdir -p "$ROOT/build"
work="$(mktemp -d "$ROOT/build/.route.XXXX")"
[ -n "${KEEP_ROUTE_TMP:-}" ] || trap 'rm -rf "$work"' EXIT
name="$(basename "$IN" .kicad_pcb)"
"$ROOT/scripts/kicad" python3 "$ROOT/scripts/pcb/specctra.py" export "$IN" "$work/$name.dsn"
# Freerouting 2.x needs Java 25 (Debian 12 ships 17), so run the jar in a JRE container.
# (The native freerouting-cli 2.5.0 build crashes with a GraalVM serialization error.)
timeout "${ROUTE_TIMEOUT:-900}" docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$ROOT:$ROOT" -w "$work" "$JRE_IMAGE" \
  java -jar "$JAR" -de "$name.dsn" -do "$name.ses" \
  --router.autorouter.max_passes="$PASSES" --gui.enabled=false \
  > "$work/freerouting.log" 2>&1 || { grep -v '^\s*at ' "$work/freerouting.log" | tail -30 >&2; exit 1; }
[ -s "$work/$name.ses" ] || { echo "freerouting produced no session file" >&2; tail -30 "$work/freerouting.log" >&2; exit 1; }
grep -Ei "auto-?rout(ing|er).*(complete|finish)|unrouted|incomplete" "$work/freerouting.log" | tail -5 >&2 || true
mkdir -p "$(dirname "$OUT")"
"$ROOT/scripts/kicad" python3 "$ROOT/scripts/pcb/specctra.py" import "$IN" "$work/$name.ses" "$OUT"
echo "routed -> $OUT"
