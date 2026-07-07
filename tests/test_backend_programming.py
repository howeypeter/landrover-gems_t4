"""Backend facade: the Phase-5 programming/immobiliser/maps surface (no Qt)."""
from __future__ import annotations

import pytest

from gems_t4.app.backend import Backend
from gems_t4.gems.programming import ProgrammingRefused


def test_coding_read_write_via_backend():
    b = Backend("healthy")
    assert b.read_coding_text("vin_last6") == "123456"
    bk = b.backup_coding("vin_last6")
    result = b.write_coding("vin_last6", b"654321", backup=bk, confirm=lambda: True)
    assert result.ok
    assert b.read_coding_text("vin_last6") == "654321"


def test_read_only_field_refused_via_backend():
    b = Backend("healthy")
    with pytest.raises(ProgrammingRefused):
        b.write_coding("market", b"\x02", backup=b.backup_coding("market"))


def test_immobiliser_recovery_via_backend():
    b = Backend("healthy", immobilised=True)
    assert b.immobiliser_status().summary == "ENGINE IMMOBILISED"
    result = b.security_learn()
    assert result.ok
    assert b.immobiliser_status().mobilised


def test_set_immobilised_toggles_state():
    b = Backend("healthy")
    assert b.immobiliser_status().mobilised
    b.set_immobilised(True)
    assert not b.immobiliser_status().mobilised


def test_maps_exposed_via_backend():
    b = Backend("healthy")
    assert set(b.available_maps()) == {"fuel", "ignition"}
    assert b.get_map("fuel").rows == 16
