"""Independent end-to-end regression tests for the ``gems_t4`` CLI.

Every test drives the real console entry point in a subprocess
(``python -m gems_t4 ...``) with ``--fake`` semantics (the default) and
``--latency 0``, asserting the behaviour documented in README.html /
CLAUDE.md — NOT behaviour learned from the existing tests/ suite.
"""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[1]
VENV_PY = PROJECT / ".venv" / "Scripts" / "python.exe"
PYTHON = str(VENV_PY if VENV_PY.exists() else sys.executable)

SCENARIOS = ["healthy", "coolant_sensor", "misfire_cyl3", "lambda_heater"]


def run_cli(*args: str, stdin_text: str | None = None) -> subprocess.CompletedProcess[str]:
    """Run ``python -m gems_t4 <args>`` and capture decoded text output."""
    env = dict(os.environ)
    env["GEMS_T4_INSTANT"] = "1"       # keep any waits instant
    env["PYTHONIOENCODING"] = "utf-8"  # Rich box-drawing survives the pipe
    env["COLUMNS"] = "200"             # no table wrapping -> one line per row
    return subprocess.run(
        [PYTHON, "-m", "gems_t4", *args],
        cwd=str(PROJECT),
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
        timeout=120,
    )


# --------------------------------------------------------------------------- #
# version / scenarios
# --------------------------------------------------------------------------- #
def test_version_flag():
    proc = run_cli("--version")
    assert proc.returncode == 0
    assert proc.stdout.strip() == "gems_t4 0.0.4"


def test_scenarios_lists_exactly_the_four():
    proc = run_cli("scenarios")
    assert proc.returncode == 0
    listed = re.findall(r"^\s*-\s*(\S+)\s*$", proc.stdout, flags=re.MULTILINE)
    assert listed == SCENARIOS


# --------------------------------------------------------------------------- #
# dtc read / clear
# --------------------------------------------------------------------------- #
def test_dtc_read_healthy_shows_no_faults():
    proc = run_cli("dtc", "read", "--scenario", "healthy", "--latency", "0")
    assert proc.returncode == 0
    assert "No faults stored" in proc.stdout
    assert "P0" not in proc.stdout


def test_dtc_read_coolant_sensor():
    proc = run_cli("dtc", "read", "--scenario", "coolant_sensor", "--latency", "0")
    assert proc.returncode == 0
    assert "P0118" in proc.stdout
    assert "Coolant" in proc.stdout


def test_dtc_read_misfire_cyl3():
    proc = run_cli("dtc", "read", "--scenario", "misfire_cyl3", "--latency", "0")
    assert proc.returncode == 0
    assert "P0303" in proc.stdout
    assert "P1303" in proc.stdout


def test_dtc_read_lambda_heater():
    proc = run_cli("dtc", "read", "--scenario", "lambda_heater", "--latency", "0")
    assert proc.returncode == 0
    assert "P1185" in proc.stdout


def test_dtc_clear_exits_zero():
    proc = run_cli("dtc", "clear", "--scenario", "misfire_cyl3", "--latency", "0")
    assert proc.returncode == 0
    assert "cleared" in proc.stdout.lower()


# --------------------------------------------------------------------------- #
# live data
# --------------------------------------------------------------------------- #
def test_live_selected_ids_renders_coolant_and_rpm():
    proc = run_cli("live", "--ids", "0x01", "0x02", "--latency", "0")
    assert proc.returncode == 0
    assert "Coolant temperature" in proc.stdout
    assert "Engine speed" in proc.stdout
    # the authentic slow-tool flavour line is printed
    assert "Communicating with ECU" in proc.stdout


def test_live_full_read_shows_37_parameter_rows():
    proc = run_cli("live", "--latency", "0")
    assert proc.returncode == 0
    # each table row carries exactly one raw-hex cell ("0x..."); nothing else
    # in the output contains "0x", so the count equals the parameter row count
    raws = re.findall(r"0x[0-9A-Fa-f]+", proc.stdout)
    assert len(raws) == 37, f"expected 37 live parameter rows, found {len(raws)}"


# --------------------------------------------------------------------------- #
# actuator tests + exit codes
# --------------------------------------------------------------------------- #
def test_actuator_mil_runs_ok_exit_zero():
    proc = run_cli("actuator", "mil", "--latency", "0")
    assert proc.returncode == 0
    assert "OK" in proc.stdout
    assert "switched on" in proc.stdout


def test_actuator_fuel_pump_refused_exit_one():
    """README.html: 'Exit code is 0 if the test ran, 1 if the ECU refused it';
    the fuel pump relay is 'refused while the engine \"runs\"'."""
    proc = run_cli("actuator", "fuel_pump", "--latency", "0")
    assert proc.returncode == 1
    assert "REFUSED" in proc.stdout
    assert "not available" in proc.stdout


