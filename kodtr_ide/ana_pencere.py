"""KodTR IDE ana penceresi.

Yerleşim:
    [Kod Blokları] | [Türkçe kod editörü] | [Python (canlı çeviri)]
    -----------------------------------------------------------------
    [Çıktı paneli + girdi satırı]

Türkçe kod yazıldıkça Python karşılığı anlık olarak sol panelde belirir.
Soldaki blok menüsünden bir kalıba tıklanınca kod, imlecin bulunduğu
satırın girintisine uydurularak editöre eklenir.
"""

import re
import sys
import tempfile
from pathlib import Path

from PyQt6.QtCore import QProcess, Qt, QTimer
from PyQt6.QtGui import (QAction, QColor, QFontDatabase, QIcon, QKeySequence,
                         QTextCharFormat, QTextCursor)
from PyQt6.QtWidgets import (QFileDialog, QHBoxLayout, QLabel, QLineEdit,
                             QMainWindow, QMessageBox, QPlainTextEdit,
                             QSplitter, QTreeWidget, QTreeWidgetItem,
                             QVBoxLayout, QWidget)

import kodtr
from kodtr.cevirici import cevir

from .bloklar import BLOKLAR
from .editor import KodTREditor
from .vurgulayici import PythonVurgulayici

SABLON = '''\
# KodTR'ye hoş geldin!
# Soldaki bloklara tıklayarak kod ekleyebilirsin. F5 ile çalıştır.

ad = kullanıcıdan al("Adın ne? ")
yazdır f"Merhaba {ad}!"
'''

CIKTI_RENK = QColor("#abb2bf")
HATA_RENK = QColor("#e06c75")
GIRDI_RENK = QColor("#61afef")
BILGI_RENK = QColor("#98c379")

ETIKET_STIL = ("QLabel { background-color: #21252b; color: #7f848e;"
               " padding: 4px 8px; font-weight: bold; }")


def _baslikli(baslik, parca):
    """Bir bileşenin üstüne ince başlık şeridi ekler."""
    kutu = QWidget()
    yerlesim = QVBoxLayout(kutu)
    yerlesim.setContentsMargins(0, 0, 0, 0)
    yerlesim.setSpacing(0)
    etiket = QLabel(baslik)
    etiket.setStyleSheet(ETIKET_STIL)
    yerlesim.addWidget(etiket)
    yerlesim.addWidget(parca)
    return kutu


