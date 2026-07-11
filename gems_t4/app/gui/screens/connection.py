"""Connection configuration screen — how the tool reaches the ECU.

The real RDS 5.06 / T4 Lite added a configuration-menu option to select between
the LAN Unit and the USB connector (CLAUDE.md design pillar 6). This screen is
that idea for our stack: **Virtual ECU** (built-in simulator), **USB connector**
(Pico adapter on a COM port), or **Network** (a ``gems_t4 serve`` bridge or a
WiFi Pico at an IP:port). It does not touch the Toolbox LAN-card self-test,
which keeps its canon period disclaimer.

The choice is applied through :meth:`Backend.set_connection` and persisted via
:mod:`gems_t4.app.config`, so the Pico's IP only has to be typed once. Network
connections are read-only unless the operator explicitly enables write
functions (wired-only write policy).
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app import config as _config
from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen


class ConnectionScreen(Screen):
    """Select and apply the VCI connection (virtual / USB COM port / network)."""

    title = "Configuration — VCI Connection"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)
        lay.setSpacing(14)

        caption = QLabel("Select how the tester communicates with the vehicle")
        caption.setStyleSheet("font-weight: bold;")
        lay.addWidget(caption)

        self._radio_virtual = QRadioButton(
            "Virtual ECU — built-in simulated vehicle (no hardware)"
        )
        self._radio_usb = QRadioButton("USB connector — Pico adapter on a COM port")
        self._radio_network = QRadioButton(
            "Network — TCP endpoint (bridge or WiFi Pico)"
        )
        lay.addWidget(self._radio_virtual)
        lay.addWidget(self._radio_usb)
        lay.addWidget(self._radio_network)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(10)

        self._com_port = QLineEdit()
        self._com_port.setToolTip("Serial port of the Pico adapter, e.g. COM3")
        self._com_port.setMaximumWidth(160)
        form.addRow("COM port:", self._com_port)

        self._host = QLineEdit()
        self._host.setToolTip("IP address or hostname, e.g. 192.168.1.50")
        self._host.setMaximumWidth(260)
        form.addRow("Host / IP:", self._host)

        self._tcp_port = QLineEdit()
        self._tcp_port.setToolTip("TCP port (default 9141)")
        self._tcp_port.setMaximumWidth(100)
        form.addRow("TCP port:", self._tcp_port)

        lay.addLayout(form)

        self._allow_writes = QCheckBox(
            "Allow write functions over the network (coding, actuators, "
            "Security-Learn)"
        )
        self._allow_writes.setToolTip(
            "Off = network is read-only (live data and fault codes). "
            "Writes stay wired-only unless you trust this link."
        )
        lay.addWidget(self._allow_writes)

        self._current = QLabel("")
        self._current.setObjectName("Lcd")
        self._current.setWordWrap(True)
        lay.addWidget(self._current)

        note = QLabel(
            "Press ✓ to apply and test the connection. The setting is "
            "remembered for the next session."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #404040;")
        lay.addWidget(note)

        lay.addStretch(1)

        for radio in (self._radio_virtual, self._radio_usb, self._radio_network):
            radio.toggled.connect(self._update_enabled)

    # -- helpers -------------------------------------------------------------#
    def _selected_kind(self) -> str:
        if self._radio_usb.isChecked():
            return "usb"
        if self._radio_network.isChecked():
            return "network"
        return "virtual"

    def _update_enabled(self) -> None:
        """Enable only the fields that belong to the selected kind."""
        kind = self._selected_kind()
        self._com_port.setEnabled(kind == "usb")
        self._host.setEnabled(kind == "network")
        self._tcp_port.setEnabled(kind == "network")
        self._allow_writes.setEnabled(kind == "network")

    def _show_current(self) -> None:
        self._current.setText(f"Current: {self.backend.connection_label}")

    # -- lifecycle ------------------------------------------------------------#
    def on_enter(self) -> None:
        """Populate the form from the saved settings and show what's active."""
        cfg = _config.load_config()
        {
            "usb": self._radio_usb,
            "network": self._radio_network,
        }.get(cfg.kind, self._radio_virtual).setChecked(True)
        self._com_port.setText(cfg.com_port)
        self._host.setText(cfg.host)
        self._tcp_port.setText(str(cfg.tcp_port))
        self._allow_writes.setChecked(cfg.allow_writes)
        self._update_enabled()
        self._show_current()
        self.status.emit("Choose a connection and press ✓ to apply.")

    # -- navigation ------------------------------------------------------------#
    def nav_buttons(self) -> set[str]:
        return {"back", "tick"}

    def on_tick(self) -> None:
        """Apply the selection: reconfigure the backend, connect, persist."""
        kind = self._selected_kind()
        com_port = self._com_port.text().strip()
        host = self._host.text().strip()
        try:
            tcp_port = int(self._tcp_port.text().strip() or "9141")
        except ValueError:
            self.status.emit("TCP port must be a number.")
            return
        allow_writes = self._allow_writes.isChecked()
        if kind == "usb" and not com_port:
            self.status.emit("Enter the COM port of the USB adapter.")
            return
        if kind == "network" and not host:
            self.status.emit("Enter the host/IP of the network endpoint.")
            return

        def work() -> str:
            # Prove the link before declaring success; on failure the backend
            # rolls back to the previous (working) connection.
            return self.backend.apply_connection(
                kind,
                com_port=com_port or None,
                host=host or None,
                tcp_port=tcp_port,
                allow_writes=allow_writes,
            )

        def done(label: str) -> None:
            _config.save_config(
                _config.ConnectionConfig(
                    kind=kind,
                    com_port=com_port or _config.ConnectionConfig().com_port,
                    host=host or _config.ConnectionConfig().host,
                    tcp_port=tcp_port,
                    allow_writes=allow_writes,
                )
            )
            self._show_current()
            self.status.emit(f"VCI configured — {label}")

        def failed(exc: Exception) -> None:
            self._show_current()
            self.status.emit(f"Connection failed: {exc}")

        self.run_with_wait("Testing VCI connection", work, done, failed)
