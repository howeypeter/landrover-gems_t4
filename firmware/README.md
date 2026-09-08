# Pico K-line adapter firmware

`pico_kline/pico_kline.ino` turns a Raspberry Pi Pico + an ISO 9141 transceiver
into the smart K-line adapter for `gems_t4`. The Pico owns all K-line timing and
speaks the USB-CDC host protocol in [HOST_PROTOCOL.md](HOST_PROTOCOL.md); the
Python `gems_t4.transport.pico.PicoAdapterTransport` drives it.

## Which board

**Raspberry Pi Pico or Pico 2 — either works, wired over USB.** The sketch only
uses the portable Arduino API (`Serial`, `Serial1`, `pinMode`, `digitalWrite`,
`delay`, `millis`), which the `arduino-pico` core implements identically on
both RP2040 (Pico) and RP2350 (Pico 2) boards — **no firmware source changes
between them**, only the build target (see "Build & flash" below).

Do **not** use a Pico W / Pico 2 W for now. Those add a wireless radio this
firmware doesn't use yet. The laptop side of the wireless mode already exists
(`gems_t4.transport.tcp` + `gems_t4 serve` speak this same host protocol over
TCP, read-only by default) — only the Pico WiFi *firmware* remains unbuilt; see
"Pico 2 W wireless (WiFi) mode" under Tech stack → Hardware in `CLAUDE.md`.

## Bill of materials

| Part | Notes |
|---|---|
| Raspberry Pi **Pico** or **Pico 2** (non-wireless) | USB-CDC to the laptop |
| ST **L9637D** K-line transceiver (bare DIP-8 chip + breadboard) | The MikroE **ISO 9141 Click** used the same chip but is retired/unavailable in the US (verified 2026-07-11) — wire the bare L9637D instead; same pins, see the shopping list in the project root |
| OBD-II (J1962) male pigtail | to the car's diagnostic socket |
| Inline fuse (1–2 A) | on the +12 V tap (pin 16 is always live) |

## Wiring

| Pico | ISO 9141 Click | OBD-II J1962 |
|---|---|---|
| GP0 (Serial1 TX) | UART TX in | — |
| GP1 (Serial1 RX) | UART RX out | — |
| 3V3 | logic Vcc | — |
| GND | GND | pins 4 & 5 (grounds) |
| — | VBAT | **pin 16 (+12 V, via fuse)** |
| — | K-line | **pin 7** |

**Safety:** OBD pin 16 is battery-live with the key off — fuse it, and never
short it to ground. Start every session read-only; test any *write* (coding /
Security-Learn) against the virtual ECU first.

## Build & flash

Using `arduino-cli` with the Arduino-Pico core (Earle Philhower). The same
`.ino` builds for either board — only the `--fqbn` target changes:

```
arduino-cli core install rp2040:rp2040

# Original Pico (RP2040):
arduino-cli compile --fqbn rp2040:rp2040:rpipico  firmware/pico_kline
arduino-cli upload  --fqbn rp2040:rp2040:rpipico  -p COM5 firmware/pico_kline

# Pico 2 (RP2350):
arduino-cli compile --fqbn rp2040:rp2040:rpipico2 firmware/pico_kline
arduino-cli upload  --fqbn rp2040:rp2040:rpipico2 -p COM5 firmware/pico_kline
```

> Board IDs can shift between `arduino-pico` core releases. If a target above
> isn't recognized, confirm the exact string with
> `arduino-cli board listall | grep -i pico` for your installed core version.

