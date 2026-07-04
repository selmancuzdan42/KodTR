"""KodTR IDE ana penceresi.

Yerleşim:
    [Kod Blokları] | [Türkçe kod editörü] | [Hedef kod (canlı çeviri)]
    -----------------------------------------------------------------
    [Çıktı paneli + girdi satırı]

Sağ panelin başlığındaki seçiciden hedef dil (Python / C# / JavaScript)
seçilir; Türkçe kod yazıldıkça seçili dile çevirisi anlık görünür.
Çalıştırma (F5) seçili hedef dilde yapılır: Python doğrudan, C# mcs+mono
ile, JavaScript node ile (mono/node .deb ile otomatik kurulur). Kesme
noktası varsa çalıştırma Python hata ayıklama kipine düşer. "Çeviriyi
Dışa Aktar" her hedefi kendi uzantısıyla ayrı dosyaya yazar.
"""

import re
import sys
import tempfile
from pathlib import Path

import json

from PyQt6.QtCore import QProcess, QProcessEnvironment, QSize, Qt, QTimer
from PyQt6.QtGui import (QAction, QColor, QIcon, QKeySequence,
                         QTextCharFormat, QTextCursor)
from PyQt6.QtNetwork import QHostAddress, QTcpServer
from PyQt6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QHeaderView,
                             QLabel, QLineEdit, QMainWindow, QMessageBox,
                             QPlainTextEdit, QSplitter, QTableWidget,
                             QTableWidgetItem, QTabWidget, QTreeWidget,
                             QTreeWidgetItem, QVBoxLayout, QWidget)

import kodtr
from kodtr.cevirici import cevir as py_cevir
from kodtr.hedefler import HEDEFLER, cevir as hedef_cevir

from .bloklar import BLOKLAR
from .editor import KodTREditor, kod_yazi_tipi
from .vurgulayici import HedefVurgulayici

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

def _baslikli(baslik, parca):
    """Bir bileşenin üstüne ince başlık şeridi ekler."""
    kutu = QWidget()
    yerlesim = QVBoxLayout(kutu)
    yerlesim.setContentsMargins(0, 0, 0, 0)
    yerlesim.setSpacing(0)
    etiket = QLabel(baslik)
    etiket.setObjectName("panelBaslik")
    yerlesim.addWidget(etiket)
    yerlesim.addWidget(parca)
    return kutu


