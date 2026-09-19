"""live_diff.py — snapshot the $21 live-data fields and DIFF between snapshots.

Use it to identify which $21 id is which sensor: snapshot, change one input
(e.g. jumper C1017 pin 15 / TPS to ground or to Pico VBUS 5V), snapshot again,
and it prints exactly which ids moved. The id that swings = that sensor.

  python live_diff.py map          # guided ANALOG pot sweep (min/mid/max) diff
  python live_diff.py switch       # guided SWITCH map (float -> ground -> float)
  python live_diff.py watch 2B     # poll ONE id live while you turn a pot
  python live_diff.py              # interactive menu (map | switch | watch <id> | q)

Use 'map' for analog sensors (throttle, MAF, temps) with the 0-5V pot; use
'switch' for two-state inputs (A/C request, heated screen, brake) - do NOT
inject voltage on those, just ground vs float the pin.

'watch' is the definitive test: a real analog sensor (e.g. TPS on C1017 pin 15)
tracks a pot smoothly across a range; a derived flag just snaps between two
values on 'clamped vs floating'. 'map' finds candidate ids; 'watch' confirms.
"""
from __future__ import annotations
import os
import time
from gems_t4.protocol.gems_secure import GemsSecureSession
from gems_t4.transport.base import InitError, TransportError, TransportTimeout

PACE_S = 0.03          # gap before each request (ECU keeps up fine at this rate)
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


def snapshot(s, ids=None):
    """Read the given $21 ids (default all 00..FF). Pass the responders from a
    prior full scan to poll ONLY those - skipping the ~156 silent ids roughly
    halves the scan (and the time you have to hold the pot)."""
    id_list = list(range(0x100)) if ids is None else list(ids)
    total = len(id_list)
    out = {}
    t0 = time.time()
    for done, rid in enumerate(id_list, 1):
        v = value_of(robust(s, bytes([0x21, rid])))
        if v is not None:
            out[rid] = v
        el = time.time() - t0
        rate = done / el if el else 0
        eta = (total - done) / rate if rate else 0
        print(f"\r  scanning $21 ({total} ids)  {done * 100 // total:3d}%  "
              f"[{done:3d}/{total}]  {el:5.1f}s  ~{eta:4.0f}s left  "
              f"{len(out):3d} hits ", end="", flush=True)
    print(f"\r  scan done: {len(out)}/{total} ids returned data in "
          f"{time.time() - t0:.1f}s" + " " * 20)
    return out


def changes(prev, cur):
    ids = sorted(set(prev) | set(cur))
    return [(i, prev.get(i), cur.get(i)) for i in ids if prev.get(i) != cur.get(i)]


def drain_input():
    """Discard any keystrokes buffered during a long scan, so the next prompt
    genuinely waits instead of being auto-answered by a stray Enter."""
    try:
        import msvcrt
        while msvcrt.kbhit():
            msvcrt.getwch()
    except Exception:  # noqa: BLE001  (non-Windows / no console)
        pass


def ask(prompt, fresh=False):
    if fresh:
        drain_input()
    try:
        return input(prompt)
    except EOFError:
        return ""


def log_map(label, ids, level_names, snaps):
    """Append one row per moved id, with its value at every level tested.

    If the existing file's header doesn't match the current level order (e.g.
    the levels were reordered between runs), the old file is rotated aside so
    rows never land under a mismatched header - the misalignment that made a
    prior live_map.csv label mid/max/min columns as min/mid/max."""
    import csv
    from datetime import datetime
    from pathlib import Path
    ts = datetime.now().isoformat(timespec="seconds")
    header = ["time", "label", "id"] + level_names
    path = Path(__file__).with_name("live_map.csv")
    if path.exists():
        first = path.read_text(encoding="utf-8").splitlines()[:1]
        if first and first[0].split(",") != header:
            path.rename(path.with_name(f"live_map.{ts.replace(':', '')}.csv"))
    new = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(header)
        if not ids:
            w.writerow([ts, label, "(none moved)"] + [""] * len(level_names))
        for i in ids:
            w.writerow([ts, label, f"0x{i:02X}"] + [snaps[n].get(i, "") for n in level_names])
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


