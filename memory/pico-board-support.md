---
name: pico-board-support
description: Which Pico boards the K-line adapter supports now, and the planned (not yet built) Pico 2 W wireless mode
metadata:
  type: project
---

**Decided 2026-07-07.** Firmware supports **Raspberry Pi Pico and Pico 2**
(both wired over USB) — no source changes between them, since
`firmware/pico_kline/pico_kline.ino` only uses the portable Arduino API
(`Serial`, `Serial1`, `pinMode`, `digitalWrite`, `delay`, `millis`), which
`arduino-pico` implements identically on RP2040 (Pico) and RP2350 (Pico 2).
Only the build's `--fqbn` target differs (`rpipico` vs `rpipico2`) — see
`firmware/README.md` "Build & flash".

**Pico W / Pico 2 W are NOT yet supported.** A read-only wireless (WiFi) mode
was scoped but explicitly deferred — user chose to land wired Pico/Pico 2
support first and track wireless as future work rather than build both at once.

## Planned Pico 2 W wireless mode (tracked in CLAUDE.md, not started)

Design already thought through, ready to pick up later:
- **WiFi/TCP, not BLE.** The existing host protocol (`firmware/HOST_PROTOCOL.md`)
  is a length-prefixed byte stream that maps directly onto a raw TCP socket.
  BLE's small MTU (~20-244 bytes vs our 255-byte frames) would need chunking
  for no benefit, and BLE was already ruled out for ECU work generally (user:
  "BLE is not a good way to handle ECU/ECM hacking").
- **Read-only by policy, enforced in Python, not firmware.** Firmware stays a
  "dumb timed pipe" (per its own design principle) — it won't parse KWP
  semantics either way. The block would live in `KwpClient`: check a new
  `Transport.is_wireless` flag before sending anything that looks like a write
  (SIDs 0x14 clear-DTC, 0x27 security-access, 0x30 actuator, 0x3B write-coding,
  plus 0x10 StartDiagnosticSession with a non-default/programming session).
  Reads (0x21 live data, 0x18 DTCs, 0x3E tester-present, 0x1A id, default
  session) stay unrestricted over WiFi.
- Rough shape when built: refactor firmware I/O to work over any `Stream` (so
  the same handler code services both `Serial` and a `WiFiClient`), add a
  compile-time `GEMS_ENABLE_WIFI` toggle (default off) + `wifi_config.h`
  (gitignored) for credentials, new `gems_t4/transport/pico_wifi.py`
  (`PicoWifiTransport`, `is_wireless = True`), a shared `pico_protocol.py` for
  the framing code so wired/wireless don't duplicate it, and a `--wifi
  HOST:PORT` CLI flag.
- Estimated size when picked up: ~400-500 lines across ~13 files (firmware +
  new transport + safety gate + CLI + tests + docs). Not a redesign — additive,
  doesn't touch the existing wired path or any passing test.

Related: [[research-hardware-interfaces]], [[tech-stack-decision]],
[[implementation-status]].
