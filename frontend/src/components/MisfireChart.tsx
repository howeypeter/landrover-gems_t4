import type { Measure } from "../api";
import Card from "./Card";

// The eight per-cylinder misfire counters as one bar chart (integers). A count
// of 0 is a calm neutral bar; any misfire shows amber so a bad cylinder pops.
export default function MisfireChart({ measures }: { measures: Measure[] }) {
  // measures come in cylinder order (0x20..0x27 -> "Misfire count cyl 1..8").
  const bars = measures.map((m) => {
    const n = Math.max(0, Math.round(Number(m.value) || 0));
    const cyl = /cyl (\d)/i.exec(m.name)?.[1] ?? "?";
    return { cyl, n };
  });
  const peak = Math.max(5, ...bars.map((b) => b.n)); // headroom so 0s aren't full

  return (
    <Card title="Misfire counts (per cylinder)">
      <div className="flex items-end gap-2 sm:gap-4" style={{ height: 160 }}>
        {bars.map((b) => {
          const pct = (b.n / peak) * 100;
          const bad = b.n > 0;
          return (
            <div key={b.cyl} className="flex flex-1 flex-col items-center gap-1">
              <div
                className={`text-xs font-semibold ${bad ? "text-amber-300" : "text-neutral-500"}`}
              >
                {b.n}
              </div>
              <div className="flex w-full flex-1 items-end">
                <div
                  className={`w-full rounded-t ${bad ? "bg-amber-400" : "bg-neutral-700"}`}
                  style={{ height: `${Math.max(2, pct)}%` }}
                  title={`Cylinder ${b.cyl}: ${b.n} misfires`}
                />
              </div>
              <div className="text-xs text-neutral-400">{b.cyl}</div>
            </div>
          );
        })}
      </div>
      <div className="mt-2 text-center text-[11px] text-neutral-600">
        cylinder number · counts are cumulative (0 = none)
      </div>
    </Card>
  );
}
