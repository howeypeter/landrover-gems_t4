"""Immobiliser-line LONG buffered capture — drives CMD_CAPTURE (0x0B) + CMD_READBUF.

Hardware-timed logic capture of GP2 (L9637D LO, LI T'd onto the 10AS->ECM mobilise
line). The Pico waits for the first edge on GP2 (up to 20 s), then DMAs ~1.6 s of
samples at 200 kS/s into RAM (fixes the old 10 ms one-frame capture that was
impossible to time an ignition-on into). Then it streams the buffer back and this
reconstructs the waveform, finds the bursts, and attempts a UART decode.

Workflow: START THIS, then within 20 s turn the ignition ON ONCE (leave it on). The
first edge arms the 1.6 s capture, which covers the whole 0->11->8 V mobilise event.

Needs firmware >= 3.7.0. Transport: GEMS_CONNECT / GEMS_PORT / auto / BLE. Output is
logged to bench/lmon_scope.log and the raw capture to bench/lmon_capture.bin.

Usage:
  python bench/lmon_scope.py               # 200 kS/s, ~1.6 s window, trigger on edge
  python bench/lmon_scope.py 100           # 100 kS/s (~3.2 s window)
  python bench/lmon_scope.py 200 now       # capture immediately (no trigger; self-test)
"""
from __future__ import annotations

import os
import re
import struct
import sys
from datetime import datetime
from pathlib import Path

CMD_PING = 0x01
CMD_CAPTURE = 0x0B
CMD_READBUF = 0x0C

LOG = Path(__file__).with_name("lmon_scope.log")
BIN = Path(__file__).with_name("lmon_capture.bin")
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


