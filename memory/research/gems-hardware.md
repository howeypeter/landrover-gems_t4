---
name: research-gems-hardware
description: Research findings — GEMS ECU hardware internals, what "programming" it means, and the Disco 2/GEMS correction
metadata:
  type: reference
---

# GEMS ECU Hardware & What "Programming" Means

Research pass 2026-07-06. Lucas/SAGEM Generic Engine Management System.

## HEADLINE CORRECTION: "Discovery 2 petrol with GEMS" cannot exist

GEMS was fitted to:
- **Range Rover P38A 4.0/4.6 V8 — 1995 to early 1999** (flagship GEMS platform)
- **Discovery Series I — 1996 to early 1999** (the "1996 Disco" V8i, 300Tdi-era body)
- **Defender 90 NAS V8 — 1997** (US-market run)

**Discovery 2 (1998→) petrol V8 was ALWAYS Bosch Motronic M5.2.1 "Thor" — never
GEMS.** Disco 2 launched late 1998 as a 1999 model, AFTER the GEMS era ended.
The GEMS→Thor switch happened at the 1999 model year (~"XA" VIN prefix).

**So: if the user's truck genuinely behaves as GEMS, it is a Discovery 1 or a
P38, NOT a Discovery 2.** A petrol Disco 2 = Thor. This is the first fork in
VIN identification. Confusion source: there IS a GEMS Discovery — the Series I —
and people say "Disco 2" loosely. Vendor catalogues split exactly: Disco 1 =
GEMS chip, Disco 2 = Thor/Motronic. NEEDS USER CONFIRMATION of actual vehicle.

## Hardware architecture

- **Two processors in one ECU** ("one side fuel, one side ignition") — dual-CPU.
- **Microcontroller: Intel 87C196KC** (MCS-96 16-bit family; chip marking
  `AN87C196KC`). Mask/OTP-ROM part, NOT flash — the reason GEMS is "chipped" by
  swapping external EPROMs, not reflashed.
- **Two socketed UV-EPROMs** (plug-in swap, no soldering):

| Chip | Size | Holds |
|---|---|---|
| 27C512 | 64 KB | Fuel maps + fuelling calibration |
| 27C1001 | 128 KB | Ignition maps + main program code |

- **No EEPROM/flash calibration region** to write over the diagnostic port.
- Map locations (COMMUNITY reverse-engineering, firmware-dependent, two variant
  reports): 27C512 fuel maps ~0x55D9 and 0x56E1; 27C1001 ignition ~0x13AEA
  (and 0x13BF2), all 16×16 8-bit tables. Exact offsets vary by firmware rev.
- **"GEMS 8"** = the V8 application (8 cylinders), NOT a version number. No
  evidence of a "GEMS 3" Land Rover ECU (don't confuse with unrelated gems.co.uk
  aftermarket ECUs).
- ECU part numbers (LR service, on case): ERR7109 (4.0), ERR6645, ERR5871,
  AMR5465. Internal Lucas/SAGEM `5WK7xxx`-style number UNVERIFIED.

## What "programming a GEMS ECU" actually means — THREE unrelated things

Only ONE happens over the diagnostic port. This reshapes the project goal.

**(a) Calibration / fuel + ignition maps → CHIP SWAP ONLY (bench).** There is
NO over-the-K-line calibration reflash for GEMS. Maps are in UV-EPROM; to change
them you pull the socketed 27C512/27C1001 and fit re-burned chips. This is the
sharp GEMS-vs-Thor divide: Thor is flash-based and dealer-reflashable (famous
"14 writes" limit); GEMS reflash simply does not exist. Aftermarket chips are
"undetectable to TestBook" — because TestBook had NO GEMS calibration
read-back/verify. So an authentic emulator should NOT offer "reprogram
calibration" for GEMS.

**(b) Immobiliser "Security Learn" → the ONE genuine K-line write.** The BeCM
mobilises the engine ECU by sending a coded signal. If BeCM↔ECU codes desync
("ENGINE IMMOBILISED"), a tool puts the ECU into Security Learn: the next code
received is stored as the new master (not compared). Procedure: enter Security
Learn → cycle ignition off/on → BeCM re-sends → status flips to Set. Done
entirely over K-line, no chip removal. This IS the project's re-sync party piece.
(Note: earliest P38 GEMS may lack the per-ECU immobiliser code later cars had.)

**(c) VIN / ZCS-style config → NOT in the GEMS ECU.** On the P38, VIN, market
coding, EKA, options live in the **BeCM**, not the engine ECU. TestBook coded
BeCMs by "Market" (UK/Europe/Gulf/Australia/NAS). The GEMS ECU has no
user-writable VIN/config store. So ZCS/VIN/EKA screens belong on the BeCM path;
the GEMS path exposes only faults, live data, actuator tests, adaptation reset,
and security learn.

## Chip-tuning community

- Method: desocket → read on bench EPROM programmer → edit maps → burn new
  27C512/27C1001 → refit. Screwdriver + programmer, no soldering.
- Tools: TunerPro with hand-built XDF defs (no maintained public GEMS XDF).
  WinOLS doesn't reliably auto-find GEMS tables or checksum. Mostly manual.
- Checksums: GEMS checksum handling poorly documented — a known pain point.
  Must recompute after edits or ECU misbehaves. Algorithm not cleanly published.
- Vendors: Tornado Systems, The Wedge Shop, RPi Engineering/v8engines — sell
  pre-burned chip pairs (rev limit ~5500→6500, revised fuelling). Security
  re-learn may be needed after fitting on immobilised cars.
- Reman "Plug n' Drive" ECUs clone donor EPROM + immobiliser data (no re-sync).

## TestBook GEMS functions (via Nanocom NCOM05 as public proxy)

Confirmed: read/clear faults · live data · output/actuator tests · reset
adaptives · Security Learn. NOT offered for GEMS: calibration reflash, VIN
coding, throttle-pot coding. TestBook's real "programming" on a P38 was BeCM
config (by Market) + EKA, not engine-ECU flashing.

## Sources
- Lucas 14CUX (GEMS history/years): https://en.wikipedia.org/wiki/Lucas_14CUX
- P38A (GEMS→Thor 1999): https://en.wikipedia.org/wiki/Range_Rover_(P38A)
- Nanocom NCOM05 GEMS: https://www.nanocom-diagnostics.com/product/ncom05-range-rover-p38-gems-petrol-to-1999-kit
- Tornado GEMS chips: https://tornadosystems.com/product/tornado-gems-chip-set-for-standard-p38-range-rover-v8-4-0-4-6-ltr/
- Security Learn / immobiliser: https://rangeroverp38.org/range-rover-p38-petrol-94-99-gems-becm-to-engine-immobiliser-code-re-sync-tool/
- Reman part numbers: https://www.precisionecu.com/products/1995-1998-range-rover-se-hse-p38-lp-v8-4-0l-and-v8-4-6l-remanufactured-gems-8-ecm-plug-n-drive

NOTE: mg-rover.org, rangerovers.net, landroversonly.com, aulro.com block
automated fetch (Tollbit 402/307). Ask user to save the richest tuning threads.

Related: [[research-gems-data]], [[research-opensource-tools]],
[[research-kline-protocols]], [[gems-p38-focus]]
