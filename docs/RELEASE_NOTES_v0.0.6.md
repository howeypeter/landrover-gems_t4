# Release Notes: v0.0.6

**Tag:** v0.0.6
**Date:** 2026-07-12
**Released from:** `main` (continuing directly on `main` after v0.0.5 was merged)

## Summary

**v0.0.6 is a small UX / polish release.** No new diagnostic capability — it makes
the existing tool clearer to use: the ECU connection is now visible and testable
from every screen, and two demo behaviors that *looked* like bugs (but were
authentic GEMS/T4 behavior) now explain themselves.

## What's new

### Persistent connection indicator + on-demand link test
- The kiosk title bar now shows a **"VCI: …" button on every screen** with the
  active connection (Virtual / USB COM / Network). Click it to jump straight to
  the Configuration screen — no more digging through the System menu to change
  or check the connection.
- The Configuration screen's **✗ button is now "Test"**: it proves the
  *currently active* connection works and, on USB/Network, measures round-trip
  latency (min/avg/max) to the adapter or server. Applying a new connection (✓)
  still tests-and-persists as before.

## Fixes

### 1. Clearing fault codes no longer implies you can clear just one
On a GEMS (and the real TestBook T4) there is no per-code clear — the clear
command always wipes every stored code. The fault-codes list previously let you
highlight a row, which wrongly implied "select one, clear that one." The list is
now a plain read-only list (no row highlight) and the action is labeled
**"Clear ALL codes."** Clearing behavior is unchanged.

### 2. The fuel-pump actuator test now explains why it's refused
Testing the fuel pump relay is refused while the engine is running — the
authentic safety interlock. It previously showed a generic *"conditions not
correct"* that read as broken. It now says **"test not available while the
engine is running"**, but only for engine-running-sensitive actuators; the
lambda-heater O2-heater refusal (a different reason) keeps the generic wording,
so the two stay distinct.

*(Note: with the current simulated ECU the engine is always "running," so the
fuel-pump test still always refuses in the demo — it just now says why. A future
"engine on/off" control would let it actually run, key-on/engine-off, like on a
real car.)*

## Housekeeping
- Removed leftover untracked shopping-list docs and framework-evaluation notes
  (they were never in git history).

## Tests
- `tests/`: **169 passed** (with the `[gui]` extra; GUI tests skip cleanly
  without PySide6).
- `tests_regression/`: **235 passed** — the independent suite (run explicitly).
- No test needs real hardware or a real serial port.

## Notes on conventions
- **Release notes are back, and now live under `docs/`** (`docs/RELEASE_NOTES_v0.0.6.md`)
  rather than the repo root — the root stays limited to `CLAUDE.md` / `README.md`
  / `INSTALL.md`. (v0.0.5 had removed the old root-level RELEASE_NOTES files; this
  reintroduces them in `docs/` at the user's request.)
- Package version tracks the tag: `pyproject.toml` / `gems_t4/__init__.py` /
  `--version` all report **0.0.6** (a regression test enforces the lockstep).
