"""Immobiliser-line PIO logic capture — drives firmware CMD_PIO_CAPTURE (0x0A).

Hardware-timed 1-bit logic capture of GP2 (L9637D LO, LI T'd onto the 10AS->ECM
mobilise line). Unlike monitor_l.py's busy-poll, the Pico samples at a fixed PIO
clock, so the microsecond timing is TRUSTWORTHY. It waits for the first edge on GP2
(up to 10 s) then captures a short high-resolution window - so trigger it, then do
ONE clean ignition-on.

Reconstructs the waveform, lists the level runs (accurate us), estimates the bit
time / baud, and attempts a UART decode at 9600 and 10400 (both polarities) to test
the "coded serial message" hypothesis.

Needs firmware >= 3.6.0 (pico_kline_all). Transport: GEMS_CONNECT / GEMS_PORT / auto
/ BLE (same as the other bench tools). Output also appended to bench/lmon_scope.log.

Usage:
  python bench/lmon_scope.py                # 200 kS/s, 255 bytes (~10 ms), then decode
  python bench/lmon_scope.py 500            # 500 kS/s (~4 ms window), finer timing
  python bench/lmon_scope.py 200 255        # explicit rate_khz nbytes
"""
from __future__ import annotations

import os
import re
import sys
from datetime import datetime
from pathlib import Path

CMD_PING = 0x01
CMD_PIO_CAPTURE = 0x0A

LOG = Path(__file__).with_name("lmon_scope.log")
_fh = open(LOG, "a", encoding="utf-8")


def out(msg: str = "") -> None:
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


def unpack_bits(resp: bytes) -> list[int]:
    """Each byte = 8 samples, bit7 = earliest (per firmware autopush/shift-left)."""
    bits = []
    for b in resp:
        for k in range(7, -1, -1):
            bits.append((b >> k) & 1)
    return bits


def runs_of(bits: list[int]) -> list[tuple[int, int]]:
    """RLE: [(level, count), ...]."""
    out_runs = []
    if not bits:
        return out_runs
    cur, n = bits[0], 1
    for b in bits[1:]:
        if b == cur:
            n += 1
        else:
            out_runs.append((cur, n)); cur, n = b, 1
    out_runs.append((cur, n))
    return out_runs


def uart_decode(bits: list[int], sample_us: float, baud: int, invert: bool):
    """Simple UART decode: idle-high, 1 start(0), 8 data(LSB first), 1 stop(1)."""
    spb = (1_000_000.0 / baud) / sample_us      # samples per bit
    if spb < 3:
        return []                                # too few samples/bit to trust
    b = [1 - x for x in bits] if invert else bits
    n = len(b)
    i = 1
    out_bytes = []
    while i < n - int(10 * spb):
        if b[i - 1] == 1 and b[i] == 0:          # falling edge = possible start
            def samp(k):
                idx = int(i + (k + 0.5) * spb)
                return b[idx] if idx < n else 1
            if samp(0) == 0 and samp(9) == 1:    # valid start + stop
                val = 0
                for k in range(8):
                    val |= samp(1 + k) << k
                out_bytes.append(val)
                i += int(10 * spb)
                continue
        i += 1
    return out_bytes


def analyze(resp: bytes, rate_hz: int) -> None:
    sample_us = 1_000_000.0 / rate_hz
    bits = unpack_bits(resp)
    runs = runs_of(bits)
    out(f"  {len(resp)} bytes = {len(bits)} samples @ {rate_hz/1000:.0f} kS/s "
        f"({sample_us:.2f} us/sample, {len(bits)*sample_us/1000:.2f} ms window)")
    # runs, filtering 1-sample glitches for the baud estimate
    durs = [cnt * sample_us for lvl, cnt in runs]
    real = [d for d in durs if d >= 2 * sample_us]
    if not real:
        out("  no real level runs (line flat over the window).")
        return
    shortest = min(real)
    out(f"  {len(runs)} runs. shortest real run = {shortest:.1f} us "
        f"-> if that is 1 bit, baud ~ {int(1_000_000/shortest)}")
    # show the first chunk of runs
    show = runs[:32]
    s = "  ".join(f"{'H' if lvl else 'L'}{cnt*sample_us:.0f}" for lvl, cnt in show)
    out(f"  runs (level+us): {s}" + (" ..." if len(runs) > len(show) else ""))
    # UART decode attempts
    best = None
    for baud in (10400, 9600):
        for invert in (False, True):
            bs = uart_decode(bits, sample_us, baud, invert)
            if bs:
                tag = f"{baud}{'/inv' if invert else ''}"
                out(f"  UART {tag}: {len(bs)} framed bytes: "
                    + " ".join(f"{x:02X}" for x in bs[:32])
                    + (" ..." if len(bs) > 32 else ""))
                if best is None or len(bs) > best[0]:
                    best = (len(bs), tag)
    if best:
        out(f"  => best framing: {best[1]} ({best[0]} bytes). If a byte pattern "
            "REPEATS across clean ignition-ons, that's the coded message.")
    else:
        out("  => no valid UART framing at 9600/10400 (either not serial at those "
            "bauds, an RC/power transient, or the comparator mangles it -> ADC scope).")


def main() -> None:
    args = [a for a in sys.argv[1:]]
    rate_khz = int(args[0]) if len(args) >= 1 else 200
    nbytes = int(args[1]) if len(args) >= 2 else 255
    rate_hz = rate_khz * 1000

    t = make_transport()
    t.open()
    try:
        try:
            st, ver = t._transceive(CMD_PING)
            fw = ver.decode("ascii", "replace")
            out(f"firmware: {fw}")
            m = re.search(r"(\d+)\.(\d+)\.(\d+)", fw)
            if m and tuple(int(x) for x in m.groups()) < (3, 6, 0):
                out("WARNING: firmware < 3.6.0 - CMD_PIO_CAPTURE not present; reflash.")
        except Exception:  # noqa: BLE001
            out("PING failed - continuing anyway")

        payload = bytes([(rate_khz >> 8) & 0xFF, rate_khz & 0xFF, nbytes & 0xFF])
        out(f"\n--- PIO capture {datetime.now().strftime('%H:%M:%S')} "
            f"({rate_khz} kS/s, {nbytes} bytes) ---")
        out("Waiting for the first edge on GP2 - do ONE clean ignition-ON now "
            "(10 s timeout)...")
        st, resp = t._transceive(CMD_PIO_CAPTURE, payload)
        if st == 1:
            out("  TIMEOUT - no edge within 10 s (no event, or line already moving?).")
            return
        if st != 0:
            out(f"  status {st} (not OK).")
            return
        out(f"  raw[:48]={resp[:48].hex(' ')}")
        analyze(resp, rate_hz)
    finally:
        t.close()


if __name__ == "__main__":
    main()
