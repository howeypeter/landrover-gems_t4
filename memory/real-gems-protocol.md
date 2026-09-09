---
name: real-gems-protocol
description: The ACTUAL wire protocol a real NAS GEMS ECU speaks — confirmed on physical hardware 2026-08. Ground truth, supersedes the stylized guess for real-ECU work.
metadata:
  type: project
---

**FIRST HARDWARE LIGHT — 2026-08-30/31.** The homemade Pico + L9637D adapter
talked to a **physical P38 GEMS ECU** for the first time. This is the real,
reverse-engineered protocol — use it (not the stylized KWP format in
`protocol/framing.py`) for anything talking to a real ECU. Implemented in
**`gems_t4/protocol/kline.py`** and exposed as **`gems_t4 kline live|dtc|monitor
--port COMx`**.

## The confirmed protocol (NAS GEMS = OBD-II ISO 9141-2)
- **K-line pin:** GEMS ECU **C1017 (36-way red) pin 23**. Pin 20 is the **L-line**
  (the other DLC pin) — both idle high through the pull-up, so idle voltage does
  NOT tell them apart; only which one *answers* an init does. (C1033 18-way black
  = power/ground: pin 7 main +12, pin 8 ignition +12, grounds 5/9/10/16.)
- **Init:** 5-baud **slow** init, address **0x33** (the tool's old default 0x10
  was a wrong placeholder). ECU replies `0x55` sync + keybytes **0x08 0x08**
  (standard ISO 9141-2).
- **Keybyte handshake (was the killer bug):** after KB2 the tester MUST send the
  **inverted second keybyte** (`KB2 ^ 0xFF`) back within the **25–50 ms W4
  window**, then read the ECU's inverted-address reply. Without it the ECU hands
  over keybytes but never enters the initialised state → ignores every request.
  Must be in the **Pico firmware** (W4 is far too tight for a USB/WiFi round-trip).
