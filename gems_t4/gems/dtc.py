"""GEMS diagnostic trouble codes: the fault table plus the encode/decode used by
both the client side (parsing an ``0x18`` response) and the virtual ECU (building
one).

The DTC table holds only the **up-to-99MY GEMS** codes documented in
``memory/research/gems-data-catalog.md`` — the 99MY-up Thor/Disco-II CAN-era
codes are deliberately excluded.

Wire format for the ``ReadDTCByStatus`` (``0x18``) response payload (see the
INTERFACES.md service map)::

    [count] then count × [raw-hi][raw-lo][status]

where ``raw`` is the ECU's internal 2-byte identifier for the code and
``status`` is one of the :class:`~gems_t4.gems.types.DtcState` byte encodings
below. There is **no I/O and no sleep** in this module; the client helpers merely
call the generic :class:`~gems_t4.protocol.client.KwpClient` methods.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from gems_t4.gems.types import Dtc, DtcState

if TYPE_CHECKING:  # pragma: no cover - import only for type checking
    from gems_t4.protocol.client import KwpClient


@dataclass(frozen=True, slots=True)
class DtcDef:
    """One entry in the GEMS fault table.

    ``code`` is the 5-char P-code the technician sees (e.g. ``"P0118"``),
    ``raw`` is the 2-byte internal identifier the emulator uses on the wire, and
    ``description`` is the RAVE/TestBook-style text.
    """

    code: str
    raw: int
    description: str


#: Byte encoding of a stored fault's :class:`DtcState` in the ``0x18`` payload.
_STATE_TO_BYTE: dict[DtcState, int] = {
    DtcState.ACTIVE: 0x24,   # test failed, confirmed (active)
    DtcState.STORED: 0x20,   # test failed at some point (stored/historic)
    DtcState.PENDING: 0x04,  # test failed this cycle (pending)
}
_BYTE_TO_STATE: dict[int, DtcState] = {v: k for k, v in _STATE_TO_BYTE.items()}


def _state_from_byte(status: int) -> DtcState:
    """Map a status byte back to a :class:`DtcState`, tolerating unknown bytes."""
    if status in _BYTE_TO_STATE:
        return _BYTE_TO_STATE[status]
    # Unknown status byte: fall back on the "active" bit (0x04) heuristic.
    return DtcState.ACTIVE if status & 0x04 else DtcState.STORED


def _state_to_byte(state: DtcState) -> int:
    return _STATE_TO_BYTE.get(state, 0x20)


# ---------------------------------------------------------------------------
# The GEMS fault table (up-to-99MY block only).
#
# raw ids are assigned coherently: the high byte groups the fault family and the
# low byte enumerates within it, so the emulator has a stable 2-byte handle for
# every code and no two codes collide.
# ---------------------------------------------------------------------------
_DEFS: tuple[DtcDef, ...] = (
    # --- Crank / cam position (0x01xx) ---
    DtcDef("P0335", 0x0101, "Crankshaft position sensor circuit"),
    DtcDef("P0336", 0x0102, "Crankshaft position sensor range/performance"),
    DtcDef("P0340", 0x0103, "Camshaft position sensor circuit"),
    # --- Throttle position (0x02xx) ---
    DtcDef("P0121", 0x0201, "Throttle position sensor range/performance"),
    DtcDef("P0122", 0x0202, "Throttle position sensor low input"),
    DtcDef("P0123", 0x0203, "Throttle position sensor high input"),
    # --- Coolant temperature (0x03xx) ---
    DtcDef("P0116", 0x0301, "Coolant temperature sensor range/performance"),
    DtcDef("P0117", 0x0302, "Coolant temperature sensor low input"),
    DtcDef("P0118", 0x0303, "Coolant temperature sensor high input"),
    DtcDef("P0125", 0x0304, "Insufficient coolant temp for closed loop"),
    # --- Fuel temperature (GEMS party piece, 0x04xx) ---
    DtcDef("P0181", 0x0401, "Fuel temperature sensor range/performance"),
    DtcDef("P0182", 0x0402, "Fuel temperature sensor low input"),
    DtcDef("P0183", 0x0403, "Fuel temperature sensor high input"),
    # --- Knock sensors bank A / bank B (0x05xx) ---
    DtcDef("P0326", 0x0501, "Knock sensor 1 (bank A) range/performance"),
    DtcDef("P0327", 0x0502, "Knock sensor 1 (bank A) low input"),
    DtcDef("P0328", 0x0503, "Knock sensor 1 (bank A) high input"),
    DtcDef("P0331", 0x0504, "Knock sensor 2 (bank B) range/performance"),
    DtcDef("P0332", 0x0505, "Knock sensor 2 (bank B) low input"),
    DtcDef("P0333", 0x0506, "Knock sensor 2 (bank B) high input"),
    # --- Injector circuits per cylinder (0x06xx) ---
    DtcDef("P0201", 0x0601, "Injector circuit cylinder 1"),
    DtcDef("P0202", 0x0602, "Injector circuit cylinder 2"),
    DtcDef("P0203", 0x0603, "Injector circuit cylinder 3"),
    DtcDef("P0204", 0x0604, "Injector circuit cylinder 4"),
    DtcDef("P0205", 0x0605, "Injector circuit cylinder 5"),
    DtcDef("P0206", 0x0606, "Injector circuit cylinder 6"),
    DtcDef("P0207", 0x0607, "Injector circuit cylinder 7"),
    DtcDef("P0208", 0x0608, "Injector circuit cylinder 8"),
    DtcDef("P1201", 0x0611, "Injector cylinder 1 open/ground short"),
    DtcDef("P1202", 0x0612, "Injector cylinder 2 open/ground short"),
    DtcDef("P1203", 0x0613, "Injector cylinder 3 open/ground short"),
    DtcDef("P1204", 0x0614, "Injector cylinder 4 open/ground short"),
    DtcDef("P1205", 0x0615, "Injector cylinder 5 open/ground short"),
    DtcDef("P1206", 0x0616, "Injector cylinder 6 open/ground short"),
    DtcDef("P1207", 0x0617, "Injector cylinder 7 open/ground short"),
    DtcDef("P1208", 0x0618, "Injector cylinder 8 open/ground short"),
    # --- IACV / idle stepper (0x07xx) ---
    DtcDef("P0506", 0x0701, "Idle control system RPM lower than expected"),
    DtcDef("P0507", 0x0702, "Idle control system RPM higher than expected"),
    DtcDef("P1508", 0x0703, "IACV stepper motor circuit open"),
    DtcDef("P1509", 0x0704, "IACV stepper motor circuit short"),
    # --- O2 sensor signal, bank A/B up/downstream (0x08xx) ---
    DtcDef("P0130", 0x0801, "O2 sensor circuit bank 1 sensor 1 (upstream)"),
    DtcDef("P0136", 0x0802, "O2 sensor circuit bank 1 sensor 2 (downstream)"),
    DtcDef("P0150", 0x0803, "O2 sensor circuit bank 2 sensor 1 (upstream)"),
    DtcDef("P0156", 0x0804, "O2 sensor circuit bank 2 sensor 2 (downstream)"),
    # --- O2 heaters (lambda-heater scenario, 0x09xx) ---
    DtcDef("P1185", 0x0901, "O2 sensor heater bank 1 sensor 1 (upstream)"),
    DtcDef("P1186", 0x0902, "O2 sensor heater bank 1 sensor 2"),
    DtcDef("P1187", 0x0903, "O2 sensor heater bank 2 sensor 1"),
    DtcDef("P1188", 0x0904, "O2 sensor heater bank 2 sensor 2"),
    DtcDef("P1189", 0x0905, "O2 sensor heater circuit (upstream)"),
    DtcDef("P1190", 0x0906, "O2 sensor heater circuit (upstream)"),
    DtcDef("P1191", 0x0907, "O2 sensor heater bank 1 sensor 1 (downstream)"),
    DtcDef("P1192", 0x0908, "O2 sensor heater bank 1 sensor 2 (downstream)"),
    DtcDef("P1193", 0x0909, "O2 sensor heater bank 2 sensor 1 (downstream)"),
    DtcDef("P1194", 0x090A, "O2 sensor heater bank 2 sensor 2 (downstream)"),
    DtcDef("P1195", 0x090B, "O2 sensor heater circuit (downstream)"),
    DtcDef("P1196", 0x090C, "O2 sensor heater circuit (downstream)"),
    # --- Fuel trims (0x0Axx) ---
    DtcDef("P0171", 0x0A01, "System too lean (bank 1)"),
    DtcDef("P0174", 0x0A02, "System too lean (bank 2)"),
    DtcDef("P0172", 0x0A03, "System too rich (bank 1)"),
    DtcDef("P0175", 0x0A04, "System too rich (bank 2)"),
    DtcDef("P1171", 0x0A05, "Fuel trim malfunction both banks"),
    DtcDef("P1172", 0x0A06, "Fuel trim malfunction both banks"),
    # --- Catalyst (0x0Bxx) ---
    DtcDef("P0420", 0x0B01, "Catalyst efficiency below threshold (bank 1)"),
    DtcDef("P0430", 0x0B02, "Catalyst efficiency below threshold (bank 2)"),
    # --- EVAP (NAS, 0x0Cxx) ---
    DtcDef("P1440", 0x0C01, "EVAP system purge valve stuck open"),
    DtcDef("P0441", 0x0C02, "EVAP system incorrect purge flow"),
    DtcDef("P0442", 0x0C03, "EVAP system small leak detected"),
    DtcDef("P0443", 0x0C04, "EVAP purge control valve circuit"),
    DtcDef("P0446", 0x0C05, "EVAP vent control circuit"),
    DtcDef("P0448", 0x0C06, "EVAP vent control circuit shorted"),
    DtcDef("P0451", 0x0C07, "EVAP pressure sensor range/performance"),
    DtcDef("P0452", 0x0C08, "EVAP pressure sensor low input"),
    DtcDef("P0453", 0x0C09, "EVAP pressure sensor high input"),
    DtcDef("P1447", 0x0C0A, "EVAP system leak / flow monitor"),
    # --- Gearbox interface (0x0Dxx) ---
    DtcDef("P1775", 0x0D01, "Gearbox torque reduction signal circuit"),
    DtcDef("P1776", 0x0D02, "Gearbox torque reduction signal range"),
    DtcDef("P1777", 0x0D03, "Gearbox interface malfunction"),
    # --- ECM / anti-theft (0x0Exx) ---
    DtcDef("P0605", 0x0E01, "Internal control module ROM error"),
    DtcDef("P1607", 0x0E02, "ECM internal fault"),
    DtcDef("P1621", 0x0E03, "Immobiliser code word memory fault"),
    DtcDef("P1622", 0x0E04, "Immobiliser ID not learned"),
    DtcDef("P1623", 0x0E05, "Immobiliser signal line fault"),
    DtcDef("P1666", 0x0E06, "ECM anti-theft fault"),
    DtcDef("P1667", 0x0E07, "ECM anti-theft fault"),
    DtcDef("P1668", 0x0E08, "ECM anti-theft fault"),
    DtcDef("P1672", 0x0E09, "ECM anti-theft fault"),
    DtcDef("P1673", 0x0E0A, "ECM anti-theft fault"),
    DtcDef("P1674", 0x0E0B, "ECM anti-theft fault"),
    # --- Misfire (misfire scenario, 0x0Fxx) ---
    DtcDef("P0300", 0x0F00, "Random / multiple cylinder misfire detected"),
    DtcDef("P1300", 0x0F10, "Multiple cylinder misfire detected"),
    DtcDef("P0301", 0x0F01, "Cylinder 1 misfire detected"),
    DtcDef("P0302", 0x0F02, "Cylinder 2 misfire detected"),
    DtcDef("P0303", 0x0F03, "Cylinder 3 misfire detected"),
    DtcDef("P0304", 0x0F04, "Cylinder 4 misfire detected"),
    DtcDef("P0305", 0x0F05, "Cylinder 5 misfire detected"),
    DtcDef("P0306", 0x0F06, "Cylinder 6 misfire detected"),
    DtcDef("P0307", 0x0F07, "Cylinder 7 misfire detected"),
    DtcDef("P0308", 0x0F08, "Cylinder 8 misfire detected"),
    DtcDef("P1301", 0x0F11, "Cylinder 1 misfire (with low fuel)"),
    DtcDef("P1302", 0x0F12, "Cylinder 2 misfire (with low fuel)"),
    DtcDef("P1303", 0x0F13, "Cylinder 3 misfire (with low fuel)"),
    DtcDef("P1304", 0x0F14, "Cylinder 4 misfire (with low fuel)"),
    DtcDef("P1305", 0x0F15, "Cylinder 5 misfire (with low fuel)"),
    DtcDef("P1306", 0x0F16, "Cylinder 6 misfire (with low fuel)"),
    DtcDef("P1307", 0x0F17, "Cylinder 7 misfire (with low fuel)"),
    DtcDef("P1308", 0x0F18, "Cylinder 8 misfire (with low fuel)"),
    DtcDef("P1319", 0x0F19, "Misfire detected with low fuel level"),
)

#: The GEMS fault table, keyed by the 2-byte raw id.
DTC_TABLE: dict[int, DtcDef] = {d.raw: d for d in _DEFS}

#: Reverse index: P-code string -> definition.
_BY_CODE: dict[str, DtcDef] = {d.code: d for d in _DEFS}


def by_code(code: str) -> DtcDef:
    """Return the :class:`DtcDef` for a P-code string (e.g. ``"P0118"``).

    Raises :class:`KeyError` if the code is not part of the GEMS table.
    """
    return _BY_CODE[code]


def by_raw(raw: int) -> DtcDef | None:
    """Return the :class:`DtcDef` for a raw id, or ``None`` if unknown."""
    return DTC_TABLE.get(raw)


def make_dtc(code: str, state: DtcState = DtcState.STORED) -> Dtc:
    """Build a :class:`Dtc` (with description + raw filled from the table)."""
    d = by_code(code)
    return Dtc(code=d.code, description=d.description, raw=d.raw, state=state)


def encode_dtc_response(dtcs: list[Dtc]) -> bytes:
    """Build the ``0x18`` (ReadDTCByStatus) positive-response payload (ECU side).

    Layout: ``[count]`` followed by ``count`` × ``[raw-hi][raw-lo][status]``.
    ``count`` is clamped to a single byte (0..255).
    """
    count = len(dtcs)
    if count > 0xFF:
        raise ValueError(f"too many DTCs to encode: {count}")
    out = bytearray([count])
    for dtc in dtcs:
        raw = dtc.raw & 0xFFFF
        out.append((raw >> 8) & 0xFF)
        out.append(raw & 0xFF)
        out.append(_state_to_byte(dtc.state))
    return bytes(out)


def decode_dtc_response(payload: bytes) -> list[Dtc]:
    """Parse the ``0x18`` payload into a list of :class:`Dtc` (client side).

    Unknown raw ids are surfaced as ``P----`` with a generic description so a
    surprising ECU never crashes the reader.
    """
    if not payload:
        return []
    count = payload[0]
    body = payload[1:]
    if len(body) < count * 3:
        raise ValueError(
            f"truncated DTC payload: declared {count} codes, "
            f"only {len(body)} body bytes"
        )
    dtcs: list[Dtc] = []
    for i in range(count):
        hi, lo, status = body[i * 3 : i * 3 + 3]
        raw = (hi << 8) | lo
        state = _state_from_byte(status)
        d = DTC_TABLE.get(raw)
        if d is not None:
            dtcs.append(Dtc(code=d.code, description=d.description, raw=raw, state=state))
        else:
            dtcs.append(
                Dtc(code="P----", description=f"Unknown DTC (raw 0x{raw:04X})",
                    raw=raw, state=state)
            )
    return dtcs


def read_dtcs(client: KwpClient) -> list[Dtc]:
    """Read stored DTCs from the ECU via the generic client and decode them."""
    payload = client.read_dtcs_raw()
    return decode_dtc_response(payload)


def clear_dtcs(client: KwpClient) -> None:
    """Clear stored diagnostic information (``0x14``) via the generic client."""
    client.clear_dtcs()
