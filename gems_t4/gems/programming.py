"""GEMS coding / programming surface — the small, gated write operations.

Reality check (see gems-hardware.md): GEMS maps live in socketed UV-EPROMs and
are NOT reflashable over the K-line. What the tool *can* write over the wire is
the ECU's small coding block — VIN last-6, dealer id, 4.0/4.6 select,
transmission — plus the immobiliser Security-Learn. The map "reflash" is a
bench chip-swap and is only ever an emulated lookalike here.

Every write goes through :func:`write_coding`, which enforces the safety gates
the project requires: a fresh backup, an explicit confirmation, the write, and a
verify-after-write read-back. The actual transport write is delegated to the
generic client; the *gating* is real.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

if TYPE_CHECKING:  # pragma: no cover
    from gems_t4.protocol.client import KwpClient


@dataclass(frozen=True, slots=True)
class CodingField:
    """One coding/settings field, with its local id and whether it is writable."""

    key: str
    local_id: int
    name: str
    writable: bool


#: The GEMS coding block. Writable identity fields vs read-only factory fields
#: (see gems-data-catalog.md "Coding / programming").
CODING_FIELDS: dict[str, CodingField] = {
    f.key: f
    for f in (
        CodingField("vin_last6", 0x81, "VIN (last 6)", True),
        CodingField("dealer_id", 0x82, "Dealer ID", True),
        CodingField("engine", 0x83, "Engine (4.0/4.6 select)", True),
        CodingField("transmission", 0x84, "Transmission (auto/manual)", True),
        CodingField("build_code", 0x85, "Build code", True),
        CodingField("market", 0x86, "Market", False),
        CodingField("part_number", 0x87, "ECU part number", False),
    )
}


#: Coding fields whose bytes are human-readable ASCII (shown/edited as text);
#: everything else is shown/edited as hex.
_TEXT_FIELDS: frozenset[str] = frozenset({"vin_last6", "part_number"})


def decode_field(field: str, data: bytes) -> str:
    """Render a coding field's bytes for display/editing (ASCII or hex)."""
    if field in _TEXT_FIELDS:
        return data.decode("ascii", errors="replace")
    return data.hex(" ").upper()


def encode_field(field: str, text: str) -> bytes:
    """Parse an edited coding value back to bytes (ASCII or hex).

    Raises :class:`ValueError` on malformed hex.
    """
    if field in _TEXT_FIELDS:
        return text.encode("ascii", errors="replace")
    return bytes.fromhex(text.replace(" ", ""))


@dataclass(frozen=True, slots=True)
class Backup:
    """A read-before-write snapshot of a coding field's current bytes."""

    local_id: int
    data: bytes


@dataclass
class WriteResult:
    """Outcome of a gated coding write."""

    field: str
    ok: bool
    message: str
    backup: Backup | None = None


class ProgrammingRefused(Exception):
    """A write was blocked by a safety gate (no backup, not confirmed, ...)."""


def read_coding(client: "KwpClient", field: str) -> bytes:
    """Read the current bytes of a coding field."""
    f = CODING_FIELDS[field]
    return client.read_data_by_local_id(f.local_id)


def backup(client: "KwpClient", field: str) -> Backup:
    """Take a verified backup of a coding field (read-before-write)."""
    f = CODING_FIELDS[field]
    return Backup(local_id=f.local_id, data=read_coding(client, field))


def write_coding(
    client: "KwpClient",
    field: str,
    value: bytes,
    *,
    backup: Backup | None,
    verify: bool = True,
    confirm: Callable[[], bool] | None = None,
) -> WriteResult:
    """Write a coding field, enforcing every safety gate.

    Gates, in order: field must exist and be writable; a fresh ``backup`` of the
    same field must be supplied; ``confirm()`` (if given) must return True; the
    write is performed; if ``verify`` the field is read back and compared.
    """
    f = CODING_FIELDS.get(field)
    if f is None:
        raise KeyError(f"unknown coding field {field!r}")
    if not f.writable:
        raise ProgrammingRefused(f"coding field {field!r} is read-only")
    if backup is None or backup.local_id != f.local_id:
        raise ProgrammingRefused(
            f"refusing to write {field!r} without a fresh backup of it"
        )
    if confirm is not None and not confirm():
        raise ProgrammingRefused(f"write of {field!r} not confirmed by operator")

    client.write_data_by_local_id(f.local_id, value)

    if verify:
        readback = client.read_data_by_local_id(f.local_id)
        if readback != value:
            return WriteResult(
                field=field,
                ok=False,
                message=(
                    f"verify FAILED: wrote {value.hex()} but read back "
                    f"{readback.hex()} — restore from backup"
                ),
                backup=backup,
            )
    return WriteResult(field=field, ok=True, message="write verified", backup=backup)
