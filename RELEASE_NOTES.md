# Release Notes: v0.0.4

**Tag:** v0.0.4
**Date:** 2026-07-07
**Branch:** `v0.0.4` (from `v0.0.3`)

## Summary

**v0.0.4 is a quality/bugfix release.** No new features — instead: a
**229-test independent regression suite** written from scratch against the
frozen contracts (deliberately not derived from the original `tests/` suite),
the bugs it found fixed, the package version aligned with the release tags,
and stale files removed from the repository.

## Bug Fixes

### 1. CLI `coding write` now asks the operator before writing

The CLI previously auto-satisfied the confirmation gate
(`confirm=lambda: True` in `gems_t4/app/cli.py`), so a coding write — which
also has a real-hardware `--port` path — went through without any operator
confirmation, contrary to the documented "every ECU write gated … +
confirmation" rule. Now:

```
> gems_t4 coding write --field vin_last6 --value 654321
Write VIN (last 6): '123456' -> '654321'? [y/N]
```

- Anything but `y`/`yes` (including EOF on a non-interactive stdin) refuses
  the write: `write of 'vin_last6' not confirmed by operator`, exit 1.
- New **`--yes` / `-y`** flag skips the prompt for scripted use.
- The prompt tolerates the UTF-8 BOM that PowerShell 5.1 pipes prepend
  (`echo y | gems_t4 coding write …` works from PowerShell and bash alike).

### 2. `firmware/HOST_PROTOCOL.md` worked example had wrong KWP checksums

The TesterPresent example frames used a stale `60` placeholder as the KWP
checksum. Corrected to the real 8-bit sums (`80 10 F1 01 3E` → `C0`;
`80 F1 10 01 7E` → `00`), with the arithmetic shown. Runtime was never
affected (the Pico is a byte pipe and doesn't validate KWP checksums), but
the example would have misled anyone hand-crafting frames.

### 3. Version alignment: package now reports `0.0.4`

The Python package carried `0.1.0` (`pyproject.toml`, `__version__`,
`--version`) while git branches/release notes used `v0.0.x` — two schemes.
The package version now tracks the release tag: `gems_t4 --version` →
`gems_t4 0.0.4`.

### 4. Stale comment fix

`gems_t4/app/gui/screens/live_data.py` said "~24-parameter sweep"; it's 37.

## Removed (git rm)

- **`diagrams/p38-gems-network.svg`** — the P38 network diagram the user
  reported as incorrect (2026-07-06). It was no longer referenced anywhere;
  the accurate diagram is `diagrams/p38-gems-electronics.html` (built from
  `docs/land-rover-electronics.md`). The SVG survives in git history.

Audited but deliberately **kept**: `gems_t4/protocol/init.py` (never imported
yet, but a frozen INTERFACES.md contract module holding the canonical init
constants) and `gems_t4/transport/ftdi.py` (documented intentional stub).

## New: independent regression suite (`tests_regression/`)

Written by a 4-agent parallel fan-out, each agent working **only** from
INTERFACES.md / GUI_INTERFACES.md / CLAUDE.md / the READMEs /
HOST_PROTOCOL.md and the source — reading the original `tests/` suite was
forbidden — so it independently verifies that the code does what the
documentation promises.

| File | Tests | Covers |
|---|---|---|
| `test_regr_protocol.py` | 37 | framing/checksums, KwpClient, init constants, security, layering-purity guard |
| `test_regr_transport.py` | 19 | VirtualTransport, PicoAdapterTransport vs fake serial (HOST_PROTOCOL framing), FTDI stub |
| `test_regr_virtual_ecu.py` | 15 | $21/$1A/$27/$31 services, warm-up curve, idle hunt, sim clock, immobilised flag |
| `test_regr_scenarios.py` | 14 | per-scenario DTC signatures, clear semantics, live-data coherence, cyl-3 saturation |
| `test_regr_livedata_actuators.py` | 20 | exactly 37 params + documented ids/units, encode/decode round-trips, 5 actuators + interlocks |
| `test_regr_programming_immo_maps.py` | 24 | coding field set + gates, Security-Learn flow, read-only 16×16 maps |
| `test_regr_backend.py` | 19 | Qt-free proof, lifecycle, all Backend methods per GUI_INTERFACES.md |
| `test_regr_cli.py` | 25 | every subcommand end-to-end in subprocesses, exit codes, **new confirm-gate tests** |
| `test_regr_gui.py` | 38 | 11 screens, nav/back-stack, gauges + bandwidth trade-off, LAN disclaimer, wait overlay, paint smoke |

Run it explicitly (it is outside pyproject's default `testpaths`):

```bash
pytest tests_regression        # 233 passed (with the [gui] extra)
pytest                         # the original suite: 123 passed
```

(229 tests as delivered by the fan-out + 4 confirm-gate tests added with the
CLI fix = 233.)

## Known observations (documented, not changed)

Flagged by the regression agents; deferred as hardware-path polish for the
Phase-3 on-car work:

1. `PicoAdapterTransport` has no `set_timing()` — HOST_PROTOCOL.md defines
   SET_TIMING (0x04) and `TimingPolicy.as_milliseconds()` exists for it, but
   Python never sends it.
2. `PicoAdapterTransport.receive()` after `close()` can still return a
   buffered response (VirtualTransport raises `TransportClosed`).
3. `PicoAdapterTransport` mode strings are case-sensitive, unlike
   `init.normalize_mode`.
4. The virtual ECU accepts `$3B` writes to any local id — read-only coding
   enforcement is client-side (consistent with `programming.py`'s documented
   design, but the wire itself has no write protection).

## Metrics

| Metric | v0.0.3 | v0.0.4 | Change |
|---|---|---|---|
| **Original suite** | 123 passed | 123 passed | unchanged |
| **Independent regression suite** | — | 233 passed | new |
| **Package version** | 0.1.0 (mismatched) | 0.0.4 (aligned) | fixed |
| **Tracked files removed** | — | 1 (`p38-gems-network.svg`) | `git rm` |

## Testing

```bash
pytest                         # original suite: 123 passed ([gui] extra) / 74 passed + 10 skipped without
pytest tests_regression        # independent suite: 233 passed ([gui] extra) / 195 passed + 1 skipped without
```

(Both "without PySide6" counts verified in a genuinely clean disposable venv
with only `requirements.txt` installed.)

Windows exes rebuilt from clean `build/`+`dist/` at 0.0.4 and validated
(`--version`, scenarios, 37-param live parity, windowed exe alive headless).

---

Previous releases: [v0.0.3](RELEASE_NOTES_v0.0.3.md) ·
[v0.0.2](RELEASE_NOTES_v0.0.2.md) · [v0.0.1](RELEASE_NOTES_v0.0.1.md)
