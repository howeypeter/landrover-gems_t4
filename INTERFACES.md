# gems_t4 — Build Contract (read before writing any code)

This file is the single source of truth for module boundaries and public APIs.
**Code to the interfaces described here, not to other agents' implementations.**
Several modules are built in parallel; they only fit together if everyone honors
these signatures exactly.

## Ground rules

- **Python 3.11+**, full type hints, `from __future__ import annotations` at top
  of every module. Docstrings on every public class/function.
- **Strict layering, imports only go downward:** `app → gems → protocol →
  transport`, and everything may import `protocol.messages` / `gems.types`.
  **`protocol` must NOT import `gems`; `transport` must NOT import `gems` or
  `protocol.client`.** (transport.virtual may import `protocol.framing` and
  `gems.ecu_base` only — see below.)
- **No I/O or `time.sleep` in `protocol/` or `gems/`.** Timing/sleep lives only
  in `transport/` real implementations. The virtual path must be instant.
- Every module ships with pytest tests under `tests/`. Prefer pure-function unit
  tests; use the virtual stack for integration.
- Keep it dependency-light: stdlib + `pyserial` (transport only) + `rich` (app
  only). No new deps without noting it.
- These already exist and are FIXED (do not modify): `protocol/messages.py`
  (`Request`, `Response`, `NRC`, `NegativeResponse`), `transport/base.py`
  (`Transport`, `InitResult`, `TransportError/Timeout/Closed`, `InitError`),
  `gems/types.py` (`Dtc`, `DtcState`, `Measure`, `ActuatorOutcome`),
  `gems/ecu_base.py` (`EcuHandler`).

## Module ownership (no two agents touch the same file)

| Agent | Files |
|---|---|
| 1 Protocol | `gems_t4/protocol/framing.py`, `timing.py`, `init.py`, `security.py`, `client.py`; `tests/test_framing.py`, `tests/test_client.py` |
| 2 GEMS data | `gems_t4/gems/dtc.py`, `livedata.py`, `actuators.py`, `ecu_profile.py`, `programming.py`; `tests/test_dtc.py`, `tests/test_livedata.py`, `tests/test_actuators.py` |
| 3 Virtual ECU | `gems_t4/gems/virtual_ecu.py`, `scenarios.py`; `tests/test_virtual_ecu.py`, `tests/test_scenarios.py` |
| 4 Transport | `gems_t4/transport/virtual.py`, `pico.py`, `ftdi.py`; `tests/test_virtual_transport.py`, `tests/test_pico_framing.py` |
| 5 App + integration | `gems_t4/app/cli.py`, `render.py`; `tests/test_integration.py` |
| 6 Firmware | `firmware/HOST_PROTOCOL.md`, `firmware/pico_kline/pico_kline.ino`, `firmware/README.md` |

## Wire format (stylized KWP2000 / ISO-14230)

A **frame** (what `Transport.send`/`receive` carry) is:

```
[FMT=0x80] [TGT] [SRC] [LEN] [ data ... ] [CS]
```

- `FMT` = `0x80` (address bytes present, explicit length byte).
- `TGT`/`SRC` = target/source addresses. Tester = `0xF1`. ECU = `0x10`.
- `LEN` = number of `data` bytes (1..255).
- `data` = the service bytes: request `[SID][payload...]`; positive response
  `[SID+0x40][payload...]`; negative response `[0x7F][SID][NRC]`.
- `CS` = **8-bit sum of every preceding byte in the frame, mod 256.**

## `protocol/framing.py` (Agent 1) — public API

```python
class FramingError(Exception): ...
class ChecksumError(FramingError): ...

TESTER_ADDRESS = 0xF1
DEFAULT_ECU_ADDRESS = 0x10

def checksum(payload: bytes) -> int                      # sum & 0xFF
def build_frame(data: bytes, *, target: int, source: int) -> bytes
def parse_frame(frame: bytes) -> tuple[int, int, bytes]  # (target, source, data); validates CS/len

def encode_request(req: Request, *, ecu_address: int = 0x10,
                   tester_address: int = 0xF1) -> bytes
def decode_request(frame: bytes) -> Request              # used by VirtualTransport
def encode_response(resp: Response, *, ecu_address: int = 0x10,
                    tester_address: int = 0xF1) -> bytes # used by VirtualTransport
def decode_response(frame: bytes, request_service: int) -> Response  # used by KwpClient
```

