"""Win98 dealer-tool aesthetic: palette constants + a Qt stylesheet.

Target look (per CLAUDE.md design pillars): 800x600, beveled buttons, tan/grey
palette, blue title bar, MS-Sans-style font. Qt Style Sheets fake the classic
raised/sunken 3D bevels with explicit per-side borders (white top-left +
dark-grey bottom-right = raised; inverted = sunken) on the silver (#c0c0c0)
surface color — crisper than Qt's generic ``outset``/``inset`` shading.

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

# Extra period colors used by the stylesheet.
WHITE = "#ffffff"
TROUGH = "#efefef"        # scrollbar trough — the dithered silver-on-white feel
TOOLTIP_YELLOW = "#ffffe1"  # classic Win98 tooltip

#: Fixed kiosk size (the period 800x600 dealer screen).
SCREEN_W = 800
SCREEN_H = 600

# -- generated glyph assets -------------------------------------------------- #
# QSS cannot draw the solid black Win98 arrow/check glyphs itself (the classic
# zero-size border-triangle trick renders as a filled rectangle in Qt), so the
# tiny bitmaps are rasterised once into a temp dir and referenced with url().
# Pure QImage pixel work — safe at import time, before any QApplication exists.
import os as _os
import tempfile as _tempfile

_GLYPHS: dict[str, tuple[str, ...]] = {
    "up": (
        "...#...",
        "..###..",
        ".#####.",
        "#######",
    ),
    "down": (
        "#######",
        ".#####.",
        "..###..",
        "...#...",
    ),
    "left": (
        "...#",
        "..##",
        ".###",
        "####",
        ".###",
        "..##",
        "...#",
    ),
    "right": (
        "#...",
        "##..",
        "###.",
        "####",
        "###.",
        "##..",
        "#...",
    ),
    "check": (
        "......#",
        ".....##",
        "....###",
        "#..###.",
        "#####..",
        ".###...",
        "..#....",
    ),
    "dot": (
        ".###.",
        "#####",
        "#####",
        "#####",
        ".###.",
    ),
}


def _write_glyphs() -> dict[str, str]:
    """Rasterise the glyph bitmaps ('#' = black) to PNGs; return ``image:`` fragments."""
    from PySide6.QtGui import QImage

    out_dir = _os.path.join(_tempfile.gettempdir(), "gems_t4_glyphs")
    _os.makedirs(out_dir, exist_ok=True)
    frags: dict[str, str] = {}
    for name, rows in _GLYPHS.items():
        w, h = max(len(r) for r in rows), len(rows)
        img = QImage(w, h, QImage.Format.Format_ARGB32)
        img.fill(0)
        for y, row in enumerate(rows):
            for x, ch in enumerate(row):
                if ch == "#":
                    img.setPixel(x, y, 0xFF000000)
        path = _os.path.join(out_dir, f"{name}.png")
        if not img.save(path):
            raise OSError(f"could not write {path}")
        frags[name] = f'image: url("{path.replace(chr(92), "/")}");'
    return frags


try:
    _IMG = _write_glyphs()
except Exception:  # pragma: no cover - cosmetic-only degradation (blank glyphs)
    _IMG = {name: "" for name in _GLYPHS}

# Reusable bevel fragments (per-side borders read like the real UxTheme-free
# Win98 chrome: light source top-left).
_RAISED = f"""
    border-top: 2px solid {WHITE};
    border-left: 2px solid {WHITE};
    border-right: 2px solid {DARK_SHADOW};
    border-bottom: 2px solid {DARK_SHADOW};
"""
_SUNKEN = f"""
    border-top: 2px solid {SHADOW};
    border-left: 2px solid {SHADOW};
    border-right: 2px solid {WHITE};
    border-bottom: 2px solid {WHITE};
"""
_RAISED_THIN = f"""
    border-top: 1px solid {WHITE};
    border-left: 1px solid {WHITE};
    border-right: 1px solid {DARK_SHADOW};
    border-bottom: 1px solid {DARK_SHADOW};
"""
_SUNKEN_THIN = f"""
    border-top: 1px solid {SHADOW};
    border-left: 1px solid {SHADOW};
    border-right: 1px solid {WHITE};
    border-bottom: 1px solid {WHITE};
"""

WIN98_QSS = f"""
/* ===== base / kiosk chrome ============================================== */
* {{
    font-family: {FONT};
    font-size: 13px;
    color: {INK};
}}
QMainWindow, QWidget#Kiosk {{
    background: {SILVER};
}}
/* Title bar across the top of the kiosk: a QFrame row holding the screen
   title (left) and the persistent connection-status button (right). */
