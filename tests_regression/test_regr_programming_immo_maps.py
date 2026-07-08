"""Independent regression tests: gated coding writes, immobiliser Security-Learn,
and the read-only EPROM map lookalike.

Written from the frozen contracts (INTERFACES.md "gems/programming.py — coding
settings map ... gated write_coding(client, field, value, *, backup, verify=True)
... the safety gates (backup+verify+confirm)"; GUI_INTERFACES.md "Phase 5 —
programming / immobiliser / maps") and CLAUDE.md — NOT from the existing tests/.
"""
from __future__ import annotations

import dataclasses

import pytest

from gems_t4.gems import immobiliser, maps, programming
from gems_t4.gems.scenarios import get_scenario
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.protocol.client import KwpClient
from gems_t4.protocol.messages import NRC
from gems_t4.transport.virtual import VirtualTransport


def make_client(scenario: str = "healthy", *, immobilised: bool = False):
    """Build the documented off-car stack: VirtualEcu -> VirtualTransport -> KwpClient."""
    ecu = VirtualEcu(get_scenario(scenario), immobilised=immobilised)
    client = KwpClient(VirtualTransport(ecu))
    client.connect()
    client.start_session()
    return client, ecu


# --------------------------------------------------------------------------- #
# Coding block shape (CLAUDE.md / README: writable identity fields VIN last-6,
# dealer id, 4.0/4.6 select, transmission, build code; read-only market + part no.)
# --------------------------------------------------------------------------- #
def test_coding_fields_contract():
    fields = programming.CODING_FIELDS
    assert set(fields) == {
        "vin_last6", "dealer_id", "engine", "transmission",
        "build_code", "market", "part_number",
    }
    writable = {k for k, f in fields.items() if f.writable}
    assert writable == {"vin_last6", "dealer_id", "engine", "transmission", "build_code"}
    assert not fields["market"].writable
    assert not fields["part_number"].writable
    # local ids must be unique (they address distinct ECU records)
    ids = [f.local_id for f in fields.values()]
    assert len(ids) == len(set(ids))
    # dict is keyed by each field's own key
    assert all(k == f.key for k, f in fields.items())


def test_codec_ascii_and_hex_roundtrip():
    # VIN last-6 is ASCII (README: "ASCII for vin/part, else hex")
    assert programming.encode_field("vin_last6", "654321") == b"654321"
    assert programming.decode_field("vin_last6", b"123456") == "123456"
    # non-text fields are hex
    assert programming.encode_field("dealer_id", "00 01") == b"\x00\x01"
    assert programming.decode_field("dealer_id", b"\x00\x01") == "00 01"
    # round trips both ways
    for field, raw in [("part_number", b"ERR7109"), ("engine", b"\x46")]:
        assert programming.encode_field(field, programming.decode_field(field, raw)) == raw


def test_codec_rejects_malformed_hex():
    with pytest.raises(ValueError):
        programming.encode_field("dealer_id", "not-hex")


def test_read_coding_defaults():
    client, _ = make_client()
    assert programming.read_coding(client, "vin_last6") == b"123456"
    assert programming.read_coding(client, "part_number") == b"ERR7109"
    assert programming.decode_field(
        "part_number", programming.read_coding(client, "part_number")
    ) == "ERR7109"


# --------------------------------------------------------------------------- #
# The gated write path (backup + confirm + write + verify)
# --------------------------------------------------------------------------- #
def test_backup_is_a_verified_read_before_write_snapshot():
    client, _ = make_client()
    b = programming.backup(client, "vin_last6")
    assert b.local_id == programming.CODING_FIELDS["vin_last6"].local_id
    assert b.data == b"123456"
    # a snapshot must be immutable
    with pytest.raises(dataclasses.FrozenInstanceError):
        b.data = b"tampered"  # type: ignore[misc]


def test_gated_write_happy_path_roundtrips():
    client, _ = make_client()
    confirmed = []
    b = programming.backup(client, "vin_last6")
    result = programming.write_coding(
        client, "vin_last6", b"654321",
        backup=b, confirm=lambda: confirmed.append(True) or True,
    )
    assert result.ok
    assert result.message == "write verified"
    assert result.backup is b
    assert confirmed == [True], "the operator-confirm gate must run exactly once"
    # write-then-read shows the new value
    assert programming.read_coding(client, "vin_last6") == b"654321"


