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
  sensor-ID wizard `live_diff` (snapshot, inject 5V/ground on a pin, diff to
  find which $21 id is that sensor) also lives here.
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
