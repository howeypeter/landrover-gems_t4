import type { Tone } from "./components/StatusTile";

// Binary/state measures rendered as a StatusTile instead of a 0/1 gauge.
// Each maps value 0 (off) and non-zero (on) to a label + colour tone.
// Tones: ok=green, bad=red, warn=amber, info=blue, idle=grey.

interface StateSpec {
  on: [string, Tone];
  off: [string, Tone];
}

export const STATES: Record<string, StateSpec> = {
  "Immobiliser mobilised": { on: ["Mobilised", "ok"], off: ["Immobilised", "bad"] },
  "Fuel pump state": { on: ["Running", "ok"], off: ["Off", "idle"] },
  "Ignition switch": { on: ["On", "ok"], off: ["Off", "idle"] },
  "A/C request": { on: ["Requested", "info"], off: ["Off", "idle"] },
  "Cooling fan state": { on: ["On", "info"], off: ["Off", "idle"] },
  "Security learn state": { on: ["Learn active", "warn"], off: ["Normal", "ok"] },
  "Gearbox status (0=P,1=D)": { on: ["Drive", "info"], off: ["Park", "idle"] },
  "Fuelling loop status": { on: ["Closed loop", "ok"], off: ["Open loop", "warn"] },
};

export function stateFor(
  name: string,
  value: number,
): { state: string; tone: Tone } | null {
  const spec = STATES[name];
  if (!spec) return null;
  const [label, tone] = value ? spec.on : spec.off;
  return { state: label, tone };
}
