"""Ara katman: çekirdek çeviricinin ürettiği tek biçimli Python satırlarını
yapısal kayıtlara ayırır. C# ve JavaScript backend'leri bu kayıtlardan
kendi sözdizimlerini üretir.

Çekirdek çevirici KodTR'yi her zaman aynı kalıplarda Python'a çevirdiği
için buradaki parser tam bir Python parser'ı değildir; yalnızca kendi
ürettiğimiz alt kümeyi tanır. Tanınmayan satırlar "ifade" olarak geçer.

Satır kaydı: (girinti_seviyesi, tür, alanlar_dict, yorum)
"""

import re

from ..cevirici import _MASTER, cevir as _py_cevir

# üretilen Python'da görülen satır kalıpları
_DESENLER = [
    ("if",       re.compile(r"^if (?P<kosul>.+):$")),
    ("elif",     re.compile(r"^elif (?P<kosul>.+):$")),
    ("else",     re.compile(r"^else *:$")),
    ("while",    re.compile(r"^while (?P<kosul>.+):$")),
    ("for_aralik", re.compile(r"^for (?P<degisken>\w+) in range\((?P<args>.+)\):$")),
    ("for_each", re.compile(r"^for (?P<degisken>\w+) in (?P<kaynak>.+):$")),
    ("def",      re.compile(r"^def (?P<ad>\w+)\((?P<parametreler>.*)\):$")),
    ("return",   re.compile(r"^return(?: (?P<deger>.+))?$")),
    ("break",    re.compile(r"^break$")),
    ("continue", re.compile(r"^continue$")),
    ("pass",     re.compile(r"^pass$")),
    ("print",    re.compile(r"^print\((?P<args>.*)\)$")),
    ("atama",    re.compile(r"^(?P<hedef>[^\W\d]\w*) = (?P<deger>.+)$")),
]


def tokenize(metin):
    """Metni (tür, metin) çiftlerine ayırır (çekirdek tokenizer)."""
    return [(m.lastgroup, m.group()) for m in _MASTER.finditer(metin)]


def _yorumu_ayir(satir):
    """Satır sonu yorumunu (string'lerin dışındaki #) ayırır."""
    for m in _MASTER.finditer(satir):
        if m.lastgroup == "comment":
            return satir[:m.start()].rstrip(), satir[m.start():].rstrip()
    return satir.rstrip(), None


def ust_duzey_virgul_bol(metin):
    """Parantez/köşeli parantez dışındaki virgüllerden böler."""
    parcalar, derinlik, son = [], 0, 0
    for m in _MASTER.finditer(metin):
        tur, t = m.lastgroup, m.group()
        if tur != "other":
            continue
        if t in "([{":
            derinlik += 1
        elif t in ")]}":
            derinlik -= 1
        elif t == "," and derinlik == 0:
            parcalar.append(metin[son:m.start()].strip())
            son = m.end()
    kuyruk = metin[son:].strip()
    if kuyruk or parcalar:
        parcalar.append(kuyruk)
    return parcalar


def satirlari_ayristir(kodtr_kaynak):
    """KodTR kaynağını satır kayıtlarına çevirir.

    Dönen liste elemanı: (seviye, tür, alanlar, yorum)
    - seviye: girinti derinliği (4 boşluk = 1)
    - tür: "bos", "yorum" veya _DESENLER'deki adlardan biri; kalıba
      uymayan kod satırları "ifade" türünde gelir (alanlar["metin"]).
    - yorum: satır sonundaki "#..." (varsa, # dahil)
    """
    py = _py_cevir(kodtr_kaynak)
    kayitlar = []
    for ham in py.split("\n"):
        if not ham.strip():
            kayitlar.append((0, "bos", {}, None))
            continue
        girinti = len(ham) - len(ham.lstrip(" "))
        seviye = girinti // 4
        govde, yorum = _yorumu_ayir(ham.strip())
        if not govde:
            kayitlar.append((seviye, "yorum", {}, yorum))
            continue
        for tur, desen in _DESENLER:
            m = desen.match(govde)
            if m:
                kayitlar.append((seviye, tur, m.groupdict(), yorum))
                break
        else:
            kayitlar.append((seviye, "ifade", {"metin": govde}, yorum))
    return kayitlar


