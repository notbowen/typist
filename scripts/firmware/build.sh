#!/usr/bin/env bash
# Headless ZMK build of firmware/zmk-config, the same way ZMK's GitHub Actions
# workflow (build-user-config.yml) does it, in the zmkfirmware/zmk-build-arm image.
#
#   scripts/firmware/build.sh            all targets from build.yaml
#   scripts/firmware/build.sh sweep_xiao_left   only shields matching the filter
#
# Workspace (zmk + zephyr + modules, ~1.5 GB) : build/zmk/ws  (west.yml from the config)
# Outputs                                     : build/firmware/<shield>-<board>.uf2
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
CFG=$ROOT/firmware/zmk-config
WS=$ROOT/build/zmk/ws
OUT=$ROOT/build/firmware
IMAGE=${ZMK_IMAGE:-zmkfirmware/zmk-build-arm:stable}
FILTER=${1:-}

mkdir -p "$WS/config" "$OUT"
cp "$CFG/config/west.yml" "$WS/config/west.yml"

# board/shield pairs from build.yaml
mapfile -t TARGETS < <(python3 - "$CFG/build.yaml" <<'PY'
import sys, yaml
for t in yaml.safe_load(open(sys.argv[1]))["include"]:
    print(f'{t["board"]} {t.get("shield", "")}')
PY
)

docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -v "$ROOT:$ROOT" -w "$WS" "$IMAGE" bash -euo pipefail -c '
  [ -d .west ] || west init -l config
  west update --fetch-opt=--filter=tree:0 -n >/dev/null 2>&1 || west update --fetch-opt=--filter=tree:0
  west zephyr-export >/dev/null
  CFG='"$CFG"'; OUT='"$OUT"'; FILTER="'"$FILTER"'"
  extra=""; [ -e "$CFG/zephyr/module.yml" ] && extra="-DZMK_EXTRA_MODULES=$CFG"
  rc=0
  while read -r board shield; do
    [ -n "$FILTER" ] && [[ "$shield" != *$FILTER* ]] && continue
    name="${shield:+$shield-}${board//\//_}"
    echo "=== $name"
    if west build -p -s zmk/app -d "build/$name" -b "$board" -- \
        -DZMK_CONFIG="$CFG/config" ${shield:+-DSHIELD=$shield} $extra > "$OUT/$name.log" 2>&1; then
      cp "build/$name/zephyr/zmk.uf2" "$OUT/$name.uf2"
      grep -E "^ *(FLASH|RAM):" "$OUT/$name.log" | sed "s/^/    /"
      ls -l "$OUT/$name.uf2" | awk "{print \"    uf2 \" \$5 \" bytes\"}"
    else
      echo "    FAILED, see $OUT/$name.log"; tail -30 "$OUT/$name.log"; rc=1
    fi
  done <<< "'"$(printf '%s\n' "${TARGETS[@]}")"'"
  exit $rc
'
