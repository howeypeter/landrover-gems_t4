# Release Notes: v0.0.5

**Tag:** v0.0.5
**Date:** 2026-07-11
**Branch:** `v0.0.5` (from `v0.0.4`)

## Summary

**v0.0.5 adds a TCP/network transport** so the GUI and CLI can reach the ECU
over the network as an alternative to USB — the groundwork for both a
Raspberry-Pi-at-the-car setup and a future WiFi Pico 2 W (identical laptop-side
code for both). The same host protocol the Pico speaks over USB now also runs
over a socket, served by a new `gems_t4 serve` command. Network links are
**read-only by default** (live data + fault codes); coding, actuator and
Security-Learn writes stay wired-only unless explicitly enabled. A GUI
**Configuration → VCI connection** screen lets you pick Virtual / USB COM port /
Network and remembers the choice.

The change shipped alongside a 6-agent adversarial review sweep; the 9 confirmed
findings are all fixed (see "Hardening").

## New Features

### TCP transport (`gems_t4/transport/tcp.py`)

`TcpTransport(host, port, *, allow_writes=False)` — a fourth `Transport`
implementation speaking the `0xA5/0x5A` host protocol over a socket. Default
port **9141**. `is_wireless = True`, so the write policy applies. IPv6
endpoints supported (`::1`, `[::1]:9141`). `parse_endpoint("HOST[:PORT]")`
helper.

### `gems_t4 serve` (`gems_t4/app/server.py`)