def bits_from_bytes(raw: bytes) -> list[int]:
    """raw = little-endian 32-bit words; each word holds 32 samples, bit31 = earliest
    (firmware autopush=32, shift-left). Reconstruct chronological samples."""
    bits = []
    for (w,) in struct.iter_unpack("<I", raw[: (len(raw) // 4) * 4]):
        for k in range(31, -1, -1):
            bits.append((w >> k) & 1)
    return bits


def runs_of(bits: list[int]) -> list[tuple[int, int]]:
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
    spb = (1_000_000.0 / baud) / sample_us
    if spb < 3:
        return []
    b = [1 - x for x in bits] if invert else bits
    n = len(b)
    i = 1
    res = []
    lim = n - int(10 * spb)
    while i < lim:
        if b[i - 1] == 1 and b[i] == 0:
            def samp(k):
                idx = int(i + (k + 0.5) * spb)
                return b[idx] if idx < n else 1
            if samp(0) == 0 and samp(9) == 1:
                val = 0
                for k in range(8):
                    val |= samp(1 + k) << k
                res.append(val)
                i += int(10 * spb)
                continue
        i += 1
    return res


def analyze(bits: list[int], rate_hz: int) -> None:
    sample_us = 1_000_000.0 / rate_hz
    runs = runs_of(bits)
    total_ms = len(bits) * sample_us / 1000
    out(f"  {len(bits)} samples @ {rate_hz/1000:.0f} kS/s "
        f"({sample_us:.2f} us/sample, {total_ms:.0f} ms window)")

    # locate the active region (first..last transition) and count edges
    edges = len(runs) - 1
    if edges <= 0:
        lvl = "HIGH" if (bits and bits[0]) else "LOW"
        out(f"  FLAT at {lvl} - no transitions in the whole window.")
        return
    # cumulative time (ms) of each transition, from capture start
    cum = 0
    edge_times = []
    for lvl, cnt in runs[:-1]:
        cum += cnt
        edge_times.append(cum * sample_us / 1000.0)  # ms
    out(f"  {edges} transitions. active from {edge_times[0]:.1f} ms to "
        f"{edge_times[-1]:.1f} ms (span {edge_times[-1]-edge_times[0]:.1f} ms)")

    # shortest real run -> bit-time hint
    durs = [cnt * sample_us for lvl, cnt in runs]
    real = [d for d in durs if d >= 2 * sample_us]
    if real:
        sm = min(real)
        out(f"  shortest real run = {sm:.1f} us -> if 1 bit, baud ~ {int(1_000_000/sm)}")

    # UART decode attempts over the whole capture
    best = None
    for baud in (10400, 9600):
        for invert in (False, True):
            bs = uart_decode(bits, sample_us, baud, invert)
            if bs:
                tag = f"{baud}{'/inv' if invert else ''}"
                out(f"  UART {tag}: {len(bs)} framed bytes: "
                    + " ".join(f"{x:02X}" for x in bs[:48])
                    + (" ..." if len(bs) > 48 else ""))
                if best is None or len(bs) > best[0]:
                    best = (len(bs), tag)
    if best:
        out(f"  => best framing: {best[1]} ({best[0]} bytes). If the SAME byte "
            "pattern repeats across clean ignition-ons, that's the coded message.")
    else:
        out("  => no valid UART framing at 9600/10400. If bursts exist but don't "
            "decode, it's likely a power-up transient, not serial -> ADC scope.")


def read_buffer(t, nbytes: int) -> bytes:
    raw = bytearray()
    off = 0
    while off < nbytes:
        n = min(255, nbytes - off)
        st, chunk = t._transceive(CMD_READBUF, bytes([(off >> 8) & 0xFF, off & 0xFF, n]))
        if st != 0 or not chunk:
            break
        raw.extend(chunk)
        off += len(chunk)
    return bytes(raw)


def main() -> None:
    args = [a for a in sys.argv[1:]]
    rate_khz = 200
    trig = 1
    for a in args:
        if a.lower() == "now":
            trig = 0
        else:
            try:
                rate_khz = int(a)
            except ValueError:
                pass
    rate_hz = rate_khz * 1000

    t = make_transport()
    t.open()
    try:
        try:
            st, ver = t._transceive(CMD_PING)
            fw = ver.decode("ascii", "replace")
            out(f"firmware: {fw}")
            m = re.search(r"(\d+)\.(\d+)\.(\d+)", fw)
            if m and tuple(int(x) for x in m.groups()) < (3, 7, 0):
                out("WARNING: firmware < 3.7.0 - CMD_CAPTURE not present; reflash.")
        except Exception:  # noqa: BLE001
            out("PING failed - continuing anyway")

        out(f"\n--- capture {datetime.now().strftime('%H:%M:%S')} "
            f"({rate_khz} kS/s, trigger={'edge' if trig else 'immediate'}) ---")
        if trig:
            out("ARMED. Turn the ignition ON ONCE within 20 s (leave it on)...")

        # the capture blocks up to ~22 s (20 s trigger + ~1.6 s DMA); widen the
        # serial read timeout for THIS exchange only.
        old_to = getattr(getattr(t, "_serial", None), "timeout", None)
        if old_to is not None:
            t._serial.timeout = 30
        payload = bytes([(rate_khz >> 8) & 0xFF, rate_khz & 0xFF, trig])
        st, meta = t._transceive(CMD_CAPTURE, payload)
        if old_to is not None:
            t._serial.timeout = old_to

        if st == 1:
            out("  TIMEOUT - no edge within 20 s (no event seen on GP2).")
            return
        if st != 0 or len(meta) < 4:
            out(f"  capture failed: status {st}, meta={meta.hex()}")
            return
        nbytes = (meta[0] << 8) | meta[1]
        cap_rate = ((meta[2] << 8) | meta[3]) * 1000
        out(f"  captured {nbytes} bytes @ {cap_rate/1000:.0f} kS/s; reading back...")

        raw = read_buffer(t, nbytes)
        BIN.write_bytes(raw)
        out(f"  read {len(raw)} bytes -> {BIN.name}")
        bits = bits_from_bytes(raw)
        analyze(bits, cap_rate)
    finally:
        t.close()


if __name__ == "__main__":
    main()
