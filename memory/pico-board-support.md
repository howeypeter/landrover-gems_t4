---
name: pico-board-support
description: Which Pico boards the K-line adapter supports now, and the Pico 2 W wireless mode (firmware built 2026-09-07)
metadata:
  type: project
---

**Decided 2026-07-07.** Firmware supports **Raspberry Pi Pico and Pico 2**
(both wired over USB) — no source changes between them, since
`firmware/pico_kline/pico_kline.ino` only uses the portable Arduino API
(`Serial`, `Serial1`, `pinMode`, `digitalWrite`, `delay`, `millis`), which
`arduino-pico` implements identically on RP2040 (Pico) and RP2350 (Pico 2).
Only the build's `--fqbn` target differs (`rpipico` vs `rpipico2`) — see
`firmware/README.md` "Build & flash".

**Pico W / Pico 2 W firmware WiFi firmware is BUILT (2026-09-07)** (use `firmware/pico_kline_wifi/` on a W board). But as of **v0.0.5 (2026-07-11) the LAPTOP side of the wireless
path IS built** — see "Wireless status" below.

## ⚠️ Transceiver: bare L9637D, NOT the ISO 9141 Click (2026-07-11)
The docs originally specified the **MikroE ISO 9141 Click** (which uses the ST
**L9637D** chip). Agent research 2026-07-11 confirmed the Click is
**retired/unavailable in the US** (was SparkFun-exclusive, delisted). Decision:
buy the **bare E-L9637D** (DIP-8, ~$2 from DigiKey/Mouser) + a breadboard and
wire it to the Pico — same chip, same pins as the Click's breakout. Wiring
guide in `firmware/README.md`; shopping lists are in the project root
(untracked). Other US options that exist but weren't chosen: FTDI FT232RL KKL
cable (read-only-ish, quick), CANable (CAN only — wrong protocol, skip).

## Wireless status: laptop side BUILT (v0.0.5), Pico WiFi firmware BUILT (2026-09-07)
The WiFi mode's design landed exactly as scoped, but **only on the host side**:
- **BUILT:** `gems_t4/transport/tcp.py` (`TcpTransport`, `is_wireless=True`),
  `gems_t4/app/server.py` (`gems_t4 serve` — virtual ECU or USB-Pico bridge),
  the `KwpClient` wireless write gate, the `--connect` CLI flag, and the GUI
  connection screen. A future WiFi Pico just answers the same host-protocol
  frames `serve` answers today — nothing else on the laptop changes.
- **BUILT (2026-09-07):** the **Pico W / Pico 2 W WiFi firmware** (`firmware/pico_kline_wifi/`)
  — join WiFi and expose the host protocol over a TCP socket. Design notes
  (from when it was fully scoped): WiFi/TCP not BLE (BLE's ~20–244B MTU vs our
  255B frames needs pointless chunking; BLE ruled out for ECU work generally);
  firmware stays a dumb timed pipe (the read-only policy lives in Python, not
  firmware); refactor firmware I/O over any `Stream` so one handler serves both
  `Serial` and a `WiFiClient`; compile-time `GEMS_ENABLE_WIFI` toggle +
  gitignored `wifi_config.h`. Built as scoped: WiFiServer on TCP :9141, host protocol over a WiFiClient, gitignored `wifi_secrets.h`, mDNS `gems-pico.local`. Connect: `gems_t4 kline ... --connect <pico-ip>`.
- Write policy as actually shipped (v0.0.5): over a wireless transport,
  `KwpClient` refuses SIDs `$27`/`$30`/`$3B` + the `$31` learn routines unless
  `allow_writes`; reads, `$14` clear and `$31` routine `0x03` (immo status)
  stay allowed. (Slightly different from the original scoping note above — the
  shipped gate is the source of truth. See [[implementation-status]].)

Related: [[research-hardware-interfaces]], [[tech-stack-decision]],
[[implementation-status]], [[eprom-programmability-question]].
