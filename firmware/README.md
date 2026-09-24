# Pico K-line adapter firmware

`pico_kline_all/pico_kline_all.ino` is **the** sketch — one firmware that turns a
Raspberry Pi Pico (2) W + an ISO 9141 transceiver into the smart K-line adapter
for `gems_t4`. It serves the host protocol ([HOST_PROTOCOL.md](HOST_PROTOCOL.md))
over **USB, BLE, and (optional) WiFi at the same time**, so there's only one thing
to flash. The Pico owns all K-line timing; the Python transports drive it
(`transport/pico.py` = USB, `transport/ble.py` = BLE, `transport/tcp.py` = WiFi/TCP).

**Hardware-verified over BLE** — PING reports `gems_t4-pico-all-pentest 3.0.0`.
It's a superset that also answers the pentest `CMD_RAW_INIT`, so the debug/probe
scripts work too.

## Which board

- **Pico 2 W / Pico W** (RP2350 / RP2040 + CYW43) — required for **BLE and WiFi**.
- **Plain Pico / Pico 2** (no radio) — works **USB-only**: set `ENABLE_BLE 0` at
  the top of the sketch and build for `rpipico` / `rpipico2`.

## Bill of materials

| Part | Notes |
|---|---|
| Raspberry Pi **Pico 2 W** (or Pico W) | USB + BLE + WiFi. A plain Pico/Pico 2 works USB-only. |
| ST **L9637D** K-line transceiver (bare DIP-8 + breadboard) | The MikroE **ISO 9141 Click** used the same chip but is retired/unavailable in the US — wire the bare L9637D; same pins. |
| OBD-II (J1962) male pigtail | to the car's diagnostic socket |
| Inline fuse (1–2 A) | on the +12 V tap (pin 16 is always live) |

## Wiring

| Pico | L9637D | OBD-II J1962 |
|---|---|---|
| GP0 (Serial1 TX) | UART TX in | — |
| GP1 (Serial1 RX) | UART RX out | — |
| 3V3 | logic Vcc | — |
| GND | GND | pins 4 & 5 (grounds) |
| — | VBAT | **pin 16 (+12 V, via fuse)** |
| — | K-line | **pin 7** |

For the proprietary `0xDA` channel the ECU's **L-line must be tied to the K node**
(bench only) — keep that on a removable jumper (see the wiring diagrams / manual).

**Safety:** OBD pin 16 is battery-live with the key off — fuse it, never short it
to ground. Start every session read-only; test any *write* (coding / Security-Learn)
against the virtual ECU first.

## Build & flash

Using `arduino-cli` with the Arduino-Pico core (Earle Philhower). Build with the
**combined Bluetooth stack** so BLE (and WiFi) are available:

```
arduino-cli core install rp2040:rp2040

# Pico 2 W (USB + BLE + WiFi):
arduino-cli compile -u --fqbn rp2040:rp2040:rpipico2w:ipbtstack=ipv4btcble firmware/pico_kline_all
#   Pico W  -> rpipicow ; IDE -> Tools > IP/Bluetooth Stack > "IPv4 + Bluetooth"

# Plain Pico / Pico 2 (USB only): set ENABLE_BLE 0 in the sketch, then:
arduino-cli compile -u --fqbn rp2040:rp2040:rpipico  firmware/pico_kline_all
```

> **⚠️ Build error `static assertion failed: This library needs Bluetooth
> enabled` (`_needsbt.h`, `ENABLE_CLASSIC 0`)?** The Bluetooth stack isn't
> compiled in. It is NOT a code bug — it's a board option. **Arduino IDE:** Tools
> → **IP/Bluetooth Stack → "IPv4 + Bluetooth"** (the default "IPv4 Only" has no
> BT). **arduino-cli:** the FQBN must carry `:ipbtstack=ipv4btcble` (as above).
> Also confirm the board is the **Pico 2 W / Pico W** (only the "W" variants have
> the CYW43 radio). For a non-radio board, build USB-only with `ENABLE_BLE 0`.