- **Request frame:** `68 6A F1` + `<service>` + `<data…>` + 1-byte **sum**
  checksum. (NOT the tool's stylized `80 target source len … cksum`.)
- **Response frame:** `48 6B E8` + `<service+0x40>` + `<data…>` + checksum.
  ECU source address = **E8**.
- **Live data:** Mode 01 works (coolant, RPM, timing, O2, fuel trims, MAF,
  throttle…). Mode 01 **PID 00** = supported-PID bitmask (auto-detect PIDs).
- **DTCs:** Mode 03 (stored/confirmed) + **Mode 07 (pending)** — on the bench a
  fresh fault is pending long before it matures to stored; engine-off it may
  NEVER become stored. ECU stays **silent when there are zero codes** (a
  TransportTimeout that means "no codes", not an error). Confirmed pending code
  from the bench (coolant/IAT sensors unplugged): **P1179** (manufacturer-specific).
- **Clearing DTCs (Mode 04) REBOOTS the ECU (confirmed 2026-09-01).** After a
  Mode 04 clear the GEMS ECU drops the K-line session and **goes unresponsive
  for ~1–2 minutes while it reboots its diagnostic subsystem**, then recovers on
  its own (cycling the ignition can force/speed it — it is NOT strictly
  required). You get `init failed (status 1)` on any command in the meantime. The tool handles it: `kline clear`
  does NOT re-read (it prints a "cycle the ignition" hint); the GUI clear drops
  the session (`Backend.disconnect()`) and prompts to cycle before re-reading;
  `Backend.read_*` now reconnect via `_ensure_connected()` so the post-clear
  re-read re-inits instead of crashing on a null client. Also: pending codes for
  a *still-present* fault (a disconnected sensor) reappear immediately —
  clearing a live fault is inherently temporary.
- **Real captured frames (used as test fixtures in `tests/test_kline.py`):**
  PID00 resp `48 6b e8 41 00 bf 9f f9 91 c4`; PID05 (coolant) resp
  `48 6b e8 41 05 00 e1` → 0x00 → −40 °C.
- **OBD-II surface mapped (Tier-1 probe, 2026-09-02; `probe1.py` in ~):**
  Mode 01 = **bank 1 only** (PID20 mask `00000001`, PID40 `00000000` — no
  PID21-60 data). Supported Mode-01 PIDs include the **V8 bank-2** ones now
  decoded (0x08/0x09 STFT/LTFT B2, 0x18/0x19 O2 B2S1/B2S2); 0x03 fuel-system
  status is a string enum (CLI-only candidate, not a gauge). **Mode 09
  (VIN/cal-id/ECU name) is NOT supported — CONFIRMED 2026-09-08 over BLE: PID
  00/02/04/06/0A ALL silent.** So there is NO OBD identity data at all (no VIN,
  Cal ID, CVN, ECU name). The full VIN lives in the body/security module (P38
  **BeCM** / Discovery 1 **Lucas 10AS**, NOT the GEMS engine ECU); the engine ECU
  only *codes* the VIN last-6, and even that is a **proprietary GEMS coding**
  field — NOT readable over OBD, only via the unmapped manufacturer channel
  (0xDA/pentest). `gems_t4 kline vin` + the GUI "Read VIN from ECU" therefore
  return "not available" on the real ECU (correct); the VIN last-6 only resolves
  on the virtual ECU today. Reading real GEMS coding (incl. VIN last-6) is a
  P1.4/P1.5 research target. → **no multi-frame reassembly needed** for the
  OBD-II layer. **Mode 02 (freeze
  frame)** supported (`M02 PID00` mask `7f980000`) but empty on the bench (DTC
  `0000` — no *confirmed* code). **Mode 06 (on-board monitor tests)** supported
  (`4600 fff8…`, TIDs 01-0D). Freeze-frame + Mode 06 populate on-car when a code
  matures — future features.

## Tier-2 probe (2026-09-02) + adversarial review — "OBD-II is the ceiling" was PREMATURE
What we tried: on the 0x33 OBD session, **no KWP2000 service** (`$3E/$10/$1A/$21/
$22/$27`) answered — neither with the OBD header (`68 6A F1`) NOR with KWP2000
framing (fmt `80`/`8L`/`C1` × targets `10/11/12/13/6A/33`). Total silence, not
even `7F`. Earlier 5-baud sweep: only 0x33 answered.
**Correct conclusion (after adversarial deep-research review):** blind SID
probing *on the established OBD session* is exhausted — DON'T repeat it — BUT the
"ceiling" is the *configuration's*, not the rig's. Those SIDs went out on top of
a live ISO 9141-2 OBD session, which is the emissions channel; a KWP2000
manufacturer channel is a SEPARATE session needing its OWN init, so silence is
expected. **Two concrete, cheap, NEVER-actually-tried doors remain (do these
before concluding anything):**
1. **A real KWP2000 StartCommunication fast-init.** Our firmware's "fast init" is
   only a wake pulse — it never sends the StartCommunication frame. Documented LR
   engine-ECU init (Rover MEMS 2J + Td5): fast-init pulse (25 ms low/25 ms high),
   then at 10400 8N1 send **`81 13 F7 81 0C`** (fmt `81`, **dest `13`** = LR
   engine ECU, **source `F7`** — we wrongly used `F1`, SID `81` StartComm),
   expect **`C1 KB1 KB2`**. If dest 13 silent, sweep dest `10/11/12/33/6A`. THEN
   `10 <session>` → `21 <lid>` / `22 <hi><lo>` for live data, `18`/`14` for DTCs.
2. **Un-ground the L-line.** P38 wires the engine ECU to BOTH OBD pin 7 (K) AND
   pin 15 (L); classic ISO 9141 (what T4/TestBook use) sends the 5-baud address
   on K **and** L simultaneously. L tied to ground blocks the manufacturer 5-baud
   channel while K-only ISO 9141-2 (0x33) still answers — EXACTLY the "only 0x33"
   symptom. Free C1017 pin 20 (drive via the L9637D L path / a GPIO) and re-sweep
   5-baud incl. 0x33/**0x16**, at 10400 AND **9600** (MEMS 1.9 = 0x16 @ 9600).
Mistakes found: source addr should be **F7** not F1; never sent SID `81` init;
L grounded during the sweep; omitted 0x16/9600. Only if #1 (real StartComm) and
#2 (live L-line) BOTH stay silent does the ceiling harden → then a real-T4/Nanocom
/Faultmate **K-line capture** (logic analyser on pins 7+15) is the only source of
the service-ID map (public record IS genuinely silent on GEMS SIDs — Revill is
MEMS3/K-series, Nanocom/Faultmate closed). P1179 confirmed = "Max Negative AMFR
Correction Fault" (air/fuel correction limit — matches unplugged sensors).
Sources: rovermems.com (MEMS 2J/1.9 init), SimonRafferty Td5 Arduino, ISO 9141
K+L 5-baud, rangerovers.pub P38 OBD pinout. (Probe scripts: `~/tier2.py`,
`~/tier2b.py`.)

## L-line experiment RESULT (2026-09-03): strong NEGATIVE
Ran the zero-hardware K+L-tied test: C1017 **pin 20 jumpered onto the K node**,
so the 5-baud address drives K and L together. OBD `0x33` still worked tied (no
interference — wiring sound), but a manufacturer sweep — 5-baud slow
(0x13/10/11/12/16/01/28/6A) AND fast-init StartComm (0x13/10/11/12/33/6A), all at
10400 — got **total silence**. So driving the L-line in parallel opens no
manufacturer channel either. **Every firmware/wiring-level door is now tested
negative** (blind KWP on OBD session, fast-init StartComm, K+L-tied). Caveats NOT
yet closed (low-probability): firmware `slowInit` only detects an OBD-style `0x55`
sync, so a non-`0x55` response reads as "no reply" (need a raw-capture firmware
variant to rule out); **9600 baud never tested** (firmware fixed at 10400, MEMS
1.9 precedent); address list may be incomplete. **Blind experimentation is
effectively exhausted** — the realistic path to the proprietary layer is now a
real-T4/Nanocom/Faultmate **K-line capture** or **RAVE** docs, NOT more probing.
Probe: `~/lline_probe.py`.

## Exhaustive K-line pentest (2026-09-04) — 0xDA = REAL channel, but only with the L-line
**⭐ K+L CONFIRMATION (2026-09-04, `~/da_probe.py` + `~/da2_probe.py`, C1017 pin 20
TIED to the K node): 0xDA is a REAL, distinct, security-LOCKED KWP2000 manufacturer
channel — the first proprietary channel found. The L-line is what unlocks it.**
With the L-line in circuit, 0xDA/DB/DC reproducibly complete a 5-baud handshake
(they were SILENT on K-only — see the refutation below), and **0xDA answers KWP
`$22` (ReadDataByCommonID) with a checksum-valid, echo-checked `03 7F 22 33 D7` =
securityAccessDenied (NRC 0x33)** — 10/10 identical across different record IDs,
and UNIQUE to 0xDA (plain OBD 0x33 is silent to the exact same requests). The Pico
can't synthesise a checksummed KWP frame and only the GEMS ECU is on the bench, so
the ECU is exposing a second, security-gated KWP2000 channel that the L-line
unlocks. keybytes: 0xDA=`aa55`; 0xDB/0xDC=`6666` (but DB/DC returned only ECHOes
on reads — **0xDA is the live one**). NOT yet OPENED: `$27 01` requestSeed was
silent — but the reply is **ISO 14230 no-address framing** (fmt byte = length,
`03 7F…`) whereas our requests used the OBD envelope `68 6A F1…`; the fix is to
send bare `<len><data><cksum>` frames — being tested by `~/da3_probe.py`. Ties
straight to the immobiliser / security-access ($27) backlog. **This supersedes the
"OBD is the only door / blind probing exhausted" verdict: there IS a proprietary
door, it's on 0xDA, and it needs the L-line + security access.**

**RESOLUTION (2026-09-04, `~/da_probe.py` Pass 1, K-only): the 0xDA/0xDB/0xDC
"candidates" were FALSE ON K-ONLY — a transient artifact there, not a channel.
(They ARE real with the L-line — see the K+L confirmation above.)** On a focused
re-test each was **silent to 4× raw init** (no emission at all — not even the
`55 aa 55`), so a real session was never even in question. The `0x33` control in
the same run behaved perfectly (raw `55 08 08` ×4, W4 handshake -> keybytes
`0808`, real Mode 01 supported-PID + Mode 03 multi-frame DTC reads), so the method
is sound. The single pentest observation was almost certainly line ringing/echo in
the continuous-sweep timing; it does not reproduce in isolation. **`0x33`/OBD-II is
the only real K-line door.** (I overstated "deterministic, not noise" below — the
cross-baud consistency was one observation, outweighed by 4× fresh silence.) STILL
PENDING: the L-line pass (tie C1017 pin 20 to the K node, re-run da_probe with the
manufacturer addresses) — the one path not yet tried with raw+handshake. The
original (now-superseded) candidate notes are kept below for the record.

Ran the full raw-capture sweep (`~/pentest_scan.py`, pentest firmware
`gems_t4-pico-pentest 2.1.0` with `CMD_RAW_INIT`): ALL 256 5-baud addresses AND
fast-init StartComm dests, at **10400 AND 9600**, RAW capture (no 0x55 filter) —
i.e. it closed every caveat the earlier L-line note listed. Clean, heartbeat-
verified run: **confirmed_silent=1016, unresolved=0**. Result is NOT a pure
negative — for the FIRST time, non-0x33 addresses answered.

**Candidate addresses (10400, the ECU's native baud), reproducible:**
- `0x33 -> 55 08 08`  (OBD control: sync + keybytes 08 08)
- `0xDA -> 55 aa 55`
- `0xDB -> 55 66 66`
- `0xDC -> 55 66 66`
Each starts with the 0x55 sync; only these 3 (of 1016 silent) answered, and each
reproduced as the consistent baud-shifted bytes at 9600 — so they are DETERMINISTIC
ECU emissions, not noise. **The 9600 "hits" (`a5 …`) are artifacts** — a 10400
reply misread at 9600 (0x55->0xA5, 0x08->0x88); `0x33@9600 = a5 88 88` proves it.
So the real finding is just {0xDA,0xDB,0xDC} at 10400.

**UNCONFIRMED — status = candidate, not a channel yet.** The sweep used the RAW
init path (5-baud address only, NO W4 handshake), so it only proved the ECU emits
a sync+2 bytes. Not yet known whether a real session opens. Caveats: keybytes
`aa 55`/`66 66` are non-standard (could be genuine, or a partial 5-baud trigger
emitting sync+garbage); 0xDA/DB/DC are adjacent (could be one channel decoding a
range). **Definitive test = `~/da_probe.py`:** full slow init WITH the W4
inverted-keybyte handshake on 0xDA/DB/DC (the CMD_INIT path `kline live` uses on
0x33); if the handshake completes with stable keybytes -> real session-capable
channel (then chase reads); if it never completes -> artifact, and 0x33 stays the
only door. RUN da_probe.py to resolve. NOTE this supersedes the earlier
"blind experimentation exhausted" framing — the exhaustive raw scan DID surface
leads.

## Pentest tooling notes (2026-09-04)
`~/pentest_scan.py` (RESUMABLE via `pentest_scan.state.json`; append log
`pentest_scan.log`) drives the pentest firmware. Two bugs found & fixed during
bring-up: (1) the multi-frame Mode 03 decode bug in `protocol/kline.py` — >3
stored DTCs span multiple `48 6B E8 43` frames; fixed with `_split_frames`/
`decode_responses`/multi-frame `read_dtcs` (real 2nd-ECU capture
`486be84311930158131604`+`486be84301250000000004` = P1193/P0158/P1316/P0125,
pinned in tests). (2) the scan heartbeat must use the RAW init (CMD_RAW_INIT),
NOT CMD_INIT — CMD_INIT completes the handshake and OPENS a session, and an
in-session ECU refuses every subsequent 5-baud init, which silently poisoned a
whole 34-min run (all 1024 unresolved). Heartbeat = 0x33 raw; it never locks a
session. Pentest firmware is a SEPARATE sketch (`firmware/pico_kline_pentest/`),
production `firmware/pico_kline/` untouched. [[install-editable-from-repo]].

## ⭐⭐ 0xDA SEED IS FLOWING — `$27` half-open (2026-09-08, `da3_probe.py`, K+L)
**BREAKTHROUGH. With the L-line tied (C1017 pin 20 → K node), the 0xDA channel
now returns real SecurityAccess seeds.** `$27 01 requestSeed`, sent in **ISO-14230
no-address framing** `[len][data][sum]` (e.g. `02 27 01 2A`), gets a checksum-valid
positive: `04 67 01 <seed_hi> <seed_lo> <cksum>` → **`67 01 <2-byte seed>`**. The
seed is **randomized every request** (observed `8AE8`, `AE62`, `6FC7`, `2C5E`) —
a genuine algorithm, not an echo/artifact. This supersedes ALL earlier "`$27 01`
silent" notes: the fix was (a) the L-line tied AND (b) no-address framing (the OBD
`68 6A F1` envelope still gets silence/denied). Details:
- Seeds flow in the **default session** — no `$10 StartDiagSession` needed (`$10 <s>`
  returns a non-standard NRC **`0x0C`**, meaning TBD).
- keybytes on 0xDA slow-init = **`aa55`**.
- **Behind the lock:** `$21 01/02` (ReadLocalId) and `$22` (ReadDataByCID) both
  return `securityAccessDenied` (0x33) — so **a valid key unlocks the proprietary
  reads: coding, VIN last-6, and (hypothesis) the `$30`/`$31` actuator/output
  services.** `$3E`/`$81`/`$1A` → serviceNotSupported (focused security+data channel).

**Seed characterized (500-sample harvest, `harvest_seeds.py`/`lcg_test.py`, 2026-09-08):**
16-bit, **500/500 unique** (no tiny-space or fixed-seed shortcut), advances by a
**near-constant ~`0xBF1F` per request** (92% within ±0x400) but is NOT a clean
LCG/counter (exact affine recurrence fits only 5%) and NOT a function of wall-clock
time (timer fit loose) → consistent with a **free-running timer/counter sampled
per request**: an old, simple scheme with fine timing entropy. **Operational
takeaway: seed generation is IRRELEVANT to the key** — the ECU checks `key==f(S)`
for the seed `S` it hands you, so harvesting can't reveal `f`. The harvest's value
was ruling out the lucky cases; the transform `f` is the wall. The simple-seed
prior *does* raise the odds `f` is a classic Lucas/Rover transform (rotate /
XOR-const / add-const / byte-swap), i.e. testable with very few offline-computed
on-ECU attempts.

**NEXT = the seed→key algorithm `f`. DO NOT brute-force.** `$27` locks after ~3 wrong
KEY submissions (`0x36`); the key is 16-bit (65536) so on-ECU brute force is
impossible within budget. The key MUST be computed offline from the algorithm.
Paths: (1) **capture seed→key pairs from a real tool** (Nanocom/Faultmate/T4) with
a K+L logic analyser and reverse the transform — reliable; (2) try **known
Lucas/GEMS `$27` algorithms** offline against a captured seed. Seed requests are
UNLIMITED and safe (they don't touch the attempt counter) — so we can harvest as
many seed samples as we want for offline analysis without risk. Guardrails when we
DO try keys: seed-only until we have an algorithm; ≤3 keys/power-cycle; abort on
`0x36`/`0x37`; power-cycle + wait between sessions; log everything. `da3_probe.py`
now has `SUBMIT_DUMMY_KEY=False` (seed-only) to enforce this.

## Seed→key research synthesis (4-agent web sweep, 2026-09-08)
**No public GEMS-specific `$27` seed→key algorithm exists** (all 4 agents; ~10-15%
one exists). The GEMS aftermarket unlocks the immobiliser by **bench EEPROM edits**
(code stored in the serial EEPROM ~bytes 152-155 & 552-555, two copies), never by a
`$27` key — so there was never community pressure to crack it. No public GEMS
seed→key example pairs anywhere. BUT two **published Lucas-family 16-bit `$27`
transforms** are the lead testable candidates:
- **MEMS3 (Revill)** — LFSR, seed-derived iteration count (1-16), feedback tap on
  bits {9,8,2,1}, AND-cond on {13,3}. Rover K-series, Sagem-built, 16→16-bit KWP
  `$27`. https://andrewrevill.co.uk/MEMS3SeedToKeyAlgorithm.htm (derived from ECU
  ASM; HIGH credibility; 3 of 4 agents converged on it).
- **Td5 (Lucas)** — `byteswap(seed) ^ 0x2E71 + 0xCF -> rotate` (exact rotate step
  unverified). Fully open in SimonRafferty/Land-Rover-Td5-Arduino-Diagnostics &
  EA2EGA/Ekaitza_Itzali. Another Lucas 16-bit analog.
Both implemented (+trivials, +a pairs solver) in **`~/seedkey_candidates.py`**
(offline, no ECU). **Key strategic fact: one captured (seed,key) pair collapses the
trivial families instantly; the LFSR family solves with 2-3 pairs (GF(2) linear
algebra)** — a real-tool logic-analyser capture is the highest-value artifact.
**Definitive fallback = disassemble the `$27` handler out of the GEMS 27C1001 code
EPROM** (Intel AN87C196KC / MCS-96; the 27C512 is fuel-only). Community bin dumps
circulate behind login (TunerPro forum t=4294 reportedly has both EPROMs);
disassembly is the guaranteed-correct path — same way Revill got MEMS3, ties to the
P1.4 chip-read. **L-line/0xDA is explained:** standard dual-line ISO 9141 asserts
the 5-baud address on K AND L; the "unlocked" free state is a real GEMS
"development mode" Faultmate can set. **Caveat to rule out (agent 1):** our 16-bit
`$27` seed vs the 16-bit immobiliser mobilise code (0000-FFFF) are suggestively
similar — verify the 0xDA `$27` is a pure diagnostic cipher, not entangled with the
mobilise path, before trusting a seed→key. **EKA correction (agent 2):** the EKA is
a STORED EEPROM value, NOT derived from VIN — reading it from the Lucas 10AS is a
memory-read task, not a crypto/formula task (update the EKA backlog item). Login-
gated leads for the user: mg-rover.org "Testbook from hell", mhhauto "GEMS 8 IMMO
OFF", TunerPro t=4294 (EPROM dumps), ecuconnections t=59049.

**Attempt plan (on-ECU, budget-limited, needs approval each time):** request a fresh
seed → `python ~/seedkey_candidates.py 0x<seed>` → submit the priority-1 (MEMS3) key
via `$27 02`, ONE per power-cycle, ≤3/cycle, abort on `0x36`/`0x37`. If MEMS3 &
Td5 both miss, the answer is a capture or the EPROM disassembly, not more guessing.

## ⚠️ Unlock ATTEMPT result (2026-09-08) — MEMS3/Td5 did NOT open it; sendKey is opaque
Ran budget-limited on-ECU `$27` attempts (`~/unlock_attempt.py`, `~/unlock_verify.py`,
`~/disambiguate.py`). **Outcome: the 0xDA `$27` did NOT unlock.** Key facts:
- `$27 02 <any 2-byte key>` returns a **CONSTANT `03 67 02 CC 38`** — identical for
  MEMS3 keys AND a deliberately-wrong key (`0x8579`). So `67 02 CC` is a **canned
  reply, NOT "key accepted"** (a real handler returns `7F 27 35` invalidKey for a
  wrong key; this channel never does). The trailing **`0xCC`** is constant across
  all seeds/keys — possibly a "denied" status byte in a `67 02 <status>` format, or
  a stub.
- **The true oracle = do the locked reads open?** After every accepted-looking
  sendKey, `$21 01/02/03` and `$22 00 00` / `$22 F1 90` STILL return
  `securityAccessDenied (0x33)`. Access was never granted. **MEMS3 is therefore
  NOT confirmed** (and can't be, via this reply — the reply doesn't discriminate).
- The channel is otherwise a genuine KWP responder: `$27 01` gives real varying
  seeds, and other services give real per-service negatives (`$10`->0x0C,
  `$3E/$81/$1A`->0x11, `$21/$22`->0x33), so it's not blindly echoing positives —
  only `$27 02` is opaque.
**Implication:** the two published Lucas quick-wins (MEMS3, Td5) did not open it,
and the sendKey path gives no right/wrong signal beyond the reads (which stay
locked). Blind 16-bit key guessing is NOT viable (no clean oracle + unknown
lockout). **Reliable paths now: (1) disassemble the 27C1001 code EPROM to read the
actual `$27` handler — expected key LENGTH/LEVEL and what `0xCC` means; (2) a real-
tool (Nanocom/Faultmate/T4) logic-analyser capture of a full seed→key→grant.**
Cheap un-run bench diagnostics worth trying first: vary the **key length** (1/3/4
bytes — maybe the ECU wants ≠2 bytes and mishandles ours into the canned reply);
try higher security **levels** (`$27 03/05/07`); and RULE OUT agent-1's caveat that
this `$27` is entangled with the 16-bit immobiliser **mobilise** code, not a
diagnostic cipher. Lockout note: the channel returned `67 02` (never `0x35`) to
wrong keys, so it may not even enforce the `$27` attempt counter — but do NOT
assume; keep power-cycling between batches.

## ⭐⭐⭐ `$27` SEED→KEY CRACKED — key = (seed × 16723) mod 65536 (2026-09-08, from the FlemcoDesign APK)
**The one unknown gating the entire proprietary layer is solved.** Decompiled the
closed-source Android app **"GEMS ECU Utility for Land Rover"** (FlemcoDesign v1.5,
`com.flemcodesign.gems.gemsutility`; apkcombo APK sha256
`a51a9e9df37ce35af9db81a2524a96d3ac3e88e07a6753d67a71edc99a93f5c2`; jadx 1.5.6). The
user owns the vehicle and the app — right-to-repair interop. Its `GEMS.java` implements
the exact 0xDA SecurityAccess we were stuck on:

- **Seed→key: `key = (seed * 16723) % 65536`** (16723 = 0x4153; odd ⇒ clean bijection).
  Seed and key are 16-bit, **big-endian, 4 hex chars** (verified in `rfUtilities`:
  `hexIntToInt` = `parseInt(s,16)`; `intToHex` = big-endian 2-byte). Inverse (if ever
  needed): `seed = key * 0xAADB mod 65536`.
- **Handshake (`authorizeScanTool`):** `1002` → `5002` (StartDiagnosticSession) →
  `2701` → `6701<seed>` (requestSeed) → send `2702<key>` → **`6702AA` = ACCEPTED**.
- **ORACLE RESOLVED:** `6702AA` = accept, **`6702CC` = reject**. Our earlier "`$27 02`
  returns a canned `6702CC`, no oracle" was simply the WRONG-KEY reply — a *correct* key
  returns `AA`. MEMS3/Td5 failed only because the real `f` is this trivial multiply.
- **Channel setup (matches our findings):** ELM327 `ATSP4` (KWP 5-baud), **`ATIIA DA`**
  (init addr 0xDA), **`ATSH C133F1`** (header), `ATSI`. On our Pico stack the seed
  already flows with the no-address `[len][data][sum]` framing (da3) — submit the key the
  same way.

**Full proprietary command map (all behind `$27`), from `GEMS.readSetting`/`writeOptionChanges`:**
- **Reads (service `22`):** VIN `2204C4`; PROM ID `2204E2` (shickenchit's `22 04 E2`);
  displacement/transmission/drivetrain `2204BF`; air-flow `222332`; fuel-flow `222333`;
  throttle `222334`; short-term idle `222336`; long-term idle `222337`. Responses echo
  `62…`. Busy/retry sentinel the app watches for: `2280`.
- **Writes (service `A3`):** reset adaptive values `A3234800`; set immobiliser synch
  (the "pair alarm" Security-Learn) `A300622588`. Close: `A4` then `ATPC`.

**App behaviour notes (from `MainActivity.java`) — what it does NOT do:** the app only
ever WRITES those two `A3` commands (gated behind two switches shown only after a
successful authorized read cycle). VIN, displacement (4.0/4.6), transmission (auto/manual),
and drivetrain are **read-only displays** — it never writes them, so the APK does NOT reveal
coding-WRITE commands for those; it gives their READ identifiers and the write *service*
(`A3`) with two worked examples. Extra facts: **keep-alive = a `2204E2` (PROM ID) read every
~2.5 s** (the tester-present equivalent on this channel). **`2204BF` is a combined config
record** — the app reads it once and byte-decodes displacement (first byte 1|2 ⇒ 4.6 else
4.0), transmission (2|3 ⇒ manual else auto) and drivetrain from the same `6204BF` response.
So the **[4.0/4.6 toggle] backlog item now knows where that field is READ (`2204BF`), just
not how to write it.** To maintain OTHER settings (VIN/displacement/etc.), future work once
`$27` is unlocked: study the `A3` payload format and/or probe WriteDataByCommonID (`2E`)
against the known CIDs with read-back verification (writes — do carefully on the bench).

**STATUS: ✅ UNLOCK CONFIRMED ON HARDWARE (2026-09-08, `~/da6_unlock.py`, BLE, K+L).**
The unlock worked first try on our Disco-1 ECU:
```
1002 -> 02 5002 54            (StartDiagSession OK)
2701 -> 04 6701 BFC8 F3       (seed = BFC8)
key  = (0xBFC8 * 16723) % 65536 = F5D8
2702F5D8 -> 03 6702 AA 16     (6702AA = ACCEPTED)
```
So the FlemcoDesign key is correct for our ECU, the `1002` session prelude works, and
`6702AA`/`6702CC` is confirmed as the accept/reject oracle. Correct keys do NOT touch the
lockout counter, so re-unlocking to read is safe. Next: authorized reads (`~/da7_read.py`
captures real VIN/PROMID/`2204BF` bytes), then implement `security_access` + coding in
`gems_t4`. Guardrails still apply for any WRONG-key situation (`0x36` after ~3, `0x37` =
wait; one attempt per power-cycle). APK decompiled at `scratchpad/gems_apk/jadx_out/`
(GEMS.java, rfUtilities.java, ELM327.java).

**✅ AUTHORIZED READS CONFIRMED (2026-09-08, `~/da7_read.py`, same hot session).** After the
unlock (seed `F6E8` → key `F538` → `6702AA`), every proprietary read answered (frame =
`[len][62 04 xx | 62 23 xx][data][cksum]`):
- **PROM ID `2204E2` → `4096`** (data bytes `40 96`; the app displays it byte-swapped "9640").
- **Config `2204BF` → `00`** ⇒ **displacement 4.0 L, transmission automatic, drivetrain 00**
  (the app derives all three from this one byte: disp 1|2⇒4.6 else 4.0; trans 2|3⇒manual else
  auto). This ECU is a 4.0 auto — consistent with the Disco 1.
- **Live params:** air-flow `222332`→`CD00`, fuel-flow `222333`→`3F00`, throttle `222334`→
  `2000`, short-idle `222336`→`FF00`, long-idle `222337`→`F4`.
- **VIN `2204C4` → `7F 22 80`** = the manufacturer "UNAVAILABLE" negative (the app's `2280`
  sentinel). **VIN last-6 is NOT on this engine ECU** — consistent with an early Disco 1 (VIN
  is in the Lucas 10AS, not the ECM; no OBD Service 09 either). VIN comes from 10AS work here.
Note: `da7_read.py`'s log left the trailing frame checksum on the "data" field; the real
value is those bytes minus the last one (the `gems_t4` decoder strips it via the `[len]…[cksum]`
frame parse).

**✅ 0x3C MEMORY-READ FORMAT CONFIRMED (2026-09-08, `~/da8_secure_probe.py`, unlocked).** On an
unlocked session `0x3C` reads succeed (positive `7C`). **Request = `3C <addrHi> <addrLo> <len>`
— BIG-ENDIAN address** (MSB-first returned real data at both 0x1800 and 0x2000; the LSB-first
order shickenchit quoted read the byte-swapped address and returned FF). Reply = `7C` + `len`
data bytes. Captured **config EEPROM @0x1800 = `EE 01 E4 01 01 F8 0A 10 21 00 3B 0D 7D A2 DD 00`**
(this is the VIN/immo/security region — the clone/immobiliser payload) and **27C1001 @0x2000 =
`21 00 33 0D BC 20 DD 00 …`**. Gotcha: a reply >63 bytes uses ISO-14230's **2-byte length form**
(`00 41 7C …` = length 0x41 = the 7C + 64 data bytes), and BLE reassembly is unreliable for big
single reads → **dump in ≤16-byte chunks** (`GemsSecureSession.read_memory` caps len at 63 and
sends big-endian; `decode_secure` now handles both length forms). So the over-the-wire EEPROM +
27C1001 dump (coding, immobiliser, and the `$27` handler itself) is now reachable, chunk by chunk.

**⚠️ CORRECTION / OPEN (2026-09-08 later) — the flat-address model is NOT confirmed, and
multi-chunk dumps DRIFT.** Follow-up dumps exposed two problems: (1) a `--dump 1800:800` (128
back-to-back BLE reads) came back **corrupted** — the ~256-byte config block repeated ~8× with
progressive byte-shift, not a clean linear image; even the earlier `1800:80` (8 chunks) is now
suspect. (2) The addressing diagnostic **refutes flat linear addressing**: `--dump 180C:08` read
`80 60 80 00 60 60 00 00` **repeatably** (twice identical — so 0x180C is STABLE, killing the
earlier "volatile counter at 0x180C" guess, which was just dump drift), yet those bytes do NOT
match offset 0x0C of a `1800`-based read (`7D/E4 55 DD 00…`), and 0x180E–0F differs too
(`80 00` vs `DD 00`). So reading the same physical location via a different base address returns
different bytes ⇒ the two `0x3C` arg bytes are **not** a simple flat byte pointer (or reads
desync badly over BLE). **Only SINGLE reads are trustworthy right now** (they're self-consistent
and repeatable). Hardened `read_memory` to reject a short/overlong frame (→ None) and
and made short reads return None so they can't silently desync — but that doesn't
resolve the addressing question. **Overlap test RESULT (2026-09-08): flat addressing REFUTED.**
`1800:10` = `EE 01 E4 01 01 F8 0A 10 21 00 3B 0D F0 9E DD 00`; `1801:10` = `00 20 00 80 00 00 00
00 00 00 00 40 02 00 00 00` — NOT a one-byte shift, totally unrelated. So the two `0x3C` arg
bytes select a record/page, not a byte offset; consecutive "addresses" don't give overlapping
windows, and a linear `dump_memory` cannot build an image (which is why the 2 KB dump was
scrambled). **API changed to match reality:** `dump_memory` REMOVED; `read_memory(b1, b2, len)`
now takes the two raw arg bytes; `read_at(address, len)` is a big-endian-split convenience kept
only for probing (NOT a validated linear address). **What actually works reliably = the app's
CID reads** (`22 04 C4` VIN / `22 04 E2` PROM id / `22 04 BF` config / `22 23 xx` params →
`read_prom_id`/`read_config`/`read_vin_last6`); the real app never used `0x3C` at all. The
`0x3C` `<b1><b2>` indexing is still uncharacterized — a raw EEPROM/EPROM dump over the wire is
NOT currently possible, and we don't need the 27C1001 dump for `$27` anyway (algorithm already
cracked). Chasing `0x3C` indexing is optional/low-priority; chip-pull remains the route for a
full image if ever needed.

## ⭐⭐ 0x3C MEMORY-READ CONFIRMED on 0xDA, `$27`-gated (2026-09-08, `da5_mode3c.py`, K+L)
**A memory-read service exists on the 0xDA channel and is gated by `$27` — so a
cracked key gives an OVER-THE-WIRE dump of the EEPROM and the 27C1001.** Lead
from ecuconnections t=59049 (user *shickenchit*, 2021): "mode 0x3C over the obd2
port queries the intel memory; `3C LSB MSB LEN`; **0x1800 = start of the EEPROM,
0x2000 = start of the 1001**; not linear after a while; truncates at FFFF; `22 04
E2` returns it in correct order." Two probes settled where it lives:
- **On plain OBD (0x33), `mode3c_probe.py`: TOTAL SILENCE.** `0x3C` and `22 04 E2`
  got no reply at all (liveness fine — `01 00 -> 41 00 bf 9f f9 91`). The 0x33
  address processes ONLY OBD-II modes. shickenchit's bin was a '95 RR; our Disco 1
  doesn't expose 0x3C on OBD. Dead end on that channel.
- **On 0xDA (L-line tied, ISO-14230 no-addr framing), `da5_mode3c.py`: `0x3C` and
  `22 04 E2` both return checksum-valid `securityAccessDenied` (0x33)** — NOT
  silence, NOT serviceNotSupported. Seed flowed first (`04 67 01 b787 aa`, seed
  0xB787) confirming a live channel. Reply to every `0x3C` read (both byte orders,
  0x2000/0x1800/0x0000) was `03 7f 3c 33 f1`. **So 0x3C EXISTS on 0xDA and is
  `$27`-locked.** Byte order was irrelevant — the ECU denies on security before
  parsing the address, so 0x3C's real addr/length format is a post-unlock unknown.
- **Standard KWP `$23 ReadMemoryByAddress` = `serviceNotSupported` (0x11)** on
  0xDA — so this ECU's memory-read is the proprietary **0x3C**, not `$23`.
  shickenchit's 0x3C is confirmed as the right service, just on 0xDA not OBD.

**Why this matters / strategy shift:** every proprietary target — coding, VIN
last-6, the immobiliser/security code, AND the 27C1001 code image (the `$27`
handler + ignition maps at 0x2000) plus the config EEPROM at 0x1800 — sits behind
this one `$27` door, all reachable via `0x3C` reads once unlocked. So `$27`
seed→key is unambiguously the **single highest-value target**; it unlocks
*everything* on this ECU over the wire. **Honest caveat (no free bootstrap):**
reading 0x2000 over 0x3C needs the key, and deriving the key algorithm needs the
27C1001 — chicken-and-egg, so the EPROM still comes from a chip-pull/community
dump for the seed→key disassembly. BUT this makes a **real-tool seed→key capture
pay off double**: a captured key unlocks 0x3C → dump the EEPROM (immo/VIN/config/
clone data) and the whole EPROM with NO chip pull, ever. Probes: `~/mode3c_probe.py`
(OBD, silent) and `~/da5_mode3c.py` (0xDA, `$27`-gated). Both strictly read-only.

## Actuator / output-test channel — NOT on OBD (2026-09-08)
Confirmed the output/actuator tests (fuel-pump relay, O2 heater, MIL, A/C,
fans) are **not reachable on the OBD channel**. On the live 0x33 session, with
liveness proven that same run (`01 00 -> 41 00 bf 9f f9 91`), the KWP2000
output-control services were **silent**: `$30` (InputOutputControlByLocalId) and
`$31` (StartRoutine), sent non-actuating (subfunction/state 0x00) in the
`68 6A F1` envelope, both got no reply — not even `7F 30 11`. The 0x33 address
processes ONLY OBD-II modes; it ignores the `$30`/`$31` envelope entirely. So
actuators sit behind the proprietary **0xDA channel (L-line + `$27` security)**,
same locked door as coding/immobiliser — there is no OBD shortcut. Probe:
`~/actuator_probe.py` (uses `KlineClient.raw_service`; NON-ACTUATING by default —
state byte 0x00 only; a real drive is gated behind `ACTUATE=True` + a single
`DRIVE_FRAME`, off by default, because the real GEMS `$30` layout is unknown so
no state byte can be assumed harmless).

**$27 lockout strategy (for the upcoming 0xDA unlock — `~/da4_actuator_plan.md`).**
KWP `$27` locks (`0x36 exceedNumberOfAttempts`, ~3 tries) on wrong **KEY**
submissions, NOT on seed requests — and `0x37 requiredTimeDelayNotExpired`
enforces a wait between attempts. Seed discovery is SOLVED (`$27 01` now returns
real seeds in ISO-14230 no-addr framing — see the SEED-flowing section) and is
the SAFE zone: seed requests don't increment the counter. Rules baked into the plan: seed-only first; NEVER
brute-force keys (only submit a key computed from a known algorithm); hard
per-session attempt budget; abort on `0x36`/`0x37`; power-cycle + wait between
sessions; log every attempt. Diagnostic `$27` lockout is recoverable (power
cycle + delay); it is not the immobiliser PIN.

## NOT yet mapped (the frontier)
What's proven over the wire is only the **OBD-II emissions subset** (on 0x33). The
fuller **proprietary GEMS/T4 diagnostics** — the ~108 T4 live measures, actuator
drives, coding, VIN last-6, immobiliser — now have a KNOWN HOME and a KNOWN GATE:
they live on the **0xDA channel** (L-line tied, ISO-14230 no-addr framing) behind
**`$27` security**. Confirmed reachable-but-locked there: coding/data reads (`$21`/
`$22`), memory reads (`0x3C` at 0x1800 EEPROM / 0x2000 27C1001), and — by the same
`securityAccessDenied` pattern — the rest. The single remaining gate is the **`$27`
seed→key algorithm `f`** (seed flows; key is unknown; get it from a 27C1001
disassembly or a real-tool capture). Crack `$27` and effectively everything opens,
including an over-the-wire dump of the EEPROM + EPROM via `0x3C`. `KlineClient.raw_service`
(OBD envelope) and the `da*`/`mode3c` probes (0xDA no-addr framing) are the hooks.

## Two bring-up bugs found & fixed (both committed)
1. **Host serial timeout too short** (`transport/pico.py`): default was 2.0 s but
   the 5-baud slow init blocks ~2.3–3.3 s → every init raised "no response from
   Pico" on real HW. Bumped to **6.0 s**. (fake serial in tests hid it.)
2. **Missing ISO 9141 keybyte handshake** (`firmware/pico_kline/pico_kline.ino`
   `slowInit`): added the inverted-KB2 / W4 step (see above). This is what turned
   "init OK but all data times out" into working comms.

## How to run it (real ECU)
**CLI:** `gems_t4 kline live --port COM4` (one-shot table) / `kline dtc` /
`kline monitor` (continuous). Real-ECU only — no `--fake`; `--connect HOST` for
a TCP bridge. `KlineClient(transport)` for code.
**GUI (works on real hardware as of e51c549):** `gems_t4 gui --port COM4` drives
the Win98 kiosk from the REAL ECU. The Backend uses `KlineClient` when the
connection kind is **USB** (seam: `Backend._use_kline`, set by
`set_connection("usb")`; `Backend.on_real_ecu` property), mapping OBD live data
+ DTCs onto the shared `Measure`/`Dtc` types. The live-data screen discovers the
ECU's supported OBD PIDs and builds gauges from them (`gauge_specs.obd_spec_for`).
Proprietary screens (actuator/coding/immobiliser/security) raise
`RealEcuUnsupported` and refuse gracefully (OBD-II subset only). Virtual +
network (serve) keep the KWP-stylized stack.
Commits: firmware `fca1ab9`, timeout `640034f`, kline module+CLI `4bfa738`,
manual `6bd4ad5`, rename obd→kline `9f82b6b`, GUI real-ECU `e51c549`. Tests:
`tests/test_kline.py` (decoders vs captured bytes), `tests/test_backend_kline.py`
+ `tests/test_gui_real_ecu.py` (backend/GUI real-ECU paths).

## Wireless/web forward note (from the same session)
Architecture is already latency-safe: all K-line timing is on the Pico, host↔Pico
is request/response tolerating any latency (the W4 fix PROVES the principle). The
one wireless item is **session keep-alive** — the ECU drops the session if idle
too long (KWP TesterPresent timeout ~1–5 s); over WiFi/web with idle gaps it'll
drop → do keep-alive **in firmware** (Pico auto-sends TesterPresent), same
timing-on-the-Pico principle. Live-data over WiFi: batch multiple PIDs per Pico
command to amortize RTT (UX, not correctness). Not built yet.

Related: [[implementation-status]], [[repo-git-state]], [[pico-board-support]],
[[gems-p38-focus]].
