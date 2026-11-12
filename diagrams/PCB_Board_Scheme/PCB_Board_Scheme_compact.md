# Board 1 — Schematic Capture Spec (compact)

> **Do not fetch, open, or re-verify any manufacturer datasheet unless the
> current chunk request explicitly asks you to.** This file is a reference
> spec, sent in stages (a "Chunk 0–5" process). It lists three states per
> item: **FINALIZED** (never re-derive), **NOT YET VETTED** (a real, known
> gap — do NOT investigate, validate, or resolve it until a future chunk
> request specifically names it), and open items for whichever chunk you've
> been asked to do right now. If this file is sent to you without an
> accompanying chunk instruction, treat it as read-only context and wait for
> the actual request before doing any work — do not proactively start
> validating "NOT YET VETTED" items on your own initiative.

> **✅ STATUS (2026-09-30): SCHEMATIC + PCB LAYOUT + ROUTING + MANUFACTURING
> EXPORTS ARE ALL COMPLETE.** This jumped ahead of the Chunk 6/6.1/6.2 plan
> below — the user drove PCB layout directly with flux rather than through
> individually tracked chunks, so this doc is reconciling after the fact
> against flux's own consolidated findings (its stated authority: "when an
> older chunk file conflicts with this file, this file and the live project
> state take precedence"). Board: 110mm × 70mm, 4-layer, all 40 components
> top-side, fully routed (0 airwires, 0 redundant traces), 4× M3 mounting
> holes, antenna keepout applied, Gerbers/drill/JLCPCB BOM+CPL/STEP
> generated and structurally validated. **D3 no longer exists** — it was
> removed along with Q1/R3 as part of the whole MOSFET-stage-to-SS36
> simplification (D3 was only ever Q1's gate protection; no Q1, no D3
> needed). The old "D3 automotive-qualification caveat" is stale, ignore
> it. **What's left is order-time work, not design work** — see the
> "Remaining work" entry in the progress log below.

- **Chunk 0** — power design paper review. ✅ Done and confirmed (REG1/Q1/D3
  decisions below).
- **Chunk 0.1** — power budget + support-circuit MPNs. ✅ Done and confirmed
  (L1/C3/C5/C6 locked; F1/C4/R4/R5/D3-exact-part still open).
- **Chunk 1** — place/wire the power section (F1, D1, Q1, R3, D3, REG1 +
  support circuit) and run ERC. **✅ Done and confirmed** — a written
  findings record exists (not just a chat summary): exactly the 13 scoped
  components were placed, the 9 specified nets were created and verified
  (`12V_IN`, `VS_FUSED`, `Q1_GATE`, `VIN_PROT`, `REG1_SW`, `REG1_BOOT`,
  `VOUT_5V`, `REG1_FB`, `GND`), C6 confirmed CB-to-SW not GND, EN confirmed
  tied to `VIN_PROT`, and ERC returned exactly the one expected finding
  (`12V_IN` single-pin net — correct, since J1 is out of scope) with 0
  warnings and nothing else. U1/U2/U3/J1/D2/VSYS were correctly left
  untouched. Do not redo this chunk.
- **Chunk 2** — place/wire U1 (Pico 2 W), U2/U3 (L9637D transceivers), R1/R2,
  C1/C2. **✅ Done and confirmed** — written findings record exists: exactly
  7 components added (project total 20), all specified nets created/extended
  correctly (K1/K1_TX/K1_RX/K1_LO/LI1, K2/K2_TX/K2_RX/K2_LO/LI2, P3V3, and
  `VS_FUSED`/`GND` correctly extended to the new parts). ERC returned 6
  errors, 0 warnings — **all 6 are expected staged-capture artifacts, not
  bugs**: `12V_IN` and `LI1`/`LI2` single-pin (J1 still deferred), `U1:VBUS`
  unconnected (intentionally NC), and `U2:VS`/`U3:VS` "not driven" on
  `VS_FUSED` (expected — `VS_FUSED` traces back to `12V_IN`, which has no
  real source until J1 is placed). U1 VBUS/VSYS correctly marked no-connect
  for now. J1 and D2/VSYS correctly left untouched. Do not redo this chunk.
