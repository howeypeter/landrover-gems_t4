---
name: research-kline-protocols
description: Research findings — K-line wire/message protocols for GEMS (ISO 9141, KWP2000, Rover-native), init, services, programming
metadata:
  type: reference
---

# K-line Diagnostic Protocols for GEMS

Research pass 2026-07-06. Labels: [GEMS] documented for GEMS, [MEMS3]/[MEMS]
Revill/Bourassa Rover work, [GENERIC] KWP2000/ISO (inferred for GEMS).

## Most important finding: GEMS is NOT field-reflashable [GEMS]
Motorola 68HC11 + two external UV-EPROMs (27C512 fuel maps, 27C1001 ignition +
code). "Remapping" = swapping physical chips. NO RequestDownload/TransferData
flash sequence over K-line for GEMS. T4's GEMS "programming" = config/adaptation/
coding writes to a small serial EEPROM + immobiliser re-sync — NOT map rewrite.
Key divergence from MEMS3, which uses AMD AM29F200BT flash and IS reprogrammable
over the link. Revill's reflash/seed-key work is real but MEMS3-only.

## Physical layer [applies to GEMS]
J1962 pin 7 = K-line, pins 4/5 ground, pin 16 +12V. Single bidirectional wire,
half-duplex. L-line (pin 15) optional, not needed for GEMS. Idle HIGH ≈12V
(pull-up ~510Ω); "0"=0V, "1"=12V. 10,400 baud 8N1 LSB-first after init (some
Rover modes 9600 8N1). **Self-echo: tester sees its own TX bytes echoed back —
read and discard before ECU reply.**

## Initialization — three families
**5-baud slow init (ISO 9141-2)** [generic + partial GEMS]: idle high 300ms →
tester sends address at 5 baud (~2s): **0x33** = OBD-II generic, **0x16** =
Rover-native wake → ECU sends sync 0x55 → two keybytes KB1/KB2 → tester sends
KB2 inverted → ECU sends address inverted. Windows: W1 55-255ms, W2 5-20ms, W3
0-20ms, W4 25-50ms, W5 ≥300ms retry.

**Fast init (ISO 14230-2/KWP2000)** [generic, MEMS3]: K high ≥300ms → 25ms low +
25ms high wake pulse → send StartCommunication 81 → positive response w/ keybytes.

**Rover-native MEMS-style (no ISO handshake)** [MEMS, closest to GEMS-native]:
open 9600 8N1, send fixed wake bytes, read echoes. MEMS 1.6 documented:
send CA→echo CA, send 75→echo 75, send D0→D0 99 00 03 03 (ID follows). **ECU
echoes every command byte first, then appends data.** Best template for
GEMS-native behaviour.

## Protocol family — what applies to GEMS
Three protocols on Rover K-lines (Revill lists all three for MEMS3):
1. ISO 9141-2 — 10400 baud, 5-baud init (generic-OBD path, least reliable)
2. "Rover BMW 9600 Baud" — 9600 baud, KWP2000-like msgs, different addressing
   (native dealer path; ties to Ediabas/BMW parentage)
3. ISO 14230-2/KWP2000 — 10400 baud, fast init (most reliable for MEMS3 flash)

For GEMS: NAS trucks OBD-II compliant → ISO 9141-2 for emissions PIDs (what
ELM327 sees). Full dealer access (all DTCs, live data, actuators, adaptations) =
Rover proprietary protocol (single-byte-echo MEMS family / "Rover 9600"). From
Revill's MEMS3: framing conventions + service-ID philosophy ($61 records, $7F
negatives, session model) TRANSFER to GEMS; flash/seed-key/memory-map specifics
DO NOT.

## Message format & timing
**KWP2000/ISO14230 frame** [generic]: `[Fmt][Tgt][Src][Len?][SID+data...][CS]`
- Fmt: top 2 bits addressing mode, bottom 6 bits length (1-63); 0x80|len with
  addresses. Tester src conventionally 0xF1, functional target 0x33.
- SID: positive response = request SID + 0x40 (0x21→0x61, 0x10→0x50).
- CS: simple 8-bit sum of preceding bytes mod 256. No CRC.
- Example: tester `C1 33 F1 81 66` → ECU `83 F1 01 C1 E9 8F AE`.

**Rover-native**: no framing/checksum; single-byte commands, ECU echoes then
returns fixed-length block (0x7D→32 bytes, 0x80→28 bytes). Big-endian.

**Timing P1-P4** [generic KWP2000]: P1 inter-byte in response 0-20ms; P2 req-end
→resp-start 25-50ms typical; P3 resp-end→next req 55ms min–5000ms max (exceed→
link drops); P4 inter-byte in request 5-20ms. These + 2s init + 10.4kbaud =
authentic slowness; 108-param poll genuinely ~1 sample/2s.

## Diagnostic services
**Rover-native single-byte commands (MEMS 1.6, best byte-level GEMS template)**:
7D=32-byte live frame A, 80=28-byte frame B, 01/11=fuel pump off/on, 02/12=PTC
relay, 03/13=A/C relay, F8=fire ignition coil, FB=request IAC, FD/FE=idle valve
±1 step, 91/92=idle speed ±, 93/94=ignition advance ±, 79/7A=fuel trim ±, CC=
clear faults, F4=NOP/keep-alive, F6=disconnect. Maps closely to CLAUDE.md
actuator list + service adjustments.

