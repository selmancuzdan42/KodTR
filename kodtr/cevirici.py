"""KodTR çevirici çekirdeği: Türkçe kaynak kodu Python'a çevirir.

Yaklaşım: kaynak metin token'lara ayrılır (string / yorum / kelime /
boşluk / diğer). Çeviri yalnızca "kelime" token'larına uygulanır, bu
sayede string içindeki Türkçe metinler ve yorumlar bozulmaz.

Satır bazlı özel kurallar (Türkçe cümle kalıpları):
- ``<koşul> iken:``      ->  ``while <koşul>:``   (Türkçe kelime sırası)
- ``eğer <koşul> ise:``  ->  ``if <koşul>:``      (sondaki "ise" düşer)
- ``<liste> dizisini <değişken> ile dön:`` -> ``for <değişken> in <liste>:``
- ``1'den 10'a kadar i ile say:`` -> ``for i in range(1, 10 + 1):``
- ``3 kere tekrarla:``   ->  ``for _ in range(3):``
- ``x <isim> içinde``    ->  ``x in <isim>``
- ``yazdır x, y``        ->  ``print(x, y)``      (parantezsiz yazım)

Kesme ekleri (``10'a``, ``n'e``) tek token olarak birleştirilir; bir
kalıpta kullanılmazlarsa ek sessizce atılır.
"""

import re

from .sozluk import KELIMELER, OBEKLER

# Uzun öbek önce eşleşsin: "kullanıcıdan sayı al" > "kullanıcıdan al"
_OBEKLER = sorted(OBEKLER, key=lambda o: len(o[0]), reverse=True)

_MASTER = re.compile(
    r'''
      (?P<string>[fFrRbBuU]{0,2}
          (?: """(?:\\.|[^\\])*?"""
            | \'\'\'(?:\\.|[^\\])*?\'\'\'
            | "(?:\\.|[^"\\\n])*"
            | '(?:\\.|[^'\\\n])*'
          ))
    | (?P<comment>\#[^\n]*)
    | (?P<nl>\n)
    | (?P<ekli>(?:\d[\d_]*|[^\W\d]\w*)'[^\W\d]\w*)
    | (?P<number>\d[\d_]*(?:\.\d+)?)
    | (?P<word>[^\W\d]\w*)
    | (?P<space>[ \t]+)
    | (?P<other>.)
    ''',
    re.VERBOSE,
)


def _tokenize(kaynak):
    """Metni (tür, metin) çiftlerine ayırır."""
    tokenlar = []
    for m in _MASTER.finditer(kaynak):
        tokenlar.append((m.lastgroup, m.group()))
    return tokenlar


def _anlamli(tokenlar):
    """Boşluk ve yorum dışındaki token indekslerini döndürür."""
    return [i for i, (tur, _) in enumerate(tokenlar) if tur not in ("space", "comment")]


def _taban(tok):
    """Ekli token'ın kesmeden önceki kısmı: ("ekli", "10'a") -> "10"."""
    return tok[1].split("'", 1)[0]


# Not: kesme ekli kullanım ("ekli" token'ı: 10'a, n'e) doğrudan _MASTER
# içinde yakalanır; string denemesinden sonra geldiği için f'...' gibi
# tek tırnaklı string'ler bozulmaz.


def _sondaki_baglaci_isle(toks):
    """Satır sonundaki 'iken:' ve 'ise:' kalıplarını dönüştürür."""
    m = _anlamli(toks)
    if len(m) < 3 or toks[m[-1]][1] != ":":
        return toks
    aday = toks[m[-2]]
    if aday == ("word", "iken"):
        # kelimeyi (ve önündeki boşluğu) sök, başa 'while ' koy
        del toks[m[-2]]
        if m[-2] > 0 and toks[m[-2] - 1][0] == "space" and m[-2] - 1 != 0:
            del toks[m[-2] - 1]
        bas = 1 if toks and toks[0][0] == "space" else 0
        toks[bas:bas] = [("word", "while"), ("space", " ")]
    elif aday == ("word", "ise"):
        del toks[m[-2]]
        if m[-2] > 0 and toks[m[-2] - 1][0] == "space":
            del toks[m[-2] - 1]
    return toks


