# ZMK config for the Sweep XIAO

Copy this folder into its own GitHub repository (ZMK's GitHub Actions build
expects `build.yaml` and `config/` at the repo root), add the standard
`.github/workflows/build.yml` from
[zmkfirmware/unified-zmk-config-template](https://github.com/zmkfirmware/unified-zmk-config-template),
push, and download the `.uf2` files from the Actions run.

Flashing: plug a half in over USB-C, double-tap the XIAO's tiny reset button so
it mounts as a drive, and copy the matching `.uf2` onto it. Flash
`settings_reset` to both halves first if they were paired with something else.

- Left half = central (connects to the computer), right half = peripheral.
- Matrix: columns D0-D4 (pinky to inner), rows D5, D8, D9, D10 (top, home, bottom, thumbs),
  `col2row` diodes. D6/D7 (UART) and the NFC pads are unused.
- On newer ZMK (Zephyr 4.1 and later), change `seeeduino_xiao_ble` to `xiao_ble//zmk` in `build.yaml`.