`encode_request`/`decode_response` are the client side; `decode_request`/
`encode_response` are the ECU/virtual side. All four must round-trip.

## Service / SID map (the stylized GEMS dialect) — FIXED

| SID | Name | Request `data` | Positive resp `data` |
|---|---|---|---|
| `0x10` | StartDiagnosticSession | `[session]` (`0x81` default, `0x85` programming) | `[session]` |
| `0x3E` | TesterPresent | `[]` | `[]` |
| `0x21` | ReadDataByLocalId | `[localId]` | `[localId][value bytes]` |
| `0x18` | ReadDTCByStatus | `[]` | `[count]` then count×`[hi][lo][status]` |
| `0x14` | ClearDiagnosticInformation | `[]` | `[]` |
| `0x27` | SecurityAccess | `[0x01]` seed / `[0x02][key…]` | seed: `[0x01][seed hi][seed lo]`; key ok: `[0x02]` |
| `0x30` | ActuatorControl (custom) | `[actuatorId][state]` | `[actuatorId][state]` (refusal = negative CONDITIONS_NOT_CORRECT) |
| `0x31` | StartRoutine (Security-Learn) | `[routineId][params]` | `[routineId][results]` |
| `0x3B` | WriteDataByLocalId (coding) | `[localId][value bytes]` | `[localId]` |

`0x31` routines (immobiliser Security-Learn, see `gems/immobiliser.py`):
`0x01` enter-learn (needs `0x27` unlock, else SECURITY_ACCESS_DENIED); `0x02
[hi][lo]` store BeCM code as new master (needs learn mode, else
REQUEST_SEQUENCE_ERROR); `0x03` status → `[0x03][mobilised][learn]`.
| `0x1A` | ReadEcuIdentification | `[idOption]` | `[idOption][data…]` |

Negative response for any unsupported SID/localId = `Response.negative(sid,
NRC.SERVICE_NOT_SUPPORTED or REQUEST_OUT_OF_RANGE)`.

## `protocol/client.py` (Agent 1) — `KwpClient`

Generic KWP only — **no GEMS knowledge, no import of `gems`**.

```python
class KwpClient:
    def __init__(self, transport: Transport, *, ecu_address: int = 0x10,
                 tester_address: int = 0xF1, timing: TimingPolicy | None = None): ...
    def connect(self, mode: str = "slow") -> InitResult   # transport.open()+init()
    def close(self) -> None                               # transport.close()
    def request(self, req: Request, *, timeout: float | None = None,
                expect_positive: bool = False) -> Response
    # convenience wrappers (return Response unless noted):
    def start_session(self, session: int = 0x81) -> Response
    def tester_present(self) -> None
    def read_data_by_local_id(self, local_id: int) -> bytes    # returns value bytes; raises NegativeResponse
    def read_dtcs_raw(self) -> bytes                           # payload of the 0x18 response
    def clear_dtcs(self) -> Response
    def security_access(self, key_fn) -> None                  # 0x27 seed→key_fn(seed)→send
    def write_data_by_local_id(self, local_id: int, value: bytes) -> Response
    def actuator(self, actuator_id: int, state: int) -> Response
```

`timing.py` defines `TimingPolicy` (dataclass of P1..P4 + response timeout, all
seconds/floats, with sane KWP defaults) — used by real transports; the client
just passes a default timeout to `transport.receive`. `init.py` holds init
constants/helpers (addresses 0x33 generic / 0x16 Rover, 5-baud vs fast) that the
real transport/firmware use; keep it pure/data-only. `security.py` holds a
toy/opaque seed→key routine `compute_key(seed: int) -> int` (documented as a
placeholder; real GEMS key is not public) used by both the client helper and the
virtual ECU.

