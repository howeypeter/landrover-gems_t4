"""$27 SecurityAccess UNLOCK attempt on the 0xDA channel — the real key (K+L).

Tests the seed->key algorithm recovered from the FlemcoDesign "GEMS ECU Utility"
Android app (GEMS.java, via jadx):

    key = (seed * 16723) % 65536        # 16723 = 0x4153; 16-bit, big-endian

Handshake (per the app's authorizeScanTool):
    2701          -> 6701<seed>         (requestSeed; seed = 2 bytes)
    2702<key>     -> 6702AA             (ACCEPT)   / 6702CC (REJECT)

This does ONE computed key attempt — NOT a brute force. If our seed->key is
right we get 6702AA and never meaningfully touch the lockout counter. If it's
wrong we get 6702CC / 7F2735 (one of ~3 tries; recoverable by power-cycle).

########################  SAFETY / GUARDRAILS  ##############################
- ONE key submission per run. Re-running = another attempt: $27 locks after ~3
  WRONG keys (0x36 exceedNumberOfAttempts); 0x37 = requiredTimeDelayNotExpired.
  If you see 0x36/0x37, STOP, power-cycle the ECU, wait, then run once more.
- Read-only otherwise: a seed request (safe, no counter) + one key. No writes
  to coding/immobiliser, no memory writes. (A3xxxx writes are NOT sent here.)
- The key is COMPUTED from the seed the ECU just issued — never guessed.
#############################################################################

WIRING: **C1017 pin 20 (L-line) tied to the K node** (K+L). Ignition ON.

Run (one attempt):
  python da6_unlock.py                 # BLE, scans for 'gems-pico'
  GEMS_PORT=COM5 python da6_unlock.py  # force a wired/USB Pico
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
LOG = Path(__file__).with_name("da6_unlock.log")

logger = logging.getLogger("da6_unlock")
logger.setLevel(logging.INFO)
logger.propagate = False
_fmt = logging.Formatter("%(asctime)s.%(msecs)03d  %(message)s", datefmt="%H:%M:%S")
for _h in (logging.FileHandler(LOG, mode="w", encoding="utf-8"), logging.StreamHandler()):
    _h.setFormatter(_fmt)
    logger.addHandler(_h)
log = logger.info

NRC = {
    0x11: "serviceNotSupported", 0x12: "subFunctionNotSupported",
    0x22: "conditionsNotCorrect", 0x31: "requestOutOfRange",
    0x33: "securityAccessDenied", 0x35: "invalidKey",
    0x36: "exceedNumberOfAttempts", 0x37: "requiredTimeDelayNotExpired",
    0x78: "responsePending",
}


def gen_key(seed: int) -> int:
    """The recovered GEMS $27 transform: key = (seed * 16723) mod 65536."""
    return (seed * 16723) % 65536


def k14(data: list[int]) -> bytes:
    """ISO-14230 no-address frame [len][data][sum] — the framing that got seeds."""
    f = bytes([len(data)]) + bytes(data)
    return f + bytes([sum(f) & 0xFF])


def ascii_of(b: bytes) -> str:
    return "".join(chr(x) if 32 <= x < 127 else "." for x in b)


def find_after(reply: bytes, tag: bytes) -> bytes | None:
    """Return the bytes following `tag` inside a no-address reply, or None."""
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
    log(f"da6_unlock ($27 real-key attempt, 0xDA, ONE try) — src {PORT} fw {ver}")
    log("key = (seed * 16723) % 65536  [from FlemcoDesign GEMS.java]")
    log("ASSUMES C1017 pin 20 (L-line) tied to K. Ignition ON.")
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
        log(f"0xDA init FAILED: {exc!r} — is the L-line tied? aborting.")
        t.close()
        return
    log(f"0xDA session open (keybytes {kb}; expect aa55)")

    # Optional prelude the app does: StartDiagnosticSession 1002 -> 5002.
    # Our ECU answered $10 oddly before; log it but don't gate on it.
    r = send(k14([0x10, 0x02]))
    log(f"  1002 StartDiagSession       -> {r.hex() or '(silent)'}  |{ascii_of(r)}|")

    # 1) requestSeed
    seed_req = k14([0x27, 0x01])
    r = send(seed_req)
    log(f"  2701 requestSeed            -> {r.hex() or '(silent)'}  |{ascii_of(r)}|")
    tail = find_after(r, bytes([0x67, 0x01]))
    if not tail or len(tail) < 2:
        log("  No 6701<seed> — channel not live / wrong framing. Aborting (no key sent).")
        t.close()
        return
    seed = (tail[0] << 8) | tail[1]           # big-endian 2-byte seed
    key = gen_key(seed)
    log(f"  seed = {seed:04X}  ->  key = {key:04X}  (sending 2702{key:04X})")

    # 2) sendKey — the SINGLE computed attempt
    key_frame = k14([0x27, 0x02, (key >> 8) & 0xFF, key & 0xFF])
    r = send(key_frame)
    log(f"  2702{key:04X} sendKey          -> {r.hex() or '(silent)'}  |{ascii_of(r)}|")

    # 3) verdict
    log("-" * 72)
    if find_after(r, bytes([0x67, 0x02, 0xAA])) is not None:
        log("  *** UNLOCKED — 6702AA. The seed->key is CORRECT on this ECU. ***")
        log("  Next: implement security_access in gems_t4, then the coding reads")
        log("  (2204C4 VIN, 2204BF displacement, 2204E2 PROMID) should answer.")
    elif find_after(r, bytes([0x67, 0x02, 0xCC])) is not None:
        log("  REJECTED — 6702CC. Key math or framing differs for this ECU variant.")
        log("  STOP. Power-cycle before another attempt (lockout after ~3 wrong keys).")
    elif 0x7F in r:
        i = r.index(0x7F)
        nrc = r[i + 2] if i + 2 < len(r) else -1
        name = NRC.get(nrc, "?")
        log(f"  NEGATIVE 7F 27 {nrc:02X} ({name}).")
        if nrc in (0x36, 0x37):
            log("  LOCKOUT — power-cycle the ECU and wait before running again.")
    else:
        log("  Unclear/silent reply — do NOT retry blindly; inspect the raw bytes above.")
    log(f"[wrote {LOG}]")
    t.close()


if __name__ == "__main__":
    main()
