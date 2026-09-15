"""pin_test.py — fix your probe on ONE pin, step the actuator routines, note each.

You clip the test light / bulb / meter to a single pin (e.g. pin 24 = fuel pump),
then this fires each output routine one at a time and asks you what that pin did.
Your note for each is logged to pin_test.csv alongside the ECU's response.

KEY DIFFERENCE vs actuator_test.py: it fires each routine ONCE and holds the
session open with a harmless READ (not by re-firing $31). Re-firing $31 restarts
the routine and blips the output — that was the 'dip' you saw. This keeps the
output steady while you watch.

  python pin_test.py       (via the venv python)
Transport precedence USB > WiFi > BLE (USB recommended - no dropouts).
"""
from __future__ import annotations
import csv
import os
import threading
import time
from datetime import datetime
from pathlib import Path

from gems_t4.protocol.gems_secure import GemsSecureSession
from gems_t4.transport.base import InitError, TransportError, TransportTimeout

ROUTINES = [0x01, 0x04, 0x05, 0x07, 0x09, 0x0A, 0x0B]   # the fireable ids (positive $31)
# Baseline states you set physically on the bench BEFORE firing routines; the
# script just prompts + logs your observation (no ECU command). These tell a
# permanent rail/ground apart from a routine-driven output.
BASELINES = [
    ("pwr-on_ign-off", "Power ON, Ignition OFF"),
    ("ign-on_idle",    "Power ON, Ignition ON, engine NOT running, nothing firing"),
]
KEEPALIVE = bytes([0x22, 0x04, 0xBF])             # benign coding read: holds the
                                                  # session WITHOUT restarting the routine
LOGCSV = Path(__file__).with_name("pin_test.csv")


def make_transport():
    """USB (GEMS_PORT or auto-detect) > WiFi (GEMS_CONNECT) > BLE (GEMS_BLE)."""
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
    conn = os.environ.get("GEMS_CONNECT")
    if conn:
        from gems_t4.transport.tcp import TcpTransport, parse_endpoint
        host, tcp_port = parse_endpoint(conn)
        print(f"[transport: WiFi {host}:{tcp_port}]")
        return TcpTransport(host, tcp_port, allow_writes=True)
    from gems_t4.transport.ble import BleTransport
    name = os.environ.get("GEMS_BLE", "gems-pico")
    print(f"[transport: BLE {name}]  (USB is steadier - plug in the cable if you can)")
    return BleTransport(name)


def xchg(s, payload: bytes) -> bytes:
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


def is_positive(r: bytes) -> bool:
    return bool(r) and (r[0] != 0x7F or (len(r) >= 3 and r[2] == 0x78))


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return ""


def log_row(target, pin, mode, condition, start_hex, positive, drops, note):
    """condition = a routine id string ('0x05') or a baseline label; positive is a
    string ('yes'/'no'/'n/a')."""
    new = not LOGCSV.exists()
    with open(LOGCSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "target", "pin", "mode", "condition", "start_response",
                        "positive", "session_drops", "note"])
        w.writerow([datetime.now().strftime("%H:%M:%S"), target, pin, mode,
                    condition, start_hex, positive, drops, note])


def baseline_note(pin: str, mode_name: str, condition: str) -> str:
    print(f"=== Baseline: {condition} ===")
    print(f"    Set the bench to that state, then watch pin {pin} for {mode_name}.")
    return ask(f"        note - pin {pin} now (y/n + anything): ")


def parse_target(t: str) -> tuple[str, str, str]:
    """'14G' / '24V' -> (pin, mode, mode_name). Trailing G=ground, V=+12V."""
    t = t.strip().upper()
    mode = ""
    if t and t[-1] in ("G", "V"):
        mode, t = t[-1], t[:-1]
    pin = t.strip() or "?"
    return pin, mode, {"G": "GROUND", "V": "+12V"}.get(mode, "?")


