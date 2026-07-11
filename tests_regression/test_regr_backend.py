"""Independent regression tests for the Qt-free ``Backend`` facade.

Behaviour is asserted against GUI_INTERFACES.md ("`Backend` API (the only data
source)" + "Phase 5 — programming / immobiliser / maps (Backend API)") — NOT
against the existing tests/ suite.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from gems_t4.app.backend import Backend
from gems_t4.gems.actuators import (
    ACT_FUEL_PUMP,
    ACT_MIL,
    ACT_O2_HEATER,
    STATE_ON,
)
from gems_t4.gems.programming import ProgrammingRefused

PROJECT = Path(__file__).resolve().parents[1]
VENV_PY = PROJECT / ".venv" / "Scripts" / "python.exe"


# --------------------------------------------------------------------------- #
# Qt-freeness: importing the backend must not drag in PySide6/Qt
# --------------------------------------------------------------------------- #
def test_backend_import_is_qt_free():
    """GUI_INTERFACES.md: 'gems_t4/app/backend.py — Backend: the Qt-free seam'.

    Check in a fresh interpreter that importing the module loads no Qt binding.
    """
    code = (
        "import sys; import gems_t4.app.backend; "
        "bad = sorted(m for m in sys.modules "
        "if m.split('.')[0] in ('PySide6', 'PyQt5', 'PyQt6', 'shiboken6')); "
        "print(','.join(bad))"
    )
    proc = subprocess.run(
        [str(VENV_PY if VENV_PY.exists() else sys.executable), "-c", code],
        cwd=str(PROJECT), capture_output=True, text=True, timeout=120,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "", (
        f"importing gems_t4.app.backend loaded Qt modules: {proc.stdout.strip()}"
    )


# --------------------------------------------------------------------------- #
# Session lifecycle / scenario selection
# --------------------------------------------------------------------------- #
def test_scenario_and_actuator_catalogues():
    assert Backend.available_scenarios() == [
        "healthy", "coolant_sensor", "misfire_cyl3", "lambda_heater",
    ]
    acts = Backend.actuator_list()
    assert len(acts) == 5
    names = {a.name for a in acts}
    assert any("MIL" in n for n in names)
    assert any("Fuel pump" in n for n in names)
    # exactly one actuator is barred while the engine runs (the fuel pump relay)
    assert [a.actuator_id for a in acts if not a.allowed_engine_running] == [ACT_FUEL_PUMP]


def test_connect_is_idempotent_and_disconnect_resets():
    b = Backend("healthy")
    assert b.scenario_name == "healthy"
    assert not b.connected
    b.connect()
    assert b.connected
    b.connect()  # documented: safe to call repeatedly
    assert b.connected
    assert b.is_wireless is False  # wired/virtual path
    b.disconnect()
    assert not b.connected
    b.disconnect()  # idempotent


def test_set_scenario_validates_and_reconnects():
    b = Backend("healthy")
    with pytest.raises(KeyError):
        b.set_scenario("no_such_scenario")
    b.connect()
    assert b.read_dtcs() == []  # healthy has no DTCs
    b.set_scenario("coolant_sensor")
    assert b.scenario_name == "coolant_sensor"
    assert b.connected, "set_scenario on an open session must reconnect"
    codes = [d.code for d in b.read_dtcs()]
    assert codes == ["P0118"]
    b.disconnect()


def test_read_methods_autoconnect():
    """GUI_INTERFACES.md: 'read_* auto-connect if needed'."""
    b = Backend("healthy")
    assert not b.connected
    measures = b.read_live([0x01])
    assert b.connected
    assert len(measures) == 1


# --------------------------------------------------------------------------- #
# Live data / DTCs / actuators
# --------------------------------------------------------------------------- #
def test_read_live_all_and_selected():
    b = Backend("healthy")
    all_measures = b.read_live()
    assert len(all_measures) == 40, "CLAUDE.md: '40 live-data params'"
    two = b.read_live([0x01, 0x02])
    assert [m.name for m in two] == ["Coolant temperature", "Engine speed"]
    assert two[0].unit == "degC"
    assert two[1].unit == "rpm"
    b.disconnect()


def test_coolant_scenario_live_anomaly():
    """GUI_INTERFACES.md: '\"coolant_sensor\" sets P0118 with coolant reading -40'."""
    b = Backend("coolant_sensor")
    (coolant,) = b.read_live([0x01])
    assert coolant.value == -40.0
    b.disconnect()


def test_dtc_read_and_clear_roundtrip():
    b = Backend("misfire_cyl3")
    codes = [d.code for d in b.read_dtcs()]
    assert codes == ["P0303", "P1303"]
    b.clear_dtcs()
    assert b.read_dtcs() == []
    b.disconnect()


def test_actuator_ok_and_engine_running_refusal():
    b = Backend("healthy")
    ok = b.run_actuator(ACT_MIL, STATE_ON)
    assert ok.ok
    assert "switched on" in ok.message
    refused = b.run_actuator(ACT_FUEL_PUMP, STATE_ON)
    assert not refused.ok
    assert "not available" in refused.message
    assert "conditions not correct" in refused.message
    b.disconnect()


def test_scenario_driven_actuator_refusal():
    b = Backend("lambda_heater")
    outcome = b.run_actuator(ACT_O2_HEATER, STATE_ON)
    assert not outcome.ok, "open heater circuit must make the O2 heater test fail"
    b.disconnect()


def test_tick_advances_the_warmup_curve():
    b = Backend("healthy")
    (before,) = b.read_live([0x01])
    assert before.value == 85.0  # nominal cold-ish baseline
    b.tick(5.0)
    (after,) = b.read_live([0x01])
    assert after.value == 88.0  # warm-up curve saturates at 88 degC
    b.disconnect()


# --------------------------------------------------------------------------- #
# Coding through the backend (gated writes)
# --------------------------------------------------------------------------- #
def test_backend_coding_fields_and_reads():
    fields = {f.key: f for f in Backend.coding_fields()}
    assert set(fields) == {
        "vin_last6", "dealer_id", "engine", "transmission",
        "build_code", "market", "part_number",
    }
    assert fields["vin_last6"].writable
    assert not fields["market"].writable
    assert not fields["part_number"].writable

    b = Backend("healthy")
    assert b.read_coding_text("vin_last6") == "123456"
    assert b.read_coding_text("part_number") == "ERR7109"
    assert b.read_coding_text("market") == "01"  # hex rendering for non-text fields
    b.disconnect()


def test_backend_gated_write_roundtrip():
    b = Backend("healthy")
    backup = b.backup_coding("vin_last6")
    assert backup.data == b"123456"
    value = Backend.encode_coding_text("vin_last6", "654321")
    result = b.write_coding("vin_last6", value, backup=backup, confirm=lambda: True)
    assert result.ok
    assert result.message == "write verified"
    assert b.read_coding_text("vin_last6") == "654321"
    b.disconnect()


def test_backend_write_gates_refuse():
    b = Backend("healthy")
    # read-only field
    with pytest.raises(ProgrammingRefused):
        b.write_coding("market", b"\x02", backup=b.backup_coding("market"))
    # unconfirmed write
    with pytest.raises(ProgrammingRefused):
        b.write_coding(
            "vin_last6", b"999999",
            backup=b.backup_coding("vin_last6"), confirm=lambda: False,
        )
    # backup of the wrong field
    with pytest.raises(ProgrammingRefused):
        b.write_coding("vin_last6", b"999999", backup=b.backup_coding("dealer_id"))
    # nothing changed
    assert b.read_coding_text("vin_last6") == "123456"
    b.disconnect()


def test_backend_encode_coding_text_errors():
    assert Backend.encode_coding_text("dealer_id", "00 02") == b"\x00\x02"
    with pytest.raises(ValueError):
        Backend.encode_coding_text("dealer_id", "zz")  # GUI contract: ValueError on bad hex


# --------------------------------------------------------------------------- #
# Immobiliser through the backend
# --------------------------------------------------------------------------- #
def test_backend_immobiliser_default_mobilised():
    b = Backend("healthy")
    status = b.immobiliser_status()
    assert status.mobilised
    assert not status.learn_mode
    assert status.summary == "MOBILISED - engine enabled"
    b.disconnect()


def test_backend_immobilised_flag_and_security_learn_recovery():
    b = Backend("healthy", immobilised=True)
    assert b.immobiliser_status().summary == "ENGINE IMMOBILISED"

    progress: list[str] = []
    result = b.security_learn(on_progress=progress.append)
    assert result.ok
    assert "re-synced" in result.message
    assert result.steps == progress and progress
    assert b.immobiliser_status().mobilised
    b.disconnect()


def test_backend_set_immobilised_rebuilds_the_ecu():
    b = Backend("healthy")
    assert b.immobiliser_status().mobilised
    b.set_immobilised(True)
    assert b.immobiliser_status().summary == "ENGINE IMMOBILISED"
    b.set_immobilised(False)
    assert b.immobiliser_status().mobilised
    b.disconnect()


# --------------------------------------------------------------------------- #
# Maps through the backend
# --------------------------------------------------------------------------- #
def test_backend_maps_surface():
    assert Backend.available_maps() == ["fuel", "ignition"]
    for token in Backend.available_maps():
        table = Backend.get_map(token)
        assert table.rows == 16 and table.cols == 16
        assert len(table.rpm_axis) == 16 and len(table.load_axis) == 16
        assert isinstance(table.cell(3, 4), float)
