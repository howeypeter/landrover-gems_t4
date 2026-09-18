import { useEffect, useState } from "react";
import { api, type Status } from "./api";
import ConnectionPanel from "./components/ConnectionPanel";
import LiveDashboard from "./components/LiveDashboard";

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);

  const refresh = () => api.status().then(setStatus).catch(() => setStatus(null));

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, []);

  // Live data streams whenever we have a session (real ECU or the emulator).
  const enabled = !!status?.connected || status?.connection_kind === "virtual";

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <header className="mb-6 flex items-baseline gap-3">
        <h1 className="text-2xl font-bold tracking-tight text-neutral-100">gems_t4</h1>
        <span className="text-sm text-neutral-500">GEMS V8 diagnostics</span>
        <div className="flex-1" />
        {status && (
          <span className="rounded-full bg-neutral-800 px-3 py-1 text-xs text-neutral-400 ring-1 ring-white/10">
            {status.on_real_ecu ? "real ECU" : `emulator · ${status.scenario}`}
          </span>
        )}
      </header>

      <div className="space-y-6">
        <ConnectionPanel status={status} onChange={refresh} />
        <section>
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
            Live Data
          </h2>
          <LiveDashboard enabled={enabled} />
        </section>
      </div>

      <footer className="mt-10 text-center text-xs text-neutral-600">
        gems_t4 API · localhost
      </footer>
    </div>
  );
}
