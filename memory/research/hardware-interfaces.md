---
name: research-hardware-interfaces
description: Research findings — DIY K-line hardware interfaces (transceivers, cables, J2534) to reach a GEMS ECU from Python
metadata:
  type: reference
---

# DIY K-line Hardware Interfaces for GEMS

Research pass 2026-07-06. Practical hardware to build/buy for a Python tool that
talks to (and maybe programs) a GEMS ECU over the single-wire K-line.

## Recommendation: build Tier B (smart microcontroller front-end)
| Tier | Build | Cost | Reads | Timing init | Programming |
|---|---|---|---|---|---|
| A | Genuine-FTDI KKL 409.1 cable (FT232RL+L9637D) + pyserial | ~£10-15 | Yes | Marginal (USB latency) | No/unreliable |
| B | MCU (Arduino/ESP32/RP2040) + L9637D doing K-line timing, USB-serial to PC | ~£10-20 | Yes | **Yes (MCU owns timing)** | Yes, with care |
| C | J2534 passthru (Tactrix OpenPort 2.0) | ~£150 | Yes | Yes | Yes (OEM reflash route) |

**Build Tier B**: put an ST L9637D transceiver on a small board, drive from a
cheap MCU that owns ALL ISO 9141 bit-timing (5-baud init, inter-byte gaps,
timeouts), expose a clean framed protocol over USB-serial to Python. Side-steps
the fatal weakness of pure-FTDI: USB scheduling jitter 1-16ms makes host-driven
K-line timing unreliable — fine for reads, disqualifying for programming (blown
timing window bricks the ECU). This matches the project's swappable-transport
design: MCU speaking framed $61/$7f records over USB is a drop-in for the
emulated transport.

## J1962 pinout (these Rovers)
Pin 4 chassis gnd, pin 5 signal gnd, **pin 7 K-line** (idles ~12V, ~10.4kbit/s),
pin 15 L-line (optional init, often unused), **pin 16 +12V permanent**. ISO9141-2
and ISO14230 share identical pinout; no CAN pins (6/14). K-line open-drain pulled
to 12V — CANNOT connect 5V/3.3V UART directly, need a transceiver. P38 GEMS DLC
in passenger footwell by transmission tunnel.

## K-line transceiver chips
- **ST L9637D** (classic, in KKL cables): ISO 9141 bus driver, 4.5-36V supply,
  K current limit ~60mA. Pins K/L/TX/RX/GND/VS. Standard circuit: K pulled to
  Vbatt via **510Ω** + small filter cap (~1.3-10nF). Tiny BOM. Datasheet:
  https://www.st.com/resource/en/datasheet/l9637.pdf
- **NXP MC33290** — direct equivalent. https://www.nxp.com/docs/en/data-sheet/MC33290.pdf
- **TI SN65HVDA195/SN65HVDA100, Vishay Si9241A** — modern in-production
  alternatives (L9637D getting scarce). OBD9141 author confirms MC33290/
  SN65HVDA100/195 all work with datasheet circuit.
- **MikroElektronika "ISO 9141 Click"** — L9637-based module, UART out, no PCB
  design needed. https://www.mikroe.com/iso-9141-click
- Cheap fallbacks (prototyping reads only): LM393 comparator design, or discrete
  transistor (R6=3.3kΩ for 3.3V MCU, ~5.3kΩ for 5V).

## DIY interfaces
- **KKL 409.1 USB cable** (FT232RL + L9637D/Si9241A): the canonical DIY K-line
  interface, presents as plain COM port → **pyserial talks directly**, no ELM327
  firmware in the way. Handles ISO9141 + KWP2000. **Buy genuine FTDI only**
  (clones have driver problems). Great cheap start for reads + 5-baud experiments;
  marginal for programming. https://www.obdinnovations.com/vag-kkl-k-line-obd2-usb-interface-cable-with-ftdi-ft232rl-chip/
- **Raspberry Pi UART + transceiver**: use PL011 (`dtoverlay=disable-bt`) not
  mini-UART; 5-baud init must be bit-banged on GPIO then switch UART to 10400.
  Doable, scheduling jitter fiddly.
- **Arduino/ESP32/RP2040 + transceiver** (strong DIY option): libraries
  muki01/OBD2_KLine_Library (5-baud + fast init, ISO9141+14230) and
  iwanders/OBD9141 (clean ISO9141-2, ESP32 example, timing in header). MCU owns
  timing; host just sends "read/send" over USB. **This makes programming feasible.**

