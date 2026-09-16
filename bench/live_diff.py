"""live_diff.py — snapshot the $21 live-data fields and DIFF between snapshots.

Use it to identify which $21 id is which sensor: snapshot, change one input
(e.g. jumper C1017 pin 15 / TPS to ground or to Pico VBUS 5V), snapshot again,
and it prints exactly which ids moved. The id that swings = that sensor.

  python live_diff.py map          # guided rest / +5V / ground snapshot diff
  python live_diff.py watch 2B     # poll ONE id live while you turn a pot
  python live_diff.py              # interactive menu (map | watch <id> | q)

'watch' is the definitive test: a real analog sensor (e.g. TPS on C1017 pin 15)
tracks a pot smoothly across a range; a derived flag just snaps between two
values on 'clamped vs floating'. 'map' finds candidate ids; 'watch' confirms.
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


def log_map(label, ids, level_names, snaps):
    """Append one row per moved id, with its value at every level tested."""
    import csv
    from pathlib import Path
    path = Path(__file__).with_name("live_map.csv")
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["label", "id"] + level_names)
        if not ids:
            w.writerow([label, "(none moved)"] + [""] * len(level_names))
        for i in ids:
            w.writerow([label, f"0x{i:02X}"] + [snaps[n].get(i, "") for n in level_names])
    return path.name


def watch_id(s, rid):
    """Poll ONE $21 id continuously and print its value live, so you can turn a
    pot / vary the voltage on a pin and watch the field track. Ctrl-C to stop.
    A real analog sensor (e.g. TPS) rises and falls smoothly with the voltage;
    a derived flag just snaps between two values on 'clamped vs floating'."""
    import csv
    from datetime import datetime
    from pathlib import Path
    try:
        import msvcrt          # Windows: non-blocking key reads for annotation
    except ImportError:
        msvcrt = None
    logp = Path(__file__).with_name(f"watch_{rid:02X}.csv")
    print(f"\n  watching 0x{rid:02X} live - vary the voltage on the pin now.")
    print("  (a real sensor tracks the pot smoothly; a flag just snaps.)  Ctrl-C to stop.")
    if msvcrt:
        print("  ANNOTATE the trace as you change the input - press a key:")
        print("    v = +5V    4 = 4.5V    g = GND    f = FLOATING    . = other mark")
    print(f"  logging every read to {logp.name}\n")
    marks = {"v": "5V", "4": "4.5V", "g": "GND", "f": "FLOAT", ".": "mark"}
    state = ""                 # current annotation, carried on every row until changed
    lo = hi = None
    t0 = time.time()
    n = 0
    logf = open(logp, "w", newline="", encoding="utf-8")
    lw = csv.writer(logf)
    lw.writerow(["t_s", "iso_time", "id", "raw_hex", "value_dec", "state", "event"])
    try:
        while True:
            event = ""
            if msvcrt and msvcrt.kbhit():          # a key was pressed -> annotate
                k = msvcrt.getwch().lower()
                if k in marks:
                    state = event = marks[k]
            v = value_of(robust(s, bytes([0x21, rid])))
            n += 1
            el = time.time() - t0
            tag = f" <{state}>" if state else ""
            if v is None:
                lw.writerow([f"{el:.2f}", datetime.now().isoformat(timespec="seconds"),
                             f"0x{rid:02X}", "", "", state, event])
                print(f"\r  0x{rid:02X}: (silent){tag}            ", end="", flush=True)
            else:
                iv = int(v[:4], 16) if len(v) >= 4 else int(v, 16)  # first word as a number
                lw.writerow([f"{el:.2f}", datetime.now().isoformat(timespec="seconds"),
                             f"0x{rid:02X}", v, iv, state, event])
                lo = iv if lo is None else min(lo, iv)
                hi = iv if hi is None else max(hi, iv)
                bar_lo, bar_hi = (lo, hi) if hi != lo else (iv, iv + 1)
                pos = int((iv - bar_lo) / (bar_hi - bar_lo) * 30)
                bar = "#" * pos + "-" * (30 - pos)
                print(f"\r  0x{rid:02X}: {v:<8} = {iv:5d}  [{bar}]  "
                      f"min {lo} max {hi}{tag}   ", end="", flush=True)
            logf.flush()
            time.sleep(0.05)
    except KeyboardInterrupt:
        logf.close()
        span = (hi - lo) if (hi is not None and lo is not None) else 0
        el = time.time() - t0
        print(f"\n  stopped. {n} reads in {el:.0f}s. range seen: {lo}..{hi} (span {span}).")
        print(f"  full trace saved to {logp.name}")
        if span > 8:
            print("  -> it MOVED across a range: looks like a real analog channel.")
        elif span > 0:
            print("  -> only tiny movement: probably not the sensor (or didn't vary enough).")
        else:
            print("  -> no movement: not this id, or the voltage didn't change.")


# The voltage steps the wizard walks you through, in order. "rest" is the
# baseline (nothing connected); the rest are held levels. Injecting several
# levels lets a real analog sensor reveal itself: its value should climb
# monotonically GND -> 3.3V -> 4.5V -> 5V. A flag only snaps between two values.
MAP_LEVELS = [
    ("rest", "Leave the pin UNTOUCHED (floating baseline)"),
    ("GND",  "Jumper the pin to GROUND      (Pico pin 38, GND)"),
    ("3.3V", "Jumper the pin to +3.3V       (Pico pin 36, 3V3 OUT)"),
    ("4.5V", "Jumper the pin to +4.5V       (Pico pin 39, VSYS ~4.5-4.7V)"),
    ("5V",   "Jumper the pin to +5V         (Pico pin 40, VBUS)"),
]


def guided_map(s):
    names = [n for n, _ in MAP_LEVELS]
    print("Guided sensor mapping. For each pin I'll snapshot $21 at several")
    print("voltages - " + ", ".join(names) + " - and show each id's value at every")
    print("level. A real analog sensor climbs across the levels; a flag just snaps.")
    print(f"Change ONLY the one pin you're testing. {len(MAP_LEVELS)} snaps x ~30s each.\n")
    while True:
        label = ask("What are you testing? (e.g. 'C1017 p15 TPS'), Enter to quit: ").strip()
        if not label:
            break
        snaps = {}
        for idx, (name, instr) in enumerate(MAP_LEVELS, 1):
            ask(f"  {idx}/{len(MAP_LEVELS)}  {instr}. Press Enter to snapshot...")
            snaps[name] = snapshot(s)
            print(f"       [{name}] {len(snaps[name])} ids returned data.")

        base = snaps["rest"]
        levels = names[1:]                       # the held voltages (not rest)
        # An id "moved" if it differs from rest at any held level.
        moved = sorted({i for n in levels for i, a, b in changes(base, snaps[n])})

        print(f"\n  --- result for '{label}' ---")
        if not moved:
            print("  no ids moved - check the jumper contact / right pin / RED connector.")
        else:
            # Rank: ids taking the MOST distinct values across all levels first
            # (a real analog channel steps through several; a flag has ~2).
            def distinct(i):
                return len({snaps[n].get(i) for n in names if i in snaps[n]})
            print(f"  {'id':<6}" + "".join(f"{n:<10}" for n in names) + "distinct")
            for i in sorted(moved, key=distinct, reverse=True):
                row = "".join(f"{(snaps[n].get(i) or '-'):<10}" for n in names)
                print(f"  0x{i:02X}  {row}{distinct(i)}")
            top = max(moved, key=distinct)
            if distinct(top) >= 3:
                print(f"  >>> BEST analog candidate for '{label}': 0x{top:02X} "
                      f"(takes {distinct(top)} distinct values across the sweep)")
            else:
                print(f"  >>> only 2-state changes - likely flags, not '{label}'. "
                      "Confirm a candidate with:  watch <id>")
        fn = log_map(label, moved, names, snaps)
        print(f"  logged to {fn}\n")


def parse_args(argv):
    import argparse
    p = argparse.ArgumentParser(
        description="GEMS $21 sensor-ID tools (guided map, or watch one id live).")
    sub = p.add_subparsers(dest="mode")
    sub.add_parser("map", help="guided sensor mapping (snapshot at rest / +5V / ground)")
    w = sub.add_parser("watch", help="poll ONE id live while you vary the voltage")
    w.add_argument("id", help="hex $21 id to watch, 00..FF (e.g. 2B)")
    return p.parse_args(argv)


def interactive(s):
    print("Commands:")
    print("  map          - guided sensor mapping (snapshot at rest / +5V / ground)")
    print("  watch <id>   - poll ONE id live while you vary the voltage (e.g. watch 2B)")
    print("  q            - quit\n")
    while True:
        try:
            line = input("live> ").strip()
        except EOFError:
            break
        if not line or line in ("q", "quit", "exit"):
            break
        if line == "map":
            guided_map(s)
        elif line.startswith("watch"):
            rid = parse_id(line[5:].strip())
            if rid is None:
                print("  usage: watch <hex id 00..FF>, e.g. watch 2B"); continue
            watch_id(s, rid)
        else:
            print("  usage: map | watch <id> | q")


def parse_id(arg):
    try:
        rid = int(arg, 16)
    except (ValueError, TypeError):
        return None
    return rid if 0 <= rid <= 0xFF else None


def main(argv=None):
    import sys
    args = parse_args(sys.argv[1:] if argv is None else argv)
    rid = None
    if args.mode == "watch":
        rid = parse_id(args.id)
        if rid is None:
            print(f"bad id '{args.id}' - want a hex value 00..FF, e.g. 2B"); return

    s = GemsSecureSession(make_transport())
    try:
        s.connect()
    except (InitError, TransportError, OSError) as e:
        print(f"connect FAILED: {e}"); return
    if not s.unlock():
        print("unlock FAILED"); s.close(); return
    print("UNLOCKED.\n")
    try:
        if args.mode == "watch":
            watch_id(s, rid)
        elif args.mode == "map":
            guided_map(s)
        else:
            interactive(s)          # no subcommand -> menu
    finally:
        s.close()
    print("done.")


if __name__ == "__main__":
    main()
