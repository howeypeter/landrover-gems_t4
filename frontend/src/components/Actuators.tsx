import { useEffect, useState } from "react";
import { api, type Actuator, type ActuatorResult } from "../api";
import Card, { Button } from "./Card";

// Run actuator tests. The backend enforces the safety interlocks (e.g. fuel
// pump refused while the engine is running) - we surface the refusal message
// verbatim, which is half the character of the real T4.
export default function Actuators({ enabled }: { enabled: boolean }) {
  const [list, setList] = useState<Actuator[]>([]);
  const [results, setResults] = useState<Record<number, ActuatorResult>>({});
  const [busy, setBusy] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api
      .actuators()
      .then((r) => setList(r.actuators))
      .catch((e) => setError((e as Error).message));
  }, []);

  async function run(id: number, state: number) {
    setBusy(id);
    setError(null);
    try {
      const r = await api.runActuator(id, state);
      setResults((prev) => ({ ...prev, [id]: r }));
    } catch (e) {
      setResults((prev) => ({
        ...prev,
        [id]: { actuator_id: id, ok: false, message: (e as Error).message },
      }));
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card title="Actuator Tests">
      {error && <div className="mb-3 text-sm text-red-400">{error}</div>}
      {!enabled && (
        <div className="mb-3 text-sm text-amber-400">
          Connect to run actuator tests.
        </div>
      )}
      {list.length === 0 ? (
        <div className="rounded-xl bg-neutral-900/50 p-6 text-center text-neutral-500 ring-1 ring-white/5">
          No actuators available.
        </div>
      ) : (
        <ul className="space-y-2">
          {list.map((a) => {
            const res = results[a.id];
            return (
              <li
                key={a.id}
                className="rounded-xl bg-neutral-800/50 p-3 ring-1 ring-white/5"
              >
                <div className="flex items-center gap-3">
                  <span className="flex-1 text-sm text-neutral-200">
                    {a.name}
                    {!a.allowed_engine_running && (
                      <span className="ml-2 rounded bg-amber-500/15 px-1.5 py-0.5 text-[10px] uppercase text-amber-300">
                        engine-off only
                      </span>
                    )}
                  </span>
                  <Button
                    onClick={() => run(a.id, 1)}
                    disabled={!enabled || busy === a.id}
                    variant="primary"
                  >
                    {busy === a.id ? "…" : "On / Test"}
                  </Button>
                  <Button
                    onClick={() => run(a.id, 0)}
                    disabled={!enabled || busy === a.id}
                    variant="ghost"
                  >
                    Off
                  </Button>
                </div>
                {res && (
                  <div
                    className={`mt-2 text-xs ${res.ok ? "text-emerald-400" : "text-amber-400"}`}
                  >
                    {res.ok ? "✓ " : "✗ "}
                    {res.message}
                  </div>
                )}
              </li>
            );
          })}
        </ul>
      )}
    </Card>
  );
}
