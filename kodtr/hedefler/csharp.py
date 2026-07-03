"""C# hedefi.

Üretilen program klasik okul biçimindedir: `class Program` + `static
Main`; kullanıcı fonksiyonları static metot olarak Main'in üstüne
taşınır. Girdi/uzunluk gibi işlemler için Türkçe adlı küçük yardımcı
metotlar yalnızca kullanıldıklarında eklenir.
"""

import re

from . import ara

_YARDIMCILAR = {
    "SayıAl": ('    static int SayıAl(string mesaj = "")\n'
               "    { Console.Write(mesaj); return int.Parse(Console.ReadLine()); }"),
    "OndalıkAl": ('    static double OndalıkAl(string mesaj = "")\n'
                  "    { Console.Write(mesaj); return double.Parse(Console.ReadLine(),"
                  " System.Globalization.CultureInfo.InvariantCulture); }"),
    "MetinAl": ('    static string MetinAl(string mesaj = "")\n'
                "    { Console.Write(mesaj); return Console.ReadLine(); }"),
    "Yazdır": ("    static void Yazdır(params object[] p)\n"
               '    { Console.WriteLine(string.Join(" ", p)); }'),
    "Uzunluk": ("    static int Uzunluk(dynamic x)\n"
                "    { return x is string s ? s.Length : (int)x.Count; }"),
}


class _Ifade(ara.IfadeCevirici):
    KELIMELER = {
        "True": "true", "False": "false", "None": "null",
        "and": "&&", "or": "||", "not": "!",
    }
    CAGRI_ADLARI = {
        "len": "Uzunluk", "str": "Convert.ToString",
        "int": "Convert.ToInt32", "float": "Convert.ToDouble",
        "abs": "Math.Abs", "round": "Math.Round",
        "max": "Math.Max", "min": "Math.Min",
    }
    GIRDILER = {"int(input": "SayıAl", "float(input": "OndalıkAl",
                "input": "MetinAl"}
    ICINDE_BICIMI = "{kap}.Contains({eleman})"

    def cevir(self, metin):
        return self._listeleri_cevir(super().cevir(metin))

    def _string_cevir(self, t):
        if t[:1] in "fF" and t[1:2] in "\"'":
            t = "$" + t[1:]
        # tek tırnaklı Python string'i C#'ta char olur; çift tırnağa çevir
        govde_isareti = t.lstrip("$")
        if govde_isareti[:1] == "'":
            on_ek = t[:len(t) - len(govde_isareti)]
            ic = govde_isareti[1:-1].replace('"', '\\"').replace("\\'", "'")
            t = f'{on_ek}"{ic}"'
        return t

    def _listeleri_cevir(self, metin):
        """[a, b] -> new List<dynamic> {a, b} (indeksleme dokunulmaz)."""
        toks = ara.tokenize(metin)
        parcalar = []
        acik_yigin = []  # her '[' için: True = liste literali
        onceki_anlamli = None
        for tur, t in toks:
            if tur == "other" and t == "[":
                literal = not (
                    onceki_anlamli
                    and (onceki_anlamli[0] in ("word", "string", "number")
                         or onceki_anlamli[1] in (")", "]")))
                acik_yigin.append(literal)
                parcalar.append("new List<dynamic> {" if literal else t)
            elif tur == "other" and t == "]" and acik_yigin:
                parcalar.append("}" if acik_yigin.pop() else t)
            else:
                parcalar.append(t)
            if tur not in ("space", "comment"):
                onceki_anlamli = (tur, t)
        return "".join(parcalar)


_ifade = _Ifade()


class _Hedef:
    AYNI_SATIRDA_PARANTEZ = False

    def __init__(self):
        self.bildirilenler = set()

    def satir(self, tur, alan, seviye=0):
        e = _ifade.cevir
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
            return (f"for (var {d} = {e(bas)}; {d} {islec} {e(bit)}; {d}++)",
                    True)
        if tur == "for_each":
            return (f"foreach (var {alan['degisken']} in {e(alan['kaynak'])})",
                    True)
        if tur == "return":
            deger = alan.get("deger")
            return (f"return {e(deger)};" if deger else "return;"), False
        if tur in ("break", "continue"):
            return tur + ";", False
        if tur == "pass":
            return "// geç", False
        if tur == "print":
            args = ara.ust_duzey_virgul_bol(alan["args"])
            if len(args) <= 1:
                ic = e(args[0]) if args else ""
                return f"Console.WriteLine({ic});", False
            return "Yazdır(" + ", ".join(e(a) for a in args) + ");", False
        if tur == "atama":
            hedef_ad, deger = alan["hedef"], e(alan["deger"])
            if hedef_ad not in self.bildirilenler:
                self.bildirilenler.add(hedef_ad)
                return f"var {hedef_ad} = {deger};", False
            return f"{hedef_ad} = {deger};", False
        return e(alan["metin"]) + ";", False


def _fonksiyon_uret(blok):
    """Bir def bloğunu static C# metoduna çevirir."""
    _, _, alan, _ = blok[0]
    ad = alan["ad"]
    parametreler = ", ".join(
        f"dynamic {p.strip()}" for p in alan["parametreler"].split(",")
        if p.strip())
    govde_kayitlari = [(s - 1, t, a, y) for s, t, a, y in blok[1:]]

    donduruyor = any(t == "return" and a.get("deger")
                     for _, t, a, _ in govde_kayitlari)
    tip = "dynamic" if donduruyor else "void"

    hedef = _Hedef()
    hedef.bildirilenler = {p.strip() for p in alan["parametreler"].split(",")
                           if p.strip()}
    satirlar = ara.govde_uret(govde_kayitlari, hedef, taban=2)
    # derleyici her yoldan dönüş ister; son satır return değilse ekle
    if donduruyor:
        son_kod = next((s.strip() for s in reversed(satirlar) if s.strip()), "")
        if not son_kod.startswith("return"):
            satirlar.append("        return null;")
    return [f"    static {tip} {ad}({parametreler})", "    {"] + satirlar + ["    }"]


def cevir(kaynak):
    kayitlar = ara.satirlari_ayristir(kaynak)
    fonksiyonlar, govde = ara.fonksiyonlari_ayikla(kayitlar)

    parcalar = []
    for blok in fonksiyonlar:
        parcalar.extend(_fonksiyon_uret(blok))
        parcalar.append("")

    ana = ara.govde_uret(govde, _Hedef(), taban=2)
    # baştaki/sondaki boş satırları kırp
    while ana and not ana[0].strip():
        ana.pop(0)
    while ana and not ana[-1].strip():
        ana.pop()
    parcalar += ["    static void Main()", "    {"] + ana + ["    }"]

    metin = "\n".join(parcalar)
    yardimcilar = [kod for ad, kod in _YARDIMCILAR.items()
                   if re.search(rf"\b{ad}\(", metin)]

    baslik = ["using System;"]
    if "new List<dynamic>" in metin or "Uzunluk(" in metin:
        baslik.append("using System.Collections.Generic;")
    baslik += ["", "class Program", "{"]
    if yardimcilar:
        baslik += yardimcilar + [""]
    return "\n".join(baslik + parcalar + ["}"])
