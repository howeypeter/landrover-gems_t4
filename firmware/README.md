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

Three wireless sketches, all on the Pico 2 W / Pico W. They serve the *same*
host protocol; they differ only in which radio(s) carry it:

| Sketch | Radios | Use it when |
|---|---|---|
| **`pico_kline_wireless`** (recommended) | **WiFi + Bluetooth Classic at once** | You want both available without re-flashing — TCP when both ends share a network, Bluetooth (COM port) when they don't |
| `pico_kline_wifi` | WiFi/TCP only | You only use WiFi and want the leanest build |
| `pico_kline_bt`   | Bluetooth **Classic** SPP only | You only use Bluetooth Classic |
| `pico_kline_ble`  | Bluetooth **LE** (NUS) only | Classic SPP's Windows pairing / COM-port lifecycle is unreliable for you — **BLE needs no pairing and no COM port** (see below) |

> **Classic SPP vs BLE.** Bluetooth *Classic* SPP appears as a Windows virtual
> COM port (reuses `--port COMx`), but Windows' SPP outgoing-port lifecycle is
> flaky — bonds drop on re-flash, the outgoing port must be re-created, and it
> never auto-reconnects. **Bluetooth LE** (`pico_kline_ble`) avoids all of that:
> no bonding, no pairing dialog, no COM port — the Python client (`bleak`)
> connects to the service by name. Trade-off: BLE uses a different Python
> transport (`--ble`, needs `bleak`) and has an on-hardware tuning step (notify
> chunk size vs MTU). If Classic SPP fights you, use BLE.

All three need the Bluetooth-enabled build option **only if they use BT** — the
combined and BT sketches do (`ipbtstack=ipv4btcble`); the WiFi-only sketch does
not. The combined sketch is a **superset** and includes the pentest
`CMD_RAW_INIT`, so `gems_t4` and the pentest/debug scripts work over either
radio. Sections below cover each; start with the combined one.

## Combined WiFi + Bluetooth (Pico 2 W) — recommended

`pico_kline_wireless/pico_kline_wireless.ino` brings up **both radios at once**
and accepts whichever tester connects first (one at a time — there's one
K-line). So you can reach it by TCP *or* by a paired Bluetooth COM port from the
same flashed board.

1. **Credentials:** copy `pico_kline_wireless/wifi_secrets.h.example` →
   `wifi_secrets.h` and fill in your 2.4 GHz network(s) — same format as the
   WiFi sketch (multi-network `WIFI_NETWORKS` block supported). Bluetooth needs
   no credentials, so even with no WiFi in range the BT link still works.
