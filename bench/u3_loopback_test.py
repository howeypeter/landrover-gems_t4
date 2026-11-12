"""L9637D channel loopback sanity test (works on either chip).

Checks that a K-line transceiver -- channel 0 = U2 (UART0/Serial1, TX=GP0,
RX=GP1, LO=GP2, K-node terminals A1/A2), or channel 1 = U3 (UART1/Serial2,
TX=GP4, RX=GP5, LO=GP6, K-node terminals B1/B2) -- is powered and oriented
correctly, using only USB + the existing host protocol -- no new firmware, no
multimeter needed for THIS step. Uses commands already in pico_kline_all
>= 3.8.0 and already wired into gems_t4.transport.pico.PicoAdapterTransport:
select_channel() + raw_xfer().

Default channel is 1 (U3, the untested second chip). Pass --channel 0 to run
the identical test against U2 (the known-working chip) as a baseline -- if
channel 0 ALSO fails, the problem is the test setup/firmware/board, not U3's
orientation specifically.

HOW THE TEST WORKS
-------------------
The L9637D is a half-duplex transceiver: TX drives the K output, and K's own
state (whatever is actually on the bus) is read back on RX. With nothing else
attached to B1/B2 (no vehicle, no car module), the chip's own transmission is
the only thing on that K-node, so a correctly-powered, correctly-oriented chip
will "hear itself": raw_xfer() should return the same bytes we sent, as the
chip's self-echo. A backwards chip (Vcc/GND swapped) typically won't power up
correctly at all, so the echo comes back empty, truncated, or garbled.

THIS TEST IS SECONDARY, NOT PRIMARY. Do these checks FIRST, before relying on
this script's result:
  1. VISUAL: pin-1 dot/notch on the physical chip vs the PCB footprint marker.
  2. MULTIMETER (recommended, do this before full power-up): with ONLY USB
     connected (no 12V/Vs yet), measure U3 pin 3 (Vcc) and pin 5 (GND) with a
     multimeter. Vcc should read +3.3V, GND should read 0V. If swapped, STOP --
     the chip is backwards; don't bother running this script until it's fixed.

This script is a functional cross-check on top of that, not a replacement for
it -- a chip that's merely *dead* (bad solder joint, etc.) will also fail this
test but isn't necessarily backwards. The multimeter check is what actually
distinguishes "backwards" from "just not working."

USAGE
-----
    python bench/u3_loopback_test.py                     # U3, auto-detect port
    python bench/u3_loopback_test.py --port COM4          # U3, explicit port
    python bench/u3_loopback_test.py --channel 0          # U2 baseline instead
"""

from __future__ import annotations

import argparse
import sys

from gems_t4.transport.pico import PicoAdapterTransport, find_pico_port

TEST_PATTERN = bytes([0x55, 0xAA, 0x01, 0xFE, 0x00, 0xFF])


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
            0: "channel 0 (U2: Serial1, TX=GP0/RX=GP1, K-node A1/A2)",
            1: "channel 1 (U3: Serial2, TX=GP4/RX=GP5, K-node B1/B2)",
        }[args.channel]

        try:
            t.select_channel(args.channel)
        except Exception as exc:  # noqa: BLE001 - want the raw message
            print(f"ERROR: select_channel({args.channel}) failed: {exc}")
            print("  -> is this firmware pico_kline_all >= 3.8.0? Re-flash if not.")
            return 1
        print(f"Selected {chan_desc}.")

        print(f"Sending test pattern: {TEST_PATTERN.hex(' ')}")
        echo = t.raw_xfer(TEST_PATTERN)
        print(f"Received:             {echo.hex(' ') if echo else '(nothing)'}")

        if not echo:
            chip = "U3" if args.channel == 1 else "U2"
            print()
            print("RESULT: NO RESPONSE.")
            if args.channel == 1:
                print("  Consistent with: backwards chip (Vcc/GND swapped), a dead chip,")
                print("  a bad solder joint, or U3 simply not populated yet.")
            else:
                print("  U2 is the chip already believed working -- a failure here points")
                print("  at the TEST SETUP (board reset/boot timing, wrong port, firmware)")
                print("  rather than chip orientation. Fix this before trusting a U3 result.")
            print(f"  -> Check Vcc (pin 3, should be +3.3V) and GND (pin 5, should be")
            print(f"     0V) on {chip} with a multimeter (USB-only power, no 12V/Vs yet)")
            print("     to tell 'backwards' apart from 'just not working'.")
            return 1

        if echo[: len(TEST_PATTERN)] == TEST_PATTERN:
            print()
            print("RESULT: PASS. U3 echoed its own transmission back cleanly.")
            print("  Consistent with correct power/orientation and a functioning chip.")
            return 0

        print()
        print("RESULT: GARBLED. Got a response, but it doesn't match what was sent.")
        print("  Could be correct power/orientation with some other issue (timing,")
        print("  a partially-wired K-node, bus contention), or a chip that's powered")
        print("  but still misbehaving. Not a clean pass -- investigate further")
        print("  (start with the Vcc/GND multimeter check) before trusting this channel.")
        return 1
    finally:
        t.close()


if __name__ == "__main__":
    sys.exit(main())
