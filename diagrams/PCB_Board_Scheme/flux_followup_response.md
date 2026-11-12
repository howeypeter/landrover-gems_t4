# Response to electrical design review

Thanks for the review — the datasheet citations checked out against what we'd
already independently confirmed (Vcc 3–7V range, TX threshold, K pull-up
≤5kΩ limit, D2 ratings, VSYS≤5.5V, antenna keepout), and the R1/R2 power math
is correct. Two findings are confirmed bugs we're fixing immediately; a few
others need your input to close out properly.

## Confirmed and being fixed

**D1 polarity.** Agreed — the net table had it backwards. Correcting to
**cathode (banded end) → VS_FUSED, anode → GND** (reverse-biased/inert in
normal operation, clamps on a positive spike).

**R1/R2 power rating.** Agreed, math confirmed independently (12²/510=0.28W,
14.4²/510=0.41W, 18²/510=0.64W — zero margin on a ¼W part even at nominal
12V). Upgrading to 1W.

## Needs your input — please help resolve

### 1. TVS clamp voltage discrepancy

Your review states the 1.5KE24A clamps at **~33.2V**. We had independently
sourced **38.9V** as the clamp voltage (Vc at rated Ipp) for the 24V "A"
(tight-tolerance) suffix part across the 1.5KE24A/P6KE24A/5KP24A family —
same breakdown grade, same silicon characteristic, different package/power
rating. Can you confirm which number is correct against the actual
manufacturer datasheet (please cite the exact source/page), including the
test current (Ipp) the clamp voltage is specified at? This number directly
sets the minimum absolute-max input rating we need on the regulator.

### 2. Please recommend an exact REG1 (buck) part

Current REG1 is a generic unbranded "5–30V in, fixed 5V out, 3A" module with
no MPN or datasheet — exactly the gap you flagged. Given:
- Confirmed clamp voltage from item 1 above (33.2V or 38.9V, TBD), with margin
- Continuous automotive input range including load-dump / cold-crank behavior
- Stable at light, bursty load (Pico 2 W, ~0.5A design target on the 5V rail
  per your provisional load envelope)
- Manufacturer-published input/output capacitor recommendations
- Ideally an actual chip/module (not a generic multi-pack) so the full
  support circuit can be captured

Can you recommend 2–3 specific candidate parts (MPN + datasheet link) that
meet this, so we can pick one and complete the support circuit?

### 3. Reverse-polarity protection scope

One nuance on this finding: Board 1's normal in-vehicle connection is via a
**keyed OBD-II (J1962) connector**, which mechanically prevents reversing
pin 16 (+12V) against pins 4/5 (GND) — so reverse-battery via a real car
connection isn't physically possible through that path. Separately, on the
bench side, **Board 2 already has its own reverse-polarity Schottky on the
DC barrel-jack input**, ahead of Board 1.

The actual exposure is narrower: Board 1's design deliberately puts +12V,
GND, and signal lines on **reconfigurable screw terminals** (see the
9-terminal scheme, `A1..B3, 12V, GND, GND`) — so a wiring mistake while
moving a wire between terminals could put +12V where GND is expected, in a
way a keyed connector prevents.

Given that specific (narrower) exposure, do you still recommend the
series-Schottky / ideal-diode stage on Board 1 itself, or would you consider
the keyed-connector + Board-2-protection combination sufficient for the
car-connected and bench-hub-connected cases, leaving only the
standalone-hand-wired case as a residual (documented) risk? Your call on
whether that residual risk warrants the extra stage.

## Accepted, will implement without further discussion

- Automotive-rated F1 with defined technology/curve — will select once REG1
  (and its inrush/surge behavior) is known.
- Test points on 12V_IN, VS_FUSED, 5V_BUCK, VSYS_5V, P3V3, K1, K2, LI1, LI2,
  TX/RX/LO, GND.
- Input/output bulk capacitors per REG1's datasheet once selected.
- Terminal silkscreen: `K1`, `K1/STRAP`, `LI1`, `K2`, `K2/AUX`, `LI2`, `+12V`,
  `GND4`, `GND5`, plus the `L-K STRAP — REMOVE FOR NORMAL OBD` warning at A2.
- 1.5KE24A BOM wording corrected (VRWM ≠ the "24" in the part number).
- Bring-up gate checklist adopted as written for first power-on.

## Confirmed correct, no change

C1/C2 100nF decoupling (retained), K1/K2 channel separation, VSYS-not-VBUS
injection point, D2 1N5817 selection, 3V3 budget headroom for both
transceivers, UART0/UART1 pin allocation (will confirm exact SDK
alternate-function setup during firmware bring-up as you noted).
