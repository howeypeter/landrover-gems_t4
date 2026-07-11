"""Connection-configuration screen — headless GUI tests.

Covers: field enablement follows the selected kind, applying a network
connection actually reroutes the backend through a live TCP server, the
setting persists to the (temp) config file, USB/network flags pre-seed the
backend in ``run()``'s precedence order, and the vehicle-id screen disables
its scenario picker in remote mode.
"""
from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6")

from gems_t4.app.backend import Backend
from gems_t4.app.server import TcpFrameServer
from gems_t4.gems.scenarios import get_scenario
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.transport.virtual import VirtualTransport


@pytest.fixture(autouse=True)
def temp_config(tmp_path, monkeypatch):
    """Point the settings file at a temp path so tests never touch $HOME."""
    path = tmp_path / "gems_t4.json"
    monkeypatch.setenv("GEMS_T4_CONFIG", str(path))
    return path


@pytest.fixture
def served_ecu(request):
    ecu = VirtualEcu(get_scenario("misfire_cyl3"))
    server = TcpFrameServer(VirtualTransport(ecu), port=0, on_exchange=ecu.tick)
    server.start_background()
    request.addfinalizer(server.stop)
    return server.address


def _make_screen(backend: Backend):
    from gems_t4.app.gui.screens.connection import ConnectionScreen

    return ConnectionScreen(backend)


def test_field_enablement_follows_kind(qtbot):
    screen = _make_screen(Backend())
    qtbot.addWidget(screen)
    screen.on_enter()

    screen._radio_virtual.setChecked(True)
    assert not screen._com_port.isEnabled()
    assert not screen._host.isEnabled()

    screen._radio_usb.setChecked(True)
    assert screen._com_port.isEnabled()
    assert not screen._host.isEnabled()

    screen._radio_network.setChecked(True)
    assert not screen._com_port.isEnabled()
    assert screen._host.isEnabled()
    assert screen._tcp_port.isEnabled()
    assert screen._allow_writes.isEnabled()


def test_apply_network_connection_reroutes_backend(qtbot, served_ecu, temp_config):
    host, port = served_ecu
    backend = Backend()
    screen = _make_screen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    screen._radio_network.setChecked(True)
    screen._host.setText(host)
    screen._tcp_port.setText(str(port))
    screen.on_tick()  # instant mode (conftest) -> runs inline

    assert backend.is_remote and backend.is_wireless
    assert backend.connected
    # The remote (served) ECU's scenario shows through, not a local fake.
    codes = {d.code for d in backend.read_dtcs()}
    assert "P0303" in codes
    # Setting persisted for the next session.
    saved = json.loads(temp_config.read_text(encoding="utf-8"))
    assert saved["kind"] == "network"
    assert saved["host"] == host
    assert saved["tcp_port"] == port
    backend.disconnect()


def test_apply_virtual_restores_local_ecu(qtbot, served_ecu):
    host, port = served_ecu
    backend = Backend()
    backend.set_connection("network", host=host, tcp_port=port)
    screen = _make_screen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    screen._radio_virtual.setChecked(True)
    screen.on_tick()
    assert not backend.is_remote
    assert backend.read_dtcs() == []  # local healthy fake again
    backend.disconnect()


# --------------------------------------------------------------------------- #
# "Test" action (cross button) — tests the ACTIVE connection, changes nothing
# --------------------------------------------------------------------------- #

def test_cross_is_labeled_test_and_present_in_nav():
    screen = _make_screen(Backend())
    assert "cross" in screen.nav_buttons()
    assert screen.cross_label() == "Test"


def test_on_cross_tests_the_active_virtual_connection(qtbot):
    backend = Backend()
    screen = _make_screen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    screen.on_cross()  # instant mode -> runs inline

    assert "OK" in screen._test_result.text()
    assert "Virtual ECU" in screen._test_result.text()
    assert backend.connected  # test_connection() opened the session


def test_on_cross_tests_active_network_connection_and_measures_latency(
    qtbot, served_ecu
):
    host, port = served_ecu
    backend = Backend()
    backend.set_connection("network", host=host, tcp_port=port)
    screen = _make_screen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    screen.on_cross()

    text = screen._test_result.text()
    assert "OK" in text
    assert "replies" in text  # TcpTransport.ping() -> measured round trip
    backend.disconnect()


def test_on_cross_does_not_persist_or_change_the_form(qtbot, served_ecu, temp_config):
    """Test is read-only: no config write, no reroute of an unrelated backend."""
    host, port = served_ecu
    backend = Backend()  # stays virtual; screen fields never touch it
    screen = _make_screen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()

    screen._radio_network.setChecked(True)
    screen._host.setText(host)
    screen._tcp_port.setText(str(port))
    screen.on_cross()  # tests the ACTIVE (virtual) connection, ignores the form

    assert not backend.is_remote
    assert not temp_config.exists()
    backend.disconnect()


