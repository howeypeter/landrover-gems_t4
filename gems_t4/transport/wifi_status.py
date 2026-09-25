"""Parse the Pico firmware's ``wifi-status`` reply into structured fields.

Single source of truth for the format, shared by the CLI and GUI (the web
front-end has its own small parser in TypeScript). Firmware >= 3.1.0 always
includes the MAC; the SSID is LAST because it can contain spaces, with the MAC
(fixed 17 chars, no spaces) before it so the split stays unambiguous::

    connected <ip> <mac> <ssid>
    offline <mac> (creds set: <ssid>)
    no-creds <mac>

Older firmware (no MAC) is still parsed::

    connected <ip> <ssid>
    offline (creds set: <ssid>)
    no-creds
"""
from __future__ import annotations

import re
from dataclasses import dataclass

_MAC = r"[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}"


@dataclass(frozen=True)
class WifiStatus:
    state: str                      # connected | offline | no-creds | unknown
    ip: str | None = None
    mac: str | None = None
    ssid: str | None = None
    raw: str = ""

    def summary(self) -> str:
        """A human line for the CLI/GUI readout."""
        if self.state == "connected":
            bits = [f"WiFi connected - IP {self.ip or '?'}"]
            if self.ssid:
                bits.append(f"SSID '{self.ssid}'")
            if self.mac:
                bits.append(f"MAC {self.mac}")
            return ", ".join(bits)
        if self.state == "offline":
            s = "WiFi offline"
            if self.ssid:
                s += f" - creds set for SSID '{self.ssid}' (not joined yet)"
            if self.mac:
                s += f" [MAC {self.mac}]"
            return s
        if self.state == "no-creds":
            s = "WiFi: no credentials stored on the Pico yet"
            if self.mac:
                s += f" [MAC {self.mac}]"
            return s
        return f"WiFi: {self.raw}"


def parse_wifi_status(s: str) -> WifiStatus:
    raw = s or ""
    t = raw.strip()

    m = re.match(rf"^connected (\S+)(?: ({_MAC}))?(?: (.*))?$", t)
    if m:
        ssid = m.group(3)
        return WifiStatus("connected", ip=m.group(1), mac=m.group(2),
                          ssid=(ssid.strip() if ssid else None), raw=raw)

    if t.startswith("offline"):
        mac_m = re.search(_MAC, t)
        ssid_m = re.search(r"creds set:\s*(.+?)\)?\s*$", t)
        return WifiStatus("offline",
                          mac=(mac_m.group(0) if mac_m else None),
                          ssid=(ssid_m.group(1).strip() if ssid_m else None),
                          raw=raw)

    if t.startswith("no-creds"):
        mac_m = re.search(_MAC, t)
        return WifiStatus("no-creds", mac=(mac_m.group(0) if mac_m else None), raw=raw)

    return WifiStatus("unknown", raw=raw)
