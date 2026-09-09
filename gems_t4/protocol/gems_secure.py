"""GEMS proprietary 0xDA channel: SecurityAccess ($27) + coding reads/writes.

This is separate from the OBD-II :class:`~gems_t4.protocol.kline.KlineClient`
(address 0x33, ``68 6A F1`` envelope, emissions subset only). The *proprietary*
GEMS layer — coding, PROM id, immobiliser, the T4 extras — lives on a
manufacturer channel reached by:

* a 5-baud slow init at **address 0xDA** (keybytes come back ``aa55``), which
  requires the ECU's **L-line tied to the K node** on the bench; and
* **ISO-14230 no-address framing**: every message is ``[len][data...][checksum]``
  where ``len`` = number of data bytes and ``checksum`` = 8-bit sum of ``len`` +
  data. (The OBD ``68 6A F1`` envelope gets silence on this channel.)

The channel is gated by KWP2000 **SecurityAccess ($27)**. The seed→key transform
was recovered from the FlemcoDesign "GEMS ECU Utility" Android app and **confirmed
on real hardware (2026-09-08)**:

    key = (seed * 16723) % 65536          # 16-bit, big-endian

Handshake: ``1002`` (StartDiagnosticSession) → ``2701`` (requestSeed) →
``6701 <seed>`` → send ``2702 <key>`` → ``6702 AA`` (accept; ``6702 CC`` = reject).
Once unlocked, coding is read with service ``22`` (ReadDataByCommonIdentifier)
and the two known actions use service ``A3``. See ``memory/real-gems-protocol.md``.

WARNING — writes: ``$27`` locks after ~3 *wrong* keys (NRC 0x36). A *correct*
key never touches that counter. The ``A3`` writes here (reset-adaptive,
immobiliser-synch) mutate the ECU; they are refused unless the session is
unlocked, and callers should gate them behind explicit user confirmation.
"""
from __future__ import annotations

from dataclasses import dataclass

from gems_t4.transport.base import (
    InitError,
    InitResult,
    Transport,
    TransportError,
    TransportTimeout,
)

__all__ = [
    "SECURE_INIT_ADDRESS",
    "SECURITY_MULTIPLIER",
    "GemsSecureError",
    "GemsSecureLocked",
    "security_key",
    "secure_checksum",
    "encode_secure",
    "decode_secure",
    "CID_VIN",
    "CID_PROM_ID",
    "CID_CONFIG",
    "WRITE_RESET_ADAPTIVE",
    "WRITE_IMMOBILISER_SYNCH",
    "SECURE_PAGE_CONFIG",
    "IMMO_BLOCK_RECORDS",
    "GemsConfig",
    "GemsSecureSession",
]

#: 5-baud slow-init address for the proprietary channel (needs the L-line).
SECURE_INIT_ADDRESS = 0xDA
#: The recovered $27 seed→key multiplier (0x4153); odd ⇒ a clean bijection.
SECURITY_MULTIPLIER = 16723

# Coding identifiers (service 0x22 ReadDataByCommonIdentifier). Confirmed on a
# real Disco-1 GEMS ECU 2026-09-08 (VIN answered "unavailable" on that ECU).
CID_VIN = b"\x04\xC4"       # VIN last-6 (proprietary coding)
CID_PROM_ID = b"\x04\xE2"   # PROM id (also the app's keep-alive read)
CID_CONFIG = b"\x04\xBF"    # combined displacement / transmission / drivetrain

# The two proprietary write actions (service 0xA3), verbatim from the app.
WRITE_RESET_ADAPTIVE = bytes.fromhex("A3234800")
WRITE_IMMOBILISER_SYNCH = bytes.fromhex("A300622588")

# 0x3C memory is (page, record)-indexed, NOT a flat byte address (confirmed on
# hardware: 3C 18 00 and 3C 18 01 return unrelated 16-byte records). Page 0x18
# holds the config/EEPROM; da9 cataloged it, da10 confirmed the block below.
SECURE_PAGE_CONFIG = 0x18
#: Records A4-A8 on page 0x18 are the immobiliser/security block — a GEMS-signature
#: "two copies" structure: A4 and A7 are byte-identical (the static security
#: core), A5/A8 are a paired field differing in one byte, A6 a small header.
#: Confirmed stable on a real Disco-1 ECU 2026-09-08 (da10). ⚠️ The byte SEMANTICS
#: (which bytes are the mobilise code vs a checksum/adaptive value) are NOT yet
#: decoded — reading them is proven; interpreting them needs a reference ECU.
IMMO_BLOCK_RECORDS = (0xA4, 0xA5, 0xA6, 0xA7, 0xA8)


