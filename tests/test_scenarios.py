"""Fault-scenario coherence."""
from __future__ import annotations

from gems_t4.gems import scenarios
from gems_t4.gems.actuators import ACT_O2_HEATER


def test_registry_has_the_four_scenarios():
    assert set(scenarios.SCENARIOS) == {
        "healthy", "coolant_sensor", "misfire_cyl3", "lambda_heater"
    }


def test_healthy_has_no_dtcs():
    assert scenarios.get_scenario("healthy").stored_dtcs() == []


def test_coolant_scenario_sets_code_and_perturbs_live():
    sc = scenarios.get_scenario("coolant_sensor")
    assert any(d.code == "P0118" for d in sc.stored_dtcs())
    state = {"coolant_temp": 85.0, "engine_running": True, "rpm": 750.0}
    sc.perturb(state)
    assert state["coolant_temp"] == -40.0


def test_lambda_heater_blocks_o2_heater_actuator():
    sc = scenarios.get_scenario("lambda_heater")
    assert any(d.code == "P1185" for d in sc.stored_dtcs())
    assert sc.blocks_actuator(ACT_O2_HEATER) is True


def test_misfire_scenario_reports_cyl3():
    sc = scenarios.get_scenario("misfire_cyl3")
    assert any(d.code == "P0303" for d in sc.stored_dtcs())
