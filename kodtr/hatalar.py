"""Türkçe hata mesajları.

Çalışma sırasında oluşan Python hatalarını, KodTR kaynağındaki satıra
işaret eden anlaşılır Türkçe açıklamalara çevirir. Çeviri satır satır
1:1 olduğu için Python traceback'indeki satır numarası doğrudan
Türkçe kaynaktaki satırdır.
"""

import difflib
import re
import traceback

from .cevirici import _MASTER


def _yakin_adlar(ad, kaynak):
    """Kaynaktaki benzer isimleri bulur ('yas' yazıldıysa 'yaş' öner)."""
    adaylar = {m.group() for m in _MASTER.finditer(kaynak)
               if m.lastgroup == "word" and m.group() != ad}
    return difflib.get_close_matches(ad, adaylar, n=1, cutoff=0.6)


# sonu ':' ile bitmesi gereken Türkçe blok kalıplarının son kelimeleri
_BLOK_SONLARI = ("ise", "iken", "tekrarla", "say", "dön", "don",
                 "değilse", "degilse")


def _sozdizimi_mesaji(hata, kodtr_satir=""):
    govde = kodtr_satir.split("#")[0].rstrip()
    m_art = re.search(r"([^\W\d]\w*)\s*(\+\+|--)", govde)
    if m_art:
        ad = m_art.group(1)
        islem = "+ 1" if m_art.group(2) == "++" else "- 1"
        return (f"KodTR'de '++' ve '--' işleçleri yok (bunlar C#/JavaScript "
                f"yazımı). Şöyle yaz: {ad} = {ad} {islem}")
    if (govde and not govde.endswith(":")
            and govde.split()[-1] in _BLOK_SONLARI):
        return (f"Satırın sonunda ':' eksik. Blok başlatan satırlar "
                f"':' ile biter: \"{govde}:\"")
    m = str(hata.msg if hasattr(hata, "msg") else hata)
    if isinstance(hata, IndentationError):
        return ("Girinti hatası: satır başındaki boşluklar tutarsız. "
                "Blok içindeki satırları 4 boşlukla girintile.")
    if "expected ':'" in m or "expected an indented block" in m:
        return ("Söz dizimi hatası: blok başlatan satırın sonunda ':' "
                "eksik olabilir ya da bloğun içi boş kalmış.")
    if "was never closed" in m or "unmatched" in m:
        return "Söz dizimi hatası: açılan parantez ya da tırnak kapatılmamış."
    if "unterminated string" in m.lower():
        return "Söz dizimi hatası: tırnak açılmış ama kapatılmamış."
    if "cannot assign" in m:
        return ("Söz dizimi hatası: buraya atama (=) yazılamaz. "
                "Karşılaştırma için '==' kullan.")
    return "Söz dizimi hatası: bu satır KodTR kurallarına uymuyor."


def _calisma_mesaji(hata, kaynak):
    if isinstance(hata, NameError):
        ad = getattr(hata, "name", None)
        if not ad:
            m = re.search(r"name '([^']*)'", str(hata))
            ad = m.group(1) if m else "?"
        mesaj = f"'{ad}' diye bir değişken ya da fonksiyon tanımlanmamış."
        yakin = _yakin_adlar(ad, kaynak)
        if yakin:
            mesaj += f" Şunu mu demek istedin: '{yakin[0]}'?"
        return mesaj
    if isinstance(hata, ZeroDivisionError):
        return "Bir sayı sıfıra bölünemez."
    if isinstance(hata, IndexError):
        return ("Listenin sınırları dışına çıkıldı: olmayan bir sıra "
                "numarası istendi. Unutma, saymaya 0'dan başlanır.")
    if isinstance(hata, KeyError):
        return f"Sözlükte {hata.args[0]!r} diye bir anahtar yok."
    if isinstance(hata, ValueError):
        m = re.search(r"invalid literal for int\(\).*: '(.*)'", str(hata))
        if m:
            return (f"Sayı bekleniyordu ama '{m.group(1)}' yazıldı ve "
                    "sayıya çevrilemedi.")
        m = re.search(r"could not convert string to float: '(.*)'", str(hata))
        if m:
            return (f"Ondalık sayı bekleniyordu ama '{m.group(1)}' yazıldı "
                    "ve sayıya çevrilemedi.")
        return f"Değer hatası: {hata}"
    if isinstance(hata, TypeError):
        m = str(hata)
        if "can only concatenate str" in m or ('unsupported operand' in m
                                               and 'str' in m):
            return ("Metin ile sayı doğrudan birleştirilemez. Sayıyı "
                    "metin(...) ile metne çevir ya da f\"...\" kullan.")
        if "not callable" in m:
            return ("Fonksiyon olmayan bir şey çağrılmaya çalışıldı. "
                    "Değişken adıyla fonksiyon adı karışmış olabilir.")
        if "argument" in m:
            return ("Fonksiyona yanlış sayıda değer verildi. Tanımdaki "
                    "parametre sayısıyla çağrıyı karşılaştır.")
        return f"Tür hatası: bu işlem bu değerler arasında yapılamaz. ({hata})"
    if isinstance(hata, RecursionError):
        return ("Fonksiyon kendini durmadan çağırıyor. Özyinelemeli "
                "fonksiyona bir durma koşulu ekle.")
    if isinstance(hata, EOFError):
        return "Program girdi bekliyordu ama girdi gelmedi."
    if isinstance(hata, AttributeError):
        return f"Bu değerin böyle bir özelliği yok: {hata}"
    return f"{type(hata).__name__}: {hata}"


def hata_metni(hata, dosya_adi, kaynak):
    """Hatayı KodTR kaynağına işaret eden Türkçe metne çevirir."""
    satirlar_liste = kaynak.split("\n")
    satir_no = None
    if isinstance(hata, SyntaxError):
        if hata.filename == dosya_adi:
            satir_no = hata.lineno
        kodtr_satir = (satirlar_liste[satir_no - 1]
                       if satir_no and 1 <= satir_no <= len(satirlar_liste)
                       else "")
        mesaj = _sozdizimi_mesaji(hata, kodtr_satir)
    else:
        for cerceve in traceback.extract_tb(hata.__traceback__):
            if cerceve.filename == dosya_adi:
                satir_no = cerceve.lineno  # en derin kullanıcı satırı kalsın
        mesaj = _calisma_mesaji(hata, kaynak)

    parcalar = []
    if satir_no and 1 <= satir_no <= len(satirlar_liste):
        parcalar.append(f"HATA — {satir_no}. satır:")
        parcalar.append("    " + satirlar_liste[satir_no - 1].strip())
    else:
        parcalar.append("HATA:")
    parcalar.append(mesaj)
    return "\n".join(parcalar)
