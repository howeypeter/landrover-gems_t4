"""HTTP/WebSocket API over the Backend (optional [api] extra).

A thin FastAPI layer that exposes the SAME ``gems_t4.app.backend.Backend`` the
CLI and PySide6 GUI use - no protocol/transport code is duplicated here. The
browser front-end (backlogged) will talk to this; the Pico/ECU stay behind the
Python transport. Import :func:`build_app` to get the FastAPI application.
"""
from gems_t4.app.web.api import build_app

__all__ = ["build_app"]
