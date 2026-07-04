"""JavaScript hedefi (Node.js).

Girdi, stdin'den satır satır senkron okunur (`metinAl`); bu sayede hem
klavyeden (IDE'de) hem borudan gelen girdi çalışır. Çıktı `console.log`
iledir. Yardımcı fonksiyonlar yalnızca kullanıldıklarında dosya başına
eklenir.
"""

import re

from . import ara

_YARDIMCILAR = {
    # stdin'den bir satır senkron okur (klavye ve boru; Türkçe karakter güvenli)
    "metinAl": (
        'function metinAl(mesaj = "") {\n'
        "  process.stdout.write(mesaj);\n"
        '  const fs = require("fs");\n'
        "  const bayt = Buffer.alloc(1), satir = [];\n"
        "  while (true) {\n"
        "    let n;\n"
        "    try { n = fs.readSync(0, bayt, 0, 1); }\n"
        '    catch (e) { if (e.code === "EAGAIN") continue; throw e; }\n'
        "    if (n === 0 || bayt[0] === 10) break;\n"
        "    satir.push(bayt[0]);\n"
        "  }\n"
        '  return Buffer.from(satir).toString("utf8");\n'
        "}"),
    "sayıAl": ('function sayıAl(mesaj = "") { return parseInt(metinAl(mesaj)); }'),
    "ondalıkAl": ('function ondalıkAl(mesaj = "") { return Number(metinAl(mesaj)); }'),
    "uzunluk": ("function uzunluk(x) { return x.length; }"),
    "rastgeleSayı": ("function rastgeleSayı(a, b) "
                     "{ return Math.floor(Math.random() * (b - a + 1)) + a; }"),
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
    NOKTALI = {("random", "randint"): "rastgeleSayı"}
    METOTLAR = {"append": "push"}
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


def cevir(kaynak, gizle_notu=None):
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

    if not gerekli:
        baslik = []
    elif gizle_notu is not None:
        baslik = [gizle_notu, ""]
    else:
        baslik = [_YARDIMCILAR[ad] for ad in gerekli] + [""]
    return "\n".join(baslik + govde)