**Revill MEMS3 model ($61/$7F in CLAUDE.md)** [MEMS3]: Service $21 Request Data
by Local ID → $61 Read Data by Local ID; each record `61 <localID> <payload>`,
words/bytes at fixed offsets, ~108 measures. $7F negative: `7F <SID> <NRC>`.
NRCs: 0x11 svc-not-supported, 0x12 subfn-not-supported, 0x22 conditions-not-
correct, 0x24 request-sequence-error, 0x31 out-of-range, 0x33 security-access-
denied, 0x78 response-pending. MEMS3 doesn't fully follow KWP2000 (proprietary IDs).

**Standard KWP2000 SIDs for programming** [generic]: 10 StartDiagnosticSession
(81 default, 85/86 programming), 11 ECUReset, **27 SecurityAccess** (27 01
requestSeed, 27 02 sendKey), 31 StartRoutine, 32 StopRoutine, 33 RoutineResults,
**34 RequestDownload**, 35 RequestUpload, **36 TransferData** (must follow 34/35
or NRC 0x24), 37 RequestTransferExit, 23 ReadMemoryByAddress, 3D WriteMemory
ByAddress, 3B WriteDataByLocalID (coding writes), 14/18/17 DTC services, 85
StartProgrammingMode.

## Programming / reflash
**GEMS (what T4 did)** [GEMS]: config writes only, NOT reflash — 4.0↔4.6 map
select flag, VIN/coding/variant in serial EEPROM, immobiliser/BeCM security
re-sync ("ENGINE IMMOBILISED" recovery), reset adaptations. To change maps:
remove ECU, swap 27C512/27C1001 EPROMs offline. Exact GEMS security-unlock bytes
NOT public — the one genuinely undocumented GEMS operation.

**MEMS3 reflash (documented, for contrast/future Td5 profile)** [MEMS3]: AMD
AM29F200BT-90SE at base $100000 (SA0 64KB boot, SA1-4 168KB firmware, SA5 8KB
coding, SA6 16KB maps). Enter boot mode via programming session (10 85) → 16-bit
seed→key (27 01/27 02, Revill's reverse-engineered algorithm) → erase sectors
via 31 routines (full erase returns 7F..78 pending) → block writes with 16-bit
word checksums → verify. Timings: map write ~24s+22s verify; firmware ~3m44s
+4m19s. Runtime data (DTCs/adaptations/immobiliser) in separate 93C66 EEPROM.

**GEMS seed-key** [inference]: no public algorithm. GEMS security = BeCM↔ECM
mobilisation handshake + T4 unlock before coding write. For emulator: model
seed-key (27 01→seed, 27 02→key) with opaque/toy algorithm + authentic
"ENGINE IMMOBILISED"/"security access denied ($7F $33)" failure modes.

## Recommendations for the Python tool
1. Transport: one K-line 8N1 tester-initiated half-duplex with self-echo;
   support 10.4kbaud (ISO/KWP) + 9600 (Rover-native).
2. Three pluggable init strategies: 5-baud (0x33/0x16), fast init, Rover-native
   (CA 75 D0 echo).
3. Services: $21/$61 records with $7F negatives (Revill) for 40-60 params +
   single-byte actuator/adjust commands (Bourassa) for pump/coil/idle/timing.
4. Timing realism: count bytes on the virtual wire → bandwidth curve falls out.
5. Programming screens: real config/coding writes + adaptation reset + seed-key/
   immobiliser-sync with authentic refusals; present map reflash as chip-swap
   (lookalike); optionally keep MEMS3 34/36 flash behind a "Td5/MEMS3" profile.

## Sources
- Revill: https://andrewrevill.co.uk/MEMS3TestBookT4Support.htm · https://andrewrevill.co.uk/MEMSFlasher.htm
- Bourassa MEMS 1.6 (byte-level commands): https://colinbourassa.github.io/car_stuff/mems_interface/
- Nanocom GEMS guide: https://www.nanocom-diagnostics.com/uploads/downloads/Lucas%20GEMS%20ECU%20Guide.pdf
- KWP2000 ISO 14230-3: http://www.internetsomething.com/kwp/KWP2000%20ISO%2014230-3.pdf
- obd-cable 5-baud guide: https://obd-cable.com/iso-9141-2-k-line-5-baud-handshake-guide/
- bri3d/kwp2000: https://github.com/bri3d/kwp2000 · pd0wm/pq-flasher: https://github.com/pd0wm/pq-flasher

**Confidence:** GEMS=EPROM not-reflashable = HIGH (multiple vendors). Rover-native
single-byte echo protocol = documented for MEMS 1.6, analogous to GEMS but NOT
byte-verified on GEMS — exact GEMS command bytes/address are the main public gap.
MEMS3 flash fully documented but MEMS3-only. GEMS seed-key/immobiliser bytes not public.

Related: [[research-gems-hardware]], [[research-gems-data]],
[[research-python-architecture]], [[research-hardware-interfaces]], [[gems-p38-focus]]
