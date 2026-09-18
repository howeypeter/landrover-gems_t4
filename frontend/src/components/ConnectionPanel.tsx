import { useState } from "react";
import { api, type Status } from "../api";

interface Props {
  status: Status | null;
  onChange: () => void;
}

const KINDS = [
  { id: "virtual", label: "Virtual (emulator)" },
  { id: "ble", label: "Bluetooth LE" },
  { id: "usb", label: "USB (COM port)" },
  { id: "network", label: "Network (WiFi/serve)" },
];

export default function ConnectionPanel({ status, onChange }: Props) {
  const [kind, setKind] = useState("ble");
  const [device, setDevice] = useState("gems-pico");
  const [comPort, setComPort] = useState("COM4");
  const [host, setHost] = useState("192.168.1.50");
  const [tcpPort, setTcpPort] = useState(9141);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const connected = status?.connected && status.connection_kind !== "virtual";

  async function connect() {
    setBusy(true);
    setError(null);
    try {
      await api.connect({
        kind,
        device: kind === "ble" ? device : null,
        com_port: kind === "usb" ? comPort : null,
        host: kind === "network" ? host : null,
        tcp_port: tcpPort,
        real_ecu: kind !== "virtual",
      });
      onChange();
    } catch (e) {
      setError(String((e as Error).message));
    } finally {
      setBusy(false);
    }
  }

  async function disconnect() {
    setBusy(true);
    setError(null);
    try {
      await api.disconnect();
      onChange();
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="rounded-2xl bg-neutral-900/70 ring-1 ring-white/5 p-5">
      <div className="mb-4 flex items-center gap-3">
        <span
          className={`inline-block h-2.5 w-2.5 rounded-full ${
            connected ? "bg-emerald-400" : "bg-neutral-600"
          }`}
        />
        <div className="text-sm">
          <div className="font-medium text-neutral-200">
            {status?.connection_label ?? "…"}
          </div>
          <div className="text-neutral-500">
            {status?.adapter_firmware ?? (status?.on_real_ecu ? "" : "emulated ECU")}
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        <label className="flex flex-col text-xs text-neutral-400">
          Connection
          <select
            className="mt-1 rounded-lg bg-neutral-800 px-3 py-2 text-sm text-neutral-100 ring-1 ring-white/10"
            value={kind}
            onChange={(e) => setKind(e.target.value)}
          >
            {KINDS.map((k) => (
              <option key={k.id} value={k.id}>
                {k.label}
              </option>
            ))}
          </select>
        </label>

        {kind === "ble" && (
          <Field label="Device" value={device} onChange={setDevice} />
        )}
        {kind === "usb" && (
          <Field label="COM port" value={comPort} onChange={setComPort} />
        )}
        {kind === "network" && (
          <>
            <Field label="Host / IP" value={host} onChange={setHost} />
            <Field
              label="Port"
              value={String(tcpPort)}
              onChange={(v) => setTcpPort(Number(v) || 9141)}
              width="w-20"
            />
          </>
        )}

        <button
          onClick={connect}
          disabled={busy}
          className="rounded-lg bg-emerald-500 px-4 py-2 text-sm font-semibold text-neutral-950 hover:bg-emerald-400 disabled:opacity-50"
        >
          {busy ? "…" : "Connect"}
        </button>
        {connected && (
          <button
            onClick={disconnect}
            disabled={busy}
            className="rounded-lg bg-neutral-700 px-4 py-2 text-sm font-semibold text-neutral-100 hover:bg-neutral-600 disabled:opacity-50"
          >
            Disconnect
          </button>
        )}
      </div>

      {error && <div className="mt-3 text-sm text-red-400">{error}</div>}
    </div>
  );
}

function Field({
  label,
  value,
  onChange,
  width = "w-40",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  width?: string;
}) {
  return (
    <label className="flex flex-col text-xs text-neutral-400">
      {label}
      <input
        className={`mt-1 rounded-lg bg-neutral-800 px-3 py-2 text-sm text-neutral-100 ring-1 ring-white/10 ${width}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </label>
  );
}