class AnaPencere(QMainWindow):
    def __init__(self, dosya=None):
        super().__init__()
        self.dosya = None          # açık dosyanın yolu (Path | None)
        self.surec = None          # çalışan QProcess
        self._gecici_py = None

        self._arayuzu_kur()
        if dosya:
            self._dosya_yukle(Path(dosya))
        else:
            self.editor.setPlainText(SABLON)
            self.editor.document().setModified(False)
        self._basligi_guncelle()
        self._canli_cevir()

    # ------------------------------------------------------------------ UI
    def _arayuzu_kur(self):
        self.resize(1280, 760)
        ikon = Path(__file__).with_name("kodtr.svg")
        if ikon.exists():
            self.setWindowIcon(QIcon(str(ikon)))

        sabit_yazi = QFontDatabase.systemFont(QFontDatabase.SystemFont.FixedFont)
        sabit_yazi.setPointSize(11)

        # --- Türkçe kod editörü
        self.editor = KodTREditor()
        self.editor.document().modificationChanged.connect(
            lambda _: self._basligi_guncelle())
        self.editor.cursorPositionChanged.connect(self._konumu_guncelle)

        # yazdıkça canlı çeviri (küçük bekleme ile, her tuşta değil)
        self._cevirme_sayaci = QTimer(self)
        self._cevirme_sayaci.setSingleShot(True)
        self._cevirme_sayaci.setInterval(200)
        self._cevirme_sayaci.timeout.connect(self._canli_cevir)
        self.editor.textChanged.connect(self._cevirme_sayaci.start)

        # --- canlı Python paneli
        self.python_gorunum = QPlainTextEdit(readOnly=True)
        self.python_gorunum.setFont(self.editor.font())
        self.python_gorunum.setStyleSheet(
            "QPlainTextEdit { background-color: #282c34; color: #abb2bf; border: none; }")
        PythonVurgulayici(self.python_gorunum.document())

        # --- kod blokları menüsü
        self.blok_agaci = QTreeWidget()
        self.blok_agaci.setHeaderHidden(True)
        self.blok_agaci.setStyleSheet(
            "QTreeWidget { background-color: #21252b; color: #abb2bf; border: none; }")
        for kategori, bloklar in BLOKLAR:
            dal = QTreeWidgetItem([kategori])
            dal.setFlags(dal.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            self.blok_agaci.addTopLevelItem(dal)
            for ad, kod, aciklama in bloklar:
                yaprak = QTreeWidgetItem([ad])
                yaprak.setToolTip(0, f"{aciklama}\n\n{kod.replace('{n}', '1')}")
                yaprak.setData(0, Qt.ItemDataRole.UserRole, kod)
                dal.addChild(yaprak)
        self.blok_agaci.expandAll()
        self.blok_agaci.itemClicked.connect(self._blok_tiklandi)

        # --- çıktı paneli + girdi satırı
        self.cikti = QPlainTextEdit(readOnly=True)
        self.cikti.setFont(sabit_yazi)
        self.cikti.setStyleSheet(
            "QPlainTextEdit { background-color: #21252b; color: #abb2bf; border: none; }")

        self.girdi = QLineEdit()
        self.girdi.setFont(sabit_yazi)
        self.girdi.setPlaceholderText(
            "Program girdi beklediğinde buraya yaz ve Enter'a bas")
        self.girdi.returnPressed.connect(self._girdi_gonder)
        self.girdi.setEnabled(False)

        cikti_kutu = QWidget()
        yerlesim = QVBoxLayout(cikti_kutu)
        yerlesim.setContentsMargins(0, 0, 0, 0)
        yerlesim.setSpacing(0)
        yerlesim.addWidget(self.cikti)
        girdi_satiri = QWidget()
        g_yerlesim = QHBoxLayout(girdi_satiri)
        g_yerlesim.setContentsMargins(4, 2, 4, 2)
        g_yerlesim.addWidget(QLabel(">"))
        g_yerlesim.addWidget(self.girdi)
        yerlesim.addWidget(girdi_satiri)

        # --- yerleşim
        yatay = QSplitter(Qt.Orientation.Horizontal)
        yatay.addWidget(_baslikli("KOD BLOKLARI", self.blok_agaci))
        yatay.addWidget(_baslikli("TÜRKÇE KOD (KODTR)", self.editor))
        self._python_paneli = _baslikli("PYTHON (CANLI ÇEVİRİ)", self.python_gorunum)
        yatay.addWidget(self._python_paneli)
        yatay.setSizes([200, 520, 460])
        yatay.setStretchFactor(1, 1)
        yatay.setStretchFactor(2, 1)

        dikey = QSplitter(Qt.Orientation.Vertical)
        dikey.addWidget(yatay)
        dikey.addWidget(_baslikli("ÇIKTI", cikti_kutu))
        dikey.setSizes([520, 200])
        self.setCentralWidget(dikey)

        self.konum_etiketi = QLabel("Satır 1, Sütun 1")
        self.statusBar().addPermanentWidget(self.konum_etiketi)
        self.statusBar().showMessage("Hazır")

        self._eylemleri_kur()
        self.editor.setFocus()

    def _eylemleri_kur(self):
        arac_cubugu = self.addToolBar("Araçlar")
        arac_cubugu.setMovable(False)
        menu = self.menuBar()
        dosya_menu = menu.addMenu("&Dosya")
        calistir_menu = menu.addMenu("&Çalıştır")
        gorunum_menu = menu.addMenu("&Görünüm")
        yardim_menu = menu.addMenu("&Yardım")

        def eylem(ad, kisayol, islev, tema_ikonu, menu_, cubukta=True):
            e = QAction(QIcon.fromTheme(tema_ikonu), ad, self)
            if kisayol:
                e.setShortcut(QKeySequence(kisayol))
            e.triggered.connect(islev)
            menu_.addAction(e)
            if cubukta:
                arac_cubugu.addAction(e)
            return e

        eylem("Yeni", "Ctrl+N", self.yeni, "document-new", dosya_menu)
        eylem("Aç...", "Ctrl+O", self.ac, "document-open", dosya_menu)
        eylem("Kaydet", "Ctrl+S", self.kaydet, "document-save", dosya_menu)
        eylem("Farklı Kaydet...", "Ctrl+Shift+S", self.farkli_kaydet,
              "document-save-as", dosya_menu, cubukta=False)
        dosya_menu.addSeparator()
        eylem("Çık", "Ctrl+Q", self.close, "application-exit",
              dosya_menu, cubukta=False)

        arac_cubugu.addSeparator()
        self.calistir_eylemi = eylem(
            "Çalıştır", "F5", self.calistir, "media-playback-start", calistir_menu)
        self.durdur_eylemi = eylem(
            "Durdur", "Shift+F5", self.durdur, "media-playback-stop", calistir_menu)
        self.durdur_eylemi.setEnabled(False)

        eylem("Python Panelini Gizle/Göster", "F6", self._python_paneli_degistir,
              "view-split-left-right", gorunum_menu, cubukta=False)

        eylem("Hakkında", None, self.hakkinda, "help-about",
              yardim_menu, cubukta=False)

    # ----------------------------------------------------------- bloklar
    def _blok_tiklandi(self, oge, _sutun):
        kod = oge.data(0, Qt.ItemDataRole.UserRole)
        if not kod:  # kategori başlığı: aç/kapa
            oge.setExpanded(not oge.isExpanded())
            return
        self._blok_ekle(kod)

    def _blok_ekle(self, kod):
        """Bloğu, imlecin satır girintisine uydurup yeni satıra ekler.

        Koddaki "sayı{n}" gibi adlar, editörde geçen en büyük numaranın
        bir fazlasını alır (sayı1 varsa sayı2, sonra sayı3...).
        """
        metin = self.editor.toPlainText()
        for taban in set(re.findall(r"([^\W\d]\w*)\{n\}", kod)):
            kullanilan = [int(n) for n in
                          re.findall(rf"\b{re.escape(taban)}(\d+)\b", metin)]
            yeni_ad = taban + str(max(kullanilan, default=0) + 1)
            kod = kod.replace(taban + "{n}", yeni_ad)

        imlec = self.editor.textCursor()
        satir = imlec.block().text()
        girinti = satir[:len(satir) - len(satir.lstrip())]

        govde = "".join(
            (girinti + parca if parca.strip() else parca)
            for parca in kod.splitlines(keepends=True))

        imlec.beginEditBlock()
        if satir.strip():  # satırda kod varsa alt satıra geç
            imlec.movePosition(QTextCursor.MoveOperation.EndOfBlock)
            imlec.insertText("\n" + govde)
        else:
            imlec.movePosition(QTextCursor.MoveOperation.StartOfBlock)
            imlec.insertText(govde)
        imlec.endEditBlock()
        self.editor.setTextCursor(imlec)
        self.editor.setFocus()

    # ------------------------------------------------------ canlı çeviri
    def _canli_cevir(self):
        try:
            self.python_gorunum.setPlainText(cevir(self.editor.toPlainText()))
        except Exception as hata:  # çeviri asla IDE'yi düşürmesin
            self.python_gorunum.setPlainText(f"# çeviri hatası: {hata}")

    def _python_paneli_degistir(self):
        self._python_paneli.setVisible(not self._python_paneli.isVisible())

    # ------------------------------------------------------------- dosya
    def _basligi_guncelle(self):
        ad = self.dosya.name if self.dosya else "adsız.kodtr"
        yildiz = "*" if self.editor.document().isModified() else ""
        self.setWindowTitle(f"{ad}{yildiz} — KodTR IDE")

    def _konumu_guncelle(self):
        imlec = self.editor.textCursor()
        self.konum_etiketi.setText(
            f"Satır {imlec.blockNumber() + 1}, Sütun {imlec.positionInBlock() + 1}")

    def _kayit_sorusu(self):
        """Kaydedilmemiş değişiklik varsa sorar. Devam edilecekse True."""
        if not self.editor.document().isModified():
            return True
        cevap = QMessageBox.question(
            self, "KodTR IDE", "Kaydedilmemiş değişiklikler var. Kaydedilsin mi?",
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel)
        if cevap == QMessageBox.StandardButton.Save:
            return self.kaydet()
        return cevap == QMessageBox.StandardButton.Discard

    def yeni(self):
        if not self._kayit_sorusu():
            return
        self.dosya = None
        self.editor.setPlainText(SABLON)
        self.editor.document().setModified(False)
        self._basligi_guncelle()

    def ac(self):
        if not self._kayit_sorusu():
            return
        yol, _ = QFileDialog.getOpenFileName(
            self, "Dosya Aç", "", "KodTR Dosyaları (*.kodtr);;Tüm Dosyalar (*)")
        if yol:
            self._dosya_yukle(Path(yol))

    def _dosya_yukle(self, yol):
        try:
            self.editor.setPlainText(yol.read_text(encoding="utf-8"))
        except OSError as hata:
            QMessageBox.critical(self, "KodTR IDE", f"Dosya açılamadı:\n{hata}")
            return
        self.dosya = yol
        self.editor.document().setModified(False)
        self._basligi_guncelle()
        self.statusBar().showMessage(f"Açıldı: {yol}", 4000)

    def kaydet(self):
        if self.dosya is None:
            return self.farkli_kaydet()
        try:
            self.dosya.write_text(self.editor.toPlainText(), encoding="utf-8")
        except OSError as hata:
            QMessageBox.critical(self, "KodTR IDE", f"Kaydedilemedi:\n{hata}")
            return False
        self.editor.document().setModified(False)
        self._basligi_guncelle()
        self.statusBar().showMessage(f"Kaydedildi: {self.dosya}", 4000)
        return True

    def farkli_kaydet(self):
        yol, _ = QFileDialog.getSaveFileName(
            self, "Farklı Kaydet", "adsız.kodtr",
            "KodTR Dosyaları (*.kodtr);;Tüm Dosyalar (*)")
        if not yol:
            return False
        if not yol.endswith(".kodtr"):
            yol += ".kodtr"
        self.dosya = Path(yol)
        return self.kaydet()

    # ---------------------------------------------------------- çalıştır
    def calistir(self):
        if self.surec is not None:
            self.statusBar().showMessage("Zaten çalışan bir program var", 3000)
            return

        py_kaynak = cevir(self.editor.toPlainText())
        self.python_gorunum.setPlainText(py_kaynak)

        self._gecici_py = tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", prefix="kodtr_", delete=False,
            encoding="utf-8")
        self._gecici_py.write(py_kaynak)
        self._gecici_py.close()

        self.cikti.clear()
        self._yaz("— program başladı —\n", BILGI_RENK)

        self.surec = QProcess(self)
        self.surec.readyReadStandardOutput.connect(self._cikti_oku)
        self.surec.readyReadStandardError.connect(self._hata_oku)
        self.surec.finished.connect(self._bitti)
        self.surec.start(sys.executable, ["-u", self._gecici_py.name])

        self.girdi.setEnabled(True)
        self.girdi.setFocus()
        self.calistir_eylemi.setEnabled(False)
        self.durdur_eylemi.setEnabled(True)
        self.statusBar().showMessage("Çalışıyor...")

    def durdur(self):
        if self.surec is not None:
            self.surec.kill()

    def _girdi_gonder(self):
        if self.surec is None:
            return
        veri = self.girdi.text()
        self.girdi.clear()
        self._yaz(veri + "\n", GIRDI_RENK)
        self.surec.write((veri + "\n").encode("utf-8"))

    def _yaz(self, metin, renk):
        imlec = self.cikti.textCursor()
        imlec.movePosition(QTextCursor.MoveOperation.End)
        bicim = QTextCharFormat()
        bicim.setForeground(renk)
        imlec.insertText(metin, bicim)
        self.cikti.setTextCursor(imlec)
        self.cikti.ensureCursorVisible()

    def _cikti_oku(self):
        self._yaz(bytes(self.surec.readAllStandardOutput())
                  .decode("utf-8", "replace"), CIKTI_RENK)

    def _hata_oku(self):
        self._yaz(bytes(self.surec.readAllStandardError())
                  .decode("utf-8", "replace"), HATA_RENK)

    def _bitti(self, kod, _durum):
        self._yaz(f"\n— program bitti (çıkış kodu {kod}) —\n", BILGI_RENK)
        self.girdi.setEnabled(False)
        self.calistir_eylemi.setEnabled(True)
        self.durdur_eylemi.setEnabled(False)
        self.statusBar().showMessage("Hazır")
        if self._gecici_py:
            Path(self._gecici_py.name).unlink(missing_ok=True)
            self._gecici_py = None
        self.surec = None

    # ------------------------------------------------------------- çeşitli
    def hakkinda(self):
        QMessageBox.about(
            self, "KodTR IDE Hakkında",
            f"<b>KodTR IDE {kodtr.__version__}</b><br>"
            "Türkçe yazılan, Python'a çevrilen mini programlama dili.<br><br>"
            "Selman  Farisi CÜZDAN— github.com/selmancuzdan42")

    def closeEvent(self, olay):
        if self._kayit_sorusu():
            if self.surec is not None:
                self.surec.kill()
            olay.accept()
        else:
            olay.ignore()
