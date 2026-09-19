# Land Rover VIN decode + reconstruction from the ECU's last-6

**Idea (2026-09-19):** the GEMS ECU (or, on a Discovery 1, the Lucas 10AS)
stores only the **last 6 characters** of the VIN — the unique serial. For a
*known* vehicle the first **11** characters are almost entirely fixed/derivable,
so **full VIN ≈ (derived 11-char prefix) + (read last-6)**.

> ⚠️ **Two different Land Rover VIN schemes — use the right one.** The
> **NAS (US/Canada)** 17-char VIN and the **ROW/UK** VIN are **structurally
> different** (different field→position mapping, not just different codes). The
> **user's truck is a NAS Discovery 1 GEMS**, so **§1 (NAS) is the one to use**;
> §2 (ROW/UK) is kept for RHD/UK trucks and must not be mixed with it.

## ⚠️ Caveats (read before trusting a reconstruction)

- **The engine ECU may not hold the last-6.** On the user's real Disco-1 ECU the
  secure read `22 04 C4` returned `7F 22 80` (unavailable) — the ECM does **not**
  carry the VIN serial; on a Disco 1 it's in the **Lucas 10AS** (P38 = BeCM). So
  reconstruction depends on sourcing the last-6 (10AS read — the [EKA/10AS]
  backlog item — or the owner simply knowing it).
- **NAS has a check digit (position 9)** — so a reconstruction **can be
  validated**, and pos 9 must be *computed*, not guessed (algorithm in §3).
  (The ROW/UK scheme in §2 has **no** check digit.)
- Reconstruction is an **identification aid**, never proof of identity. Always
  confirm against the physical VIN plate (door/windscreen/chassis).

---

## §1 — NAS (US/Canada) scheme — **the user's Disco 1**

Source: Wikibooks "Land Rover VIN Codes" (the position tables there are the
NAS/US-Canada breakdown), read 2026-09-19. Positions relevant to the GEMS era
(Discovery 1 '94–'99, P38 Range Rover '95–'02, NAS Defender 90/110):

