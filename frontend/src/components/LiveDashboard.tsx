import { useEffect, useRef, useState } from "react";
import { liveSocket, type Measure } from "../api";
import { rangeFor } from "../ranges";
import Gauge from "./Gauge";
import MisfireChart from "./MisfireChart";
import StatusTile from "./StatusTile";
import { stateFor } from "../states";

const isMisfireCyl = (name: string) => /^Misfire count cyl \d$/.test(name);
const MISFIRE_TOTAL = "Misfire count (total)";

// Measures where a high reading isn't "worse", so the gauge stays a calm
// neutral colour instead of the green/amber/red threshold ramp.
const NEUTRAL = new Set<string>(["Battery voltage"]);

// Streams live measures over the WebSocket and renders a gauge per numeric one.
// A "Focus" picker narrows the stream to one PID for a fast single-sensor read.
export default function LiveDashboard({ enabled }: { enabled: boolean }) {
  const [measures, setMeasures] = useState<Measure[]>([]);
  const [focus, setFocus] = useState<string>(""); // "" = all
  const [error, setError] = useState<string | null>(null);
  const [live, setLive] = useState(false);
  const sockRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!enabled) {
      sockRef.current?.close();
      setLive(false);
      return;
    }
    // Stream all measures; when focused on one, just bump the rate and filter
    // client-side by name (the id isn't unique on the virtual ECU, so we can't
    // narrow the server read by pid reliably).
    const ws = liveSocket([], focus ? 12 : 4);
    sockRef.current = ws;
    ws.onopen = () => {
      setLive(true);
      setError(null);
    };
    ws.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.error) setError(msg.error);
      else if (msg.measures) setMeasures(msg.measures);
    };
    ws.onclose = () => setLive(false);
    return () => ws.close();
  }, [enabled, focus]);

  const numeric = measures.filter((m) => typeof m.value === "number");
  // Focus filters by NAME (unique + stable). The id can repeat across the
  // stylized virtual measures, so name is the safe selector.
  const focused = focus ? numeric.filter((m) => m.name === focus) : [];
  // In the "all" view the 8 per-cylinder misfire counters collapse into one bar
  // chart (with the running total as a stat readout, not a gauge).
  const misfire = numeric.filter((m) => isMisfireCyl(m.name));
  const misfireTotal = numeric.find((m) => m.name === MISFIRE_TOTAL);
  const shown = focus
    ? focused
    : numeric.filter((m) => !isMisfireCyl(m.name) && m.name !== MISFIRE_TOTAL);

  return (
    <div>
      <div className="mb-4 flex items-center gap-3">
        <span
          className={`inline-block h-2 w-2 rounded-full ${live ? "bg-emerald-400 animate-pulse" : "bg-neutral-600"}`}
        />
        <span className="text-sm text-neutral-400">{live ? "Streaming" : "Idle"}</span>
        <div className="flex-1" />
        <label className="flex items-center gap-2 text-xs text-neutral-400">
          Focus
          <select
            className="rounded-lg bg-neutral-800 px-3 py-1.5 text-sm text-neutral-100 ring-1 ring-white/10"
            value={focus}
            onChange={(e) => setFocus(e.target.value)}
          >
            <option value="">All parameters</option>
            {measures.map((m) => (
              <option key={m.name} value={m.name}>
                {m.pid_hex ? `${m.pid_hex}  ${m.name}` : m.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {error && <div className="mb-3 text-sm text-red-400">{error}</div>}

      {shown.length === 0 ? (
        <div className="rounded-2xl bg-neutral-900/50 p-10 text-center text-neutral-500 ring-1 ring-white/5">
          {enabled ? "Waiting for live data…" : "Connect to see live data."}
        </div>
      ) : (
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5">
          {shown.map((m) => {
            // Binary/state measures render as a status tile, not a 0/1 gauge.
            const st = stateFor(m.name, m.value as number);
            if (st) {
              return (
                <StatusTile
                  key={m.name}
                  label={m.name}
                  state={st.state}
                  tone={st.tone}
                />
              );
            }
            const [lo, hi] = rangeFor(m.name, m.value as number);
            return (
              <Gauge
                key={m.name}
                label={m.name}
                value={m.value as number}
                unit={m.unit}
                min={lo}
                max={hi}
                neutral={NEUTRAL.has(m.name)}
              />
            );
          })}
        </div>
      )}

      {!focus && (misfire.length > 0 || misfireTotal) && (
        <div className="mt-4">
          <MisfireChart measures={misfire} total={misfireTotal} />
        </div>
      )}
    </div>
  );
}