class GemsSecureError(TransportError):
    """Framing / protocol error on the proprietary 0xDA channel."""


class GemsSecureLocked(GemsSecureError):
    """A privileged operation was attempted before a successful $27 unlock."""


def security_key(seed: int) -> int:
    """The GEMS ``$27`` seed→key transform: ``key = (seed * 16723) mod 65536``.

    ``seed`` and the returned key are 16-bit. Recovered from the FlemcoDesign
    app and confirmed on hardware (seed ``BFC8`` → key ``F5D8``; ``F6E8`` →
    ``F538``).
    """
    return (seed * SECURITY_MULTIPLIER) % 65536


def secure_checksum(data: bytes) -> int:
    """ISO-14230 no-address checksum: 8-bit sum of every preceding byte."""
    return sum(data) & 0xFF


def encode_secure(payload: bytes) -> bytes:
    """Wrap a service payload in a no-address frame ``[len][payload][checksum]``."""
    if not payload:
        raise GemsSecureError("empty payload")
    if len(payload) > 0xFF:
        raise GemsSecureError(f"payload too long ({len(payload)} bytes)")
    frame = bytes([len(payload)]) + payload
    return frame + bytes([secure_checksum(frame)])


def decode_secure(buf: bytes) -> bytes:
    """Validate a no-address response frame and return its data bytes.

    ISO-14230 no-address framing: the format byte's low 6 bits are the data
    length; **if that field is 0, a separate length byte follows** (used when the
    payload exceeds 63 bytes — e.g. a 64-byte ``0x3C`` memory read comes back as
    ``00 41 7C …``, length 0x41 = 65 = the ``7C`` service byte + 64 data bytes).
    Returns ``data`` (which for a read still carries the ``62 <cid>``/``7C`` echo,
    or ``7F <sid> <nrc>`` for a negative). Raises on a short frame or bad checksum.
    """
    if len(buf) < 3:
        raise GemsSecureError(f"response too short: {buf.hex()}")
    length = buf[0] & 0x3F
    data_start = 1
    if length == 0:                       # length carried in a second byte
        length = buf[1]
        data_start = 2
    end = data_start + length
    if end >= len(buf):
        raise GemsSecureError(f"length {length} overruns frame: {buf.hex()}")
    if secure_checksum(buf[:end]) != buf[end]:
        raise GemsSecureError(f"checksum mismatch: {buf.hex()}")
    return buf[data_start:end]


@dataclass(frozen=True, slots=True)
class GemsConfig:
    """Decoded ``2204BF`` config record (displacement / transmission / drivetrain)."""

    raw: int
    displacement: str   # "4.0" or "4.6"
    transmission: str   # "auto" or "manual"

    @classmethod
    def from_byte(cls, b: int) -> "GemsConfig":
        # Per the app: displacement byte 1|2 ⇒ 4.6 else 4.0; 2|3 ⇒ manual else auto.
        disp = "4.6" if b in (1, 2) else "4.0"
        trans = "manual" if b in (2, 3) else "auto"
        return cls(raw=b, displacement=disp, transmission=trans)


