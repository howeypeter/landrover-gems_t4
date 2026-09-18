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

## Phase 1 (current)

Connection panel (virtual / BLE / USB / network) + a live-data dashboard with
radial gauges streamed over the WebSocket, and a Focus picker to watch one PID.
Fault codes, actuators, coding, immobiliser are backlogged (Phase 2/3).