def _dongu_kalibi_isle(toks):
    """'meyveler dizisini meyve ile dön:' -> 'for meyve in meyveler:'

    Kalıp: <ifade> dizisini|listesini <değişken> ile dön:
    """
    m = _anlamli(toks)
    if len(m) < 6 or toks[m[-1]] != ("other", ":"):
        return toks
    if (toks[m[-2]] not in (("word", "dön"), ("word", "don"))
            or toks[m[-3]] != ("word", "ile")
            or toks[m[-4]][0] != "word"
            or toks[m[-5]][0] != "word"
            or toks[m[-5]][1] not in ("dizisini", "listesini")):
        return toks

    degisken = toks[m[-4]][1]
    ifade = toks[m[0]:m[-5]]
    while ifade and ifade[-1][0] == "space":
        ifade.pop()

    yeni = toks[:m[0]]  # girinti
    yeni += [("word", "for"), ("space", " "), ("word", degisken),
             ("space", " "), ("word", "in"), ("space", " ")]
    yeni += ifade
    yeni += toks[m[-1]:]  # ':' ve sonrası (yorum vb.)
    return yeni


_SAYMA_FIILLERI = ("say", "dön", "don")


def _kadar_kalibi_isle(toks):
    """'1'den 10'a kadar i ile say:' -> 'for i in range(1, 10 + 1):'

    Kalıplar (başlangıç verilmezse 1'den başlar, bitiş dahildir):
        <n>'den <m>'e kadar <değişken> ile say:
        <m>'e kadar <değişken> ile say:
        <m>'e kadar say:                          (değişken: _)
    """
    m = _anlamli(toks)
    if len(m) < 4 or toks[m[-1]] != ("other", ":"):
        return toks
    if toks[m[-2]][0] != "word" or toks[m[-2]][1] not in _SAYMA_FIILLERI:
        return toks

    if (len(m) >= 6 and toks[m[-3]] == ("word", "ile")
            and toks[m[-4]][0] == "word"
            and toks[m[-5]] == ("word", "kadar")):
        degisken, bit_i = toks[m[-4]][1], m[-6]
    elif toks[m[-3]] == ("word", "kadar"):
        degisken, bit_i = "_", m[-4]
    else:
        return toks

    if toks[bit_i][0] != "ekli":
        return toks
    bitis = _taban(toks[bit_i])

    baslangic = "1"
    onceki = [i for i in m if i < bit_i]
    if len(onceki) == 1 and toks[onceki[0]][0] == "ekli":
        baslangic = _taban(toks[onceki[0]])
    elif onceki:
        return toks

    yeni = toks[:m[0]]  # girinti
    yeni.append(("word", f"for {degisken} in range({baslangic}, {bitis} + 1)"))
    yeni += toks[m[-1]:]  # ':' ve sonrası
    return yeni


def _tekrarla_kalibi_isle(toks):
    """'3 kere tekrarla:' -> 'for _ in range(3):'  (kere/defa/kez)"""
    m = _anlamli(toks)
    if len(m) < 4 or toks[m[-1]] != ("other", ":"):
        return toks
    if (toks[m[-2]] != ("word", "tekrarla")
            or toks[m[-3]][0] != "word"
            or toks[m[-3]][1] not in ("kere", "defa", "kez")):
        return toks

    ifade = toks[m[0]:m[-3]]
    while ifade and ifade[-1][0] == "space":
        ifade.pop()

    yeni = toks[:m[0]]
    yeni += [("word", "for _ in range(")] + ifade + [("other", ")")]
    yeni += toks[m[-1]:]
    return yeni


def _icinde_kalibi_isle(toks):
    """'x meyveler içinde' -> 'x in meyveler'

    "içinde"den hemen önceki tek isim kapsayan kabul edilir ve
    "in" onun önüne alınır.
    """
    i = 0
    while i < len(toks):
        if toks[i][1] in ("içinde", "icinde") and toks[i][0] == "word":
            m = [j for j in range(i)
                 if toks[j][0] not in ("space", "comment")]
            if m and toks[m[-1]][0] in ("word", "number", "string", "ekli"):
                kap = m[-1]
                kap_tok = toks[kap]
                if kap_tok[0] == "ekli":
                    kap_tok = ("word", _taban(kap_tok))
                del toks[i]
                if toks[i - 1][0] == "space":
                    del toks[i - 1]
                toks[kap:kap + 1] = [("word", "in"), ("space", " "), kap_tok]
                i = kap + 3
                continue
        i += 1
    return toks


