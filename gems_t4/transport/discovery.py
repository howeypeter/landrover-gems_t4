"""Locate the Pico adapter's serial port automatically.

The Bluetooth (SPP) firmware pairs as a Windows *virtual COM port*, but that
COM number is not fixed — re-pairing (which a firmware re-flash forces) can
change it. Rather than hard-code ``PORT = "COMx"``, these helpers find the port
by the Bluetooth device name (default ``gems-pico``), and can fall back to a
USB-connected Pico.

How the match works on Windows (verified against real ``pyserial`` +
``Get-PnpDevice`` output):

* The device ``gems-pico`` appears as a Bluetooth PnP entry whose InstanceId is
  ``BTHENUM\\DEV_<12-hex-MAC>\\...`` — that gives the MAC.
* Its **outgoing** SPP COM port has an hwid ending ``...&<MAC>_C........`` (the
  *incoming*/local server port uses an all-zero MAC and no ``_C`` suffix — never
  use it).

So we resolve name -> MAC, then pick the COM whose hwid carries that MAC.
Everything degrades gracefully off-Windows / when nothing is found: the
resolvers return ``None`` or raise :class:`PortNotFound` with a helpful message.
"""
from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass

try:  # pyserial is a hard dep of the real transports, but keep import defensive
    from serial.tools import list_ports
except Exception:  # pragma: no cover - only if pyserial missing
    list_ports = None  # type: ignore[assignment]

DEFAULT_BT_NAME = "gems-pico"
_PICO_USB_VIDS = ("2E8A",)  # Raspberry Pi (RP2040/RP2350) USB-CDC vendor id

_MAC_IN_HWID = re.compile(r"&([0-9A-Fa-f]{12})_")          # ...&88A29EED70D0_C000...
_MAC_IN_DEVID = re.compile(r"DEV_([0-9A-Fa-f]{12})")        # BTHENUM\DEV_88A29EED70D0\...
_ZERO_MAC = "000000000000"


class PortNotFound(RuntimeError):
    """Raised when no matching serial port can be located."""


@dataclass(frozen=True)
class SppPort:
    device: str          # "COM5"
    mac: str             # "88A29EED70D0" (upper hex, no separators)
    outgoing: bool       # True for the port that connects TO the device


def _norm_mac(mac: str) -> str:
    return re.sub(r"[^0-9A-Fa-f]", "", mac).upper()


def list_bt_spp_ports() -> list[SppPort]:
    """All Bluetooth "Standard Serial over Bluetooth link" COM ports."""
    if list_ports is None:
        return []
    out: list[SppPort] = []
    for p in list_ports.comports():
        hwid = (p.hwid or "").upper()
        if "BTHENUM" not in hwid:
            continue
        m = _MAC_IN_HWID.search(hwid)
        mac = _norm_mac(m.group(1)) if m else ""
        outgoing = bool(mac) and mac != _ZERO_MAC and "_C" in hwid
        out.append(SppPort(device=p.device, mac=mac, outgoing=outgoing))
    return out


def bt_mac_for_name(name: str = DEFAULT_BT_NAME) -> str | None:
    """Resolve a paired Bluetooth device *name* to its MAC (Windows only).

    Uses ``Get-PnpDevice`` (no admin needed). Returns an upper-hex MAC with no
    separators, or ``None`` if it can't be determined (not Windows, PowerShell
    missing, or the device isn't paired).
    """
    if not sys.platform.startswith("win"):
        return None
    ps = (
        "Get-PnpDevice -Class Bluetooth -ErrorAction SilentlyContinue | "
        f"Where-Object {{ $_.FriendlyName -eq '{name}' }} | "
        "Select-Object -ExpandProperty InstanceId"
    )
    try:
        res = subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
            capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    for line in res.stdout.splitlines():
        m = _MAC_IN_DEVID.search(line.strip().upper())
        if m:
            return _norm_mac(m.group(1))
    return None


def find_gems_pico_port(name: str = DEFAULT_BT_NAME) -> str:
    """Return the COM port for the paired ``gems-pico`` Bluetooth adapter.

    Strategy: resolve the device MAC by name and return the *outgoing* SPP port
    carrying that MAC. If the name can't be resolved (e.g. PowerShell blocked),
    fall back to the sole outgoing SPP port when there is exactly one.

    Raises :class:`PortNotFound` with an explanatory message otherwise.
    """
    spp = list_bt_spp_ports()
    outgoing = [s for s in spp if s.outgoing]

    mac = bt_mac_for_name(name)
    if mac:
        for s in outgoing:
            if s.mac == mac:
                return s.device
        raise PortNotFound(
            f"'{name}' is paired (MAC {mac}) but no outgoing Bluetooth COM port "
            f"carries that MAC. Outgoing SPP ports seen: "
            f"{[s.device for s in outgoing] or 'none'}. "
            f"Re-pair '{name}' (Remove device, then Add device) and try again."
        )

    if len(outgoing) == 1:
        return outgoing[0].device
    if not outgoing:
        raise PortNotFound(
            f"No outgoing Bluetooth SPP port found. Is '{name}' paired and the "
            f"Pico powered? (Pair it in Windows Bluetooth settings.)"
        )
    raise PortNotFound(
        f"Could not resolve '{name}' to a MAC and multiple Bluetooth SPP ports "
        f"exist ({[s.device for s in outgoing]}). Pass the COM port explicitly."
    )


def find_usb_pico_port() -> str | None:
    """Return the COM port of a USB-connected Pico (VID 2E8A), or ``None``."""
    if list_ports is None:
        return None
    for p in list_ports.comports():
        hwid = (p.hwid or "").upper()
        if any(f"VID_{vid}" in hwid or f"VID:{vid}" in hwid for vid in _PICO_USB_VIDS):
            return p.device
    return None


def autodetect_port(name: str = DEFAULT_BT_NAME) -> str:
    """Best-effort: the ``gems-pico`` Bluetooth port, else a USB Pico.

    Raises :class:`PortNotFound` if neither is present.
    """
    try:
        return find_gems_pico_port(name)
    except PortNotFound:
        usb = find_usb_pico_port()
        if usb:
            return usb
        raise
