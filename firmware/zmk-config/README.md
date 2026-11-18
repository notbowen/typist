# ZMK config for the Sweep XIAO

Copy this folder into its own GitHub repository (ZMK's GitHub Actions build
expects `build.yaml` and `config/` at the repo root), add the standard
`.github/workflows/build.yml` from
[zmkfirmware/unified-zmk-config-template](https://github.com/zmkfirmware/unified-zmk-config-template),
push, and download the `.uf2` files from the Actions run. The folder is also a
Zephyr module (`zephyr/module.yml`, for the status-LED code); ZMK's workflow
detects that and loads it automatically.

Building locally (from the main repo, Docker only): `make firmware` →
`build/firmware/sweep_xiao_{left,right}-xiao_ble__zmk.uf2`,
`settings_reset-xiao_ble__zmk.uf2`. `make firmware-test` runs the LED logic tests.

ZMK is pinned in `config/west.yml` to a commit of ZMK main (Zephyr 4.1, board
`xiao_ble//zmk`). To update, change the revision there and rebuild.

Flashing: plug a half in over USB-C, double-tap the XIAO's tiny reset button so
it mounts as a drive, and copy the matching `.uf2` onto it. Flash
`settings_reset` to both halves first if they were paired with something else.

- Left half = central (connects to the computer), right half = peripheral.
- One reversible PCB for both halves; the pin map is identical on both.
- Matrix: columns D0-D4 (pinky to inner), rows D5, D8, D9, D10 (top, home, bottom, thumbs),
  `col2row` diodes.
- Status LEDs (gpio-leds `status_leds`): LED1 = D6, LED2 = D7, LED3 = P0.09 (NFC1),
  LED4 = P0.10 (NFC2). UART0 is disabled and the NFC pads are switched to GPIO
  (`&uicr { nfct-pins-as-gpios; }`, applied by Zephyr on the first boot).

## Status LEDs

The LEDs are **off in steady state**; everything below is a short blink or a
display of at most a couple of seconds (driven by `src/status_leds.c`).

| When | Left half (central) | Right half (peripheral) |
|---|---|---|
| Power on / reset | battery level for 2 s | battery level for 2 s |
| Battery level | 1-4 LEDs solid: ≤25 % → LED1, ≤50 % → LED1-2, ≤75 % → LED1-3, else all four | same |
| Battery ≤ 10 % | LED1 blinks 5× fast (on boot, on demand, and when the level drops; at most every 5 min) | same |
| Connected | profile LED (profile 0-3 → LED1-LED4) on for 1 s, then dark | all four on for 1 s when the link to the left half comes up |
| Profile open (not paired yet), advertising | profile LED triple-blinks every 1.5 s | — |
| Paired host not connected | profile LED short blip every 1.5 s | — |
| Not linked to the left half | — | LED1→LED4 chase every 1.5 s |
| Active layer (while held) | layer 1-4 → LED1-LED4 (NAV = LED1, SYM = LED2, SYS = LED3) | — (layers live on the central) |

- "Not connected" indications run for 30 s after boot, a profile change
  (`&bt BT_SEL n`, connect, disconnect) or an `IND_CON` press, then stop to save power.
  ZMK keeps advertising; press `IND_CON` to look again.
- Profiles ≥ 4 (ZMK has 5) light all four LEDs.
- A battery level of 0 means "not measured yet" and also shows as the LED1 blink.
- On deep sleep (15 min idle) all LEDs are switched off first.

Keymap (`config/sweep_xiao.keymap`): on the SYS layer (hold both thumb layer
keys) the **Z** position is `&status_ind IND_BAT` (both halves show their
battery) and **X** is `&status_ind IND_CON` (show the connection state again).
The behavior is defined in `dts/behaviors/status_ind.dtsi`; parameters in
`include/dt-bindings/sweep/status_leds.h`.

Options (put in `config/sweep_xiao.conf`, defaults in `Kconfig`):

| Option | Default | |
|---|---|---|
| `CONFIG_SWEEP_STATUS_LEDS` | y (if the `status_leds` node exists) | whole feature |
| `CONFIG_SWEEP_STATUS_LEDS_BOOT_BATTERY` | y | battery display on boot |
| `CONFIG_SWEEP_STATUS_LEDS_BATTERY_MS` | 2000 | battery display time |
| `CONFIG_SWEEP_STATUS_LEDS_BATTERY_LOW` | 10 | low-battery threshold, % |
| `CONFIG_SWEEP_STATUS_LEDS_LOW_WARN_INTERVAL_S` | 300 | min. time between low warnings |
| `CONFIG_SWEEP_STATUS_LEDS_CONN_TIMEOUT_S` | 30 | how long "not connected" blinks continue |
| `CONFIG_SWEEP_STATUS_LEDS_CONFIRM_MS` | 1000 | "connected" confirmation length |
| `CONFIG_SWEEP_STATUS_LEDS_LAYER` | y (central) | layer LEDs while a layer is active |

### What is verified

- All three targets (left, right, settings_reset) compile and link with the pinned ZMK.
- `tests/host/test_status_logic.c`: the decisions (battery → LEDs, profile/layer → LED,
  what each connection state shows and when it stops) on the host.
- `tests/status-leds/layers`: ZMK native_sim run with emulated GPIO LEDs: the layer LEDs
  follow `&mo` presses (including nested layers) and `&status_ind` reaches the module.
- **Not** verified (needs the hardware): real LED wiring and brightness, NFC pads
  actually switching to GPIO, battery readings, and the BLE connection indications
  (no BLE in the simulator).