def _obek_dene(toks, i):
    """toks[i]'den başlayan bir öbek eşleşmesi arar.

    Eşleşirse (yeni_tokenlar, atlanacak_son_indeks) döner, yoksa None.
    """
    for kelimeler, karsilik in _OBEKLER:
        j, uc = i, i
        uydu = True
        for k, kelime in enumerate(kelimeler):
            if k > 0:  # araya yalnızca boşluk girebilir
                while j < len(toks) and toks[j][0] == "space":
                    j += 1
            if j >= len(toks) or toks[j] != ("word", kelime):
                uydu = False
                break
            uc = j
            j += 1
        if not uydu:
            continue

        if isinstance(karsilik, dict):
            # öbekten sonra parantezli argüman var mı?
            j = uc + 1
            while j < len(toks) and toks[j][0] == "space":
                j += 1
            arg = "()"
            if j < len(toks) and toks[j] == ("other", "("):
                derinlik, parca = 0, []
                while j < len(toks):
                    parca.append(toks[j][1])
                    if toks[j] == ("other", "("):
                        derinlik += 1
                    elif toks[j] == ("other", ")"):
                        derinlik -= 1
                        if derinlik == 0:
                            break
                    j += 1
                arg = "".join(parca)
                uc = j
            return [("word", karsilik["tpl"].format(a=arg))], uc

        if karsilik == "":
            return [], uc
        return [("word", karsilik)], uc
    return None


def _kelimeleri_cevir(toks):
    """Öbek ve tek kelime karşılıklarını uygular."""
    yeni = []
    i = 0
    while i < len(toks):
        tur, metin = toks[i]
        if tur != "word":
            yeni.append(toks[i])
            i += 1
            continue

        obek = _obek_dene(toks, i)
        if obek is not None:
            parcalar, uc = obek
            yeni.extend(parcalar)
            i = uc + 1
            if not parcalar:  # silinen kelimenin ardındaki boşluğu da at
                if i < len(toks) and toks[i][0] == "space":
                    i += 1
            continue

        karsilik = KELIMELER.get(metin)
        if karsilik is None:
            yeni.append(toks[i])
        elif karsilik == "":
            if i + 1 < len(toks) and toks[i + 1][0] == "space":
                i += 1
        else:
            yeni.append(("word", karsilik))
        i += 1
    return yeni


def _print_sarmala(toks):
    """Parantezsiz 'print x' satırını 'print(x)' yapar."""
    m = _anlamli(toks)
    if not m or toks[m[0]][1] != "print":
        return toks
    if len(m) == 1:  # yalnız 'yazdır' -> boş satır bas
        toks[m[0]] = ("word", "print()")
        return toks
    sonraki = toks[m[1]][1]
    if sonraki in ("(", "="):  # zaten parantezli ya da atama
        return toks
    toks.insert(m[-1] + 1, ("other", ")"))
    toks[m[0]] = ("word", "print(")
    if toks[m[0] + 1][0] == "space":
        del toks[m[0] + 1]
    return toks


def cevir(kaynak):
    """KodTR kaynağını Python kaynağına çevirir."""
    tokenlar = _tokenize(kaynak)

    # token akışını satırlara böl
    satirlar, satir = [], []
    for tok in tokenlar:
        if tok[0] == "nl":
            satirlar.append(satir)
            satir = []
        else:
            satir.append(tok)
    satirlar.append(satir)

    cikti = []
    for satir in satirlar:
        satir = _dongu_kalibi_isle(satir)
        satir = _kadar_kalibi_isle(satir)
        satir = _tekrarla_kalibi_isle(satir)
        satir = _icinde_kalibi_isle(satir)
        satir = _sondaki_baglaci_isle(satir)
        satir = _kelimeleri_cevir(satir)
        satir = _print_sarmala(satir)
        # kalıpta kullanılmayan kesme ekleri sessizce atılır (10'a -> 10)
        satir = [("word", _taban(t)) if t[0] == "ekli" else t for t in satir]
        cikti.append("".join(metin for _, metin in satir))
    return "\n".join(cikti)


def calistir(kaynak, dosya_adi="<kodtr>"):
    """KodTR kaynağını çevirir ve çalıştırır."""
    py_kaynak = cevir(kaynak)
    kod = compile(py_kaynak, dosya_adi, "exec")
    exec(kod, {"__name__": "__main__"})
    return py_kaynak
