// Per-measure gauge full-scale ranges, keyed by the measure NAME (the display
// label is shared between the virtual and real-ECU paths, whereas the numeric
// id differs). Anything unlisted falls back to a value-derived range so every
// measure still renders sensibly.

const BY_NAME: Record<string, [number, number]> = {
  "Coolant temperature": [-40, 130],
  "Intake air temperature": [-40, 130],
  "Fuel temperature": [-40, 130],
  "Oil temperature": [-40, 160],
  "Catalyst temperature (bank A)": [0, 900],
  "Engine speed": [0, 7000],
  "Idle speed reference": [0, 7000],
  "Battery voltage": [0, 16],
  "Throttle angle": [0, 100],
  "Calculated load": [0, 100],
  "Mass air flow": [0, 120],
  "O2 sensor voltage (bank A)": [0, 1.0],
  "O2 sensor voltage (bank B)": [0, 1.0],
  "Short-term fuel trim": [-25, 25],
  "Long-term fuel trim": [-25, 25],
  "Idle air control valve": [0, 200],
  "Ignition advance": [-10, 50],
  "Gearbox torque retard": [0, 30],
  "Road speed": [0, 160],
  "Injector pulse width": [0, 20],
  "Coil charge time": [0, 10],
  "Purge valve duty": [0, 100],
  "Engine run time": [0, 3600],
  "Misfire count (total)": [0, 255],
  // Two-state / status flags: 0..1 so the arc reads as off/on, not 0/100.
  "Fuelling loop status": [0, 1],
  "Gearbox status (0=P,1=D)": [0, 1],
  "A/C request": [0, 1],
  "Ignition switch": [0, 1],
  "Security learn state": [0, 1],
  "Immobiliser mobilised": [0, 1],
  "Fuel pump state": [0, 1],
  "Cooling fan state": [0, 1],
};

export function rangeFor(
  name: string,
  value: number,
): [number, number] {
  const hit = BY_NAME[name];
  if (hit) return hit;
  // Per-cylinder misfire counters and other unknowns: derive a sane range.
  if (/misfire count/i.test(name)) return [0, 255];
  const hi = Math.max(100, Math.abs(value) * 1.5) || 1;
  return [0, hi];
}
