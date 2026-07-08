"""Coding / settings screen — read / edit / write the ECU coding block.

The GEMS coding block holds the small, writable identity fields (VIN last-6,
dealer id, 4.0/4.6 select, transmission, build code) plus read-only factory
fields (market, ECU part number). This screen reads the whole block into a
table, lets the technician edit a *writable* field's value, and writes it back
through the mandatory safety gates in :mod:`gems_t4.gems.programming`:

    backup = backend.backup_coding(field)
    backend.write_coding(field, encoded, backup=backup, confirm=...)

The confirmation is a two-step *inline* one (arm on first press, commit on the
second) — modelled on ``fault_codes.py``'s clear — rather than a blocking modal,
which keeps the kiosk flow and the headless tests simple. Read-only fields are
visibly non-editable and the Write action refuses them with a reason.

The block read (populate) and the backup+write commit run behind the
"Communicating with ECU" wait (``run_with_wait``) — a coding write is several
K-line exchanges (read, backup-verify, write, verify) and the pause before the
verified result is authentic. In instant mode this degrades to the old
synchronous behaviour.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen
from gems_t4.app.gui.style import GREEN_OK, RED_BAD
from gems_t4.gems.programming import CodingField, ProgrammingRefused

#: Custom item-data role storing the field key on the first-column item.
_KEY_ROLE = int(Qt.UserRole)


def _grey() -> QBrush:
    """A grey brush for greying out read-only rows."""
    return QBrush(QColor("#808080"))


class CodingScreen(Screen):
    """Read / edit / write the ECU coding block, with the write safety gates."""

    title = "Coding / Settings"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)
        #: Field key currently loaded into the editor (None if none selected).
        self._selected_key: str | None = None
        #: True once Write has been armed and is awaiting a confirming second press.
        self._pending_write = False
        #: The CodingField objects, keyed by key, cached from the backend.
        self._fields: dict[str, CodingField] = {}

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(8)

        caption = QLabel("ECU coding block — select a writable field to edit")
        caption.setStyleSheet("font-weight: bold;")
        lay.addWidget(caption)

        self._table = QTableWidget(0, 3)
        self._table.setHorizontalHeaderLabels(["Field", "Value", "Writable"])
        self._table.verticalHeader().setVisible(False)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.setSelectionBehavior(QTableWidget.SelectRows)
        self._table.setSelectionMode(QTableWidget.SingleSelection)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.setColumnWidth(0, 200)
        self._table.setColumnWidth(1, 240)
        self._table.itemSelectionChanged.connect(self._on_selection_changed)
        lay.addWidget(self._table, 1)

        # -- editor row: label + line edit + write button ------------------- #
        editor = QHBoxLayout()
        editor.setSpacing(8)
        self._edit_label = QLabel("New value:")
        editor.addWidget(self._edit_label)

        self._value_edit = QLineEdit()
        self._value_edit.setEnabled(False)
        editor.addWidget(self._value_edit, 1)

        self._write_btn = QPushButton("Write", objectName="MenuItem")
        self._write_btn.setEnabled(False)
        self._write_btn.clicked.connect(self._write)
        editor.addWidget(self._write_btn)
        lay.addLayout(editor)

        # -- readout label (success green / failure red) -------------------- #
        self._readout = QLabel("")
        self._readout.setWordWrap(True)
        lay.addWidget(self._readout)

        self._hint = QLabel("Select a field · edit its value · press Write")
        self._hint.setStyleSheet("color: #404040;")
        lay.addWidget(self._hint)

    # -- data --------------------------------------------------------------- #
    def on_enter(self) -> None:
        """Populate the coding table fresh from the backend."""
        self._fields = {f.key: f for f in self.backend.coding_fields()}
        self._pending_write = False
        self._selected_key = None
        self._readout.setText("")
        self._populate()

    def _populate(self, reselect: str | None = None) -> None:
        """Read the whole coding block behind the wait, then fill the table.

        ``reselect`` names a field key to re-select once the table is rebuilt
        (used after a write, when the refresh would otherwise drop selection).
        """
        fields = list(self._fields.values())

        def work() -> list[tuple[CodingField, str]]:
            rows: list[tuple[CodingField, str]] = []
            for f in fields:
                try:
                    value = self.backend.read_coding_text(f.key)
                except Exception as exc:  # pragma: no cover - defensive
                    value = f"<error: {exc}>"
                rows.append((f, value))
            return rows

        def done(rows: list[tuple[CodingField, str]]) -> None:
            self._table.setRowCount(len(rows))
            for row, (f, value) in enumerate(rows):
                self._set_row(row, f, value)
            self.status.emit(f"{len(rows)} coding field(s)")
            if reselect is not None:
                self._reselect(reselect)

        self.run_with_wait("Reading coding block", work, done)

    def _set_row(self, row: int, f: CodingField, value: str) -> None:
        key_item = QTableWidgetItem(f.name)
        key_item.setData(_KEY_ROLE, f.key)
        val_item = QTableWidgetItem(value)
        writable_item = QTableWidgetItem("yes" if f.writable else "no (read-only)")
        for item in (key_item, val_item, writable_item):
            if not f.writable:
                # Visibly non-editable: greyed text on read-only rows.
                item.setForeground(_grey())
        self._table.setItem(row, 0, key_item)
        self._table.setItem(row, 1, val_item)
        self._table.setItem(row, 2, writable_item)

    # -- selection ---------------------------------------------------------- #
    def _on_selection_changed(self) -> None:
        """Load the selected field's value into the editor; gate read-only fields."""
        self._pending_write = False
        key = self._current_row_key()
        self._selected_key = key
        if key is None:
            self._value_edit.setEnabled(False)
            self._value_edit.clear()
            self._write_btn.setEnabled(False)
            return

        f = self._fields[key]
        current = self.backend.read_coding_text(key)
        self._value_edit.setText(current)
        if f.writable:
            self._value_edit.setEnabled(True)
            self._write_btn.setEnabled(True)
            self._write_btn.setText("Write")
            self._hint.setText(f"Editing {f.name} · press Write to save")
            self.status.emit(f"Editing {f.name}")
        else:
            self._value_edit.setEnabled(False)
            self._write_btn.setEnabled(False)
            self._write_btn.setText("Write")
            self._hint.setText(f"{f.name} is read-only — cannot be written")
            self.status.emit(f"{f.name} is read-only")

    def _current_row_key(self) -> str | None:
        items = self._table.selectedItems()
        if not items:
            return None
        key_item = self._table.item(items[0].row(), 0)
        if key_item is None:
            return None
        key = key_item.data(_KEY_ROLE)
        return str(key) if key is not None else None

    # -- write (two-step inline confirm + gated flow) ----------------------- #
    def _write(self) -> None:
        """Write the edited value through the gated flow with inline confirm."""
        key = self._selected_key
        if key is None:
            return
        f = self._fields[key]
        if not f.writable:
            # Read-only field selected — refuse and say why.
            self._pending_write = False
            self._write_btn.setText("Write")
            self._show_failure(f"{f.name} is read-only — cannot be written.")
            return

        new_text = self._value_edit.text()

        # First press: arm the confirmation.
        if not self._pending_write:
            self._pending_write = True
            self._write_btn.setText("Confirm")
            msg = f"Write {f.name} = {new_text!r}? Press Write again to confirm."
            self.status.emit(msg)
            self._hint.setText("⚠ Press Write again to confirm")
            self._readout.setText(msg)
            self._readout.setStyleSheet(f"color: {RED_BAD};")
            return

        # Second press: commit through every safety gate.
        self._pending_write = False
        self._write_btn.setText("Write")
        try:
            value = self.backend.encode_coding_text(key, new_text)
        except ValueError as exc:
            self._show_failure(f"Bad value: {exc}")
            return

        # backup + gated write are several K-line exchanges — behind the wait.
        def work():
            backup = self.backend.backup_coding(key)
            return self.backend.write_coding(
                key, value, backup=backup, confirm=lambda: True
            )

        def done(result) -> None:
            if result.ok:
                self._show_success(f"{f.name}: {result.message}")
                self._populate(reselect=key)
            else:
                self._show_failure(f"{f.name}: {result.message}")

        def fail(exc: Exception) -> None:
            if isinstance(exc, ProgrammingRefused):
                self._show_failure(f"Refused: {exc}")
            elif isinstance(exc, ValueError):  # pragma: no cover - encode caught
                self._show_failure(f"Bad value: {exc}")
            else:  # pragma: no cover - defensive
                self._show_failure(f"Error: {exc}")

        self.run_with_wait(f"Writing {f.name}", work, done, fail)

    def _reselect(self, key: str) -> None:
        """Re-select the row for ``key`` after a table refresh."""
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            if item is not None and item.data(_KEY_ROLE) == key:
                self._table.selectRow(row)
                return

    # -- readout helpers ---------------------------------------------------- #
    def _show_success(self, text: str) -> None:
        self._readout.setText(text)
        self._readout.setStyleSheet(f"color: {GREEN_OK}; font-weight: bold;")
        self.status.emit(text)

    def _show_failure(self, text: str) -> None:
        self._readout.setText(text)
        self._readout.setStyleSheet(f"color: {RED_BAD}; font-weight: bold;")
        self.status.emit(text)

    # -- nav buttons -------------------------------------------------------- #
    def nav_buttons(self) -> set[str]:
        return {"back"}
