# gems_t4

A **TestBook-T4-style diagnostic and (emulated) programming tool** for the
**Lucas/SAGEM GEMS V8** engine ECU fitted to the **P38 Range Rover 4.0/4.6** and
**Discovery 1 V8i** (1995–early 1999).

It speaks the GEMS K-line (KWP2000 / ISO-14230) dialect and ships with a built-in
**virtual ECU**, so the whole thing runs on a laptop with **no car and no adapter**.
When you're ready for real hardware, the same code drives a Raspberry Pi Pico
K-line adapter over USB.

> 📄 **Full, styled documentation lives in [`README.html`](README.html)** — open it
> in a browser (best viewed locally; GitHub shows `.html` as source, not rendered).
> This Markdown file is the short version for the GitHub landing page.

> **Scope note.** GEMS engine maps live in socketed UV-EPROMs and are **not**
> reflashable over the K-line — that capability never existed for GEMS. This tool
> does the real over-the-wire work (fault codes, live data, actuator tests, coding,
> immobiliser Security-Learn) and treats map "reflash" as an emulated chip-swap
> lookalike. Background dossier is in `memory/research/`.

## Install & run

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # Windows; on macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt     # CLI only
# ...or, for the GUI too:  pip install -e ".[gui]"
python -m gems_t4 scenarios
```

Use the venv's Python (activate once, or prefix with `.venv\Scripts\`). PySide6
(the GUI) is intentionally kept out of `requirements.txt` — it's a large optional
dependency; install it via the `[gui]` extra.

## What it does

```bash
python -m gems_t4 live --scenario coolant_sensor   # live sensor data
python -m gems_t4 dtc read --scenario misfire_cyl3 # read/clear fault codes
python -m gems_t4 actuator fuel_pump --state on    # actuator tests (with refusals)
python -m gems_t4 coding read                      # ECU coding block (gated writes)
python -m gems_t4 immo learn --immobilised         # immobiliser Security-Learn re-sync
python -m gems_t4 gui                               # the Win98 kiosk GUI (needs [gui])
```

| Area | What |
|---|---|
| **Fault codes** | Read / clear GEMS DTCs (P0118, P0303, P1185, …) |
| **Live data** | ~24 `$61` measures with the authentic gauge-count → refresh-rate trade-off |
| **Actuator tests** | MIL, O2 heater, fuel pump, etc. — with the "engine running" refusals |
| **Coding** | Gated read/edit/write (backup + verify + confirm) of VIN, dealer id, 4.0/4.6, … |
| **Security-Learn** | The one genuine GEMS K-line write — recover "ENGINE IMMOBILISED" |
| **Maps** | Read-only 16×16 fuel/ignition viewer (chip-swap lookalike; no K-line reflash) |
| **GUI** | PySide6 Win98 kiosk over the same engine as the CLI |

Four fault scenarios (`healthy`, `coolant_sensor`, `misfire_cyl3`, `lambda_heater`)
produce coherent symptoms across every screen.

## Layout

```
gems_t4/
  transport/   the only I/O layer — virtual ECU, Pico adapter (USB), FTDI stub
  protocol/    KWP2000 framing, init, services, security, the KwpClient
  gems/        GEMS meaning — DTCs, live data, actuators, immobiliser, maps, virtual ECU
  app/         Backend facade + Rich CLI + gui/ (PySide6 Win98 kiosk)
firmware/      Pico sketch + USB-CDC host-protocol spec + wiring guide
tests/         pytest suite (runs headless, no hardware)
```

The load-bearing seam is `KwpClient(transport)`: it takes a real serial transport
or the in-memory `VirtualTransport`, so the whole stack is testable off-car.

## Development

```bash
pytest        # 99 passed with the [gui] extra; 65 passed + 8 skipped without PySide6
```

Build contracts: [`INTERFACES.md`](INTERFACES.md) (core) and
[`GUI_INTERFACES.md`](GUI_INTERFACES.md) (screens) pin the wire format, service
map, and every module's public API.

## Hardware (optional)

A Raspberry Pi **Pico or Pico 2** + an ISO 9141 Click (L9637D) transceiver over USB
— see [`firmware/README.md`](firmware/README.md) for the parts list, wiring, and
flashing. The Pico owns the K-line timing; the PC talks to it over a simple USB
protocol.

## Status

Phases 1–5 complete (virtual ECU, full protocol stack, CLI, PySide6 GUI, gated
programming/coding/immobiliser/maps). Pending: on-car validation of the Pico
adapter, and Phase-6 polish (real gauge widgets, PyInstaller build). See the "Tech
stack" / "Build status" sections of [`CLAUDE.md`](CLAUDE.md) for the roadmap.
