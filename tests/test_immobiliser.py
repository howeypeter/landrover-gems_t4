"""Immobiliser Security-Learn ($31 routines) over the virtual ECU."""
from __future__ import annotations

from gems_t4.gems import immobiliser as immo
from gems_t4.gems.virtual_ecu import VirtualEcu
from gems_t4.protocol.messages import NRC
from gems_t4.protocol.client import KwpClient
from gems_t4.transport.virtual import VirtualTransport


def make_client(*, immobilised: bool = False) -> KwpClient:
    client = KwpClient(VirtualTransport(VirtualEcu(immobilised=immobilised)))
    client.connect()
    client.start_session()
    return client


def test_status_mobilised_by_default():
    st = immo.read_status(make_client())
    assert st.mobilised and not st.learn_mode
    assert st.summary.startswith("MOBILISED")


def test_immobilised_start_reports_engine_immobilised():
    st = immo.read_status(make_client(immobilised=True))
    assert not st.mobilised
    assert st.summary == "ENGINE IMMOBILISED"


def test_enter_learn_requires_security_access():
    c = make_client(immobilised=True)
    resp = c.start_routine(immo.ROUTINE_ENTER_LEARN)
    assert resp.is_negative and resp.nrc == NRC.SECURITY_ACCESS_DENIED


def test_submit_code_out_of_sequence_rejected():
    # Submitting a code without first entering learn mode must be rejected.
    c = make_client()
    resp = c.start_routine(immo.ROUTINE_SUBMIT_CODE, b"\xA5\xA5")
    assert resp.is_negative and resp.nrc == NRC.REQUEST_SEQUENCE_ERROR


def test_full_security_learn_recovers_immobilised_ecu():
    c = make_client(immobilised=True)
    progress: list[str] = []
    result = immo.security_learn(c, on_progress=progress.append)
    assert result.ok
    assert progress == result.steps and len(result.steps) >= 4
    assert immo.read_status(c).mobilised