def aralik_coz(args_metin):
    """range(...) argümanlarını (başlangıç, bitiş, kapsayıcı_mı) yapar.

    Çekirdek "1'den 10'a kadar" kalıbı range(1, 10 + 1) üretir; sondaki
    "+ 1" tespit edilirse bitiş kapsayıcı kabul edilip sadeleştirilir
    (10'a kadar -> i <= 10).
    """
    args = ust_duzey_virgul_bol(args_metin)
    if len(args) == 1:
        return "0", args[0], False
    baslangic, bitis = args[0], args[1]
    m = re.match(r"^(.*?) \+ 1$", bitis)
    if m:
        return baslangic, m.group(1), True
    return baslangic, bitis, False


def parantez_esi(toks, ac_i):
    """toks[ac_i]'deki '(' veya '[' için kapanış indeksini döndürür."""
    acilislar = {"(": ")", "[": "]", "{": "}"}
    kapanis = acilislar[toks[ac_i][1]]
    derinlik = 0
    for j in range(ac_i, len(toks)):
        if toks[j][0] != "other":
            continue
        if toks[j][1] == toks[ac_i][1]:
            derinlik += 1
        elif toks[j][1] == kapanis:
            derinlik -= 1
            if derinlik == 0:
                return j
    return None


class IfadeCevirici:
    """Python ifadelerini hedef dile çeviren, tablo güdümlü çevirici.

    Backend'ler kelime tablolarını verir; paren dengesi, girdi çağrısı
    daraltma, `in` operatörü ve f-string dönüşümleri burada ortaktır.
    """

    # alt sınıflar doldurur
    KELIMELER = {}          # True -> true, and -> && ...
    CAGRI_ADLARI = {}       # len -> Uzunluk, str -> String ...
    GIRDILER = {}           # int(input -> SayıAl, input -> MetinAl ...
    NOKTALI = {}            # ("random", "randint") -> RastgeleSayı ...
    METOTLAR = {}           # nesne.append -> nesne.Add / nesne.push
    ICINDE_BICIMI = "{kap}.Contains({eleman})"

    def cevir(self, metin):
        toks = tokenize(metin)
        toks = self._noktalilari_daralt(toks)
        toks = self._metotlari_cevir(toks)
        toks = self._girdileri_daralt(toks)
        toks = self._icinde_cevir(toks)
        parcalar = []
        for tur, t in toks:
            if tur == "word":
                t = self.KELIMELER.get(t, self.CAGRI_ADLARI.get(t, t))
            elif tur == "string":
                t = self._string_cevir(t)
            elif tur == "other":
                t = self._noktalama_cevir(t)
            parcalar.append(t)
        return "".join(parcalar)

    def _noktalilari_daralt(self, toks):
        """modul.ad çiftini hedefteki tek isme çevirir (random.randint)."""
        yeni = []
        i = 0
        while i < len(toks):
            if (toks[i][0] == "word" and i + 2 < len(toks)
                    and toks[i + 1] == ("other", ".")
                    and toks[i + 2][0] == "word"
                    and (toks[i][1], toks[i + 2][1]) in self.NOKTALI):
                yeni.append(
                    ("word", self.NOKTALI[(toks[i][1], toks[i + 2][1])]))
                i += 3
            else:
                yeni.append(toks[i])
                i += 1
        return yeni

    def _metotlari_cevir(self, toks):
        """Noktadan sonra gelen metot adını hedefe çevirir (.append -> .Add)."""
        yeni = list(toks)
        for i in range(1, len(yeni)):
            if yeni[i][0] == "word" and yeni[i][1] in self.METOTLAR:
                j = i - 1
                while j >= 0 and yeni[j][0] == "space":
                    j -= 1
                if j >= 0 and yeni[j] == ("other", "."):
                    yeni[i] = ("word", self.METOTLAR[yeni[i][1]])
        return yeni

    def _girdileri_daralt(self, toks):
        """int(input(X)) -> SayıAl(X) vb.; iç içe parantezleri söker."""
        yeni = list(toks)
        i = 0
        while i < len(yeni):
            if yeni[i][0] != "word":
                i += 1
                continue
            # int(input( / float(input(
            uzun = None
            if (yeni[i][1] in ("int", "float")
                    and i + 3 < len(yeni)
                    and yeni[i + 1] == ("other", "(")
                    and yeni[i + 2] == ("word", "input")
                    and yeni[i + 3] == ("other", "(")):
                uzun = yeni[i][1] + "(input"
            if uzun and uzun in self.GIRDILER:
                dis_kapanis = parantez_esi(yeni, i + 1)
                if dis_kapanis is not None:
                    del yeni[dis_kapanis]
                    yeni[i:i + 3] = [("word", self.GIRDILER[uzun])]
                    i += 1
                    continue
            # yalın input(
            if (yeni[i][1] == "input" and "input" in self.GIRDILER
                    and i + 1 < len(yeni) and yeni[i + 1] == ("other", "(")):
                yeni[i] = ("word", self.GIRDILER["input"])
            i += 1
        return yeni

    def _icinde_cevir(self, toks):
        """x in kap -> kap.Contains(x) (yalnız en üst parantez düzeyinde)."""
        derinlik = 0
        for k, (tur, t) in enumerate(toks):
            if tur == "other":
                if t in "([{":
                    derinlik += 1
                elif t in ")]}":
                    derinlik -= 1
            elif tur == "word" and t == "in" and derinlik == 0:
                eleman = "".join(x[1] for x in toks[:k]).strip()
                kap = "".join(x[1] for x in toks[k + 1:]).strip()
                if eleman and kap:
                    if " " in kap:
                        kap = f"({kap})"
                    sonuc = self.ICINDE_BICIMI.format(kap=kap, eleman=eleman)
                    return tokenize(sonuc)
        return toks

    def _string_cevir(self, t):
        return t

    def _noktalama_cevir(self, t):
        return t


