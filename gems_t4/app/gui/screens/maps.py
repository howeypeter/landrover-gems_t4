"""Engine-maps screen — a READ-ONLY chip-swap lookalike.

GEMS calibration lives in two socketed UV-EPROMs and is **not** reflashable
over the K-line — that path never existed for GEMS (see
:mod:`gems_t4.gems.maps`). Real remapping is a bench operation: pull the chip,
read/edit/burn, refit. So this screen surfaces the fuel/ignition maps as
viewable 16x16 tables plus the EPROM chip facts, with the honest note that
there is no "write" here. There is deliberately no editing and no tick button.

A combo selects the map (``fuel`` / ``ignition``); the 16x16 grid uses the
map's RPM breakpoints as horizontal headers and load-% breakpoints as vertical
headers, filled from :meth:`MapTable.cell`. Changing the combo reloads the grid.
"""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from gems_t4.app.backend import Backend
from gems_t4.app.gui.base import Screen
from gems_t4.gems.maps import (
    CHIP_SWAP_NOTE,
    FUEL_EPROM,
    IGNITION_EPROM,
    EpromChip,
    MapTable,
)

#: Which EPROM to show alongside each selectable map token.
_MAP_EPROM: dict[str, EpromChip] = {"fuel": FUEL_EPROM, "ignition": IGNITION_EPROM}


class MapsScreen(Screen):
    """Read-only 16x16 fuel/ignition map viewer + the EPROM chip facts."""

    title = "Engine Maps — READ ONLY (chip-swap lookalike)"

    def __init__(self, backend: Backend, parent: QWidget | None = None) -> None:
        super().__init__(backend, parent)

        #: The map tokens the backend offers ("fuel", "ignition").
        self._tokens: list[str] = list(self.backend.available_maps())

        lay = QVBoxLayout(self)
        lay.setContentsMargins(20, 16, 20, 16)
        lay.setSpacing(8)

        # -- top control row: map selector + name/unit ---------------------- #
        controls = QHBoxLayout()
        controls.setSpacing(8)
        controls.addWidget(QLabel("Map:"))

        self._map_box = QComboBox()
        for token in self._tokens:
            self._map_box.addItem(token.capitalize(), token)
        self._map_box.currentIndexChanged.connect(self._on_map_changed)
        controls.addWidget(self._map_box)

        controls.addStretch(1)

        self._name_label = QLabel("", objectName="Lcd")
        controls.addWidget(self._name_label)
        lay.addLayout(controls)

        # -- the 16x16 grid (read-only) ------------------------------------- #
        self._table = QTableWidget(0, 0)
        self._table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._table.horizontalHeader().setStretchLastSection(False)
        lay.addWidget(self._table, 1)

        # -- EPROM chip facts ----------------------------------------------- #
        self._chip_label = QLabel("", objectName="Lcd")
        self._chip_label.setWordWrap(True)
        lay.addWidget(self._chip_label)

        # -- the honest "no reflash" note ----------------------------------- #
        self._note_label = QLabel(CHIP_SWAP_NOTE)
        self._note_label.setWordWrap(True)
        self._note_label.setStyleSheet("font-size: 12px; color: #404040;")
        lay.addWidget(self._note_label)

    # -- helpers ------------------------------------------------------------ #
    def _selected_token(self) -> str:
        """The map token for the current combo selection."""
        data = self._map_box.currentData()
        if isinstance(data, str):
            return data
        # Fallback (empty selection): first available token.
        return self._tokens[0]

    def _load_table(self, token: str) -> None:
        """Fill the grid with the selected map: axes as headers, cells as text."""
        table: MapTable = self.backend.get_map(token)

        self._table.clear()
        self._table.setColumnCount(table.cols)
        self._table.setRowCount(table.rows)
        self._table.setHorizontalHeaderLabels([str(r) for r in table.rpm_axis])
        self._table.setVerticalHeaderLabels([str(l) for l in table.load_axis])

        for row in range(table.rows):
            for col in range(table.cols):
                item = QTableWidgetItem(f"{table.cell(row, col):g}")
                item.setTextAlignment(Qt.AlignCenter)
                # Belt-and-braces: the value cells are not editable.
                item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self._table.setItem(row, col, item)

        self._name_label.setText(f"{table.name}  [{table.unit}]")
        self._update_chip_facts(token)

    def _update_chip_facts(self, token: str) -> None:
        """Show the socketed-EPROM facts for the selected map."""
        chip = _MAP_EPROM.get(token)
        if chip is None:
            self._chip_label.setText("")
            return
        self._chip_label.setText(
            f"EPROM: {chip.part} · {chip.size_kb} KB · holds {chip.holds}"
        )

    # -- lifecycle ---------------------------------------------------------- #
    def on_enter(self) -> None:
        """(Re)load the currently selected map each time the screen is shown."""
        self._load_table(self._selected_token())
        self.status.emit(
            "Read-only map view — no K-line write path for GEMS calibration"
        )

    # -- controls ----------------------------------------------------------- #
    def _on_map_changed(self, _index: int) -> None:
        """Reload the grid for the newly selected map."""
        self._load_table(self._selected_token())

    # -- nav buttons -------------------------------------------------------- #
    def nav_buttons(self) -> set[str]:
        return {"back"}
