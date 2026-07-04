"""Sol paneldeki hazır kod blokları.

Yeni blok eklemek için ilgili kategoriye (ad, kod, açıklama) satırı ekle.
Kod editöre eklenirken imlecin bulunduğu satırın girintisine uydurulur.

Değişken adındaki "{n}" otomatik numaralanır: editörde sayı1 varsa
"sayı{n}" eklenirken sayı2 olur, sonra sayı3...
"""

BLOKLAR = [
    ("Temel", [
        ("Sayı tanımla",
         "tanımla sayı{n} = 0\n",
         "Yeni bir sayı değişkeni oluşturur"),
        ("Metin tanımla",
         'tanımla yazı{n} = "Merhaba"\n',
         "Yeni bir metin değişkeni oluşturur"),
        ("Ekrana yazdır",
         'yazdır "Merhaba dünya"\n',
         "Ekrana mesaj yazar"),
        ("Kullanıcıdan metin al",
         'yazı{n} = kullanıcıdan al("Adın ne? ")\n',
         "Kullanıcıya soru sorar, cevabı metin olarak alır"),
        ("Kullanıcıdan sayı al",
         'sayı{n} = kullanıcıdan sayı al("Bir sayı gir: ")\n',
         "Kullanıcıya soru sorar, cevabı sayı olarak alır"),
        ("Rastgele sayı",
         'sayı{n} = rastgele(1, 10)\n',
         "1 ile 10 arasında (ikisi de dahil) rastgele bir sayı üretir"),
    ]),
    ("Karar", [
        ("Eğer",
         'eğer sayı1 > 5 ise:\n'
         '    yazdır "5\'ten büyük"\n',
         "Koşul doğruysa içindeki kodu çalıştırır"),
        ("Eğer / değilse",
         'eğer sayı1 > 5 ise:\n'
         '    yazdır "5\'ten büyük"\n'
         'değilse:\n'
         '    yazdır "5\'ten büyük değil"\n',
         "Koşula göre iki yoldan birini seçer"),
        ("Çok koşullu",
         'eğer sayı1 > 5 ise:\n'
         '    yazdır "büyük"\n'
         'değilse eğer sayı1 == 5 ise:\n'
         '    yazdır "tam 5"\n'
         'değilse:\n'
         '    yazdır "küçük"\n',
         "Birden fazla koşulu sırayla dener"),
        ("İçinde mi?",
         'meyveler = ["elma", "armut", "kiraz"]\n'
         'eğer "elma" meyveler içinde ise:\n'
         '    yazdır "listede var"\n',
         "Bir değerin listede olup olmadığına bakar"),
    ]),
    ("Döngü", [
        ("Sayarak döngü",
         "1'den 10'a kadar i ile say:\n"
         '    yazdır i\n',
         "1'den 10'a kadar sayar (bitiş dahil)"),
        ("Belli sayıda tekrar",
         '3 kere tekrarla:\n'
         '    yazdır "merhaba"\n',
         "İçindeki kodu istediğin kadar tekrar eder"),
        ("Koşullu döngü (iken)",
         'sayaç = 0\n'
         'sayaç < 5 iken:\n'
         '    yazdır sayaç\n'
         '    sayaç = sayaç + 1\n',
         "Koşul doğru olduğu sürece tekrar eder"),
        ("Liste ve gezinme",
         'meyveler = ["elma", "armut", "kiraz"]\n'
         'meyveler dizisini meyve ile dön:\n'
         '    yazdır meyve\n',
         "Liste oluşturur ve elemanlarını tek tek gezer"),
        ("Listeye eleman ekle",
         'sayılar = []\n'
         '3 kere tekrarla:\n'
         '    sayılar\'a kullanıcıdan sayı al("Sayı: ") ekle\n'
         'yazdır sayılar\n',
         "Boş listeye tek tek eleman ekler (liste'ye DEĞER ekle)"),
        ("Sonsuz döngü + dur",
         'sayaç = 0\n'
         'doğru iken:\n'
         '    sayaç = sayaç + 1\n'
         '    eğer sayaç > 5 ise:\n'
         '        dur\n'
         '    yazdır sayaç\n',
         "Sonsuza kadar döner; 'dur' ile istediğin an çıkarsın"),
    ]),
    ("Matematik", [
        ("Toplama / çıkarma",
         'sonuç = 10 + 5 - 3\n'
         'yazdır sonuç\n',
         "Aritmetik işlemler: + - * / (bölme), % (kalan)"),
        ("En büyük / en küçük",
         'yazdır enbüyük(4, 9, 2)\n'
         'yazdır enküçük(4, 9, 2)\n',
         "Verilen sayıların en büyüğünü / en küçüğünü bulur"),
        ("Yuvarla ve mutlak",
         'yazdır yuvarla(3.7)\n'
         'yazdır mutlak(-5)\n',
         "Sayıyı yuvarlar / negatifi pozitife çevirir"),
    ]),
    ("Fonksiyon", [
        ("Değer döndüren fonksiyon",
         'fonksiyon topla(a, b):\n'
         '    döndür a + b\n'
         '\n'
         'yazdır topla(3, 4)\n',
         "Girdi alıp sonuç döndüren, tekrar kullanılabilir kod parçası"),
        ("Parametresiz fonksiyon",
         'fonksiyon selamla():\n'
         '    yazdır "Merhaba!"\n'
         '\n'
         'selamla()\n',
         "Girdi almadan iş yapan fonksiyon"),
    ]),
    ("Hazır Programlar", [
        ("Sayı tahmin oyunu",
         '# Bilgisayar 1-10 arası bir sayı tutar, sen tahmin edersin\n'
         'hedef = rastgele(1, 10)\n'
         'hak = 3\n'
         'kazandı = yanlış\n'
         '\n'
         'hak > 0 iken:\n'
         '    tahmin = kullanıcıdan sayı al("Tahminin (1-10): ")\n'
         '    eğer tahmin == hedef ise:\n'
         '        yazdır "Tebrikler, bildin!"\n'
         '        kazandı = doğru\n'
         '        dur\n'
         '    değilse eğer tahmin < hedef ise:\n'
         '        yazdır "Daha büyük bir sayı dene"\n'
         '    değilse:\n'
         '        yazdır "Daha küçük bir sayı dene"\n'
         '    hak = hak - 1\n'
         '    yazdır "Kalan hakkın:", hak\n'
         '\n'
         'eğer kazandı == yanlış ise:\n'
         '    yazdır "Bildin bilemedin, sayı:", hedef\n',
         "Tam bir tahmin oyunu: rastgele sayı, hak sistemi, kazanma kontrolü"),
        ("Ortalama hesabı",
         'notlar = [70, 85, 90, 60]\n'
         'toplam = 0\n'
         'notlar dizisini n ile dön:\n'
         '    toplam = toplam + n\n'
         'ortalama = toplam / uzunluk(notlar)\n'
         'yazdır "Ortalama:", ortalama\n',
         "Bir listenin toplamını ve ortalamasını hesaplar"),
    ]),
]
