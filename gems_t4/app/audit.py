"""ECU audit log — a single, front-end-agnostic record of what the tool did.

Because the CLI, PySide6 GUI, and web API all drive the ECU through one shared
:class:`gems_t4.app.backend.Backend`, logging inside ``Backend`` captures EVERY
ECU interaction regardless of which front-end issued it — there is no per-UI
copy to drift or a gap where one UI's writes go unrecorded.

Format: one JSON object per line (JSON Lines), so it's greppable and trivially
machine-readable. Writes to the real ECU (coding, DTC-clear, actuators,
immobiliser Security-Learn) are the load-bearing entries; notable reads (DTCs,
coding, VIN) are logged too, but high-rate live-data polling is NOT (it would
flood the log and drown the audit-worthy events).

Location (first that applies):
  * ``$GEMS_T4_AUDIT_LOG``  — explicit file path (tests point this at a tmp file)
  * ``$GEMS_T4_HOME/audit.log``
  * ``~/.gems_t4/audit.log``  (default; same dir as the web launcher/log)

Audit logging must NEVER break the tool: every failure here is swallowed.
"""
from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOGGER_NAME = "gems_t4.audit"
_configured = False


def _default_path() -> Path:
    env = os.environ.get("GEMS_T4_AUDIT_LOG")
    if env:
        return Path(env)
    home = os.environ.get("GEMS_T4_HOME")
    root = Path(home) if home else Path.home() / ".gems_t4"
    return root / "audit.log"


def get_logger() -> logging.Logger:
    """The configured audit logger (rotating file; stderr fallback)."""
    global _configured
    log = logging.getLogger(_LOGGER_NAME)
    if _configured:
        return log
    log.setLevel(logging.INFO)
    log.propagate = False  # don't leak audit lines into the root logger
    path = _default_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            path, maxBytes=2_000_000, backupCount=5, encoding="utf-8"
        )
    except OSError:
        # Can't write the file (permissions, read-only FS) — never fail the
        # tool over the audit log; degrade to stderr.
        handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(message)s"))
    log.addHandler(handler)
    _configured = True
    return log


def audit(event: dict) -> None:
    """Append one JSON-line audit event (timestamped). Never raises."""
    try:
        record = {
            "ts": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            **event,
        }
        get_logger().info(json.dumps(record, default=str, ensure_ascii=False))
    except Exception:  # noqa: BLE001 - audit must never break the caller
        pass


def _reset_for_tests() -> None:
    """Drop the cached handler so a test can re-point GEMS_T4_AUDIT_LOG."""
    global _configured
    log = logging.getLogger(_LOGGER_NAME)
    for h in list(log.handlers):
        log.removeHandler(h)
        try:
            h.close()
        except Exception:  # noqa: BLE001
            pass
    _configured = False
