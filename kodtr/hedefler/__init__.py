"""KodTR hedef dil backend'leri.

Her hedef dil ayrı modüldür ve tek bir `cevir(kaynak)` fonksiyonu sunar.
Yeni dil eklemek için: modülü yaz, HEDEFLER tablosuna satır ekle.
"""

from . import csharp, javascript, python

# ad -> (etiket, dosya uzantısı, çeviri fonksiyonu)
HEDEFLER = {
    "python": ("Python", ".py", python.cevir),
    "csharp": ("C#", ".cs", csharp.cevir),
    "javascript": ("JavaScript", ".js", javascript.cevir),
}

# CLI'da kabul edilen alternatif adlar
TAKMA_ADLAR = {
    "py": "python",
    "cs": "csharp", "c#": "csharp",
    "js": "javascript",
}


def hedef_bul(ad):
    """'c#', 'js' gibi yazımları asıl hedef adına çevirir; yoksa None."""
    ad = ad.lower()
    ad = TAKMA_ADLAR.get(ad, ad)
    return ad if ad in HEDEFLER else None


# IDE canlı panelinde yardımcı fonksiyon gövdeleri yerine bu not gösterilir.
# Yalnız JavaScript: require("fs")/stdin okuma kalıbı yeni başlayanı
# korkutuyor. C#'ta yapı (class Program + Main) öğretici olduğu için kalır.
GIZLI_NOT = {
    "javascript": "// (girdi/yardımcı fonksiyonlar dışa aktarınca eklenir)",
}


def cevir(kaynak, hedef="python", yardimcilari_gizle=False):
    """KodTR kaynağını istenen hedef dile çevirir.

    yardimcilari_gizle=True: C#/JS yardımcı fonksiyon gövdeleri tek satır
    nota indirilir (IDE canlı paneli için; dışa aktarımda tam hâli yazılır).
    """
    fn = HEDEFLER[hedef][2]
    if yardimcilari_gizle and hedef in GIZLI_NOT:
        return fn(kaynak, gizle_notu=GIZLI_NOT[hedef])
    return fn(kaynak)
