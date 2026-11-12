"""U3 LI->LO ground-touch test -- Vs-free (no 12V) orientation check, LIVE mode.

Safety note: this test is safe specifically BECAUSE it's run USB-only, with no
Vs/12V connected. LI (pin 8) is rated for direct handling of K-line-range
voltages and is a passive SENSE input, so grounding it is harmless on its own.
If the chip is backwards, the board's "LI" terminal (B3) actually lands on the
chip's real pin 4 (RX, an active output) instead -- which COULD be a problem
if the chip were powered, but with no Vs connected, a backwards chip's real
Vcc pin sits on the unconnected Vs pad and has NO logic power at all. No power
means no active output driver to fight against, so the worst case here is
"nothing happens," not damage. Do NOT connect Vs/12V for this test.

LIVE MODE: polls CMD_READ_PINS continuously and shows TX/RX/LO as live,
DYNAMIC bars in place (updates the same terminal line), so you see the effect
of touching a wire immediately, in real time, instead of waiting for a fixed
capture window to end. Runs until you press Enter.

These are digital 0/1 reads (not an analog voltage), so each bar shows a
SMOOTHED rolling-average fill level over the last WINDOW samples (like the
TPS gauge, but built from a moving average instead of a true analog value) --
it rises as the signal spends more time HIGH and falls as it spends more time
LOW, so it visibly moves up and down as you toggle the pin, rather than just
snapping full/empty. A small transition counter per signal is kept too, so
you can tell afterward whether anything moved at all, even if you looked
away for a second.

PROCEDURE
---------
1. Run this script. It selects a channel and starts live-polling.
2. Touch a ground wire to the LI terminal shown (B3 for U3, A3 for U2) a few
   times -- make contact, release, repeat -- and watch the LO bar on screen.
3. Also try touching the CHIP'S OWN pin 8 directly (counted from its pin-1
   dot marker, carefully -- SOIC-8 pins are close together) and compare: if
   touching B3 and touching the chip's own pin 8 give DIFFERENT results,
   that mismatch itself is evidence the chip's pins don't line up with what
   the board expects (i.e. backwards) -- it doesn't even require knowing
   which level means what.
4. Press Enter when done to stop and see the summary.

USAGE
-----
    python bench/u3_li_lo_ground_test.py                  # U3, USB auto-detect
    python bench/u3_li_lo_ground_test.py --channel 0      # U2 baseline instead
    python bench/u3_li_lo_ground_test.py --ble            # over BLE instead of USB
    python bench/u3_li_lo_ground_test.py --rate-ms 50     # poll interval (default 50ms)
"""

from __future__ import annotations

import argparse
import sys
import time
from collections import deque

from gems_t4.transport.pico import PicoAdapterTransport, find_pico_port
from gems_t4.transport.ble import BleTransport, DEFAULT_NAME

try:
    import msvcrt  # Windows-only; this project is Windows-only (see CLAUDE.md)
except ImportError:  # pragma: no cover - non-Windows fallback, Enter-to-stop won't work
    msvcrt = None

BAR_WIDTH = 20
SMOOTH_WINDOW = 10  # samples averaged into the bar fill -- bigger = smoother/slower


def dynamic_bar(history: deque) -> str:
    """Render a bar whose fill is the rolling-average HIGH ratio over `history`."""
    if not history:
        frac = 0.0
    else:
        frac = sum(history) / len(history)
    filled = round(frac * BAR_WIDTH)
    filled = max(0, min(BAR_WIDTH, filled))
    return "#" * filled + "." * (BAR_WIDTH - filled) + f" {frac * 100:5.1f}%"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--port", help="COM port (default: auto-detect by USB VID)")
    ap.add_argument(
        "--ble",
        nargs="?",
        const=DEFAULT_NAME,
        default=None,
        metavar="NAME",
        help=f"use BLE instead of USB (default name '{DEFAULT_NAME}' if given with no value)",
    )
    ap.add_argument(
        "--channel",
        type=int,
        choices=(0, 1),
        default=1,
        help="0 = U2 (known-good baseline), 1 = U3 (default, the untested chip)",
    )
    ap.add_argument(
        "--rate-ms", type=int, default=50, help="poll interval in ms (default 50)"
    )
    args = ap.parse_args()

    if args.ble is not None:
        print(f"Connecting over BLE to '{args.ble}'...")
        t = BleTransport(args.ble)
    else:
        port = args.port or find_pico_port()
        if not port:
            print("ERROR: no Pico found on USB and --port not given.")
            print("  (use --ble to connect over Bluetooth LE instead)")
            return 1
        print(f"Using port: {port}")
        t = PicoAdapterTransport(port=port)

    t.open()
    try:
        version = t.ping().decode("ascii", "replace")
        print(f"Firmware: {version}")

        li_term = "B3" if args.channel == 1 else "A3"
        chan_desc = {
            0: f"channel 0 (U2: LI terminal {li_term}, TX=GP0 RX=GP1 LO=GP2)",
            1: f"channel 1 (U3: LI terminal {li_term}, TX=GP4 RX=GP5 LO=GP6)",
        }[args.channel]

        try:
            t.select_channel(args.channel)
        except Exception as exc:  # noqa: BLE001
            print(f"ERROR: select_channel({args.channel}) failed: {exc}")
            return 1
        print(f"Selected {chan_desc}.")
        print(f"\nTouch a ground wire to terminal {li_term} (or the chip's own pin 8")
        print("directly) and watch the LO bar below. Press ENTER to stop.\n")

        last = None
        counts = {"tx": 0, "rx": 0, "lo": 0}
        history = {k: deque(maxlen=SMOOTH_WINDOW) for k in ("tx", "rx", "lo")}
        rate_s = max(0.01, args.rate_ms / 1000.0)

        while True:
            if msvcrt is not None and msvcrt.kbhit():
                key = msvcrt.getch()
                if key in (b"\r", b"\n"):
                    break

            try:
                pins = t.read_pins()
            except Exception as exc:  # noqa: BLE001
                print(f"\nERROR: read_pins() failed: {exc}")
                return 1

            if last is not None:
                for k in ("tx", "rx", "lo"):
                    if pins[k] != last[k]:
                        counts[k] += 1
            last = pins
            for k in ("tx", "rx", "lo"):
                history[k].append(1 if pins[k] else 0)

            line = (
                f"TX [{dynamic_bar(history['tx'])}]  "
                f"RX [{dynamic_bar(history['rx'])}]  "
                f"LO [{dynamic_bar(history['lo'])}]  "
                f"(transitions: tx={counts['tx']} rx={counts['rx']} lo={counts['lo']})"
            )
            sys.stdout.write("\r" + line + "   ")
            sys.stdout.flush()
            time.sleep(rate_s)

        print("\n\nStopped.")
        print(f"Total transitions seen -- TX: {counts['tx']}  RX: {counts['rx']}  LO: {counts['lo']}")
        if counts["lo"] > 0:
            print("\nLO changed state at least once. If that lined up with touching")
            print(f"terminal {li_term}, that's real evidence the LI->LO path is")
            print("correctly wired (consistent with correct orientation).")
        else:
            print("\nLO never changed. Inconclusive on its own -- could mean backwards")
            print("orientation, or just that nothing in this path is active without")
            print("more than USB power. Try touching the chip's own pin 8 directly")
            print("and compare against this result (see the script's docstring).")
        return 0
    finally:
        t.close()


if __name__ == "__main__":
    sys.exit(main())