class AnaPencere(QMainWindow):
    def __init__(self, dosya=None):
        super().__init__()
        self.dosya = None          # açık dosyanın yolu (Path | None)
        self.surec = None          # çalışan QProcess
        self._gecici_py = None
        self._temizlenecek = []    # program bitince silinecek geçici dosyalar
        self._hata_sunucu = None   # QTcpServer (hata ayıklama oturumu)
        self._hata_soket = None    # bağlı QTcpSocket
        self._hata_kipinde = False

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
        for ikon_adi in ("kodtr.png", "kodtr.svg"):
            ikon = Path(__file__).with_name(ikon_adi)
            if ikon.exists():
                self.setWindowIcon(QIcon(str(ikon)))
                break

        sabit_yazi = kod_yazi_tipi(11)

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

        # --- canlı hedef kod paneli (düzenlenebilir; Türkçe kod değişince
        # yeniden çevrilir, elle yapılan geçici değişiklikler kaybolur)
        self.hedef = "python"
        self.python_gorunum = QPlainTextEdit()
        self.python_gorunum.setFont(self.editor.font())
        self.python_gorunum.setStyleSheet(
            "QPlainTextEdit { background-color: #282c34; color: #abb2bf; border: none; }")
        self._vurgulayici = HedefVurgulayici(
            self.python_gorunum.document(), self.hedef)

        self.hedef_secici = QComboBox()
        for ad, (etiket, _uzanti, _fn) in HEDEFLER.items():
            self.hedef_secici.addItem(etiket, ad)
        self.hedef_secici.currentIndexChanged.connect(self._hedef_degisti)

        # --- kod blokları menüsü
        self.blok_agaci = QTreeWidget()
        self.blok_agaci.setHeaderHidden(True)
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

        # --- değişken paneli (yalnız hata ayıklamada görünür)
        self.degisken_tablosu = QTableWidget(0, 2)
        self.degisken_tablosu.setHorizontalHeaderLabels(["Değişken", "Değer"])
        self.degisken_tablosu.verticalHeader().setVisible(False)
        self.degisken_tablosu.setEditTriggers(
            QTableWidget.EditTrigger.NoEditTriggers)
        self.degisken_tablosu.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch)
        self.degisken_tablosu.setFont(sabit_yazi)
        self._degisken_paneli = _baslikli("DEĞİŞKENLER", self.degisken_tablosu)

        # --- hedef paneli: başlık şeridi + dil seçici + kod görünümü
        hedef_baslik = QWidget()
        hb = QHBoxLayout(hedef_baslik)
        hb.setContentsMargins(8, 2, 8, 2)
        hedef_etiket = QLabel("HEDEF KOD")
        hedef_etiket.setObjectName("panelBaslik")
        hedef_etiket.setStyleSheet("border-bottom: none;")
        hb.addWidget(hedef_etiket)
        hb.addStretch()
        hb.addWidget(self.hedef_secici)

        self._python_paneli = QWidget()
        hp = QVBoxLayout(self._python_paneli)
        hp.setContentsMargins(0, 0, 0, 0)
        hp.setSpacing(0)
        hp.addWidget(hedef_baslik)
        hp.addWidget(self.python_gorunum)

        # --- yerleşim
        yatay = QSplitter(Qt.Orientation.Horizontal)
        yatay.addWidget(_baslikli("KOD BLOKLARI", self.blok_agaci))
        yatay.addWidget(_baslikli("TÜRKÇE KOD (KODTR)", self.editor))
        yatay.addWidget(self._python_paneli)
        yatay.setSizes([200, 520, 460])
        yatay.setStretchFactor(1, 1)
        yatay.setStretchFactor(2, 1)

        alt = QSplitter(Qt.Orientation.Horizontal)
        alt.addWidget(_baslikli("ÇIKTI", cikti_kutu))
        alt.addWidget(self._degisken_paneli)
        alt.setSizes([760, 280])
        self._degisken_paneli.hide()

        dikey = QSplitter(Qt.Orientation.Vertical)
        dikey.addWidget(yatay)
        dikey.addWidget(alt)
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
        arac_cubugu.setToolButtonStyle(
            Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        arac_cubugu.setIconSize(QSize(18, 18))
        menu = self.menuBar()
        dosya_menu = menu.addMenu("&Dosya")
        calistir_menu = menu.addMenu("&Çalıştır")
        gorunum_menu = menu.addMenu("&Görünüm")
        ornek_menu = menu.addMenu("Ö&rnekler")
        yardim_menu = menu.addMenu("&Yardım")

        ornek_dizini = self._ornek_dizini()
        if ornek_dizini:
            for yol in sorted(ornek_dizini.glob("*.kodtr")):
                ad = yol.stem.replace("_", " ").capitalize()
                eylemi = QAction(ad, self)
                eylemi.triggered.connect(
                    lambda _isaret=False, y=yol: self._ornek_ac(y))
                ornek_menu.addAction(eylemi)
        else:
            bos = QAction("(örnek bulunamadı)", self)
            bos.setEnabled(False)
            ornek_menu.addAction(bos)

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
        eylem("Çeviriyi Dışa Aktar...", "Ctrl+E", self.disa_aktar,
              "document-export", dosya_menu, cubukta=False)
        dosya_menu.addSeparator()
        eylem("Çık", "Ctrl+Q", self.close, "application-exit",
              dosya_menu, cubukta=False)

        arac_cubugu.addSeparator()
        self.calistir_eylemi = eylem(
            "Çalıştır", "F5", self.calistir, "media-playback-start", calistir_menu)
        self.durdur_eylemi = eylem(
            "Durdur", "Shift+F5", self.durdur, "media-playback-stop", calistir_menu)
        self.durdur_eylemi.setEnabled(False)
        calistir_menu.addSeparator()
        self.kesme_eylemi = eylem(
            "Kesme Noktası Aç/Kapat", "F2", self.editor.kesme_degistir,
            "media-record", calistir_menu, cubukta=False)
        self.adim_eylemi = eylem(
            "Adım (satır satır)", "F10", self._adim, "media-skip-forward",
            calistir_menu)
        self.devam_eylemi = eylem(
            "Devam Et", "F8", self._devam, "media-seek-forward", calistir_menu)
        self.adim_eylemi.setEnabled(False)
        self.devam_eylemi.setEnabled(False)

        eylem("Python Panelini Gizle/Göster", "F6", self._python_paneli_degistir,
              "view-split-left-right", gorunum_menu, cubukta=False)

        eylem("Hakkında", None, self.hakkinda, "help-about",
              yardim_menu, cubukta=False)

    # ----------------------------------------------------------- örnekler
    @staticmethod
    def _ornek_dizini():
        """Örnek programların dizinini bulur (repo ya da kurulu paket)."""
        for aday in (Path(kodtr.__file__).parent.parent / "ornekler",
                     Path("/usr/share/doc/kodtr/ornekler")):
            if aday.is_dir():
                return aday
        return None

    def _ornek_ac(self, yol):
        """Örneği kopya olarak açar; kaydetmek isteyince yeni ad sorulur."""
        if not self._kayit_sorusu():
            return
        try:
            icerik = yol.read_text(encoding="utf-8")
        except OSError as hata:
            QMessageBox.critical(self, "KodTR IDE", f"Örnek açılamadı:\n{hata}")
            return
        self.dosya = None
        self.editor.setPlainText(icerik)
        self.editor.document().setModified(False)
        self._basligi_guncelle()
        self.statusBar().showMessage(f"Örnek açıldı: {yol.name}", 4000)

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
            self.python_gorunum.setPlainText(
                hedef_cevir(self.editor.toPlainText(), self.hedef,
                            yardimcilari_gizle=True))
        except Exception as hata:  # çeviri asla IDE'yi düşürmesin
            self.python_gorunum.setPlainText(f"# çeviri hatası: {hata}")

    def _hedef_degisti(self, _indeks):
        self.hedef = self.hedef_secici.currentData()
        self._vurgulayici.setDocument(None)
        self._vurgulayici = HedefVurgulayici(
            self.python_gorunum.document(), self.hedef)
        self._canli_cevir()

    def _python_paneli_degistir(self):
        self._python_paneli.setVisible(not self._python_paneli.isVisible())

    def disa_aktar(self):
        """Seçili hedef dilin çevirisini kendi uzantısıyla ayrı dosyaya yazar."""
        etiket, uzanti, _fn = HEDEFLER[self.hedef]
        varsayilan = (str(self.dosya.with_suffix(uzanti))
                      if self.dosya else f"adsız{uzanti}")
        yol, _ = QFileDialog.getSaveFileName(
            self, f"{etiket} Olarak Dışa Aktar", varsayilan,
            f"{etiket} Dosyaları (*{uzanti});;Tüm Dosyalar (*)")
        if not yol:
            return
        if not yol.endswith(uzanti):
            yol += uzanti
        try:
            Path(yol).write_text(
                hedef_cevir(self.editor.toPlainText(), self.hedef) + "\n",
                encoding="utf-8")
        except OSError as hata:
            QMessageBox.critical(self, "KodTR IDE", f"Yazılamadı:\n{hata}")
            return
        self.statusBar().showMessage(f"{etiket} kodu yazıldı: {yol}", 5000)

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
    def _gecici_yaz(self, icerik, uzanti):
        """İçeriği geçici dosyaya yazar, yolunu döndürür (sonra silinir)."""
        dosya = tempfile.NamedTemporaryFile(
            mode="w", suffix=uzanti, prefix="kodtr_", delete=False,
            encoding="utf-8")
        dosya.write(icerik)
        dosya.close()
        self._temizlenecek.append(dosya.name)
        return dosya.name

    def calistir(self):
        if self.surec is not None:
            self.statusBar().showMessage("Zaten çalışan bir program var", 3000)
            return

        kaynak = self.editor.toPlainText()
        kesmeler = self.editor.kesme_satirlari()
        if self.hedef == "python":
            self.python_gorunum.setPlainText(py_cevir(kaynak))

        self._temizlenecek = []
        self.cikti.clear()
        self._yaz("— program başladı —\n", BILGI_RENK)

        # ortak QProcess kurulumu
        ortam = QProcessEnvironment.systemEnvironment()
        paket_koku = str(Path(kodtr.__file__).parent.parent)
        mevcut = ortam.value("PYTHONPATH", "")
        ortam.insert("PYTHONPATH",
                     paket_koku + (":" + mevcut if mevcut else ""))
        self.surec = QProcess(self)
        self.surec.setProcessEnvironment(ortam)
        self.surec.readyReadStandardOutput.connect(self._cikti_oku)
        self.surec.readyReadStandardError.connect(self._hata_oku)
        self.surec.finished.connect(self._bitti)

        # kesme noktası varsa: hata ayıklama yalnızca Python'da
        self._hata_kipinde = bool(kesmeler) and self.hedef == "python"
        if kesmeler and self.hedef != "python":
            self._yaz("(Hata ayıklama Python'da yapılır; C#/JS için kesme "
                      "noktaları yok sayıldı.)\n", BILGI_RENK)

        etiket = HEDEFLER[self.hedef][0]
        basladi = True
        if self._hata_kipinde:
            self._gecici_py = self._gecici_yaz(kaynak, ".kodtr")
            self._hata_baslat_yol(kesmeler, self._gecici_py)
            durum = "Hata ayıklanıyor..."
        elif self.hedef == "python":
            yol = self._gecici_yaz(kaynak, ".kodtr")
            self.surec.start(sys.executable,
                             ["-u", "-m", "kodtr", "çalıştır", yol])
            durum = "Çalışıyor... (Python)"
        elif self.hedef == "csharp":
            basladi = self._calistir_csharp(kaynak)
            durum = "Çalışıyor... (C#)"
        else:  # javascript
            basladi = self._calistir_javascript(kaynak)
            durum = "Çalışıyor... (JavaScript)"

        if not basladi:
            return  # araç yok / derleme hatası; _calistir_X UI'ı topladı

        self.girdi.setEnabled(True)
        self.girdi.setFocus()
        self.calistir_eylemi.setEnabled(False)
        self.durdur_eylemi.setEnabled(True)
        self.statusBar().showMessage(durum)

    def _arac_yok(self, dil, paket):
        """Gerekli çalıştırıcı bulunamadığında kullanıcıyı bilgilendirir."""
        self._yaz(f"\n{dil} çalıştırmak için gerekli araç bulunamadı.\n"
                  f"Kurmak için:  sudo apt install {paket}\n"
                  f"(Şimdilik hedefi Python seçip çalıştırabilirsin.)\n",
                  HATA_RENK)
        self._calistirma_iptal()

    def _calistirma_iptal(self):
        """Program başlatılamadığında arayüzü normale döndürür."""
        self.surec = None
        for yol in self._temizlenecek:
            Path(yol).unlink(missing_ok=True)
        self._temizlenecek = []
        self.calistir_eylemi.setEnabled(True)
        self.durdur_eylemi.setEnabled(False)
        self.statusBar().showMessage("Hazır")

    def _calistir_csharp(self, kaynak):
        import shutil
        import subprocess
        if not shutil.which("mcs") or not shutil.which("mono"):
            self._arac_yok("C#", "mono-mcs")
            return False
        cs = self._gecici_yaz(hedef_cevir(kaynak, "csharp"), ".cs")
        exe = cs[:-3] + ".exe"
        self._temizlenecek.append(exe)
        derleme = subprocess.run(["mcs", "-out:" + exe, cs],
                                 capture_output=True, text=True)
        if derleme.returncode != 0:
            self._yaz((derleme.stderr or derleme.stdout) +
                      "\n— C# derleme başarısız —\n", HATA_RENK)
            self._calistirma_iptal()
            return False
        self.surec.start("mono", [exe])
        return True

    def _calistir_javascript(self, kaynak):
        import shutil
        calistirici = shutil.which("node") or shutil.which("nodejs")
        if not calistirici:
            self._arac_yok("JavaScript", "nodejs")
            return False
        js = self._gecici_yaz(hedef_cevir(kaynak, "javascript"), ".js")
        self.surec.start(calistirici, [js])
        return True

    # -------------------------------------------------- hata ayıklama
    def _hata_baslat_yol(self, kesmeler, yol):
        """TCP sunucusunu açar ve programı hata-ayıkla kipinde başlatır."""
        self._kesmeler = kesmeler
        self._hata_sunucu = QTcpServer(self)
        self._hata_sunucu.listen(QHostAddress.SpecialAddress.LocalHost, 0)
        self._hata_sunucu.newConnection.connect(self._hata_baglandi)
        kapi = self._hata_sunucu.serverPort()

        self._degisken_paneli.show()
        self.adim_eylemi.setEnabled(True)
        self.devam_eylemi.setEnabled(True)
        self.surec.start(sys.executable,
                         ["-u", "-m", "kodtr", "hata-ayıkla",
                          yol, "--kapi", str(kapi)])

    def _hata_baglandi(self):
        self._hata_soket = self._hata_sunucu.nextPendingConnection()
        self._hata_soket.readyRead.connect(self._hata_oku_protokol)

    def _hata_oku_protokol(self):
        while self._hata_soket and self._hata_soket.canReadLine():
            satir = bytes(self._hata_soket.readLine()).decode("utf-8").strip()
            if not satir:
                continue
            veri = json.loads(satir)
            olay = veri.get("olay")
            if olay == "hazir":
                self._hata_gonder(komut="basla", kesmeler=self._kesmeler)
            elif olay == "durdu":
                self._durakta(veri["satir"], veri["degiskenler"])
            elif olay == "bitti":
                self.editor.durak_goster(None)

    def _hata_gonder(self, **veri):
        if self._hata_soket:
            self._hata_soket.write((json.dumps(veri) + "\n").encode("utf-8"))
            self._hata_soket.flush()

    def _durakta(self, satir, degiskenler):
        """Program bir satırda durdu: satırı vurgula, değişkenleri göster."""
        self.editor.durak_goster(satir)
        self.degisken_tablosu.setRowCount(len(degiskenler))
        for sira, (ad, deger) in enumerate(sorted(degiskenler.items())):
            self.degisken_tablosu.setItem(sira, 0, QTableWidgetItem(ad))
            self.degisken_tablosu.setItem(sira, 1, QTableWidgetItem(deger))
        self.statusBar().showMessage(f"Durdu — {satir}. satır")

    def _adim(self):
        if self._hata_soket:
            self.editor.durak_goster(None)
            self._hata_gonder(komut="adim")

    def _devam(self):
        if self._hata_soket:
            self.editor.durak_goster(None)
            self._hata_gonder(komut="devam")

    def durdur(self):
        if self._hata_soket:
            self._hata_gonder(komut="dur")
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
        for yol in getattr(self, "_temizlenecek", []):
            Path(yol).unlink(missing_ok=True)
        self._temizlenecek = []
        self._gecici_py = None
        self.surec = None
        self._hata_temizle()

    def _hata_temizle(self):
        """Hata ayıklama oturumunu kapatır ve arayüzü normale döndürür."""
        self.editor.durak_goster(None)
        self.adim_eylemi.setEnabled(False)
        self.devam_eylemi.setEnabled(False)
        self._degisken_paneli.hide()
        self.degisken_tablosu.setRowCount(0)
        if self._hata_soket is not None:
            self._hata_soket.close()
            self._hata_soket = None
        if self._hata_sunucu is not None:
            self._hata_sunucu.close()
            self._hata_sunucu = None
        self._hata_kipinde = False

    # ------------------------------------------------------------- çeşitli
    def hakkinda(self):
        QMessageBox.about(
            self, "KodTR IDE Hakkında",
            f"<b>KodTR IDE {kodtr.__version__}</b><br>"
            "Türkçe yazılan kodları, Python, C# , Javascript'e  çevrilen mini programlama dili.<br><br>"
            "Selman  Farisi CÜZDAN— github.com/selmancuzdan42")

    def closeEvent(self, olay):
        if self._kayit_sorusu():
            if self.surec is not None:
                self.surec.kill()
            olay.accept()
        else:
            olay.ignore()
