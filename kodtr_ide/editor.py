"""KodTR editör bileşeni: satır numarası, aktif satır vurgusu, otomatik
girinti ve otomatik tamamlama."""

from PyQt6.QtCore import QRect, QSize, QStringListModel, Qt
from PyQt6.QtGui import (QColor, QFont, QFontDatabase, QPainter, QTextCursor,
                         QTextFormat)
from PyQt6.QtWidgets import QCompleter, QPlainTextEdit, QTextEdit, QWidget

from kodtr.cevirici import _MASTER
from kodtr.sozluk import KELIMELER, OBEKLER, YAPI_KELIMELERI

from .vurgulayici import KodTRVurgulayici


def _ascii_hali(s):
    return s.translate(str.maketrans("çğıöşü", "cgiosu"))


def _dil_kelimeleri():
    """Tamamlama için dil kelimeleri: ascii kopyalar (yazdir) elenir."""
    hepsi = set(KELIMELER) | set(YAPI_KELIMELERI)
    hepsi |= {" ".join(kelimeler) for kelimeler, _ in OBEKLER}
    return {k for k in hepsi
            if _ascii_hali(k) != k
            or not any(b != k and _ascii_hali(b) == k for b in hepsi)}


_SABIT_ONERILER = _dil_kelimeleri()

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


def kod_yazi_tipi(boyut=12):
    """Sistemde varsa modern bir kod fontu, yoksa sabit genişlikli varsayılan."""
    aileler = set(QFontDatabase.families())
    for aday in ("JetBrains Mono", "Fira Code", "Cascadia Code",
                 "Source Code Pro", "Hack"):
        if aday in aileler:
            yazi = QFont(aday)
            break
    else:
        yazi = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
    yazi.setPointSize(boyut)
    return yazi


class KodTREditor(QPlainTextEdit):
    def __init__(self, ebeveyn=None):
        super().__init__(ebeveyn)

        self.setFont(kod_yazi_tipi(12))
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

        # --- otomatik tamamlama
        self._oneri_modeli = QStringListModel()
        self.tamamlayici = QCompleter(self._oneri_modeli, self)
        self.tamamlayici.setWidget(self)
        self.tamamlayici.setCompletionMode(
            QCompleter.CompletionMode.PopupCompletion)
        self.tamamlayici.setCaseSensitivity(
            Qt.CaseSensitivity.CaseSensitive)
        self.tamamlayici.activated.connect(self._tamamla)
        acilir = self.tamamlayici.popup()
        acilir.setFont(self.font())
        acilir.setStyleSheet(
            "QListView { background-color: #282c34; color: #abb2bf;"
            " border: 1px solid #3b4048; padding: 2px; }"
            "QListView::item { padding: 3px 8px; border-radius: 3px; }"
            "QListView::item:selected { background-color: #e06c75;"
            " color: #16191d; }")

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

    # --- otomatik tamamlama ---------------------------------------------
    def _kelime_oneki(self):
        imlec = self.textCursor()
        imlec.select(QTextCursor.SelectionType.WordUnderCursor)
        return imlec.selectedText()

    def _tamamla(self, metin):
        imlec = self.textCursor()
        imlec.select(QTextCursor.SelectionType.WordUnderCursor)
        imlec.insertText(metin)
        self.setTextCursor(imlec)

    def _onerileri_guncelle(self, onek):
        """Dil kelimeleri + belgedeki isimlerden öneri listesini kurar."""
        oneriler = set(_SABIT_ONERILER)
        oneriler |= {m.group() for m in _MASTER.finditer(self.toPlainText())
                     if m.lastgroup == "word" and len(m.group()) >= 3}
        oneriler.discard(onek)  # yazılmakta olan kelime kendini önermesin
        self._oneri_modeli.setStringList(sorted(oneriler))

    def _tamamlama_dene(self):
        onek = self._kelime_oneki()
        if len(onek) < 2:
            self.tamamlayici.popup().hide()
            return
        self._onerileri_guncelle(onek)
        self.tamamlayici.setCompletionPrefix(onek)
        if self.tamamlayici.completionCount() == 0:
            self.tamamlayici.popup().hide()
            return
        self.tamamlayici.popup().setCurrentIndex(
            self.tamamlayici.completionModel().index(0, 0))
        kutu = self.cursorRect()
        kutu.setWidth(self.tamamlayici.popup().sizeHintForColumn(0)
                      + self.tamamlayici.popup().verticalScrollBar()
                      .sizeHint().width() + 16)
        self.tamamlayici.complete(kutu)

    # --- girinti + tuşlar ------------------------------------------------
    def keyPressEvent(self, olay):
        acilir = self.tamamlayici.popup()
        if acilir.isVisible():
            if olay.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter,
                              Qt.Key.Key_Tab):
                indeks = acilir.currentIndex()
                secim = (indeks.data() if indeks.isValid()
                         else self.tamamlayici.currentCompletion())
                acilir.hide()
                if secim:
                    self._tamamla(secim)
                return
            if olay.key() == Qt.Key.Key_Escape:
                acilir.hide()
                return
            if olay.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down,
                              Qt.Key.Key_PageUp, Qt.Key.Key_PageDown):
                olay.ignore()  # gezinmeyi tamamlama penceresi yapsın
                return
        if (olay.modifiers() & Qt.KeyboardModifier.ControlModifier
                and olay.key() == Qt.Key.Key_Space):
            self._tamamlama_dene()
            return

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

        # harf yazıldıkça önerileri göster
        yazilan = olay.text()
        if yazilan and (yazilan.isalnum() or yazilan == "_"
                        or olay.key() == Qt.Key.Key_Backspace):
            self._tamamlama_dene()
        elif acilir.isVisible():
            acilir.hide()
