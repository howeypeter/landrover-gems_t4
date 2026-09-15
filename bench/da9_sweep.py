"""Authorized read-SWEEP of the 0xDA channel — map what's reachable (K+L).

Goal: locate the immobiliser / security / "clone" data now that $27 is open.
0x3C is record/page-indexed (NOT a linear byte address), so we can't just dump a
range — instead we CATALOG it: step the index bytes and log every record that
comes back with real content. Same for the CID reads the app uses (22 04 xx /
22 23 xx) to find any field that exposes the immobiliser/security code directly.

Three sweeps (toggle below), all on ONE unlocked session:
  A) 0x3C index:  3C <B1> <B2> 10   for B1 in PAGES_3C, B2 = 00..FF
  B) CID 22 04 xx:  the family holding VIN(C4)/PROMID(E2)/config(BF)
  C) CID 22 23 xx:  the params family (2332..2337 known)

STRICTLY READ-ONLY: unlock ($27, correct key — no lockout) + reads. No writes,
no A3, no 2E. WIRING: C1017 pin 20 (L-line) tied to K. Ignition ON.

  python da9_sweep.py                 # BLE 'gems-pico'
  GEMS_PORT=COM5 python da9_sweep.py  # USB

~500-770 reads over BLE ≈ 2-3 min. Narrow the ranges below to go faster.
"""
from __future__ import annotations

import logging
import os as _os
from pathlib import Path

from gems_t4.protocol.gems_secure import GemsSecureSession, security_key
from gems_t4.transport.base import InitError, TransportError

# ---- what to sweep (trim to go faster) ------------------------------------- #
SWEEP_3C = True
PAGES_3C = [0x18]            # B1 values to try (0x18 = config EEPROM area). Add
                            # 0x19, 0x1A, 0x20 to widen (each adds 256 reads).
SWEEP_CID_04 = True          # 22 04 00..FF
SWEEP_CID_23 = True          # 22 23 00..FF
# ---------------------------------------------------------------------------- #

NRC = {
    0x10: "generalReject", 0x11: "serviceNotSupported", 0x12: "subFunctionNotSupported",
    0x22: "conditionsNotCorrect", 0x31: "requestOutOfRange", 0x33: "securityAccessDenied",
    0x78: "responsePending",
}


def _make_transport():
    port = _os.environ.get("GEMS_PORT")
    if port:
        from gems_t4.transport.pico import PicoAdapterTransport
        return PicoAdapterTransport(port)
    from gems_t4.transport.ble import BleTransport
    return BleTransport(_os.environ.get("GEMS_BLE", "gems-pico"))


PORT = _os.environ.get("GEMS_PORT") or ("BLE:" + _os.environ.get("GEMS_BLE", "gems-pico"))
LOG = Path(__file__).with_name("da9_sweep.log")

logger = logging.getLogger("da9_sweep")
logger.setLevel(logging.INFO)
logger.propagate = False
_fmt = logging.Formatter("%(asctime)s.%(msecs)03d  %(message)s", datefmt="%H:%M:%S")
for _h in (logging.FileHandler(LOG, mode="w", encoding="utf-8"), logging.StreamHandler()):
    _h.setFormatter(_fmt)
    logger.addHandler(_h)
log = logger.info


def ascii_of(b: bytes) -> str:
    return "".join(chr(x) if 32 <= x < 127 else "." for x in b)


def interesting(data: bytes) -> bool:
    """A record worth logging: has real content (not all-FF, not all-00)."""
    return bool(data) and len(set(data)) > 1 and set(data) not in ({0xFF}, {0x00})


class Sweeper:
    def __init__(self, s: GemsSecureSession) -> None:
        self.s = s
        self.reunlocks = 0

    def exch(self, payload: bytes) -> bytes:
        """One authorized exchange; re-unlock once if the session dropped
        (securityAccessDenied after we were in), then retry."""
        r = self.s._exchange(payload)
        if len(r) >= 3 and r[0] == 0x7F and r[2] == 0x33:   # securityAccessDenied
            if self.s.unlock():
                self.reunlocks += 1
                r = self.s._exchange(payload)
        return r

    @staticmethod
    def classify(r: bytes) -> tuple[str, bytes]:
        if not r:
            return "silent", b""
        if r[0] == 0x7F and len(r) >= 3:
            return f"NRC {r[2]:02X} {NRC.get(r[2], '?')}", b""
        # positive: service+0x40 then echo; return the payload after the 3-byte echo
        return "positive", r


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

    log("=" * 74)
    log(f"da9_sweep (0xDA authorized read sweep) — src {PORT} fw {ver}")
    log("=" * 74)
    if not s.unlock():
        log("$27 unlock FAILED (no 6702AA) — L-line/power? aborting.")
        s.close()
        return
    log(f"UNLOCKED — seed {s.last_seed:04X} -> key {security_key(s.last_seed):04X}")
    sw = Sweeper(s)

    # ---- A) 0x3C record-index sweep --------------------------------------- #
    if SWEEP_3C:
        for b1 in PAGES_3C:
            log(f"\n[A] 0x3C index sweep  B1=0x{b1:02X}, B2=00..FF (16 B each)")
            hits = 0
            for b2 in range(0x100):
                r = sw.exch(bytes([0x3C, b1, b2, 0x10]))
                kind, _ = sw.classify(r)
                if kind == "positive" and r[0] == 0x7C and interesting(r[1:]):
                    hits += 1
                    log(f"   3C {b1:02X} {b2:02X} -> {r[1:].hex().upper()}  |{ascii_of(r[1:])}|")
            log(f"   ({hits} records with content on page 0x{b1:02X})")

    # ---- B) CID 22 04 xx -------------------------------------------------- #
    if SWEEP_CID_04:
        log("\n[B] CID sweep  22 04 00..FF")
        for xx in range(0x100):
            r = sw.exch(bytes([0x22, 0x04, xx]))
            kind, _ = sw.classify(r)
            if kind == "positive" and r[:1] == b"\x62":
                body = r[3:] if len(r) > 3 else b""
                log(f"   22 04 {xx:02X} -> {r.hex().upper()}  data {body.hex().upper()} |{ascii_of(body)}|")

    # ---- C) CID 22 23 xx -------------------------------------------------- #
    if SWEEP_CID_23:
        log("\n[C] CID sweep  22 23 00..FF")
        for xx in range(0x100):
            r = sw.exch(bytes([0x22, 0x23, xx]))
            kind, _ = sw.classify(r)
            if kind == "positive" and r[:1] == b"\x62":
                body = r[3:] if len(r) > 3 else b""
                log(f"   22 23 {xx:02X} -> {r.hex().upper()}  data {body.hex().upper()} |{ascii_of(body)}|")

    log("\n" + "=" * 74)
    log(f"done. re-unlocks during sweep: {sw.reunlocks}")
    log("Look for: ASCII that resembles part of a VIN; a 16-bit value that matches")
    log("the immobiliser/security code; two identical records (the 'two copies').")
    log("Re-read any hit on its own to confirm it's stable (not a desync artifact).")
    log(f"[wrote {LOG}]")
    s.close()


if __name__ == "__main__":
    main()
