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
- **DTCs:** Mode 03 (stored/confirmed) + **Mode 07 (pending)** — on the bench a
  fresh fault is pending long before it matures to stored; engine-off it may
  NEVER become stored. ECU stays **silent when there are zero codes** (a
  TransportTimeout that means "no codes", not an error). Confirmed pending code
  from the bench (coolant/IAT sensors unplugged): **P1179** (manufacturer-specific).
- **Clearing DTCs (Mode 04) REBOOTS the ECU (confirmed 2026-09-01).** After a
  Mode 04 clear the GEMS ECU drops the K-line session and **goes unresponsive
  for ~1–2 minutes while it reboots its diagnostic subsystem**, then recovers on
  its own (cycling the ignition can force/speed it — it is NOT strictly
  required). You get `init failed (status 1)` on any command in the meantime. The tool handles it: `kline clear`
  does NOT re-read (it prints a "cycle the ignition" hint); the GUI clear drops
  the session (`Backend.disconnect()`) and prompts to cycle before re-reading;
  `Backend.read_*` now reconnect via `_ensure_connected()` so the post-clear
  re-read re-inits instead of crashing on a null client. Also: pending codes for
  a *still-present* fault (a disconnected sensor) reappear immediately —
  clearing a live fault is inherently temporary.
- **Real captured frames (used as test fixtures in `tests/test_kline.py`):**
  PID00 resp `48 6b e8 41 00 bf 9f f9 91 c4`; PID05 (coolant) resp
  `48 6b e8 41 05 00 e1` → 0x00 → −40 °C.
- **OBD-II surface mapped (Tier-1 probe, 2026-09-02; `probe1.py` in ~):**
  Mode 01 = **bank 1 only** (PID20 mask `00000001`, PID40 `00000000` — no
  PID21-60 data). Supported Mode-01 PIDs include the **V8 bank-2** ones now
  decoded (0x08/0x09 STFT/LTFT B2, 0x18/0x19 O2 B2S1/B2S2); 0x03 fuel-system
  status is a string enum (CLI-only candidate, not a gauge). **Mode 09
  (VIN/cal-id/ECU name) is NOT supported** — VIN lives in the BeCM, not GEMS →
  **no multi-frame reassembly needed** for the OBD-II layer. **Mode 02 (freeze
  frame)** supported (`M02 PID00` mask `7f980000`) but empty on the bench (DTC
  `0000` — no *confirmed* code). **Mode 06 (on-board monitor tests)** supported
  (`4600 fff8…`, TIDs 01-0D). Freeze-frame + Mode 06 populate on-car when a code
  matures — future features.

## Tier-2 probe (2026-09-02) + adversarial review — "OBD-II is the ceiling" was PREMATURE
What we tried: on the 0x33 OBD session, **no KWP2000 service** (`$3E/$10/$1A/$21/
$22/$27`) answered — neither with the OBD header (`68 6A F1`) NOR with KWP2000
framing (fmt `80`/`8L`/`C1` × targets `10/11/12/13/6A/33`). Total silence, not
even `7F`. Earlier 5-baud sweep: only 0x33 answered.
**Correct conclusion (after adversarial deep-research review):** blind SID
probing *on the established OBD session* is exhausted — DON'T repeat it — BUT the
"ceiling" is the *configuration's*, not the rig's. Those SIDs went out on top of
a live ISO 9141-2 OBD session, which is the emissions channel; a KWP2000
manufacturer channel is a SEPARATE session needing its OWN init, so silence is
expected. **Two concrete, cheap, NEVER-actually-tried doors remain (do these
before concluding anything):**
1. **A real KWP2000 StartCommunication fast-init.** Our firmware's "fast init" is
   only a wake pulse — it never sends the StartCommunication frame. Documented LR
   engine-ECU init (Rover MEMS 2J + Td5): fast-init pulse (25 ms low/25 ms high),
   then at 10400 8N1 send **`81 13 F7 81 0C`** (fmt `81`, **dest `13`** = LR
   engine ECU, **source `F7`** — we wrongly used `F1`, SID `81` StartComm),
   expect **`C1 KB1 KB2`**. If dest 13 silent, sweep dest `10/11/12/33/6A`. THEN
   `10 <session>` → `21 <lid>` / `22 <hi><lo>` for live data, `18`/`14` for DTCs.
2. **Un-ground the L-line.** P38 wires the engine ECU to BOTH OBD pin 7 (K) AND
   pin 15 (L); classic ISO 9141 (what T4/TestBook use) sends the 5-baud address
   on K **and** L simultaneously. L tied to ground blocks the manufacturer 5-baud
   channel while K-only ISO 9141-2 (0x33) still answers — EXACTLY the "only 0x33"
   symptom. Free C1017 pin 20 (drive via the L9637D L path / a GPIO) and re-sweep
   5-baud incl. 0x33/**0x16**, at 10400 AND **9600** (MEMS 1.9 = 0x16 @ 9600).
Mistakes found: source addr should be **F7** not F1; never sent SID `81` init;
L grounded during the sweep; omitted 0x16/9600. Only if #1 (real StartComm) and
#2 (live L-line) BOTH stay silent does the ceiling harden → then a real-T4/Nanocom
/Faultmate **K-line capture** (logic analyser on pins 7+15) is the only source of
the service-ID map (public record IS genuinely silent on GEMS SIDs — Revill is
MEMS3/K-series, Nanocom/Faultmate closed). P1179 confirmed = "Max Negative AMFR
Correction Fault" (air/fuel correction limit — matches unplugged sensors).
Sources: rovermems.com (MEMS 2J/1.9 init), SimonRafferty Td5 Arduino, ISO 9141
K+L 5-baud, rangerovers.pub P38 OBD pinout. (Probe scripts: `~/tier2.py`,
`~/tier2b.py`.)

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