# The steps the wizard walks you through, in order, using your ISOLATED 0-5V
# pot injected on the sensor pin (NOT the Pico's rails). Just sweep the pot
# min -> mid -> max; the id that climbs across those three is the sensor. The
# FIRST level is the baseline the others are compared against, so a real analog
# channel shows as "changed", while ids unaffected by voltage stay put.
MAP_LEVELS = [
    ("mid", "RELEASE the pot to its centre (~2.5 V) - the easy one, no holding"),
    ("max", "Hold the pot at MAXIMUM (~5 V)"),
    ("min", "Hold the pot at MINIMUM (~0 V)"),
]


def _resp_cache():
    from pathlib import Path
    return Path(__file__).with_name("live_responders.json")


def load_responders():
    """The ids that answered last time (cached), so even the FIRST scan skips
    the ~156 silent ids. Returns a sorted id list, or None if no cache."""
    import json
    p = _resp_cache()
    if not p.exists():
        return None
    try:
        ids = sorted(int(x) for x in json.loads(p.read_text()))
        return ids or None
    except Exception:  # noqa: BLE001 - a bad cache just means full scan
        return None


def save_responders(ids):
    import json
    try:
        _resp_cache().write_text(json.dumps(sorted(int(i) for i in ids)))
    except Exception:  # noqa: BLE001
        pass


def guided_map(s):
    names = [n for n, _ in MAP_LEVELS]
    print("Guided sensor mapping with your isolated 0-5V pot. For each pin I'll")
    print("snapshot $21 at " + ", ".join(names) + " and show each id's value at")
    print("every level. A real analog sensor climbs across the sweep; a flag snaps.")
    print("Inject ONLY on the one pin you're testing (0-5V, pot ground on the bench")
    print(f"ground). {len(MAP_LEVELS)} snaps - HOLD the pot steady through each.")
    cached = load_responders()
    if cached:
        print(f"(using {len(cached)} cached responder ids - delete "
              "live_responders.json to full-rescan.)")
    print()
    while True:
        label = ask("What are you testing? (e.g. 'C1017 p14 RED coolant'), Enter to quit: ").strip()
        if not label:
            break
        snaps = {}
        responders = load_responders()           # skip silent ids from the start
        for idx, (name, instr) in enumerate(MAP_LEVELS, 1):
            # fresh=True drains keystrokes buffered during the previous scan, so
            # this really waits for you to set the pot before snapshotting.
            ask(f"  {idx}/{len(MAP_LEVELS)}  {instr}.\n        set it as above and HOLD, "
                "then press Enter to snapshot (keep holding until it finishes)...",
                fresh=True)
            snaps[name] = snapshot(s, responders)
            if responders is None:               # first ever run: learn + cache
                responders = sorted(snaps[name])
                save_responders(responders)
            print(f"       [{name}] {len(snaps[name])} ids returned data.")

        base = snaps[names[0]]                   # compare against the first level (min)
        levels = names[1:]                       # the remaining levels (mid, max)
        # An id "moved" if it differs from the min level at mid or max.
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


# The switch-mode sequence. A switch input has only two states (grounded ~0 V
# "closed" / floating pulled-up ~5 V "open"), so a pot sweep won't find it -
# instead we snapshot FLOAT, then GROUND, then FLOAT again. The real switch id
# differs between float and ground AND returns to its float value on the second
# float; an id that only wanders (noise) fails the return-to-baseline check.
SWITCH_LEVELS = [
    ("float_1", "Leave the pin FLOATING (nothing connected / switch OPEN)"),
    ("ground",  "GROUND the pin (touch it to bench ground - switch CLOSED)"),
    ("float_2", "FLOAT the pin again (disconnect ground - switch OPEN)"),
]