Sketch usage is ~12% flash / ~17% RAM. `enum ActiveT` lives in
`kline_transport.h` (a header so Arduino's auto-generated prototypes can see it).

## Transports — all in one firmware

Frame precedence when clients arrive: **USB > WiFi > BLE**. USB-CDC is always on.

```
gems_t4 kline live                       # USB (auto-detects the Pico's COM port)
gems_t4 kline live --ble                 # BLE  (no pairing, no COM port)
gems_t4 kline live --connect gems-pico.local   # WiFi/TCP (or --connect 192.168.x.y)
```

- **BLE** needs `pip install bleak` (or `pip install -e ".[ble]"`); it connects to
  the Nordic UART Service by name (`gems-pico`) — no bonding, no pairing dialog, no
  COM port. The onboard LED is solid while a BLE/WiFi client is connected.
- **WiFi** default TCP port is **9141**; it advertises `gems-pico.local` (mDNS).
  One tester at a time. Network writes are read-only unless `--allow-writes`.

### WiFi credentials — set at runtime, no reflash

The unified firmware stores WiFi creds in **LittleFS**, set over USB *or* BLE — no
`wifi_secrets.h`, and **no re-flash to change the password**:

```
gems_t4 kline set-wifi --ssid "YourNet" --password "yourpass"       # over USB
gems_t4 kline set-wifi --ble --ssid "YourNet" --password "yourpass"  # over BLE
gems_t4 kline wifi-status            # connected <ip> / offline (creds set: …) / no-creds
```

Use a **2.4 GHz** network (the CYW43 is 2.4 GHz only). WiFi stays idle until creds
are stored. (Host commands: `CMD_SET_WIFI 0x06`, `CMD_WIFI_STATUS 0x07`.)

### BLE — require arduino-pico core ≥ 6.1.1

> **⚠️ Do NOT build BLE on arduino-pico core 6.1.0 — it is broken for BLE.** In
> 6.1.0, `BLEUUID(String)` parses 128-bit UUIDs with `sscanf(…, "%llx", …)`;
> **newlib-nano's `sscanf` has no `long long`**, so the parse fails silently and
> every 128-bit UUID comes out all-zero — which breaks `BLEServiceUART` (bleak
> can't find `6e400003`). **This is fixed upstream in core 6.1.1** (issue #3524 /
> PR #3526 "Fix BLEUUID String constructor" — a long-long-free byte-wise parse),
> so **just use core ≥ 6.1.1 and no patch is needed**. (Historical note: on 6.1.0
> we hand-patched `libraries/BLE/src/BLEUUID.h`; that workaround is obsolete once
> the core is ≥ 6.1.1.) Upgrade with:
> `arduino-cli core upgrade rp2040:rp2040 --additional-urls <earlephilhower index>`.
> BLE notifications don't fragment — they truncate to the ATT MTU — so the
> firmware sends replies in ≤16 B chunks with a short inter-chunk delay; if replies
> ever garble, tune `BLE_TX_CHUNK` / the delay.

### Security

The firmware is a dumb timed K-line pipe. Over **WiFi** the read-only write policy
is enforced on the **laptop** (`KwpClient` + `TcpTransport.is_wireless`), *not* the
Pico — anything that reaches TCP `:9141` can drive the K-line, so keep it on a
trusted LAN / SSH tunnel. Over **BLE/USB** writes are allowed (treated as trusted);
use on a bench you control.

> Concurrent BLE+WiFi share the one CYW43 radio through the delay()-heavy ~2–3 s
> 5-baud init; if a wireless session drops mid-init, retry. USB is unaffected.
> (BLE is hardware-verified; the USB and WiFi paths of this unified build are still
> to be exercised on hardware.)

## Use from Python

```python
from gems_t4.transport.pico import PicoAdapterTransport, find_pico_port
from gems_t4.protocol.client import KwpClient

client = KwpClient(PicoAdapterTransport(find_pico_port()))  # USB auto-detect
client.connect(mode="slow")   # 5-baud init on the Pico
```

Or from the CLI: `gems_t4 kline live` (USB auto-detect), `--ble`, or `--connect <ip>`.
