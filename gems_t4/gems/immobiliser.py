"""GEMS immobiliser / Security-Learn — the ONE genuine over-the-wire GEMS write.

The GEMS ECM won't run until it receives a coded mobilisation signal from the
BeCM; if the two fall out of sync you get the canon "ENGINE IMMOBILISED"
non-start. Re-syncing is the only real K-line *write* GEMS ever supported (maps
are a bench EPROM swap; see gems-hardware.md). The T4/Nanocom procedure:

    1. gain security access (seed/key)          -> $27
    2. put the ECU into Security-Learn mode      -> $31 routine 0x01
    3. cycle ignition; the BeCM re-sends its code (simulated here)
    4. the ECU stores the NEXT code as its new master (not compared) -> $31 0x02
    5. confirm the ECU is now mobilised          -> $31 routine 0x03 (status)

Any error and the ECU rejects it and stores nothing (authentic). This module is
the high-level flow over the generic :class:`~gems_t4.protocol.client.KwpClient`;
the virtual ECU models the matching state machine.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Callable

from gems_t4.protocol.messages import NRC
from gems_t4.protocol.security import compute_key

if TYPE_CHECKING:  # pragma: no cover
    from gems_t4.protocol.client import KwpClient

# -- $31 StartRoutine routine ids (Security-Learn) -------------------------- #
ROUTINE_ENTER_LEARN = 0x01
ROUTINE_SUBMIT_CODE = 0x02
ROUTINE_STATUS = 0x03

#: The code the (simulated) BeCM re-sends during a learn. Any value works — in a
#: real learn the ECU stores whatever the BeCM sends without comparing.
DEFAULT_BECM_CODE = 0xA5A5


@dataclass(frozen=True, slots=True)
class ImmobiliserStatus:
    """Snapshot of the engine ECU's immobiliser state."""

    mobilised: bool
    learn_mode: bool

    @property
    def summary(self) -> str:
        if self.learn_mode:
            return "SECURITY-LEARN MODE - awaiting BeCM code"
        return "MOBILISED - engine enabled" if self.mobilised else "ENGINE IMMOBILISED"


@dataclass
class SecurityLearnResult:
    """Outcome of a Security-Learn run, with the step log for display."""

    ok: bool
    message: str
    steps: list[str] = field(default_factory=list)


def read_status(client: "KwpClient") -> ImmobiliserStatus:
    """Read the immobiliser status ($31 routine 0x03)."""
    resp = client.start_routine(ROUTINE_STATUS, expect_positive=True)
    # payload: [routineId][mobilised][learn]
    d = resp.data
    mobilised = bool(d[1]) if len(d) > 1 else False
    learn = bool(d[2]) if len(d) > 2 else False
    return ImmobiliserStatus(mobilised=mobilised, learn_mode=learn)


def security_learn(
    client: "KwpClient",
    becm_code: int = DEFAULT_BECM_CODE,
    *,
    key_fn: Callable[[int], int] = compute_key,
    on_progress: Callable[[str], None] | None = None,
) -> SecurityLearnResult:
    """Run the full Security-Learn re-sync. Returns a result with a step log.

    ``on_progress`` (if given) is called with each step message as it happens,
    for live UI feedback.
    """
    steps: list[str] = []

    def step(msg: str) -> None:
        steps.append(msg)
        if on_progress is not None:
            on_progress(msg)

    # 1. security access (unlock)
    try:
        client.security_access(key_fn)
    except Exception as exc:  # NegativeResponse etc.
        return SecurityLearnResult(False, f"Security access denied: {exc}", steps)
    step("Security access granted (seed/key).")

    # 2. enter Security-Learn mode
    resp = client.start_routine(ROUTINE_ENTER_LEARN)
    if resp.is_negative:
        if resp.nrc == NRC.SECURITY_ACCESS_DENIED:
            return SecurityLearnResult(False, "Refused: security access required.", steps)
        return SecurityLearnResult(False, f"Could not enter learn mode ({resp.nrc_name}).", steps)
    step("ECU in Security-Learn mode - next code will be stored as master.")

    # 3. simulate the ignition cycle / BeCM re-sending its code
    step("Cycle ignition OFF->ON - BeCM re-sending mobilisation code...")

    # 4. store the BeCM code
    resp = client.start_routine(
        ROUTINE_SUBMIT_CODE, bytes([(becm_code >> 8) & 0xFF, becm_code & 0xFF])
    )
    if resp.is_negative:
        return SecurityLearnResult(False, f"Code rejected ({resp.nrc_name}) - nothing stored.", steps)
    step("BeCM code accepted and stored as new master.")

    # 5. confirm mobilised
    status = read_status(client)
    if status.mobilised:
        step("Confirmed: ECU is now MOBILISED - engine enabled.")
        return SecurityLearnResult(True, "Security-Learn complete - immobiliser re-synced.", steps)
    return SecurityLearnResult(False, "Learn finished but ECU still reports immobilised.", steps)