def test_bad_endpoint_rolls_back_to_previous_connection(qtbot):
    """A failed connection test must NOT strand the backend on the dead
    endpoint — the previous (working) connection is restored."""
    backend = Backend()
    backend.connect()  # start on a live virtual session
    screen = _make_screen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()
    statuses: list[str] = []
    screen.status.connect(statuses.append)

    screen._radio_network.setChecked(True)
    screen._host.setText("127.0.0.1")
    screen._tcp_port.setText("1")  # nothing listens there
    screen.on_tick()
    assert any("Connection failed" in s for s in statuses)
    # Rolled back: still the virtual ECU, and it still works.
    assert not backend.is_remote
    assert backend.connection_label == "Virtual ECU"
    assert backend.read_dtcs() == []
    backend.disconnect()


def test_missing_fields_prompt_instead_of_apply(qtbot):
    backend = Backend()
    screen = _make_screen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()
    statuses: list[str] = []
    screen.status.connect(statuses.append)

    screen._radio_usb.setChecked(True)
    screen._com_port.setText("")
    screen.on_tick()
    assert any("COM port" in s for s in statuses)
    assert not backend.is_remote


def test_vehicle_id_scenario_picker_disabled_in_remote_mode(qtbot, served_ecu):
    from gems_t4.app.gui.screens.vehicle_id import VehicleIdScreen

    host, port = served_ecu
    backend = Backend()
    backend.set_connection("network", host=host, tcp_port=port)
    screen = VehicleIdScreen(backend)
    qtbot.addWidget(screen)
    screen.on_enter()
    assert not screen._scenario.isEnabled()

    backend.set_connection("virtual")
    screen.on_enter()
    assert screen._scenario.isEnabled()
    backend.disconnect()


def test_usb_kind_builds_pico_transport():
    """The USB branch must actually construct a PicoAdapterTransport factory
    (no test previously executed set_connection('usb') with a real value)."""
    from gems_t4.transport.pico import PicoAdapterTransport

    backend = Backend()
    backend.set_connection("usb", com_port="COM9")
    assert backend.is_remote
    assert not backend.is_wireless  # USB is the wired path — no write gate
    assert "COM9" in backend.connection_label
    transport = backend._transport_factory()
    assert isinstance(transport, PicoAdapterTransport)


# -- apply_startup_connection: the flags > saved config > virtual precedence --#

def _startup(backend, **kwargs):
    from gems_t4.app.gui.app import apply_startup_connection

    apply_startup_connection(backend, **kwargs)


def test_startup_flags_beat_saved_config(served_ecu, temp_config):
    from gems_t4.app import config as _config

    host, port = served_ecu
    _config.save_config(_config.ConnectionConfig(kind="usb", com_port="COM7"))
    backend = Backend()
    _startup(backend, connect=f"{host}:{port}")
    assert backend.is_wireless  # the flag won, not the saved USB config
    codes = {d.code for d in backend.read_dtcs()}
    assert "P0303" in codes
    backend.disconnect()


def test_startup_port_flag_selects_usb(temp_config):
    backend = Backend()
    _startup(backend, port="COM5")
    assert backend.is_remote and not backend.is_wireless
    assert "COM5" in backend.connection_label


def test_startup_saved_network_config_applies_with_allow_writes(
    served_ecu, temp_config
):
    """run()'s no-flag path must forward every saved field — allow_writes
    included (dropping it would silently re-enable the write gate)."""
    from gems_t4.app import config as _config

    host, port = served_ecu
    _config.save_config(
        _config.ConnectionConfig(
            kind="network", host=host, tcp_port=port, allow_writes=True
        )
    )
    backend = Backend()
    _startup(backend)
    assert backend.is_wireless
    assert "writes enabled" in backend.connection_label
    codes = {d.code for d in backend.read_dtcs()}
    assert "P0303" in codes
    backend.disconnect()


def test_startup_bad_saved_config_falls_back_to_virtual(temp_config):
    """A corrupt saved config must never stop the GUI from starting."""
    temp_config.write_text(
        '{"kind": "network", "host": null}', encoding="utf-8"
    )
    backend = Backend()
    _startup(backend)  # must not raise
    assert not backend.is_remote
    assert backend.read_dtcs() == []
    backend.disconnect()


def test_load_config_rejects_non_bool_allow_writes(temp_config):
    """A truthy non-bool (e.g. the JSON string "false") must not enable
    writes — invalid types yield the safe defaults."""
    from gems_t4.app import config as _config

    temp_config.write_text(
        '{"kind": "network", "host": "10.0.0.1", "allow_writes": "false"}',
        encoding="utf-8",
    )
    cfg = _config.load_config()
    assert cfg.allow_writes is False
    assert cfg.kind == "virtual"  # whole config fell back to defaults
