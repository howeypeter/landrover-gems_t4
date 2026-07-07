"""Headless tests for the custom gauge widgets and their specs."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6")

from gems_t4.app.gui.gauge_specs import (
    GAUGE_SPECS,
    STYLE_BAR,
    STYLE_DIAL,
    STYLE_LCD,
    spec_for,
)
from gems_t4.app.gui.widgets import BarGauge, DialGauge, LcdReadout, build_gauge


def test_set_value_clamps_to_scale(qtbot):
    g = DialGauge(spec_for(0x02))  # rpm 0..7000
    qtbot.addWidget(g)
    g.set_value(99999)
    assert g.value() == 7000
    g.set_value(-100)
    assert g.value() == 0
    g.set_value(3000)
    assert g.value() == 3000


def test_fraction_midscale(qtbot):
    g = DialGauge(spec_for(0x02))
    qtbot.addWidget(g)
    g.set_value(3500)  # half of 0..7000
    assert abs(g._fraction() - 0.5) < 1e-6


def test_non_numeric_value_falls_back(qtbot):
    g = DialGauge(spec_for(0x02))
    qtbot.addWidget(g)
    g.set_value("not a number")
    assert g.value() == g.spec.vmin


def test_build_gauge_dispatches_by_style(qtbot):
    assert isinstance(build_gauge(spec_for(0x02)), DialGauge)   # dial
    assert isinstance(build_gauge(spec_for(0x04)), BarGauge)    # throttle -> bar
    assert isinstance(build_gauge(spec_for(0x0D)), LcdReadout)  # loop -> lcd


def test_specs_have_sane_ranges():
    for spec in GAUGE_SPECS.values():
        assert spec.vmax > spec.vmin
        assert spec.style in {STYLE_DIAL, STYLE_BAR, STYLE_LCD}
        if spec.redline is not None:
            assert spec.vmin <= spec.redline <= spec.vmax


def test_widgets_paint_without_error(qtbot):
    # grab() forces a paintEvent; catches QPainter mistakes even headless.
    for lid in (0x01, 0x04, 0x0D):
        g = build_gauge(spec_for(lid))
        qtbot.addWidget(g)
        g.resize(170, 150)
        g.set_value(spec_for(lid).vmax)
        assert not g.grab().isNull()
