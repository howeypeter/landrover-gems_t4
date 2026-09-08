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

This screen is also reachable from every other screen via the persistent "VCI:
..." button in the title bar (:meth:`KioskWindow.update_connection_indicator`)
— you don't have to hunt through the System menu to change the link.

It uses its own **Cancel / Apply / Save** buttons (not the shell's tick/cross/
back bar): **Apply** switches to and tests the selected connection, staying on
this screen; **Save** does the same and also remembers it for next time, then
returns to the main menu; **Cancel** returns to the main menu without saving.
Applying proves the link before committing — on failure the backend rolls back
to the previous (working) connection.
"""
from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app import config as _config
from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen

#: The GEMS main menu screen to return to on Save / Cancel.
_MAIN_MENU = "system_menu"


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
        self._radio_ble = QRadioButton(
            "Bluetooth LE — Pico adapter (no pairing, no COM port)"
        )
        lay.addWidget(self._radio_virtual)
        lay.addWidget(self._radio_usb)
        lay.addWidget(self._radio_network)
        lay.addWidget(self._radio_ble)

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

        self._ble_device = QLineEdit()
        self._ble_device.setToolTip(
            "BLE device name or address the Pico advertises (default gems-pico)"
        )
        self._ble_device.setMaximumWidth(260)
        form.addRow("BLE device:", self._ble_device)

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

        #: Result of the last Apply/Save attempt (tests the selected link) —
        #: separate from ``_current``, which just names the active connection.
        self._test_result = QLabel("")
        self._test_result.setObjectName("Lcd")
        self._test_result.setWordWrap(True)
        lay.addWidget(self._test_result)

        note = QLabel(
            "Apply — switch to and test the selected connection, staying here. "
            "Save — apply, remember it for next time, and return to the menu. "
            "Cancel — return to the menu without saving."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #404040;")
        lay.addWidget(note)

        lay.addStretch(1)

        buttons = QHBoxLayout()
        self._btn_cancel = QPushButton("Cancel")
        self._btn_apply = QPushButton("Apply")
        self._btn_save = QPushButton("Save")
        self._btn_cancel.clicked.connect(self._on_cancel)
        self._btn_apply.clicked.connect(self._on_apply)
        self._btn_save.clicked.connect(self._on_save)
        buttons.addStretch(1)
        for b in (self._btn_cancel, self._btn_apply, self._btn_save):
            buttons.addWidget(b)
        lay.addLayout(buttons)

        for radio in (self._radio_virtual, self._radio_usb, self._radio_network,
                      self._radio_ble):
            radio.toggled.connect(self._update_enabled)

    # -- helpers -------------------------------------------------------------#
    def _selected_kind(self) -> str:
        if self._radio_usb.isChecked():
            return "usb"
        if self._radio_network.isChecked():
            return "network"
        if self._radio_ble.isChecked():
            return "ble"
        return "virtual"

    def _update_enabled(self) -> None:
        """Enable only the fields that belong to the selected kind."""
        kind = self._selected_kind()
        self._com_port.setEnabled(kind == "usb")
        self._host.setEnabled(kind == "network")
        self._tcp_port.setEnabled(kind == "network")
        self._allow_writes.setEnabled(kind == "network")
        self._ble_device.setEnabled(kind == "ble")

    def _show_current(self) -> None:
        self._current.setText(f"Current: {self.backend.connection_label}")

    def _refresh_window_indicator(self) -> None:
        """Nudge the persistent "VCI: ..." title-bar button (base.KioskWindow)
        to reflect a just-applied change immediately, not just on next nav."""
        win = self.window()
        refresh = getattr(win, "update_connection_indicator", None)
        if refresh is not None:
            refresh()

    # -- lifecycle ------------------------------------------------------------#
    def on_enter(self) -> None:
        """Populate the form from the saved settings and show what's active."""
        cfg = _config.load_config()
        {
            "usb": self._radio_usb,
            "network": self._radio_network,
            "ble": self._radio_ble,
        }.get(cfg.kind, self._radio_virtual).setChecked(True)
        self._com_port.setText(cfg.com_port)
        self._host.setText(cfg.host)
        self._tcp_port.setText(str(cfg.tcp_port))
        self._allow_writes.setChecked(cfg.allow_writes)
        self._ble_device.setText(cfg.device)
        self._update_enabled()
        self._show_current()
        self._test_result.setText("")
        self.status.emit("Choose a connection — Apply to test it, Save to keep it.")

    # -- navigation ------------------------------------------------------------#
    def nav_buttons(self) -> set[str]:
        # This screen uses its own Cancel / Apply / Save buttons (below the
        # form), not the shell's tick/cross/back bar.
        return set()

    def _read_form(self) -> dict | None:
        """Validate the form and return apply_connection kwargs, or None (with a
        status message) if a required field is missing / malformed."""
        kind = self._selected_kind()
        com_port = self._com_port.text().strip()
        host = self._host.text().strip()
        device = self._ble_device.text().strip()
        try:
            tcp_port = int(self._tcp_port.text().strip() or "9141")
        except ValueError:
            self.status.emit("TCP port must be a number.")
            return None
        if kind == "usb" and not com_port:
            self.status.emit("Enter the COM port of the USB adapter.")
            return None
        if kind == "network" and not host:
            self.status.emit("Enter the host/IP of the network endpoint.")
            return None
        if kind == "ble" and not device:
            self.status.emit("Enter the BLE device name (default gems-pico).")
            return None
        return {
            "kind": kind,
            "com_port": com_port or None,
            "host": host or None,
            "tcp_port": tcp_port,
            "allow_writes": self._allow_writes.isChecked(),
            "device": device or None,
        }

    def _apply(self, *, persist: bool, then_leave: bool) -> None:
        """Apply (and thereby test) the selected connection. Optionally persist
        it and/or return to the main menu on success."""
        form = self._read_form()
        if form is None:
            return
        kind = form["kind"]
        self._test_result.setText("")

        def work() -> str:
            # apply_connection proves the link (connect); on failure the backend
            # rolls back to the previous (working) connection and re-raises.
            return self.backend.apply_connection(**form)

        def done(label: str) -> None:
            if persist:
                _config.save_config(
                    _config.ConnectionConfig(
                        kind=kind,
                        com_port=form["com_port"] or _config.ConnectionConfig().com_port,
                        host=form["host"] or _config.ConnectionConfig().host,
                        tcp_port=form["tcp_port"],
                        allow_writes=form["allow_writes"],
                        device=form["device"] or _config.ConnectionConfig().device,
                    )
                )
            self._show_current()
            self._refresh_window_indicator()
            self._test_result.setText(f"OK: {label}")
            if then_leave:
                self.status.emit(f"VCI saved — {label}")
                self.navigate.emit(_MAIN_MENU)
            else:
                self.status.emit(f"Applied — {label}")

        def failed(exc: Exception) -> None:
            self._show_current()
            self._refresh_window_indicator()
            self._test_result.setText(f"FAILED: {exc}")
            self.status.emit(f"Connection failed: {exc}")

        self.run_with_wait("Testing VCI connection", work, done, failed)

    # -- buttons ---------------------------------------------------------------#
    def _on_apply(self) -> None:
        """Apply + test the selected connection; stay on this screen."""
        self._apply(persist=False, then_leave=False)

    def _on_save(self) -> None:
        """Apply + test, persist for next time, then return to the main menu."""
        self._apply(persist=True, then_leave=True)

    def _on_cancel(self) -> None:
        """Return to the main menu without saving."""
        self.navigate.emit(_MAIN_MENU)
