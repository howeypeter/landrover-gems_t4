---
name: t4-research-sources
description: "Where the TestBook T4 facts came from — Revill's MEMS3 reverse-engineering page, the saved mg-rover.org thread PDF, and which sites block automated fetching"
metadata: 
  node_type: memory
  type: reference
  originSessionId: 8b433210-a332-4063-b996-395f1cfb9374
---

Sources behind the T4 emulator spec in [[testbook-t4-emulator]]:

- **Andrew Revill — MEMS3 TestBook T4 support**
  (https://andrewrevill.co.uk/MEMS3TestBookT4Support.htm): protocol-level
  detail — service $61 live-data records / $7f unsupported, ~108 measures,
  refresh-rate trade-off (~20/s for one measure → ~1 per 2 s for all),
  actuator-test safety interlocks, service adjustments (ignition −6°…+3°),
  ZCS/immobiliser functions. Fetches fine.
- **"Rover T4" thread, mg-rover.org** — user saved it as
  `C:\Users\howey\Downloads\Rover T4 _ MG-Rover.org Forums.pdf` (text extracts
  cleanly with pypdf). Key facts: RDS takes over the laptop entirely; RDS 4.04
  vs 5.06 "T4 Lite" (adds LAN-vs-USB config option); VCSI interface chain to
  J1962, ISO 9141; Ediabas dependency; LAN self-test "present"/"not present"
  wording; T4 Mobile is J2534 but with unique J1962 firmware.
- **Gotcha:** mg-rover.org and rangerovers.net return 402 (Tollbit bot
  paywall) to WebFetch — don't retry; ask the user for a saved copy instead.
- No good RDS screenshots exist anywhere — fidelity target is era-faithful,
  not pixel-accurate. User may supply photos of real units to improve it.
