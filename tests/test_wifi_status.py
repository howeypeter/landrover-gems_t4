"""Parsing the Pico's wifi-status reply (new MAC-bearing + legacy formats)."""
from __future__ import annotations

from gems_t4.transport.wifi_status import parse_wifi_status

MAC = "28:CD:C1:0A:1B:2C"


def test_connected_with_mac():
    s = parse_wifi_status(f"connected 192.168.1.138 {MAC} MyNet")
    assert s.state == "connected"
    assert s.ip == "192.168.1.138"
    assert s.mac == MAC
    assert s.ssid == "MyNet"


def test_connected_ssid_with_spaces():
    s = parse_wifi_status(f"connected 192.168.1.138 {MAC} My Home 2.4G")
    assert s.ip == "192.168.1.138" and s.mac == MAC
    assert s.ssid == "My Home 2.4G"          # SSID (last) keeps its spaces


def test_offline_with_mac():
    s = parse_wifi_status(f"offline {MAC} (creds set: MyNet)")
    assert s.state == "offline" and s.mac == MAC and s.ssid == "MyNet"


def test_no_creds_with_mac():
    s = parse_wifi_status(f"no-creds {MAC}")
    assert s.state == "no-creds" and s.mac == MAC and s.ssid is None


def test_legacy_connected_without_mac():
    s = parse_wifi_status("connected 192.168.1.138 MyNet")
    assert s.state == "connected" and s.ip == "192.168.1.138"
    assert s.mac is None and s.ssid == "MyNet"


def test_legacy_offline_and_no_creds():
    assert parse_wifi_status("offline (creds set: MyNet)").ssid == "MyNet"
    assert parse_wifi_status("no-creds").state == "no-creds"


def test_summary_mentions_mac():
    out = parse_wifi_status(f"connected 192.168.1.138 {MAC} MyNet").summary()
    assert "192.168.1.138" in out and MAC in out and "MyNet" in out
