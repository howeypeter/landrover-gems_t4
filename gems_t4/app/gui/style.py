"""Win98 dealer-tool aesthetic: palette constants + a Qt stylesheet.

Target look (per CLAUDE.md design pillars): 800x600, beveled buttons, tan/grey
palette, blue title bar, MS-Sans-style font. Qt Style Sheets can fake the classic
raised/sunken 3D bevels with ``border-style: outset/inset`` and the silver
(#c0c0c0) surface color.

Screens should use the object names / classes referenced here rather than
hard-coding colors, so the whole look changes in one place.
"""
from __future__ import annotations

# -- palette ---------------------------------------------------------------- #
SILVER = "#c0c0c0"        # classic Win98 face color
SILVER_LIGHT = "#dfdfdf"
SHADOW = "#808080"
DARK_SHADOW = "#404040"
TITLE_BLUE = "#000080"    # active title bar
TITLE_BLUE_2 = "#1084d0"  # title bar gradient end
INK = "#000000"
LCD_BG = "#20241f"        # message-centre / gauge readout background
LCD_AMBER = "#ffb300"     # amber dot-matrix text
GREEN_OK = "#0a7d28"
RED_BAD = "#a5140a"
FONT = '"Tahoma", "MS Sans Serif", "Segoe UI", sans-serif'

#: Fixed kiosk size (the period 800x600 dealer screen).
SCREEN_W = 800
SCREEN_H = 600

WIN98_QSS = f"""
* {{
    font-family: {FONT};
    font-size: 13px;
    color: {INK};
}}
QMainWindow, QWidget#Kiosk {{
    background: {SILVER};
}}
/* Title bar across the top of the kiosk */
QLabel#TitleBar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {TITLE_BLUE}, stop:1 {TITLE_BLUE_2});
    color: white;
    font-weight: bold;
    font-size: 14px;
    padding: 5px 10px;
}}
QLabel#StatusBar {{
    background: {SILVER};
    border-top: 2px groove {SILVER_LIGHT};
    color: {DARK_SHADOW};
    padding: 3px 8px;
    font-size: 11px;
}}
/* The content area between title bar and button bar */
QWidget#Content {{
    background: {SILVER};
}}
QFrame#ButtonBar {{
    background: {SILVER};
    border-top: 2px groove {SILVER_LIGHT};
}}
/* Beveled buttons — the raised 3D look, sunk when pressed */
QPushButton {{
    background: {SILVER};
    border: 2px outset {SILVER_LIGHT};
    padding: 6px 14px;
    min-height: 20px;
}}
QPushButton:pressed {{
    border: 2px inset {SHADOW};
    padding-top: 7px;
    padding-left: 15px;
}}
QPushButton:disabled {{
    color: {SHADOW};
}}
QPushButton:focus {{
    outline: 1px dotted {DARK_SHADOW};
}}
/* Big nav buttons in the tick/cross/back bar */
QPushButton#NavTick {{ font-size: 20px; font-weight: bold; color: {GREEN_OK}; min-width: 56px; }}
QPushButton#NavCross {{ font-size: 20px; font-weight: bold; color: {RED_BAD}; min-width: 56px; }}
QPushButton#NavBack {{ min-width: 96px; }}
/* Menu-style list buttons (system selection etc.) */
QPushButton#MenuItem {{
    text-align: left;
    padding: 10px 16px;
    font-size: 14px;
}}
/* Sunken panels / group frames */
QFrame#Sunken, QGroupBox {{
    background: {SILVER};
    border: 2px inset {SHADOW};
}}
QGroupBox {{
    margin-top: 10px;
    padding: 12px 8px 8px 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}
/* Tables (fault codes, live data) */
QTableWidget, QTableView {{
    background: white;
    border: 2px inset {SHADOW};
    gridline-color: {SILVER};
    selection-background-color: {TITLE_BLUE};
    selection-color: white;
}}
QHeaderView::section {{
    background: {SILVER};
    border: 1px outset {SILVER_LIGHT};
    padding: 3px 6px;
    font-weight: bold;
}}
/* Line edits / spin (VIN entry) */
QLineEdit, QComboBox {{
    background: white;
    border: 2px inset {SHADOW};
    padding: 3px 6px;
    selection-background-color: {TITLE_BLUE};
    selection-color: white;
}}
/* LCD-style readout labels */
QLabel#Lcd {{
    background: {LCD_BG};
    color: {LCD_AMBER};
    font-family: "Consolas", "Courier New", monospace;
    border: 2px inset {DARK_SHADOW};
    padding: 4px 8px;
    letter-spacing: 1px;
}}
QProgressBar {{
    background: white;
    border: 2px inset {SHADOW};
    text-align: center;
}}
QProgressBar::chunk {{
    background: {TITLE_BLUE};
}}
"""
