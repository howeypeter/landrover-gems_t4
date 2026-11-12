"""L9637D raw pin-level check -- Vs-free (no 12V needed) orientation cross-check.

Reads the RAW digital level of TX/RX/LO on a given channel via CMD_READ_PINS
(firmware pico_kline_all >= 3.9.0), bypassing UART byte-framing entirely. This
is DIFFERENT from bench/u3_loopback_test.py: that one sends bytes and needs
the chip's K-line driver (Vs/12V) to produce any traffic to decode. This one
just checks the pin's instantaneous electrical state -- useful because, per
the ST L9637D datasheet, RX and LO are specified to show a DEFINED level when
their inputs (K / LI) are open/floating (your exact situation: no vehicle, no
Vs connected yet).

WHAT TO EXPECT
--------------
This is a cross-check, not as conclusive as a multimeter Vcc/GND measurement
(still the recommended primary test -- see bench/u3_loopback_test.py's
docstring for that procedure). A correctly-powered, correctly-oriented chip
should report a CONSISTENT level across repeated reads (not flapping/noisy).
If the chip has no logic power at all (one likely symptom of a 180-degree
rotation, since that would put the chip's real Vcc pin on the board's Vs pad
instead -- unpowered with no Vs connected), expect either a constant LOW
(undriven pad reading its default pulled state) or an inconsistent/noisy
read across repeated calls, rather than the datasheet's specified defined-ON
behavior.

USAGE
-----
    python bench/u3_pin_level_test.py                 # U3, auto-detect port
    python bench/u3_pin_level_test.py --channel 0      # U2 baseline instead
    python bench/u3_pin_level_test.py --samples 10     # read N times (default 5)
"""

from __future__ import annotations

import argparse
import sys
import time

from gems_t4.transport.pico import PicoAdapterTransport, find_pico_port


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", help="COM port (default: auto-detect by USB VID)")
    ap.add_argument(
        "--channel",
        type=int,
        choices=(0, 1),
        default=1,
        help="0 = U2 (known-good baseline), 1 = U3 (default, the untested chip)",
    )
    ap.add_argument("--samples", type=int, default=5, help="number of reads (default 5)")
    args = ap.parse_args()

    port = args.port or find_pico_port()
    if not port:
        print("ERROR: no Pico found on USB and --port not given.")
        return 1
    print(f"Using port: {port}")

    t = PicoAdapterTransport(port=port)
    t.open()
    try:
        version = t.ping().decode("ascii", "replace")
        print(f"Firmware: {version}")

        chan_desc = {
            0: "channel 0 (U2: TX=GP0, RX=GP1, LO=GP2)",
            1: "channel 1 (U3: TX=GP4, RX=GP5, LO=GP6)",
        }[args.channel]

        try:
            t.select_channel(args.channel)
        except Exception as exc:  # noqa: BLE001 - want the raw message
            print(f"ERROR: select_channel({args.channel}) failed: {exc}")
            print("  -> is this firmware pico_kline_all >= 3.8.0? Re-flash if not.")
            return 1
        print(f"Selected {chan_desc}.\n")

        readings = []
        for i in range(args.samples):
            try:
                pins = t.read_pins()
            except Exception as exc:  # noqa: BLE001
                print(f"ERROR: read_pins() failed: {exc}")
                print("  -> is this firmware pico_kline_all >= 3.9.0? Re-flash if not.")
                return 1
            readings.append(pins)
            print(f"  read {i + 1}/{args.samples}: TX={int(pins['tx'])} RX={int(pins['rx'])} LO={int(pins['lo'])}")
            time.sleep(0.1)

        rx_vals = {r["rx"] for r in readings}
        lo_vals = {r["lo"] for r in readings}

        print()
        if len(rx_vals) == 1 and len(lo_vals) == 1:
            print(f"RESULT: STABLE. RX held at {int(rx_vals.pop())}, LO held at {int(lo_vals.pop())}")
            print("  across all reads -- consistent with a defined, powered chip output.")
            print("  This is SUGGESTIVE of correct power/orientation, not conclusive --")
            print("  still confirm with the Vcc/GND multimeter check if you haven't.")
        else:
            print("RESULT: UNSTABLE. RX and/or LO changed between reads with nothing")
            print("  driving the bus -- NOT the datasheet's expected defined-level")
            print("  behavior for an open/floating input. Consistent with the chip")
            print("  having no logic power (e.g. a 180-degree rotation putting its")
            print("  real Vcc pin on the board's unconnected Vs pad) or a bad/missing")
            print("  connection. Do the Vcc/GND multimeter check next.")
        return 0
    finally:
        t.close()


if __name__ == "__main__":
    sys.exit(main())
