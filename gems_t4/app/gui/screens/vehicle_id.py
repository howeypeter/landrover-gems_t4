"""Vehicle identification screen — VIN-first identity + fault-scenario selection.

This is the guided first fork of every P38 procedure ("GEMS or Thor?"). The
operator enters/confirms a VIN, sees the vehicle it decodes to, and — crucially —
picks which fault *scenario* the virtual ECU should present. That choice is the
vehicle-configuration step: it decides what the downstream fault-code, live-data,
and actuator screens will show, so it lives here and is committed on the tick.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app.backend import Backend, RealEcuUnsupported
from gems_t4.app.gui.base import Screen

#: A plausible P38 Range Rover VIN (SALLPAM…-style Solihull 17-char) to prefill.
_DEFAULT_VIN = "SALLPAMJ3WA123456"

#: The vehicle the VIN above decodes to — the GEMS fork, per CLAUDE.md.
_VEHICLE_SUMMARY = "Range Rover P38 · 4.0/4.6 V8 · Lucas/SAGEM GEMS (1995–99)"


class VehicleIdScreen(Screen):
    """VIN-first vehicle identification and fault-scenario selection."""

    title = "Vehicle Identification"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(30, 24, 30, 24)
        lay.setSpacing(14)

        caption = QLabel("Identify the vehicle to configure the diagnostic session")
        caption.setStyleSheet("font-weight: bold;")
        lay.addWidget(caption)

        form = QFormLayout()
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(12)

        self._vin = QLineEdit(_DEFAULT_VIN)
        self._vin.setMaxLength(17)
        self._vin.setToolTip("Vehicle Identification Number (17 characters)")
        form.addRow("VIN:", self._vin)

        self._summary = QLabel(_VEHICLE_SUMMARY)
        self._summary.setObjectName("Lcd")
        self._summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        form.addRow("Identified:", self._summary)

        #: VIN read back from the ECU. The engine ECU only *codes the last 6* of
        #: the VIN (a coding field); the full 17-char VIN isn't held here (it
        #: lives in the body/security module, and OBD Service 09 is usually
        #: unsupported on GEMS). So when only the last 6 are known, the first 11
        #: are shown as 0-placeholders rather than a fabricated VIN.
        self._ecu_vin = QLabel("(press “Read VIN from ECU”)")
        self._ecu_vin.setObjectName("Lcd")
        self._ecu_vin.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self._ecu_vin.setWordWrap(True)
        form.addRow("ECU VIN:", self._ecu_vin)

        self._read_vin_btn = QPushButton("Read VIN from ECU")
        self._read_vin_btn.clicked.connect(self._read_vin)
        form.addRow("", self._read_vin_btn)

        #: The vehicle-config choice: which fault scenario the ECU presents.
        self._scenario = QComboBox()
        for name in self.backend.available_scenarios():
            self._scenario.addItem(name)
        form.addRow("Test scenario:", self._scenario)

        lay.addLayout(form)

        note = QLabel(
            "The selected scenario configures the fitted-system responses for "
            "fault codes, live data and actuator tests. Press ✓ to confirm."
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #404040;")
        lay.addWidget(note)

        lay.addStretch(1)

    # -- data --------------------------------------------------------------- #
    def on_enter(self) -> None:
        """Sync the combo to the backend's current scenario and prompt the user.

        On a remote connection (USB/network) the scenario lives with the real
        or served ECU, not this tool — the picker is disabled.
        """
        self._ecu_vin.setText("(press “Read VIN from ECU”)")
        remote = self.backend.is_remote
        self._scenario.setEnabled(not remote)
        if remote:
            self._scenario.setToolTip(
                "Scenario is determined by the connected ECU "
                f"({self.backend.connection_label})"
            )
            self.status.emit("Confirm VIN, then press ✓ to continue.")
            return
        self._scenario.setToolTip("")
        current = self.backend.scenario_name
        idx = self._scenario.findText(current)
        if idx >= 0:
            self._scenario.setCurrentIndex(idx)
        self.status.emit("Confirm VIN and test scenario, then press ✓ to continue.")

    # -- VIN read ----------------------------------------------------------- #
    def _read_vin(self) -> None:
        """Read the VIN from the ECU, behind the "please wait" overlay.

        Tries the full VIN (OBD-II Service 09) first; if the ECU doesn't answer
        (usual for GEMS), falls back to the **coded VIN last-6** and pads the
        unknown first 11 characters with 0-placeholders. On a real-ECU K-line
        session the coding block is proprietary/unmapped, so we say so plainly
        rather than inventing a VIN.
        """
        def work() -> tuple[str | None, str]:
            try:
                full = self.backend.read_vin()
            except Exception:  # noqa: BLE001 - report, don't raise into Qt
                full = None
            if full and len(full) == 17:
                return full, "full VIN (OBD-II Service 09)"
            try:
                last6 = (self.backend.read_coding_text("vin_last6") or "").strip()
            except RealEcuUnsupported:
                return None, ("real ECU: full VIN unsupported (Service 09) and the "
                              "coding block is proprietary/unmapped — the full VIN "
                              "lives in the body/security module (BeCM / 10AS)")
            except Exception as exc:  # noqa: BLE001
                return None, f"error: {exc}"
            if not last6:
                return None, "no VIN coded in the ECU"
            padded = last6.rjust(17, "0")  # unknown first 11 -> 0-placeholders
            return padded, "last-6 from ECU coding (first 11 unknown)"

        def done(result: tuple[str | None, str]) -> None:
            value, source = result
            if value:
                self._ecu_vin.setText(f"{value}   [{source}]")
                self.status.emit(f"Read VIN — {source}")
            else:
                self._ecu_vin.setText(f"(not available) — {source}")
                self.status.emit("VIN not available from the ECU")

        def failed(exc: Exception) -> None:
            self._ecu_vin.setText(f"(read failed) — {exc}")
            self.status.emit(f"VIN read failed: {exc}")

        self.run_with_wait("Reading VIN from ECU", work, done, failed)

    # -- navigation --------------------------------------------------------- #
    def nav_buttons(self) -> set[str]:
        return {"back", "tick"}

    def on_tick(self) -> None:
        """Commit the chosen scenario, then advance to the system menu.

        The scenario change (re)connects the diagnostic session, so it runs
        behind the "Communicating with ECU" wait — the authentic pause before
        the tool trusts its vehicle configuration.
        """
        chosen = self._scenario.currentText()

        def work() -> str:
            if not self.backend.is_remote:  # scenario applies to the fake only
                self.backend.set_scenario(chosen)
            self.backend.connect()  # idempotent; opens the session if closed
            return chosen

        self.run_with_wait("Configuring vehicle systems", work, self._on_configured)

    def _on_configured(self, chosen: str) -> None:
        """The session is (re)configured — announce it and move on."""
        if self.backend.is_remote:
            self.status.emit(
                f"Vehicle configured · {self.backend.connection_label}"
            )
        else:
            self.status.emit(f"Vehicle configured · scenario: {chosen}")
        self.navigate.emit("system_menu")
