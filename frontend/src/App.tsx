import { useEffect, useState } from "react";
import { api, type Status } from "./api";
import ConnectionPanel from "./components/ConnectionPanel";
import LiveDashboard from "./components/LiveDashboard";
import FaultCodes from "./components/FaultCodes";
import Actuators from "./components/Actuators";
import Coding from "./components/Coding";
import Immobiliser from "./components/Immobiliser";
import Toolbox from "./components/Toolbox";

const TABS = [
  "Live Data",
  "Fault Codes",
  "Actuators",
  "Coding",
  "Immobiliser",
  "Toolbox",
] as const;
type Tab = (typeof TABS)[number];

export default function App() {
  const [status, setStatus] = useState<Status | null>(null);
  const [tab, setTab] = useState<Tab>("Live Data");

  const refresh = () => api.status().then(setStatus).catch(() => setStatus(null));

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, []);

  // Live data / reads work whenever we have a session (real ECU or emulator).
  const enabled = !!status?.connected || status?.connection_kind === "virtual";

  return (
    <div className="mx-auto max-w-7xl px-4 py-6 sm:px-6">
      <header className="mb-6 flex items-baseline gap-3">
        <h1 className="text-2xl font-bold tracking-tight text-neutral-100">
          gems_t4
        </h1>
        <span className="hidden text-sm text-neutral-500 sm:inline">
          GEMS V8 diagnostics
        </span>
        <div className="flex-1" />
        {status && (
          <span className="rounded-full bg-neutral-800 px-3 py-1 text-xs text-neutral-400 ring-1 ring-white/10">
            {status.on_real_ecu ? "real ECU" : `emulator · ${status.scenario}`}
          </span>
        )}
      </header>

      <ConnectionPanel status={status} onChange={refresh} />

      <nav className="my-6 flex flex-wrap gap-2">
        {TABS.map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`rounded-lg px-3.5 py-2 text-sm font-medium ring-1 ring-white/10 transition ${
              tab === t
                ? "bg-neutral-100 text-neutral-900"
                : "bg-neutral-900/70 text-neutral-300 hover:bg-neutral-800"
            }`}
          >
            {t}
          </button>
        ))}
      </nav>

      <main>
        {tab === "Live Data" && (
          <section>
            <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-neutral-500">
              Live Data
            </h2>
            <LiveDashboard enabled={enabled} />
          </section>
        )}
        {tab === "Fault Codes" && <FaultCodes enabled={enabled} />}
        {tab === "Actuators" && <Actuators enabled={enabled} />}
        {tab === "Coding" && <Coding enabled={enabled} />}
        {tab === "Immobiliser" && <Immobiliser enabled={enabled} />}
        {tab === "Toolbox" && <Toolbox status={status} onChange={refresh} />}
      </main>

      <footer className="mt-10 text-center text-xs text-neutral-600">
        gems_t4 API · {status?.connection_label ?? "localhost"}
      </footer>
    </div>
  );
}
