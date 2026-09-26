# Pico K-line adapter firmware

`pico_kline_all/pico_kline_all.ino` is **the** sketch — one firmware that turns a
Raspberry Pi Pico (2) W + an ISO 9141 transceiver into the smart K-line adapter
for `gems_t4`. It serves the host protocol ([HOST_PROTOCOL.md](HOST_PROTOCOL.md))
over **USB, BLE, and (optional) WiFi at the same time**, so there's only one thing
to flash. The Pico owns all K-line timing; the Python transports drive it
(`transport/pico.py` = USB, `transport/ble.py` = BLE, `transport/tcp.py` = WiFi/TCP).

**Hardware-verified over BLE** at `3.0.0`; the current source is **`3.4.0`** and
needs a reflash to run on hardware. Changes since 3.0.0: **3.1.0** adds the MAC to
`wifi-status` (see below); **3.2.0** makes the **WiFi server single-client,
last-connection-wins** — a new tester cleanly takes over and drops any previous/
stale connection (fixes the first-wins lockout where a second client's socket was
accepted but never serviced → silent/intermittent WiFi failures, and a half-closed
connection held the slot); **3.3.0** makes **`CMD_INIT` baud-parameterised** — the
full W4-handshake init now runs at a caller-chosen baud (payload `[addr, mode,
baud_hi, baud_lo]`; 2-byte payload still defaults to 10400). This lets us open a
**real session with the Lucas 10AS at 9600** (GEMS is 10400) — `CMD_RAW_INIT`
only wakes a module, it does NOT complete the handshake, so it can't session the
10AS; **3.4.0** adds **`CMD_RAW_XFER` (0x08)** — raw send/recv at the session baud
with NO echo cancellation, returning the full RX (echo + response) so the host can
separate them (the RE tool for the 10AS, whose framing/echo timing the normal
echo-cancelling `SEND_RECV` path mangles). PING reports
`gems_t4-pico-all-pentest <version>`. It's a superset that also
answers the pentest `CMD_RAW_INIT`, so the debug/probe scripts work too.

> ⚠️ **WiFi = one tester at a time.** Even with last-wins takeover, only ONE
> client should actively drive the Pico. If the always-on portal (`gems_t4 api`)
> is pointed at the same WiFi Pico as your CLI, they'll keep kicking each other
> off. Keep the portal on the **virtual ECU** while bench-driving real hardware
> from the CLI (or `Stop-ScheduledTask gems_t4-web`).

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
arduino-cli compile -u --fqbn rp2040:rp2040:rpipico2w:flash=4194304_1048576,ipbtstack=ipv4btcble firmware/pico_kline_all
#   Pico W  -> rpipicow ; IDE -> Tools > IP/Bluetooth Stack > "IPv4 + Bluetooth"
#   AND     -> Tools > Flash Size > "4MB (Sketch: 3MB, FS: 1MB)"

