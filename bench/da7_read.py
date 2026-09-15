"""Unlock ($27) then AUTHORIZED READS on the 0xDA channel (K+L).

da6 proved the unlock (seed->key = seed*16723 mod 65536 -> 6702AA). This does the
same unlock, then — in the SAME authorized session — issues the proprietary READ
commands recovered from the FlemcoDesign app, so we capture real data bytes:

    2204C4  VIN            2204E2  PROM ID        2204BF  displacement/trans/drivetrain
    222332  air flow       222333  fuel flow      222334  throttle
    222336  short idle     222337  long idle

STRICTLY READ-ONLY after unlock: no A3 writes, no memory writes. A correct key
does NOT increment the $27 lockout counter, so this is safe to run after da6
without a power-cycle. WIRING: L-line (C1017 pin 20) tied to K. Ignition ON.

  python da7_read.py                 # BLE 'gems-pico'
  GEMS_PORT=COM5 python da7_read.py  # USB
"""
from __future__ import annotations

import logging
import os as _os
from pathlib import Path

from gems_t4.transport.base import InitError, TransportError, TransportTimeout


def _make_transport():
    port = _os.environ.get("GEMS_PORT")
    if port:
        from gems_t4.transport.pico import PicoAdapterTransport
        return PicoAdapterTransport(port)
    from gems_t4.transport.ble import BleTransport
    return BleTransport(_os.environ.get("GEMS_BLE", "gems-pico"))


PORT = _os.environ.get("GEMS_PORT") or ("BLE:" + _os.environ.get("GEMS_BLE", "gems-pico"))
ADDR = 0xDA
LOG = Path(__file__).with_name("da7_read.log")

logger = logging.getLogger("da7_read")
logger.setLevel(logging.INFO)
logger.propagate = False
_fmt = logging.Formatter("%(asctime)s.%(msecs)03d  %(message)s", datefmt="%H:%M:%S")
for _h in (logging.FileHandler(LOG, mode="w", encoding="utf-8"), logging.StreamHandler()):
    _h.setFormatter(_fmt)
    logger.addHandler(_h)
log = logger.info

READS = [
    ("VIN            ", [0x22, 0x04, 0xC4], "6204C4"),
    ("PROM ID        ", [0x22, 0x04, 0xE2], "6204E2"),
    ("disp/trans/drv ", [0x22, 0x04, 0xBF], "6204BF"),
    ("air flow rate  ", [0x22, 0x23, 0x32], "622332"),
    ("fuel flow rate ", [0x22, 0x23, 0x33], "622333"),
    ("throttle (TPS) ", [0x22, 0x23, 0x34], "622334"),
    ("short-term idle", [0x22, 0x23, 0x36], "622336"),
    ("long-term idle ", [0x22, 0x23, 0x37], "622337"),
]


def gen_key(seed: int) -> int:
    return (seed * 16723) % 65536


def k14(data: list[int]) -> bytes:
    f = bytes([len(data)]) + bytes(data)
    return f + bytes([sum(f) & 0xFF])


def ascii_of(b: bytes) -> str:
    return "".join(chr(x) if 32 <= x < 127 else "." for x in b)


def find_after(reply: bytes, tag: bytes) -> bytes | None:
    i = reply.find(tag)
    return reply[i + len(tag):] if i >= 0 else None


def main() -> None:
    t = _make_transport()
    try:
        t.open()
        ver = t.ping().decode("ascii", "replace") if hasattr(t, "ping") else "?"
    except Exception as e:  # noqa: BLE001
        log(f"OPEN/PING FAILED: {e!r}")
        return

    log("=" * 72)
    log(f"da7_read (unlock + authorized reads, 0xDA) — src {PORT} fw {ver}")
    log("=" * 72)

    def send(frame: bytes) -> bytes:
        try:
            t.send(frame)
            return t.receive()
        except (TransportTimeout, Exception):  # noqa: BLE001
            return b""

    try:
        kb = t.init(ADDR, "slow").keybytes.hex()
    except (InitError, TransportError, OSError) as exc:
        log(f"0xDA init FAILED: {exc!r} — L-line tied? aborting.")
        t.close()
        return
    log(f"0xDA session open (keybytes {kb})")

    send(k14([0x10, 0x02]))                       # StartDiagSession
    r = send(k14([0x27, 0x01]))                   # requestSeed
    tail = find_after(r, bytes([0x67, 0x01]))
    if not tail or len(tail) < 2:
        log(f"  no seed ({r.hex() or 'silent'}) — aborting.")
        t.close()
        return
    seed = (tail[0] << 8) | tail[1]
    key = gen_key(seed)
    r = send(k14([0x27, 0x02, (key >> 8) & 0xFF, key & 0xFF]))
    if find_after(r, bytes([0x67, 0x02, 0xAA])) is None:
        log(f"  unlock FAILED (seed {seed:04X} key {key:04X} -> {r.hex() or 'silent'}) — aborting reads.")
        t.close()
        return
    log(f"  UNLOCKED (seed {seed:04X} -> key {key:04X} -> 6702AA)")
    log("-" * 72)
    log("  AUTHORIZED READS (raw response, then data after the 62.. echo):")

    for name, req, echo in READS:
        r = send(k14(req))
        data = find_after(r, bytes.fromhex(echo))
        dtxt = (data.hex().upper() + f"   |{ascii_of(data)}|") if data is not None else "(no 62-echo)"
        log(f"   {name}  {bytes(req).hex()}  -> raw {r.hex() or 'silent':22} data: {dtxt}")

    # leave the ECU cleanly
    send(bytes([0x01, 0xA4, 0xA5]))               # A4 close (k14 of [A4])
    log("-" * 72)
    log("  Reads done (no writes sent). Paste da7_read.log back.")
    log(f"[wrote {LOG}]")
    t.close()


if __name__ == "__main__":
    main()
