"""KodTR anahtar kelime sözlüğü.

Türkçe kelime → Python karşılığı. Dili genişletmek için tek yapman
gereken bu tablolara satır eklemek. Kurallar:

- Karşılıklar yalnızca KOD içindeki kelimelere uygulanır; string ve
  yorum satırlarına asla dokunulmaz.
- Boş string ("") karşılığı = kelime sessizce silinir (örn. "tanımla").
- Türkçe karakterli ve karaktersiz (ascii) yazımların ikisi de kabul.
"""

# ---------------------------------------------------------------------------
# Tek kelimelik karşılıklar
# ---------------------------------------------------------------------------
KELIMELER = {
    # deyimler
    "tanımla": "", "tanimla": "",          # opsiyonel, süs kelimesi
    "yazdır": "print", "yazdir": "print",
    "girdi": "input",
    "eğer": "if", "eger": "if",
    "değilse": "else", "degilse": "else",
    "iken": "while",                       # satır sonunda da kullanılabilir
    "her": "for",
    "için": "in", "icin": "in",
    "fonksiyon": "def",
    "işlev": "def", "islev": "def",
    "döndür": "return", "dondur": "return",
    "sınıf": "class", "sinif": "class",
    "dur": "break",
    "devam": "continue",
    "geç": "pass", "gec": "pass",
    "dene": "try",
    "yakala": "except",
    "sonunda": "finally",

    # mantık / sabitler
    "ve": "and",
    "veya": "or",
    "değil": "not", "degil": "not",
    "doğru": "True", "dogru": "True",
    "yanlış": "False", "yanlis": "False",
    "hiçbiri": "None", "hicbiri": "None",

    # gömülü fonksiyonlar
    "aralık": "range", "aralik": "range",
    "uzunluk": "len",
    "tamsayı": "int", "tamsayi": "int",
    "ondalık": "float", "ondalik": "float",
    "metin": "str",
    "mutlak": "abs",
    "yuvarla": "round",
    "enbüyük": "max", "enbuyuk": "max",
    "enküçük": "min", "enkucuk": "min",
    "sırala": "sorted", "sirala": "sorted",
}

# ---------------------------------------------------------------------------
# Yapısal kelimeler: sözlükle değil, cümle kalıbıyla çevrilirler
# (cevirici.py satır kalıpları + IDE renklendirmesi bunları kullanır)
#   x > 5 ise:                        ->  if/while satırlarının kuyruğu
#   x < 10 iken:                      ->  while x < 10:
#   meyveler dizisini meyve ile dön:  ->  for meyve in meyveler:
#   1'den 10'a kadar i ile say:       ->  for i in range(1, 10 + 1):
#   3 kere tekrarla:                  ->  for _ in range(3):
#   x meyveler içinde                 ->  x in meyveler
# ---------------------------------------------------------------------------
YAPI_KELIMELERI = {
    "ise", "iken",
    "dizisini", "listesini", "ile", "dön",
    "kadar", "say",
    "kere", "defa", "kez", "tekrarla",
    "içinde", "icinde",
}

# ---------------------------------------------------------------------------
# Çok kelimelik öbekler (uzun olan önce denenir)
#
# Karşılık bir dict ise "tpl" şablonu kullanılır: öbekten hemen sonra
# parantezli argüman varsa {a} onun yerine geçer, yoksa {a} = "()".
#   kullanıcıdan sayı al("Yaş: ")  ->  int(input("Yaş: "))
#   kullanıcıdan al                ->  input()
# ---------------------------------------------------------------------------
OBEKLER = [
    (("kullanıcıdan", "sayı", "al"), {"tpl": "int(input{a})"}),
    (("kullanicidan", "sayi", "al"), {"tpl": "int(input{a})"}),
    (("kullanıcıdan", "ondalık", "al"), {"tpl": "float(input{a})"}),
    (("kullanicidan", "ondalik", "al"), {"tpl": "float(input{a})"}),
    (("kullanıcıdan", "metin", "al"), {"tpl": "input{a}"}),
    (("kullanicidan", "metin", "al"), {"tpl": "input{a}"}),
    (("kullanıcıdan", "al"), {"tpl": "input{a}"}),
    (("kullanicidan", "al"), {"tpl": "input{a}"}),
    (("ekrana", "yaz"), "print"),
    (("değilse", "eğer"), "elif"),
    (("degilse", "eger"), "elif"),
    (("içe", "aktar"), "import"),
    (("ice", "aktar"), "import"),
    (("devam", "et"), "continue"),
]