2. **Flash with Bluetooth enabled** (this also keeps WiFi on):
   ```
   arduino-cli compile --fqbn rp2040:rp2040:rpipico2w:ipbtstack=ipv4btcble firmware/pico_kline_wireless
   arduino-cli upload  --fqbn rp2040:rp2040:rpipico2w:ipbtstack=ipv4btcble -p COM5 firmware/pico_kline_wireless
   ```
   (IDE: board "Raspberry Pi Pico 2 W", Tools > IP/Bluetooth Stack > "IPv4 +
   Bluetooth".)
3. **Use either transport** (see the two sections below for the details):
   - **WiFi:** `gems_t4 kline dtc --connect gems-pico.local` (or its IP).
   - **Bluetooth:** pair `gems-pico`, then `gems_t4 kline dtc --port COMx`.
   The onboard LED is solid whenever a tester is connected on *either* radio.

> **Coexistence caveat.** The 5-baud slow init spends ~2–3 s in `delay()` while
> the CYW43 services WiFi *and* BT; running both radios raises contention there.
> It should be fine, but if you ever see flaky inits, flash the single-radio
> `pico_kline_wifi` or `pico_kline_bt` instead — they're otherwise identical.

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

## Bluetooth (Pico 2 W) — no USB, and no shared WiFi needed

`pico_kline_bt/pico_kline_bt.ino` serves the **same K-line adapter over
Bluetooth Classic SPP** (Serial Port Profile). Use this when the WiFi/hotspot
route is awkward because it forces your **laptop** off its normal network — a
paired Bluetooth link is **point-to-point**, so the laptop keeps its WiFi and
just talks to the Pico directly. **Requires a WiFi/BT board** (Pico 2 W or
Pico W — the CYW43 does both); a plain Pico has no radio.

The neat part: a paired SPP device shows up on Windows as a **virtual COM
port**, so there is **nothing new on the Python side** — it's just another
`--port COMx`. Because it's an ordinary serial port, **any** tool that opens a
COM port works over it: `gems_t4`, the pentest sweep, and your ad-hoc debug/
probe scripts alike. This sketch is a **superset** — it answers every
production host command **plus** the pentest `CMD_RAW_INIT` primitive — so you
do **not** re-flash to switch between diagnostics and pentest/debug work over
Bluetooth. (`PING` reports `gems_t4-pico-bt-pentest 2.1.0`; the `pentest`
substring is intentional — `pentest_scan.py` refuses any firmware whose ping
doesn't contain it, so keep it in the version string.)

1. **Enable the Bluetooth stack** (this sketch won't link without it):
   - Arduino IDE: **Tools > IP/Bluetooth Stack > "IPv4 + Bluetooth"**.
   - arduino-cli: append the menu option to the fqbn (see step 2).
2. **Flash** (Pico 2 W shown; Pico W = `rpipicow`):
   ```
   arduino-cli compile --fqbn rp2040:rp2040:rpipico2w:ipbtstack=ipv4btcble firmware/pico_kline_bt
   arduino-cli upload  --fqbn rp2040:rp2040:rpipico2w:ipbtstack=ipv4btcble -p COM5 firmware/pico_kline_bt
   ```
   (`ipbtstack=ipv4btcble` = the "IPv4 + Bluetooth" menu choice; without it
   `SerialBT.h` won't compile/link.)
3. **Pair it:** Windows **Settings > Bluetooth & devices > Add device >
   Bluetooth**, pick **`gems-pico`**. The firmware pairs headless ("Just
   Works": it advertises `NO_INPUT_NO_OUTPUT` + auto-accept), so Windows should
   pair with **no PIN / no passkey prompt**. Windows then creates an **outgoing
   COM port** — find the number under *Bluetooth settings > More Bluetooth
   settings > COM Ports* (use the **"Outgoing"** one). The Pico's onboard LED
   is solid when a tester actually opens the port.
   > **Re-flashing wipes the pairing bond.** arduino-pico keeps the bond across
   > power-cycles but **not** across a firmware re-upload. So after every flash,
   > **Remove** any existing `gems-pico` in Windows Bluetooth first, then Add it
   > again — a stale bond causes "that PIN didn't work" / pairing failures.
   > (The stock SerialBT advertises `DISPLAY_YES_NO` and never confirms the
   > code, which is why an unpatched build can't pair headless — this firmware
   > overrides that in `setup()`.)
4. **Connect the laptop** over that COM port (your WiFi is untouched). Anything
   that speaks the host protocol on a serial port works — same COM number for
   all of it:
   ```
   gems_t4 kline live --port COM7        # the "Outgoing" gems-pico COM port
   gems_t4 kline dtc  --port COM7
   gems_t4 gui        --port COM7         # USB COM-port mode
   ```
   For the throwaway pentest/debug scripts in `C:\Users\howey\`
   (`pentest_scan.py`, `da*_probe.py`, …), point their serial port at the same
   "Outgoing" `gems-pico` COM port — they take the port from a `PORT = "COMx"`
   constant near the top of each file, so edit that to your Bluetooth COM number,
   then run as usual. They rely on `CMD_RAW_INIT`, which this superset firmware
   includes.

   > **SPP baud is a no-op.** These scripts open the port at 115200, but a
   > Bluetooth SPP COM port ignores the baud setting (the air link runs at BT
   > speed) — so no baud change is needed; it "just works" like a USB port,
   > only with a little more latency.

> **Security — different from WiFi mode.** A paired BT SPP link reaches the
> laptop as a *wired-looking* COM port, so the Python side treats it as a
> trusted (non-wireless) transport and **allows writes by default** (coding /
> immobiliser / actuators), exactly like plugging in USB — the read-only
> "wireless" gate does **not** apply. Only pair laptops you trust; start
> read-only until you mean to write.

> Enabling Bluetooth costs ~80 KB flash + ~20 KB RAM (fine on RP2350/RP2040).
> It's a separate sketch from the WiFi one — pick the transport you want and
> flash that; you don't run both at once.

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

> **⚠️ Unverified on hardware — needs one on-device tuning pass.** BLE
> notifications don't fragment; they truncate to the negotiated ATT MTU. The
> firmware sends replies in ≤16 B chunks with a short inter-chunk delay (which
> also pumps the CYW43 stack), and the Python side reassembles the byte stream.
> Real GEMS frames are small, so this is comfortable — but if replies look
> truncated/garbled on real hardware, tune `BLE_TX_CHUNK` / the delay in the
> sketch, or raise the ATT MTU.

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
