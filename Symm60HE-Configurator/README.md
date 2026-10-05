# Symm60HE Configurator

A dedicated browser configurator for the current 69-channel Mokeded Symm60HE
PCBs and the paired libhmk firmware v1.9 image.

The configurator talks directly to the keyboard with WebHID. It is a static web
application: after deployment to an HTTPS site, users open the page in Chrome,
Edge, or another desktop Chromium browser and choose **Connect Symm60HE**. No
native application, driver, account, or server-side API is required.

## Supported controls

- four named physical-layout profiles
  - WKL / split Backspace
  - Arrows / split Backspace
  - WKL / 2U Backspace
  - Arrows / 2U Backspace
- four remappable keymap layers per profile
- per-key actuation distance
- per-key rapid-trigger press/release distance and continuous rapid trigger
- SOCD/null binds, dynamic keystrokes, tap-hold, toggle, and macros
- advanced-key tick rate
- XInput enablement, gamepad buttons, analog stick assignments and curves
- square joystick, snappy joystick, and keyboard/gamepad override behavior
- live analog telemetry for all 69 Hall channels
- recalibration and calibration-threshold controls
- 1 kHz / 8 kHz USB polling selection
- dual-chain RGB lighting with solid, breathing, rainbow, and wave effects
- RGB color, brightness, speed, and mirrored-half controls
- a 350 mA firmware LED-current ceiling
- profile import, export, duplicate, restore, and factory reset
- reboot and bootloader entry

## Device and firmware contract

The chooser and post-connect checks accept only:

| Field             | Value      |
| ----------------- | ---------- |
| Product           | `Symm60HE` |
| USB VID           | `0xAB50`   |
| USB PID           | `0xAB61`   |
| WebHID usage page | `0xFFAB`   |
| WebHID usage      | `0x00AB`   |
| Firmware version  | `1.9`      |
| HID report size   | 64 bytes   |

The application also validates the metadata returned by the keyboard before it
allows writes. This prevents the dedicated UI from accidentally configuring a
different libhmk device.

The paired firmware source and binaries live at:

```text
../Symm60HE/firmware/
```

## Run locally

WebHID is available on secure origins, including `https://` and the special
local development origin `http://localhost`.

```bash
pnpm install
pnpm dev
```

Then open the printed localhost URL in Chrome or Edge.

## Build the hosted web UI

```bash
pnpm install --frozen-lockfile
pnpm check
pnpm build
```

The deployable static site is written to `build/`. Serve that directory from an
HTTPS origin. The included manifest and service worker also make installation
as a PWA optional; installation is not required to configure the keyboard.

The build contains no analytics and sends keyboard configuration only between
the current browser and the USB device selected by the user.

## Browser support

Chrome and Edge on desktop are the intended browsers. Firefox and Safari do
not currently expose WebHID, and mobile Chromium platforms generally do not
provide the same USB HID access. A browser may require the user to reconnect
the device after firmware reboot or bootloader entry.

## Upstream and license

This application is a marked, Symm60HE-specific derivative of
[`peppapighs/hmkconf`](https://github.com/peppapighs/hmkconf), dev commit
`fb9cfa47667f40d6df2fb09753e34e1d0511b71a`, and remains licensed under
GPL-3.0. The public
[`Charading/Shego75HE`](https://github.com/Charading/Shego75HE) repository at
commit `d3bf35d82ec249b1d817185ce1dd5381c92513d2` was used as a product and visual
reference for its keys/performance navigation, per-key visualization, profile
workflow, and live sensor feedback. That repository contains no license file,
so no Shego source code, screenshots, or graphic assets are copied into this
application.

See [NOTICE.md](NOTICE.md) and [LICENSE](LICENSE).
