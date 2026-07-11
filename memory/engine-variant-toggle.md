---
name: engine-variant-toggle
description: Open backlog item — GEMS ECU may hold both 4.0L and 4.6L calibrations with a selectable active variant (ECUs get cross-fitted)
metadata:
  type: project
---

**Open backlog item, logged 2026-07-11. Research before building the real
feature** — recorded at the user's request.

## The idea
A single GEMS engine ECU may carry the calibration for *both* the 4.0 L and
4.6 L Rover V8, with which one is **active being selectable**. The real-world
reason: a 4.6 ECU can end up fitted to a 4.0 engine and vice versa (repairs,
salvage, swaps), so the ECU has to be told which displacement it's actually
driving. The tool should let the user **toggle** the active variant.

## What already exists (partial)
`gems/programming.py` already defines a writable coding field:
`CodingField("engine", 0x83, "Engine (4.0/4.6 select)", True)` — so the
read/edit/write *mechanism* is stubbed through the gated coding path (CLI
`coding read|write`, GUI coding screen). It's currently just an opaque coding
byte, not a modelled feature.

## Backlog work (do not start until picked up)
- Research the real capability: does one ECU genuinely hold both maps, or is
  this a chip/calibration difference? What byte/coding actually flips the
  active variant on GEMS?
- What does the choice affect downstream — fuel/ignition maps, rev limit,
  injector sizing, drive-by-wire, live-data expectations, actuator behaviour?
- Once known, promote the opaque `0x83` coding byte into a first-class
  "engine variant" toggle that also drives the coherent virtual-ECU behaviour
  differences (so the fake ECU responds like a 4.0 vs a 4.6 across screens),
  not just a stored value.

Recorded in CLAUDE.md under "Backlog / open research items". Related:
[[implementation-status]], [[phase5-programming]],
[[eprom-programmability-question]].