## `gems/` data + services (Agent 2)

Owns all GEMS tables and the encode/decode used by BOTH the client side and the
virtual ECU. May import `protocol.messages`, `protocol.client`, `gems.types`.

`livedata.py` — the $61 records:
```python
@dataclass(frozen=True)
class ParamDef:
    local_id: int
    name: str
    unit: str
    nbytes: int                 # 1 or 2
    scale: float = 1.0
    offset: float = 0.0
    signed: bool = False
    def encode(self, value: float) -> bytes     # engineering→raw bytes (big-endian)
    def decode(self, raw: bytes) -> Measure      # raw bytes→Measure

PARAMETERS: dict[int, ParamDef]          # ~35 params from gems-data-catalog.md
def decode_measure(local_id: int, raw: bytes) -> Measure
def read_all(client: KwpClient, ids: list[int] | None = None) -> list[Measure]
```

`dtc.py` — the fault table + client helpers:
```python
@dataclass(frozen=True)
class DtcDef:
    code: str            # "P0118"
    raw: int             # 2-byte internal id the emulator uses
    description: str
DTC_TABLE: dict[int, DtcDef]             # keyed by raw; GEMS up-to-99MY codes only
def by_code(code: str) -> DtcDef
def decode_dtc_response(payload: bytes) -> list[Dtc]   # parses the 0x18 payload
def encode_dtc_response(dtcs: list[Dtc]) -> bytes      # builds the 0x18 payload (ECU side)
def read_dtcs(client: KwpClient) -> list[Dtc]
def clear_dtcs(client: KwpClient) -> None
```

`actuators.py`:
```python
@dataclass(frozen=True)
class ActuatorDef:
    actuator_id: int
    name: str
    allowed_engine_running: bool     # False → refuse while engine runs
ACTUATORS: dict[int, ActuatorDef]    # MIL, O2 heater, fuel pump relay, A/C grant, condenser fan
def run(client: KwpClient, actuator_id: int, state: int) -> ActuatorOutcome
```

`ecu_profile.py` — `GEMS_PROFILE` with ecu_address=0x10, keybytes, supported
SIDs/local ids, vehicle label. `programming.py` — coding settings map
(read/edit/write: VIN last6, dealer id, 4.0/4.6 select, transmission; read-only:
market, part no.) + a gated `write_coding(client, field, value, *, backup,
verify=True)` skeleton with the safety gates (backup+verify+confirm) — logic may
be stubbed but the gate structure must be real.

## `gems/virtual_ecu.py` + `scenarios.py` (Agent 3)

```python
class VirtualEcu:                        # implements EcuHandler
    def __init__(self, scenario: Scenario | None = None, profile=GEMS_PROFILE): ...
    def handle(self, request: Request) -> Response
    def tick(self, dt: float) -> None    # warm-up curve, idle hunt
    # holds: engine state (rpm, coolant temp, battery, throttle...), stored DTCs,
    # session state, security-unlocked flag, engine_running bool.
```
Uses Agent 2's `livedata.PARAMETERS[id].encode(...)` to build $61 responses,
`dtc.encode_dtc_response(...)` for 0x18, `actuators.ACTUATORS` for interlocks
(refuse fuel-pump etc. while `engine_running` → negative CONDITIONS_NOT_CORRECT),
and `security.compute_key` to validate 0x27.

```python
class Scenario(Protocol):
    name: str
    def stored_dtcs(self) -> list[Dtc]
    def perturb(self, state: dict) -> None      # mutate live state coherently
    def blocks_actuator(self, actuator_id: int) -> bool
SCENARIOS: dict[str, Scenario]   # "healthy", "coolant_sensor", "misfire_cyl3", "lambda_heater"
```
Each scenario makes DTCs + live anomalies + actuator outcomes mutually
consistent (e.g. `coolant_sensor` → P0118 + coolant reads −40°C/high, etc.).

