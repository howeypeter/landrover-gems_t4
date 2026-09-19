// Thin typed client for the gems_t4 Python API. All calls are relative (/api/*)
// so the same build works in dev (Vite proxy) and in prod (served by FastAPI).

export interface Status {
  connected: boolean;
  connection_label: string;
  connection_kind: string;
  on_real_ecu: boolean;
  is_remote: boolean;
  scenario: string;
  adapter_firmware: string | null;
}

export interface Measure {
  name: string;
  value: number | string;
  unit: string;
  pid: number | null;
  pid_hex: string | null;
}

export interface Dtc {
  code: string;
  description: string;
  raw: number | string;
  state: string;
}

export interface Actuator {
  id: number;
  name: string;
  allowed_engine_running: boolean;
}

export interface ActuatorResult {
  actuator_id: number;
  ok: boolean;
  message: string;
}

export interface CodingField {
  key: string;
  name: string;
  writable: boolean;
  value: string | null;
}

export interface Immobiliser {
  mobilised: boolean;
  learn_mode: boolean;
}

export interface TestResult {
  ok: boolean;
  label: string;
  message: string;
  latencies_ms: number[];
}

export interface VinReconstruct {
  vin: string;
  valid: boolean;
  decode: {
    wmi: string;
    model_line: string;
    body: string;
    engine: string;
    transmission: string;
    year: number | null;
    plant: string;
    serial: string;
  };
}

export interface ConnectionBody {
  kind: string; // virtual | usb | ble | network
  com_port?: string | null;
  host?: string | null;
  tcp_port?: number;
  device?: string | null;
  allow_writes?: boolean;
  real_ecu?: boolean | null;
}

async function jsonOrThrow(res: Response) {
  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(body?.detail ?? `${res.status} ${res.statusText}`);
  }
  return body;
}

const post = (url: string, body?: unknown) =>
  fetch(url, {
    method: "POST",
    headers: body ? { "Content-Type": "application/json" } : {},
    body: body ? JSON.stringify(body) : undefined,
  }).then(jsonOrThrow);

export const api = {
  status: (): Promise<Status> => fetch("/api/status").then(jsonOrThrow),

  scenarios: (): Promise<{ scenarios: string[]; current: string }> =>
    fetch("/api/scenarios").then(jsonOrThrow),
  setScenario: (scenario: string) => post("/api/scenario", { scenario }),

  connect: (body: ConnectionBody) => post("/api/connection", body),
  testConnection: (): Promise<TestResult> => post("/api/connection/test"),
  disconnect: () => post("/api/disconnect"),

  live: (pids?: string[]): Promise<{ measures: Measure[] }> => {
    const q = pids?.length ? "?" + pids.map((p) => `pid=${p}`).join("&") : "";
    return fetch("/api/live" + q).then(jsonOrThrow);
  },

  dtcs: (): Promise<{ dtcs: Dtc[] }> => fetch("/api/dtcs").then(jsonOrThrow),
  clearDtcs: (): Promise<{ cleared: boolean }> => post("/api/dtcs/clear"),

  actuators: (): Promise<{ actuators: Actuator[] }> =>
    fetch("/api/actuators").then(jsonOrThrow),
  runActuator: (actuator_id: number, state: number): Promise<ActuatorResult> =>
    post("/api/actuator", { actuator_id, state }),

  vin: (): Promise<{ vin: string | null }> => fetch("/api/vin").then(jsonOrThrow),

  coding: (): Promise<{ fields: CodingField[] }> =>
    fetch("/api/coding").then(jsonOrThrow),
  writeCoding: (field: string, text: string) =>
    post("/api/coding", { field, text }),

  immobiliser: (): Promise<Immobiliser> =>
    fetch("/api/immobiliser").then(jsonOrThrow),

  maps: (): Promise<{ maps: unknown[] }> => fetch("/api/maps").then(jsonOrThrow),

  vinReconstruct: (body: {
    prefix8: string;
    year_code: string;
    last6: string;
    plant?: string;
  }): Promise<VinReconstruct> => post("/api/vin/reconstruct", body),
};

// Open the live-data WebSocket. Returns the socket; caller wires onmessage.
export function liveSocket(pids: string[], hz = 6): WebSocket {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const params = new URLSearchParams();
  pids.forEach((p) => params.append("pid", p));
  params.set("hz", String(hz));
  return new WebSocket(`${proto}://${location.host}/api/live/stream?${params}`);
}
