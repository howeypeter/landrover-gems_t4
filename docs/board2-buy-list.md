# Board 2: what to buy (excludes parts on hand)

Drafted 2026-11-15 from `docs/board2-bom.md` and `hardware/board2-bom-mouser.csv`, after the user confirmed what they already own. Part numbers marked "verify" were not confirmed on Mouser (checklist E1).

## Already on hand (not on this list)

D3 TVS (1.5KE24A), F2 fuse holder and 2 A fuse, both illuminated switches, crimper (SN-28B type), hook-up wire, M4 screws, standoffs, enclosure, barrel jack, 12 V supply, and the XY308 screw terminals (J1 x1, SW1/SW2 x2).

## 1. PCB (JLCPCB)

| Item | Qty | Notes |
|---|---|---|
| Board 2 PCB, Rev 1.0 (Gerbers from Cherry Blossom) | as needed | 2 layers, 87 x 77 mm, 1.6 mm, 1 oz, HASL, white silk. Settings in checklist C3. Check JLCPCB's minimum order quantity at checkout. |

## 2. Mouser (upload `hardware/board2-bom-mouser.csv`)

| Mfr part number | Description | Qty | Notes |
|---|---|---|---|
| TBP02R1-381-16BE | Same Sky, J2: 16-pos 3.81 mm right-angle pluggable header | 1 | verify |
| TBP02P1-381-16BE | Same Sky, J2 mate: 16-pos pluggable screw-terminal plug | 1 | verify |
| TBL002A-350-08GR-2OR | Same Sky, J3/J4/J5: 8-pos 3.5 mm 45 deg push-button terminal block | 3 | verify (doc also cites DigiKey 102-6384-ND) |
| SB540-T | Diodes Inc., D2: 5 A 40 V Schottky, DO-201AD | 1 | |
| M20-9980546 | Harwin, J6-J9: 2x5 2.54 mm vertical pin header | 4 | verify; pull key-row pins 7/8 before soldering |
| M20-1070500 | Harwin 2x5 female crimp housing | 6 | 4 active + 2 spare |
| M20-1060500 | Harwin 1x5 female crimp housing | 6 | 4 active + 2 spare |
| M20-003 | Harwin polarizing key plug | 10 | 2 per 2x5 housing + 2 spare; count to be confirmed |
| M20-1180046 | Harwin female crimp contact, tin, 22-30 AWG | 50 | 32 needed + 18 spare |

## Before you order

- **Mouser numbers:** none of the Harwin or Same Sky numbers have been confirmed in Mouser's catalogue. Upload the CSV and check each line imports with stock and the right quantity.
- **Key plugs:** confirm 2 per 2x5 housing against the Harwin housing drawing (the older BOM said 1).
- **Crimper:** test-crimp a few spare contacts before building cables (checklist E2).
- **Tools not in any BOM:** solder, and pliers to pull the key-row pins from the J6-J9 headers.