QFrame#TitleBar {{
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                stop:0 {TITLE_BLUE}, stop:1 {TITLE_BLUE_2});
    padding: 5px 0px;
}}
QFrame#TitleBar QLabel {{
    background: transparent;
    color: white;
    font-weight: bold;
    font-size: 14px;
}}
/* Compact so it fits the thin title row without stretching it */
QPushButton#ConnectionStatus {{
    padding: 2px 10px;
    min-height: 0px;
    font-size: 11px;
}}
QPushButton#ConnectionStatus:pressed {{
    padding-top: 3px;
    padding-left: 11px;
    padding-bottom: 1px;
}}
QLabel#StatusBar {{
    background: {SILVER};
    border-top: 1px solid {SHADOW};
    border-bottom: 1px solid {WHITE};
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
    border-top: 1px solid {WHITE};
}}

/* ===== buttons ========================================================== */
/* Beveled buttons — light top-left, dark bottom-right; sunk when pressed */
QPushButton {{
    background: {SILVER};
    {_RAISED}
    padding: 6px 14px;
    min-height: 20px;
}}
QPushButton:pressed {{
    {_SUNKEN}
    padding-top: 7px;
    padding-left: 15px;
    padding-bottom: 5px;
    padding-right: 13px;
}}
QPushButton:disabled {{
    color: {SHADOW};
}}
/* Approximate the Win98 dotted focus rectangle just inside the bevel */
QPushButton:focus {{
    outline: 1px dotted {INK};
    outline-offset: -5px;
}}
/* Big nav buttons in the tick/cross/back bar */
QPushButton#NavTick {{ font-size: 20px; font-weight: bold; color: {GREEN_OK}; min-width: 56px; }}
QPushButton#NavCross {{ font-size: 20px; font-weight: bold; color: {RED_BAD}; min-width: 56px; }}
QPushButton#NavBack {{ min-width: 96px; }}
QPushButton#NavTick:disabled, QPushButton#NavCross:disabled {{ color: {SHADOW}; }}
/* Menu-style list buttons (system selection etc.) */
QPushButton#MenuItem {{
    text-align: left;
    padding: 10px 16px;
    font-size: 14px;
}}
QPushButton#MenuItem:pressed {{
    padding: 11px 15px 9px 17px;
}}

/* ===== panels / frames ================================================== */
QFrame#Sunken {{
    background: {SILVER};
    {_SUNKEN}
}}
/* Group boxes get the classic etched (groove) outline with the label
   punched through it on the face color */
QGroupBox {{
    background: {SILVER};
    border: 2px groove {SILVER_LIGHT};
    margin-top: 8px;
    padding: 10px 8px 8px 8px;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 8px;
    padding: 0 3px;
    background: {SILVER};
}}
/* Scroll areas: sunken well, silver inside (the gauge grid sits on the face) */
QScrollArea {{
    background: {SILVER};
    {_SUNKEN}
}}
QScrollArea > QWidget > QWidget {{
    background: {SILVER};
}}
QAbstractScrollArea::corner {{
    background: {SILVER};
}}

/* ===== tables / lists / headers ========================================= */
QTableWidget, QTableView, QListWidget, QListView, QTreeView {{
    background: white;
    alternate-background-color: white;   /* period tables are plain white */
    {_SUNKEN}
    gridline-color: {SILVER};
    selection-background-color: {TITLE_BLUE};
    selection-color: white;
    outline: none;                        /* selection itself is the cue */
}}
QTableWidget::item:selected, QListWidget::item:selected {{
    background: {TITLE_BLUE};
    color: white;
}}
QHeaderView::section {{
    background: {SILVER};
    {_RAISED_THIN}
    padding: 3px 6px;
    font-weight: bold;
}}
QHeaderView::section:pressed {{
    {_SUNKEN_THIN}
    padding: 4px 5px 2px 7px;
}}
QTableCornerButton::section {{
    background: {SILVER};
    {_RAISED_THIN}
}}

/* ===== text entry ======================================================= */
QLineEdit, QSpinBox, QDoubleSpinBox, QTextEdit, QPlainTextEdit {{
    background: white;
    {_SUNKEN}
    padding: 3px 6px;
    selection-background-color: {TITLE_BLUE};
    selection-color: white;
}}
QLineEdit:disabled, QSpinBox:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    background: {SILVER};
    color: {SHADOW};
}}
/* Spin buttons: little raised bevels with black glyph arrows */
QSpinBox::up-button, QDoubleSpinBox::up-button,
QSpinBox::down-button, QDoubleSpinBox::down-button {{
    background: {SILVER};
    {_RAISED_THIN}
    width: 15px;
}}
QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed,
QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {{
    {_SUNKEN_THIN}
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    {_IMG["up"]}
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    {_IMG["down"]}
}}

