import { useEffect, useState } from "react";
import { api, type Status, type TestResult } from "../api";
import Card, { Button } from "./Card";

// Toolbox: VIN read, connection self-test (with latency), emulator scenario
// selection, and the EPROM map lookalike list. Mirrors the GUI Toolbox screen.
export default function Toolbox({
  status,
  onChange,
}: {
  status: Status | null;
  onChange: () => void;
}) {
  const enabled = !!status?.connected || status?.connection_kind === "virtual";
  return (
    <div className="space-y-6">
      <VinCard enabled={enabled} />
      <SelfTestCard enabled={enabled} />
      <ScenarioCard status={status} onChange={onChange} />
      <MapsCard />
    </div>
  );
}

function VinCard({ enabled }: { enabled: boolean }) {
  const [vin, setVin] = useState<string | null | undefined>(undefined);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  async function read() {
    setBusy(true);
    setError(null);
    try {
      setVin((await api.vin()).vin);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <Card
      title="Vehicle Identification"
      actions={
        <Button onClick={read} disabled={!enabled || busy} variant="ghost">
          {busy ? "…" : "Read VIN"}
        </Button>
      }
    >
      {error && <div className="text-sm text-red-400">{error}</div>}
      {vin === undefined ? (
        <p className="text-sm text-neutral-500">
          Read the VIN via OBD Service 09 (often absent on early GEMS — the full
          VIN lives in the body/10AS module, not the ECM).
        </p>
      ) : vin ? (
        <div className="font-mono text-lg text-neutral-100">{vin}</div>
      ) : (
        <div className="text-sm text-amber-400">
          No VIN returned — this ECU doesn't answer Service 09 (expected on a
          Discovery 1 GEMS).
        </div>
      )}
    </Card>
  );
}

function SelfTestCard({ enabled }: { enabled: boolean }) {
  const [res, setRes] = useState<TestResult | null>(null);
  const [busy, setBusy] = useState(false);
  async function test() {
    setBusy(true);
    try {
      setRes(await api.testConnection());
    } catch (e) {
      setRes({
        ok: false,
        label: "",
        message: (e as Error).message,
        latencies_ms: [],
      });
    } finally {
      setBusy(false);
    }
  }
  const avg =
    res?.latencies_ms.length
      ? res.latencies_ms.reduce((a, b) => a + b, 0) / res.latencies_ms.length
      : null;
  return (
    <Card
      title="VCI Self-Test"
      actions={
        <Button onClick={test} disabled={!enabled || busy} variant="ghost">
          {busy ? "…" : "Test connection"}
        </Button>
      }
    >
      <p className="mb-2 text-xs text-neutral-600">
        LAN facility present — intended for potential future developments in
        dealership systems, and is not currently in use.
      </p>
      {res && (
        <div
          className={`text-sm ${res.ok ? "text-emerald-400" : "text-red-400"}`}
        >
          {res.ok ? "✓ " : "✗ "}
          {res.message}
          {avg !== null && (
            <span className="text-neutral-500"> · avg {avg.toFixed(1)} ms</span>
          )}
        </div>
      )}
    </Card>
  );
}

function ScenarioCard({
  status,
  onChange,
}: {
  status: Status | null;
  onChange: () => void;
}) {
  const [scenarios, setScenarios] = useState<string[]>([]);
  const [busy, setBusy] = useState(false);
  const isVirtual = status?.connection_kind === "virtual";
  useEffect(() => {
    api
      .scenarios()
      .then((r) => setScenarios(r.scenarios))
      .catch(() => setScenarios([]));
  }, []);
  async function pick(s: string) {
    setBusy(true);
    try {
      await api.setScenario(s);
      onChange();
    } finally {
      setBusy(false);
    }
  }
  return (
    <Card title="Emulator Scenario">
      {!isVirtual ? (
        <p className="text-sm text-neutral-500">
          Scenario selection applies to the virtual ECU only (you're on a real
          or remote ECU).
        </p>
      ) : (
        <div className="flex flex-wrap gap-2">
          {scenarios.map((s) => (
            <button
              key={s}
              onClick={() => pick(s)}
              disabled={busy}
              className={`rounded-lg px-3 py-1.5 text-sm ring-1 ring-white/10 disabled:opacity-50 ${
                status?.scenario === s
                  ? "bg-emerald-500 text-neutral-950"
                  : "bg-neutral-800 text-neutral-200 hover:bg-neutral-700"
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      )}
    </Card>
  );
}

function MapsCard() {
  const [maps, setMaps] = useState<unknown[]>([]);
  useEffect(() => {
    api
      .maps()
      .then((r) => setMaps(r.maps))
      .catch(() => setMaps([]));
  }, []);
  return (
    <Card title="EPROM Maps (reference)">
      <p className="mb-3 text-xs text-neutral-600">
        GEMS maps live on socketed UV-EPROMs (27C512 fuel / 27C1001 ignition) —
        read-only here; there is no K-line reflash (bench chip-swap only).
      </p>
      {maps.length === 0 ? (
        <div className="text-sm text-neutral-500">No maps loaded.</div>
      ) : (
        <ul className="grid grid-cols-2 gap-2 sm:grid-cols-3">
          {maps.map((m, i) => (
            <li
              key={i}
              className="rounded-lg bg-neutral-800/50 p-3 text-sm text-neutral-300 ring-1 ring-white/5"
            >
              {typeof m === "object" && m
                ? ((m as { name?: string }).name ?? JSON.stringify(m))
                : String(m)}
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