def test_write_without_backup_is_refused():
    client, _ = make_client()
    with pytest.raises(programming.ProgrammingRefused):
        programming.write_coding(client, "vin_last6", b"654321", backup=None)
    assert programming.read_coding(client, "vin_last6") == b"123456"


def test_write_with_wrong_field_backup_is_refused():
    client, _ = make_client()
    wrong = programming.backup(client, "dealer_id")
    with pytest.raises(programming.ProgrammingRefused):
        programming.write_coding(client, "vin_last6", b"654321", backup=wrong)
    assert programming.read_coding(client, "vin_last6") == b"123456"


def test_write_not_confirmed_is_refused():
    client, _ = make_client()
    b = programming.backup(client, "vin_last6")
    with pytest.raises(programming.ProgrammingRefused):
        programming.write_coding(client, "vin_last6", b"654321", backup=b, confirm=lambda: False)
    assert programming.read_coding(client, "vin_last6") == b"123456"


def test_write_readonly_field_is_refused():
    client, _ = make_client()
    b = programming.backup(client, "market")  # reading it is fine
    with pytest.raises(programming.ProgrammingRefused):
        programming.write_coding(client, "market", b"\x02", backup=b, confirm=lambda: True)
    assert programming.read_coding(client, "market") == b"\x01"


def test_write_unknown_field_raises_keyerror():
    client, _ = make_client()
    with pytest.raises(KeyError):
        programming.write_coding(client, "warp_drive", b"\x01", backup=None)


def test_verify_after_write_catches_a_failed_write():
    """The verify gate: if the read-back differs, the result is not-ok and points
    the operator at the backup (INTERFACES.md: gates are backup+verify+confirm)."""

    class StubClient:
        """A client whose writes silently don't stick (worst-case ECU)."""

        def __init__(self) -> None:
            self.stored = b"123456"

        def read_data_by_local_id(self, local_id: int) -> bytes:
            return self.stored

        def write_data_by_local_id(self, local_id: int, value: bytes):
            return None  # write is lost

    stub = StubClient()
    b = programming.backup(stub, "vin_last6")  # type: ignore[arg-type]
    result = programming.write_coding(
        stub, "vin_last6", b"654321", backup=b, confirm=lambda: True,  # type: ignore[arg-type]
    )
    assert not result.ok
    assert "verify FAILED" in result.message
    assert result.backup is b


# --------------------------------------------------------------------------- #
# Immobiliser / Security-Learn (the ONE genuine over-the-wire GEMS write)
# --------------------------------------------------------------------------- #
def test_immobiliser_mobilised_by_default():
    client, _ = make_client()
    status = immobiliser.read_status(client)
    assert status.mobilised
    assert not status.learn_mode
    assert status.summary == "MOBILISED - engine enabled"


def test_immobilised_ecu_reports_engine_immobilised():
    client, _ = make_client(immobilised=True)
    status = immobiliser.read_status(client)
    assert not status.mobilised
    assert status.summary == "ENGINE IMMOBILISED"


def test_security_learn_resyncs_an_immobilised_ecu():
    client, _ = make_client(immobilised=True)
    progress: list[str] = []
    result = immobiliser.security_learn(client, on_progress=progress.append)
    assert result.ok
    assert "re-synced" in result.message
    assert result.steps, "the step log must be populated for UI display"
    assert progress == result.steps, "on_progress must see the same steps live"
    # and the ECU now reports mobilised
    assert immobiliser.read_status(client).mobilised


def test_enter_learn_without_security_access_is_denied():
    """$31 routine 0x01 needs a $27 unlock first (INTERFACES.md: 'needs 0x27
    unlock, else SECURITY_ACCESS_DENIED')."""
    client, _ = make_client(immobilised=True)
    resp = client.start_routine(immobiliser.ROUTINE_ENTER_LEARN)
    assert resp.is_negative
    assert resp.nrc == NRC.SECURITY_ACCESS_DENIED


def test_submit_code_outside_learn_mode_is_sequence_error():
    """$31 routine 0x02 needs learn mode (INTERFACES.md: 'needs learn mode, else
    REQUEST_SEQUENCE_ERROR')."""
    client, _ = make_client(immobilised=True)
    resp = client.start_routine(immobiliser.ROUTINE_SUBMIT_CODE, b"\xa5\xa5")
    assert resp.is_negative
    assert resp.nrc == NRC.REQUEST_SEQUENCE_ERROR