| Pos | Field | Disco-1 GEMS value |
|----:|-------|--------------------|
| 1–3 | WMI | **`SAL`** (Land Rover UK/Europe) |
| 4 | **Model line** | **`J`** = Discovery ('94–'98 & '99 Discovery SD) |
| 5 | **Model series / GVWR / emissions** | **`Y`** = Discovery (federal); **`N`** = Discovery **California emissions** ('95–'96) |
| 6 | **Body type** | **`1`** = 4-door wagon (Discovery '94–'04) |
| 7 | **Engine** | **`2`** = 4.0L V8 OHV seq-MPI (Discovery '96–'02); **`4`** = 4.6L (Disco '03); `5`=4.0 LEV '00–'02; `6`=4.6 LEV/ULEV; `9`=4.6 '04 |
| 8 | **Transmission** (all **LHD**) | **`4`** = ZF 4HP22 auto (4HP24 with 4.6) — Disco '94–'04; **`8`** = 5-sp manual (Disco '94–'97) |
| 9 | **Check digit** | computed from the other 16 (see §3) — `0`–`9` or `X` |
| 10 | **Model year** | `T`=1996, `V`=1997, `W`=1998, `X`=1999 (GEMS = ~T/V/W; `X`/99 is usually Thor) |
| 11 | **Assembly plant** | **`A`** = Solihull UK (`H` Halewood, `2` Nitra — later models) |
| 12–17 | **Unique serial** | **the "last-6" the 10AS/ECU stores** |

### Worked NAS Disco-1 GEMS template

```
S A L  J  Y  1  2  4  [C]  [YR]  A  NNNNNN
└WMI┘  │  │  │  │  │   │    │    │   └ last-6 (from 10AS / owner)
       │  │  │  │  │   │    │    └ plant: A = Solihull
       │  │  │  │  │   │    └ year: T96 / V97 / W98
       │  │  │  │  │   └ check digit (COMPUTE — §3)
       │  │  │  │  └ transmission: 4 = ZF auto (LHD) | 8 = 5-sp manual
       │  │  │  └ engine: 2 = 4.0 V8 | 4 = 4.6 V8
       │  │  └ body: 1 = 4-door wagon
       │  └ series/emissions: Y = federal | N = California ('95–96)
       └ model line: J = Discovery
```

So for a **federal NAS Disco-1 GEMS 4.0 auto** the fixed stem is **`SALJY124`**
(positions 1–8). Then only the **check digit (computed), year, and last-6** vary
— plant is `A`. That's an extremely tight reconstruction: give it the year and
the serial and it's fully determined *and* self-checking.

Branches to pick correctly for the specific truck:
- **California** emissions '95–'96 → pos 5 = `N` (not `Y`).
- **4.6L** → pos 7 = `4`; **manual** → pos 8 = `8`.
- The VIN does **not** flag GEMS-vs-Thor for the Discovery (both are engine `2`);
  the year (pos 10) is the tell — `T/V/W` (96–98) GEMS, `X` (99) usually Thor.
  (On the **P38** it *is* flagged: pos 5 `A`-following-`P` = GEMS early-'99,
  `V`-following-`P` = Bosch '99–'00.)

### Other NAS GEMS-era model lines (pos 4), for reference
`H` = Range Rover Classic ('87–'95) · `P` = Range Rover P38A ('95–'02) ·
`D` = Defender ('93–'95,'97) · `T` = Discovery II ('99–'04).
NAS body codes: `1` 4-dr wagon; `2` 2-dr soft top (Defender 90) / 4-dr wagon
(Freelander); `3` 2-dr wagon (Defender 90 '95,'97).
NAS Rover-V8 engine codes (pos 7): `1`=3.5, `2`=3.9/4.0, `3`=4.2, `4`=4.6,
`5`=4.0 LEV, `6`=4.6 LEV/ULEV, `9`=4.6 '04.

---

## §2 — ROW / UK scheme (RHD / non-NAS) — **NOT the user's truck**

The classic rest-of-world Land Rover VIN uses **two-letter** model/body codes and
a different position mapping. Kept here for completeness (e.g. a UK RHD donor).
**Do not apply these positions to a NAS VIN.**

| Pos | Field | Notes |
|----:|-------|-------|
| 1–3 | Region/Country/Mfr | `S`=Europe, `A`=UK, `L`=Land Rover → `SAL` |
| 4–5 | Marque/model | `LJ`=Discovery, `LP`=P38A, `LH`=RR Classic, `LD`=Defender, `LT`=Disco II, `LN`=Freelander, `LM`=RR L322, `LB`=Series III |
| 6 | Wheelbase | `G`=100″ (Discovery), `A`=RRC 100″/P38 108″, `H`=110″, `K`=130″, `V`=90″ … |
| 7 | Body style | (same two-letter model pairs as 4–5) |
| 8 | Engine | `M`=3.9/4.0 V8 EFI, `J`=4.6 V8 EFI, `L`=3.5 V8 EFI, `1/2/3`=4.0 V8 cat variants, `8/9`=Td5 … |
| 9 | Gearbox/steering | `3`=ZF auto RHD, `4`=ZF auto LHD, `7`=5-sp man RHD, `8`=5-sp man LHD … (**no check digit**) |
| 10 | Model year | `T`96 `V`97 `W`98 `X`99 `M`95 `L`94 `K`93 … |
| 11 | Plant | `A`=Solihull, `F`=worldwide, `G`=South Africa |
| 12–17 | Serial | last-6 |

*(This is the table the user first supplied, 2026-09-19.)*

---

## §3 — NAS check digit (position 9) — compute & validate

NAS VINs carry the FMVSS/NHTSA check digit at position 9, so a reconstruction is
**self-validating**. Algorithm:

1. **Transliterate** each of the 17 chars to a value:
   `A=1 B=2 C=3 D=4 E=5 F=6 G=7 H=8 J=1 K=2 L=3 M=4 N=5 P=7 R=9 S=2 T=3 U=4 V=5 W=6 X=7 Y=8 Z=9`;
   digits `0–9` = themselves. (`I O Q` are never used in a VIN.)
2. **Weights** by position 1→17: `8 7 6 5 4 3 2 10 0 9 8 7 6 5 4 3 2`
   (position 9's weight is 0 — it's the check digit itself).
3. `sum(value × weight) mod 11`. Result `10` → check digit **`X`**; else the digit.

So `reconstruct_vin(...)` computes pos 9 from the assembled string (with any
placeholder at 9), and `validate_vin(vin)` recomputes and compares — catching a
wrong prefix/serial. (ROW/UK VINs skip this — no check digit to verify against.)

---

## §4 — How this could be built (if picked up)

A small pure helper `gems_t4/gems/vin.py`:
- `check_digit(vin) -> str` — the NAS position-9 algorithm (§3).
- `validate_vin(vin) -> bool` — recompute pos 9 and compare (NAS only).
- `decode_vin(vin, scheme="nas"|"row") -> dict` — explode into fields (§1/§2).
- `reconstruct_vin(fields, last6, scheme="nas") -> str` — assemble from known
  attributes + read serial; for NAS, **compute** pos 9; return the 17-char VIN
  flagged **"reconstructed — verify against the plate."**
- Surface in the Toolbox (web + GUI): show the read last-6, the derived prefix,
  the computed check digit, and the assembled full VIN with the caveat banner.
  For a NAS truck, also show ✅/❌ from `validate_vin`.

Data source: §1 (Wikibooks, NAS) + §2 (user table, ROW). Never present a
reconstructed VIN as authoritative. Tie-in: the last-6 comes from the **[EKA read
from the Lucas 10AS]** work (Disco 1) or secure ECM coding where a variant stores
it (`gems_t4 kline secure`).

*Sources: Wikibooks "Vehicle Identification Numbers (VIN codes)/Land Rover/VIN
Codes" (NAS scheme, read 2026-09-19); user-provided ROW/UK breakdown (2026-09-19).
NAS positions are authoritative for the user's Disco 1 but still verify vs plate.*
