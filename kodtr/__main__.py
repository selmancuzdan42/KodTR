"""KodTR komut satırı arayüzü.

Kullanım:
    python -m kodtr dosya.kodtr                # doğrudan çalıştır
    python -m kodtr çalıştır dosya.kodtr       # aynı şey
    python -m kodtr çalıştır dosya.kodtr --göster   # önce Python halini bas
    python -m kodtr çevir dosya.kodtr          # Python halini stdout'a yaz
    python -m kodtr çevir dosya.kodtr --hedef csharp      # C# çevirisi
    python -m kodtr çevir dosya.kodtr --hedef js -o out.js
    python -m kodtr diller                     # hedef dilleri listele

Hedef adları: python (py), csharp (cs, c#), javascript (js)
"""

import sys
from pathlib import Path

from .cevirici import calistir
from .hedefler import HEDEFLER, cevir, hedef_bul

KULLANIM = __doc__

_CALISTIR = {"çalıştır", "calistir", "run"}
_CEVIR = {"çevir", "cevir"}
_HATA_AYIKLA = {"hata-ayıkla", "hata-ayikla"}


def _oku(yol):
    dosya = Path(yol)
    if not dosya.exists():
        print(f"kodtr: dosya bulunamadı: {yol}", file=sys.stderr)
        sys.exit(1)
    return dosya.read_text(encoding="utf-8")


def main(argv=None):
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0] in ("yardım", "yardim", "-h", "--help"):
        print(KULLANIM)
        return 0

    komut = args.pop(0)
    if komut == "diller":
        for ad, (etiket, uzanti, _) in HEDEFLER.items():
            print(f"{ad:<12} {etiket:<12} {uzanti}")
        return 0
    if komut not in _CALISTIR | _CEVIR | _HATA_AYIKLA:
        # "python -m kodtr dosya.kodtr" kısayolu
        args.insert(0, komut)
        komut = "çalıştır"

    goster = False
    cikti_yolu = None
    hedef = "python"
    kapi = None
    dosyalar = []
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ("--göster", "--goster"):
            goster = True
        elif arg == "--kapi":
            i += 1
            kapi = int(args[i])
        elif arg == "--hedef":
            i += 1
            if i >= len(args) or hedef_bul(args[i]) is None:
                print("kodtr: --hedef için geçerli dil gerekli "
                      "(python, csharp, javascript)", file=sys.stderr)
                return 1
            hedef = hedef_bul(args[i])
        elif arg == "-o":
            i += 1
            if i >= len(args):
                print("kodtr: -o için dosya adı gerekli", file=sys.stderr)
                return 1
            cikti_yolu = args[i]
        else:
            dosyalar.append(arg)
        i += 1

    if len(dosyalar) != 1:
        print(KULLANIM, file=sys.stderr)
        return 1

    kaynak = _oku(dosyalar[0])

    if komut in _CEVIR:
        hedef_kaynak = cevir(kaynak, hedef)
        if cikti_yolu:
            Path(cikti_yolu).write_text(hedef_kaynak + "\n", encoding="utf-8")
            print(f"kodtr: yazıldı -> {cikti_yolu}")
        else:
            print(hedef_kaynak)
        return 0

    if goster:
        print("# --- çevrilen Python kodu ---")
        print(cevir(kaynak))
        print("# --- çıktı ---")
    try:
        if komut in _HATA_AYIKLA:
            if kapi is None:
                print("kodtr: hata-ayıkla için --kapi gerekli", file=sys.stderr)
                return 1
            from .hata_ayiklayici import calistir as ha_calistir
            ha_calistir(kaynak, dosyalar[0], kapi)
        else:
            calistir(kaynak, dosya_adi=dosyalar[0])
    except KeyboardInterrupt:
        return 130
    except Exception as hata:
        from .hatalar import hata_metni
        print(hata_metni(hata, dosyalar[0], kaynak), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
