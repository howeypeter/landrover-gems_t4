"""GEMS actuator bench tester — guided. Fire output routines, find + log pins.

Walks you through unlocking the ECU and firing output routines one at a time so
you can locate each system's pin with a multimeter. It explains what it's doing
and what each ECU reply means as it goes. Results are logged to actuator_map.csv.

  python actuator_test.py            (BLE, Pico advertising as 'gems-pico')
  GEMS_PORT=COM5 python actuator_test.py   (USB instead)
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

NRC = {0x10: "generalReject", 0x11: "serviceNotSupported", 0x12: "subFunctionNotSupported",
       0x22: "conditionsNotCorrect", 0x31: "requestOutOfRange", 0x33: "securityAccessDenied",
       0x35: "invalidKey", 0x78: "responsePending"}
NAMED: dict[int, str] = {}                     # id -> name, grows as you identify
LOGCSV = Path(__file__).with_name("actuator_map.csv")


def make_transport():
    """Pick a transport. Precedence: an EXPLICIT env var wins, GEMS_CONNECT first
    (so switching to WiFi isn't overridden by a stale GEMS_PORT / an auto-detected
    USB Pico), then GEMS_PORT, then a plugged Pico, then BLE. Matches the other
    bench scripts (pentest_scan / probe_10as).
      - GEMS_CONNECT=host[:port]  -> WiFi/TCP
      - GEMS_PORT=COMx            -> that USB port
      - (else) a plugged Pico is auto-detected; else BLE ('gems-pico').
    """
    conn = os.environ.get("GEMS_CONNECT")
    if conn:
        from gems_t4.transport.tcp import TcpTransport, parse_endpoint
        host, tcp_port = parse_endpoint(conn)
        print(f"[transport: WiFi {host}:{tcp_port}]")
        return TcpTransport(host, tcp_port, allow_writes=True)
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
    print(f"[transport: BLE {name}]")
    return BleTransport(name)


def xchg(s, payload: bytes) -> bytes:
    """Send one routine and return the reply, or b'' on timeout/comms error so a
    silent/slow id never crashes the scan."""
    try:
        return s._exchange(payload)
    except (TransportTimeout, TransportError, OSError):
        return b""


def revive(s, tries: int = 4) -> bool:
    """Re-init + re-unlock the 0xDA session (it drops after an idle gap, which
    makes every request go silent). Retries a few times - a BLE reconnect often
    needs a second attempt. Returns True once unlocked again."""
    for i in range(tries):
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


def explain(r: bytes) -> tuple[bool, str]:
    """(accepted?, human explanation) for an ECU reply to $31."""
    if not r:
        return False, "no reply (silent) - not a valid routine, or a comms glitch."
    if r[0] == 0x7F and len(r) >= 3:
        nrc = r[2]
        msg = {
            0x11: "serviceNotSupported - not a routine id.",
            0x12: "subFunctionNotSupported - not a routine id.",
            0x31: "requestOutOfRange - no routine at this id.",
            0x22: "conditionsNotCorrect - a REAL routine, but a precondition isn't "
                  "met (engine state, or the immobiliser on a bench ECU).",
            0x33: "securityAccessDenied - lost the unlock (restart the tool).",
            0x78: "responsePending - ECU is working on it (this usually means it fired).",
        }.get(nrc, f"negative NRC 0x{nrc:02X}.")
        return nrc == 0x78, msg
    return True, f"ACCEPTED (positive reply {r.hex().upper()}) - it likely fired."


def log_row(rid: int, reply: str, pin: str, name: str, note: str) -> None:
    new = not LOGCSV.exists()
    with open(LOGCSV, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["time", "routine_id", "reply", "pin", "name", "note"])
        w.writerow([datetime.now().strftime("%H:%M:%S"), f"0x{rid:02X}", reply, pin, name, note])


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except EOFError:
        return "q"


def intro():
    print("=" * 66)
    print(" GEMS actuator finder")
    print("=" * 66)
    print(" Before you start, on the bench:")
    print("  - ECU powered, L-line tied to the K node, ignition ON")
    print("  - Pico powered + advertising as 'gems-pico' (or set GEMS_PORT=COMx)")
    print("  - Multimeter in CONTINUITY/beep mode:")
    print("      * one probe clipped to ECU GROUND")
    print("      * other probe ready to touch pins on the BLACK 36-pin plug")
    print("        (that plug carries the output drivers - fuel pump, fans, etc.)")
    print(" When a routine fires, the ECU pulls its output pin to ground, so the")
    print(" right pin will BEEP on your meter. That's the pin for that system.")
    print("=" * 66)


def guided_scan(s):
    print("\n-- Scan mode ------------------------------------------------------")
    print(" I'll fire routines one id at a time. For each one I'll tell you what")
    print(" the ECU said. If it was ACCEPTED, sweep your probe over the black")
    print(" 36-pin plug and find the pin that beeps, then type it in.")
    lo = ask(" Start id in hex [default 00]: ") or "00"
    hi = ask(" End id in hex   [default ff]: ") or "ff"
    try:
        lo, hi = int(lo, 16), int(hi, 16)
        assert 0 <= lo <= hi <= 0xFF
    except (ValueError, AssertionError):
        print(" bad range; aborting scan."); return
    print(f"\n Scanning 0x{lo:02X}..0x{hi:02X}. I'll auto-skip ids that do nothing")
    print(" and only STOP to ask you when a routine is ACCEPTED. Ctrl-C to quit.")
    print(" Re-establishing a fresh unlocked session first...")
    if not revive(s):
        print(" could not unlock (bench powered? L-line tied? Pico advertising?). Aborting.")
        return
    print(" session live. Enumerating (no probing yet - just finding which ids fire).\n")
    accepted: list[int] = []
    try:
        for rid in range(lo, hi + 1):
            r = xchg(s, bytes([0x31, rid]))
            if not r:                       # silent => session dropped; recover
                if not revive(s):
                    print("   lost the ECU (link/power?). Stopping scan."); break
                r = xchg(s, bytes([0x31, rid]))
            ok, why = explain(r)
            xchg(s, bytes([0x32, rid]))     # stop immediately - enumerate only
            print(f"   0x{rid:02X}: {'ACCEPTED  ' if ok else ''}{why}")
            log_row(rid, why, "", NAMED.get(rid, ""), "scan")
            if ok:
                accepted.append(rid)
    except KeyboardInterrupt:
        print("\n (stopped)")
    ids = ", ".join(f"0x{i:02X}" for i in accepted) or "none"
    print(f"\n Scan done. ACCEPTED ids: {ids}")
    print(" Next: menu option 2 (fire one routine) to hold each and find its pin.")


def fire_one(s):
    t = ask(" Routine id in hex (e.g. 41): ")
    try:
        rid = int(t, 16); assert 0 <= rid <= 0xFF
    except (ValueError, AssertionError):
        print(" not a valid hex id."); return
    # One confirming shot first: show the ECU's actual response immediately.
    r0 = xchg(s, bytes([0x31, rid]))
    ok0, why0 = explain(r0)
    print(f"    start 0x{rid:02X} -> {(r0.hex().upper() or 'silent')}   ({why0})")
    print(f"    Holding 0x{rid:02X}. Status prints ~every 2s - 'ack' should climb")
    print("    steadily with drop=0 (that = the ECU is holding it). Probe now.")
    stop = threading.Event()
    state = {"why": why0, "lost": False, "ok": 0, "drop": 0, "sent": 0, "last": 0.0}

    def worker():
        while not stop.is_set():
            r = xchg(s, bytes([0x31, rid]))     # re-assert so the output stays active
            if not r:                            # silent => session dropped; recover
                if not revive(s):
                    state["lost"] = True
                    print("\n    !! lost the ECU (no response, revive failed)")
                    return
                r = xchg(s, bytes([0x31, rid]))
            ok, why = explain(r)
            state["why"] = why
            state["sent"] += 1
            state["ok" if ok else "drop"] += 1
            now = time.time()
            if now - state["last"] > 2.0:        # throttle so it stays readable
                state["last"] = now
                print(f"    held 0x{rid:02X}: sent={state['sent']} "
                      f"ack={state['ok']} drop={state['drop']}  "
                      f"last={(r.hex().upper() or 'silent')}")
            stop.wait(0.8)

    th = threading.Thread(target=worker, daemon=True)
    th.start()
    ask("    (probing... press Enter to STOP) ")
    stop.set()
    th.join(timeout=6)
    xchg(s, bytes([0x32, rid]))                  # stop; never leave it latched
    print(f"    stopped. sent={state['sent']} ack(positive)={state['ok']} drop={state['drop']}")
    if state["sent"] and state["drop"] == 0 and not state["lost"]:
        print("    => the ECU acked EVERY command - the routine was held solidly the whole")
        print("       time. If the light still flickered, that's ELECTRICAL (an unloaded")
        print("       low-side output floating), not the script.")
    elif state["drop"] or state["lost"]:
        print("    => NOT every response was positive - either comms drops (switch to USB!)")
        print("       or the routine won't re-arm (precondition/immobiliser). That's the flicker.")
    why = state["why"]
    pin = ask("    Which pin reacted? (blank = none): ")
    nm = ask("    Name it? (optional): ") if pin else ""
    if pin and nm:
        NAMED[rid] = nm
    log_row(rid, why, pin, nm, "hold")
    print("    logged." if pin else "    done.")


def main():
    intro()
    input("\n Press Enter when the bench is ready... ")
    s = GemsSecureSession(make_transport())
    print("\n Connecting and unlocking the ECU ($27 SecurityAccess)...")
    try:
        s.connect()
    except (InitError, TransportError, OSError) as e:
        print(f" connect FAILED: {e}")
        print(" -> Is the ECU powered, L-line tied, and the Pico advertising as")
        print("    'gems-pico'? For USB: set GEMS_PORT=COMx. Then run me again.")
        return
    if not s.unlock():
        print(" unlock FAILED (no accept). Check L-line/power and retry.")
        s.close(); return
    print(f" UNLOCKED - channel open. Logging to {LOGCSV.name}\n")
    try:
        while True:
            print("-" * 40)
            print(" 1) Scan for actuators (guided)")
            print(" 2) Fire one routine by id")
            print(" 3) Show what I've found so far")
            print(" 4) Quit")
            choice = ask(" Choose 1-4: ")
            if choice == "1":
                guided_scan(s)
            elif choice == "2":
                fire_one(s)
            elif choice == "3":
                print("  found:", {f"0x{k:02X}": v for k, v in NAMED.items()} or "(nothing yet)")
                print(f"  full log: {LOGCSV}")
            elif choice in ("4", "q", "quit"):
                break
            else:
                print("  please type 1, 2, 3, or 4.")
    finally:
        s.close()
        print("\n Closed. Your results are in", LOGCSV.name)


if __name__ == "__main__":
    main()
