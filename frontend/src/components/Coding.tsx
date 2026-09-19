import { useEffect, useState } from "react";
import { api, type CodingField } from "../api";
import Card, { Button } from "./Card";

// Read ECU coding fields; writable ones get an inline editor. Writes go through
// the gated Backend path (backup + verify + confirm) - the API confirms server
// side, but we still gate the button behind an explicit browser confirm.
export default function Coding({ enabled }: { enabled: boolean }) {
  const [fields, setFields] = useState<CodingField[]>([]);
  const [edit, setEdit] = useState<Record<string, string>>({});
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);

  async function load() {
    setError(null);
    try {
      setFields((await api.coding()).fields);
    } catch (e) {
      setError((e as Error).message);
    }
  }

  useEffect(() => {
    if (enabled) load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  async function save(f: CodingField) {
    const text = edit[f.key] ?? f.value ?? "";
    if (!confirm(`Write coding "${f.name}" = "${text}"?`)) return;
    setBusy(f.key);
    setError(null);
    setNote(null);
    try {
      await api.writeCoding(f.key, text);
      setNote(`${f.name} written.`);
      setEdit((p) => {
        const n = { ...p };
        delete n[f.key];
        return n;
      });
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(null);
    }
  }

  return (
    <Card
      title="Coding"
      actions={
        <Button onClick={load} disabled={!enabled} variant="ghost">
          Refresh
        </Button>
      }
    >
      {error && <div className="mb-3 text-sm text-red-400">{error}</div>}
      {note && <div className="mb-3 text-sm text-emerald-400">{note}</div>}
      {!enabled ? (
        <div className="rounded-xl bg-neutral-900/50 p-6 text-center text-neutral-500 ring-1 ring-white/5">
          Connect to read coding.
        </div>
      ) : (
        <ul className="space-y-2">
          {fields.map((f) => (
            <li
              key={f.key}
              className="flex flex-wrap items-center gap-3 rounded-xl bg-neutral-800/50 p-3 ring-1 ring-white/5"
            >
              <div className="min-w-40 flex-1">
                <div className="text-sm text-neutral-200">{f.name}</div>
                <div className="font-mono text-xs text-neutral-500">{f.key}</div>
              </div>
              {f.writable ? (
                <>
                  <input
                    className="w-40 rounded-lg bg-neutral-900 px-3 py-1.5 text-sm text-neutral-100 ring-1 ring-white/10"
                    value={edit[f.key] ?? f.value ?? ""}
                    onChange={(e) =>
                      setEdit((p) => ({ ...p, [f.key]: e.target.value }))
                    }
                  />
                  <Button
                    onClick={() => save(f)}
                    disabled={busy === f.key}
                    variant="primary"
                  >
                    {busy === f.key ? "…" : "Write"}
                  </Button>
                </>
              ) : (
                <span className="font-mono text-sm text-neutral-300">
                  {f.value ?? "—"}
                  <span className="ml-2 rounded bg-neutral-700/60 px-1.5 py-0.5 text-[10px] uppercase text-neutral-400">
                    read-only
                  </span>
                </span>
              )}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
