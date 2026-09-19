// A modern 270° radial gauge (SVG). No external deps.

interface Props {
  label: string;
  value: number;
  unit: string;
  min: number;
  max: number;
  // When true, the arc stays a calm neutral colour regardless of fill - for
  // measures where a high reading isn't "worse" (e.g. battery voltage).
  neutral?: boolean;
}

const START = 135; // degrees (bottom-left)
const SWEEP = 270; // clockwise to bottom-right

function polar(cx: number, cy: number, r: number, deg: number) {
  const rad = ((deg - 90) * Math.PI) / 180;
  return { x: cx + r * Math.cos(rad), y: cy + r * Math.sin(rad) };
}

function arc(cx: number, cy: number, r: number, a0: number, a1: number) {
  const s = polar(cx, cy, r, a0);
  const e = polar(cx, cy, r, a1);
  const large = a1 - a0 > 180 ? 1 : 0;
  return `M ${s.x} ${s.y} A ${r} ${r} 0 ${large} 1 ${e.x} ${e.y}`;
}

function color(frac: number) {
  if (frac < 0.6) return "#34d399"; // emerald
  if (frac < 0.85) return "#fbbf24"; // amber
  return "#f87171"; // red
}

export default function Gauge({ label, value, unit, min, max, neutral }: Props) {
  const frac = max === min ? 0 : Math.max(0, Math.min(1, (value - min) / (max - min)));
  const size = 160;
  const c = size / 2;
  const r = 62;
  const end = START + SWEEP * frac;
  const stroke = neutral ? "#60a5fa" : color(frac); // calm blue when neutral

  return (
    <div className="flex flex-col items-center rounded-2xl bg-neutral-900/70 ring-1 ring-white/5 p-4 shadow-lg">
      <svg width={size} height={size - 22} viewBox={`0 0 ${size} ${size - 22}`}>
        <path d={arc(c, c, r, START, START + SWEEP)} fill="none" stroke="#27272a" strokeWidth={12} strokeLinecap="round" />
        {frac > 0 && (
          <path d={arc(c, c, r, START, end)} fill="none" stroke={stroke} strokeWidth={12} strokeLinecap="round" />
        )}
        <text x={c} y={c - 4} textAnchor="middle" className="fill-neutral-100" style={{ fontSize: 26, fontWeight: 700 }}>
          {!Number.isFinite(value)
            ? "--"
            : Number.isInteger(value)
              ? value
              : value.toFixed(1)}
        </text>
        <text x={c} y={c + 16} textAnchor="middle" className="fill-neutral-400" style={{ fontSize: 12 }}>
          {unit}
        </text>
      </svg>
      <div className="mt-1 text-center text-sm font-medium text-neutral-300">{label}</div>
      <div className="text-[11px] text-neutral-500">
        {min} – {max}
      </div>
    </div>
  );
}
