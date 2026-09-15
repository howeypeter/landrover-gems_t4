"""Verify 0x3C memory-read format + discover the coding-WRITE path (0xDA, K+L).

Runs AFTER the proven $27 unlock. Two jobs, both needing a live unlocked session:

  #3  Verify the 0x3C memory-read format. We have never seen a 0x3C *positive*
      (all prior probes were pre-unlock securityAccessDenied), so the request
      arg order and the positive-response layout are unconfirmed. This reads a
      few small ranges at 0x1800 (EEPROM) and 0x2000 (27C1001) in BOTH byte
      orders and logs the raw replies so we can lock the format, then a bigger
      read to confirm it streams.

  #2  Discover the coding-WRITE service. The app only READS coding, so the write
      path is unknown. This is OPT-IN (WRITE_TEST=False by default) and, when
      enabled, does the SAFEST possible probe: a **no-op write** — it reads the
      config byte, writes that SAME value back via 2E (WriteDataByCommonId), and
      reads again to confirm nothing changed. That reveals whether 2E is accepted
      (positive 6E) or rejected (7F -> try the A3 form) WITHOUT altering the ECU.

########################  SAFETY  ##########################################
- Reads (0x3C, coding) are safe. The $27 unlock uses the correct key (no lockout).
- The write test is OFF by default. When you enable it, it writes a value back to
  ITSELF (net zero change) and verifies. Do NOT change WRITE_VALUE to something
  different unless you know the field and have a way to restore it.
- Never run the write test on-car; bench only, ECU you can reflash/restore.
#############################################################################

WIRING: C1017 pin 20 (L-line) tied to K. Ignition ON.
  python da8_secure_probe.py                 # BLE; reads only (write test off)
  GEMS_PORT=COM5 python da8_secure_probe.py  # USB
"""
from __future__ import annotations

import logging
import os as _os
from pathlib import Path

from gems_t4.protocol.gems_secure import (
    CID_CONFIG,
    GemsSecureError,
    GemsSecureSession,
    security_key,
)
from gems_t4.transport.base import InitError, TransportError

# ---- SAFETY SWITCH: leave False for read-only discovery -------------------- #
WRITE_TEST = False   # True = attempt ONE no-op 2E write (writes a value to itself)
# ---------------------------------------------------------------------------- #


def _make_transport():
    port = _os.environ.get("GEMS_PORT")
    if port:
        from gems_t4.transport.pico import PicoAdapterTransport
        return PicoAdapterTransport(port)
    from gems_t4.transport.ble import BleTransport
    return BleTransport(_os.environ.get("GEMS_BLE", "gems-pico"))


PORT = _os.environ.get("GEMS_PORT") or ("BLE:" + _os.environ.get("GEMS_BLE", "gems-pico"))
LOG = Path(__file__).with_name("da8_secure_probe.log")

logger = logging.getLogger("da8_secure_probe")
logger.setLevel(logging.INFO)
logger.propagate = False
_fmt = logging.Formatter("%(asctime)s.%(msecs)03d  %(message)s", datefmt="%H:%M:%S")
for _h in (logging.FileHandler(LOG, mode="w", encoding="utf-8"), logging.StreamHandler()):
    _h.setFormatter(_fmt)
    logger.addHandler(_h)
log = logger.info


def main() -> None:
    s = GemsSecureSession(_make_transport())
    try:
        try:
            ver = s.transport.ping().decode("ascii", "replace") \
                if hasattr(s.transport, "ping") else "?"
        except Exception:  # noqa: BLE001
            ver = "?"
        s.connect()
    except (InitError, TransportError, OSError) as exc:
        log(f"connect FAILED: {exc!r} — L-line tied? aborting.")
        return

    log("=" * 72)
    log(f"da8_secure_probe (0xDA) — src {PORT} fw {ver}  WRITE_TEST={WRITE_TEST}")
    log("=" * 72)

    if not s.unlock():
        log("$27 unlock FAILED (no 6702AA) — L-line/power? aborting.")
        s.close()
        return
    log(f"UNLOCKED — seed {s.last_seed:04X} -> key {security_key(s.last_seed):04X}")

    # ---- #3: 0x3C memory-read format verification (raw exchanges) ---------- #
    log("\n[#3] 0x3C memory read — verify format (raw 3C lsb msb len, both orders)")
    for addr in (0x1800, 0x2000):
        for lo, hi, tag in ((addr & 0xFF, (addr >> 8) & 0xFF, "LSB,MSB"),
                            ((addr >> 8) & 0xFF, addr & 0xFF, "MSB,LSB")):
            raw = s._exchange(bytes([0x3C, lo, hi, 0x10]))
            log(f"   3C @0x{addr:04X} ({tag})  -> {raw.hex().upper() or '(silent)'}")
    big = s._exchange(bytes([0x3C, 0x00, 0x20, 0x40]))
    log(f"   3C @0x2000 len=0x40 (LSB,MSB) -> {big.hex().upper() or '(silent)'}")
    log("   (looking for a 0x7C positive; note which byte order returns real data)")

    # ---- #3 via the library helper (single read; addressing is non-linear) -- #
    lib = s.read_at(0x2000, 0x10)
    log(f"   read_at(0x2000,16) -> {lib.hex().upper() if lib else '(none)'}")

    # ---- #2: coding-WRITE path discovery (no-op, opt-in) ------------------- #
    cfg = s.read_config()
    log(f"\n[#2] config read: {cfg}")
    if not WRITE_TEST:
        log("   write test OFF (WRITE_TEST=False). To discover the write path,")
        log("   set WRITE_TEST=True to no-op-write the config byte to itself.")
    elif cfg is None:
        log("   no config byte read — skipping write test.")
    else:
        same = bytes([cfg.raw])
        log(f"   NO-OP WRITE: 2E {CID_CONFIG.hex().upper()} {same.hex().upper()} (same value)")
        resp = s.write_cid(CID_CONFIG, same)
        log(f"     -> {resp.hex().upper() or '(silent)'}  "
            f"({'6E positive = 2E accepted' if resp[:1] == b'\x6e' else 'not 6E — try the A3 write form'})")
        back = s.read_config()
        log(f"   read back: {back}  ({'unchanged - good' if back == cfg else 'CHANGED - investigate!'})")

    log("\n" + "=" * 72)
    log("Paste da8_secure_probe.log back. Next: lock the 0x3C byte order/layout")
    log("into read_memory, and (if 6E) the 2E write into write_cid.")
    log(f"[wrote {LOG}]")
    s.close()


if __name__ == "__main__":
    try:
        main()
    except GemsSecureError as exc:
        log(f"secure error: {exc}")