class GemsSecureSession:
    """A SecurityAccess-gated session on the proprietary 0xDA GEMS channel.

    Usage::

        s = GemsSecureSession(transport)
        s.connect()                 # init 0xDA (needs L-line tied)
        if s.unlock():              # 1002 -> 2701 -> key -> 2702 -> 6702AA
            prom = s.read_prom_id()
            cfg = s.read_config()
    """

    def __init__(self, transport: Transport) -> None:
        self.transport = transport
        self.unlocked = False
        self.last_seed: int | None = None

    # -- lifecycle -------------------------------------------------------- #
    def connect(self) -> InitResult:
        """Open the transport and 5-baud-init at 0xDA. Raises on init failure."""
        self.transport.open()
        result = self.transport.init(SECURE_INIT_ADDRESS, "slow")
        self.unlocked = False
        return result

    def close(self) -> None:
        self.unlocked = False
        self.transport.close()

    def __enter__(self) -> "GemsSecureSession":
        self.connect()
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    # -- core exchange ---------------------------------------------------- #
    def _exchange(self, payload: bytes) -> bytes:
        """Send one no-address request; return the decoded response data.

        Returns an empty ``bytes`` if the ECU stays silent (a timeout), matching
        the probe behaviour; framing/checksum errors raise.
        """
        self.transport.send(encode_secure(payload))
        try:
            raw = self.transport.receive()
        except TransportTimeout:
            return b""
        if not raw:
            return b""
        return decode_secure(raw)

    @staticmethod
    def _is_negative(data: bytes) -> bool:
        return len(data) >= 1 and data[0] == 0x7F

    # -- SecurityAccess --------------------------------------------------- #
    def start_session(self) -> bool:
        """``1002`` StartDiagnosticSession; True on the ``5002`` positive."""
        return self._exchange(b"\x10\x02")[:2] == b"\x50\x02"

    def request_seed(self) -> int | None:
        """``2701`` requestSeed; return the 16-bit seed, or None if not offered."""
        data = self._exchange(b"\x27\x01")
        if len(data) >= 4 and data[0] == 0x67 and data[1] == 0x01:
            self.last_seed = (data[2] << 8) | data[3]
            return self.last_seed
        return None

    def send_key(self, key: int) -> bool:
        """``2702<key>`` sendKey; True only on the ``6702AA`` accept."""
        payload = b"\x27\x02" + bytes([(key >> 8) & 0xFF, key & 0xFF])
        data = self._exchange(payload)
        self.unlocked = data[:3] == b"\x67\x02\xAA"
        return self.unlocked

    def unlock(self) -> bool:
        """Full handshake: start session → seed → computed key → verify accept.

        Sends exactly ONE key (computed, never guessed), so it cannot trip the
        wrong-key lockout. Returns True iff the ECU answered ``6702AA``.
        """
        self.start_session()  # 1002; some ECUs answer oddly, so don't hard-gate
        seed = self.request_seed()
        if seed is None:
            return False
        return self.send_key(security_key(seed))

    # -- reads (service 22) ----------------------------------------------- #
    def read_cid(self, cid: bytes) -> bytes | None:
        """Read a coding identifier; return its value bytes, or None if the ECU
        reports it unavailable (a ``7F 22 xx`` negative, e.g. VIN on a Disco 1).
        """
        if not self.unlocked:
            raise GemsSecureLocked("read_cid requires a successful unlock() first")
        data = self._exchange(b"\x22" + cid)
        if not data or self._is_negative(data):
            return None
        # positive: 62 <cid...> <value...>
        prefix = b"\x62" + cid
        return data[len(prefix):] if data.startswith(prefix) else data

    def read_prom_id(self) -> str | None:
        """PROM id as the app displays it (the two value bytes, byte-swapped)."""
        v = self.read_cid(CID_PROM_ID)
        if v is None or len(v) < 2:
            return None
        return f"{v[1]:02X}{v[0]:02X}"

    def read_config(self) -> GemsConfig | None:
        """Displacement / transmission / drivetrain from the ``2204BF`` byte."""
        v = self.read_cid(CID_CONFIG)
        if v is None or len(v) < 1:
            return None
        return GemsConfig.from_byte(v[0])

    def read_vin_last6(self) -> str | None:
        """VIN last-6 coding. Returns None when the engine ECU doesn't hold it
        (the common case on an early Disco 1 — it lives in the Lucas 10AS)."""
        v = self.read_cid(CID_VIN)
        return v.decode("ascii", "replace") if v else None

    def read_immobiliser_block(self) -> dict[int, bytes]:
        """Read the immobiliser/security block (page 0x18, records A4-A8).

        Returns ``{record: 16 bytes}`` for :data:`IMMO_BLOCK_RECORDS` (a record
        missing from the dict means that read failed). The block is the GEMS
        "two copies" structure — A4 == A7, A5/A8 differ by one byte — so a caller
        can sanity-check the copies agree. ⚠️ Byte semantics are NOT decoded yet
        (see :data:`IMMO_BLOCK_RECORDS`); this reads the raw block, it does not
        interpret it. Requires a successful :meth:`unlock`.
        """
        if not self.unlocked:
            raise GemsSecureLocked("read_immobiliser_block requires unlock() first")
        out: dict[int, bytes] = {}
        for record in IMMO_BLOCK_RECORDS:
            data = self.read_memory(SECURE_PAGE_CONFIG, record, 0x10)
            if data is not None:
                out[record] = data
        return out

    # -- writes (service A3) — gated behind unlock ------------------------ #
    def reset_adaptive_values(self) -> bytes:
        """Send the reset-adaptive-values action. Requires an unlocked session."""
        return self._write(WRITE_RESET_ADAPTIVE)

    def immobiliser_synch(self) -> bytes:
        """Send the immobiliser-synch (Security-Learn) action. Unlock required.

        This mutates immobiliser pairing — callers must confirm with the user
        first. Returns the raw response data for inspection.
        """
        return self._write(WRITE_IMMOBILISER_SYNCH)

    def _write(self, payload: bytes) -> bytes:
        if not self.unlocked:
            raise GemsSecureLocked("writes require a successful unlock() first")
        return self._exchange(payload)

    # -- memory read (service 0x3C) --------------------------------------- #
    # Request is ``3C <b1> <b2> <len>`` and the positive reply is ``7C`` + ``len``
    # bytes; a single read is reliable and repeatable. BUT the two address bytes
    # are NOT a flat linear byte pointer on our Disco-1 ECU (confirmed 2026-09-08):
    # ``3C 18 00 10`` and ``3C 18 01 10`` return unrelated 16-byte blocks — not
    # overlapping windows — so consecutive "addresses" select different records/
    # pages, and :meth:`dump_memory`'s increment-by-``len`` model does NOT yield a
    # linear image (that's why the 2 KB dump came out scrambled). The ``<b1><b2>``
    # semantics are still uncharacterized. For KNOWN fields use the CID reads
    # (:meth:`read_prom_id`/:meth:`read_config`/:meth:`read_vin_last6`, service
    # ``22 04 xx``) — that's what the real app uses; it never used ``0x3C``.
    def read_memory(self, b1: int, b2: int, length: int = 0x10) -> bytes | None:
        """Raw ``0x3C`` read: send ``3C <b1> <b2> <len>``, return ``len`` bytes.

        ``b1``/``b2`` are the two raw arg bytes (NOT a validated linear address —
        see the note above). Returns the data (leading ``0x7C`` stripped), or None
        on a negative/silent/short reply.
        """
        if not self.unlocked:
            raise GemsSecureLocked("read_memory requires a successful unlock() first")
        if not 0 <= b1 <= 0xFF or not 0 <= b2 <= 0xFF or not 1 <= length <= 0x3F:
            raise GemsSecureError(f"bad args: {b1:#x},{b2:#x},len {length} (len 1..63)")
        data = self._exchange(bytes([0x3C, b1, b2, length]))
        if not data or self._is_negative(data):
            return None
        block = data[1:] if data[0] == 0x7C else data
        # Reject a short/overlong read: over BLE a partial notification yields a
        # valid-checksum frame with the wrong byte count. Return None so the
        # caller retries instead of trusting garbage.
        if len(block) != length:
            return None
        return block

    def read_at(self, address: int, length: int = 0x10) -> bytes | None:
        """Convenience: ``read_memory`` with a 16-bit ``address`` split big-endian.

        ⚠️ Only meaningful if the ``0x3C`` arg bytes turn out to be a linear
        address — which they are NOT on our ECU (see :meth:`read_memory`). Kept
        for probing; do not build a linear dump on it without re-verifying.
        """
        return self.read_memory((address >> 8) & 0xFF, address & 0xFF, length)

    # -- coding write (service 0x2E) -------------------------------------- #
    # PROVISIONAL: the app only READS VIN/displacement/etc.; it never writes them,
    # so the coding-WRITE service is unconfirmed. 0x2E (WriteDataByCommonIdentifier)
    # is the standard KWP counterpart to the 0x22 reads we know work — the most
    # likely candidate — but GEMS may instead use an A3 form. Discover on the bench
    # with read-back verification (~/da8_secure_probe.py) before relying on it.
    def write_cid(self, cid: bytes, value: bytes) -> bytes:
        """Attempt a coding write via ``2E <cid> <value>`` (unlock req).

        Returns the raw response for inspection. Callers MUST read the field back
        and confirm it changed (and confirm with the user first) — this is an
        unverified write path.
        """
        return self._write(b"\x2E" + cid + value)
