"""KodTR IDE koyu teması.

Fusion stili + koyu palet + uygulama geneli QSS. Renkleri değiştirmek
için RENK sözlüğünü düzenlemek yeterli.
"""

from PyQt6.QtGui import QColor, QPalette

RENK = {
    "zemin":       "#21252b",   # pencere, panel arkaplanı
    "zemin_koyu":  "#181a1f",   # kenarlıklar, ayraçlar
    "zemin_acik":  "#2c313a",   # hover, girişler
    "yuzey":       "#282c34",   # editör, menü
    "cizgi":       "#3b4048",   # ince kenarlıklar
    "tutamac":     "#3e4451",   # kaydırma çubuğu
    "yazi":        "#abb2bf",
    "yazi_soluk":  "#7f848e",
    "yazi_pasif":  "#4b5263",
    "vurgu":       "#e06c75",   # KodTR kırmızısının yumuşak hali
    "vurgu_yazi":  "#16191d",
}

QSS = """
QWidget {{
    background-color: {zemin};
    color: {yazi};
}}
QToolTip {{
    background-color: {yuzey};
    color: {yazi};
    border: 1px solid {cizgi};
    padding: 6px 8px;
}}

/* --- menü çubuğu ve menüler --- */
QMenuBar {{
    background-color: {zemin};
    border-bottom: 1px solid {zemin_koyu};
    padding: 2px 4px;
}}
QMenuBar::item {{
    background: transparent;
    padding: 5px 10px;
    border-radius: 5px;
}}
QMenuBar::item:selected {{ background-color: {zemin_acik}; }}
QMenu {{
    background-color: {yuzey};
    border: 1px solid {cizgi};
    border-radius: 8px;
    padding: 5px;
}}
QMenu::item {{
    padding: 6px 28px 6px 14px;
    border-radius: 5px;
}}
QMenu::item:selected {{
    background-color: {vurgu};
    color: {vurgu_yazi};
}}
QMenu::item:disabled {{ color: {yazi_pasif}; }}
QMenu::separator {{
    height: 1px;
    background-color: {cizgi};
    margin: 5px 10px;
}}

/* --- araç çubuğu --- */
QToolBar {{
    background-color: {zemin};
    border-bottom: 1px solid {zemin_koyu};
    padding: 4px 6px;
    spacing: 3px;
}}
QToolBar::separator {{
    width: 1px;
    background-color: {cizgi};
    margin: 4px 6px;
}}
QToolButton {{
    background: transparent;
    border-radius: 6px;
    padding: 5px 10px;
}}
QToolButton:hover {{ background-color: {zemin_acik}; }}
QToolButton:pressed {{ background-color: {cizgi}; }}
QToolButton:disabled {{ color: {yazi_pasif}; }}

/* --- blok ağacı --- */
QTreeWidget {{
    background-color: {zemin};
    border: none;
    padding: 4px;
}}
QTreeView::item {{
    padding: 4px 6px;
    border-radius: 5px;
}}
QTreeView::item:hover {{ background-color: {zemin_acik}; }}
QTreeView::item:selected {{
    background-color: {cizgi};
    color: {yazi};
}}
QTreeView::branch {{ background: transparent; }}

/* --- girişler --- */
QLineEdit {{
    background-color: {yuzey};
    border: 1px solid {cizgi};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {tutamac};
}}
QLineEdit:focus {{ border-color: {vurgu}; }}
QLineEdit:disabled {{
    color: {yazi_pasif};
    background-color: {zemin};
}}
QComboBox {{
    background-color: {zemin_acik};
    border: 1px solid {cizgi};
    border-radius: 6px;
    padding: 4px 12px;
}}
QComboBox:hover {{ border-color: {yazi_pasif}; }}
QComboBox QAbstractItemView {{
    background-color: {yuzey};
    border: 1px solid {cizgi};
    border-radius: 6px;
    padding: 4px;
    selection-background-color: {vurgu};
    selection-color: {vurgu_yazi};
}}
QPushButton {{
    background-color: {zemin_acik};
    border: 1px solid {cizgi};
    border-radius: 6px;
    padding: 6px 18px;
}}
QPushButton:hover {{ background-color: {cizgi}; }}
QPushButton:default {{ border-color: {vurgu}; }}

/* --- kaydırma çubukları --- */
QScrollBar:vertical {{
    background: transparent;
    width: 10px;
    margin: 0;
}}
QScrollBar:horizontal {{
    background: transparent;
    height: 10px;
    margin: 0;
}}
QScrollBar::handle {{
    background-color: {tutamac};
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{ min-height: 30px; }}
QScrollBar::handle:horizontal {{ min-width: 30px; }}
QScrollBar::handle:hover {{ background-color: {yazi_pasif}; }}
QScrollBar::add-line, QScrollBar::sub-line {{
    width: 0; height: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* --- ayraçlar ve durum çubuğu --- */
QSplitter::handle {{ background-color: {zemin_koyu}; }}
QSplitter::handle:horizontal {{ width: 2px; }}
QSplitter::handle:vertical {{ height: 2px; }}
QSplitter::handle:hover {{ background-color: {vurgu}; }}
QStatusBar {{
    background-color: {zemin};
    border-top: 1px solid {zemin_koyu};
    color: {yazi_soluk};
}}
QStatusBar QLabel {{ color: {yazi_soluk}; }}
QStatusBar::item {{ border: none; }}

/* --- panel başlıkları (objectName ile) --- */
QLabel#panelBaslik {{
    background-color: {zemin};
    color: {yazi_soluk};
    font-weight: bold;
    font-size: 8pt;
    padding: 6px 10px;
    border-bottom: 1px solid {zemin_koyu};
}}
""".format(**RENK)


def uygula(uygulama):
    """Fusion stili, koyu palet ve QSS'i uygular."""
    uygulama.setStyle("Fusion")

    p = QPalette()
    gruplar = {
        QPalette.ColorRole.Window: "zemin",
        QPalette.ColorRole.WindowText: "yazi",
        QPalette.ColorRole.Base: "yuzey",
        QPalette.ColorRole.AlternateBase: "zemin_acik",
        QPalette.ColorRole.Text: "yazi",
        QPalette.ColorRole.Button: "zemin_acik",
        QPalette.ColorRole.ButtonText: "yazi",
        QPalette.ColorRole.ToolTipBase: "yuzey",
        QPalette.ColorRole.ToolTipText: "yazi",
        QPalette.ColorRole.Highlight: "vurgu",
        QPalette.ColorRole.HighlightedText: "vurgu_yazi",
        QPalette.ColorRole.PlaceholderText: "yazi_pasif",
        QPalette.ColorRole.Link: "vurgu",
    }
    for rol, ad in gruplar.items():
        p.setColor(rol, QColor(RENK[ad]))
    p.setColor(QPalette.ColorGroup.Disabled,
               QPalette.ColorRole.Text, QColor(RENK["yazi_pasif"]))
    p.setColor(QPalette.ColorGroup.Disabled,
               QPalette.ColorRole.ButtonText, QColor(RENK["yazi_pasif"]))
    uygulama.setPalette(p)
    uygulama.setStyleSheet(QSS)
