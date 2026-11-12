# CAN bus reference research (deferred — NOT part of current GEMS/Discovery 1 scope)

Logged 2026-10-08. This is background research from a side conversation about
making Board 1 (the K-line adapter) also CAN-capable, for a hypothetical future
"universal pre/post-2010 vehicle adapter." **The user's actual Discovery 1 has no
CAN bus at all** — CAN only arrives with the L322 Range Rover in 2002 (see
CLAUDE.md "The headline: No CAN bus"). This doc exists purely so the research
isn't lost; it is **not wired into Board 1's real design** (`docs/two-board-rig.md`,
`diagrams/PCB_Board_Scheme/PCB_Board_Scheme.md`), which stays K-line-only.

## If CAN is ever added to Board 1 (Pico-based)

The Pico/RP2040 has **no built-in CAN peripheral**, so three distinct chip-level
functions are needed, mapped to physical parts:

| Function | Part | Role |
|---|---|---|
| Host MCU | Pico (existing) | runs everything, unchanged |
| CAN(-FD) controller | **MCP2518FD** | SPI-interface chip; handles framing/arbitration/CRC/bit-stuffing — logic the Pico can't do natively |
| CAN(-FD) transceiver | **TCAN1042** | converts the controller's digital signal to CAN-H/CAN-L differential voltage on the wire |

- **2 new chips total** (MCP2518FD + TCAN1042), wired: Pico (SPI) → MCP2518FD → TCAN1042 → OBD-II pins 6 (CAN-H) / 14 (CAN-L).
- This pairing is **backward-compatible with classic CAN 2.0**, not just CAN-FD — one addition covers both eras, so there's no reason to pick a CAN-2.0-only part instead (e.g. the older MCP2515).
- No termination resistor needed on the adapter side — the vehicle's own ECUs provide the bus's 120 Ω termination; the adapter is a high-impedance tap, not a bus endpoint.
- A combined single-chip controller+transceiver part exists for **classic CAN** (Microchip **MCP25625**) — confirmed with reasonable confidence. No combined CAN-**FD** single-chip part was confirmed; would need to verify current Microchip/TI lineups before relying on one.

## Why "just use an STM32H725 instead" doesn't actually help here

Explored and rejected swapping the host MCU to STM32H725 (what comma.ai's Red
Panda uses) to get native CAN-FD. Two separate ideas got untangled in this
discussion — worth keeping both distinctions on record:

1. **STM32H725 combines host-MCU + CAN-controller functions in one chip — it
   does NOT also integrate the transceiver.** No MCU integrates the analog
   CAN-H/CAN-L driver; the transceiver is always a separate chip on any
   platform, Pico or STM32. So the real comparison is:

   | | Host MCU | CAN controller | CAN transceiver |
   |---|---|---|---|
   | Red Panda | STM32H725 | **same chip** (its FDCAN peripheral) | separate chip |
   | Board 1 (Pico) | Pico | separate chip (MCP2518FD) | separate chip (TCAN1042) |

2. **Swapping the Pico for an STM32H725 just to gain native CAN would be a
   platform re-do, not a chip swap** — STM32H725 has **no built-in WiFi/BLE
   radio** (unlike the Pico 2 W), so you'd lose the project's whole wireless
   strategy and have to re-add a separate radio module anyway; plus it means
   throwing away all the hardware-verified Pico firmware (`pico_kline_all`,
   K-line timing via PIO, BLE/WiFi/LittleFS) for a completely different
   toolchain (STM32CubeIDE/HAL vs Arduino). Not worth it for a feature
   (CAN) that's out of scope for this project anyway.

3. **Using an STM32H725 as a "CAN coprocessor" bridged to the Pico via
   GPIO/SPI was also considered and rejected** — it would still need its own
   external transceiver (so no chip-count savings there), plus you'd be
   writing and maintaining an entire second firmware project on a full
   Cortex-M7 MCU just to replicate what the $3 MCP2518FD already does with an
   existing driver library. Strictly more parts, more cost, more firmware,
   for the same two-function split.

**Conclusion: if CAN is ever wanted on Board 1, add MCP2518FD + TCAN1042 to the
existing Pico design. Do not re-platform to STM32H725.**

## How Red Panda actually runs multiple simultaneous CAN buses

Confirmed directly from comma.ai's open-source firmware
(`github.com/commaai/panda`, files `board/drivers/fdcan.h` and
`board/boards/red.h`):

- **The STM32H725 has 3 independent, built-in FDCAN controller instances**
  (`FDCAN_GlobalTypeDef *cans[PANDA_CAN_CNT] = {FDCAN1, FDCAN2, FDCAN3};`),
  each with its own interrupt handlers and health/error tracking — confirmed
  in source, not inferred.
- **4 physical transceiver-enable GPIOs exist** (`GPIOG 11`, `GPIOB 3`,
  `GPIOD 7`, `GPIOB 4`), but there are only 3 controller instances — so one of
  them (**FDCAN2**) is time-shared between **two** physical transceivers (2
  and 4) via pin muxing, while FDCAN1 and FDCAN3 are each hardwired to one
  dedicated transceiver (1 and 3).
- **The muxing mechanism is electrical sensing + active firmware logic, NOT a
  passive effect of which way a cable is plugged in.** Precisely:
  1. Orientation is **sensed electrically** — the harness config reads ADC
     voltages on two sense pins (`adc_signal_SBU1`/`SBU2`, the same kind of
     pins USB-C uses for cable-orientation detection) to set
     `harness.status == HARNESS_STATUS_FLIPPED`.
  2. Based on that sensed value, firmware (`red_set_can_mode()`) **actively
     reconfigures GPIO alternate-function routing** (`set_gpio_mode`,
     `set_gpio_alternate`) to rewire which physical pins connect to FDCAN2's
     TX/RX, and calls `red_enable_can_transceiver()` to power the correct
     transceiver on.
  3. The connector/cable itself does nothing by itself — it's purely the
     thing being electrically sensed; all the actual switching happens inside
     the chip, in software, in response to that sensed signal.
- **Net result:** 3 simultaneous real CAN-FD buses, one of which is
  switchable between two physical ports depending on sensed harness
  orientation — i.e. "3 buses, 4 ports," matching comma.ai's own description
  ("CAN FD on all 3 buses + the one we multiplex" — this exact phrasing is
  from a user-supplied source, not independently confirmed against an
  official comma.ai document; treat as plausible paraphrase, not verified
  quote).
- A code comment in `fdcan.h` notes a known issue: "while multiplexing
  between buses 1 and 3 we are getting ACK errors that overwhelm CAN core, by
  resetting it recovers faster" — real-world evidence of contention/erratum
  handling around this scheme, kept here in case it's ever relevant to a
  future design using similar muxing.
