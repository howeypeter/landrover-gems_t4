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

## Bluetooth (SPP) transport — firmware BUILT 2026-09-07
`firmware/pico_kline_bt/pico_kline_bt.ino` serves the host protocol over
**Bluetooth Classic SPP** (arduino-pico `SerialBT`, slave role). Reason: the
WiFi/hotspot route forces the LAPTOP onto the same network (it loses home WiFi);
BT is point-to-point, so the laptop keeps its WiFi and pairs the Pico as a
**virtual COM port** → reuses the existing serial transport, `gems_t4 kline
... --port COMx`, **no Python change**. It's a **superset** firmware (all
production host cmds + pentest `CMD_RAW_INIT` 0x05), so gems_t4 AND the throwaway
pentest/debug scripts (`~/pentest_scan.py`, `~/da*_probe.py` — they hardcode
`PORT="COMx"`, edit it to the BT port) all run over one BT link. Build: enable
the BT stack — fqbn `rp2040:rp2040:rpipico2w:ipbtstack=ipv4btcble` (IDE: Tools >
IP/Bluetooth Stack > "IPv4 + Bluetooth"); PING reports
`gems_t4-pico-bt-pentest 2.1.0` — the "pentest" substring is REQUIRED because
pentest_scan.py gates on `"pentest" in ping()` (startup + mid-sweep recovery).
**Security caveat (differs from WiFi):** the paired SPP link looks *wired* to the
laptop (`PicoAdapterTransport`, is_wireless=False) so the read-only wireless gate
does NOT apply — **writes allowed by default**; pair only trusted laptops. BT SPP
COM ports ignore the pyserial baud setting. Confirmed feasible: Pico 2 W + C/C++
Pico SDK support BT Classic SPP (NOT MicroPython). **NOT yet flashed/verified on
hardware** (written, not compiled here). Detail: `firmware/README.md`.

## Combined WiFi+Bluetooth firmware — BUILT 2026-09-07 (RECOMMENDED wireless build)
`firmware/pico_kline_wireless/pico_kline_wireless.ino` runs **both radios at
once** (CYW43 + `ipbtstack=ipv4btcble` do WiFi + BT Classic concurrently). Host
frame I/O goes through a `Stream*` that points at whichever tester connected
first (BT `SerialBT` or a TCP `WiFiClient`) — one at a time (one K-line). One
flashed board is reachable by TCP (`--connect gems-pico.local`) OR a paired BT
COM port (`--port COMx`). Superset (incl. pentest `CMD_RAW_INIT`); PING =
`gems_t4-pico-wireless-pentest 2.1.0`. Includes headless BT Just-Works pairing +
WiFiMulti multi-SSID. Needs its OWN `wifi_secrets.h` in that folder (gitignored).
Single-radio sketches (`pico_kline_wifi`, `pico_kline_bt`) kept as fallbacks if
WiFi+BT coexistence is flaky during the delay()-heavy 5-baud init. NOT yet
flashed/verified. There are now 5 firmware sketches: pico_kline (USB),
pico_kline_pentest (USB+RAW_INIT), pico_kline_wifi, pico_kline_bt,
pico_kline_wireless. Detail: `firmware/README.md`.

## Bluetooth LE (BLE) transport — BUILT 2026-09-07 (Classic SPP proved flaky)
Windows Bluetooth **Classic** SPP turned out unreliable in real use: the bond is
wiped by every firmware re-flash, the **outgoing** COM port must be manually
re-created (COM Ports tab → Add → Outgoing) and never auto-reconnects, and it
often sits in "Other devices / Not connected". So we added **BLE**:
`firmware/pico_kline_ble/pico_kline_ble.ino` (arduino-pico `BLEServiceUART`, a
Nordic UART Service) + host `gems_t4/transport/ble.py` (`BleTransport`, uses
`bleak`) + CLI `gems_t4 kline ... --ble [NAME|ADDR]`. BLE GATT needs **no bonding
/ no pairing / no COM port** — bleak connects to the NUS by name (`gems-pico`).
NUS UUIDs: service 6E400001, RX 6E400002 (write), TX 6E400003 (notify). Superset
(incl. pentest CMD_RAW_INIT); PING `gems_t4-pico-ble-pentest 2.1.0`. Build:
`ipbtstack=ipv4btcble` (same as Classic). `is_wireless=False` (writes allowed).
Needs `pip install bleak` (`[ble]` extra). **✅ VERIFIED on hardware 2026-09-07**
(Pico 2 W): scan shows real NUS UUIDs, PING round-tripped `gems_t4-pico-ble-pentest
2.1.0`, chunked-notify reassembly good, no pairing/no COM port. TWO fixes were
required: (1) **arduino-pico core bug** — `BLEUUID(String)` parses 128-bit UUIDs
with `%llx`, unsupported by **newlib-nano `sscanf`**, so all 128-bit UUIDs came
out ZERO (broke the lib's own BLEServiceUART). Patched `…/6.1.0/libraries/BLE/src/
BLEUUID.h` to parse without long-long — TOOLCHAIN-LOCAL, re-apply after a core
update; worth an upstream PR to earlephilhower/arduino-pico. (2) **name truncated
to "gems-pic"** because advertising the 128-bit UUID left ~8 chars — fixed with
`BLE.startAdvertising(false)` + `BleTransport` prefix-matches a shortened name.
BLE notifies truncate to the ATT MTU (don't fragment) → ≤16 B chunks + delay;
tune `BLE_TX_CHUNK` if replies garble. **Real-ECU read CONFIRMED over BLE
2026-09-07:** `gems_t4 kline dtc --ble` returned P1193/P0158/P1316/P0125 from a
real GEMS ECU — full stack proven (BLE + 5-baud init + multi-frame Mode 03).
Upstream PR for the BLEUUID bug is in the CLAUDE.md backlog.
Now **6 firmware sketches**: pico_kline (USB), pico_kline_pentest (USB+RAW_INIT),
pico_kline_wifi, pico_kline_bt (Classic SPP), pico_kline_wireless (WiFi+Classic),
pico_kline_ble (BLE). Classic SPP kept but BLE is preferred for wireless-only.

## Powering the Pico untethered (decided 2026-09-07)
The WiFi firmware removes the laptop USB *data* tether, but the Pico still needs
5 V. Decision:
- **NOW — route C:** power the Pico from a **USB wall-charger / power bank** (no
  board change). This is the interim, in effect immediately.
- **BACKLOG — route A (before PCB1 fab):** on-board **12 V→5 V buck** (set
  5.0–5.1 V) → **1N5817 Schottky** (cathode/band toward the Pico) → Pico **VSYS
  (pin 39)**; GND → pin 38. **Feed VSYS, never VBUS (pin 40)** (onboard Schottky
  VBUS→VSYS blocks backflow, so VSYS-feed is safe alongside USB). L9637D has **no
  5 V output** (its VCC is an input, VS is 12 V in) — can't tap it. An ATX +5 V
  rail could feed VSYS directly (skip the buck) but the user has no ATX PSU.
- **Per the user: route A MUST be resolved BEFORE finalizing/ordering the PCB1
  schematic** — it changes PCB1's power section. Tracked in CLAUDE.md "Backlog /
  tech debt" + `hardware/gems-2pcb/README.md`. See [[repo-git-state]].

Related: [[research-hardware-interfaces]], [[tech-stack-decision]],
[[implementation-status]], [[eprom-programmability-question]].
