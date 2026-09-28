"""L9637D transceiver health test - is a (spare) chip good?

Exercises the K-line transceiver with NO ECU attached. The K-line is half-duplex,
so whatever the L9637D transmits it reads back as an ECHO: if the echo comes through
clean, the whole core path is proven - TX driver (pin 4 -> K), the K pin (6), the RX
receiver (K -> pin 1), Vcc (3), Vs (7), and the 510 ohm pull-up. A dead/unpowered/
mis-wired chip echoes nothing or garbage.

Rig (breadboard, no ECU):  Vcc(3)->Pico 3V3, GND(5)->gnd, Vs(7)->+12V,
  K(6)->510ohm->Vs, TX(4)->Pico GP0, RX(1)->Pico GP1. (LI(8)->GND; LO(2)->GP2 only
  for the optional L-channel test.)

Uses CMD_RAW_XFER (0x08): sends bytes on the K-line, returns the raw RX (= the echo,
with no ECU). Needs firmware >= 3.4.0. Transport: GEMS_PORT / GEMS_CONNECT / auto / BLE.

Usage:  python bench/l9637d_test.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

CMD_PING = 0x01
CMD_RAW_XFER = 0x08

LOG = Path(__file__).with_name("l9637d_test.log")
_fh = open(LOG, "a", encoding="utf-8")


def out(msg: str = "") -> None:
    print(msg)
    _fh.write(msg + "\n")
    _fh.flush()


def make_transport():
    conn = os.environ.get("GEMS_CONNECT")
    if conn:
        from gems_t4.transport.tcp import TcpTransport, parse_endpoint
        host, port = parse_endpoint(conn)
        out(f"[transport: WiFi {host}:{port}]")
        return TcpTransport(host, port)
    port = os.environ.get("GEMS_PORT")
    if not port:
        try:
            from gems_t4.transport.pico import find_pico_port
            port = find_pico_port()
        except Exception:
            port = None
    if port:
        from gems_t4.transport.pico import PicoAdapterTransport
        out(f"[transport: USB {port}]")
        return PicoAdapterTransport(port)
    from gems_t4.transport.ble import BleTransport
    name = os.environ.get("GEMS_BLE", "gems-pico")
    out(f"[transport: BLE {name}]")
    return BleTransport(name)


# Patterns chosen to exercise every bit position + both transition directions.
PATTERNS = [
    bytes([0x55]),                      # 0101 0101
    bytes([0xAA]),                      # 1010 1010
    bytes([0x00, 0xFF]),                # all-low then all-high byte
    bytes([0xFF, 0x00]),
    bytes([0x01, 0x02, 0x04, 0x08, 0x10, 0x20, 0x40, 0x80]),  # walking one
    bytes([0x12, 0x34, 0x56, 0x78, 0x9A, 0xBC, 0xDE, 0xF0]),  # mixed
]


def echo_test(t, tx: bytes):
    """Send tx on the K-line; return (ok, raw_rx). With no ECU, raw should == tx."""
    st, raw = t._transceive(CMD_RAW_XFER, tx)
    if st != 0:
        return False, raw
    # The echo is the leading bytes; a bare chip returns exactly tx (no response).
    ok = raw[: len(tx)] == tx and len(raw) >= len(tx)
    return ok, raw


def main() -> None:
    out("=" * 60)
    out(f" L9637D health test  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    out("=" * 60)
    t = make_transport()
    t.open()
    passed = failed = 0
    try:
        try:
            st, ver = t._transceive(CMD_PING)
            out(f"firmware: {ver.decode('ascii','replace')}")
        except Exception:  # noqa: BLE001
            out("PING failed - is the Pico connected? (aborting)")
            return

        out("\nK-line echo tests (no ECU needed - the chip echoes its own TX):")
        for tx in PATTERNS:
            ok, raw = echo_test(t, tx)
            tag = "PASS" if ok else "FAIL"
            out(f"  [{tag}] sent {tx.hex(' ')}  ->  got {raw.hex(' ') or '(silent)'}")
            passed += ok
            failed += (not ok)

        out("")
        if failed == 0:
            out(f"  ==> ALL {passed} ECHO TESTS PASSED. The L9637D K-line core is GOOD")
            out("      (TX driver, K pin, RX receiver, Vcc/Vs, and the 510 ohm pull-up).")
        else:
            out(f"  ==> {failed} of {passed+failed} FAILED.")
            out("      (silent) everywhere  -> chip dead, not powered (Vs 12V? Vcc 3V3?),")
            out("                              or TX/RX swapped, or no 510 ohm pull-up on K.")
            out("      garbled echo          -> wrong pull-up, Vcc not 3.3V, or a marginal chip.")
            out("      first pattern ok then fails -> flaky pin / breadboard contact.")

        out("\nOptional L-channel test (only if LI(8) and LO(2)->GP2 are wired):")
        out("  Tie LI(8) to GND, run:  python bench/monitor_l.py 1000   (expect STATIC LOW)")
        out("  Tie LI(8) to +12V,      run again                        (expect STATIC HIGH)")
        out("  Toggle LI while it runs -> transitions = the L comparator + LO output work.")
    finally:
        t.close()
        out(f"\n(log: {LOG.name})")


if __name__ == "__main__":
    main()
