# gems_t4 GUI — Build Contract (read before writing any screen)

The PySide6 kiosk shell, backend, and three reference screens already exist and
are FIXED. Your job is to flesh out one or more **screen** files to the same
contract. Code to the interfaces here; do not modify the shell/backend/other
screens.

## Architecture (already built — do not change)

- `gems_t4/app/backend.py` — `Backend`: the Qt-free seam over gems_core.
- `gems_t4/app/gui/style.py` — Win98 QSS + palette constants.
- `gems_t4/app/gui/base.py` — `Screen` base class + `KioskWindow`.
- `gems_t4/app/gui/app.py` — registers all screens by name; start = `boot`.
- Reference screens to copy the pattern from: `screens/boot.py`,
  `screens/system_menu.py`, `screens/fault_codes.py`. **Read these first.**

## The `Screen` base class (subclass this)

```python
class Screen(QWidget):
    navigate = Signal(str)   # emit a screen name to navigate there
    status   = Signal(str)   # emit text to update the status bar
    title: str = "Screen"    # shown in the window title bar
    def __init__(self, backend: Backend, parent: QWidget | None = None): ...
    def on_enter(self) -> None: ...        # called each time shown — refresh here
    def on_leave(self) -> None: ...        # called when navigating away
    def nav_buttons(self) -> set[str]: ... # subset of {"back","cross","tick"}
    def tick_label(self) -> str: ...       # default "✓"
    def cross_label(self) -> str: ...      # default "✗"
    def on_tick(self) -> None: ...         # global tick button pressed
    def on_cross(self) -> None: ...        # global cross button pressed
    def on_back(self) -> bool: ...         # return True if handled, else window pops history
```

Rules:
- Constructor signature MUST be `(self, backend, parent=None)` and call
  `super().__init__(backend, parent)`.
- Build all widgets in `__init__`; do heavy/data work in `on_enter` (the screen
  is constructed once and reused).
- Get data ONLY from `self.backend` (never import protocol/transport/gems
  directly). Read `on_enter` fresh each time.
- Use `self.status.emit("...")` for status-bar messages, `self.navigate.emit(
  "name")` to move between screens.
- Prefer object names / classes from `style.py` (e.g. `objectName="MenuItem"`,
  `objectName="Lcd"`) over hard-coded colors.

## `Backend` API (the only data source)

```python
backend.scenario_name -> str
backend.connected -> bool
backend.is_wireless -> bool                         # network transport (write policy applies)
backend.is_remote -> bool                           # any non-virtual transport (USB/network)
backend.connection_label -> str                     # e.g. "Network — 192.168.1.50:9141 (read-only)"
backend.set_connection(kind, *, com_port=None, host=None,
                       tcp_port=9141, allow_writes=False) -> None
#   kind: "virtual" | "usb" | "network". Disconnects; next op reconnects.
backend.apply_connection(kind, **same_kwargs) -> str
#   set_connection + connect, atomically: rolls back to the previous
#   transport if the new one fails to open. Returns connection_label.
#   Used by screens/connection.py; settings persist via gems_t4.app.config.
Backend.available_scenarios() -> list[str]          # staticmethod
Backend.actuator_list() -> list[ActuatorDef]        # staticmethod
backend.set_scenario(name: str) -> None             # reconnects if open
backend.connect() / backend.disconnect()
backend.tick(dt: float) -> None                     # advance warm-up/idle sim
backend.read_live(ids: list[int] | None = None) -> list[Measure]
backend.read_dtcs() -> list[Dtc]
backend.clear_dtcs() -> None
backend.run_actuator(actuator_id: int, state: int) -> ActuatorOutcome
```
Value objects (`from gems_t4.gems.types import ...` / `gems.actuators`):
- `Measure(name: str, value: float|int|str, unit: str, raw: int)`; `.formatted()`.
- `Dtc(code, description, raw, state)`; `state.value` is "active"/"stored"/...
- `ActuatorOutcome(actuator_id, ok: bool, message: str)`.
- `ActuatorDef(actuator_id, name, allowed_engine_running)`;
  ids: `gems.actuators.ACT_MIL/ACT_O2_HEATER/ACT_FUEL_PUMP/ACT_AC_GRANT/
  ACT_CONDENSER_FAN`; states `gems.actuators.STATE_ON/STATE_OFF`.

