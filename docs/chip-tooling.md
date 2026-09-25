# Chip reader/programmer + EPROM write-path plan

Decision for **reading** the GEMS EPROMs and the Lucas 10AS EEPROM on the bench,
plus a **contingent** write-path option. Logged 2026-09-25.

> ⚠️ **Scope:** the tool was bought primarily to **read/dump** chips. The
> **write-path (§below) is speculative** — a *possible* solution (e.g. an
> immobiliser-deleted chip) that we'd only pursue **if the 10AS findings point
> that way**. It is NOT a committed direction. The T48 happens to write too, so
> nothing extra is needed if we ever go there.

## Tool decided + ordered: XGecu T48 (TL866-3G)

**Bought 2026-09-25** — XGecu **T48 "+3 parts"** ($49.99), the current successor
to the TL866II+. **~1 month delivery.** One universal programmer covers every chip
in play; it **reads AND writes** UV-EPROM, EEPROM, and flash, so no second tool is
needed for the write path.

- **"+3 parts"** = programmer + 3 adapter boards (typically SOP8/SOIC8→DIP8 150/200
  mil + a PLCC-type). The programmer itself is identical across all the store's
  package tiers — only the bundled adapters differ; the big "+13/+25 parts" kits
  are TSOP/PLCC/BGA sockets we don't need.
- **Still want a SOIC-8 test clip (~$8, separate)** to read the 10AS EEPROM
  *in-circuit* (no desoldering) — the bundled adapters are for desoldered chips.
- **UV eraser: intentionally NOT bought.** Only needed to reuse genuine UV-EPROMs;
  the reusable-substitute plan below makes it pointless.

## What it does for each chip

| Chip | Package | Role | Action |
|---|---|---|---|
| 27C512 | DIP-28 | GEMS **fuel** maps | read (dump), later write a substitute |
| 27C1001 / 27C010 | DIP-32 | GEMS **ignition + code** (incl. `$27` handler, immobiliser check) | read (dump), later write a patched substitute |
| 10AS EEPROM | 8-pin (likely SOIC-8) | alarm/immobiliser store (EKA + codes) | read (fallback to the K-line route) |

The T48's built-in 40-pin ZIF reads the DIP EPROMs directly (no adapter). Reading
is non-destructive.

## Write path (CONTINGENT — only if 10AS findings lead here)

*Not a committed plan.* This is the approach we'd take **if** we decide to build a
modified chip (e.g. immobiliser-deleted). Captured now so the option is ready.

The stock GEMS chips are **UV-EPROMs** (write-once until UV-erased) — terrible for
tweak-flash-test loops. For development, burn to **pin-compatible electrically-
erasable** parts that drop into the ECU socket (read-only there) but erase+rewrite
on the T48 as many times as needed:

| Stock | Reusable dev substitute | Notes |
|---|---|---|
| 27C512 (DIP-28) | **W27C512** (Winbond EE-EPROM) | Known clean read-mode swap |
| 27C1001 (DIP-32) | **W27C010 / W27E010** | ⚠️ verify read-mode pinout (pin 1 / 31 / 32) vs the 27C1001 the ECU expects before trusting in-car |

Flash (SST39SF010 / AT29C010) also works and the T48 writes it, but its write-mode
pinout differs from 27C010 — fine since the ECU only reads it; the **W27C-series is
the cleaner drop-in**, start there. Buy several spares.

## The actual immobiliser-delete (one contingent write-path use)

*Also speculative — only if we go the write-path route.* The chip is just the
medium. Disabling the immobiliser = a **code patch in the
27C1001 image** — find the mobilise-check (in the `0x2000` code region we
identified) and NOP/short-circuit it to always-pass, then burn the patched image
to a W27C010. That's a reverse-engineering task on the dump, which is why **step
one when the T48 arrives is to dump the stock 27C1001** — that dump is the starting
image for BOTH the `$27` seed→key work (P1.4a) and the immobiliser patch.

## Ordering note: the T48 is the FALLBACK for the 10AS, not the primary path

Reading the 10AS EKA has two independent routes:
1. **K-line at C225 pin 17** (primary) — how Nanocom/Hawkeye do it in seconds; needs
   NO chip reader, works with the adapter already in hand. Crack the 10AS init/
   address over the wire. See `docs/10as-pinout.md`.
2. **Chip read** (fallback) — pull/clip the 10AS EEPROM and dump it on the T48.

So the ~1-month wait blocks nothing: use it to crack the 10AS K-line, and have the
T48 ready as the fallback + for the GEMS EPROM dump/write work. Ties to the
[EKA read from the 10AS], [EPROM programmability], and [immobiliser-from-bench]
backlog items.
