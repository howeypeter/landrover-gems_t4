"""Immobiliser-line sniffer — drives firmware CMD_MONITOR_L (0x09).

Captures digital TRANSITIONS on the Pico's GP2 (physical pin 4), which is fed by
the L9637D's read-only LO (pin 2). Wire LI (pin 8) T'd onto the coded mobilise line
(10AS C225 p15 -> ECM C1017 p26); common ground; board powered. See
docs/two-board-rig.md and docs/10as-pinout.md.

This is a CHARACTERISATION tool, not a decoder. It tells you whether the tapped line
carries digital activity the L9637D comparator can resolve, and its rough timing
(=> baud). Cycle the ignition (or trigger a mobilise event) during the window.

Needs firmware >= 3.5.0 (pico_kline_all). Transport (same as the other bench tools):
  GEMS_CONNECT=host[:port]  -> WiFi/TCP
  GEMS_PORT=COMx            -> that USB port
  (else)                    -> auto-detect a plugged Pico, then BLE 'gems-pico'

Usage:
  python bench/monitor_l.py              # one 1000 ms capture
  python bench/monitor_l.py 2000         # one 2000 ms capture window
  python bench/monitor_l.py 2000 loop    # repeat (cycle ignition between captures)
"""
from __future__ import annotations

import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

CMD_PING = 0x01
CMD_MONITOR_L = 0x09
MAX_WIN_MS = 5000            # firmware clamps to this

#: Every run is mirrored here (append) so captures survive terminal scrollback.
#: Gitignored like the other bench .log captures.
LOG = Path(__file__).with_name("monitor_l.log")
_fh = open(LOG, "a", encoding="utf-8")


def out(msg: str = "") -> None:
    """Print to the terminal AND append to monitor_l.log (flushed per line)."""
    print(msg)
    _fh.write(msg + "\n")
    _fh.flush()


def make_transport():
    conn = os.environ.get("GEMS_CONNECT")
    if conn:
        from gems_t4.transport.tcp import TcpTransport, parse_endpoint
        host, port = parse_endpoint(conn)
        out(f"[transport: WiFi {host}:{port}]")
        return TcpTransport(host, port)
    port = os.environ.get("GEMS_PORT")
    if not port:
        try:
            from gems_t4.transport.pico import find_pico_port
            port = find_pico_port()
        except Exception:
            port = None
    if port:
        from gems_t4.transport.pico import PicoAdapterTransport
        out(f"[transport: USB {port}]")
        return PicoAdapterTransport(port)
    from gems_t4.transport.ble import BleTransport
    name = os.environ.get("GEMS_BLE", "gems-pico")
    out(f"[transport: BLE {name}]")
    return BleTransport(name)


def decode(resp: bytes):
    """resp = [initial_level] + N*[dt_hi][dt_lo]. Returns (initial, [dt_us,...])."""
    if not resp:
        return None, []
    initial = resp[0] & 1
    deltas = []
    body = resp[1:]
    for i in range(0, len(body) - 1, 2):
        deltas.append((body[i] << 8) | body[i + 1])
    return initial, deltas


def summarize(initial, deltas) -> None:
    if not deltas:
        lvl = "HIGH" if initial else "LOW"
        out(f"  STATIC at {lvl} for the whole window - NO transitions.")
        out("  => either no digital signal, OR a signal the 1-bit comparator")
        out("     can't resolve. NOT proof of 'nothing there' - confirm with a")
        out("     scope. (Also check: board powered? common ground? LI T'd on?)")
        return
    n = len(deltas)
    lo, hi = min(deltas), max(deltas)
    nonzero = [d for d in deltas if d > 0]
    smallest = min(nonzero) if nonzero else 0
    out(f"  {n} transitions. initial={'HIGH' if initial else 'LOW'} "
          f"(levels alternate from there)")
    out(f"  gap us: min={lo} max={hi}")
    if smallest:
        out(f"  smallest non-zero gap ~= 1 bit time -> est. baud ~ {1_000_000 // smallest} "
              f"(if this is a serial line)")
    # first chunk of edges for eyeballing
    show = deltas[:40]
    edges = "  ".join(str(d) for d in show)
    out(f"  first {len(show)} gaps (us): {edges}"
          + (" ..." if n > len(show) else ""))
    if n >= 127:
        out("  (hit the 127-transition cap - the line is busier; capture is truncated)")


def capture(t, win_ms: int) -> None:
    out(f"--- capture {datetime.now().strftime('%H:%M:%S')} ---")
    payload = bytes([(win_ms >> 8) & 0xFF, win_ms & 0xFF])
    t0 = time.time()
    st, resp = t._transceive(CMD_MONITOR_L, payload)
    dt = time.time() - t0
    if st != 0:
        out(f"  MONITOR_L returned status {st} (not OK).")
        return
    initial, deltas = decode(resp)
    out(f"  [{win_ms} ms window, replied in {dt:.2f}s, {len(resp)} bytes]  raw={resp.hex(' ')}")
    summarize(initial, deltas)


def main() -> None:
    args = sys.argv[1:]
    win_ms = 1000
    loop = False
    for a in args:
        if a.lower() == "loop":
            loop = True
        else:
            try:
                win_ms = int(a)
            except ValueError:
                out(f"ignoring arg {a!r}")
    if win_ms > MAX_WIN_MS:
        out(f"window clamped to {MAX_WIN_MS} ms (firmware max)")
        win_ms = MAX_WIN_MS

    t = make_transport()
    t.open()
    try:
        try:
            st, ver = t._transceive(CMD_PING)
            fw = ver.decode("ascii", "replace")
            out(f"firmware: {fw}")
            m = re.search(r"(\d+)\.(\d+)\.(\d+)", fw)
            if m and tuple(int(x) for x in m.groups()) < (3, 5, 0):
                out("WARNING: firmware < 3.5.0 - CMD_MONITOR_L not present; reflash.")
        except Exception:  # noqa: BLE001
            out("PING failed - continuing anyway")

        out("\nMonitoring GP2 (L9637D LO). Trigger/ignition-cycle during the window.\n")
        if loop:
            out("(loop mode - Ctrl-C to stop)\n")
            try:
                while True:
                    capture(t, win_ms)
                    out()
                    time.sleep(0.5)
            except KeyboardInterrupt:
                out("\n(stopped)")
        else:
            capture(t, win_ms)
    finally:
        t.close()


if __name__ == "__main__":
    main()