def guided_switch(s):
    names = [n for n, _ in SWITCH_LEVELS]
    print("Guided SWITCH mapping - for two-state inputs (A/C request, heated")
    print("screen, brake, etc.), NOT analog sensors. Do NOT inject voltage:")
    print("just GROUND the pin, then FLOAT it. I snapshot float -> ground -> float")
    print("and flag the id that toggles with ground and returns on float.")
    print("Grabber on the ONE pin you're testing (RED C1017); ground = bench ground.")
    cached = load_responders()
    if cached:
        print(f"(using {len(cached)} cached responder ids - delete "
              "live_responders.json to full-rescan.)")
    print()
    while True:
        label = ask("What switch are you testing? (e.g. 'C1017 p28 RED A/C'), Enter to quit: ").strip()
        if not label:
            break
        snaps = {}
        responders = load_responders()
        for idx, (name, instr) in enumerate(SWITCH_LEVELS, 1):
            ask(f"  {idx}/{len(SWITCH_LEVELS)}  {instr}.\n        set it as above and HOLD, "
                "then press Enter to snapshot (hold until it finishes)...", fresh=True)
            snaps[name] = snapshot(s, responders)
            if responders is None:
                responders = sorted(snaps[name])
                save_responders(responders)
            print(f"       [{name}] {len(snaps[name])} ids returned data.")

        f1, gnd, f2 = (snaps[n] for n in names)
        # toggled: differs between float and ground.
        toggled = {i for i, a, b in changes(f1, gnd)}
        # clean switch: toggled AND the two float readings agree (returned to rest).
        clean = sorted(i for i in toggled if f1.get(i) == f2.get(i))
        noisy = sorted(i for i in toggled if i not in clean)

        print(f"\n  --- result for '{label}' ---")
        if not toggled:
            print("  no ids toggled - check the grabber contact / right pin / RED connector,")
            print("  or the input may not be a simple switch-to-ground (try 'map').")
        else:
            hdr = f"  {'id':<6}" + "".join(f"{n:<10}" for n in names) + "verdict"
            print(hdr)
            for i in clean + noisy:
                row = "".join(f"{(snaps[n].get(i) or '-'):<10}" for n in names)
                verdict = "CLEAN toggle (returned)" if i in clean else "changed, did NOT return"
                print(f"  0x{i:02X}  {row}{verdict}")
            if clean:
                print(f"  >>> SWITCH id for '{label}': 0x{clean[0]:02X}"
                      + (f" (also {', '.join(f'0x{i:02X}' for i in clean[1:])})" if len(clean) > 1 else ""))
                print("      confirm live with:  watch %02X  (should snap between two values)" % clean[0])
            else:
                print("  >>> ids changed but none returned to their float value - likely")
                print("      noise/drift, not the switch. Re-run and hold each state steady.")
        fn = log_map(label, clean + noisy, names, snaps)
        print(f"  logged to {fn}\n")


def parse_args(argv):
    import argparse
    p = argparse.ArgumentParser(
        description="GEMS $21 sensor-ID tools (guided map, switch mapping, or watch one id live).")
    sub = p.add_subparsers(dest="mode")
    sub.add_parser("map", help="guided ANALOG sensor mapping (pot sweep min/mid/max)")
    sub.add_parser("switch", help="guided SWITCH mapping (float -> ground -> float)")
    w = sub.add_parser("watch", help="poll ONE id live while you vary the voltage")
    w.add_argument("id", help="hex $21 id to watch, 00..FF (e.g. 2B)")
    return p.parse_args(argv)


def interactive(s):
    print("Commands:")
    print("  map          - guided ANALOG mapping (pot sweep min/mid/max)")
    print("  switch       - guided SWITCH mapping (float -> ground -> float)")
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
        elif line == "switch":
            guided_switch(s)
        elif line.startswith("watch"):
            rid = parse_id(line[5:].strip())
            if rid is None:
                print("  usage: watch <hex id 00..FF>, e.g. watch 2B"); continue
            watch_id(s, rid)
        else:
            print("  usage: map | switch | watch <id> | q")


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
        elif args.mode == "switch":
            guided_switch(s)
        else:
            interactive(s)          # no subcommand -> menu
    finally:
        s.close()
    print("done.")


if __name__ == "__main__":
    main()
