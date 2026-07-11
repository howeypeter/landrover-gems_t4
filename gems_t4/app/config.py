"""Persisted connection settings — how the tool reaches the ECU.

A tiny JSON file (``~/.gems_t4.json`` by default; override with the
``GEMS_T4_CONFIG`` env var, which the tests point at a temp path) remembering
the VCI configuration chosen on the GUI's connection screen: virtual ECU, USB
COM port, or network endpoint. Load is tolerant — any missing/corrupt file
just yields the defaults.
"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from gems_t4.transport.tcp import DEFAULT_PORT

#: The three connection kinds the GUI offers.
KINDS = ("virtual", "usb", "network")


@dataclass
class ConnectionConfig:
    """The user's saved VCI selection."""

    kind: str = "virtual"
    com_port: str = "COM3"
    host: str = "192.168.1.100"
    tcp_port: int = DEFAULT_PORT
    allow_writes: bool = False


def config_path() -> Path:
    """The settings file location (env-overridable for tests)."""
    override = os.environ.get("GEMS_T4_CONFIG")
    if override:
        return Path(override)
    return Path.home() / ".gems_t4.json"


def load_config() -> ConnectionConfig:
    """Load saved settings; silently fall back to defaults on any problem.

    "Tolerant" means STRICT validation with a default fallback: every field is
    type-checked (``allow_writes`` especially — a truthy non-bool like the
    string ``"false"`` must not silently enable network writes), and a kind
    whose required field is empty (usb without a COM port, network without a
    host) yields the defaults rather than a value that crashes downstream.
    """
    try:
        raw = json.loads(config_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ConnectionConfig()
    if not isinstance(raw, dict):
        return ConnectionConfig()
    known = {f.name for f in fields(ConnectionConfig)}
    kwargs = {k: v for k, v in raw.items() if k in known}
    try:
        cfg = ConnectionConfig(**kwargs)
    except TypeError:
        return ConnectionConfig()
    valid = (
        cfg.kind in KINDS
        and isinstance(cfg.com_port, str)
        and isinstance(cfg.host, str)
        # bool is not an acceptable int here, and vice versa below
        and isinstance(cfg.tcp_port, int)
        and not isinstance(cfg.tcp_port, bool)
        and 0 < cfg.tcp_port < 65536
        and isinstance(cfg.allow_writes, bool)
        and not (cfg.kind == "usb" and not cfg.com_port)
        and not (cfg.kind == "network" and not cfg.host)
    )
    return cfg if valid else ConnectionConfig()


def save_config(cfg: ConnectionConfig) -> None:
    """Write settings to :func:`config_path` (best-effort directories)."""
    path = config_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(asdict(cfg), indent=2), encoding="utf-8")
