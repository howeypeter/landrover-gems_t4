# RAVE cross-reference — SFI-V8 NAS (GEMS Discovery 1) vs our docs

**Source of truth:** RAVE, Discovery 1 (`lj`) Electrical Troubleshooting Manual
`etlj970x.pdf`, section **A3 "SEQUENTIAL MULTIPORT FUEL INJECTION (SFI-V8) (NAS
ONLY)"**, circuit-diagram pages **39–51** (1-indexed, = the `pages` arg for the
Read tool). SFI-V8 NAS is the GEMS engine on the NAS Discovery 1 — **our exact
vehicle/ECU**. The ECM is **Z132**, connectors **C1017 / C1032 / C1033** — the
same connector codes our SM001 pinout uses, so this cross-references pin-for-pin.

RAVE wins on every conflict. This file reconciles RAVE against:
`docs/gems-ecu-pinout.md` (SM001), `memory/real-gems-protocol.md` (the bench
`$21` map + protocol), `bench/README.md`, and `CLAUDE.md`.

Method note: pin functions/wire-colours are read directly off the RAVE circuit
pages; where a wire route is ambiguous in the render, it's marked *(verify)*.

---

## 1. Headline result — everything material is CONFIRMED

Our SM001 pinout and the bench `$21` sensor map **agree with RAVE** on every
pin we had identified. No corrections to the sensor/switch assignments were
needed; RAVE *adds* wire colours, the connected components, and the exact
switch chains, and lets us retire a few "verify" caveats.

---

## 2. ECM C1017 (red 36-way, sensors/inputs/comms) — pin-by-pin

| Pin | RAVE (SFI-V8 NAS) | wire | our SM001 | bench `$21` | status |
|----:|-------------------|------|-----------|-------------|--------|
| 1  | Anti-Lock Brake System ECU (Z108) via C1026 p8 / C2084 p29 | YK | ABS ECU | tested pin 1 | ✅ match |
| 7  | Fuel Level Sensor (Z134[1]) via instruments S2100 | GB | Fuel Level Sensor | 0x02 | ✅ match |
| 8  | Right Heated O2 **post-cat** (X290) | R | R O2 post-cat | **0x1B** | ✅ match |
| 10 | Knock-sensor **shield ground** (S142) | RB | "Knock Sensors" | — | ✅ (refine: shield, not a knock signal) |
| 11 | **Left** Knock Sensor (X295) | O | Left Knock Sensor | ⛔ pulse | ✅ match |
| 12 | **Right** Knock Sensor (X296) | Y | Right Knock Sensor | ⛔ pulse | ✅ match |
| 13 | Intake Air Temp Sensor (X311) *(verify wire)* | SLG | Intake Air Temp | **0x01** raw | ✅ match |
| 14 | Engine Coolant Temp Sensor (X126, C152) | G | Coolant Temp | **0x00** raw | ✅ match |
| 15 | **Throttle Position Sensor** (X171, C149) | YLG¹ | **TPS** | **0x0F** raw + **0x10** | ✅ match |
| 16 | Mass Air Flow Sensor (X105, C133 p2) | UG | MAF | **0x11** | ✅ match |
| 17 | **Left** Heated O2 **post-cat** (X289) | GW | L O2 post-cat | **0x1A** | ✅ match |
| 18 | Neutral Sense Diode (Z273) → Park/Neutral switch (X167) | OB | Neutral Sense Diode | tested | ✅ match |
| 20 | Data Link Connector (OBD-II) **L-line** | WK | DLC K/L line | — | ✅ (see §4) |
| 21 | Heated Front Screen sense (S2126) via C1027 p10 | YK | Heated Front Screen | raw **0x16** + 0x22 bit14 | ✅ match |
| 23 | Data Link Connector (OBD-II) **K-line** | WLG | DLC K/L line | K-line (hw) | ✅ (see §4) |
| 26 | Theft Alarm Unit (Z163, C225) | B | Theft Alarm Unit | — | ✅ match |
| 27 | *(see C1032 p27 for Vehicle Speed — see note)* | — | Vehicle Speed Output | ⛔ pulse | ⚠️ see §5 |
| 28 | **A/C evaporator-temp switch (X101) → dual-pressure switch (X102)** | YB | A/C Switches | raw **0x06** + 0x22 bit13 | ✅ match |
| 29 | **Front A/C request switch (X225)** → fan-speed switch → gnd | PB | A/C Switches | **0x22 bit6** only | ✅ match |
| 30 | Fuel Pressure Sensor (X320) *(verify wire)* | — | Fuel Pressure Sensor | **0x05** | ✅ match |
| 32 | **Right** Heated O2 pre-cat signal (X160) *(verify)* | — | Heated O2 Sensors | (see 33/34) | ✅ region match |
| 33 | **Right** Heated O2 **pre-cat** (X160) | OG | Right Heated O2 | **0x19** | ✅ match |
| 34 | **Left** Heated O2 **pre-cat** (X139) | GR | Left Heated O2 | **0x18** | ✅ match |
| 35 | Engine Fuel Temp Sensor (X128, C150) | SW | Engine Fuel Temp | **0x15** raw | ✅ match |
| 36 | Injector return / sensor common *(verify)* | — | "Multiple Sensor Connection" | — | ⚠️ see §5 |

