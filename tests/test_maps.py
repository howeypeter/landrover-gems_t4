"""GEMS map (chip-swap lookalike) data integrity."""
from __future__ import annotations

from gems_t4.gems import maps


def test_two_maps_are_16x16_with_axes():
    for table in (maps.FUEL_MAP, maps.IGNITION_MAP):
        assert table.rows == 16 and table.cols == 16
        assert len(table.rpm_axis) == 16
        assert len(table.load_axis) == 16


def test_map_registry():
    assert set(maps.MAPS) == {"fuel", "ignition"}


def test_eprom_chip_facts():
    assert maps.FUEL_EPROM.part == "27C512" and maps.FUEL_EPROM.size_kb == 64
    assert maps.IGNITION_EPROM.part == "27C1001" and maps.IGNITION_EPROM.size_kb == 128


def test_fuel_increases_with_load():
    # Injector pulse width should rise from low load to high load at a fixed rpm.
    fuel = maps.FUEL_MAP
    assert fuel.cell(15, 0) > fuel.cell(0, 0)


def test_ignition_values_are_plausible():
    ign = maps.IGNITION_MAP
    flat = [c for row in ign.cells for c in row]
    assert all(0 <= v <= 60 for v in flat)  # sane spark-advance range
