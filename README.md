# KodTR

Türkçe yazılan, Python'a çevrilen mini programlama dili — IDE'si ve komut
satırı aracıyla birlikte. Pardus başta olmak üzere Debian tabanlı sistemler
için `.deb` paketi olarak dağıtılır.

```
tanımla sayı1 = kullanıcıdan sayı al("Birinci sayı: ")
tanımla sayı2 = kullanıcıdan sayı al("İkinci sayı: ")
toplam = sayı1 + sayı2
yazdır "Toplam:", toplam
```

## Kurulum (Pardus / Debian)

```
./paketle.sh
sudo apt install ./dist/kodtr_0.1.0_all.deb
```

Kurulum sonrası:

- **kodtr-ide** — uygulama menüsünden "KodTR IDE" ya da terminalden
- **kodtr** — komut satırı aracı

## Geliştirme ortamında çalıştırma (paketsiz)

```
cd KodTR
python3 -m kodtr_ide                      # IDE
python3 -m kodtr ornekler/toplama.kodtr   # CLI ile çalıştır
python3 -m kodtr çevir ornekler/toplama.kodtr   # Python halini gör
```

Gereksinim: Python 3.9+ ve PyQt6 (`python3-pyqt6`).

## Dil rehberi

Çeviri satır satır, birebir yapılır: KodTR'deki 5. satır, üretilen Python
kodunda da 5. satırdır. String ve yorum içlerine asla dokunulmaz.

| KodTR | Python |
|---|---|
| `yazdır x` veya `yazdır(x)` | `print(x)` |
| `kullanıcıdan al("soru")` | `input("soru")` |
| `kullanıcıdan sayı al("soru")` | `int(input("soru"))` |
| `kullanıcıdan ondalık al("soru")` | `float(input("soru"))` |
| `tanımla x = 5` | `x = 5` (tanımla opsiyonel) |
| `eğer x > 5 ise:` | `if x > 5:` |
| `değilse eğer ... ise:` | `elif ...:` |
| `değilse:` | `else:` |
| `x < 10 iken:` | `while x < 10:` |
| `meyveler dizisini meyve ile dön:` | `for meyve in meyveler:` |
| `1'den 10'a kadar i ile say:` | `for i in range(1, 10 + 1):` (bitiş dahil) |
| `10'a kadar say:` | `for _ in range(1, 10 + 1):` |
| `3 kere tekrarla:` | `for _ in range(3):` (`defa`/`kez` de olur) |
| `eğer x meyveler içinde ise:` | `if x in meyveler:` |
| `ekrana yaz "selam"` | `print("selam")` |
| `her i için aralık(10):` | `for i in range(10):` |
| `fonksiyon topla(a, b):` | `def topla(a, b):` |
| `döndür sonuç` | `return sonuç` |
| `dur` / `devam et` / `geç` | `break` / `continue` / `pass` |
| `ve` / `veya` / `değil` | `and` / `or` / `not` |
| `doğru` / `yanlış` / `hiçbiri` | `True` / `False` / `None` |
| `uzunluk`, `tamsayı`, `ondalık`, `metin`, `mutlak`, `yuvarla`, `enbüyük`, `enküçük`, `sırala` | `len`, `int`, `float`, `str`, `abs`, `round`, `max`, `min`, `sorted` |

Kurallar:

- Değişken adlarında boşluk olmaz: `sayı 1` değil `sayı1`. Türkçe karakter
  serbesttir (`sayaç`, `sonuç` geçerli birer isimdir).
- Türkçe karaktersiz yazım da kabul edilir: `yazdir`, `eger`, `dongu` gibi.
- Girinti Python'daki gibi anlamlıdır (4 boşluk).
- Metinlerde çift tırnak kullan (`"elma"`). Kesme işareti `10'a`, `n'e`
  gibi ekler için ayrılmıştır; aynı satırda tek tırnaklı metinle
  karışabilir.
- Sözlükte olmayan her şey olduğu gibi Python'a geçer — yani Python'un
  tamamı gerektiğinde KodTR içinde kullanılabilir.

## Proje yapısı

```
kodtr/            Dil çekirdeği (bağımsız paket, PyQt gerektirmez)
  sozluk.py       Türkçe → Python kelime tabloları (dili buradan genişlet)
  cevirici.py     Tokenizer + çevirici
  __main__.py     CLI: kodtr çalıştır / çevir
kodtr_ide/        PyQt6 IDE
  vurgulayici.py  Söz dizimi renklendirme (sozluk.py'den beslenir)
  editor.py       Satır numaralı, otomatik girintili editör
  ana_pencere.py  Ana pencere, F5 çalıştırma, çıktı paneli
ornekler/         Örnek .kodtr programları
veri/             .desktop dosyası
paketle.sh        .deb paketi üretir (dist/ altına)
```

## Yol haritası

- [ ] Hata mesajlarının Türkçeleştirilmesi (traceback çevirisi)
- [ ] Gerçek AST tabanlı çevirici (JavaScript, C# gibi ek hedef diller için)
- [ ] IDE: otomatik tamamlama, kelime ipuçları
- [ ] Pardus mağazasına başvuru
