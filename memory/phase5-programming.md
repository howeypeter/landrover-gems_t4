---
name: phase5-programming
description: Phase 5 (programming/coding/immobiliser/maps) design and where each piece lives
metadata:
  type: project
---

**Phase 5 complete 2026-07-07.** The write side of the tool, all validated
end-to-end headless (93 tests).

## Security-Learn — the ONE genuine GEMS over-the-wire write
- `gems/immobiliser.py`: high-level `security_learn(client, on_progress=...)`
  (unlock $27 → enter-learn → simulate BeCM re-send → store code → verify) +
  `read_status`. Returns `SecurityLearnResult(ok, message, steps)`;
  `ImmobiliserStatus(mobilised, learn_mode, summary)`.
- Virtual ECU: new `$31 StartRoutine` handler with routines 0x01 enter-learn
  (needs $27 unlock else SECURITY_ACCESS_DENIED), 0x02 submit-code (needs learn
  mode else REQUEST_SEQUENCE_ERROR), 0x03 status. `VirtualEcu(immobilised=True)`
  starts desynced → reproduces the canon "ENGINE IMMOBILISED" non-start; the
  `mobilised`/`security_learn` $61 params mirror the state.
- Client: `KwpClient.start_routine(routine_id, data, *, expect_positive)`.

## Coding — gated read/edit/write
- `gems/programming.py` already had the gates (backup + verify + confirm +
  read-only refusal); Phase 5 added `decode_field`/`encode_field` (ASCII for
  vin_last6/part_number, hex otherwise) and wired it through the backend.

## Maps — read-only chip-swap lookalike (NOT a K-line write)
- `gems/maps.py`: `FUEL_EPROM` (27C512, 64KB), `IGNITION_EPROM` (27C1001, 128KB),
  `CHIP_SWAP_NOTE` (the honest "no K-line reflash — bench swap"), and two 16×16
  `MapTable`s (synthetic-but-plausible fuel pulse-width + spark-advance surfaces).
  Deliberately no write path — matches the GEMS reality.

## Surfaces
- Backend (`app/backend.py`): coding_fields/read_coding[_text]/backup_coding/
  write_coding/encode_coding_text; immobiliser_status/set_immobilised/
  security_access/security_learn; available_maps/get_map. `Backend(immobilised=)`.
- CLI: `coding read|write --field K --value V`, `immo status|learn [--immobilised]`.
- GUI: `programming_menu` hub → `coding` / `immobiliser` / `maps` screens (built
  by a 3-agent fan-out against GUI_INTERFACES.md's Phase-5 section).

## Gotcha fixed
- Step/summary/note strings were made ASCII-safe (no `—`/`→`/`…`) because the CLI
  prints them and a Windows cp1252 console crashes on those chars. Keep new
  user-facing CLI strings ASCII.

Related: [[implementation-status]], [[research-gems-data]],
[[research-gems-hardware]], [[research-kline-protocols]].
