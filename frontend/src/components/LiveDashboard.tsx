import { useEffect, useRef, useState } from "react";
import { liveSocket, type Measure } from "../api";
import { rangeFor } from "../ranges";
import Gauge from "./Gauge";

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
    const pids = focus ? [focus.replace(/^0x/i, "")] : [];
    const ws = liveSocket(pids, focus ? 10 : 4);
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
  const shown = focus
    ? numeric.filter((m) => m.pid_hex?.toLowerCase() === focus.toLowerCase())
    : numeric;

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
              <option key={m.pid_hex ?? m.name} value={m.pid_hex ?? ""}>
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
            const [lo, hi] = rangeFor(m.pid, m.value as number);
            return (
              <Gauge
                key={m.pid_hex ?? m.name}
                label={m.name}
                value={m.value as number}
                unit={m.unit}
                min={lo}
                max={hi}
              />
            );
          })}
        </div>
      )}
    </div>
  );
}
