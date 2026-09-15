"""live_sweep.py — map the GEMS proprietary live-data reads ($21) on 0xDA.

The service map found $21 (readDataByLocalId) returns live values (21 00 -> FF
then FE). This sweeps 21 00..FF over TWO full passes so live values (which change
between passes) separate from static ones, and logs a table we then label against
the SM001 input list (~108 T4 measures: coolant, throttle, RPM, O2, battery ...).

ROBUST: retry-on-silent (+ one session revive) so a marginal L-line jumper's
silent blips don't punch holes in the map. Prefer USB (steadier); it auto-detects.

  python live_sweep.py            -> live_sweep.csv + console table
"""
from __future__ import annotations
import csv
import os
import time
from pathlib import Path
from gems_t4.protocol.gems_secure import GemsSecureSession
from gems_t4.transport.base import InitError, TransportError, TransportTimeout

LOGCSV = Path(__file__).with_name("live_sweep.csv")
NRC = {0x11: "notSupported", 0x12: "subFuncNotSup", 0x22: "condNotCorrect",
       0x31: "outOfRange", 0x33: "securityDenied"}


def make_transport():
    port = os.environ.get("GEMS_PORT")
    if not port:
        try:
            from gems_t4.transport.pico import find_pico_port
            port = find_pico_port()
        except Exception:
            port = None
    if port:
        from gems_t4.transport.pico import PicoAdapterTransport
        print(f"[transport: USB {port}]")
        return PicoAdapterTransport(port)
    from gems_t4.transport.ble import BleTransport
    name = os.environ.get("GEMS_BLE", "gems-pico")
    print(f"[transport: BLE {name}]  (USB is steadier for a sweep)")
    return BleTransport(name)


def _raw(s, payload: bytes) -> bytes:
    try:
        return s._exchange(payload)
    except (TransportTimeout, TransportError, OSError):
        return b""


def revive(s, tries: int = 4) -> bool:
    for _ in range(tries):
        try:
            s.close()
        except Exception:  # noqa: BLE001
            pass
        try:
            s.connect()
            if s.unlock():
                return True
        except (InitError, TransportError, OSError):
            pass
        time.sleep(1.5)
    return False


# Pacing for a slow ~1996 Intel 87C196KC ECU: don't hammer it. A short gap before
# every request, and on silence BACK OFF (give it time to catch up) rather than
# retry fast - fast retries pile onto an already-behind ECU and make it worse.
PACE_S = 0.12                            # gap before each request
BACKOFF_S = [0.4, 0.8, 1.5]              # escalating waits after a silent reply


def robust(s, payload: bytes) -> bytes:
    """Send, pacing for the slow ECU: a short gap first, and on silence back off
    (let it recover) before retrying. Revive the session only as a last resort.
    Returns the first non-silent reply (positive OR negative), or b''."""
    time.sleep(PACE_S)
    r = _raw(s, payload)
    if r:
        return r
    for wait in BACKOFF_S:               # silent -> wait longer, then retry gently
        time.sleep(wait)
        r = _raw(s, payload)
        if r:
            return r
    revive(s)                            # persistent silence -> session likely dropped
    time.sleep(PACE_S)
    return _raw(s, payload)


def decode(r: bytes) -> tuple[str, str]:
    """(class, value-hex) — 'pos'/'nrcXX'/'silent' and the data bytes for a $21."""
    if not r:
        return "silent", ""
    if r[0] == 0x7F and len(r) >= 3:
        return f"nrc{r[2]:02X}", ""
    # positive: 61 <id> <data...>  -> return the data
    data = r[2:] if len(r) >= 2 and r[0] == 0x61 else r
    return "pos", data.hex().upper()


def main():
    s = GemsSecureSession(make_transport())
    try:
        s.connect()
    except (InitError, TransportError, OSError) as e:
        print(f"connect FAILED: {e}"); return
    if not s.unlock():
        print("unlock FAILED"); s.close(); return
    print("UNLOCKED. Sweeping $21 00..FF, two passes (live values change between passes)...\n")

    def pass_all(label: str) -> dict[int, tuple[str, str]]:
        out = {}
        print(f"-- {label} --", flush=True)
        for rid in range(0x100):
            c, v = decode(robust(s, bytes([0x21, rid])))
            out[rid] = (c, v)
            if c == "pos":
                print(f"   0x{rid:02X} -> {v}", flush=True)     # a hit
            elif rid % 16 == 0:
                print(f"   ..scanning 0x{rid:02X}", flush=True)  # progress marker
        return out

    p1 = pass_all("pass 1/2")
    print("  (waiting 5s so live values change) ...", flush=True)
    time.sleep(5.0)                      # let live values move between passes
    p2 = pass_all("pass 2/2")
    s.close()

    # Classify + report only ids that returned data at least once.
    rows = []
    for rid in range(0x100):
        c1, v1 = p1[rid]
        c2, v2 = p2[rid]
        if c1 != "pos" and c2 != "pos":
            continue                     # not a valid live id (or all silent)
        if c1 == "pos" and c2 == "pos":
            kind = "LIVE" if v1 != v2 else "static"
        else:
            kind = "flaky"               # positive one pass, not the other
        rows.append((rid, kind, v1, v2, c1, c2))

    print(f"{'id':<5}{'kind':<8}{'pass1':<12}{'pass2':<12}")
    print("-" * 40)
    for rid, kind, v1, v2, c1, c2 in rows:
        print(f"0x{rid:02X} {kind:<8}{(v1 or c1):<12}{(v2 or c2):<12}")

    with open(LOGCSV, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["id", "kind", "pass1_value", "pass2_value", "pass1", "pass2", "sm001_label"])
        for rid, kind, v1, v2, c1, c2 in rows:
            w.writerow([f"0x{rid:02X}", kind, v1, v2, c1, c2, ""])
    live = sum(1 for r in rows if r[1] == "LIVE")
    print(f"\n{len(rows)} ids return data ({live} LIVE). Saved to {LOGCSV.name}")
    print("Next: label them against the SM001 input list (coolant/throttle/RPM/O2/...).")


if __name__ == "__main__":
    main()
