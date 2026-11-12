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
| 10AS EEPROM | ~~8-pin (likely SOIC-8)~~ **CORRECTED 2026-10-02: embedded inside the main ZC99305CFN (PLCC-52)** | alarm/immobiliser store (EKA + codes) | **T48 CANNOT read this — PLCC-52 exceeds its pin-count capability.** See the bootstrap-mode lead below as the alternative. |

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

**⚠️ CORRECTED 2026-10-02 — the T48 CANNOT serve as the 10AS fallback as planned.**
The 10AS EEPROM was assumed to be a discrete 8-pin chip (fallback #2 above); the
user has now confirmed from the physical board that the 10AS's **only IC is the
Motorola ZC99305CFN in a PLCC-52 package**, with the EKA/config data embedded
**inside that microcontroller**, not in a separate discrete EEPROM. **PLCC-52
exceeds the T48's pin-count capability** — it cannot read this chip at all. The
T48 remains valid for the GEMS 27C512/27C1001 dumps (already done, see
`EPROM_DUMP_ANALYSIS.md`), but is **no longer a fallback route for the 10AS**.
The two live options for the 10AS are now: (1) the K-line route above (unchanged),
or (2) the ZC99305 bootstrap-mode UART dump below.

## External lead — Gemini "GEMS 8 tool dev" guide (2026-09-28, UNVERIFIED)

A user-supplied LLM (Gemini) architecture write-up. Treat as **leads/hypotheses,
NOT ground truth** (same rule as the FlemcoDesign app: validate against the T48
dump / LR data / raw bytes). It contains **no hard data** (no offsets, no bytes, no
checksum algorithm) — just generic tool-dev guidance plus a few plausible specifics.

**Corroborates (consistent with our docs):**
- Intel **87C196KC** (MCS-96) + **M27C1001**, 128 KB / 131072 bytes (0x0–0x1FFFF).
- Immobiliser = a **startup validation routine** that checks the 10AS's coded serial
  frames against internal registers → an **immo-delete = binary-patch that routine**
  in the 27C1001 code image (matches the speculative write-path above), then
  **recompute the block checksum** or the 87C196KC drops to fail-safe.
- **Checksum-after-modify** is a real constraint to remember for any EPROM patch.

**Do NOT trust (unverified / likely invented / conflicting):**
- Claims the **fuel map lives in the M27C1001** — CONFLICTS with our split
  (**27C512 = fuel maps, 27C1001 = ignition + code**). Don't accept.
- Specific map dims/axes/units (e.g. "AFR 8×10, X=RPM Y=coolant"; 16×16 fuel/ign
  ms/°BTDC) — plausible-sounding but unverified LLM detail.
- Checksum "8- or 16-bit summation over designated boundaries" — vague/generic;
  unconfirmed GEMS uses it or where.

**Actionable takeaway:** none new on its own; it slightly reinforces the immo-delete
plan (patch the 27C1001 validation routine + fix the checksum). Verify everything
against the T48 dump when it arrives.

### Gemini follow-up (2026-09-28) — "fixed 16-bit mobilise code" claim (UNVERIFIED)

Second Gemini message claims the 10AS→ECM mobilise signal is a **fixed 16-bit code**
(not rolling), sent as a **serial burst** each ignition-on, "sniffable once," e.g.
`A3F2` (a fabricated placeholder — no source, no real capture).

- ✅ **"Fixed, not rolling" aligns with our inference** (stored two-copy immo block
  A4–A8, synced by Security-Learn ⇒ stored secret, not a rolling counter). But BOTH
  are inference, not proof. (The fob→10AS RF link IS rolling; that's separate.)
- ⚠️ **CONFLICTS with our hardware:** we captured that exact wire (C225 p15 /
  C1017 p26) with the PIO sniffer at ignition-on and saw **NO structured serial** —
  only a ~1 ms transient then flat. So "just sniff the 4 hex chars" is **not a free
  lunch; we tried and got nothing.** Either the burst rides on the high DC level
  (8–11 V) where the 1-bit L9637D comparator can't resolve it (needs a scope/ADC),
  or the claim is wrong.
- ⚠️ "16-bit / 2 bytes" unconfirmed — our located block is records A4–A8 (maybe
  >2 B). "force-learn 0000" is speculative.
- **Takeaway:** IF fixed, the code lives in the EEPROM (ECM A4–A8 via `0x3C` / T48,
  and the 10AS EEPROM) — **read the chip, not the wire** (the wire came up empty).
  Reinforces the T48/0x3C plan; do NOT re-chase wire-sniffing on this claim alone.

## Fault injection (EMFI) — a REAL fallback via PicoEMP (not ruled out)

Revised 2026-09-28 (was briefly "ruled out"). The specific attack in O'Flynn's
"Bam the BAM" paper (glitch the BAM password check) is **PowerPC/MPC5xxx-specific**
and does NOT apply to GEMS. BUT the underlying **fault-injection technique is
general** and applies to any MCU, including the GEMS **Intel 87C196KC**.

- **Where it could help GEMS:** (1) ⭐ **extract locked INTERNAL 87C196KC code** IF
  the T48 can't read it (the internal-vs-external code-split caveat — critical code
  like the immo validation / `$27` handler *might* be in the MCU's read-protected
  internal memory, not the external 27C1001). Fault injection is the standard way to
  defeat read-out protection. (2) Glitch the immobiliser validation branch to
  mobilise without the code.
- **Cost barrier is GONE:** the **PicoEMP** (NewAE — same folks as the paper) is an
  **open-source ~$30 RP2040-based EMFI tool** (a Pico + HV pulse circuit), vs a ~$3k
  ChipShouter. Fits our existing Pico toolchain.
- **Still effort-intensive / not plug-and-play:** PicoEMP is only the pulse
  generator; a working attack also needs a trigger, success/failure detection,
  target power/reset control, and probe XY+timing+voltage sweeping. Success not
  guaranteed.
- **Gating:** only needed IF the T48 dump shows critical code is **locked inside the
  MCU**. If it's all in the external 27C1001 (our assumption), just READ it — no EMFI.
  **So: dump with the T48 FIRST, check the code split; keep PicoEMP as the cheap
  plan-B for locked internal code / immo-glitch.**

## External lead — Gemini "ZC99305 bootstrap dump" procedure (2026-10-02, UNVERIFIED)

User-supplied Gemini write-up on reading the **10AS's own microcontroller**
(**Motorola ZC99305CFN, PLCC-52** — confirmed by the user from the physical board;
NOT the GEMS 87C196KC above) via its **bootstrap/boot-ROM mode** over a direct UART
connection, bypassing the K-line entirely. Same rule as all LLM-sourced leads in this
file: **treat as hypothesis, not ground truth** — no datasheet, no confirmed byte
offsets, no confirmed baud rate.

**The claimed procedure:**
1. **Force bootstrap mode**: ground **MODA (pin 4)** and **MODB (pin 5)**, then pulse
   **RESET (pin 2)** low→high while they're held low.
2. **Isolate pins 20 (RxD) and 21 (TxD)** from the Lucas board's onboard K-line
   transceiver — Gemini says these pins are hard-wired into that circuit on the 10AS
   PCB, so they must be desoldered/lifted off their pads (or the trace cut) before an
   external UART can drive them without contention.
3. **Power**: VSS (pin 1 or 27) → GND, VDD (pin 52 or 26) → +5V.
4. **Handshake**: send sync byte `0xFF`; a correctly-wired/correctly-clocked chip
   echoes `0xFF` back, then a ~256-byte bootstrap-loader "RAM utility" is streamed in,
   which then dumps the internal EEPROM out over TxD.
5. **$0-hardware version** (2nd Gemini message, 2026-10-02): a plain USB-TTL adapter
   (CH340/CP2102/FT232RL, ~$6) or an existing Pico/Arduino as a dumb UART bridge is
   sufficient — no VVDI/UPA-USB/XPROG programmer needed. Free software: RealTerm, the
   legacy "HC11Boot"/"Motor05" DOS utilities, or a ~15-line pyserial script.

**Confirmed independently (by the user, from the physical board):**
- Crystal next to the ZC99305CFN reads **4.0000 MHz**.

**UNRESOLVED — do not assume a baud rate:**
- Gemini's reference point ("8 MHz → 1200 baud") was stated with more confidence
  than is actually warranted; the real HC11-family bootstrap baud divisor depends on
  the specific part's boot ROM and was never verified against a datasheet. A naive
  "half the crystal, half the baud" guess gives 600 baud at 4 MHz, but this is
  **unconfirmed** — 300 or 1200 are also plausible depending on the actual divisor.
  **Resolve empirically**: wire up at low risk, sweep `0xFF` at 300/600/1200 baud,
  take whichever gets a clean echo.
- **Do not conflate this with the separate 366-baud figure** logged 2026-09-30 (see
  `memory/real-gems-protocol.md` / CLAUDE.md backlog) — that number is an unverified
  external claim about the **10AS↔ECM mobilise-line K-line protocol** (pin 15/C225,
  a totally different signal), and was already contradicted by the user's own PIO
  bench capture on that line (no decodable serial, just a DC transient). It has no
  bearing on the ZC99305 bootstrap UART (pins 20/21) discussed here.

**Before cutting anything:** confirm PLCC-52 pin-1 orientation (notch/dot/bevel
corner) against the physical part — counting pins wrong on a 52-pin package with no
printed numbers risks lifting/cutting the wrong traces, which is not easily
recoverable.

**Status:** not attempted. Lowest-cost dump path found so far for the 10AS
specifically (vs. a $200–400 VVDI/UPA-USB/XPROG programmer) IF the bootstrap
handshake and baud rate can be confirmed empirically. Ties to [EKA read from the
Lucas 10AS] backlog item and `docs/10as-pinout.md`.
