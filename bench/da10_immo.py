"""Confirm + map the suspected immobiliser/security block on 0xDA (K+L).

The da9 sweep found a "two copies" pattern in the 0x3C page-0x18 records:
    3C 18 A4 == 3C 18 A7   (byte-identical)
    3C 18 A5 ~= 3C 18 A8   (one byte differs)
with 3C 18 A6 between them. That two-copy storage is the classic GEMS
immobiliser/security-code signature. This reads the A2..AA neighborhood
REPEATEDLY (default 3 passes) so we can tell:
  - which records are STATIC (identity / security code) vs CHANGING (adaptive),
  - that the A4==A7 / A5==A8 copies really match (not a sweep desync artifact).

STRICTLY READ-ONLY: unlock ($27, correct key) + reads. No writes.
WIRING: C1017 pin 20 (L-line) tied to K. Ignition ON.

  python da10_immo.py                 # BLE 'gems-pico'
  GEMS_PORT=COM5 python da10_immo.py  # USB
"""
from __future__ import annotations

import logging
import os as _os
from pathlib import Path

from gems_t4.protocol.gems_secure import GemsSecureSession, security_key
from gems_t4.transport.base import InitError, TransportError

PAGE = 0x18
RECORDS = list(range(0xA2, 0xAB))    # A2..AA (the two-copy block + neighbours)
PASSES = 3


def _make_transport():
    port = _os.environ.get("GEMS_PORT")
    if port:
        from gems_t4.transport.pico import PicoAdapterTransport
        return PicoAdapterTransport(port)
    from gems_t4.transport.ble import BleTransport
    return BleTransport(_os.environ.get("GEMS_BLE", "gems-pico"))


PORT = _os.environ.get("GEMS_PORT") or ("BLE:" + _os.environ.get("GEMS_BLE", "gems-pico"))
LOG = Path(__file__).with_name("da10_immo.log")

logger = logging.getLogger("da10_immo")
logger.setLevel(logging.INFO)
logger.propagate = False
_fmt = logging.Formatter("%(asctime)s.%(msecs)03d  %(message)s", datefmt="%H:%M:%S")
for _h in (logging.FileHandler(LOG, mode="w", encoding="utf-8"), logging.StreamHandler()):
    _h.setFormatter(_fmt)
    logger.addHandler(_h)
log = logger.info


def ascii_of(b: bytes) -> str:
    return "".join(chr(x) if 32 <= x < 127 else "." for x in b)


def main() -> None:
    s = GemsSecureSession(_make_transport())
    try:
        s.connect()
    except (InitError, TransportError, OSError) as exc:
        log(f"connect FAILED: {exc!r} — L-line tied? aborting.")
        return
    if not s.unlock():
        log("$27 unlock FAILED — aborting.")
        s.close()
        return
    log(f"UNLOCKED — seed {s.last_seed:04X} -> key {security_key(s.last_seed):04X}")

    # read each record `PASSES` times; keep every distinct value seen
    seen: dict[int, list[bytes]] = {b2: [] for b2 in RECORDS}
    for p in range(PASSES):
        for b2 in RECORDS:
            r = s.read_memory(PAGE, b2, 0x10)
            if r is not None and r not in seen[b2]:
                seen[b2].append(r)

    log(f"\nRecords 0x{PAGE:02X} A2..AA, {PASSES} passes each:")
    for b2 in RECORDS:
        vals = seen[b2]
        if not vals:
            log(f"   {PAGE:02X} {b2:02X} -> (no read)")
        elif len(vals) == 1:
            log(f"   {PAGE:02X} {b2:02X} STATIC   {vals[0].hex().upper()}  |{ascii_of(vals[0])}|")
        else:
            log(f"   {PAGE:02X} {b2:02X} CHANGING ({len(vals)} distinct):")
            for v in vals:
                log(f"            {v.hex().upper()}  |{ascii_of(v)}|")

    # explicit copy checks (use the first stable value seen)
    def first(b2: int) -> bytes | None:
        return seen[b2][0] if seen[b2] else None

    log("\ncopy checks:")
    a4, a7 = first(0xA4), first(0xA7)
    a5, a8 = first(0xA5), first(0xA8)
    log(f"   A4 == A7 ? {a4 == a7}   (A4 {a4.hex().upper() if a4 else '—'})")
    if a5 and a8:
        diff = [i for i in range(min(len(a5), len(a8))) if a5[i] != a8[i]]
        log(f"   A5 vs A8 differ at byte offsets: {diff}  "
            f"(A5 {a5.hex().upper()} / A8 {a8.hex().upper()})")

    log("\nReading: STATIC records that appear twice (A4/A7, A5/A8) are the immo/")
    log("security copies; a CHANGING record is an adaptive/rolling value, not the")
    log("stored code. Paste da10_immo.log back.")
    log(f"[wrote {LOG}]")
    s.close()


if __name__ == "__main__":
    main()
