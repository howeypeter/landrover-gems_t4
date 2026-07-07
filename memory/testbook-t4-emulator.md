---
name: testbook-t4-emulator
description: Current project — build a UI/workflow simulator of the Rover TestBook T4 Mobile dealer diagnostic tool with an emulated ECU; design pillars and spec decisions agreed July 2026
metadata: 
  node_type: memory
  type: project
  originSessionId: 8b433210-a332-4063-b996-395f1cfb9374
---

As of 2026-07-06 the active project in this workspace is a **TestBook T4 Mobile
emulator**: a software recreation of the Rover/Land Rover dealer diagnostic
tool's touchscreen UI and workflows, backed by a fake/emulated ECU (no car or
adapter). User chose "UI/workflow simulator" over a working diagnostic tool or
running original software; vehicle coverage is generic/representative.

**Why:** Nostalgia/experience project — the goal is that an ex-user says
"yes, that's it." The full spec, design pillars, and real-T4 facts live in the
repo's `CLAUDE.md` under "TestBook T4 Mobile emulator" (kiosk feel, VIN-first
guided workflows, ~108 live measures with bandwidth trade-off, interlocked
actuator tests, RDS 5.06 "T4 Lite" identity, virtual ECU speaking $61/$7f
records behind a swappable transport).

**How to apply:** The spec of record is
`C:\Users\howey\OneDrive\Documents\Claude\Projects\LandRoverV1\CLAUDE.md`
(project home — see [[landrover-v1-project-home]]; always save project files
there). Still awaiting user confirmation on: full-nostalgia vs modernized
rendering (recommended full nostalgia), v1 scope sign-off, and whether v1 gets
one guided fault-tree procedure. See [[t4-research-sources]] for where the
facts came from.
