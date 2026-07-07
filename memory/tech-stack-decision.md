---
name: tech-stack-decision
description: Decision — build the GEMS tool in Python + PySide6 for Windows desktop only, wired serial, no BLE/mobile
metadata:
  type: project
---

**FINAL decision (2026-07-06): Python + PySide6, Windows desktop only.**

## Scope
- **Windows laptop only.** No iPhone, no Android.
- **Wired USB serial only. No BLE** — the user judged BLE a poor fit for ECU
  hacking (latency, reconnect flakiness, pairing hassle); a wired link is more
  reliable/lower-latency for fast deterministic round-trips at a live ECU.
- Hacking is done on the laptop plugged into the car.

## Language & GUI
- **Python** — best environment for interactive reverse-engineering of an
  undocumented protocol over serial (REPL, pyserial, fast iteration); matches the
  research architecture in [[research-python-architecture]].
- **PySide6 (Qt)** for the GUI — single-language, custom-painted beveled widgets +
  QSS for the 800×600 Win98 kiosk, QPainter live gauges, fullscreen kiosk, ships
  to a Windows .exe via PyInstaller. **Rich** for the CLI/hacking phase.
- Alternative weighed for GUI: pywebview + `98.css` (pixel-authentic Win98 chrome
  via HTML/CSS) — rejected to stay single-language and keep realtime gauges snappy.

## Decision arc (why the flip-flops)
1. Started "Python CLI first."
2. Switched to **Flutter/Dart** when cross-platform incl. **iPhone** was a hard
   requirement (Python can't ship on iOS).
3. User then dropped **iPhone** and **BLE**, targeting a **Windows laptop** →
   removed the only reason to leave Python → **reverted to Python + PySide6**.

## Alternatives considered (and why not)
- **Flutter/Dart** — only justified by iPhone/Android; both now out of scope.
- **React Native** — weak desktop story (RN-Windows lags, no Linux), no
  cross-platform desktop BLE, JS weaker at binary work. Moot now anyway.
- **Rust core + thin UI** — most durable/reusable engine but higher effort;
  overkill with mobile off the table.

## How to apply
- Pure-Python `gems_core` (protocol + GEMS services + virtual ECU), UI/IO-free.
- `transport/` = Virtual + PicoAdapter (pyserial over USB-CDC) + FTDI-cable
  fallback; **no BLE**.
- `app/` = Rich CLI now, PySide6 GUI later — both thin over `gems_core`.

## Committed hardware plan (2026-07-06): Pico smart adapter
- **Raspberry Pi Pico + MikroE ISO 9141 Click (L9637D) over USB** is the primary
  rig and canonical transport — the modern VCSI equivalent. FTDI KKL cable is a
  quick-start/read fallback.
- **Role split — Pico owns timing, Python owns logic.** Pico firmware (Arduino
  C++, in `firmware/`) does init (5-baud/fast), P1–P4 byte timing, half-duplex
  echo cancellation, and frame-by-inter-byte-timeout; it exposes a simple
  length-prefixed **host protocol over USB-CDC**. All KWP framing, checksums,
  service IDs, and GEMS semantics stay in Python (keeps protocol R&D fast; no
  reflash to change behaviour; reliable timing for writes immune to USB jitter).
- The host protocol is the same swappable seam as the virtual transport —
  `KwpClient` can't tell Virtual from Pico. RP2040 PIO can clock 10.4 kbaud +
  5-baud init precisely. Refs: muki01/OBD2_KLine_Library, iwanders/OBD9141.
- See [[research-hardware-interfaces]] (Tier B smart front-end — now committed).

Full detail in CLAUDE.md "Tech stack — Python + PySide6". Related:
[[research-synthesis]], [[research-python-architecture]], [[workflow-directives]].
