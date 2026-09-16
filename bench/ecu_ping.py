"""ecu_ping.py - is the ECU actually responding? (adapter vs ECU triage)

Splits a failed connect into its two independent layers so you know WHICH one
is broken, instead of guessing:

  1. laptop <-> Pico adapter  (BLE/USB link) - proven by the adapter PING.
  2. Pico <-> ECU K-line      (5-baud init at 0x33) - proven by a real init.

Verdicts:
  - adapter PING fails            -> the ADAPTER/link is the problem (not the ECU).
  - adapter OK, init OK           -> the ECU is ALIVE and talking. Any higher-level
                                     failure is a gems_t4/software issue, not the ECU.
  - adapter OK, init fails always -> the ECU is NOT answering. Software is fine;
                                     the fault is bench-side (power / K-line / a
                                     dead ECU). Software CANNOT tell those apart -
                                     see the multimeter check it prints.

  python ecu_ping.py            (auto: USB if present, else BLE 'gems-pico')
  GEMS_PORT=COM4 python ecu_ping.py    # force USB
  GEMS_BLE=gems-pico python ecu_ping.py  # force/name BLE
"""
from __future__ import annotations
import os
import time

from gems_t4.transport.base import InitError, TransportError, TransportTimeout

KLINE_INIT_ADDRESS = 0x33          # the confirmed GEMS 5-baud address
ATTEMPTS = 4
PACE_S = 1.0                        # gap between init attempts (the ECU holds a
                                   # just-closed session for a few seconds)


def make_transport():
    port = os.environ.get("GEMS_PORT")
    if not port:
        try:
            from gems_t4.transport.pico import find_pico_port
            port = find_pico_port()
        except Exception:  # noqa: BLE001
            port = None
    if port:
        from gems_t4.transport.pico import PicoAdapterTransport
        print(f"[transport: USB {port}]")
        return PicoAdapterTransport(port)
    from gems_t4.transport.ble import BleTransport
    name = os.environ.get("GEMS_BLE", "gems-pico")
    print(f"[transport: BLE {name}]")
    return BleTransport(name)


def main() -> int:
    t = make_transport()

    # ---- Layer 1: the laptop <-> Pico adapter link -----------------------
    print("\n[1/2] Adapter link (laptop <-> Pico)...")
    try:
        t.open()
    except (TransportError, OSError) as e:
        print(f"  FAIL: can't open the adapter link: {e}")
        print("  -> The ADAPTER/link is the problem, not the ECU. Check the Pico is")
        print("     powered and (BLE) advertising as 'gems-pico' / (USB) on its COM port.")
        return 2
    try:
        fw = t.ping()
        fw = fw.decode("ascii", "replace").strip() if isinstance(fw, (bytes, bytearray)) else str(fw)
        print(f"  OK: Pico answered - firmware '{fw}'")
    except (TransportError, TransportTimeout, OSError) as e:
        print(f"  FAIL: Pico did not answer PING: {e}")
        print("  -> The ADAPTER is not responding (power-cycle it / re-flash). Not the ECU.")
        t.close()
        return 2

    # ---- Layer 2: the Pico <-> ECU K-line 5-baud init --------------------
    print(f"\n[2/2] ECU K-line init (5-baud @ 0x{KLINE_INIT_ADDRESS:02X}), "
          f"{ATTEMPTS} attempts...")
    last = None
    for i in range(1, ATTEMPTS + 1):
        try:
            res = t.init(KLINE_INIT_ADDRESS, "slow")
            kb = getattr(res, "keybytes", b"")
            kb = kb.hex() if isinstance(kb, (bytes, bytearray)) else kb
            print(f"  attempt {i}: OK - ECU responded (keybytes {kb})")
            print("\n==> ECU is ALIVE and talking. The adapter and the ECU are both fine,")
            print("    so any failure in a gems_t4 command is a SOFTWARE issue, not the ECU.")
            t.close()
            return 0
        except (InitError, TransportTimeout, TransportError) as e:
            last = e
            print(f"  attempt {i}: no response ({e})")
            if i < ATTEMPTS:
                time.sleep(PACE_S)
    t.close()

    # All init attempts failed, but the adapter is proven good.
    print(f"\n==> The Pico is fine (firmware answered), but the ECU did NOT respond to")
    print(f"    the K-line init after {ATTEMPTS} tries (last: {last}).")
    print("    This is NOT a Bluetooth/adapter/gems_t4 problem - it's bench-side.")
    print("    Software cannot tell 'ECU unpowered' from 'K-line open' from 'ECU dead';")
    print("    ONE multimeter reading settles it:\n")
    print("    * K-line idle voltage (L9637D pin 6 / C1017 pin 23) to ground:")
    print("        ~12 V  -> K-line + pull-up + power are good; the ECU just isn't")
    print("                  answering (re-seat K-line; suspect a dead/immobilised ECU).")
    print("        ~0 V   -> no pull-up / no power on the K node -> check the 510 ohm")
    print("                  pull-up to Vs and that the ECU main relay is powered.")
    print("    * ECU power: ~12 V at C1033 pin 7 (main) AND pin 8 (ignition), grounds")
    print("      (C1033 5/9/10/16) solid to the PSU negative.")
    print("    If K idles ~12 V and power/grounds are good but init still fails on a")
    print("    known-good harness, the ECU itself is the prime suspect.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
