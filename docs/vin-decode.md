# Land Rover VIN decode + reconstruction from the ECU's last-6

**Idea (2026-09-19):** the GEMS ECU (or, on a Discovery 1, the Lucas 10AS)
stores only the **last 6 characters** of the VIN — the unique serial. But for a
*known* vehicle the first **11** characters are almost entirely fixed/derivable
from what we already know (marque, model, body, engine, gearbox, year, plant).
So **full VIN ≈ (derived 11-char prefix) + (read last-6)**. This turns "read the
VIN" — which the engine ECU can't fully answer — into "read the 6-char serial and
prepend the known prefix."

## ⚠️ Caveats (read before trusting a reconstruction)

- **The engine ECU may not hold the last-6 at all.** On the user's real Disco-1
  ECU, the secure read `22 04 C4` returned `7F 22 80` (negative / unavailable) —
  the ECM does **not** carry the VIN last-6; it lives in the **Lucas 10AS**
  (Disco 1) or the **BeCM** (P38). See the "EKA read from the 10AS" backlog item
  — the 10AS is where both the EKA and the VIN serial live on a Disco 1. So
  reconstruction still depends on sourcing the last-6 (10AS read, ECM coding on
  variants that do store it, or the owner simply knowing it).
- **This table is the general (ROW/UK) Land Rover scheme.** **NAS
  (North-American-spec) VINs can differ** in some positions and must be
  cross-checked against the actual plate before the reconstruction is trusted.
  The user's truck is a **NAS Discovery 1 GEMS** (per the Service-09 + 10AS
  findings), so verify against the door/windscreen VIN plate.
- **A VIN has no check digit in this scheme** to self-validate a guess (unlike
  US FMVSS position-9 check digits on some makes), so a wrong prefix character
  won't be caught automatically — hence "verify against the plate."
- Reconstruction is an **identification aid**, not proof of identity. Never use
  it to represent a vehicle as something it isn't.

## The 17-character structure

`S A L | LJ | G | LJ | M | 3 | V | A | 123456`  ← illustrative Disco-1 shape

| Pos | Field | Notes |
|----:|-------|-------|
| 1 | Geographic region | `S` = Europe |
| 2 | Country | `A` = United Kingdom |
| 3 | Manufacturer | `L` = Land Rover (so 1–3 = **`SAL`** WMI) |
| 4–5 | Marque / model | see table |
| 6 | Wheelbase | see table |
| 7 | Body style | (same letter pairs as 4–5 in this scheme) |
| 8 | Engine type | see table |
| 9 | Gearbox / steering | see table |
| 10 | Model year | see table |
| 11 | Assembly plant | `A` Solihull UK / `F` worldwide / `G` South Africa |
| 12–17 | **Unique serial** | **the "last 6" the ECU/10AS stores** |

### 4th–5th / 7th — model / body

| Code | Model |
|---|---|
| LB | Series III |
| LD | Ninety, One Ten, 127, Defender |
| LH | Range Rover (Classic) |
| **LJ** | **Discovery** |
| LM | Range Rover L322 |
| LN | Freelander |
| LP | Range Rover (P38A) |
| LT | Discovery Series II |

### 6th — wheelbase

| Code | Wheelbase |
|---|---|
| A | Series III 88″ / Defender 90″ XHD / RRC 100″ / P38A 108″ / Freelander |
| B | Series III 88″ Lightweight / Defender 110″ XHD / RRC LSE 108″ / Freelander Commercial |
| C | Series III 109″ / Defender 130″ XHD |
| D | Series III 109″ |
| **G** | **100″ (Discovery)** |
| H | 110″ (L/R) |
| K | 130″ (L/R) |
| M | Special build |
| R | 110″ (24 V) |
| S | 90″ (24 V) |
| V | 90″ (L/R) |

### 8th — engine type (V8 rows are the GEMS-relevant ones)

| Code | Engine |
|---|---|
| A | 1.8 K-series I4, HC unleaded |
| B | 2.5 I4 turbo-diesel / 19J 2.0 L-series TD |
| C | 2.5 I4 diesel / 12J 1.8 K-series LC unleaded |
| D | 2.5 I4 petrol / 17H 1.8 K-series LC leaded |
| E | 3.5 V8 carb HC / 2.4 VM diesel / 2.0 BMW M47 Td4 |
| F | 2.5 I4 TD (200Tdi/300Tdi) non-EGR/cat / 1.8 K HC leaded |
| G | 2.25 I4 diesel / 2.5 KV6 unleaded |
| H | 2.25 I4 petrol / 2.5 KV6 leaded |
| **J** | **4.6 V8 EFI petrol** / 2.5 KV6 ethanol |
| L | 3.5 V8 EFI petrol |
| **M** | **3.9 & 4.0 V8 EFI petrol** |
| N | 2.5 I4 VM diesel |
| P | 2.6 I6 IOE petrol |
| V | 3.5 V8 carb LC |
| W | 2.5 I6 BMW diesel |
| Y | 2.0 I4 Mpi petrol |
| 1 | 4.0 V8 EFI LC with cat |
| 2 | 4.0 V8 EFI HC with cat |
| 3 | 4.0 V8 EFI LC without cat |
| 6 | 2.5 I4 TD (200/300Tdi) EGR/cat |
| 8 | 2.5 I5 Td5 EGR |
| 9 | 2.5 I5 Td5 EGR no-cat (Disco II) / 2.8 I6 M52 BMW petrol |