# Plain Pico / Pico 2 (USB only): set ENABLE_BLE 0 in the sketch, then:
arduino-cli compile -u --fqbn rp2040:rp2040:rpipico  firmware/pico_kline_all
```

> **⚠️ WiFi needs a LittleFS region — `flash=…_1048576` is NOT optional.** WiFi
> credentials are stored in LittleFS (`set-wifi`), so the build MUST allocate a
> filesystem. The board **default is "4MB (no FS)"** (`flash=4194304_0`), and a
> no-FS build makes `set-wifi` fail with **`status 2` (ST_BUS_ERROR)** /
> `wifi-status` = `no-creds` forever — creds have nowhere to save. Always build
> the WiFi firmware with a non-zero FS: the FQBN's `flash=4194304_1048576`
> (1 MB FS) above, or in the IDE **Tools → Flash Size → any "… FS: <n>KB/MB"**
> option (64 KB is enough; 1 MB is comfortable). Reflashing with an FS fixes an
> already-flashed no-FS Pico. (USB + BLE-only builds don't use LittleFS, so the FS
> option only matters when WiFi/`set-wifi` is in play.)

> **⚠️ Build error `static assertion failed: This library needs Bluetooth
> enabled` (`_needsbt.h`, `ENABLE_CLASSIC 0`)?** The Bluetooth stack isn't
> compiled in. It is NOT a code bug — it's a board option. **Arduino IDE:** Tools
> → **IP/Bluetooth Stack → "IPv4 + Bluetooth"** (the default "IPv4 Only" has no
> BT). **arduino-cli:** the FQBN must carry `:ipbtstack=ipv4btcble` (as above).
> Also confirm the board is the **Pico 2 W / Pico W** (only the "W" variants have
> the CYW43 radio). For a non-radio board, build USB-only with `ENABLE_BLE 0`.
>
> **⚠️ Arduino IDE link error — hundreds of `undefined reference to __wrap_memcpy
> / __wrap__malloc_r / main / _exit`, TinyUSB `mscd_*`/`hidd_*`/`midid_*`/`netd_*`,
> lwIP `__wrap_tcp_*`/`__wrap_pbuf_*`?** This is
> an **IDE build-config/cache problem, NOT the code, the core, or the toolchain** —
> and **not** a broken install, so **do not reinstall the core** (it won't help).
>
> **✅ CONFIRMED ROOT CAUSE + FIX (2026-09-24): a stale IDE core cache.** Clearing
> the IDE's compiled-core cache and rebuilding made it **link clean**. The IDE keeps
> a *separate* core cache at **`%LOCALAPPDATA%\arduino\cores\`** (dirs like
> `rp2040_rp2040_rpipico2w_ipbtstack_ipv4btcble_*`) — **distinct** from the
> `%LOCALAPPDATA%\arduino\sketches\` and `%TEMP%\arduino*` caches, so a normal
> "clear the build cache" step misses it. A `core.a` cached during an earlier failed
> build (e.g. the `_needsbt` BT-off error above, or a wrong USB/IP-BT stack pick) got
> reused, so the final link ran against a core that didn't match the selected board
> options. **The fix:** close the IDE and run (PowerShell) —
> ```
> Remove-Item "$env:LOCALAPPDATA\arduino\cores\*" -Recurse -Force -ErrorAction SilentlyContinue
> ```
> then reopen and rebuild. The first rebuild is slow (it recompiles the whole core —
> WiFi/BLE/lwIP/LittleFS/TinyUSB — a few minutes); every build after is fast again.
> Don't cancel that first rebuild — an interrupted build is what poisons the cache.
>
> **Why it is NOT a broken install (so do not reinstall the core):** the *identical*
> sketch — and even a bare empty `setup()/loop()` sketch — link **clean** via
> `arduino-cli` against the *exact same* on-disk core the IDE uses
> (`…\Arduino15\packages\rp2040\hardware\rp2040\6.1.1`, `pqt-gcc/5.0.0-9576866`,
> `arm-none-eabi 16.1.0`). Only **one** rp2040 core is installed (no duplicate), the
> IDE reads that same path, and the IDE's *bundled* `arduino-cli` is the **same
> version/commit** as standalone (1.5.1 / `01f3d4f2b`) — same data dir, no env
> override. The undefined set (`main` + newlib syscalls `_exit`/`_read`/`_write` +
> the `__wrap_*` shims + libpico's TinyUSB `_usbd_driver` class-driver table) is the
> signature of a cached core built for a **different board-option combination** than
> the one selected — a cache mismatch, not a bad toolchain.
>
> **If a cache clear ever doesn't fix it:** (1) match every Tools-menu option to the
> FQBN — **Board = Raspberry Pi Pico 2 W**, **USB Stack = "Pico SDK"**, **IP/Bluetooth
> Stack = "IPv4 + Bluetooth"** (`ipbtstack=ipv4btcble`); (2) rule out the **OneDrive
> path** by copying `firmware/pico_kline_all` to `C:\pico\pico_kline_all\` and building
> there; (3) fall back to `arduino-cli` (the supported path, always links clean):
> `arduino-cli compile -u -p COM# --fqbn "rp2040:rp2040:rpipico2w:ipbtstack=ipv4btcble" firmware/pico_kline_all`.
> To inspect the IDE's link recipe, turn on **File → Preferences → "Show verbose
> output during: compile"** and diff its final `…ld.exe…` line against
> `arduino-cli compile --verbose`.

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
gems_t4 kline set-wifi --connect <ip> --ssid "YourNet" --password … # over WiFi (once joined)
gems_t4 kline wifi-status            # see format below
```

Use a **2.4 GHz** network (the CYW43 is 2.4 GHz only). WiFi stays idle until creds
are stored. (Host commands: `CMD_SET_WIFI 0x06`, `CMD_WIFI_STATUS 0x07`.)

**`wifi-status` reply format (firmware ≥ 3.1.0)** — the **MAC is always reported**
(handy for a DHCP reservation), placed *before* the SSID since the SSID can
contain spaces and the MAC can't:

```
connected <ip> <mac> <ssid>
offline <mac> (creds set: <ssid>)
no-creds <mac>
```

Older firmware (≤ 3.0.0) omits the MAC (`connected <ip> <ssid>` / `offline (creds
set: <ssid>)` / `no-creds`); `gems_t4.transport.wifi_status.parse_wifi_status`
parses both. WiFi admin also works over `--connect` once the Pico is on WiFi.

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
