---
name: qa-unmet-requirements
description: QA sweep 2026-07-11 — spec requirements the product doesn't yet meet (features never built, or built partway); NOT the future-research backlog
metadata:
  type: project
---

**Logged 2026-07-11 from a full requirements-vs-code QA sweep (11-dimension
agent fan-out + adversarial verification). The product is healthy — 153 tests +
234 regression all pass, every core workflow works — but these SPEC requirements
(design pillars / locked-in decisions / v1 scope) are unmet or partial.** These
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
6. **"Every ECU write gated" overstated.** CLAUDE.md lists 7 gates (backup,
   verify, checksum, security-access, precondition, dry-run, confirmation).
   Coding-write path enforces 3 (backup, verify, confirm — real, non-bypassable).
   MISSING: security-access ($27) not required for a $3B coding write; no
   precondition interlocks; no dry-run; "checksum" is frame-level only. (The
   immobiliser Security-Learn write DOES enforce security + sequence.) Fix: build
   the missing gates OR correct the doc to "three gates."
7. **Full-screen kiosk on boot** — pillar 1. Runs as a normal 800×600 titled
   window; no `showFullScreen`/frameless code. Win98 look present, chrome not
   suppressed.
8. **Live-data breadth** — aim was ~40–60 (real T4 ~108); actual 37. Missing
   named readings: oil temperature, catalyst state, cooling-fan operation
   (A/C request present, fan absent).
9. **Immobilised not coherent across screens** — immo status says ENGINE
   IMMOBILISED but sim keeps `engine_running=True` / rpm idling; live data would
   show a running engine. `virtual_ecu` never gates rpm/engine_running on
   `_mobilised`.
10. **CLI `dtc clear` has no confirmation prompt** — v1 flow wanted clears
    confirmed. GUI prompts; CLI clears immediately.
11. **Em-dash renders as "�" on default Windows console** — literal "—" in
    `gems/actuators.py` refusal message (+ similar). Use ASCII "-" or force UTF-8
    console. Cosmetic, on-target-platform.

## C. Security note (by design; know it)
The "network is read-only" write gate is enforced only client-side (in
`KwpClient`), NOT by the `serve` bridge/firmware ("dumb pipe" design). Safe while
`serve` stays on localhost / behind an SSH tunnel (documented). If ever run
`serve --port COMx --listen 0.0.0.0` against a real car, a misbehaving client
could still send writes — wants server-side enforcement before real
over-the-network use. See [[implementation-status]] (TCP transport).

## Not defects (excluded from the above, per QA scope)
The 5 future-research backlog items, guided fault-tree wizards, on-car hardware
validation, windowed-exe icon/version resources, Td5/MEMS3 reflash demo. The
v0.0.5 TCP transport + host-protocol fidelity + wireless write-gate logic all
verified MET (this file is pre-existing gaps, none introduced by v0.0.5).

Related: [[implementation-status]], [[phase5-programming]],
[[testbook-t4-emulator]].
