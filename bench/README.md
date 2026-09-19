# bench/ — one-off GEMS bench diagnostic scripts

Throwaway R&D scripts used to reverse-engineer and probe a real GEMS ECU on the
bench (Pico 2 W + L9637D adapter, over USB or BLE). They are **not** part of the
`gems_t4` package — proven capability graduates into `gems_t4/` and its tests.
These stay here so the experiments are referenceable and re-runnable.

## Running

Each script talks to the ECU via the installed `gems_t4` package, so run from an
env where `pip install -e .` has been done (the repo `.venv`). Transport is
auto-detected: a plugged USB Pico (VID 0x2E8A) is used if present, else BLE
`gems-pico`. Override with env vars:

```powershell
python bench\live_diff.py            # auto: USB if present, else BLE
$env:GEMS_PORT="COM4"; python bench\live_diff.py   # force USB port
$env:GEMS_BLE="gems-pico"; python bench\live_diff.py  # force/name BLE
```

Captured output (`*.log`, `*.csv`) is gitignored — regenerable.

## Safety (see CLAUDE.md / memory/real-gems-protocol.md)

- **NEVER put 12V on a sensor input** — they are 0-5V. Use the Pico 5V (VBUS
  pin 40) or ground for signal injection.
- The old Intel 87C196KC is slow — **pace requests and back off on silence**,
  don't hammer it (the probes already do: `PACE_S` + `BACKOFF_S`).
- `$A3` mutates the ECU (immobiliser-synch is `A300622588`) — never poke it
  blind. Reads (`22`/`21`/`1A`) are safe.

## What's here

Curated down to the reusable tools; superseded one-shot probes were removed once
their findings landed in `memory/real-gems-protocol.md`.

- **0xDA channel / security** — `da6_unlock` (standalone `$27` unlock check),
  `da7_read` (unlock + authorized coding reads: PROM/config/adaptive),
  `da8_secure_probe` (verify `0x3C` memory-read format + discover the
  coding-WRITE path), `da9_sweep` (authorized read-sweep of the whole channel).
  The `$27` seed->key is cracked (`key=(seed*16723)%65536`) and shipped in
  `gems_t4`.
- **Live data** — `live_sweep` ($21 00..FF sweep, LIVE vs static). The guided
  sensor-ID wizard `live_diff` also lives here, with three modes: `map` (analog
  sensors - pot sweep min/mid/max, diff to find which $21 id moves), `switch`
  (two-state inputs like A/C/heated-screen - float -> ground -> float, flags the
  id that toggles and returns; do NOT inject voltage), and `watch <id>` (poll
  one id live to confirm a candidate).
- **Actuators / outputs** — `actuator_hunt` (interactive `send <hex>` tester),
  `actuator_test` (guided actuator/fuel-pump bench tester). ($31 was ruled out
  as the output-control command.)
- **Immobiliser block** — `immo_align` (align two page-0x18 dumps + classify),
  `immo_xref` (content cross-ref), `da10_immo` (confirm/map the block, records
  A4-A8). Decoding via same-PROM reference-ECU diff.
- **Health check** — `ecu_ping` (is the ECU responding?): pings the adapter,
  then tries the 5-baud init, and tells you WHICH layer is broken -
  adapter/link vs ECU-not-answering vs software - so a failure isn't a guess.
- **Pins / init / transport** — `pin_test` (per-pin G/V id),
  `pentest_scan` (full raw 256-address scan), `ble_scan` (dump the gems-pico
  BLE services).

## `$21` live-data map (RED plug C1017) — in progress

Built by isolated 0-5V pot injection on each RED sensor pin, watched over the
0xDA `$21` channel (L-line tied). Analog: `map` to find, `watch <id>` to
confirm. Switch inputs (A/C p28/29, heated screen p21): `switch` (ground vs
float), not the pot. Full
detail + method in `memory/real-gems-protocol.md`.

| ✓ | Pin | Sensor | `$21` id |
|---|----:|--------|----------|
| ✅ | 14 | Coolant temp | `0x00` (raw) |
| ✅ | 13 | Intake air temp | `0x01` (raw) |
| ✅ | 35 | Fuel temp | `0x15` (raw) |
| ✅ | 15 | Throttle | `0x0F` (raw) + `0x10` (scaled) |
| ✅ | 16 | MAF | `0x11` (scaled) |
| ✅ | 30 | Fuel pressure | `0x05` (scaled) |
| ✅ | 7 | Fuel level | `0x02` |
| ✅ | 34 | Left O2 | `0x18` (inject 0-1V only) |
| ✅ | 33 | Right O2 | `0x19` |
| ✅ | 17 | Left O2 post-cat | `0x1A` |
| ✅ | 8 | Right O2 post-cat | `0x1B` (needed >1.5V to swing) |
| — | 32 | (O2 heater — output, no voltage id) | n/a |
| ✅ | 28 | A/C evap/pressure switch | `0x06` (raw FF/00) + `0x22` **bit13** |
| ✅ | 29 | A/C request switch | `0x22` **bit6** only (no dedicated raw id) |
| ✅ | 21 | Heated front screen | `0x16` (raw FF/00) + `0x22` **bit14** (`0x0F` = noise, not it) |
| ⛔ | 10/11/12 | Knock (AC piezo) | needs square-wave injector |
| ⛔ | 27 | Vehicle speed (output/pulse) | needs square-wave injector |

**Blocks:** O2 voltages `0x18-0x1B`; scaled measures throttle `0x10`/MAF `0x11`
/fuel-press `0x05`; raw-ADC temps `0x00`/`0x01`/`0x15`. **Switch-status bitmap
`0x22`:** a 16-bit pull-up switch word (float=`7FC0`, all open); grounding a
switch **clears its bit**: pin 28→bit13 (`5FC0`), pin 21→bit14 (`3FC0`), pin
29→bit6 (`7F80`). RAVE-confirmed (see `docs/rave-cross-reference.md`).
**Noise (ignore):** `0x2B` and idle O2 `0x19-0x1B` jitter (±1 last nibble) appear
in EVERY run - the real id is the one with a big monotonic swing.