/* ===== combo boxes ====================================================== */
QComboBox {{
    background: white;
    {_SUNKEN}
    padding: 3px 22px 3px 6px;
    selection-background-color: {TITLE_BLUE};
    selection-color: white;
}}
QComboBox:disabled {{
    background: {SILVER};
    color: {SHADOW};
}}
/* The drop-down button: a raised silver bevel sitting inside the sunken well */
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 17px;
    background: {SILVER};
    {_RAISED_THIN}
}}
QComboBox::drop-down:pressed {{
    {_SUNKEN_THIN}
}}
QComboBox::down-arrow {{
    {_IMG["down"]}
}}
QComboBox::down-arrow:on {{
    top: 1px; left: 1px;   /* nudge like the period control */
}}
/* The popup list: white, framed like a Win98 menu, navy highlight */
QComboBox QAbstractItemView {{
    background: white;
    {_RAISED}
    selection-background-color: {TITLE_BLUE};
    selection-color: white;
    outline: none;
}}

/* ===== check boxes / radio buttons ====================================== */
QCheckBox, QRadioButton {{
    background: transparent;
    spacing: 6px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 13px;
    height: 13px;
    background: white;
    {_SUNKEN_THIN}
}}
QRadioButton::indicator {{
    border-radius: 7px;
}}
QCheckBox::indicator:checked {{
    {_IMG["check"]}
}}
QRadioButton::indicator:checked {{
    {_IMG["dot"]}
}}
QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
    background: {SILVER};
}}
QCheckBox:disabled, QRadioButton:disabled {{
    color: {SHADOW};
}}

/* ===== scrollbars ======================================================= */
/* The chunky 16px silver scrollbar: beveled arrow buttons at the ends, a
   raised handle, pale dithered-looking trough */
QScrollBar:vertical {{
    background: {TROUGH};
    width: 16px;
    margin: 16px 0 16px 0;
    border: none;
}}
QScrollBar:horizontal {{
    background: {TROUGH};
    height: 16px;
    margin: 0 16px 0 16px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: {SILVER};
    {_RAISED_THIN}
    min-height: 24px;
}}
QScrollBar::handle:horizontal {{
    background: {SILVER};
    {_RAISED_THIN}
    min-width: 24px;
}}
/* Arrow buttons live in the margins at the ends */
QScrollBar::sub-line:vertical {{
    background: {SILVER};
    {_RAISED_THIN}
    height: 16px;
    subcontrol-position: top;
    subcontrol-origin: margin;
}}
QScrollBar::add-line:vertical {{
    background: {SILVER};
    {_RAISED_THIN}
    height: 16px;
    subcontrol-position: bottom;
    subcontrol-origin: margin;
}}
QScrollBar::sub-line:horizontal {{
    background: {SILVER};
    {_RAISED_THIN}
    width: 16px;
    subcontrol-position: left;
    subcontrol-origin: margin;
}}
QScrollBar::add-line:horizontal {{
    background: {SILVER};
    {_RAISED_THIN}
    width: 16px;
    subcontrol-position: right;
    subcontrol-origin: margin;
}}
QScrollBar::sub-line:vertical:pressed, QScrollBar::add-line:vertical:pressed,
QScrollBar::sub-line:horizontal:pressed, QScrollBar::add-line:horizontal:pressed {{
    {_SUNKEN_THIN}
}}
/* Solid black arrow glyphs (generated PNGs — see _write_glyphs above) */
QScrollBar::up-arrow:vertical {{
    {_IMG["up"]}
}}
QScrollBar::down-arrow:vertical {{
    {_IMG["down"]}
}}
QScrollBar::left-arrow:horizontal {{
    {_IMG["left"]}
}}
QScrollBar::right-arrow:horizontal {{
    {_IMG["right"]}
}}
/* Keep the page areas showing the trough */
QScrollBar::add-page, QScrollBar::sub-page {{
    background: {TROUGH};
}}

/* ===== LCD readouts / progress / tooltips =============================== */
/* LCD-style readout labels */
QLabel#Lcd {{
    background: {LCD_BG};
    color: {LCD_AMBER};
    font-family: "Consolas", "Courier New", monospace;
    border-top: 2px solid {SHADOW};
    border-left: 2px solid {SHADOW};
    border-right: 2px solid {SILVER_LIGHT};
    border-bottom: 2px solid {SILVER_LIGHT};
    padding: 4px 8px;
    letter-spacing: 1px;
}}
/* Progress: the classic segmented marching blue blocks in a sunken well */
QProgressBar {{
    background: white;
    {_SUNKEN}
    text-align: center;
    color: {INK};
}}
QProgressBar::chunk {{
    background: {TITLE_BLUE};
    width: 10px;
    margin: 1px;
}}
/* The pale-yellow Win98 tooltip */
QToolTip {{
    background: {TOOLTIP_YELLOW};
    color: {INK};
    border: 1px solid {INK};
    padding: 2px 4px;
    font-size: 12px;
}}
"""
