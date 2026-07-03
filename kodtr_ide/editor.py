"""KodTR editör bileşeni: satır numarası, aktif satır vurgusu, otomatik girinti."""

from PyQt6.QtCore import QRect, QSize, Qt
from PyQt6.QtGui import QColor, QFont, QFontDatabase, QPainter, QTextFormat
from PyQt6.QtWidgets import QPlainTextEdit, QTextEdit, QWidget

from .vurgulayici import KodTRVurgulayici

ARKAPLAN = QColor("#282c34")
YAZI = QColor("#abb2bf")
AKTIF_SATIR = QColor("#2c313a")
NUMARA_ALANI = QColor("#21252b")
NUMARA_YAZI = QColor("#495162")
GIRINTI = "    "  # 4 boşluk


class _NumaraAlani(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.numara_genisligi(), 0)

    def paintEvent(self, olay):
        self.editor.numara_ciz(olay)


class KodTREditor(QPlainTextEdit):
    def __init__(self, ebeveyn=None):
        super().__init__(ebeveyn)

        yazi_tipi = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        yazi_tipi.setPointSize(12)
        self.setFont(yazi_tipi)
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(" ") * 4)

        self.setStyleSheet(
            f"QPlainTextEdit {{ background-color: {ARKAPLAN.name()};"
            f" color: {YAZI.name()}; border: none; }}"
        )

        self.vurgulayici = KodTRVurgulayici(self.document())

        self.numara_alani = _NumaraAlani(self)
        self.blockCountChanged.connect(self._numara_genislik_guncelle)
        self.updateRequest.connect(self._numara_alani_guncelle)
        self.cursorPositionChanged.connect(self._aktif_satiri_vurgula)
        self._numara_genislik_guncelle()
        self._aktif_satiri_vurgula()

    # --- satır numarası alanı -------------------------------------------
    def numara_genisligi(self):
        basamak = max(3, len(str(self.blockCount())))
        return 16 + self.fontMetrics().horizontalAdvance("9") * basamak

    def _numara_genislik_guncelle(self):
        self.setViewportMargins(self.numara_genisligi(), 0, 0, 0)

    def _numara_alani_guncelle(self, dikdortgen, kaydirma):
        if kaydirma:
            self.numara_alani.scroll(0, kaydirma)
        else:
            self.numara_alani.update(0, dikdortgen.y(),
                                     self.numara_alani.width(),
                                     dikdortgen.height())
        if dikdortgen.contains(self.viewport().rect()):
            self._numara_genislik_guncelle()

    def resizeEvent(self, olay):
        super().resizeEvent(olay)
        icerik = self.contentsRect()
        self.numara_alani.setGeometry(
            QRect(icerik.left(), icerik.top(),
                  self.numara_genisligi(), icerik.height()))

    def numara_ciz(self, olay):
        boyaci = QPainter(self.numara_alani)
        boyaci.fillRect(olay.rect(), NUMARA_ALANI)
        boyaci.setFont(self.font())

        blok = self.firstVisibleBlock()
        numara = blok.blockNumber()
        ust = round(self.blockBoundingGeometry(blok)
                    .translated(self.contentOffset()).top())
        alt = ust + round(self.blockBoundingRect(blok).height())

        while blok.isValid() and ust <= olay.rect().bottom():
            if blok.isVisible() and alt >= olay.rect().top():
                boyaci.setPen(NUMARA_YAZI)
                boyaci.drawText(0, ust, self.numara_alani.width() - 8,
                                self.fontMetrics().height(),
                                Qt.AlignmentFlag.AlignRight, str(numara + 1))
            blok = blok.next()
            ust = alt
            alt = ust + round(self.blockBoundingRect(blok).height())
            numara += 1

    # --- aktif satır ----------------------------------------------------
    def _aktif_satiri_vurgula(self):
        secim = QTextEdit.ExtraSelection()
        secim.format.setBackground(AKTIF_SATIR)
        secim.format.setProperty(QTextFormat.Property.FullWidthSelection, True)
        secim.cursor = self.textCursor()
        secim.cursor.clearSelection()
        self.setExtraSelections([secim])

    # --- girinti --------------------------------------------------------
    def keyPressEvent(self, olay):
        if olay.key() == Qt.Key.Key_Tab:
            self.insertPlainText(GIRINTI)
            return
        if olay.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            imlec = self.textCursor()
            satir = imlec.block().text()[:imlec.positionInBlock()]
            girinti = satir[:len(satir) - len(satir.lstrip())]
            if satir.rstrip().endswith(":"):
                girinti += GIRINTI
            super().keyPressEvent(olay)
            self.insertPlainText(girinti)
            return
        super().keyPressEvent(olay)
