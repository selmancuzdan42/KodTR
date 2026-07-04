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
    ]),
    ("Fonksiyon", [
        ("Fonksiyon tanımla",
         'fonksiyon topla(a, b):\n'
         '    döndür a + b\n'
         '\n'
         'yazdır topla(3, 4)\n',
         "Tekrar kullanılabilir bir kod parçası tanımlar"),
    ]),
]