- **Chunk 3** — place/wire J1 (terminal block) into the Chunk 1/2 nets.
  **✅ Done and confirmed** — written findings record exists, explicitly
  "independently verified" with a timestamped ERC rerun
  (2026-09-29T18:30:41Z). All 9 terminal-to-net mappings inspected live and
  match the locked spec exactly. ERC returned 3 errors, 0 warnings — the
  three previously-carried single-pin findings (`12V_IN`, `LI1`, `LI2`) all
  cleared as expected; the remaining 3 (U1:VBUS NC, U2:VS/U3:VS "not
  driven") are the same expected carried-over findings from Chunk 2, nothing
  new introduced. U1/U2/U3/D2/VSYS correctly left untouched; no actual
  J1962 connector was placed. Do not redo this chunk. **New item surfaced:**
  J1's current library symbol (Phoenix Contact `1844281`) is explicitly
  marked placeholder-only, excluded from BOM/PCB, not an approved production
  part — J1 needs its own exact-MPN resolution before layout, same as the
  other still-open parts (added to Chunk 4.1 below).
- **Chunk 4** — place/wire D2 and the final VSYS connection to U1. **✅ Done
  and confirmed** — written findings record exists, timestamped ERC rerun
  (2026-09-29T18:37:32Z). D2 placed as **ON Semiconductor 1N5817RLG** (DO-15
  through-hole) — note: the bare "1N5817" base MPN wasn't an exact library
  hit, this suffix variant is the library's active implementation; final
  acceptance deferred to Chunk 4.1. Wiring verified live: `VOUT_5V` →
  D2 anode, D2 cathode → `VSYS_5V` → U1 VSYS (pin 39); U1 VBUS (pin 40)
  confirmed still no-connect. This completes the full intended power chain
  end-to-end: J1 12V → F1/protection → REG1 → D2 → U1 VSYS.
  **Important, permanent finding — not a bug, don't try to "fix" it later:**
  ERC still shows `U2:VS`/`U3:VS` "not driven" on `VS_FUSED`, and per
  flux's own explanation **this will never clear through wiring alone** —
  ERC's engine doesn't recognize passive connector/fuse pins (J1, F1) as a
  formal power-output driver, regardless of actual end-to-end connectivity.
  Flux correctly declined to add an artificial power-flag/fix just to
  silence this. Clearing it (if ever wanted) would need an explicit
  power-flag symbol added deliberately — that's a Chunk 5 decision, not
  something to chase now. Along with `U1:VBUS` NC (intentional), **these are
  now the permanent, expected ERC baseline for this design** — a "fully
  clean 0-error ERC" is not the actual target state; "3 known, explained
  findings" is.
- **Chunk 4.1** — lock all remaining exact MPNs. **✅ Done and confirmed** —
  written findings record exists. Every part now has a final MPN decision:
  **F1** Littelfuse 0459001.UR (1A/125V, 50A interrupt, SMD — 29.8% margin
  at worst-case load); **C4** KEMET C0603C104K5RACAUTO (100nF/50V/0603 —
  clears the ~33.2V VIN_PROT worst case with margin); **R4** Yageo
  AC0603FR-07118KL (118kΩ, automotive, LCSC C227557); **R5** Yageo
  AC0603FR-0722K1L (22.1kΩ, automotive, LCSC C227715); **R1/R2** Vishay
  CRCW2512510RFKEG (510Ω/1%/1W/**2512** — 0603 explicitly rejected per the
  locked constraint); **C1/C2** same part as C4 (KEMET
  C0603C104K5RACAUTO — reduces BOM part diversity); **D3** Nexperia
  BZT52H-C12-QX (automotive, MPN locked in component properties — but see
  library gap below); **J1** Phoenix Contact 1715815 "MKDS 1,5/9-5,08"
  (9-position, 5.08mm pitch THT, 17.5A, straight entry — replaces the old
  1844281 placeholder MPN); **D2** 1N5817RLG **final acceptance confirmed**
  (DO-41 THT retained over SMD — rating/forward-drop/library-availability/
  hand-assembly all favor keeping it).
  **Residual gaps carried forward (footprint/library binding, NOT open MPN
  decisions):** D3's exact library-backed part/footprint still needs
  importing — the schematic still shows the old placeholder symbol with
  correct 2-terminal connectivity but wrong physical part. J1's schematic
  object still originated from the old 1844281 symbol — its footprint needs
  replacing/verifying against the 1715815 mechanical drawing. F1's
  placeholder object lacks the 0459001.UR footprint geometry. These three
  join Q1 and D1 (already-known footprint gaps) as pure footprint/library
  work for Chunk 5 — not electrical-selection questions any more.
  **⚠️ Gap found in Chunk 4.2: R3 was never given an exact MPN in this
  chunk** — only its 10kΩ value was ever locked (from the original design),
  unlike R1/R2/R4/R5 which all got real orderable parts. This was a miss in
  scoping Chunk 4.1, not something Chunk 4.1 deliberately deferred. Needs
  its own exact-MPN decision before Chunk 5/ordering — see open items.
- **Chunk 4.2** — check every locked MPN against JLCPCB's assembly-sourcing
  library (JLCPCB/LCSC), report cost/MOQ at a 5-board build quantity.
  **✅ Done and confirmed** — written findings record exists (live
  enrichment 2026-09-29; prices/stock are snapshots, must be refreshed
  before ordering). **Full results in the new "JLCPCB sourcing status"
  section below** — summary:
  - **Mandatory gate PASSES**: U2/U3 (ST E-L9637D013TR) confirmed at LCSC
    C153038, Extended tier, 3,010 in stock, ~$1.68/unit (~$16.83 for 10
    units/5 boards).
  - **Full turnkey does NOT clear.** 4 parts have no live JLCPCB/LCSC
    listing at all: **R1/R2, D3, Q1, J1**. 4 more have a catalog entry but
    zero confirmed live stock at review time: **F1, D1, D2, C3**.
  - Known sourceable-line cost is **~$87 for 5 boards** (dominated by U1,
    U2/U3, REG1, L1) — explicitly a partial subtotal, excludes every
    blocked/out-of-stock line, PCB fab, assembly labor, shipping, tax, and
    Extended-part setup fees. Not a real quote.
  - Recommended build path per the findings: JLCPCB assembly for every
    confirmed-stocked part, customer-consigned or hand-soldered for the
    blocked ones (R1/R2, D3, Q1, J1, and whichever of F1/D1/D2/C3 remain
    unstocked by order time) — this is a **decision for Chunk 4.3/5**, not
    resolved yet.
- **Interim Claude review (between Chunk 4.2 and Chunk 4.3, not a numbered
  chunk — renamed to avoid colliding with flux's own "Chunk 4.3" below).**
  **✅ Done** — Claude personally cross-checked every findings file (Chunks
  0–4.2) against this spec: every net's live-verified membership matches the
  documented net list exactly, ERC results are all correctly explained, and
  the project component count reconciles precisely (13+7+1+1 = 22, matching
  the BOM row count). **One real gap found**: D1 was never given an exact
  manufacturer MPN, the same category of miss as R3 — of all 22 BOM refs,
  these were the only two still at "spec/value locked, no real part number."
  Fed directly into the Chunk 4.3 request below. No other inconsistencies,
  fabricated facts, or unfollowed-up flags found.
- **Chunk 4.3 — Final R3 and D1 MPN closure.** **✅ Done and confirmed** —
  written findings record exists. **R3**: Yageo AC0603FR-0710KL (10kΩ, 1%,
  0603, automotive-series) — LCSC C116677, Extended, 3.3M+ in stock,
  ~$0.03 for 5 boards. **D1**: Micro Commercial Components 1.5KE24A-TP
  (axial DO-201AE/DO-201) — exactly matches the locked VRWM 20.5V/VBR
  22.8–25.2V/VC(max) 33.2V; LCSC C1975979, Extended, but **live stock/price
  not confirmed at review time — treat as cataloged, not yet proven
  in-stock** (same category as F1/D2/C3's sourcing status). **All 22 BOM
  components now have a real, exact manufacturer MPN — zero electrical-
  selection gaps remain.** Only footprint/library-binding work (F1, D3, J1,
  Q1, D1) and the turnkey-blocker build-path decision are left before
  Chunk 5.
- **Chunk 4.4 — NOT a flux task.** **✅ Done** — Claude confirmed the Chunk
  4.3 R3/D1 closure is consistent everywhere: BOM rows, FINALIZED/NOT-YET-
  VETTED sections, the JLCPCB sourcing table, and the known-sourceable-line
  subtotal (bumped from $86.99 to ~$87.02 to include R3's now-confirmed
  $0.03; D1 correctly stays excluded, stock unconfirmed). No other drift
  found. Clean.
- **Chunk 4.5** — paper-only check: does C5 hold enough effective
  capacitance under real DC bias for REG1's needs? **✅ Done — C5 alone
  FAILS.** TI's LMR51610-Q1 design example requires **20µF minimum**
  effective output capacitance. C5 (22µF nominal, −10% tolerance) is only
  **19.8µF worst-case before any DC-bias loss** — already 0.2µF short.
  Factoring in Samsung's real DC-bias characteristic (~−17 to −19% at 5V for
  this 22µF/16V/X7R/1210 construction), effective capacitance drops to
  **~16.0–16.4µF, an 18–20% shortfall**. **Approved fix: add a second
  identical Samsung CL32B226KOJVPNE in parallel on VOUT_5V** — two in
  parallel give ~32µF effective even at the conservative bias estimate, a
  60% margin above the 20µF requirement. New BOM line **C7** (see BOM/net
  list). Flux correctly did not add this itself (paper-only scope) —
  approval given 2026-09-29, now reflected in this spec.
- **J1 terminal silkscreen labels** — a labeling decision (not one of the
  numbered chunks, done alongside 4.5): `K1-A / K1-B / LI1-IN / K2-A / K2-B
  / LI2-IN / +12V / GND / GND`, in that physical order, matching our
  A1/A2/A3/B1/B2/B3/12V/GND/GND terminal order exactly (position-for-
  position verified). Human-readable labels layered on top of our internal
  reference scheme, not a renaming of it — see the Terminal block section.
  **⚠️ SUPERSEDED during PCB layout (2026-09-30)**: the LI labels changed to
  `LI1-MON`/`LI2-MON` and the "DO NOT DRIVE" warning was dropped — see the
  PCB layout phase entry and the Terminal Block section for the final
  version.
- **Chunk 5** — footprints for every part, test points, full-sheet
  reconciliation, final ERC. **✅ Done — but PCB layout is explicitly NOT
  yet approved.** Written findings record exists. Results:
  - **C7 added successfully** (parallel with C5 on `VOUT_5V`/`GND`), ERC
    clean, no new findings.
  - **Footprint reconciliation: F1 and D1 fully bound** to real
    library-backed footprints (F1: `FUSE-SMD_L7.3-W4.3`; D1:
    `DO-201AE_BD5.3-L9.5-P13.50-D1.0-FD`). **D3, J1, and Q1 remain
    BLOCKED** — no authoritative library-backed footprint was available for
    any of the three exact locked MPNs (Nexperia BZT52H-C12-QX SOD-123F;
    Phoenix Contact 1715815 THT; Nexperia BUK6M61-60P LFPAK33/SOT1210).
    Flux correctly refused to substitute a similar-but-wrong package for any
    of them (rejected a C15 Zener variant for D3, rejected the LFPAK56
    `BUK6Y61-60PX` for Q1). **These 3 are now the explicit PCB-layout
    gate.**
  - **17 test points added** (TP7–TP23 — Pico's own module reserves
    TP1–TP6 internally), one per requested net: `12V_IN`, `VS_FUSED`,
    `VIN_PROT`, `VOUT_5V`, `VSYS_5V`, `P3V3`, `K1`, `K2`, `LI1`, `LI2`, and
    both channels' TX/RX/LO signals, plus `GND`.
  - **ERC baseline**: 3 errors (the accepted permanent baseline — `U1:VBUS`
    NC, `U2:VS`/`U3:VS` not driven) **+ 1 new warning**: D1's exact library
    part has incomplete pin-role metadata (pins 1/2 "unspecified terminal
    type/role/name") — a library-quality warning, not an electrical
    connectivity error. No power-flag symbol was added; the 3-error
    baseline decision stands as originally planned.
  - **Full-sheet reconciliation passed** — every net/chain verified
    end-to-end (J1→F1→protection→REG1→D2→U1 VSYS; both L9637D channels;
    all 9 J1 terminal mappings; the silkscreen label decision). Project
    now has **40 components, 21 nets**.
  - **Layout gate at end of Chunk 5 proper**: blocked on D3/J1/Q1 — see
    the three amendments immediately below, which resolved all three.
- **Chunk 5 Amendment 1 — J1 blocker resolved.** ✅ Done. The single
  9-position Phoenix Contact 1715815 (unavailable) was replaced by **three
  separate 3-position Phoenix Contact 1715734** connectors (J1, J2, J3) —
  real, library-backed, in stock. New mapping: **J1** pins 1/2/3 = `K1`,
  `K1`, `LI1` (labels K1-A/K1-B/LI1-IN); **J2** pins 1/2/3 = `K2`, `K2`,
  `LI2` (labels K2-A/K2-B/LI2-IN); **J3** pins 1/2/3 = `12V_IN`, `GND`,
  `GND` (labels +12V/GND/GND). Electrical behavior unchanged — A/B K-line
  pins still bonded duplicates, LI still separate input-only. Project now
  42 components (was 40). ERC unchanged (3 errors, 1 warning).
- **Chunk 5 Amendment 2 — Q1 footprint blocker resolved.** ✅ Done. Rather
  than substitute a wrong package, flux built a **custom exact footprint
  from scratch**: read Nexperia's official BUK6M61-60P datasheet and
  SOT1210 package-outline PDFs directly, cross-checked the copper geometry
  against KiCad's public LFPAK33 footprint source, and created/published a
  corrected library part. Q1 stays the original automotive-grade part — no
  grade relaxation needed here, the blocker was purely a missing footprint
  which is now solved properly. Gate/Source/Drain connectivity to
  `Q1_GATE`/`VS_FUSED`/`VIN_PROT` preserved exactly (all 3 physical source
  leads connected). ERC unchanged (3 errors, 1 warning).
- **Chunk 5 Amendment 3 — D3 footprint blocker resolved.** ✅ Done, with
  a caveat. Switched to the **non-automotive sibling `BZT52H-C12,115`**
  (real footprint, in BOM/PCB/pick-and-place) since the automotive `-QX`
  ordering code has no footprint-backed library part anywhere. **This
  aligns with the scope-change decision above** (automotive grade dropped
  for this 5-unit bench build). ⚠️ **Caveat explicitly on record**: if
  AEC-Q101 automotive qualification is ever required, D3 needs revisiting
  — the `,115` part is not claimed to carry the same qualification.
  Cathode(K)→`VS_FUSED`, anode(A)→`Q1_GATE`, matching the locked polarity.
  ERC unchanged (3 errors, 1 warning). **All three footprint blockers are
  now closed — PCB layout may proceed for prototyping.**
- **Chunk 5.1** — JLCPCB sourcing cleanup pass. **✅ Done.** Written
  findings record exists (2026-09-30). Results:
  - **J1/J2/J3 (Phoenix Contact 1715734)**: ✅ cleared. LCSC C480520,
    2,436 in stock, ~$11.12 for all 15 pieces (5 boards × 3). Retain.
  - **D3 (Nexperia BZT52H-C12,115)**: ✅ cleared. LCSC C282531, 37,620 in
    stock, ~$0.21 for 5 boards. Retain.
  - **R1/R2 (Vishay CRCW2512510RFKEG)**: ✅ cleared — the earlier "not
    found live" was a search/indexing gap, not a real shortage. LCSC
    C2125401, ~$0.32 for 10 pieces. Retain, no change needed.
  - **Q1 — ✅ DECISION MADE (2026-09-30): replace the whole Q1/D3/R3
    reverse-polarity stage with a single series Schottky diode, SS36
    (3A/60V).** Both my independent suggestion and flux's own follow-up
    review converged on this same fix. Reasoning: Q1 (BUK6M61-60P) has no
    confirmed authorized-distributor stock, and the whole MOSFET
    ideal-diode topology is more complexity than a 5-unit hobby board
    needs. SS36 gives comfortable margin (D1 clamps transients to ~30V max,
    SS36 rated 60V) with a harmless ~0.3-0.5V forward drop (~0.09-0.15W)
    at this board's ~0.3A load — same category of part as D2, already
    proven easy to source. **Reverse-polarity protection is being kept, not
    dropped — just simplified.** ⚠️ **Not yet applied to the schematic** —
    this is a recorded decision, the actual removal/addition still needs
    doing (see the new chunk below).
  - **C3 — ⚠️ APPROVED BY USER, but NOT YET APPLIED to the live flux
    schematic.** Confirmed by flux's own consolidated findings
    (2026-09-30): "C3 substitution has NOT been applied to the schematic."
    Your approval only recorded the decision here — it still needs an
    actual chunk sent to flux to make the edit. **Do this before/alongside
    Chunk 6** so layout works from the real final BOM. Recommended swap
    from KEMET C1210X225K1RACAUTO (zero LCSC stock) to **SAMWHA CS3225X7R225K101NRK**
    (LCSC C2900749, 11,565 in stock, ~$0.60 for 5 boards) — same
    2.2µF/100V/X7R/1210 spec/package. See BOM.
  - **F1, D1, L1, C1/C2/C4/C6, C5/C7**: all reviewed, no change
    recommended — already adequately priced/stocked as-is.
  - No parts were silently substituted beyond the approved C3 swap.
- **Chunk 5.2** — apply the approved Q1/D3/R3 → SS36 simplification AND a
  visual drafting/legibility pass. **✅ Part 1 done; Part 2 blocked by a
  tool limitation (not skipped — genuinely unavailable).** Written findings
  record exists (commit `b719cf98`, ERC rerun 2026-09-30T01:15:58Z).
  - **Circuit change — DONE.** Q1 (BUK6M61-60P), R3 (10kΩ), D3
    (BZT52H-C12,115), and the `Q1_GATE` net are all removed. Added **D4 —
    Vishay SS36-E3/9AT** (3A/60V Schottky, footprint `FP_DIOM7959X262N`):
    anode on `VS_FUSED`, cathode on `VIN_PROT`. Net memberships
    independently verified. F1/D1 unchanged. ERC: 3 errors, 1 warning —
    unchanged from the pre-change baseline (no new D4 or deleted-net
    findings; the accepted `U1:VBUS`/`U2:VS`/`U3:VS` findings plus the D1
    metadata warning). Project component count drops by 2 (Q1+R3+D3 out,
    D4 in = net −2).
  - **Drafting/legibility pass — BLOCKED, not done.** This execution
    environment (the automated chunk-runner) doesn't have a working
    schematic-placement/wire-drawing/block-title mutation capability —
    flux reported this honestly rather than faking a "done." Functional-
    group *metadata* was updated (5 named blocks exist as data), but the
    actual visual layout is unchanged: symbols remain scattered, D4 sits
    far from the main drawing area, no left-to-right flow/aligned rails/
    short local wires/block titles were drawn. **The sheet is electrically
    complete and correct but still not visually professional** — this
    would need the interactive flux.ai web UI (not this chunk-runner) to
    actually redraw, if it's ever wanted. Not a layout blocker — PCB
    prototyping may proceed on the electrical data regardless.

### PCB layout phase (Chunk 6+) — completed 2026-09-30 outside the tracked chunk sequence

The user drove this directly with flux rather than via the Chunk 6/6.1/6.2
prompts originally planned (never sent). Reconciled here from flux's own
consolidated findings file, which explicitly supersedes any older chunk
file it conflicts with.

- **C3 KEMET→SAMWHA swap** — ✅ applied (confirmed in flux's BOM: C3 is now
  SAMWHA `CS3225X7R225K101NRK`).
- **Board outline + component placement** — ✅ done. 110mm × 70mm
  rectangle, 4-layer stackup (~1.55mm total, 1oz copper), all 40 components
  on the top side. J1/J2/J3 aligned along the top board edge. **U1 (Pico
  2 W) is direct-soldered, not socketed** — the earlier female-socket plan
  was abandoned (the mixed SMD/THT library footprint didn't provide valid
  drilled header pads); U1 is excluded from BOM/pick-and-place as a result
  (it's a manual hand-solder step). Pico orientation/location is
  user-approved and frozen — **no component may be moved/rotated without
  explicit approval**, per flux's own stated rule.
- **Antenna keepout** — ✅ applied. 0.5mm all-layer copper clearance
  beneath and around the Pico's antenna region (in addition to the
  antenna's own 14×9mm footprint itself — see the antenna-keepout research
  from earlier). One placement finding flagged U1 against its own antenna
  keepout — accepted as a self-reporting artifact, not a real issue.
- **Routing + DRC** — ✅ done. 0 airwires, 0 redundant traces, 264 route
  segments, 53 vias + 17 smart vias, one copper fill, one keepout zone.
  `VS_FUSED` and `K1_RX` were specifically rebuilt during routing
  convergence. DRC returned no routing/copper errors or warnings. Minimum
  copper spacing 0.127mm (0.15mm preferred), minimum trace width 0.15mm,
  default through-via 0.55mm pad/0.25mm drill. 4× 3.2mm NPTH M3 mounting
  holes, ~100mm × 60mm hole pattern.
- **Silkscreen finalized, with one label change from what was originally
  planned**: LI labels are now **`LI1-MON`/`LI2-MON`** (not `LI1-IN`/
  `LI2-IN`), and the **"DO NOT DRIVE" warning was dropped** — flux's
  reasoning: "the terminals accept external vehicle diagnostic signals;
  the actual limitation is that the Pico cannot transmit through the
  L9637D LI pins," which is a more accurate framing than the old wording.
  See the Terminal Block section below for the updated labels/layout.
- **Manufacturing exports** — ✅ generated and structurally validated:
  Gerbers, drill files, corrected JLCPCB assembly BOM + CPL (component
  placement list), and STEP files. **Remaining before ordering**: your own
  visual review in the board-house Gerber viewer, plus an order-time stock/
  rotation refresh (see "Remaining work" below).

---

## What this board is

Board 1 is a dual-channel K-line (ISO 9141-2/KWP2000) automotive diagnostic
adapter. A Raspberry Pi Pico 2 W (host MCU) drives two independent K-line
transceivers (ST L9637D), each talking to a separate diagnostic bus on a
vehicle — e.g. the engine ECU on one channel and a body/alarm module on the
other, simultaneously, without contention. The board runs from the vehicle's
12V battery rail with USB as an alternate/simultaneous power source, and
includes automotive input protection (fuse, TVS clamp, reverse-polarity
stage) ahead of a buck regulator that supplies the Pico.

**J1/J2/J3 are three 3-position screw-terminal blocks mounted on THIS
board — not an OBD-II/J1962 connector.** (Originally one 9-position block;
split into three in Chunk 5 Amendment 1 when the single 9-position part
turned out unavailable — see the Terminal blocks section.) The male J1962
plug is a separate pigtail cable, wired by hand into these terminals after
the PCB is built; it is not part of this board's BOM as an actual
connector, and flux should never source, place, or footprint an actual
J1962 plug for this design. The "OBD pin" numbers used throughout this
spec (pin 4, 7, 15, etc.) exist only to document which external pigtail
wire lands on which terminal — they don't imply an on-board connector.

**PCB layout may now proceed** (schematic capture is complete, all
footprint blockers resolved as of Chunk 5's amendments) — this doc remains
the schematic-level reference; no placement/routing/layer detail is
captured here.

**Net naming key**: K1/K2 = the two K-line buses (one per transceiver). LI1/LI2
= each transceiver's read-only L-line listen input. GP0–GP6 = Pico GPIO pins.

## ✅ Design decisions already finalized — treat as fixed requirements, do not re-derive or re-verify

Everything below is a settled requirement from independent electrical review,
not an open question for this pass. Capture these values as given and spend
your effort on the "STILL OPEN" items instead — re-deriving anything in this
section is wasted work covering ground already checked.

- **REG1 part + topology**: LMR51610XQDBVRQ1 is the correct orderable part.
  It is **adjustable, not fixed-5V** — this is confirmed, not an open
  question. The full support circuit (R4/R5 divider, L1, C3/C4/C5/C6, EN
  tied to VIN) is specified below at final values — do not re-derive from
  the datasheet.
- **Q1 part**: Nexperia BUK6M61-60P. Already checked against automotive
  qualification (AEC-Q101), voltage rating, and RDS(on)/conduction loss at
  this rail's current. Do not re-evaluate alternatives.
- **D3 gate-protection Zener, requirement + value**: 12V, required because
  D1's 33.2V clamp would otherwise exceed Q1's ±20V gate rating. This
  requirement is settled — just place it as specified.
- **D1 TVS clamp voltage**: VC(max) = 33.2V (10/1000µs), full VRWM/VBR/VC
  chain already established. Do not re-look-up or re-question this number.
- **R1/R2 power rating + exact MPN**: 1W, dissipation math already done and
  reconfirmed with tolerance (0.297W/0.428W at 12V/14.4V including −5%
  resistance tolerance — 42.8% of rating at worst case). Do not recompute.
  **LOCKED in Chunk 4.1: Vishay CRCW2512510RFKEG, 2512 package** — the "no
  0603" constraint (standard 0603 resistors are rated ~0.1–0.125W max, far
  below the 0.428W this design requires) was satisfied by this pick. Do not
  re-select.
- **GP0/GP1/GP2/GP4/GP5/GP6 K-line pin allocation must be preserved exactly
  as specified when wiring**, and is **not an ERC defect**: ERC checks
  connectivity (unconnected pins, driver conflicts), not whether a given
  GPIO's alternate function genuinely supports UART — that's a separate
  datasheet/pinmux question outside ERC's scope, and out of scope for
  schematic capture entirely. Do not flag it as an ERC finding, do not
  change the mapping, and do not attempt to resolve it during capture.
  (Whether the mapping is *itself correct* is a different, still-open
  question — see NOT YET VETTED.)
- **F1/REG1/Q1 worst-case current budget**: computed. F1 sustained current
  298.2mA@12V / 266.7mA@14.4V (29.8%/26.7% of the 1A rating). REG1 loaded to
  50% of its 1A rating at the provisional 0.5A Pico draw. Do not recompute
  unless the load assumptions change.
- **Every part's exact MPN is now LOCKED, and every footprint is now
  BOUND** — see BOM. As of the Chunk 5 amendments (2026-09-30), F1, D1,
  D3, J1 (now J1/J2/J3), and Q1 are all footprint-bound and closed out.
  **PCB layout may proceed.** D3 switched to its non-automotive sibling
  (BZT52H-C12,115 — flag if AEC-Q101 is ever required); Q1 got a
  custom-built footprint on the original automotive part; J1 became three
  separate connectors (J1/J2/J3). None of these are open "pick a different
  part" questions any more.
- **Datasheet citation traceability**: the manufacturer datasheets for
  REG1/Q1 have been reviewed and the values below are datasheet-derived.
  Formal inline citation linking is not required for this pass — defer it to
  final BOM lock if your process needs it; it is not a blocker here.

## ⚠️ NOT YET VETTED — real gaps, do NOT investigate until a chunk request names them

These items were never actually resolved by review, despite earlier drafts
of this doc implying otherwise. **Do not start working on these unless a
specific chunk request tells you to** — they're listed for accurate status,
not as a to-do list. Grouped by what kind of gap each one actually is:

**Tier 1 — mechanical footprint/library binding — ALL 5 NOW RESOLVED (as
of the Chunk 5 amendments, 2026-09-30):**
- **F1 and D1** — bound to real library footprints in Chunk 5 proper
  (`FUSE-SMD_L7.3-W4.3` / `DO-201AE_BD5.3-L9.5-P13.50-D1.0-FD`). D1 also has
  a library-metadata ERC warning (pins 1/2 unspecified role/name — not
  electrical) and still-unconfirmed JLCPCB stock.
- **J1** — split into three separate 3-position Phoenix Contact 1715734
  connectors (J1/J2/J3), real footprints, since the single 9-position part
  had none available (Amendment 1).
- **Q1** — a custom exact footprint was built from Nexperia's official
  datasheet + package PDFs, cross-checked against KiCad's public LFPAK33
  footprint source, rather than substituting a wrong package (Amendment 2).
- **D3** — switched to the non-automotive sibling BZT52H-C12,115, which
  has a real footprint (Amendment 3) — ⚠️ not automotive-qualified, revisit
  if AEC-Q101 is ever required.
- **PCB layout may now proceed.** JLCPCB sourcing for the newly-changed
  J1/J2/J3, Q1, and D3 parts hasn't been re-checked yet — see the sourcing
  table.

**Tier 2 — real open engineering questions, need an actual decision (not
just Chunk 5 busywork):**
- **C5 effective capacitance under DC bias**: the exact part (Samsung
  CL32B226KOJVPNE) is selected at its 22µF nominal rating, but its real
  effective capacitance at 5V across bias/tolerance/temperature was never
  checked. If it falls short of what REG1 needs, a second parallel output
  cap may be required — flag, don't add one speculatively.
- **Terminal-block/connector topology** (the J1/J2/J3 three-connector
  layout, the A1/A2-equivalent K+L tie, the LI listen-taps): this is an
  internal design decision that has never been through any outside
  electrical review — unlike the power section, nobody has checked this
  for correctness or safety. (Separate from the footprint-binding work,
  which is now done — see Tier 1 above.)

**Tier 3 — deferred to hardware bring-up or layout, not actionable right
now (nothing to do until then):**
- **C3 citation**: the exact part (KEMET C1210X225K1RACAUTO) is selected,
  but formal citation evidence for it was still indexing when last checked —
  re-verify before final BOM lock, not a reason to re-select the part now.
- **R1/R2 ambient-temperature derating sign-off**: the exact MPN (Vishay
  CRCW2512510RFKEG) and package are locked — what's left is the final
  thermal derating-curve sign-off, which can't happen until real PCB copper/
  layout exists (same for REG1's thermal sign-off, tracked below).
- **GP0/GP1/GP2/GP4/GP5/GP6 K-line pin allocation on the Pico**: whether
  this mapping is *actually correct* (confirmed against machine-verifiable
  Pico alternate-function documentation) is still open — deferred to
  firmware bring-up. (That it must be preserved as-is and isn't an ERC
  defect is settled — see FINALIZED above.)

## ⏳ Remaining work (as of 2026-09-30 — schematic + layout + routing + manufacturing exports all done)

Everything design-related is finished. What's left is **order-time
procurement work**, not engineering:

- **Your visual review in the board-house Gerber viewer** — the manufacturing
  package (Gerbers, drill, JLCPCB BOM+CPL, STEP) is generated and
  structurally validated, but hasn't had a human look at the rendered
  preview yet. Do this before actually placing the order.
- **Refresh stock/price immediately before ordering** for anything
  time-sensitive: REG1 (only 32 in stock at last check — highest risk),
  F1 (79 in stock), L1 (97 in stock), C3 (Extended tier), and every other
  Extended-classified line. All prior stock numbers in this doc are
  snapshots, not live.
- **R1/R2 sourcing decision** — the exact Vishay CRCW2512510RFKEG is out of
  LCSC stock. Two candidates surfaced but neither applied yet:
  `CR2512F510RE04Z` (LCSC C146930, only 10 shown — use only if ≥12
  available) or `CRCW2512510RFKEGHP` (LCSC C1710525, AEC-Q200, 1.5W, higher
  rating — currently zero stock). **Do not go below 1W for R1/R2** — worst-
  case dissipation is ~0.428W each. If neither pans out, manual-install
  externally-sourced parts.
- **Optional, not yet applied**: swap C1/C2/C4/C6 (currently KEMET
  C0603C104K5RACAUTO) to Samsung `CL10B104KB8NNNC` (LCSC C1591) — a
  validated drop-in 100nF/50V/X7R/0603 equivalent with very high stock.
  Pure cost/availability upside if you want it; current parts work fine.
- **Firmware**: confirm the Pico UART/PIO peripheral assignments for
  GP0/1/2 and GP4/5/6 during bring-up (electrically captured, never
  verified against Pico alternate-function docs — same open item as
  always). Prepare a firmware pin-map/init guide and a first-board
  bring-up plan (current-limited power-up, rail measurements, Pico
  programming, both K-line channels).
- **Manual-install parts to pull from the JLCPCB assembly order**: U1
  (Pico, direct-solder), J1/J2/J3 (THT terminal blocks), D1 (marginal
  stock), D2 (zero LCSC stock), TP7–TP23 (optional — can also just DNP
  for a first prototype run), and R1/R2 if no acceptable stocked line
  turns up. Recommended-for-JLCPCB-SMT list: REG1, U2/U3, F1, D4, L1,
  C1/C2/C3/C4/C5/C6/C7, R4/R5.

---

## BOM

| Ref | Part | Value | Status |
|---|---|---|---|
| J1 | **Phoenix Contact 1715734** "MKDS 1,5/3-5,08" — 3-position, single-row, 5.08mm pitch THT, 17.5A/400V, AWG 26-14. **Manual (THT) install.** | pin1/2/3 = `K1`, `K1`, `LI1` — see "Terminal block" section | **✅ locked and footprint BOUND** (Chunk 5 Amendment 1) |
| J2 | **Phoenix Contact 1715734** (same part as J1). **Manual (THT) install.** | pin1/2/3 = `K2`, `K2`, `LI2` | **✅ locked and footprint BOUND** (Chunk 5 Amendment 1) |
| J3 | **Phoenix Contact 1715734** (same part as J1). **Manual (THT) install.** | pin1/2/3 = `12V_IN`, `GND`, `GND` | **✅ locked and footprint BOUND** (Chunk 5 Amendment 1) |
| U1 | Raspberry Pi Pico 2 W (SMD/castellated module, library part) | — | locked. **Direct-soldered, not socketed** (the female-socket plan was abandoned during layout — the mixed SMD/THT footprint didn't provide valid drilled header pads). **Excluded from BOM/pick-and-place** — hand-solder separately. Orientation/location frozen, user-approved. |
| U2 | **ST E-L9637D013TR** (automotive-grade), SOIC-8 | K-line channel 1 | locked |
| U3 | **ST E-L9637D013TR** (automotive-grade), SOIC-8 | K-line channel 2 | locked |
| R1 | **Vishay CRCW2512510RFKEG** — 510Ω, 1%, 1W, AEC-Q200, **2512 package** (K1 pull-up) | 510 Ω, 1 W | locked |
| R2 | **Vishay CRCW2512510RFKEG** — 510Ω, 1%, 1W, AEC-Q200, **2512 package** (K2 pull-up) | 510 Ω, 1 W | locked |
| R4 | **Yageo AC0603FR-07118KL** — 118kΩ, 1%, automotive, 0603, LCSC C227557 (REG1 feedback top) | 118 kΩ | locked |
| R5 | **Yageo AC0603FR-0722K1L** — 22.1kΩ, 1%, automotive, 0603, LCSC C227715 (REG1 feedback bottom) | 22.1 kΩ | locked |
| F1 | **Littelfuse 0459001.UR** — 1A, 125VAC/VDC, very-fast-acting SMD, 50A interrupt rating | worst-case load: 298.2mA@12V / 266.7mA@14.4V, 29.8%/26.7% of rating | **✅ locked and footprint BOUND** (Chunk 5): `FUSE-SMD_L7.3-W4.3` |
| D1 | **Micro Commercial Components 1.5KE24A-TP** — unidirectional axial TVS, DO-201AE/DO-201, LCSC C1975979 (VRWM 20.5V, VBR 22.8-25.2V, VC(max) 33.2V — exact match to locked spec). **Manual install/external source recommended** (JLCPCB sourcing marginal). | 1.5KE24A-family, exact part now locked | **✅ locked and footprint BOUND** (Chunk 5): `DO-201AE_BD5.3-L9.5-P13.50-D1.0-FD`. ⚠️ ERC warning: pins 1/2 have unspecified terminal type/role/name (library metadata gap, not electrical) — polarity/connectivity separately verified correct. |
| D2 | Schottky diode | **ON Semiconductor 1N5817RLG** (1A/20V, DO-41/DO-204AL through-hole) — final acceptance confirmed over an SMD alternative (rating/forward-drop/library-availability/hand-assembly all favor keeping it). **Manual install/external source** — not in the JLCPCB assembly BOM. | **locked, final**. ⚠️ Cosmetic-only issue: library STEP/GLB 3D model renders as a question-mark placeholder (part-quality report filed) — does not affect manufacturing geometry or connectivity, 3D visualization only. |
| D4 | Schottky diode, reverse-polarity protection | **Vishay SS36-E3/9AT** — 3A/60V, footprint `FP_DIOM7959X262N`. Anode(A)→`VS_FUSED`, cathode(K)→`VIN_PROT` | **✅ locked and footprint BOUND** (Chunk 5.2) — replaces the former Q1+D3+R3 MOSFET ideal-diode stage entirely (removed for Q1 sourcing risk, per Chunk 5.1's recommendation). ~0.3-0.5V forward drop at this board's ~0.3A load is harmless. |
| REG1 | Buck converter | **LMR51610XQDBVRQ1** (TI, automotive, 65V/1A sync buck, PFM light-load, SOT-23-6, **adjustable output — needs R4/R5 feedback divider**) | **locked** |
| L1 | Power inductor | **Bourns SRP1038A-330M** — 33µH ±20%, shielded, 3.5A Irms/5A Isat, AEC-Q200 | **locked** |
| C1 | **KEMET C0603C104K5RACAUTO** — 100nF, 50V, 0603, automotive (U2 Vcc decoupling, same part as C4) | 100 nF, 50V | locked |
| C2 | **KEMET C0603C104K5RACAUTO** — 100nF, 50V, 0603, automotive (U3 Vcc decoupling, same part as C4) | 100 nF, 50V | locked |
| C3 | Ceramic cap | **SAMWHA CS3225X7R225K101NRK** — 2.2µF, 100V, X7R, 1210 (REG1 VIN bulk) — ✅ **swap APPLIED** during PCB layout (2026-09-30), confirmed in flux's live BOM. Replaced the zero-stock KEMET C1210X225K1RACAUTO while preserving the 1210 footprint and VIN_PROT/GND connectivity. | locked, applied |
| C4 | **KEMET C0603C104K5RACAUTO** — 100nF, 50V, X7R, ±10%, 0603, automotive — HF decoupling at REG1 VIN/GND | 100 nF, 50V — clears the ~33.2V VIN_PROT worst case with margin | locked |
| C5 | Ceramic cap | **Samsung CL32B226KOJVPNE** — 22µF, 16V, X7R, ±10%, 1210, automotive (REG1 VOUT) | locked — **fails alone** (Chunk 4.5: worst-case 19.8µF before DC bias, ~16-16.4µF with it, vs. 20µF minimum required) — see C7 |
| C7 | Ceramic cap | **Samsung CL32B226KOJVPNE** — same part as C5, in parallel on VOUT_5V | added Chunk 4.5 (approved) — C5+C7 together give ~32µF effective, 60% margin above the 20µF requirement |
| C6 | Ceramic cap | **KEMET C0603C104K5RACAUTO** — 100nF, 50V, X7R, ±10%, 0603, automotive — REG1 bootstrap, **CB pin to SW pin, not to GND** | locked |

⚠️ **REG1 is not a fixed-5V part** (already established — see above) — it
requires the R4/R5 feedback divider to set 5V output. EN pin ties directly to
VIN (always-on; no UVLO circuit specified). Converter is synchronous — no
external catch diode needed.

⚠️ **Not yet vetted**: the terminal-block/connector topology below (the
A1/A2 K+L tie, the LI listen-taps) is an internal design decision that has
never been through outside electrical review.

## Terminal blocks (J1/J2/J3 — three separate 3-position screw-terminal blocks)

**Superseded by Chunk 5 Amendment 1 (2026-09-30):** the original design was
one 9-position block; the exact 9-position Phoenix Contact part was
unavailable, so it was split into **three separate 3-position Phoenix
Contact 1715734 connectors**, each electrically identical in role to a
third of the original single block. J1/J2/J3 are the only things placed on
this schematic/PCB — the "external pigtail wire" column is documentation
only, not a connector/footprint to place; it says which hand-wired
external wire (from the separate OBD2 pigtail cable) lands on which pin.

**PCB silkscreen labels — FINAL (updated during PCB layout, 2026-09-30):**
`K1-A K1-B LI1-MON` (J1) · `K2-A K2-B LI2-MON` (J2) · `+12V GND GND` (J3).
K1-A/K1-B and K2-A/K2-B are bonded duplicate points (not a differential
pair). **LI labels are `LI1-MON`/`LI2-MON` (not the earlier `LI1-IN`/
`LI2-IN`), and the "DO NOT DRIVE" warning was deliberately dropped** —
these terminals genuinely accept external vehicle diagnostic signals; the
real limitation is only that the Pico/L9637D can't transmit *through* the
LI pins, which "MON" (monitor) captures better than "IN" did.

Actual top-view physical silkscreen order on the finished board (reflects
real PCB placement, not just a linear list):
```
GND  GND  +12V
LI2-MON  K2-B  K2-A
LI1-MON  K1-B  K1-A
```

| Connector | Pin | Silkscreen label | Net | External pigtail wire (OBD pin) |
|---|---|---|---|---|
| J1 | 1 | K1-A | K1 | 7 |
| J1 | 2 | K1-B | K1 (bussed w/ pin 1) | 15 |
| J1 | 3 | LI1-MON | LI1 | (spare) |
| J2 | 1 | K2-A | K2 | 8 |
| J2 | 2 | K2-B | K2 (bussed w/ pin 1) | (spare) |
| J2 | 3 | LI2-MON | LI2 | (spare) |
| J3 | 1 | +12V | 12V_IN | 16 |
| J3 | 2 | GND | GND | 4 |
| J3 | 3 | GND | GND | 5 |

## U2 pinout (L9637D, channel 1)

| Pin | Name | Net |
|---|---|---|
| 1 | RX | K1_RX → U1.GP1 |
| 2 | LO | K1_LO → U1.GP2 |
| 3 | VCC | P3V3 |
| 4 | TX | K1_TX ← U1.GP0 |
| 5 | GND | GND |
| 6 | K | K1 |
| 7 | Vs | VS_FUSED |
| 8 | LI | LI1 |

R1 across pins 6–7. C1 across pins 3–5 (close to chip).

## U3 pinout (L9637D, channel 2)

| Pin | Name | Net |
|---|---|---|
| 1 | RX | K2_RX → U1.GP5 |
| 2 | LO | K2_LO → U1.GP6 |
| 3 | VCC | P3V3 |
| 4 | TX | K2_TX ← U1.GP4 |
| 5 | GND | GND |
| 6 | K | K2 |
| 7 | Vs | VS_FUSED |
| 8 | LI | LI2 |

R2 across pins 6–7. C2 across pins 3–5 (close to chip).

## Power path

```
J3.1 (12V_IN) → F1 → VS_FUSED
VS_FUSED → D1 (cathode=VS_FUSED, anode=GND, clamp, VC(max)=33.2V)
VS_FUSED → U2.7, U3.7 (direct, unprotected — L9637D tolerates reverse supply)
VS_FUSED → D4.anode
D4.cathode → VIN_PROT → REG1.VIN
REG1.VIN → C3 (2.2µF) → GND, and C4 (100nF, at pins) → GND
REG1.EN → VIN_PROT (tied high, always-on)
REG1.SW → L1 → VOUT_5V
REG1.CB (bootstrap) → C6 → REG1.SW  [not to GND]
REG1.FB ← R4 (from VOUT_5V) and → R5 (to GND)  [sets 5V output]
VOUT_5V → C5 (22µF) → GND, and C7 (22µF, parallel with C5) → GND
VOUT_5V → D2.anode
D2.cathode → U1.VSYS (pin 39)
U1.VBUS (pin 40): not connected
USB VBUS diode-ORs onto U1.VSYS automatically (Pico's own internal path)
```

**D4 (SS36 Schottky) is a series reverse-polarity protection diode ahead of
REG1 only** (replaces the former Q1+D3+R3 MOSFET ideal-diode stage as of
Chunk 5.2 — removed due to Q1 sourcing risk). Simple series diode, no gate
protection needed since there's no gate. ~0.3-0.5V forward drop at this
board's ~0.3A load is harmless (~0.09-0.15W dissipation).

## U1 (Pico 2 W) connections

| Pin | Net |
|---|---|
| VSYS (39) | VSYS_5V (from D2) |
| VBUS (40) | not connected |
| 3V3 | P3V3 |
| GND | GND |
| GP0 | K1_TX |
| GP1 | K1_RX |
| GP2 | K1_LO |
| GP4 | K2_TX |
| GP5 | K2_RX |
| GP6 | K2_LO |

GP0/GP1 = UART0. GP4/GP5 = UART1.

⚠️ **Not yet vetted**: this GPIO-to-UART mapping is the intended firmware
plan, not a pinout confirmed against Pico alternate-function documentation.
Confirmation is deferred to firmware bring-up, not resolved here.

## Full net list

| Net | Members |
|---|---|
| K1 | J1.1, J1.2, U2.6, R1.A |
| K1_TX | U2.4, U1.GP0 |
| K1_RX | U2.1, U1.GP1 |
| K1_LO | U2.2, U1.GP2 |
| LI1 | J1.3, U2.8 |
| K2 | J2.1, J2.2, U3.6, R2.A |
| K2_TX | U3.4, U1.GP4 |
| K2_RX | U3.1, U1.GP5 |
| K2_LO | U3.2, U1.GP6 |
| LI2 | J2.3, U3.8 |
| 12V_IN | J3.1, F1.A |
| VS_FUSED | F1.B, D1.cathode, U2.7, U3.7, D4.anode, R1.B, R2.B |
| VIN_PROT | D4.cathode, REG1.VIN, C3, C4, REG1.EN |
| REG1_SW | REG1.SW, L1 (pin A) |
| REG1_BOOT | REG1.CB, C6 (to REG1_SW, not GND) |
| VOUT_5V | L1 (pin B), REG1.FB ← R4, C5, C7, D2.anode |
| REG1_FB | REG1.FB, R4, R5 |
| VSYS_5V | D2.cathode → U1.VSYS |
| GND | J3.2, J3.3, U2.5, U3.5, REG1.GND, U1.GND, D1.anode, R5, C1.B, C2.B, C3.B, C4.B, C5.B, C7.B |
| P3V3 | U1.3V3, U2.3, U3.3, C1.A, C2.A |

## JLCPCB sourcing status (last refreshed Chunk 5.1, 2026-09-30 snapshot)

⚠️ Prices/stock are a point-in-time snapshot — refresh before actually
ordering. Excludes PCB fab, assembly labor, shipping, tax, and Extended-part
setup fees. **Mandatory gate (U2/U3) PASSES.**

| Ref | MPN | JLCPCB/LCSC status | Tier | Unit price | Qty-5 line cost | Notes |
|---|---|---|---|---:|---:|---|
| U1 | Pico 2 W module | LCSC C41407547, 160 in stock | n/a | $9.32 | $46.61 (×5) | — sourceable |
| U2, U3 | ST E-L9637D013TR | **LCSC C153038, 3,010 in stock — mandatory gate PASSES** | Extended | $1.68 | $16.83 (×10) | — sourceable |
| R1, R2 | Vishay CRCW2512510RFKEG | ✅ LCSC C2125401 — earlier "not found" was a search gap, not real | Extended | $0.0317 | $0.32 (×10) | Retain, resolved Chunk 5.1 |
| R4 | Yageo AC0603FR-07118KL | LCSC C227557, 4,800 in stock | Extended | $0.0057 | $0.03 (×5) | — sourceable |
| R5 | Yageo AC0603FR-0722K1L | LCSC C227715, 2,200 in stock | Extended | $0.0084 | $0.04 (×5) | — sourceable |
| F1 | Littelfuse 0459001.UR | LCSC C151129, 79 in stock | Extended | $0.7325 | $3.66 (×5) | Low stock — recheck before order |
| D1 | MCC 1.5KE24A-TP | Mouser 951 in stock; no live LCSC stock/price returned | Extended | $1.27 (Mouser) | ~$6.35 (×5, Mouser) | Retain for hand-assembly/external sourcing |
| D2 | ON Semi 1N5817RLG | Cataloged (LCSC C232461) but zero live stock | Extended | ref $0.25 | — | Consign, hand-solder, or approve a stocked equivalent |
| D4 | Vishay SS36-E3/9AT | Not yet checked — added Chunk 5.2, replaces the old Q1/D3/R3 stage | — | — | — | **Needs a sourcing check** — likely trivial, this is a very common part |
| REG1 | TI LMR51610XQDBVRQ1 | LCSC C41834356, 32 in stock (low) | Extended-risk | $2.58 | $12.90 (×5) | Sourceable now, but low stock — recheck before order |
| L1 | Bourns SRP1038A-330M | LCSC C2041318, 97 in stock (low) | Extended | $1.66 | $8.28 (×5) | Sourceable, low stock |
| C1, C2, C4, C6 | KEMET C0603C104K5RACAUTO | LCSC C129621, 765,620 in stock | Extended | $0.0153 | $0.31 (×20) | — sourceable, one part serves 4 positions |
| C3 | KEMET C1210X225K1RACAUTO (still live) | ⚠️ Zero LCSC stock. Approved replacement SAMWHA CS3225X7R225K101NRK (LCSC C2900749, 11,565 in stock) NOT yet applied | Extended | $0.1206 (SAMWHA, if applied) | $0.60 (×5, if applied) | **Apply before/with Chunk 6** |
| C5, C7 | Samsung CL32B226KOJVPNE (×2, parallel) | LCSC C472858, 43,756 in stock | Extended | $0.40 | $3.98 (×10) | — sourceable, same part serves both positions |
| J1, J2, J3 | Phoenix Contact 1715734 (×3) | ✅ LCSC C480520, 2,436 in stock (Mouser 13,142, DigiKey 5,915) | — | $0.7411 | $11.12 (×15) | Cleared Chunk 5.1 |

**Removed from BOM in Chunk 5.2** (no longer exist, no sourcing needed):
Q1 (Nexperia BUK6M61-60P — was a genuine procurement risk, resolved by
removing it), D3 (Nexperia BZT52H-C12,115), R3 (Yageo AC0603FR-0710KL).

**Known sourceable-line subtotal: ~$105 for 5 boards** (updated post-Chunk
5.1/5.2: adds J1/J2/J3 ~$11.12, R1/R2 ~$0.32, F1's now-confirmed ~$3.66,
C3's new $0.60 in place of the old unstocked part; removes the old R3
~$0.03) — still partial: excludes fab/labor/shipping/tax/setup fees, D1
(Mouser-only, not LCSC-confirmed), D2 (still zero LCSC stock), and D4
(not yet checked at all). Not a real quote.

## Test points (added Chunk 5)

17 library-backed Harwin S2761-46R test points, TP7–TP23 (TP1–TP6 are
reserved internally by the Pico module):

| Test point | Net | Purpose |
|---|---|---|
| TP7 | `12V_IN` | Raw vehicle supply |
| TP8 | `VS_FUSED` | Fused/protected supply |
| TP9 | `VIN_PROT` | Buck input after reverse-polarity protection |
| TP10 | `VOUT_5V` | Regulated 5V output |
| TP11 | `VSYS_5V` | Pico supply after D2 |
| TP12 | `P3V3` | Pico 3.3V rail |
| TP13 | `K1` | Channel 1 K-line |
| TP14 | `K2` | Channel 2 K-line |
| TP15 | `LI1` | Channel 1 LI input |
| TP16 | `LI2` | Channel 2 LI input |
| TP17 | `K1_TX` | Channel 1 TX logic |
| TP18 | `K1_RX` | Channel 1 RX logic |
| TP19 | `K1_LO` | Channel 1 LO logic |
| TP20 | `K2_TX` | Channel 2 TX logic |
| TP21 | `K2_RX` | Channel 2 RX logic |
| TP22 | `K2_LO` | Channel 2 LO logic |
| TP23 | `GND` | Ground reference |

## Status summary

See "⚠️ NOT YET VETTED" and "⏳ Open items for whichever chunk is currently
active" near the top for the authoritative, current list — this section is
intentionally not duplicated here to avoid drift between two copies.

One standing layout requirement regardless of chunk: keep the TVS current
loop and the REG1 VIN/GND loop extremely short.
