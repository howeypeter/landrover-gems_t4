// A binary/state measure shown as a status indicator (coloured dot + word)
// instead of a 0/1 radial gauge. Same card footprint as Gauge so the grid stays
// uniform.

export type Tone = "ok" | "bad" | "warn" | "info" | "idle";

const TONE: Record<Tone, { dot: string; text: string }> = {
  ok: { dot: "bg-emerald-400", text: "text-emerald-300" },
  bad: { dot: "bg-red-400", text: "text-red-300" },
  warn: { dot: "bg-amber-400", text: "text-amber-300" },
  info: { dot: "bg-sky-400", text: "text-sky-300" },
  idle: { dot: "bg-neutral-500", text: "text-neutral-300" },
};

export default function StatusTile({
  label,
  state,
  tone,
}: {
  label: string;
  state: string;
  tone: Tone;
}) {
  const t = TONE[tone];
  return (
    <div className="flex flex-col items-center rounded-2xl bg-neutral-900/70 p-4 shadow-lg ring-1 ring-white/5">
      <div className="flex flex-1 flex-col items-center justify-center gap-2 py-4">
        <span className={`h-3 w-3 rounded-full ${t.dot}`} />
        <span className={`text-lg font-semibold ${t.text}`}>{state}</span>
      </div>
      <div className="mt-1 text-center text-sm font-medium text-neutral-300">{label}</div>
      <div className="text-[11px] text-neutral-600">status</div>
    </div>
  );
}