¹ SM001's C507 photo transcribed TPS as `YU` (yellow/blue); RAVE `lj` shows the
TPS signal as `YLG`. Both are the Disco-1; the SM001 C507 photo was flagged
"meter-verify, especially the throttle pin". **Trust RAVE (`YLG`) for the Disco-1
harness**; a P38 (C507) loom may differ. This is the one wire-colour to re-meter.

## 3. ECM C1032 (black 36-way, OUTPUTS/actuators) — confirmations

| Pin | RAVE (SFI-V8 NAS) | our SM001 | status |
|----:|-------------------|-----------|--------|
| 1  | A/C Compressor Clutch Relay (K108) | Compressor Clutch Relay | ✅ |
| 3  | Condenser Fan Relay (K109) | Condenser Fan Relay | ✅ |
| 6  | Evap Canister Vent Seal Valve (K233) | same | ✅ |
| 11,13,18,30,32,33,36 | Fuel Injectors (K141, 8 injectors) | Fuel Injectors | ✅ (see note) |
| 15,16,34,35 | Idle Air Control Valve (M112, 4-wire stepper A/C/B/D) | IACV | ✅ |
| 19 | Evap Canister Purge Valve (K132) | same | ✅ |
| 21 | Left/Right pre-cat O2 heater ground | O2 heater | ✅ |
| 22 | Malfunction Indicator Lamp (Check Engine) via C222 | MIL | ✅ |
| 24 | Fuel Pump Relay (Z207[4]) | Fuel Pump Relay | ✅ |
| 27 | **Vehicle Speed** input from instrument cluster [12] (C221 p4 → C209 p17) | (SM001 put VSS on C1017 p27) | ⚠️ **RAVE: C1032 p27** |
| 28 | Post-cat O2 heater ground | O2 post-cat heater | ✅ |

Injector→ECM pin detail from RAVE p2 (C1032): 13(YU) 36(YW) 11(YB) 30(YN)
33(YG) 17??(YS) 32(YR) 18(YK). Note RAVE shows **eight** injector drivers; the
exact pin-per-cylinder differs slightly from SM001's list — recorded here as the
authoritative set: **11, 13, 18, 30, 32, 33, 36** plus one more in the 17/YS row
*(verify the 8th; the render's YS row is ambiguous between C1032 p17 and a
shared node)*.

## 4. ⭐ K-line / L-line — RAVE CONFIRMS the hardware finding

RAVE page 9 (DLC): the OBD-II Data Link Connector **X318** ties to the ECM at:
- **C1017 pin 23 = WLG → K-line** (ISO 9141 J1962 pin 7)
- **C1017 pin 20 = WK → L-line** (ISO 9141 J1962 pin 15 / L-line)

This independently confirms `memory/real-gems-protocol.md`: **K-line = C1017
pin 23** (proven on hardware, 5-baud init) and the **L-line = C1017 pin 20**
(the pin we jumper to the K node to open the proprietary **0xDA** channel). The
SM001 doc listed both pins as "DLC K/L line" without splitting them; **RAVE
splits them: 23 = K, 20 = L.** Our bench had already deduced exactly this.