(Or open `pico_kline/pico_kline.ino` in the Arduino IDE and pick "Raspberry Pi
Pico" or "Raspberry Pi Pico 2" from the board menu — same package either way.)

## Wireless firmware — pick one to flash

Two wireless sketches, both on the Pico 2 W / Pico W. They serve the *same* host
protocol; they differ only in which radio carries it:

| Sketch | Radio | Use it when |
|---|---|---|
| `pico_kline_wifi` | WiFi / TCP | Both ends are on one network (home WiFi, or a Pi-at-the-car). Reach it with `--connect`. |
| **`pico_kline_ble`** (recommended for wireless) | Bluetooth **LE** (NUS) | Point-to-point, no shared network — **no pairing and no COM port**. Reach it with `--ble`. |

> **Bluetooth here means BLE only.** Bluetooth *Classic* SPP was removed
> (2026-09-08): on Windows its outgoing-COM-port lifecycle proved unreliable
> (bonds drop on re-flash, the port must be re-created, it never auto-reconnects).
> **Bluetooth LE** (`pico_kline_ble`) has none of that — no bonding, no pairing
> dialog, no COM port; the Python client (`bleak`) connects to the service by
> name. It's the confirmed, hardware-verified Bluetooth path.

Only the BLE sketch needs the Bluetooth-enabled build option
(`ipbtstack=ipv4btcble`); the WiFi-only sketch does not. Both are **supersets**
that include the pentest `CMD_RAW_INIT`, so `gems_t4` and the pentest/debug
scripts work over either. Sections below cover each.

## Wireless (Pico 2 W) — no USB needed

`pico_kline_wifi/pico_kline_wifi.ino` is the **same K-line adapter served over
WiFi/TCP** instead of USB. Same wiring to the L9637D/ECU; same host protocol; the
only change is the transport. **Requires a WiFi board** (Pico 2 W or Pico W) — a
plain Pico has no radio.

1. **Credentials** (kept out of git): in `firmware/pico_kline_wifi/`, copy
   `wifi_secrets.h.example` → `wifi_secrets.h` and set your **2.4 GHz** SSID +
   password (the CYW43 is 2.4 GHz only). `wifi_secrets.h` is `.gitignore`d.
   You can list **multiple** networks via the `WIFI_NETWORKS` X-macro block (one
   `X("ssid","pass")` line each) — on boot it joins whichever known 2.4 GHz
   network is in range with the strongest signal (handy for a home-WiFi + phone-
   hotspot fallback). A single `WIFI_SSID`/`WIFI_PASS` pair still works too.
   Editing credentials means **recompile + re-upload** — they're baked into the
   firmware binary, not stored as a file on the Pico.
2. **Flash** (Pico 2 W shown; Pico W = `rpipicow`):
   ```
   arduino-cli compile --fqbn rp2040:rp2040:rpipico2w firmware/pico_kline_wifi
   arduino-cli upload  --fqbn rp2040:rp2040:rpipico2w -p COM5 firmware/pico_kline_wifi
   ```
   (Or Arduino IDE → board "Raspberry Pi Pico 2 W".)
3. **Find it:** on first boot it prints its IP to USB serial (115200) — note it
   once. It also advertises **`gems-pico.local`** (mDNS) and registers the DHCP
   hostname `gems-pico`. The onboard LED is solid when WiFi is up. For a fixed
   address, uncomment the `STATIC_IP` block at the top of the sketch.
4. **Connect the laptop** (no USB to the Pico after this):
   ```
   gems_t4 kline live --connect gems-pico.local        # or --connect 192.168.x.y
   gems_t4 kline dtc  --connect 192.168.x.y
   gems_t4 gui        --connect 192.168.x.y             # GUI Network mode
   ```
   Default TCP port is **9141** (append `:PORT` to override). One tester at a
   time (one K-line). Writes are **read-only by default** over the network — add
   `--allow-writes` to permit `$30/$31/$3B` (see the security note).

> **Security:** the firmware is a dumb timed K-line pipe; the read-only write
> policy is enforced on the **laptop** (`KwpClient` + `TcpTransport.is_wireless`),
> **not** on the Pico. Anything that can reach TCP `:9141` can drive the K-line —
> so keep it on a trusted LAN (or an SSH tunnel), not exposed to the internet.

> Doing long 5-baud inits (~2–3 s of `delay()`) while the CYW43 services WiFi in
> the background is the one thing to watch on first bring-up; if a session drops
> mid-init, retry — the arduino-pico core services WiFi during `delay()`.

## Bluetooth LE (Pico 2 W) — no pairing, no COM port

`pico_kline_ble/pico_kline_ble.ino` serves the host protocol over a **BLE Nordic
UART Service (NUS)**. This is the answer to flaky Windows Bluetooth *Classic*
SPP: BLE GATT needs **no bonding**, so there's **no pairing dialog, no virtual
COM port, and no incoming/outgoing port mess** — the Python client just connects
to the service by name. Point-to-point, so the laptop keeps its own WiFi.

NUS UUIDs (baked into both firmware and `gems_t4.transport.ble`):
`service 6E400001-…`, `RX 6E400002-…` (host→Pico write), `TX 6E400003-…`
(Pico→host notify). Advertises as **`gems-pico`**. Superset firmware (incl.
pentest `CMD_RAW_INIT`); PING = `gems_t4-pico-ble-pentest 2.1.0`.

1. **Install `bleak`** on the laptop (the Python BLE library):
   ```
   pip install bleak            # or:  pip install -e ".[ble]"
   ```
2. **Flash with Bluetooth enabled** (BLE uses the same stack option as Classic):
   ```
   arduino-cli compile --fqbn rp2040:rp2040:rpipico2w:ipbtstack=ipv4btcble firmware/pico_kline_ble
   arduino-cli upload  --fqbn rp2040:rp2040:rpipico2w:ipbtstack=ipv4btcble -p COM5 firmware/pico_kline_ble
   ```
   (IDE: Tools > IP/Bluetooth Stack > "IPv4 + Bluetooth".)
3. **Connect — no pairing step at all:**
   ```
   gems_t4 kline dtc --ble               # scans for "gems-pico"
   gems_t4 kline dtc --ble gems-pico      # or by name / BLE address
   gems_t4 kline live --ble
   ```
   The onboard LED is solid while a BLE client is connected.

> **✅ Verified on hardware 2026-09-07** (Pico 2 W): NUS UUIDs correct, PING
> round-tripped `gems_t4-pico-ble-pentest 2.1.0` (write + chunked-notify
> reassembly both good). BLE notifications don't fragment — they truncate to the
> ATT MTU — so the firmware sends replies in ≤16 B chunks with a short
> inter-chunk delay (which also pumps the CYW43 stack) and the Python side
> reassembles the byte stream. If replies ever garble, tune `BLE_TX_CHUNK` /
> the delay, or raise the MTU.
>
> **⚠️ Requires a one-line patch to the arduino-pico core** (`libraries/BLE/src/
> BLEUUID.h`). The stock `BLEUUID(String)` parses 128-bit UUIDs with
> `sscanf(..., "%llx", ...)`; **newlib-nano's `sscanf` has no `long long`
> support**, so the parse fails silently and **every 128-bit UUID comes out
> all-zero** — which breaks the library's own `BLEServiceUART` (bleak can't find
> `6e400003`). Fix: replace the `%llx` read with a `long-long`-free split, e.g.
> `sscanf(str, "%x-%x-%x-%x-%4x%x", &a,&b,&c,&d,&e_hi,&e_lo)` and pack
> `e_hi`(16-bit)+`e_lo`(32-bit) into the last 6 bytes. This patch lives in the
> toolchain, so **re-apply it after any arduino-pico core update** (and it is
> worth reporting upstream). Symptom if missing: `ble_scan.py` shows the service
> with `00000000-…` UUIDs.

> **Security:** no bonding and no link encryption by default — anything in BLE
> range that speaks NUS can drive the K-line, and the Python side treats BLE as a
> trusted (non-wireless) transport, so **writes are allowed**. Use on a bench you
> control.

## Use from Python

```python
from gems_t4.transport.pico import PicoAdapterTransport
from gems_t4.protocol.client import KwpClient

client = KwpClient(PicoAdapterTransport("COM5"))
client.connect(mode="slow")   # 5-baud init on the Pico
```

Or from the CLI: `gems_t4 live --port COM5`.