## `transport/` implementations (Agent 4)

`virtual.py`:
```python
class VirtualTransport(Transport):
    def __init__(self, ecu: EcuHandler, *, latency: float = 0.0): ...
    # send(frame): decode_request→ecu.handle→encode_response, buffer it
    # receive(): return buffered response (respect optional latency via a hook,
    #            but DEFAULT latency=0.0 and NO real sleep in tests)
```
May import `protocol.framing` and `gems.ecu_base` only. `pico.py`:
`PicoAdapterTransport(Transport)` — pyserial USB-CDC client speaking the host
protocol in `firmware/HOST_PROTOCOL.md` (see below). `ftdi.py`: `FtdiKlineTransport`
stub with the intended approach documented (pyserial + latency-timer note); may
raise NotImplementedError for now but must define the class + docstring.

## Host protocol (Agents 4 & 6 share this) — FIXED

PC↔Pico over USB-CDC serial, binary, little-endian, COBS-free simple framing:

```
Host→Pico:  0xA5 <cmd> <len> <payload...> <crc8>
Pico→Host:  0x5A <status> <len> <payload...> <crc8>
```
- `crc8` = simple XOR of `cmd/status`,`len`, and all payload bytes.
- Commands: `0x01 PING` → status `0x00`, payload = version string;
  `0x02 INIT` payload `[address][mode 0=slow/1=fast]` → status ok, payload =
  keybytes; `0x03 SEND_RECV` payload = one KWP frame → status ok, payload = the
  KWP response frame (Pico handles K-line timing + echo); `0x04 SET_TIMING`
  payload = P1..P4 as 4×uint16 ms.
- `status`: `0x00 OK`, `0x01 TIMEOUT`, `0x02 BUS_ERROR`, `0x03 BAD_REQUEST`.
Agent 4's `pico.py` and Agent 6's firmware must both implement exactly this.
Agent 6 also documents it fully in `firmware/HOST_PROTOCOL.md`.

### Host protocol over TCP (added 2026-07-11)

The same frames also run over a TCP socket (default port **9141**):
`transport/tcp.py` `TcpTransport(host, port, *, timeout=5.0,
allow_writes=False)` is the client (a fourth `Transport`; `is_wireless=True`),
and `app/server.py` `TcpFrameServer` / `gems_t4 serve` is the endpoint
(virtual ECU, or a raw byte bridge to a USB Pico with `--port`). Write policy:
`KwpClient.request` raises `WirelessWriteRefused` for SIDs `$30/$31/$3B` on a
transport with `is_wireless=True` unless it has `allow_writes=True`
(`WIRELESS_BLOCKED_SERVICES` in `protocol/client.py`); `$14` clear stays
allowed. A future WiFi Pico implements exactly what `TcpFrameServer` answers.

## `app/cli.py` + `render.py` (Agent 5)

Rich-based CLI, entry point `main()` (wired in pyproject as `gems_t4`; run via
`python -m gems_t4`). Commands (use argparse or a tiny hand-rolled dispatch; no
new deps): `gems_t4 live --fake [--scenario NAME]`, `dtc read --fake`, `dtc clear --fake`,
`actuator <name> --fake`, `scenarios` (list). `--fake` builds
`VirtualEcu(scenario) → VirtualTransport → KwpClient`; a `--port COM3` path
builds a `PicoAdapterTransport` instead (may be a documented TODO if no hardware).
`render.py` holds Rich tables/gauges + the "Communicating with ECU…" flavor.
`tests/test_integration.py` drives the full virtual stack end-to-end: connect →
read DTCs (per scenario) → read live data → run an actuator (incl. a refusal) →
clear DTCs, asserting coherent cross-module behavior.

## Testing

- All tests must pass under `pytest` from the repo root using the project venv.
- No test may require real hardware or a real serial port.
- Aim for meaningful assertions (round-trip framing, scenario coherence,
  interlock refusals), not just smoke tests.
