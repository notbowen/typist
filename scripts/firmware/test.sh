#!/usr/bin/env bash
# Checks of the status-LED logic without hardware:
#  1. host unit test of firmware/zmk-config/src/status_logic.h (cc)
#  2. ZMK native_sim tests in firmware/zmk-config/tests/status-leds/ (ZMK's run-test.sh,
#     mock kscan, emulated GPIO LEDs; log lines compared with keycode_events.snapshot).
#     ZMK_TESTS_AUTO_ACCEPT=1 rewrites the snapshots.
# Needs the west workspace from scripts/firmware/build.sh.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
CFG=$ROOT/firmware/zmk-config
WS=$ROOT/build/zmk/ws
IMAGE=${ZMK_IMAGE:-zmkfirmware/zmk-build-arm:stable}
mkdir -p "$ROOT/build/firmware"

cc -Wall -Wextra -Werror -I"$CFG/src" "$CFG/tests/host/test_status_logic.c" \
   -o "$ROOT/build/firmware/test_status_logic"
"$ROOT/build/firmware/test_status_logic"

[ -d "$WS/zmk/app" ] || "$ROOT/scripts/firmware/build.sh" settings_reset
docker run --rm -u "$(id -u):$(id -g)" -e HOME=/tmp -e ZMK_TESTS_AUTO_ACCEPT="${ZMK_TESTS_AUTO_ACCEPT:-}" \
  -v "$ROOT:$ROOT" -w "$WS/zmk/app" "$IMAGE" sh -c "
    west zephyr-export >/dev/null
    rc=0
    for t in \$(find '$CFG/tests/status-leds' -name native_sim.keymap -exec dirname {} \; | sort); do
      ZMK_BUILD_DIR='$WS/build/tests-sl' ZMK_EXTRA_MODULES='$CFG' ./run-test.sh \"\$t\" || rc=1
    done
    exit \$rc"
