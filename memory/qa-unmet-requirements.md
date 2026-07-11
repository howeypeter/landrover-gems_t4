---
name: qa-unmet-requirements
description: QA sweep 2026-07-11 — spec requirements the product doesn't yet meet (features never built, or built partway); NOT the future-research backlog
metadata:
  type: project
---

**Logged 2026-07-11 from a full requirements-vs-code QA sweep (11-dimension
agent fan-out + adversarial verification). The product is healthy — 153 tests +
235 regression all pass, every core workflow works — but these SPEC requirements
(design pillars / locked-in decisions / v1 scope) are unmet or partial.**

**⚠️ UPDATE 2026-07-11: the four "quick fixes" (#6, #8, #10, #11) are now DONE.
Items #1-5, #7, #9 and the security note (C) remain open.** These
are distinct from the future-research backlog ([[eprom-programmability-question]]
etc.): they are things already promised in CLAUDE.md that the code doesn't do.
Full plain-English list is in CLAUDE.md "Backlog / QA-found unmet requirements".

## A. Promised but never built
1. **Service adjustments** — ignition timing (−6°…+3°) + idle-speed offset write
   path. Pillar 6 / v1 scope. Only read-only "ignition advance" live param
   exists; no adjustment service/screen/command.
2. **Connection-chain link status** — model laptop→VCSI→J1962 lead→ECU as
   separate links with per-link state + authentic "VCI not responding" when one
   is "unplugged." LOCKED-IN spec decision. Reality: `VirtualTransport` is one
   binary `_open` flag; Toolbox VCI check is a hardcoded "present" string.
3. **EAS (air-suspension) height/calibration screens** — P38 party piece
   (pillar 7). No EAS code at all.
4. **Message-centre text mirroring active faults** — pillar 7. Only the
   immobiliser screen shows one status line; coolant/misfire/lambda produce no
   message text; scenarios carry no message field.
5. **Injector "brief pulse only" actuator** — spec safety behaviour (injectors
   pulsed, never continuous). No injector actuator test exists; injector PW is a
   read-only live param only.

## B. Built but incomplete / docs oversell
6. **✓ DONE (doc). "Every ECU write gated" overstated.** CLAUDE.md listed 7
   gates; coding-write path enforces 3 (backup, verify, confirm — real,
   non-bypassable). MISSING: security-access ($27) on $3B coding writes;
   precondition interlocks; dry-run; "checksum" frame-level only. (Immobiliser
   Security-Learn DOES enforce security + sequence.) **Fixed by correcting the
   CLAUDE.md Tech-stack line to state the three real gates; building the missing
   four remains an optional feature.**
7. **Full-screen kiosk on boot** — pillar 1. Runs as a normal 800×600 titled
   window; no `showFullScreen`/frameless code. Win98 look present, chrome not
   suppressed. **(OPEN — feature decision.)**
8. **✓ DONE. Live-data breadth** — aim was ~40–60 (real T4 ~108); was 37, **now
   40**: added oil temperature (0x1E), catalyst temperature (0x1F), cooling-fan
   state (0x28) in `gems/livedata.py`. Ids now contiguous 0x01..0x28. Virtual
   ECU serves them automatically (state built from param nominals). Tests updated
   37→40.
9. **Immobilised not coherent across screens** — immo status says ENGINE
   IMMOBILISED but sim keeps `engine_running=True` / rpm idling; live data would
   show a running engine. `virtual_ecu` never gates rpm/engine_running on
   `_mobilised`. **(OPEN — behaviour fix.)**
10. **✓ DONE. CLI `dtc clear` now prompts** — "Clear all stored fault codes?
    [y/N]"; EOF/empty stdin ⇒ declined (exit 1); `--yes`/`-y` skips for scripts.
    Shared `_prompt_yes_no` helper in `cli.py` (coding-write confirm reuses it).
11. **✓ DONE. Em-dash on Windows console** — runtime CLI-printed messages
    (actuator refusal `actuators.py`, Security-Learn `immobiliser.py`, coding
    `programming.py`, serve banners `cli.py`) now use ASCII "-". GUI QLabels keep
    "—" (Qt renders Unicode fine).

## C. Security note (by design; know it)
The "network is read-only" write gate is enforced only client-side (in
`KwpClient`), NOT by the `serve` bridge/firmware ("dumb pipe" design). Safe while
`serve` stays on localhost / behind an SSH tunnel (documented). If ever run
`serve --port COMx --listen 0.0.0.0` against a real car, a misbehaving client
could still send writes — wants server-side enforcement before real
over-the-network use. See [[implementation-status]] (TCP transport).

## Suggested triage
- Quick fixes: ✓ ALL DONE 2026-07-11 (#6 doc, #8 params 37→40, #10 dtc-clear
  confirm, #11 em-dash→ASCII). Tests 153 + 235 green.
- Real feature decisions (keep or drop): #1 service adjustments, #2 VCSI
  connection-chain status, #3 EAS screens, #4 message-centre text, #5 injector
  test, #7 full-screen kiosk.
- Behaviour fix: #9 gate rpm/engine_running on the immobilised flag.
- Security hardening (before any non-localhost `serve`): enforce the write
  policy server-side in the bridge, not just client-side.

## Not defects (excluded from the above, per QA scope)
The 5 future-research backlog items, guided fault-tree wizards, on-car hardware
validation, windowed-exe icon/version resources, Td5/MEMS3 reflash demo. The
v0.0.5 TCP transport + host-protocol fidelity + wireless write-gate logic all
verified MET (this file is pre-existing gaps, none introduced by v0.0.5).

Related: [[implementation-status]], [[phase5-programming]],
[[testbook-t4-emulator]].
