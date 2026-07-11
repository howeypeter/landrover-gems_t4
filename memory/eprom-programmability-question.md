---
name: eprom-programmability-question
description: Open backlog research question — whether GEMS EPROM/calibration can be programmed on certain model years (not just bench chip-swap)
metadata:
  type: project
---

**Open research item, logged 2026-07-11. DO NOT investigate until explicitly
picked up** — the user asked to record it as a backlog question, not to research
it now.

## The question
Current project stance (see CLAUDE.md "⚠️ 'Programming' a GEMS ECU means three
things — only one is over the wire"): GEMS engine maps/calibration live on
**socketed UV-EPROMs** (27C512 fuel, 27C1001 ignition+code) with **NO K-line
reflash path — a bench chip-swap only**, unlike the later Td5/MEMS3 (AMD flash,
documented by Revill). The map editor in the tool is a read-only "chip-swap
lookalike" precisely because of this.

**Open question to research later:** does "no reflash, ever" actually hold
across *all* GEMS model years and variants? Or do certain years/variants allow
the EPROM (or its calibration) to be programmed some other way —
in-system/in-circuit, a different chip revision (e.g. an OTP or flash-based
part substituted in some production run), or a factory/dealer path that isn't
the K-line? Revisit before treating "bench chip-swap only" as absolute across
the whole GEMS era.

## Why it matters
If some model years are field-/dealer-programmable, that changes the tool's
scope: the map editor could become a real write path for those, not just a
lookalike. Until researched, keep the read-only chip-swap framing.

Recorded in CLAUDE.md under "Backlog / open research items" in the Build-status
section. Related: [[implementation-status]], [[pico-board-support]].
