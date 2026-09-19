import { useEffect, useState } from "react";
import { api, type Immobiliser as ImmoState } from "../api";
import Card, { Button } from "./Card";

// Immobiliser status (read-only in the web UI). The Security-Learn re-sync is a
// bench/car proprietary write gated behind security access - kept to the CLI
// (gems_t4 kline secure) rather than exposed over a browser.
export default function Immobiliser({ enabled }: { enabled: boolean }) {
  const [state, setState] = useState<ImmoState | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function read() {
    setBusy(true);
    setError(null);
    try {
      setState(await api.immobiliser());
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  useEffect(() => {
    if (enabled) read();
    else setState(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  return (
    <Card
      title="Immobiliser"
      actions={
        <Button onClick={read} disabled={!enabled || busy} variant="ghost">
          Refresh
        </Button>
      }
    >
      {error && <div className="mb-3 text-sm text-red-400">{error}</div>}
      {!enabled ? (
        <div className="rounded-xl bg-neutral-900/50 p-6 text-center text-neutral-500 ring-1 ring-white/5">
          Connect to read immobiliser status.
        </div>
      ) : state === null ? (
        <div className="text-sm text-neutral-500">Reading…</div>
      ) : (
        <div className="grid grid-cols-2 gap-4">
          <StatusTile
            label="Engine mobilised"
            ok={state.mobilised}
            okText="Mobilised"
            badText="IMMOBILISED"
          />
          <StatusTile
            label="Learn mode"
            ok={!state.learn_mode}
            okText="Normal"
            badText="LEARN ACTIVE"
            neutral
          />
        </div>
      )}
      <p className="mt-4 text-xs text-neutral-600">
        Security-Learn (BeCM↔ECM re-sync) is a gated proprietary write — run it
        from the CLI (<code className="text-neutral-500">gems_t4 kline secure
        --immobiliser-synch</code>), not the browser.
      </p>
    </Card>
  );
}

function StatusTile({
  label,
  ok,
  okText,
  badText,
  neutral,
}: {
  label: string;
  ok: boolean;
  okText: string;
  badText: string;
  neutral?: boolean;
}) {
  const tone = ok
    ? "bg-emerald-500/10 text-emerald-300 ring-emerald-500/20"
    : neutral
      ? "bg-amber-500/10 text-amber-300 ring-amber-500/20"
      : "bg-red-500/10 text-red-300 ring-red-500/20";
  return (
    <div className={`rounded-xl p-4 ring-1 ${tone}`}>
      <div className="text-xs uppercase tracking-wide opacity-70">{label}</div>
      <div className="mt-1 text-lg font-semibold">{ok ? okText : badText}</div>
    </div>
  );
}
