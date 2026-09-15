"""actuator_hunt.py — find the GEMS output-control command, watching pin 1 (A/C).

We proved $31 isn't the actuator command (outputs are driven while immobilised -
the MIL blinks at key-on - yet $31 moves nothing). This hunts the real command
INTERACTIVELY: you send one command at a time on the unlocked 0xDA channel and
watch pin 1 (A/C compressor-clutch relay) - it's OFF at baseline and non-gated,
so a hit shows as the relay clicking / a 0-5V swing on pin 1.

SAFETY: this sends whatever you type. Reads (22/21/1A...) are safe. WRITE/action
services MUTATE the ECU:
  - $2E writes coding.  - $3D writes memory.  - $A3 is the manufacturer
    action service - our IMMOBILISER-SYNCH lives there (A300622588). DO NOT send
    A3 00 62 25 88 (it pairs/immobilises). Blind A3 pokes are dangerous.
Only send mutating commands deliberately. Everything is logged.

  python actuator_hunt.py
Commands:  map | send <hex...> | q       (e.g.  send 31 01 01)
"""
from __future__ import annotations
import os
import time
from datetime import datetime
from pathlib import Path
from gems_t4.protocol.gems_secure import GemsSecureSession
from gems_t4.transport.base import InitError, TransportError, TransportTimeout

LOG = Path(__file__).with_name("actuator_hunt.log")
NRC = {0x10: "generalReject", 0x11: "serviceNotSupported", 0x12: "subFunctionNotSupported",
       0x22: "conditionsNotCorrect", 0x31: "requestOutOfRange", 0x33: "securityAccessDenied",
       0x35: "invalidKey", 0x78: "responsePending"}

# SAFE service-existence probes (reads/queries only - no writes/actuation).
# minimal payloads; we only classify supported-vs-not, not the data.
MAP_PROBES = [
    ("22 read-coding",        [0x22, 0x04, 0xBF]),
    ("21 readDataByLocalId",  [0x21, 0x00]),
    ("1A readEcuId",          [0x1A, 0x00]),
    ("23 readMemByAddr",      [0x23, 0x00, 0x00, 0x00]),
    ("2F IOControlByCommonId",[0x2F, 0x00, 0x00]),
    ("30 IOControlByLocalId", [0x30, 0x00]),
    ("31 StartRoutine",       [0x31, 0x00]),
    ("3E TesterPresent",      [0x3E, 0x00]),
    ("18 readDTCbyStatus",    [0x18, 0x00, 0xFF, 0x00]),
    ("17 readStatusOfDTC",    [0x17, 0x00]),
]


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
    print(f"[transport: BLE {name}]")
    return BleTransport(name)


def xchg(s, payload: bytes) -> bytes:
    try:
        return s._exchange(payload)
    except (TransportTimeout, TransportError, OSError):
        return b""


def classify(r: bytes) -> str:
    if not r:
        return "silent"
    if r[0] == 0x7F and len(r) >= 3:
        return f"NRC {r[2]:02X} {NRC.get(r[2], '?')}"
    return f"POSITIVE {r.hex().upper()}"


def logline(msg: str) -> None:
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%H:%M:%S')}  {msg}\n")


def main():
    s = GemsSecureSession(make_transport())
    try:
        s.connect()
    except (InitError, TransportError, OSError) as e:
        print(f"connect FAILED: {e}"); return
    if not s.unlock():
        print("unlock FAILED"); s.close(); return
    print("UNLOCKED.\n")
    logline("=== session start ===")

    print("Watch PIN 1 (A/C clutch relay) - OFF at baseline. A hit = it clicks /")
    print("a meter on pin 1 swings. Try 'map' first, then 'send <hex>' one at a time.")
    print("Commands:  map | send <hex...> | q\n")
    print("Ideas to try (watch pin 1 each time):")
    print("  - $31 sub-forms (low risk):   send 31 01 01   / send 31 04 01")
    print("  - OBD-style output control:   send 2F 00 01 00 / send 30 01 01")
    print("  - manufacturer action $A3 (RISKY - mutates; NEVER 'A3 00 62 25 88'):")
    print("      only if you accept the immobilise risk on a SPARE ecu.\n")

    def do_send(hexstr: str):
        try:
            payload = bytes(int(b, 16) for b in hexstr.split())
        except ValueError:
            print("  bad hex"); return
        if not payload:
            print("  empty"); return
        r = xchg(s, payload)
        if not r and s.connect() is not None and not s.unlock():
            pass  # best-effort; ignore revive noise
        out = classify(r)
        print(f"  -> {out}")
        logline(f"send {payload.hex().upper()} -> {out}")

    try:
        while True:
            try:
                line = input("hunt> ").strip()
            except EOFError:
                break
            if not line:
                continue
            if line in ("q", "quit", "exit"):
                break
            if line == "map":
                print(" service map (safe reads):")
                for name, p in MAP_PROBES:
                    r = xchg(s, bytes(p))
                    print(f"   {name:24s} {bytes(p).hex().upper():12s} -> {classify(r)}")
                    logline(f"map {name} {bytes(p).hex().upper()} -> {classify(r)}")
                continue
            if line.startswith("send "):
                do_send(line[5:])
                continue
            print("  usage: map | send <hex...> | q")
    finally:
        s.close()
    print(f"\nlogged to {LOG.name}")


if __name__ == "__main__":
    main()
