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

export const api = {
  status: (): Promise<Status> => fetch("/api/status").then(jsonOrThrow),

  connect: (body: ConnectionBody) =>
    fetch("/api/connection", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    }).then(jsonOrThrow),

  disconnect: () => fetch("/api/disconnect", { method: "POST" }).then(jsonOrThrow),

  live: (pids?: string[]): Promise<{ measures: Measure[] }> => {
    const q = pids?.length ? "?" + pids.map((p) => `pid=${p}`).join("&") : "";
    return fetch("/api/live" + q).then(jsonOrThrow);
  },
};

// Open the live-data WebSocket. Returns the socket; caller wires onmessage.
export function liveSocket(pids: string[], hz = 6): WebSocket {
  const proto = location.protocol === "https:" ? "wss" : "ws";
  const params = new URLSearchParams();
  pids.forEach((p) => params.append("pid", p));
  params.set("hz", String(hz));
  return new WebSocket(`${proto}://${location.host}/api/live/stream?${params}`);
}
