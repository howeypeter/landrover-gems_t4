"""live_diff.py — snapshot the $21 live-data fields and DIFF between snapshots.

Use it to identify which $21 id is which sensor: snapshot, change one input
(e.g. jumper C1017 pin 15 / TPS to ground or to Pico VBUS 5V), snapshot again,
and it prints exactly which ids moved. The id that swings = that sensor.

  python live_diff.py
Commands:  snap [label] | q
Workflow for TPS (C1017 pin 15):
  snap rest      (pin untouched)
  ...jumper pin 15 -> Pico VBUS (5V)...     snap 5v
  ...jumper pin 15 -> ground...             snap gnd
  -> the id listed as changed is Throttle Position.
"""
from __future__ import annotations
import os
import time
from gems_t4.protocol.gems_secure import GemsSecureSession
from gems_t4.transport.base import InitError, TransportError, TransportTimeout

PACE_S = 0.12
BACKOFF_S = [0.4, 0.8, 1.5]


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
    print("[transport: BLE gems-pico]  (USB is steadier)")
    return BleTransport(os.environ.get("GEMS_BLE", "gems-pico"))


def _raw(s, payload):
    try:
        return s._exchange(payload)
    except (TransportTimeout, TransportError, OSError):
        return b""


def revive(s, tries=4):
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


def robust(s, payload):
    time.sleep(PACE_S)
    r = _raw(s, payload)
    if r:
        return r
    for wait in BACKOFF_S:
        time.sleep(wait)
        r = _raw(s, payload)
        if r:
            return r
    revive(s)
    time.sleep(PACE_S)
    return _raw(s, payload)


def value_of(r):
    """Return the data-hex for a positive $21 reply, else None."""
    if not r or (r[0] == 0x7F):
        return None
    return (r[2:] if len(r) >= 2 and r[0] == 0x61 else r).hex().upper()


def snapshot(s):
    out = {}
    t0 = time.time()
    total = 0x100
    for rid in range(total):
        v = value_of(robust(s, bytes([0x21, rid])))
        if v is not None:
            out[rid] = v
        done = rid + 1
        el = time.time() - t0
        rate = done / el if el else 0
        eta = (total - done) / rate if rate else 0
        # in-place status line: percent, count, elapsed, ETA, hits so far
        print(f"\r  scanning 21 00..FF  {done * 100 // total:3d}%  "
              f"[{done:3d}/{total}]  {el:5.1f}s elapsed  ~{eta:4.0f}s left  "
              f"{len(out):3d} hits ", end="", flush=True)
    print(f"\r  scan done: {len(out)} ids returned data in {time.time() - t0:.1f}s"
          + " " * 20)
    return out


def changes(prev, cur):
    ids = sorted(set(prev) | set(cur))
    return [(i, prev.get(i), cur.get(i)) for i in ids if prev.get(i) != cur.get(i)]


def ask(prompt):
    try:
        return input(prompt)
    except EOFError:
        return ""


def log_map(label, ids, base, hi, lo):
    import csv
    from pathlib import Path
    path = Path(__file__).with_name("live_map.csv")
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["label", "id", "rest", "at_5v", "at_gnd"])
        if not ids:
            w.writerow([label, "(none moved)", "", "", ""])
        for i in ids:
            w.writerow([label, f"0x{i:02X}", base.get(i, ""), hi.get(i, ""), lo.get(i, "")])
    return path.name


def main():
    s = GemsSecureSession(make_transport())
    try:
        s.connect()
    except (InitError, TransportError, OSError) as e:
        print(f"connect FAILED: {e}"); return
    if not s.unlock():
        print("unlock FAILED"); s.close(); return
    print("UNLOCKED.\n")
    print("Guided sensor mapping. For each pin I'll snapshot $21 three ways -")
    print("untouched, at +5V (Pico VBUS pin 40), at ground - and tell you which id")
    print("moved. Change ONLY the one pin you're testing. Each snap takes ~30s.\n")

    try:
        while True:
            label = ask("What are you testing? (e.g. 'C1017 p15 TPS'), Enter to quit: ").strip()
            if not label:
                break
            ask("  1/3  Leave the pin UNTOUCHED (rest). Press Enter to snapshot...")
            base = snapshot(s)
            print(f"       {len(base)} ids returned data.")

            ask("  2/3  Jumper the pin to +5V (Pico VBUS, pin 40). Press Enter...")
            hi = snapshot(s)
            ch_hi = {i: (a, b) for i, a, b in changes(base, hi)}

            ask("  3/3  Jumper the pin to GROUND. Press Enter...")
            lo = snapshot(s)
            ch_lo = {i: (a, b) for i, a, b in changes(base, lo)}

            print(f"\n  --- result for '{label}' ---")
            if ch_hi:
                print("  moved at +5V: " + ", ".join(
                    f"0x{i:02X} ({base.get(i)}->{ch_hi[i][1]})" for i in sorted(ch_hi)))
            if ch_lo:
                print("  moved at GND: " + ", ".join(
                    f"0x{i:02X} ({base.get(i)}->{ch_lo[i][1]})" for i in sorted(ch_lo)))
            both = sorted(set(ch_hi) & set(ch_lo))
            any_moved = sorted(set(ch_hi) | set(ch_lo))
            if both:
                print(f"  >>> BEST match for '{label}' (swings BOTH ways): "
                      + ", ".join(f"0x{i:02X}" for i in both))
                ids = both
            elif any_moved:
                print(f"  >>> candidate(s) for '{label}': "
                      + ", ".join(f"0x{i:02X}" for i in any_moved))
                ids = any_moved
            else:
                print("  no ids moved - check the jumper contact / right pin / RED connector.")
                ids = []
            fn = log_map(label, ids, base, hi, lo)
            print(f"  logged to {fn}\n")
    finally:
        s.close()
    print("done.")


if __name__ == "__main__":
    main()