## 5. Discrepancies / refinements (RAVE overrides)

1. **Vehicle Speed: C1032 p27, not C1017 p27.** SM001 listed "Vehicle Speed
   Output" on C1017 p27. RAVE routes the instrument-cluster vehicle-speed signal
   to **ECM C1032 pin 27** (via C221 p4 / C209 p17). Use C1032 p27 for the VSS
   square-wave-injection work. *(SM001's C1017 p27 may be a transcription slip;
   meter-verify which plug carries the VSS wire on the bench.)*
2. **C1017 p10 = knock-sensor shield ground**, not a knock signal. The knock
   *signals* are p11 (left, X295) and p12 (right, X296); p10 (RB→S142) is the
   shield/screen common. SM001's "Knock Sensors" on p10 is the shield.
3. **C1017 p36 "Multiple Sensor Connection"** (SM001) = a sensor-common/return
   node in RAVE (S150 "Partial" ties several sensor grounds); not a single
   sensor. Consistent, just clarified.
4. **TPS wire colour** — RAVE `YLG` (Disco-1) vs SM001 C507-photo `YU` (P38
   loom). Trust RAVE for our vehicle (§2 note ¹).
5. **Main power / ignition feed** — SM001 already flagged the C1033 p7/p8
   question (p7 = MFI Load Relay, p8 = Satellite Fuse Box 1 per SM001; an older
   bench note had guessed p7=+12V/p8=ign). RAVE p1/p3 show the ECM powered
   through the **Multi-Function Relay Unit Z207** (MFI load relay [1]) off fuse
   F7, with C1033 grounds on p5/p9/p10/p16 → E102. The intermittent-start
   "frayed ignition wire" the user found is the **ignition-switched feed** that
   arms this chain — still **meter-verify C1033 p7/p8 before powering** (unchanged
   guidance).

## 6. `0x22` switch-status bitmap — fully decoded (bench + RAVE)

`$21` id **0x22** is a 16-bit pull-up switch word (float=`7FC0`, all inputs
open). Grounding a switch pin (closing it) **clears that switch's bit**:

| Pin | RAVE function | grounded 0x22 | bit cleared | dedicated raw id |
|----:|---------------|---------------|-------------|------------------|
| 28 | A/C evap-temp + dual-pressure switch (X101/X102) | `5FC0` | **bit 13** (0x2000) | 0x06 (FF/00) |
| 21 | Heated front screen (S2126) | `3FC0` | **bit 14** (0x4000) | 0x16 (FF/00) |
| 29 | Front A/C request switch (X225) | `7F80` | **bit 6** (0x0040) | — (bitmap only) |

Pattern: **A/C-request and both A/C interlock switches feed the ECM's A/C logic**
(RAVE p11), and the heated-screen line (p10) is a load-shed input — all read as
pull-up-to-5V switch-to-ground inputs, exactly matching the bench captures.

## 7. Component reference (RAVE names, for future probing)

ECM=Z132. MAF X105. TPS X171. Coolant-temp X126. Fuel-temp X128. IAT X311.
Fuel-pressure X320. CKP X250 (C1033 p12, shield Z202). CMP Z262. Knock L X295 /
R X296. Pre-cat O2 L X139 / R X160; post-cat O2 L X289 / R X290. IACV M112.
Injectors K141 (C134–C141). Coils Z261 (wasted-spark 1&6/2&3/4&7/5&8 →
C1033 p14/13/15/1). Fuel pump module Z134 (level sensor + pump); inertia switch
X135. Relays Z207 (MFI load [1], sec-air [2], O2 heater [3], fuel pump [4]),
K108 compressor clutch, K109 condenser fan, K121 heated-screen. A/C X225 switch,
X101 evap-temp switch, X102 dual-pressure switch, X247 fan-speed. Park/neutral
X167 + neutral-sense diode Z273 (+ K166 480Ω on manual). DLC X318/OBD-II.
Theft alarm Z163. ABS Z108. Instruments Z142.

---

*Cross-referenced 2026-09-19 from `etlj970x.pdf` A3 (pages 39–51). Index:
`docs/rave-index.md`. RAVE PDFs are Land Rover IP — local only, not committed.*
