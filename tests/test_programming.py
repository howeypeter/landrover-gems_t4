"""Gated coding writes (gems/programming.py) over the virtual ECU."""
from __future__ import annotations

import pytest

from gems_t4.gems import programming as prog
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.protocol.client import KwpClient
from gems_t4.transport.virtual import VirtualTransport


def make_client() -> KwpClient:
    client = KwpClient(VirtualTransport(VirtualEcu()))
    client.connect()
    client.start_session()
    return client


def test_read_and_write_coding_round_trip():
    c = make_client()
    assert prog.read_coding(c, "vin_last6") == b"123456"
    bk = prog.backup(c, "vin_last6")
    result = prog.write_coding(c, "vin_last6", b"654321", backup=bk, confirm=lambda: True)
    assert result.ok
    assert prog.read_coding(c, "vin_last6") == b"654321"


def test_write_read_only_field_refused():
    c = make_client()
    with pytest.raises(prog.ProgrammingRefused):
        prog.write_coding(c, "market", b"\x02", backup=prog.backup(c, "market"))


def test_write_without_backup_refused():
    c = make_client()
    with pytest.raises(prog.ProgrammingRefused):
        prog.write_coding(c, "vin_last6", b"999999", backup=None)


def test_write_not_confirmed_refused():
    c = make_client()
    bk = prog.backup(c, "vin_last6")
    with pytest.raises(prog.ProgrammingRefused):
        prog.write_coding(c, "vin_last6", b"000000", backup=bk, confirm=lambda: False)


def test_field_codecs():
    assert prog.decode_field("vin_last6", b"123456") == "123456"
    assert prog.encode_field("vin_last6", "ABCDEF") == b"ABCDEF"
    # non-text field round-trips as hex
    assert prog.decode_field("engine", b"\x46") == "46"
    assert prog.encode_field("engine", "46") == b"\x46"
