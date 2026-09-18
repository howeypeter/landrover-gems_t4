// Per-measure gauge full-scale ranges. Keyed by OBD PID (real ECU); falls back
// to a value-derived range so any measure still renders sensibly.

const BY_PID: Record<number, [number, number]> = {
  0x04: [0, 100], // engine load %
  0x05: [-40, 130], // coolant °C
  0x06: [-100, 100],
  0x07: [-100, 100],
  0x08: [-100, 100],
  0x09: [-100, 100],
  0x0c: [0, 7000], // rpm
  0x0d: [0, 200], // speed
  0x0e: [-30, 60], // timing
  0x0f: [-40, 130], // intake air °C
  0x10: [0, 120], // MAF
  0x11: [0, 100], // throttle %
  0x14: [0, 1.275],
  0x15: [0, 1.275],
  0x18: [0, 1.275],
  0x19: [0, 1.275],
};

export function rangeFor(pid: number | null, value: number): [number, number] {
  if (pid != null && BY_PID[pid]) return BY_PID[pid];
  const hi = Math.max(100, Math.abs(value) * 1.5) || 1;
  return [0, hi];
}