`backend.connect()` is safe to call repeatedly (idempotent); `read_*` auto-connect
if needed. The default scenario ("healthy") has no DTCs; "coolant_sensor" sets
P0118 with coolant reading -40, etc.

### Phase 5 — programming / immobiliser / maps (Backend API)

```python
# Coding (gated read/edit/write)
Backend.coding_fields() -> list[CodingField]     # .key, .name, .writable (staticmethod)
backend.read_coding_text(field: str) -> str      # display string (ASCII or hex)
backend.encode_coding_text(field, text) -> bytes # staticmethod; parse edited value (ValueError on bad hex)
backend.backup_coding(field: str) -> Backup      # read-before-write snapshot
backend.write_coding(field, value: bytes, *, backup: Backup,
                     verify=True, confirm: Callable[[],bool]|None=None) -> WriteResult
#   WriteResult(.ok: bool, .message: str). Raises ProgrammingRefused
#   (from gems_t4.gems.programming) if field is read-only / no backup / not confirmed.

# Immobiliser / Security-Learn
backend.immobiliser_status() -> ImmobiliserStatus   # .mobilised, .learn_mode, .summary
backend.set_immobilised(bool) -> None               # force ENGINE IMMOBILISED on/off (rebuilds ECU)
backend.security_learn(on_progress: Callable[[str],None]|None=None) -> SecurityLearnResult
#   SecurityLearnResult(.ok, .message, .steps: list[str]). on_progress is called per step.

# Maps (read-only chip-swap lookalike)
Backend.available_maps() -> list[str]            # ["fuel","ignition"]  (staticmethod)
Backend.get_map(token) -> MapTable               # .name .unit .rpm_axis .load_axis .rows .cols .cell(r,c)
# from gems_t4.gems.maps import FUEL_EPROM, IGNITION_EPROM, CHIP_SWAP_NOTE
#   EpromChip(.part, .size_kb, .holds); CHIP_SWAP_NOTE is the "no K-line reflash" text.
```
Types: `from gems_t4.gems.programming import CodingField, Backup, WriteResult,
ProgrammingRefused`; `from gems_t4.gems.immobiliser import ImmobiliserStatus,
SecurityLearnResult`; `from gems_t4.gems.maps import MapTable, FUEL_EPROM,
IGNITION_EPROM, CHIP_SWAP_NOTE`.

## Concurrency

v1 is single-threaded: the virtual ECU answers instantly. For periodic refresh
(live data) use a `QTimer` in the screen — do NOT spawn threads. Stop your timer
in `on_leave` and start it in `on_enter`. (A background worker for slow real
hardware is a later enhancement; don't add it now.)

## Testing (required, headless)

Each screen ships a pytest test under `tests/` using **pytest-qt** (`qtbot`).
Headless is already configured (tests/conftest.py sets `QT_QPA_PLATFORM=
offscreen`). Pattern:

```python
def test_live_data_populates(qtbot):
    from gems_t4.app.backend import Backend
    from gems_t4.app.gui.screens.live_data import LiveDataScreen
    screen = LiveDataScreen(Backend("healthy"))
    qtbot.addWidget(screen)
    screen.on_enter()
    # assert the screen pulled measures from the backend ...
    screen.on_leave()   # ensure timers stop cleanly
```
Assert real behavior (rows populated, refusal shown, timer stops), not just that
it constructs. Run ONLY your test file(s):
`.venv\Scripts\python -m pytest tests/<your_test>.py -q`

## Quality bar

Python 3.11+, `from __future__ import annotations`, type hints, docstrings. Match
the look and structure of the reference screens. Keep imports to PySide6 +
`gems_t4.app...` + `gems_t4.gems...`.