## ELM327 limits (why it's inadequate for GEMS/programming)
1. 8-byte payload ceiling → can't do coding/immobiliser/block-write procedures.
2. Incomplete KWP2000 data-link (no one-byte-header support some ECUs use).
3. You don't control timing/init → can't run custom init or raw programming
   sequence. Cheap clones have out-of-spec fast-init timing (some ECUs won't wake).
4. Rover payloads proprietary → returns raw bytes without meaning.
OK for casual GEMS fault-code reads if it connects; do NOT plan programming
around it. STN1100-based OBDLink chips (ST commands, finer timing) are the
"better ELM" if staying in interpreter world.

## J2534 PassThru
SAE J2534 = Windows DLL API + hardware exposing raw protocol channels (ISO9141,
KWP2000, CAN) with programmable timing — sanctioned OEM reflash route, modern
equivalent of the VCSI box. GEMS predates the mandate so not strictly needed, but
most robust off-the-shelf way to get properly-timed raw K-line writes. Device:
**Tactrix OpenPort 2.0** (72MHz, USB, K-line ISO9141/14230 + CAN, free J2534
DLL). From Python: ctypes onto vendor DLL (Windows). Ties you to Windows + DLL —
heavier than the clean-serial MCU path. https://www.tactrix.com/index.php?Itemid=61

## The timing problem (core trade-off: who owns timing?)
K-line needs precise control: 5-baud init (address at 5 bit/s ~2s, then flip to
10400 within ~60ms window to catch 0x55 sync), inter-byte P1/P4 ~5ms, response
P2 ~25-50ms. Miss mid-flash → brick. **USB is the enemy**: FT232R default latency
timer 16ms (lowerable to 1ms), plus documented bit-bang timing inaccuracy. Fine
for reads (retries paper over it), real risk for programming.

## Practical path for this project
1. Start: genuine FTDI KKL cable (£10) + pyserial to prove reads and slow-init
   vs a real car (or the emulator). Set FTDI latency timer to 1ms.
2. Build L9637D + Pico/ESP32 front-end for timing-critical work; keep the SAME
   framed serial protocol the emulator uses → real hardware and virtual ECU
   swappable (the "transport swappable for real hardware later" pillar).
3. Reserve J2534/OpenPort as fallback only if attempting real GEMS reflash and
   DIY timing proves insufficient (though GEMS reflash = EPROM swap anyway — see
   [[research-gems-hardware]]).

## Part numbers / links
- L9637D https://www.st.com/resource/en/datasheet/l9637.pdf · MC33290
  https://www.nxp.com/docs/en/data-sheet/MC33290.pdf · SN65HVDA195 · Si9241A
- MikroE ISO 9141 Click https://www.mikroe.com/iso-9141-click
- Genuine KKL cable https://www.obdinnovations.com/vag-kkl-k-line-obd2-usb-interface-cable-with-ftdi-ft232rl-chip/
- Libraries: https://github.com/muki01/OBD2_KLine_Library · https://github.com/iwanders/OBD9141
- Tactrix OpenPort 2.0 https://www.tactrix.com/index.php?Itemid=61

## Concrete US-sourced parts list (given to user 2026-07-06)
User is in the US. Recommended two-part kit:

**Buy first — read a real ECU today (~$20-30):**
- Genuine-FTDI KKL 409.1 cable (search "OHP FTDI FT232RL KKL VAG-COM 409.1"),
  Amazon US. MUST be genuine FTDI, not clone. Shows as COM port → pyserial direct.

**The Pico hacking rig (~$45-60 total):**
| Item | Part | US source | ~USD |
|---|---|---|---|
| MCU | Raspberry Pi Pico (or Pico 2) | Adafruit/SparkFun/PiShop.us/DigiKey/Amazon | $4-6 |
| Transceiver | MikroE ISO 9141 Click (L9637D, no bare-chip solder) | DigiKey/Mouser/mikroe.com | $18-22 |
| OBD plug | OBD2 male 16-pin pigtail w/ bare wires | Amazon US | $8-12 |
| Breadboard+jumpers | any starter kit | Amazon/SparkFun | $10 |
| Optional | 8-ch USB logic analyzer (clone) to watch K-line | Amazon | $12-15 |

Bare-chip alternative to the Click (if soldering): NXP MC33290 or TI SN65HVDA195
(current, in-production; L9637D getting scarce) — DigiKey/Mouser.

**Wiring:** transceiver K→OBD pin7, VBAT→OBD pin16 (+12V, FUSE IT 1-2A), GND→OBD
pins4&5; transceiver logic→Pico 3V3, TX/RX→Pico UART (GP0/GP1), GND→Pico GND.
ALL grounds common; transceiver needs real car 12V on VBAT for correct K-line
level. Pico powered from laptop USB.

**Firmware/language:** Pico runs Arduino C++ (muki01 or iwanders libs) for the
timing-critical 5-baud init — easier than MicroPython. Python stays on the laptop
above the wire. NAS/US-spec GEMS trucks are OBD-II compliant → generic reads work
even on the cheap path; Rover-proprietary data needs the real rig.

**Safety:** pin16 always live (fuse it); start read-only; test writes against the
virtual ECU first — botched immobiliser write = non-starting P38.

Related: [[research-kline-protocols]], [[research-python-architecture]],
[[research-gems-hardware]]
