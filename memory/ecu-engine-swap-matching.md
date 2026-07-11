---
name: ecu-engine-swap-matching
description: Open backlog item — reconciling a cross-fitted GEMS ECU (from a parts car) to a different engine/model-year; what coding/Security-Learn can vs can't fix
metadata:
  type: project
---

**Open backlog item, logged 2026-07-11. Do NOT investigate until picked up** —
recorded at the user's request.

## The real-world scenario (the user's actual situation)
User has a GEMS ECU from a **parts car** and an **engine from a different car**,
possibly a slightly different model year and/or displacement. Question: can this
tool "reprogram" the GEMS ECU to match the engine?

## Starting assessment (to VERIFY when picked up — not gospel)
Three layers, different answers:
1. **True calibration match = the fuel/ignition MAPS, which live on socketed
   EPROM chips inside the ECU.** These are a bench chip-swap, NOT reprogrammable
   over the K-line (neither this tool nor the original T4 could). So a genuinely
   mismatched displacement (e.g. 4.6 ECU on a 4.0 engine) can't be
   software-converted over the wire — you need the ECU with the right chips, or
   swap the EPROMs. See [[eprom-programmability-question]].
2. **Getting it to START = immobiliser Security-Learn** (BeCM↔ECM re-sync). A
   swapped ECU will usually be out of sync → canon "ENGINE IMMOBILISED". This is
   the ONE genuine GEMS K-line write and is already modelled (`immo learn`).
   This is most likely what the user actually needs to make a swapped ECU run.
3. **Config CODING** (VIN last-6, dealer id, 4.0/4.6 select, transmission)
   partly applies — coding fields exist (`gems/programming.py`) — but real-world
   fidelity is unvalidated, and much VIN/EKA/market coding lives in the **BeCM,
   not the engine ECU**. See [[engine-variant-toggle]] for the 4.0/4.6 byte.

Overriding caveat: today the tool only drives the VIRTUAL ECU; the
real-hardware path is unvalidated (Phase 3, pending the L9637D). Nothing is
proven against a real ECU yet. See [[implementation-status]].

## Backlog work (when picked up)
- Pin down exactly which mismatches (displacement, model year, market) are
  reconcilable by coding + Security-Learn vs. which force an EPROM swap or a
  different ECU.
- Turn that into a guided "ECU-to-engine matching" procedure in the tool.
- Needs the specifics of the two donor vehicles (displacement + year for both
  the ECU's parts car and the engine) to answer concretely.

Recorded in CLAUDE.md under "Backlog / open research items". Related:
[[eprom-programmability-question]], [[engine-variant-toggle]],
[[phase5-programming]], [[implementation-status]].
