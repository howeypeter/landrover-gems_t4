import { useEffect, useState } from "react";
import { api, type Dtc } from "../api";
import Card, { Button } from "./Card";

// Read / clear stored fault codes. Clear prompts for confirmation, mirroring
// the CLI/GUI (there is no per-code clear on GEMS/T4 - it's clear-all).
export default function FaultCodes({ enabled }: { enabled: boolean }) {
  const [dtcs, setDtcs] = useState<Dtc[] | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function read() {
    setBusy(true);
    setError(null);
    setNote(null);
    try {
      setDtcs((await api.dtcs()).dtcs);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function clear() {
    if (!confirm("Clear ALL stored fault codes? This cannot be undone.")) return;
    setBusy(true);
    setError(null);
    try {
      const r = await api.clearDtcs();
      setNote(r.cleared ? "Fault codes cleared." : "Clear not acknowledged.");
      await read();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (enabled) read();
    else setDtcs(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  return (
    <Card
      title="Fault Codes"
      actions={
        <div className="flex gap-2">
          <Button onClick={read} disabled={busy || !enabled} variant="ghost">
            Re-read
          </Button>
          <Button
            onClick={clear}
            disabled={busy || !enabled || !dtcs?.length}
            variant="danger"
          >
            Clear ALL codes
          </Button>
        </div>
      }
    >
      {error && <div className="mb-3 text-sm text-red-400">{error}</div>}
      {note && <div className="mb-3 text-sm text-emerald-400">{note}</div>}

      {!enabled ? (
        <Empty>Connect to read fault codes.</Empty>
      ) : dtcs === null ? (
        <Empty>Reading…</Empty>
      ) : dtcs.length === 0 ? (
        <div className="rounded-xl bg-emerald-500/10 p-6 text-center text-emerald-300 ring-1 ring-emerald-500/20">
          No stored fault codes.
        </div>
      ) : (
        <ul className="divide-y divide-white/5">
          {dtcs.map((d) => (
            <li key={d.code} className="flex items-center gap-4 py-3">
              <span className="font-mono text-sm font-semibold text-amber-300">
                {d.code}
              </span>
              <span className="flex-1 text-sm text-neutral-300">
                {d.description}
              </span>
              <span className="rounded-full bg-neutral-800 px-2.5 py-0.5 text-xs text-neutral-400 ring-1 ring-white/10">
                {d.state}
              </span>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return (
    <div className="rounded-xl bg-neutral-900/50 p-6 text-center text-neutral-500 ring-1 ring-white/5">
      {children}
    </div>
  );
}
