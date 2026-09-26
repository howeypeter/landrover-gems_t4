"""Focused probe of the Lucas 10AS alarm/immobiliser on the bench K-line.

Discovered by pentest_scan (2026-09-25): with the 10AS wired onto the bench K
node alongside the GEMS ECU, NEW responders appeared — the 10AS's diagnostic
channel. It runs at **9600 baud** (GEMS is 10400), 5-baud SLOW init, on addresses
**0x1C** and **0x9D**, keybytes `55 83 76` / `55 83 f7`, and engages KWP service
**0x21** (readDataByLocalIdentifier) — the road to the EKA / EEPROM.

This probe inits at 9600 on the chosen address(es) and:
  1. captures the clean keybytes,
  2. runs a small FRAMING recon (which KWP target byte the 10AS answers),
  3. sweeps svc 0x21 local IDs 0x00..0xFF,
  4. tries a few identification / read services.

STRICTLY READ-ONLY. Needs the pentest firmware (CMD_RAW_INIT). Transport:
  GEMS_CONNECT=host[:port]  -> WiFi/TCP Pico (recommended; fast)
  GEMS_PORT=COMx            -> USB Pico
  (else)                    -> BLE 'gems-pico'

Usage:
  python probe_10as.py            # probes 0x9D then 0x1C
  python probe_10as.py 9D         # just 0x9D
  python probe_10as.py 9D 1C 33   # explicit list (hex)
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

from rich.console import Console

CMD_PING = 0x01
CMD_SEND_RECV = 0x03
CMD_RAW_INIT = 0x05
BAUD = 9600                      # the 10AS baud (GEMS is 10400)
MODE_SLOW = 0                    # 5-baud slow init

#: Every run is mirrored to this log (append) so the 0x21 sweep output is kept,
#: not just shown. Gitignored like the other bench .log captures.
LOG = Path(__file__).with_name("probe_10as.log")


class _Tee:
    """Print to the terminal AND append to the log file (flushed per line)."""

    def __init__(self, path: Path) -> None:
        self._con = Console()
        self._fh = open(path, "a", encoding="utf-8")
        self._filecon = Console(file=self._fh, width=100)

    def print(self, *a, **k) -> None:
        self._con.print(*a, **k)
        self._filecon.print(*a, **k)
        self._fh.flush()

    def rule(self, *a, **k) -> None:
        self._con.rule(*a, **k)
        self._filecon.rule(*a, **k)
        self._fh.flush()


console = _Tee(LOG)


def make_transport():
    conn = os.environ.get("GEMS_CONNECT")
    if conn:
        from gems_t4.transport.tcp import TcpTransport, parse_endpoint
        host, port = parse_endpoint(conn)
        return TcpTransport(host, port)
    port = os.environ.get("GEMS_PORT")
    if port:
        from gems_t4.transport.pico import PicoAdapterTransport
        return PicoAdapterTransport(port)
    from gems_t4.transport.ble import BleTransport
    return BleTransport(os.environ.get("GEMS_BLE", "gems-pico"))


def kwp(dest: int, data: list[int], src: int = 0xF7) -> bytes:
    """ISO-14230 header frame: [0x80|len] dest src <data...> checksum."""
    fmt = 0x80 | (len(data) & 0x3F)
    f = bytes([fmt, dest, src]) + bytes(data)
    return f + bytes([sum(f) & 0xFF])


def hexs(b: bytes) -> str:
    return b.hex(" ") if b else "(silent)"


def raw_init(t, addr: int) -> bytes:
    payload = bytes([MODE_SLOW, (BAUD >> 8) & 0xFF, BAUD & 0xFF, addr])
    st, resp = t._transceive(CMD_RAW_INIT, payload)
    return resp if st == 0 else b""


def send_recv(t, frame: bytes) -> bytes:
    st, pl = t._transceive(CMD_SEND_RECV, frame)
    return pl if st == 0 else b""


def probe(t, addr: int) -> None:
    console.rule(f"10AS probe  addr 0x{addr:02X} @ {BAUD} baud")
    kb = raw_init(t, addr)
    console.print(f"init -> {hexs(kb)}")
    if not kb:
        console.print("[yellow]no init response — 10AS powered? K on the node? "
                      "right baud/addr?[/]")
        return

    # 1) FRAMING recon: which target byte does the 10AS answer? Try 21 01 several
    #    ways so we learn the correct header before sweeping.
    console.print("[bold]-- framing recon (svc 21 01) --[/]")
    for label, frame in (
        (f"kwp dest=0x{addr:02X}", kwp(addr, [0x21, 0x01])),
        ("kwp dest=0x33", kwp(0x33, [0x21, 0x01])),
        ("kwp dest=0x00", kwp(0x00, [0x21, 0x01])),
        ("bare 21 01", bytes([0x21, 0x01])),
    ):
        raw_init(t, addr)
        console.print(f"    {label:16} -> {hexs(send_recv(t, frame))}")

    # 2) svc 0x21 readDataByLocalIdentifier sweep. Uses dest=addr; init once, then
    #    re-init if the pseudo-session drops (a run of silents).
    console.print("[bold]-- svc 0x21 (readDataByLocalId) sweep 0x00..0xFF --[/]")
    raw_init(t, addr)
    silent = 0
    for lid in range(0x100):
        r = send_recv(t, kwp(addr, [0x21, lid]))
        if r:
            console.print(f"    21 {lid:02X} -> {hexs(r)}")
            silent = 0
        else:
            silent += 1
            if silent >= 12:               # session may have timed out; re-init
                if raw_init(t, addr):
                    r = send_recv(t, kwp(addr, [0x21, lid]))
                    if r:
                        console.print(f"    21 {lid:02X} -> {hexs(r)} (re-init)")
                silent = 0

    # 3) A few identification / other read services (read-only).
    console.print("[bold]-- other read services --[/]")
    for label, data in (
        ("1A 80 (ecu id)", [0x1A, 0x80]),
        ("1A 90 (vin?)", [0x1A, 0x90]),
        ("1A 9B", [0x1A, 0x9B]),
        ("10 81 (startComm)", [0x10, 0x81]),
        ("10 85 (diag sess)", [0x10, 0x85]),
        ("81 (startComm)", [0x81]),
        ("22 00 00", [0x22, 0x00, 0x00]),
        ("23 read mem", [0x23, 0x00, 0x00, 0x00, 0x01]),
        ("3E (tester present)", [0x3E]),
    ):
        raw_init(t, addr)
        console.print(f"    {label:22} -> {hexs(send_recv(t, kwp(addr, data)))}")


def main() -> None:
    args = sys.argv[1:]
    addrs = [int(a, 16) for a in args] if args else [0x9D, 0x1C]
    t = make_transport()
    t.open()
    try:
        try:
            st, ver = t._transceive(CMD_PING)
            console.print(f"[dim]firmware: {ver.decode('ascii', 'replace')}[/]")
        except Exception:  # noqa: BLE001
            console.print("[yellow]PING failed — continuing anyway[/]")
        for a in addrs:
            probe(t, a)
    finally:
        t.close()


if __name__ == "__main__":
    main()
