# gems_t4 web front-end

Modern browser UI for the `gems_t4` API — **React + Vite + TypeScript + Tailwind**.
Talks to the Python API (`gems_t4 api`) over HTTP/WebSocket; the browser never
touches the hardware. No Electron; Node is a build-time tool only.

## Develop

Run the Python API and the Vite dev server in two terminals:

```bash
pip install -e ".[api]"      # once (FastAPI + uvicorn + websockets)
python -m gems_t4 api        # API on http://127.0.0.1:8080
```

```bash
cd frontend
npm install                  # once
npm run dev                  # Vite on http://localhost:5173 (proxies /api -> :8080)
```

Open the Vite URL; edits hot-reload. The proxy forwards `/api` (incl. the live
WebSocket) to the running API.

## Build (ship it)

```bash
cd frontend
npm run build                # outputs to ../gems_t4/app/web/static/
```

Then `gems_t4 api` serves the built app at `/` — open `http://127.0.0.1:8080`.
The built `static/` dir is gitignored (a build artifact); rebuild after changes.

## Features (complete — 2026-09-19)

Tabbed shell over the full API, browser-verified against the virtual ECU:

- **Connection** — virtual / BLE / USB / network, with adapter-firmware readout.
- **Live Data** — radial gauges streamed over the WebSocket + a Focus picker to
  watch one PID at a higher rate.
- **Fault Codes** — read + clear-all (with a confirm prompt); populates from the
  fault scenarios (e.g. misfire → P0303/P1303).
- **Actuators** — run tests; refusal messages surface verbatim (e.g. the fuel
  pump is refused while the engine is running).
- **Coding** — read every field; writable ones get an inline editor + gated Write
  (the backend enforces backup/verify/confirm); read-only fields are badged.
- **Immobiliser** — mobilised / learn-mode status. Security-Learn stays on the
  CLI (`gems_t4 kline secure --immobiliser-synch`) by design, not the browser.
- **Toolbox** — VIN read, VCI self-test (with latency), emulator scenario picker,
  and the EPROM map reference list.

## Layout

`src/api.ts` — typed client (all endpoints + the live WebSocket).
`src/components/` — `ConnectionPanel`, `LiveDashboard`, `Gauge`, `FaultCodes`,
`Actuators`, `Coding`, `Immobiliser`, `Toolbox`, `Card` (shared UI). `App.tsx`
is the tab shell; `ranges.ts` holds per-PID gauge scales.