def govde_uret(kayitlar, hedef, taban=0):
    """Satır kayıtlarından süslü parantezli gövde üretir (C# / JS ortak).

    `hedef` şu arabirimi sunar:
      satir(tur, alanlar, seviye) -> (metin, blok_aciyor_mu)
      AYNI_SATIRDA_PARANTEZ: True ise "if (x) {", False ise Allman stili
    Yorumlar '#' -> '//' çevrilir; girinti 4 boşluk korunur.
    """
    girinti = "    "
    cikti, yigin = [], []

    def yorumu_cevir(y):
        return "//" + y[1:] if y else ""

    def bloklari_kapat(sev):
        # kapanış parantezleri sarkan boş satırların üstüne gelsin
        bosluklar = []
        while cikti and not cikti[-1].strip():
            bosluklar.append(cikti.pop())
        while yigin and yigin[-1] >= sev:
            ust = yigin.pop()
            cikti.append(girinti * (taban + ust) + "}")
        cikti.extend(bosluklar)

    for sev, tur, alan, yorum in kayitlar:
        if tur == "bos":
            cikti.append("")
            continue
        pad = girinti * (taban + sev)
        if tur == "yorum":
            cikti.append(pad + yorumu_cevir(yorum))
            continue

        bloklari_kapat(sev)
        metin, acar = hedef.satir(tur, alan, sev)
        kuyruk = "  " + yorumu_cevir(yorum) if yorum else ""
        if acar:
            if hedef.AYNI_SATIRDA_PARANTEZ:
                cikti.append(pad + metin + " {" + kuyruk)
            else:
                cikti.append(pad + metin + kuyruk)
                cikti.append(pad + "{")
            yigin.append(sev)
        else:
            cikti.append(pad + metin + kuyruk)

    bloklari_kapat(0)
    return cikti


def fonksiyonlari_ayikla(kayitlar):
    """Üst düzey def bloklarını ana gövdeden ayırır.

    (fonksiyon_bloklari, ana_govde) döndürür; her fonksiyon bloğu kendi
    kayıt listesidir (def satırı dahil, girintisi 1 azaltılmış gövdeyle).
    """
    fonksiyonlar, govde = [], []
    i = 0
    while i < len(kayitlar):
        sev, tur, alan, yorum = kayitlar[i]
        if tur == "def" and sev == 0:
            blok = [kayitlar[i]]
            i += 1
            while i < len(kayitlar) and (
                    kayitlar[i][0] > 0
                    or kayitlar[i][1] in ("bos", "yorum")):
                blok.append(kayitlar[i])
                i += 1
            # bloğun sonundaki boş/yorum satırları ana gövdeye aittir
            kuyruk = []
            while blok and blok[-1][1] in ("bos", "yorum") and blok[-1][0] == 0:
                kuyruk.insert(0, blok.pop())
            fonksiyonlar.append(blok)
            govde.extend(kuyruk)
        else:
            govde.append(kayitlar[i])
            i += 1
    return fonksiyonlar, govde
