"""Independent regression tests: the four fault scenarios and their coherence.

Written from the frozen contract (INTERFACES.md), CLAUDE.md and
RELEASE_NOTES.md — NOT derived from the original tests/ suite.

Documented claims under test:
* exactly four scenarios: healthy / coolant_sensor / misfire_cyl3 / lambda_heater;
* DTCs per scenario (none / P0118 / P0303+P1303 / P1185);
* clear works and the codes stay gone on re-read;
* each scenario's live-data anomalies are coherent with its DTCs
  (coolant -40 degC failsafe, whole misfire count on cylinder 3, open loop).
"""
from __future__ import annotations

import pytest

from gems_t4.gems import dtc as dtc_mod
from gems_t4.gems import livedata
from gems_t4.gems.scenarios import SCENARIOS, get_scenario
from gems_t4.gems.types import DtcState
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.protocol.client import KwpClient
from gems_t4.transport.virtual import VirtualTransport

ALL_SCENARIOS = ("healthy", "coolant_sensor", "misfire_cyl3", "lambda_heater")

#: Documented DTC signature per scenario (CLAUDE.md fault scenarios).
EXPECTED_DTCS = {
    "healthy": set(),
    "coolant_sensor": {"P0118"},
    "misfire_cyl3": {"P0303", "P1303"},
    "lambda_heater": {"P1185"},
}


def make_stack(scenario: str = "healthy", **ecu_kwargs):
    ecu = VirtualEcu(get_scenario(scenario), **ecu_kwargs)
    client = KwpClient(VirtualTransport(ecu))
    client.connect()
    return ecu, client


def read_value(client: KwpClient, local_id: int):
    raw = client.read_data_by_local_id(local_id)
    return livedata.decode_measure(local_id, raw).value


# --------------------------------------------------------------------------- #
# Registry
# --------------------------------------------------------------------------- #

def test_exactly_four_scenarios():
    assert set(SCENARIOS) == set(ALL_SCENARIOS)


def test_scenario_names_match_registry_keys():
    for key, scenario in SCENARIOS.items():
        assert scenario.name == key


def test_get_scenario_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        get_scenario("head_gasket")


# --------------------------------------------------------------------------- #
# DTC signatures + clear
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("name", ALL_SCENARIOS)
def test_scenario_dtc_signature(name):
    _, client = make_stack(name)
    codes = {d.code for d in dtc_mod.read_dtcs(client)}
    assert codes == EXPECTED_DTCS[name]


def test_scenario_dtcs_are_active_with_canonical_descriptions():
    _, client = make_stack("coolant_sensor")
    (d,) = dtc_mod.read_dtcs(client)
    assert d.code == "P0118"
    assert "high input" in d.description.lower()
    assert "coolant" in d.description.lower()
    assert d.state == DtcState.ACTIVE
    assert d.raw == dtc_mod.by_code("P0118").raw


@pytest.mark.parametrize("name", ALL_SCENARIOS)
def test_clear_dtcs_and_they_stay_gone(name):
    ecu, client = make_stack(name)
    dtc_mod.clear_dtcs(client)
    assert dtc_mod.read_dtcs(client) == []
    # ...and they do not silently reappear as the simulation advances.
    for _ in range(5):
        ecu.tick(1.0)
    assert dtc_mod.read_dtcs(client) == []


# --------------------------------------------------------------------------- #
# Live-data coherence per scenario
# --------------------------------------------------------------------------- #

def test_healthy_live_data_is_nominal():
    """CLAUDE.md: healthy vehicle — ~85-88 degC coolant, idle around 750 rpm."""
    ecu, client = make_stack("healthy")
    ecu.tick(1.0)
    assert 80 <= read_value(client, 0x01) <= 90       # coolant near 87 degC
    assert 700 <= read_value(client, 0x02) <= 800     # idle ~750 rpm
    assert read_value(client, 0x03) == pytest.approx(13.8, abs=0.5)  # battery
    assert read_value(client, 0x0E) == 0              # no misfires
    # closed-loop fuelling on a healthy warm engine
    assert read_value(client, 0x0D) == livedata.LOOP_MAP["closed"]


def test_coolant_sensor_live_shows_minus_40_failsafe():
    """Open ECT circuit reads as the implausible -40 degC failsafe value."""
    ecu, client = make_stack("coolant_sensor")
    assert read_value(client, 0x01) == -40
    # ...and stays pinned there even as the warm-up simulation ticks.
    for _ in range(10):
        ecu.tick(1.0)
    assert read_value(client, 0x01) == -40
    # Cold-reading enrichment stretches the injector pulse width past warm idle.
    assert read_value(client, 0x17) > 2.5


def test_misfire_puts_whole_count_on_cylinder_3():
    """RELEASE_NOTES.md: cylinder 3's count climbs while 1-2 and 4-8 stay 0."""
    ecu, client = make_stack("misfire_cyl3")
    total = read_value(client, 0x0E)
    assert total > 0
    assert read_value(client, 0x22) == total  # cylinder 3 carries it all
    for local_id in (0x20, 0x21, 0x23, 0x24, 0x25, 0x26, 0x27):
        assert read_value(client, local_id) == 0
    # the count climbs as the fault persists
    ecu.tick(1.0)
    assert read_value(client, 0x0E) > total


def test_misfire_cylinder_counter_saturates_at_255():
    """Per-cylinder counters are 1-byte and saturate at 255 (RELEASE_NOTES.md);
    the 2-byte total keeps counting past that."""
    ecu, client = make_stack("misfire_cyl3")
    for _ in range(20):
        ecu.tick(0.5)
    assert read_value(client, 0x0E) > 255  # 2-byte total keeps climbing
    assert read_value(client, 0x22) == 255  # 1-byte cyl-3 counter saturated


def test_misfire_idle_is_rough_and_low():
    ecu, client = make_stack("misfire_cyl3")
    ecu.tick(1.0)
    assert read_value(client, 0x02) <= 700  # dead-ish cylinder drops idle


def test_lambda_heater_forces_open_loop():
    """Cold O2 sensor -> no closed loop; O2 voltage floats at ~0.45 V bias."""
    _, client = make_stack("lambda_heater")
    assert read_value(client, 0x0D) == livedata.LOOP_MAP["open"]
    assert read_value(client, 0x07) == pytest.approx(0.45, abs=0.05)


def test_lambda_heater_blocks_only_the_o2_heater_actuator():
    scenario = get_scenario("lambda_heater")
    from gems_t4.gems.actuators import (
        ACT_AC_GRANT,
        ACT_CONDENSER_FAN,
        ACT_FUEL_PUMP,
        ACT_MIL,
        ACT_O2_HEATER,
    )
    assert scenario.blocks_actuator(ACT_O2_HEATER) is True
    for other in (ACT_MIL, ACT_FUEL_PUMP, ACT_AC_GRANT, ACT_CONDENSER_FAN):
        assert scenario.blocks_actuator(other) is False


def test_healthy_blocks_no_actuators():
    scenario = get_scenario("healthy")
    assert not any(scenario.blocks_actuator(i) for i in range(1, 6))
