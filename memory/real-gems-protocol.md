---
name: real-gems-protocol
description: The ACTUAL wire protocol a real NAS GEMS ECU speaks — confirmed on physical hardware 2026-08. Ground truth, supersedes the stylized guess for real-ECU work.
metadata:
  type: project
---

**FIRST HARDWARE LIGHT — 2026-08-30/31.** The homemade Pico + L9637D adapter
talked to a **physical P38 GEMS ECU** for the first time. This is the real,
reverse-engineered protocol — use it (not the stylized KWP format in
`protocol/framing.py`) for anything talking to a real ECU. Implemented in
**`gems_t4/protocol/kline.py`** and exposed as **`gems_t4 kline live|dtc|monitor
--port COMx`**.

## The confirmed protocol (NAS GEMS = OBD-II ISO 9141-2)
- **K-line pin:** GEMS ECU **C1017 (36-way red) pin 23**. Pin 20 is the **L-line**
  (the other DLC pin) — both idle high through the pull-up, so idle voltage does
  NOT tell them apart; only which one *answers* an init does. (C1033 18-way black
  = power/ground: pin 7 main +12, pin 8 ignition +12, grounds 5/9/10/16.)
- **Init:** 5-baud **slow** init, address **0x33** (the tool's old default 0x10
  was a wrong placeholder). ECU replies `0x55` sync + keybytes **0x08 0x08**
  (standard ISO 9141-2).
- **Keybyte handshake (was the killer bug):** after KB2 the tester MUST send the
  **inverted second keybyte** (`KB2 ^ 0xFF`) back within the **25–50 ms W4
  window**, then read the ECU's inverted-address reply. Without it the ECU hands
  over keybytes but never enters the initialised state → ignores every request.
  Must be in the **Pico firmware** (W4 is far too tight for a USB/WiFi round-trip).
- **Request frame:** `68 6A F1` + `<service>` + `<data…>` + 1-byte **sum**
  checksum. (NOT the tool's stylized `80 target source len … cksum`.)
- **Response frame:** `48 6B E8` + `<service+0x40>` + `<data…>` + checksum.
  ECU source address = **E8**.
- **Live data:** Mode 01 works (coolant, RPM, timing, O2, fuel trims, MAF,
  throttle…). Mode 01 **PID 00** = supported-PID bitmask (auto-detect PIDs).
- **DTCs:** Mode 03. ECU stays **silent when there are zero codes** (a
  TransportTimeout that means "no codes", not an error).
- **Real captured frames (used as test fixtures in `tests/test_kline.py`):**
  PID00 resp `48 6b e8 41 00 bf 9f f9 91 c4`; PID05 (coolant) resp
  `48 6b e8 41 05 00 e1` → 0x00 → −40 °C.

## NOT yet mapped (the frontier)
The fuller **proprietary GEMS/T4 diagnostics** — the ~108 T4 live measures,
actuator drives, coding, immobiliser — ride the **same `68 6A F1` envelope**
but use manufacturer service bytes still to be discovered. `KlineClient.raw_service`
is the hook to probe/add them at the bench. What's proven is only the **OBD-II
emissions subset**; the proprietary stuff (esp. the immobiliser) is still
experimental.

## Two bring-up bugs found & fixed (both committed)
1. **Host serial timeout too short** (`transport/pico.py`): default was 2.0 s but
   the 5-baud slow init blocks ~2.3–3.3 s → every init raised "no response from
   Pico" on real HW. Bumped to **6.0 s**. (fake serial in tests hid it.)
2. **Missing ISO 9141 keybyte handshake** (`firmware/pico_kline/pico_kline.ino`
   `slowInit`): added the inverted-KB2 / W4 step (see above). This is what turned
   "init OK but all data times out" into working comms.

## How to run it (real ECU)
**CLI:** `gems_t4 kline live --port COM4` (one-shot table) / `kline dtc` /
`kline monitor` (continuous). Real-ECU only — no `--fake`; `--connect HOST` for
a TCP bridge. `KlineClient(transport)` for code.
**GUI (works on real hardware as of e51c549):** `gems_t4 gui --port COM4` drives
the Win98 kiosk from the REAL ECU. The Backend uses `KlineClient` when the
connection kind is **USB** (seam: `Backend._use_kline`, set by
`set_connection("usb")`; `Backend.on_real_ecu` property), mapping OBD live data
+ DTCs onto the shared `Measure`/`Dtc` types. The live-data screen discovers the
ECU's supported OBD PIDs and builds gauges from them (`gauge_specs.obd_spec_for`).
Proprietary screens (actuator/coding/immobiliser/security) raise
`RealEcuUnsupported` and refuse gracefully (OBD-II subset only). Virtual +
network (serve) keep the KWP-stylized stack.
Commits: firmware `fca1ab9`, timeout `640034f`, kline module+CLI `4bfa738`,
manual `6bd4ad5`, rename obd→kline `9f82b6b`, GUI real-ECU `e51c549`. Tests:
`tests/test_kline.py` (decoders vs captured bytes), `tests/test_backend_kline.py`
+ `tests/test_gui_real_ecu.py` (backend/GUI real-ECU paths).

## Wireless/web forward note (from the same session)
Architecture is already latency-safe: all K-line timing is on the Pico, host↔Pico
is request/response tolerating any latency (the W4 fix PROVES the principle). The
one wireless item is **session keep-alive** — the ECU drops the session if idle
too long (KWP TesterPresent timeout ~1–5 s); over WiFi/web with idle gaps it'll
drop → do keep-alive **in firmware** (Pico auto-sends TesterPresent), same
timing-on-the-Pico principle. Live-data over WiFi: batch multiple PIDs per Pico
command to amortize RTT (UX, not correctness). Not built yet.

Related: [[implementation-status]], [[repo-git-state]], [[pico-board-support]],
[[gems-p38-focus]].
