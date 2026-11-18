#!/usr/bin/env bash
# Idempotent toolchain setup. Safe to re-run; each step is skipped when done.
#
# System packages (prusa-slicer, libosmesa6) are part of the Lapiz project
# environment. Elsewhere: apt install prusa-slicer libosmesa6 docker.io nodejs python3-venv
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

KICAD_IMAGE="${KICAD_IMAGE:-kicad/kicad:9.0}"
JRE_IMAGE="${JRE_IMAGE:-eclipse-temurin:25-jre}"
FR_VERSION=2.5.0
FR_SHA256=f6f51bb02245e8e717f9359bd260cc9c5c0b1bc0acc8b7cb2cd5b8ffeb5de3c7

step() { printf '\n== %s\n' "$*"; }

step "python venv (.venv)"
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt

step "node deps (ergogen)"
if [ -f package-lock.json ]; then npm ci --silent --no-audit --no-fund; else npm install --silent; fi

step "docker images ($KICAD_IMAGE, $JRE_IMAGE)"
for img in "$KICAD_IMAGE" "$JRE_IMAGE"; do
  docker image inspect "$img" >/dev/null 2>&1 || docker pull -q "$img"
done

step "freerouting $FR_VERSION"
mkdir -p tools
if ! echo "$FR_SHA256  tools/freerouting.jar" | sha256sum -c --status 2>/dev/null; then
  curl -fsSL -o tools/freerouting.jar \
    "https://github.com/freerouting/freerouting/releases/download/v$FR_VERSION/freerouting-$FR_VERSION.jar"
  echo "$FR_SHA256  tools/freerouting.jar" | sha256sum -c
fi

step "check"
scripts/kicad-cli version
npx ergogen --version
command -v prusa-slicer >/dev/null || { echo "prusa-slicer missing (apt install prusa-slicer)"; exit 1; }
echo "$(prusa-slicer --help 2>/dev/null | grep -m1 -o 'PrusaSlicer-[0-9.]*' || echo prusa-slicer)"
.venv/bin/python -c "import build123d, trimesh, pyvista; print('build123d', build123d.__version__, '| trimesh', trimesh.__version__, '| pyvista', pyvista.__version__)"
echo "setup OK"
