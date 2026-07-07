"""End-to-end: VirtualEcu -> VirtualTransport -> KwpClient -> GEMS services.

This is the real proof the parallel-built layers compose: a full read ->
diagnose -> act -> clear workflow, with coherent cross-module symptoms per
fault scenario.
"""
from __future__ import annotations

import pytest

from gems_t4.gems import actuators, dtc, livedata
from gems_t4.gems.scenarios import get_scenario
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.protocol.client import KwpClient
from gems_t4.transport.virtual import VirtualTransport


def _client(scenario_name: str) -> KwpClient:
    ecu = VirtualEcu(get_scenario(scenario_name))
    for _ in range(5):
        ecu.tick(0.1)
    client = KwpClient(VirtualTransport(ecu))
    client.connect()
    client.start_session()
    return client


def test_healthy_has_no_faults_and_reads_live():
    client = _client("healthy")
    assert dtc.read_dtcs(client) == []
    measures = livedata.read_all(client)
    assert len(measures) == len(livedata.PARAMETERS)
    coolant = next(m for m in measures if m.name.startswith("Coolant"))
    assert 80 <= float(coolant.value) <= 90


def test_coolant_scenario_is_coherent():
    client = _client("coolant_sensor")
    codes = [d.code for d in dtc.read_dtcs(client)]
    assert "P0118" in codes
    coolant_raw = client.read_data_by_local_id(0x01)
    coolant = livedata.decode_measure(0x01, coolant_raw)
    assert float(coolant.value) == -40  # fail-safe / implausible reading


def test_misfire_scenario_reports_cyl3():
    client = _client("misfire_cyl3")
    codes = [d.code for d in dtc.read_dtcs(client)]
    assert "P0303" in codes


def test_lambda_heater_refuses_o2_heater_test():
    client = _client("lambda_heater")
    assert "P1185" in [d.code for d in dtc.read_dtcs(client)]
    outcome = actuators.run(client, actuators.ACT_O2_HEATER, actuators.STATE_ON)
    assert not outcome.ok


def test_fuel_pump_refused_across_scenarios():
    for name in ("healthy", "coolant_sensor", "misfire_cyl3", "lambda_heater"):
        client = _client(name)
        outcome = actuators.run(client, actuators.ACT_FUEL_PUMP, actuators.STATE_ON)
        assert not outcome.ok, f"fuel pump should be refused in {name}"


def test_read_then_clear_workflow():
    client = _client("coolant_sensor")
    assert dtc.read_dtcs(client)  # non-empty
    dtc.clear_dtcs(client)
    assert dtc.read_dtcs(client) == []
