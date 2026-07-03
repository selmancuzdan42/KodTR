"""JavaScript hedefi (Node.js).

Girdi, Node'da satır satır senkron okunamadığından stdin baştan okunup
satırlara bölünür (`metinAl` yardımcısı); çıktı `console.log` iledir.
Yardımcı fonksiyonlar yalnızca kullanıldıklarında dosya başına eklenir.
"""

import re

from . import ara

_YARDIMCILAR = {
    "metinAl": (
        'const _girdiSatirlari = require("fs").readFileSync(0, "utf8").split("\\n");\n'
        "let _girdiSira = 0;\n"
        'function metinAl(mesaj = "") { process.stdout.write(mesaj);'
        " return _girdiSatirlari[_girdiSira++]; }"),
    "sayıAl": ('function sayıAl(mesaj = "") { return parseInt(metinAl(mesaj)); }'),
    "ondalıkAl": ('function ondalıkAl(mesaj = "") { return Number(metinAl(mesaj)); }'),
    "uzunluk": ("function uzunluk(x) { return x.length; }"),
}

# yardımcının ihtiyaç duyduğu diğer yardımcılar
_BAGIMLILIKLAR = {"sayıAl": ["metinAl"], "ondalıkAl": ["metinAl"]}


class _Ifade(ara.IfadeCevirici):
    KELIMELER = {
        "True": "true", "False": "false", "None": "null",
        "and": "&&", "or": "||", "not": "!",
    }
    CAGRI_ADLARI = {
        "len": "uzunluk", "str": "String",
        "int": "parseInt", "float": "Number",
        "abs": "Math.abs", "round": "Math.round",
        "max": "Math.max", "min": "Math.min",
    }
    GIRDILER = {"int(input": "sayıAl", "float(input": "ondalıkAl",
                "input": "metinAl"}
    ICINDE_BICIMI = "{kap}.includes({eleman})"

    def _string_cevir(self, t):
        # f-string -> şablon dizesi: f"selam {ad}" -> `selam ${ad}`
        if t[:1] in "fF" and t[1:2] in "\"'":
            ic = t[2:-1].replace("`", "\\`").replace("{", "${")
            return f"`{ic}`"
        return t


_ifade = _Ifade()


class _Hedef:
    AYNI_SATIRDA_PARANTEZ = True

    def __init__(self):
        self.bildirilenler = set()
        self._kapsamlar = []  # (fonksiyonun seviyesi, dıştaki bildirilenler)

    def satir(self, tur, alan, seviye=0):
        e = _ifade.cevir
        # fonksiyon gövdesinden çıkıldıysa dış kapsamı geri yükle
        while self._kapsamlar and seviye <= self._kapsamlar[-1][0]:
            self.bildirilenler = self._kapsamlar.pop()[1]
        if tur == "if":
            return f"if ({e(alan['kosul'])})", True
        if tur == "elif":
            return f"else if ({e(alan['kosul'])})", True
        if tur == "else":
            return "else", True
        if tur == "while":
            return f"while ({e(alan['kosul'])})", True
        if tur == "for_aralik":
            d = alan["degisken"]
            bas, bit, kapsayici = ara.aralik_coz(alan["args"])
            islec = "<=" if kapsayici else "<"
            return (f"for (let {d} = {e(bas)}; {d} {islec} {e(bit)}; {d}++)",
                    True)
        if tur == "for_each":
            return (f"for (const {alan['degisken']} of {e(alan['kaynak'])})",
                    True)
        if tur == "def":
            self.bildirilenler.add(alan["ad"])
            self._kapsamlar.append((seviye, set(self.bildirilenler)))
            self.bildirilenler = self.bildirilenler | {
                p.strip() for p in alan["parametreler"].split(",") if p.strip()}
            return f"function {alan['ad']}({alan['parametreler']})", True
        if tur == "return":
            deger = alan.get("deger")
            return (f"return {e(deger)};" if deger else "return;"), False
        if tur in ("break", "continue"):
            return tur + ";", False
        if tur == "pass":
            return "// geç", False
        if tur == "print":
            args = ara.ust_duzey_virgul_bol(alan["args"])
            return "console.log(" + ", ".join(e(a) for a in args) + ");", False
        if tur == "atama":
            hedef_ad, deger = alan["hedef"], e(alan["deger"])
            if hedef_ad not in self.bildirilenler:
                self.bildirilenler.add(hedef_ad)
                return f"let {hedef_ad} = {deger};", False
            return f"{hedef_ad} = {deger};", False
        return e(alan["metin"]) + ";", False


def cevir(kaynak):
    kayitlar = ara.satirlari_ayristir(kaynak)
    govde = ara.govde_uret(kayitlar, _Hedef(), taban=0)
    while govde and not govde[0].strip():
        govde.pop(0)

    metin = "\n".join(govde)
    gerekli, kuyruk = [], [ad for ad in _YARDIMCILAR
                           if re.search(rf"\b{ad}\(", metin)]
    for ad in kuyruk:
        for bagimlilik in _BAGIMLILIKLAR.get(ad, []):
            if bagimlilik not in gerekli and bagimlilik not in kuyruk:
                gerekli.append(bagimlilik)
    # bağımlılıklar önce, sonra kullanım sırası
    gerekli += [ad for ad in kuyruk if ad not in gerekli]

    baslik = [_YARDIMCILAR[ad] for ad in gerekli]
    if baslik:
        baslik.append("")
    return "\n".join(baslik + govde)