> **GEMS 4.0/4.6:** the engine char is one of **`M`** (3.9/4.0), **`J`** (4.6),
> or the cat-specific 4.0 digits **`1`/`2`/`3`**. Confirm against the plate — a
> NAS cat truck may use `1`/`2` rather than `M`.

### 9th — gearbox / steering

| Code | Gearbox / drive |
|---|---|
| 1 | 4-speed / JATCO 5-sp auto — RHD |
| 2 | 4-speed / JATCO 5-sp auto — LHD |
| **3** | **Chrysler 747 3-sp auto / ZF 4-sp auto — RHD** |
| **4** | **Chrysler 747 3-sp auto / ZF 4-sp auto — LHD** |
| 5 | 4-speed + overdrive — RHD |
| 6 | 4-speed + overdrive — LHD |
| 7 | LT77/LT85/R380/PG1 5-sp manual — RHD |
| 8 | LT77/LT85/R380/PG1 5-sp manual — LHD |

> **NAS = LHD:** so a NAS GEMS auto is `4` (ZF 4-sp auto, LHD); a NAS manual is
> `8`. (RHD equivalents are `3` / `7`.)

### 10th — model year

| Code | Year | | Code | Year |
|---|---|-|---|---|
| M | 1995 | | X | 1999 |
| T | 1996 | | Y | 2000 |
| V | 1997 | | 1 | 2001 |
| W | 1998 | | 2 | 2002 |

*(Full range in the source: A/B/C/D/E/F/G/H/J = 2010–2018 reuse letters;
K=1993, L=1994. For a GEMS Disco 1 the year is one of **T/V/W/X** = 1996–1999.)*

### 11th — assembly plant

| Code | Plant |
|---|---|
| A | Solihull, United Kingdom |
| F | Worldwide |
| G | South Africa |

## Worked reconstruction — Disco-1 GEMS (template)

For the user's vehicle (NAS Discovery 1, GEMS V8), fill the knowns:

```
S A L  L J  G  L J  <engine>  <gbox>  <year>  <plant>  <LAST-6 from ECU/10AS>
└─SAL─┘ └Disco┘ 100" └Disco┘   M/J/1/2  4 or 8  T/V/W/X   A/F      e.g. 123456
```

- **1–7 fixed for any Disco 1:** `SALLJG` + body `LJ` → **`SALLJGLJ`** *(verify
  char 7 body-style vs plate)*.
- **8 engine:** `M` (4.0) or `J` (4.6), or a cat digit `1`/`2` on NAS.
- **9 gearbox:** `4` (ZF auto, LHD/NAS) or `8` (manual, LHD/NAS).
- **10 year:** `T`96 / `V`97 / `W`98 / `X`99.
- **11 plant:** `A` (Solihull) for most; `F` worldwide.
- **12–17:** the **last 6 read from the ECU coding or the 10AS EEPROM.**

So once the market/engine/gearbox/year are pinned, **only the last 6 vary**, and
those are exactly what the module stores — hence the reconstruction.

## How this could be built (if picked up)

A small pure helper `gems_t4/gems/vin.py`:
- `decode_vin(vin) -> dict` — explode a 17-char VIN into the fields above.
- `reconstruct_vin(prefix_fields, last6) -> str` — assemble from known
  attributes + the read serial, returning the 17-char VIN **flagged
  "reconstructed, verify against plate."**
- Surface in the Toolbox (web + GUI): show the read last-6, the derived prefix,
  and the assembled full VIN with the caveat banner.

Data source: this table (general LR scheme). **Do not** present a reconstructed
VIN as authoritative — always label it and prompt the user to confirm against
the physical plate. Tie-in: the last-6 comes from the **[EKA read from the Lucas
10AS]** work (Disco 1) or secure ECM coding (`gems_t4 kline secure`) where a
variant stores it.

*Source: user-provided Land Rover VIN breakdown, 2026-09-19. General ROW/UK
scheme; NAS positions to be verified against the vehicle.*