The network endpoint. Two modes:
- **Virtual (default):** `TcpFrameServer` answers from a local virtual ECU
  (`--scenario`, `--immobilised`, `--latency`), advancing the simulation by
  wall-clock time between exchanges (remote clients' local `tick()` no-ops).
- **Serial bridge (`--port COMx`):** raw byte passthrough between the TCP
  client and a USB Pico — the remote client talks straight to the firmware.

Binds `127.0.0.1:9141` by default; `--listen 0.0.0.0:9141` exposes it on the
LAN (or reach localhost through an SSH tunnel for auth + encryption). One
client at a time, mirroring one-tester-per-K-line.

### Wireless write gate (`gems_t4/protocol/client.py`)

`KwpClient.request` raises `WirelessWriteRefused` for write-capable services
over a wireless transport unless `allow_writes` is set. Blocked: `$27`
SecurityAccess, `$30` ActuatorControl, `$3B` coding writes, and the `$31`
Security-Learn routines. Allowed: all reads, `$14` DTC clear (part of
read→diagnose→clear), and `$31` routine `0x03` (immobiliser status — a pure
read).

### CLI flags

`--connect HOST[:PORT]` and `--allow-writes` on `live`, `dtc`, `actuator`,
`coding`, `immo`, `gui` (`--port` and `--connect` are mutually exclusive).
Table titles show the endpoint.

### GUI connection screen (`gems_t4/app/gui/screens/connection.py`)

System menu → **Configuration — VCI connection**: radio Virtual / USB COM port
/ Network (IP + port + allow-writes checkbox). Applies via
`Backend.apply_connection` (tests the link, rolls back on failure), persists to
`~/.gems_t4.json` (`GEMS_T4_CONFIG` overrides the path). The Toolbox LAN-card
self-test and its canon disclaimer are untouched. Launch precedence:
`gui --port/--connect` flags > saved config > virtual. GUI screens: 12 (was 11).

## Hardening (from the 2026-07-11 multi-agent review)

Six finder agents + adversarial verifiers reviewed the change before commit;
9 findings confirmed and fixed:

1. **Server DoS (critical):** a malformed KWP payload from any peer raised an
   uncaught `FramingError` that closed the listener and killed `gems_t4 serve`
   permanently. Now caught → `BUS_ERROR`; the server survives anything (a real
   Pico can't crash either).
2. **Immobiliser status wrongly blocked:** `$31` routine `0x03` is a pure read;
   carved out of the gate so `immo status --connect` works and the immobiliser
   GUI screen no longer raises on entry in read-only mode.
3. **SecurityAccess ungated:** `$27` (which mutates ECU security state and only
   ever precedes blocked writes) is now blocked, so a read-only link can't
   unlock the ECU before Security-Learn is refused mid-sequence. A refused
   learn now returns a clean `SecurityLearnResult` without touching the ECU.
4. **Failed connection stranded the tool:** `Backend.apply_connection` rolls
   back to the previous transport when a connection test fails.
5. **Transport desync:** `TcpTransport` drains a late reply after a timeout, so
   a single stall no longer makes every later exchange answer the previous
   request.
6. **GUI crash on dead endpoint:** live-data and immobiliser screens degrade
   to an error state instead of raising out of Qt handlers.
7. **Config type-safety:** `load_config` strictly validates every field — a
   JSON string `"false"` for `allow_writes` no longer truthy-enables writes; a
   corrupt config falls back to virtual instead of crashing the windowed exe.
8. **Serial bridge robustness:** survives serial errors (drops client, keeps
   listening), Ctrl+C works on an idle Windows bridge, testable via an injected
   fake serial + `stop_event`.
9. **Firmware parity + IPv6:** server INIT/SET_TIMING edge cases match the Pico
   firmware byte-for-byte; `parse_endpoint` handles IPv6 literals.

Startup-connection precedence was extracted into a testable
`apply_startup_connection` helper (previously uncovered).

## Documentation

- CLAUDE.md, README.md/README.html, INTERFACES.md, GUI_INTERFACES.md updated
  for the TCP transport, `serve`, the connection screen, and the write policy.
- The "Pico 2 W wireless mode" notes across CLAUDE.md, firmware/README.md and
  the sketch header now say the laptop side is **built**, only the Pico WiFi
  firmware remains.
- **Vehicle hardware correction:** the MikroE **ISO 9141 Click** is
  retired/unavailable in the US (agent-verified 2026-07-11). Docs that named it
  as the primary transceiver now specify the bare **ST L9637D** (same chip,
  breadboarded); a shopping list is in the project root.

## QA quick fixes (post-review, same branch)

A full requirements-vs-code QA sweep confirmed the product is healthy and found
11 unmet/partial spec items (recorded in the backlog). The four low-risk "quick
fixes" were applied here:

- **Live data 37 → 40 parameters** — added oil temperature (0x1E), catalyst
  temperature (0x1F), and cooling-fan state (0x28), the three categories the
  sweep found missing. Ids are now contiguous 0x01..0x28; the virtual ECU serves
  them automatically.
- **`dtc clear` now confirms** — the CLI asks "Clear all stored fault codes?
  [y/N]" before wiping codes (EOF/empty stdin declines, exit 1); `--yes`/`-y`
  skips it for scripts. (The GUI already prompted.)
- **Windows console text** — runtime CLI messages (actuator refusal,
  Security-Learn, coding, `serve` banners) now use an ASCII "-" instead of an
  em-dash that garbled on the default Windows codepage.
- **Doc accuracy** — the "every ECU write gated" line now states the three gates
  the coding path actually enforces (backup + verify + confirmation), rather
  than the seven once advertised.

The larger unmet items (service adjustments, VCSI connection-chain status, EAS
screens, message-centre text, injector-pulse test, full-screen kiosk,
immobilised-state coherence, server-side write enforcement) remain open in the
backlog as scope decisions.

## Tests

- `tests/`: **153 passed** (was 141) — new `test_tcp_transport.py` (full stack
  over a real localhost socket, the write gate on/off, hostile-input survival,
  sequential clients, timeout resync, the serial bridge via a fake serial) and
  `test_gui_connection.py` (connection screen, rollback, startup precedence,
  config validation).
- `tests_regression/`: **235 passed** — updated for the 12-screen / 6-menu-item
  contract and the 40-parameter live-data count; new coverage for the
  `dtc clear` confirmation; the version test asserts `__version__` /
  `--version` / `pyproject.toml` stay in lockstep.
- No test requires real hardware or a real serial port.