def test_security_learn_with_bad_key_fails_and_stores_nothing():
    client, _ = make_client(immobilised=True)
    result = immobiliser.security_learn(client, key_fn=lambda seed: (seed + 1) & 0xFFFF)
    assert not result.ok
    assert "Security access denied" in result.message
    # nothing stored: still immobilised
    assert not immobiliser.read_status(client).mobilised


def test_learn_mode_status_summary():
    from gems_t4.protocol.security import compute_key

    client, _ = make_client(immobilised=True)
    client.security_access(compute_key)
    resp = client.start_routine(immobiliser.ROUTINE_ENTER_LEARN)
    assert not resp.is_negative
    status = immobiliser.read_status(client)
    assert status.learn_mode
    assert status.summary == "SECURITY-LEARN MODE - awaiting BeCM code"


# --------------------------------------------------------------------------- #
# Maps — the read-only chip-swap lookalike
# --------------------------------------------------------------------------- #
def test_map_registry_and_dimensions():
    assert list(maps.MAPS) == ["fuel", "ignition"]
    for table in maps.MAPS.values():
        assert table.rows == 16
        assert table.cols == 16
        assert len(table.rpm_axis) == 16
        assert len(table.load_axis) == 16
        # cell accessor agrees with the raw grid
        assert table.cell(0, 0) == table.cells[0][0]
        assert table.cell(15, 15) == table.cells[15][15]


def test_map_axes_are_plausible():
    assert maps.RPM_AXIS[0] == 500
    assert maps.RPM_AXIS[-1] == 5750
    assert list(maps.RPM_AXIS) == sorted(maps.RPM_AXIS)
    assert maps.LOAD_AXIS[-1] == 100
    assert list(maps.LOAD_AXIS) == sorted(maps.LOAD_AXIS)


def test_eprom_chip_facts():
    """CLAUDE.md: 'two socketed UV-EPROMs (27C512 fuel maps, 27C1001 ignition + code)'."""
    assert maps.FUEL_EPROM.part == "27C512"
    assert maps.FUEL_EPROM.size_kb == 64
    assert "fuel" in maps.FUEL_EPROM.holds.lower()
    assert maps.IGNITION_EPROM.part == "27C1001"
    assert maps.IGNITION_EPROM.size_kb == 128
    assert "ignition" in maps.IGNITION_EPROM.holds.lower()
    note = maps.CHIP_SWAP_NOTE
    assert "27C512" in note and "27C1001" in note
    assert "no K-line reflash" in note
    assert "read-only" in note


def test_maps_are_immutable_and_have_no_write_api():
    """There is no over-the-wire map write for GEMS — the module must expose no
    write/burn/flash entry point, and the tables themselves must be frozen."""
    forbidden = [
        name for name in dir(maps)
        if not name.startswith("_")
        and any(word in name.lower() for word in ("write", "burn", "flash", "program"))
    ]
    assert forbidden == [], f"maps module unexpectedly exposes write-ish API: {forbidden}"

    table = maps.MAPS["fuel"]
    with pytest.raises(dataclasses.FrozenInstanceError):
        table.cells = ()  # type: ignore[misc]
    assert isinstance(table.cells, tuple)
    assert all(isinstance(row, tuple) for row in table.cells)
    with pytest.raises(TypeError):
        table.cells[0][0] = 99.0  # type: ignore[index]


def test_map_surfaces_are_physically_plausible():
    fuel = maps.MAPS["fuel"]
    ign = maps.MAPS["ignition"]
    # more load -> more fuel (at any rpm column)
    assert fuel.cell(15, 0) > fuel.cell(0, 0)
    assert fuel.cell(15, 15) > fuel.cell(0, 15)
    # more rpm -> more spark advance (at light load)
    assert ign.cell(0, 15) > ign.cell(0, 0)
    # advance is clamped to a sane floor
    assert min(min(row) for row in ign.cells) >= 4.0
    # units per GUI_INTERFACES map contract
    assert fuel.unit == "ms"
    assert ign.unit == "deg BTDC"
