#!/usr/bin/env bash
# Idempotent toolchain setup. Safe to re-run; each step is skipped when done.
#
# Needs docker, nodejs and python3-venv (apt install docker.io nodejs python3-venv).
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

step "logo font (JetBrains Mono ExtraBold, OFL; scripts/pcb/silk_logo.py)"
mkdir -p tools/fonts
[ -s tools/fonts/JetBrainsMono-ExtraBold.ttf ] || curl -fsSL -o tools/fonts/JetBrainsMono-ExtraBold.ttf \
  "https://github.com/JetBrains/JetBrainsMono/raw/master/fonts/ttf/JetBrainsMono-ExtraBold.ttf"

step "check"
scripts/kicad-cli version
npx ergogen --version
.venv/bin/python -c "import shapely, cairosvg; print('shapely', shapely.__version__, '| cairosvg', cairosvg.__version__)"
echo "setup OK"
