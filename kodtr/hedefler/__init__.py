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


def cevir(kaynak, hedef="python"):
    """KodTR kaynağını istenen hedef dile çevirir."""
    return HEDEFLER[hedef][2](kaynak)
