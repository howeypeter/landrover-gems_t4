"""The Backend ECU audit log — one record for every front-end (CLI/GUI/web).

These exercise the shared Backend directly (virtual ECU), which is exactly the
chokepoint all three front-ends share, so passing here means writes/reads are
captured no matter which UI issued them.
"""
from __future__ import annotations

import json

import pytest

from gems_t4.app import audit as _audit
from gems_t4.app.backend import Backend


@pytest.fixture
def audit_lines(tmp_path, monkeypatch):
    """Point the audit log at a tmp file and return a reader for its JSON lines."""
    logfile = tmp_path / "audit.log"
    monkeypatch.setenv("GEMS_T4_AUDIT_LOG", str(logfile))
    _audit._reset_for_tests()

    def read() -> list[dict]:
        if not logfile.exists():
            return []
        return [json.loads(ln) for ln in logfile.read_text("utf-8").splitlines() if ln.strip()]

    yield read
    _audit._reset_for_tests()


def test_read_dtcs_is_audited(audit_lines):
    be = Backend("misfire_cyl3")
    be.connect()
    be.read_dtcs()
    events = [e for e in audit_lines() if e["op"] == "read_dtcs"]
    assert events, "read_dtcs should log an audit event"
    e = events[-1]
    assert e["kind"] == "read"
    assert e["connection_kind"] == "virtual"
    assert e["scenario"] == "misfire_cyl3"
    assert e["count"] == len(e["codes"]) and e["count"] > 0  # misfire has codes


def test_coding_write_records_before_and_after(audit_lines):
    be = Backend()
    be.connect()
    field = "dealer_id"
    new = be.encode_coding_text(field, "AB12")
    bk = be.backup_coding(field)
    be.write_coding(field, new, backup=bk, confirm=lambda: True)

    writes = [e for e in audit_lines() if e["op"] == "write_coding"]
    assert writes, "write_coding should log an audit event"
    e = writes[-1]
    assert e["kind"] == "write" and e["field"] == field
    assert e["after"] == new.hex()
    assert e["before"] == bk.data.hex()       # read-before-write captured
    assert e["ok"] is True


def test_clear_dtcs_is_audited(audit_lines):
    be = Backend("misfire_cyl3")
    be.connect()
    be.clear_dtcs()
    events = [e for e in audit_lines() if e["op"] == "clear_dtcs"]
    assert events and events[-1]["kind"] == "write" and events[-1]["ok"] is True


def test_live_data_is_not_audited(audit_lines):
    """High-rate live-data polling must NOT flood the audit log."""
    be = Backend()
    be.connect()
    for _ in range(5):
        be.read_live([0x00])
    assert not [e for e in audit_lines() if e["op"] == "read_live"]


def test_audit_never_raises_on_unwritable_path(tmp_path, monkeypatch):
    # A path whose parent is a FILE can't be mkdir'd - audit must degrade
    # (stderr fallback), never blow up the tool.
    afile = tmp_path / "afile"
    afile.write_text("x")
    monkeypatch.setenv("GEMS_T4_AUDIT_LOG", str(afile / "sub" / "x.log"))
    _audit._reset_for_tests()
    try:
        _audit.audit({"op": "smoke", "kind": "read"})  # must not raise
    finally:
        _audit._reset_for_tests()
