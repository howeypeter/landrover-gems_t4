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

## Use from Python

```python
from gems_t4.transport.pico import PicoAdapterTransport
from gems_t4.protocol.client import KwpClient

client = KwpClient(PicoAdapterTransport("COM5"))
client.connect(mode="slow")   # 5-baud init on the Pico
```

Or from the CLI: `gems_t4 live --port COM5`.