def hold_and_note(s, rid: int, pin: str, mode_name: str) -> tuple[str, bool, int, str]:
    """Fire routine ONCE, hold session with reads, collect a note, then stop."""
    r0 = xchg(s, bytes([0x31, rid]))
    start_hex = r0.hex().upper() or "silent"
    positive = is_positive(r0)
    tag = "POSITIVE - firing" if positive else "NOT positive"
    print(f"    0x{rid:02X} start -> {start_hex}   [{tag}]")
    if not positive:
        print("    WARNING: no positive ack from the ECU - this routine is NOT firing")
        print("    (conditionsNotCorrect/immobiliser, or a comms drop). Note may be N/A.")

    stop = threading.Event()
    st = {"drops": 0}

    def keepalive():
        # Re-fire the routine so a MOMENTARY output keeps pulsing (and a latching
        # relay stays energised) while you watch. A steady light = latching output
        # on this pin; a blinking light = a pulsed output (both = a real hit).
        while not stop.is_set():
            r = xchg(s, bytes([0x31, rid]))
            if not r:                       # session dropped -> recover
                if not revive(s):
                    print("\n    !! lost the ECU (revive failed) - check USB/power")
                    return
                st["drops"] += 1
            stop.wait(0.5)

    th = threading.Thread(target=keepalive, daemon=True)
    th.start()
    note = ask(f"        note - did pin {pin} go {mode_name}?  (e.g. y / n / anything): ")
    stop.set()
    th.join(timeout=6)
    xchg(s, bytes([0x32, rid]))             # stop the routine
    if st["drops"]:
        print(f"    (note: {st['drops']} session drop(s) during this one - prefer USB)")
    return start_hex, positive, st["drops"], note


def main():
    target = ask("What are you testing? e.g. 14G (looking for GROUND) "
                 "or 24V (looking for +12V): ")
    pin, mode, mode_name = parse_target(target)
    label = f"pin{pin}{mode}"
    print(f"\n{label}: watching pin {pin} for {mode_name}.")
    print("(GROUND search = clip the test light to +12V; +12V search = clip to ground.)\n")

    # --- 1) baselines (physical states you set; no ECU command) --------------
    print("First, two baselines. Set each state on the bench, observe pin, note it.\n")
    try:
        for base_label, condition in BASELINES:
            note = baseline_note(pin, mode_name, condition)
            log_row(label, pin, mode, base_label, "n/a", "n/a", 0, note)
            print(f"    logged [{base_label}]: {note or '(no note)'}\n")
    except KeyboardInterrupt:
        print("\n(stopped)")
        return

    # --- 2) actuator routines (ignition ON + unlocked session) --------------
    print("Now the actuator routines - make sure IGNITION is ON.\n")
    s = GemsSecureSession(make_transport())
    print("Connecting + unlocking ($27)...")
    try:
        s.connect()
    except (InitError, TransportError, OSError) as e:
        print(f"connect FAILED: {e}\n(ECU powered? L-line tied? Pico advertising / USB in?)")
        return
    if not s.unlock():
        print("unlock FAILED - check L-line/power, retry.")
        s.close()
        return
    print(f"UNLOCKED. Holding each routine steady while you watch. Routines: "
          f"{', '.join(f'0x{r:02X}' for r in ROUTINES)}\n")

    try:
        for rid in ROUTINES:
            ask(f"--- press Enter to fire 0x{rid:02X} (watch pin {pin} for {mode_name}) ---")
            start_hex, positive, drops, note = hold_and_note(s, rid, pin, mode_name)
            log_row(label, pin, mode, f"0x{rid:02X}", start_hex,
                    "yes" if positive else "no", drops, note)
            print(f"    logged 0x{rid:02X} [{label}]: {note or '(no note)'}\n")
    except KeyboardInterrupt:
        print("\n(stopped)")
    finally:
        s.close()
    print(f"Done. {label} results saved to {LOGCSV.name}.")


if __name__ == "__main__":
    main()
