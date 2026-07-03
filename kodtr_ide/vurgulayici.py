"""KodTR ve Python söz dizimi vurgulayıcıları.

KodTR kelime listeleri kodtr.sozluk'ten türetilir; sözlüğe eklenen her
yeni kelime otomatik olarak burada da renklenir. PythonVurgulayici,
canlı çeviri panelindeki üretilen kodu renklendirir.
"""

import keyword
import re

from PyQt6.QtCore import QRegularExpression
from PyQt6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat

from kodtr.sozluk import KELIMELER, OBEKLER, YAPI_KELIMELERI

# Python karşılığına göre kategori ayrımı
_SABITLER = {"True", "False", "None"}
_GOMULULER = {"print", "input", "range", "len", "int", "float", "str",
              "abs", "round", "max", "min", "sorted"}

RENKLER = {
    "deyim":   QColor("#c678dd"),   # eğer, iken, fonksiyon...
    "sabit":   QColor("#d19a66"),   # doğru, yanlış, hiçbiri
    "gomulu":  QColor("#61afef"),   # yazdır, aralık, uzunluk...
    "obek":    QColor("#61afef"),   # kullanıcıdan sayı al
    "metin":   QColor("#98c379"),
    "sayi":    QColor("#d19a66"),
    "yorum":   QColor("#7f848e"),
}


def _bicim(renk, kalin=False, italik=False):
    b = QTextCharFormat()
    b.setForeground(renk)
    if kalin:
        b.setFontWeight(QFont.Weight.Bold)
    if italik:
        b.setFontItalic(italik)
    return b


class _KuralliVurgulayici(QSyntaxHighlighter):
    """Ortak altyapı: kelime kuralları + sayı/string/yorum kuralları."""

    def __init__(self, belge):
        super().__init__(belge)
        self.kurallar = []
        self._kurallari_kur()
        self._ortak_kurallar()

    def _kurallari_kur(self):
        raise NotImplementedError

    def _kelime_kurali(self, kelimeler, bicim):
        desen = r"\b(?:" + "|".join(map(re.escape, kelimeler)) + r")\b"
        self.kurallar.append((QRegularExpression(desen), bicim))

    def _ortak_kurallar(self):
        self.kurallar.append(
            (QRegularExpression(r"\b\d[\d_]*(?:\.\d+)?\b"),
             _bicim(RENKLER["sayi"])))
        self.kurallar.append(
            (QRegularExpression(r'''[fFrRbB]{0,2}"[^"\n]*"?|[fFrRbB]{0,2}'[^'\n]*'?'''),
             _bicim(RENKLER["metin"])))
        self.kurallar.append(
            (QRegularExpression(r"#[^\n]*"),
             _bicim(RENKLER["yorum"], italik=True)))

    def highlightBlock(self, metin):
        for desen, bicim in self.kurallar:
            eslesmeler = desen.globalMatch(metin)
            while eslesmeler.hasNext():
                m = eslesmeler.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), bicim)


class KodTRVurgulayici(_KuralliVurgulayici):
    def _kurallari_kur(self):
        deyimler, sabitler, gomululer = list(YAPI_KELIMELERI), [], []
        for kelime, karsilik in KELIMELER.items():
            if karsilik in _SABITLER:
                sabitler.append(kelime)
            elif karsilik in _GOMULULER:
                gomululer.append(kelime)
            else:
                deyimler.append(kelime)

        self._kelime_kurali(deyimler, _bicim(RENKLER["deyim"], kalin=True))
        self._kelime_kurali(sabitler, _bicim(RENKLER["sabit"], kalin=True))
        self._kelime_kurali(gomululer, _bicim(RENKLER["gomulu"]))

        # çok kelimeli öbekler ("kullanıcıdan sayı al" vb.)
        obek_desen = r"\b(?:" + "|".join(
            r"\s+".join(map(re.escape, kelimeler)) for kelimeler, _ in OBEKLER
        ) + r")\b"
        self.kurallar.append(
            (QRegularExpression(obek_desen), _bicim(RENKLER["obek"])))


class PythonVurgulayici(_KuralliVurgulayici):
    def _kurallari_kur(self):
        sabitler = {"True", "False", "None"}
        deyimler = [k for k in keyword.kwlist if k not in sabitler]
        self._kelime_kurali(deyimler, _bicim(RENKLER["deyim"], kalin=True))
        self._kelime_kurali(sabitler, _bicim(RENKLER["sabit"], kalin=True))
        self._kelime_kurali(_GOMULULER, _bicim(RENKLER["gomulu"]))