def test_actuator_o2_heater_refused_in_lambda_heater_scenario():
    """README.html example: the o2_heater test is refused by the same fault
    that set P1185."""
    proc = run_cli(
        "actuator", "o2_heater", "--scenario", "lambda_heater", "--latency", "0"
    )
    assert proc.returncode == 1
    assert "REFUSED" in proc.stdout


def test_actuator_unknown_name_exits_two():
    proc = run_cli("actuator", "hyperdrive", "--latency", "0")
    assert proc.returncode == 2
    assert "unknown actuator" in proc.stdout


# --------------------------------------------------------------------------- #
# coding read / write (gated)
# --------------------------------------------------------------------------- #
def test_coding_read_renders_the_block():
    proc = run_cli("coding", "read", "--latency", "0")
    assert proc.returncode == 0
    out = proc.stdout
    assert "GEMS coding block" in out
    assert "VIN (last 6)" in out and "123456" in out
    assert "ERR7109" in out  # read-only part number
    # writability column: market + part number are the read-only rows
    for line in out.splitlines():
        if "Market" in line or "part number" in line:
            assert re.search(r"\bno\b", line), f"expected read-only marker in: {line!r}"
        if "VIN (last 6)" in line:
            assert re.search(r"\byes\b", line)


def test_coding_write_vin_succeeds_and_verifies():
    # the piped "y" answers the CLI's interactive confirmation prompt (v0.0.4)
    proc = run_cli(
        "coding", "write", "--field", "vin_last6", "--value", "654321",
        "--latency", "0", stdin_text="y\n",
    )
    assert proc.returncode == 0
    assert "write verified" in proc.stdout


def test_coding_write_prompts_before_writing():
    """v0.0.4: the CLI asks the operator before any coding write."""
    proc = run_cli(
        "coding", "write", "--field", "vin_last6", "--value", "654321",
        "--latency", "0", stdin_text="y\n",
    )
    assert "[y/N]" in proc.stdout
    assert "'123456' -> '654321'" in proc.stdout


def test_coding_write_declined_makes_no_change():
    """Answering "n" (or anything but y/yes) refuses the write, exit 1."""
    proc = run_cli(
        "coding", "write", "--field", "vin_last6", "--value", "654321",
        "--latency", "0", stdin_text="n\n",
    )
    assert proc.returncode == 1
    assert "not confirmed by operator" in proc.stdout
    assert "write verified" not in proc.stdout


def test_coding_write_no_input_refuses():
    """EOF on stdin (non-interactive run without --yes) must refuse, not write."""
    proc = run_cli(
        "coding", "write", "--field", "vin_last6", "--value", "654321",
        "--latency", "0", stdin_text="",
    )
    assert proc.returncode == 1
    assert "not confirmed by operator" in proc.stdout


def test_coding_write_yes_flag_skips_prompt():
    """--yes / -y answers the confirmation gate for scripted use."""
    proc = run_cli(
        "coding", "write", "--field", "vin_last6", "--value", "654321",
        "--latency", "0", "--yes",
    )
    assert proc.returncode == 0
    assert "write verified" in proc.stdout
    assert "[y/N]" not in proc.stdout


def test_coding_write_readonly_field_refused_exit_one():
    proc = run_cli(
        "coding", "write", "--field", "market", "--value", "02",
        "--latency", "0", stdin_text="y\n",
    )
    assert proc.returncode == 1
    assert "read-only" in proc.stdout


def test_coding_write_invalid_hex_rejected():
    proc = run_cli(
        "coding", "write", "--field", "dealer_id", "--value", "zz",
        "--latency", "0", stdin_text="y\n",
    )
    assert proc.returncode == 1


def test_coding_write_missing_args_exits_two():
    proc = run_cli("coding", "write", "--latency", "0")
    assert proc.returncode == 2
    assert "--field" in proc.stdout


# --------------------------------------------------------------------------- #
# immobiliser status / Security-Learn
# --------------------------------------------------------------------------- #
def test_immo_status_default_mobilised():
    proc = run_cli("immo", "status", "--latency", "0")
    assert proc.returncode == 0
    assert "MOBILISED - engine enabled" in proc.stdout


def test_immo_status_immobilised_shows_engine_immobilised():
    proc = run_cli("immo", "status", "--immobilised", "--latency", "0")
    assert proc.returncode == 0
    assert "ENGINE IMMOBILISED" in proc.stdout


def test_immo_learn_resyncs_and_exits_zero():
    proc = run_cli("immo", "learn", "--immobilised", "--latency", "0")
    assert proc.returncode == 0
    out = proc.stdout
    assert "Security-Learn complete" in out
    assert "re-synced" in out
    # the step log is echoed as it happens
    assert "Security access granted" in out
    assert "MOBILISED" in out
