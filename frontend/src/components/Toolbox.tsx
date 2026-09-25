import { useEffect, useState } from "react";
import { api, type Status, type TestResult, type VinReconstruct } from "../api";
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
      <VinReconstructCard />
      <WifiCard />
      <SelfTestCard enabled={enabled} />
      <ScenarioCard status={status} onChange={onChange} />
      <MapsCard />
    </div>
  );
}

// Manage the Pico adapter's stored WiFi credentials (host cmds 0x06/0x07), the
// same as `gems_t4 kline set-wifi`/`wifi-status`. The API host opens a fresh
// USB/BLE link to the Pico for this, so it must physically reach the adapter —
// and the Backend must NOT currently hold that same Pico (disconnect first).
function WifiCard() {
  const [transport, setTransport] = useState("usb"); // usb | ble | network
  const [device, setDevice] = useState("gems-pico");
  const [comPort, setComPort] = useState("");
  const [host, setHost] = useState("");
  const [tcpPort, setTcpPort] = useState("9141");
  const [ssid, setSsid] = useState("");
  const [password, setPassword] = useState("");
  const [showPw, setShowPw] = useState(false);
  const [msg, setMsg] = useState<{ ok: boolean; text: string } | null>(null);
  const [busy, setBusy] = useState<null | "set" | "status">(null);

  function body() {
    if (transport === "ble")
      return { kind: "ble", device: device.trim() || "gems-pico" };
    if (transport === "network")
      return {
        kind: "network",
        host: host.trim(),
        tcp_port: Number(tcpPort) || 9141,
      };
    return { kind: "usb", com_port: comPort.trim() || null };
  }

  async function doStatus() {
    setBusy("status");
    setMsg(null);
    try {
      const r = await api.wifiStatus(body());
      // Firmware >=3.1.0: "connected <ip> <mac> <ssid>" | "offline <mac> (creds
      // set: <ssid>)" | "no-creds <mac>" (MAC before SSID; SSID last since it can
      // contain spaces). Older firmware omits the MAC. Pull the SSID into the
      // field (password is write-only and never comes back).
      const mac = r.status.match(/[0-9A-Fa-f]{2}(?::[0-9A-Fa-f]{2}){5}/)?.[0];
      const m =
        r.status.match(/^connected \S+ (?:[0-9A-Fa-f:]{17} )?(.+)$/) ??
        r.status.match(/creds set:\s*(.+?)\)?$/);
      if (m?.[1]) setSsid(m[1].trim());
      setMsg({ ok: true, text: `WiFi: ${r.status}` + (mac ? `  (MAC ${mac})` : "") });
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    } finally {
      setBusy(null);
    }
  }

  async function doSet() {
    setBusy("set");
    setMsg(null);
    try {
      const r = await api.wifiSet({ ...body(), ssid: ssid.trim(), password });
      setMsg({
        ok: true,
        text:
          `Saved SSID '${r.ssid}' to the Pico (joins on next boot/reconnect).` +
          (r.status ? ` WiFi: ${r.status}` : ""),
      });
    } catch (e) {
      setMsg({ ok: false, text: (e as Error).message });
    } finally {
      setBusy(null);
    }
  }

  const canSet = ssid.trim().length > 0 && busy === null;

  return (
    <Card title="Pico WiFi Credentials">
      <p className="mb-3 text-xs text-neutral-600">
        Store the WiFi SSID/password on the adapter (LittleFS) so it can serve
        the host protocol over TCP — no reflash needed. The API host must reach
        the Pico over USB or BLE, and it must not be in use as your active
        connection.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <Picker
          label="Via"
          value={transport}
          onChange={setTransport}
          opts={[
            { code: "usb", label: "USB" },
            { code: "ble", label: "Bluetooth LE" },
            { code: "network", label: "Network (WiFi)" },
          ]}
        />
        {transport === "ble" && (
          <label className="flex flex-col text-xs text-neutral-400">
            BLE name
            <input
              className="mt-1 w-40 rounded-lg bg-neutral-800 px-3 py-2 text-sm text-neutral-100 ring-1 ring-white/10"
              value={device}
              onChange={(e) => setDevice(e.target.value)}
            />
          </label>
        )}
        {transport === "usb" && (
          <label className="flex flex-col text-xs text-neutral-400">
            COM port (auto if blank)
            <input
              className="mt-1 w-40 rounded-lg bg-neutral-800 px-3 py-2 text-sm text-neutral-100 ring-1 ring-white/10"
              value={comPort}
              placeholder="COM5"
              onChange={(e) => setComPort(e.target.value)}
            />
          </label>
        )}
        {transport === "network" && (
          <>
            <label className="flex flex-col text-xs text-neutral-400">
              Host / IP
              <input
                className="mt-1 w-40 rounded-lg bg-neutral-800 px-3 py-2 text-sm text-neutral-100 ring-1 ring-white/10"
                value={host}
                placeholder="192.168.1.138"
                onChange={(e) => setHost(e.target.value)}
              />
            </label>
            <label className="flex flex-col text-xs text-neutral-400">
              TCP port
              <input
                className="mt-1 w-24 rounded-lg bg-neutral-800 px-3 py-2 text-sm text-neutral-100 ring-1 ring-white/10"
                value={tcpPort}
                onChange={(e) => setTcpPort(e.target.value)}
              />
            </label>
          </>
        )}
        <Button onClick={doStatus} disabled={busy !== null} variant="ghost">
          {busy === "status" ? "…" : "Status"}
        </Button>
      </div>

      <div className="mt-3 flex flex-wrap items-end gap-3">
        <label className="flex flex-col text-xs text-neutral-400">
          SSID
          <input
            className="mt-1 w-52 rounded-lg bg-neutral-800 px-3 py-2 text-sm text-neutral-100 ring-1 ring-white/10"
            value={ssid}
            onChange={(e) => setSsid(e.target.value)}
          />
        </label>
        <label className="flex flex-col text-xs text-neutral-400">
          Password
          <input
            type={showPw ? "text" : "password"}
            className="mt-1 w-52 rounded-lg bg-neutral-800 px-3 py-2 text-sm text-neutral-100 ring-1 ring-white/10"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
        </label>
        <label className="flex items-center gap-1.5 pb-2 text-xs text-neutral-400">
          <input
            type="checkbox"
            checked={showPw}
            onChange={(e) => setShowPw(e.target.checked)}
          />
          Show
        </label>
        <Button onClick={doSet} disabled={!canSet} variant="primary">
          {busy === "set" ? "…" : "Set WiFi"}
        </Button>
      </div>

      {msg && (
        <div
          className={`mt-3 text-sm ${msg.ok ? "text-emerald-400" : "text-red-400"}`}
        >
          {msg.text}
        </div>
      )}
    </Card>
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

// Reconstruct the full 17-char NAS VIN from the last-6 (which the ECM doesn't
// store on a Disco 1 — it's in the 10AS, or read off the plate) plus the known
// vehicle attributes. The check digit is computed server-side (single source of
// truth = gems_t4/gems/vin.py), so the result is self-validating.
const ENGINES = [
  { code: "2", label: "4.0 V8 (GEMS)" },
  { code: "4", label: "4.6 V8" },
];
const TRANS = [
  { code: "4", label: "ZF auto" },
  { code: "8", label: "5-sp manual" },
];
const EMISSIONS = [
  { code: "Y", label: "Federal (49-state)" },
  { code: "N", label: "California ('95–96)" },
];
const YEARS = [
  { code: "T", label: "1996" },
  { code: "V", label: "1997" },
  { code: "W", label: "1998" },
  { code: "X", label: "1999" },
];

function VinReconstructCard() {
  const [engine, setEngine] = useState("2");
  const [trans, setTrans] = useState("4");
  const [emissions, setEmissions] = useState("Y");
  const [year, setYear] = useState("V");
  const [last6, setLast6] = useState("");
  const [result, setResult] = useState<VinReconstruct | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function build() {
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      // prefix8 = pos 1-8: S A L J <emissions> 1 <engine> <trans>
      const prefix8 = `SALJ${emissions}1${engine}${trans}`;
      setResult(
        await api.vinReconstruct({
          prefix8,
          year_code: year,
          last6: last6.trim().toUpperCase(),
          plant: "A",
        }),
      );
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const canBuild = last6.trim().length === 6;

  return (
    <Card title="VIN Reconstruction (Discovery 1)">
      <p className="mb-3 text-xs text-neutral-600">
        The full VIN ≈ known 11-char prefix + the last-6 serial. The ECM doesn't
        store the last-6 on a Disco 1 — read it from the 10AS or the VIN plate,
        enter it below, and the tool assembles + check-digit-validates the rest.
      </p>
      <div className="flex flex-wrap items-end gap-3">
        <Picker label="Engine" value={engine} onChange={setEngine} opts={ENGINES} />
        <Picker label="Gearbox" value={trans} onChange={setTrans} opts={TRANS} />
        <Picker label="Emissions" value={emissions} onChange={setEmissions} opts={EMISSIONS} />
        <Picker label="Year" value={year} onChange={setYear} opts={YEARS} />
        <label className="flex flex-col text-xs text-neutral-400">
          Last 6
          <input
            className="mt-1 w-28 rounded-lg bg-neutral-800 px-3 py-2 font-mono text-sm uppercase text-neutral-100 ring-1 ring-white/10"
            value={last6}
            maxLength={6}
            placeholder="123456"
            onChange={(e) => setLast6(e.target.value)}
          />
        </label>
        <Button onClick={build} disabled={!canBuild || busy} variant="primary">
          {busy ? "…" : "Reconstruct"}
        </Button>
      </div>

      {error && <div className="mt-3 text-sm text-red-400">{error}</div>}

      {result && (
        <div className="mt-4 rounded-xl bg-neutral-800/50 p-4 ring-1 ring-white/5">
          <div className="flex items-center gap-3">
            <span className="font-mono text-lg tracking-wider text-neutral-100">
              {result.vin}
            </span>
            <span
              className={`rounded-full px-2 py-0.5 text-xs ring-1 ${
                result.valid
                  ? "bg-emerald-500/10 text-emerald-300 ring-emerald-500/20"
                  : "bg-red-500/10 text-red-300 ring-red-500/20"
              }`}
            >
              {result.valid ? "✓ check digit valid" : "✗ check digit invalid"}
            </span>
          </div>
          <div className="mt-2 grid grid-cols-2 gap-x-6 gap-y-1 text-xs text-neutral-400 sm:grid-cols-3">
            <span>{result.decode.model_line}</span>
            <span>{result.decode.engine}</span>
            <span>{result.decode.transmission}</span>
            <span>{result.decode.year}</span>
            <span>{result.decode.plant}</span>
            <span>serial {result.decode.serial}</span>
          </div>
          <div className="mt-3 text-[11px] text-amber-400/80">
            Reconstructed — verify against the vehicle's VIN plate before relying
            on it. NAS positions assumed; identification aid only.
          </div>
        </div>
      )}
    </Card>
  );
}

function Picker({
  label,
  value,
  onChange,
  opts,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  opts: { code: string; label: string }[];
}) {
  return (
    <label className="flex flex-col text-xs text-neutral-400">
      {label}
      <select
        className="mt-1 rounded-lg bg-neutral-800 px-3 py-2 text-sm text-neutral-100 ring-1 ring-white/10"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {opts.map((o) => (
          <option key={o.code} value={o.code}>
            {o.label}
          </option>
        ))}
      </select>
    </label>
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
