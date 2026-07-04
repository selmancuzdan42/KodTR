"""KodTR hata ayıklayıcı (debugger) çalıştırıcısı.

IDE, programı bu modülle ayrı süreçte başlatır ve 127.0.0.1 üzerinde
JSON-satır protokolüyle konuşur; programın kendi stdin/stdout'una
karışılmaz. Çeviri satır satır 1:1 olduğu için kesme noktaları doğrudan
KodTR kaynağındaki satır numaralarıdır.

Protokol (her satır bir JSON nesnesi):
  çalıştırıcı -> IDE : {"olay": "hazir"}
  IDE -> çalıştırıcı : {"komut": "basla", "kesmeler": [3, 7]}
  çalıştırıcı -> IDE : {"olay": "durdu", "satir": 3, "degiskenler": {...}}
  IDE -> çalıştırıcı : {"komut": "adim" | "devam" | "dur"}
  çalıştırıcı -> IDE : {"olay": "bitti"}
"""

import inspect
import json
import socket
import sys

from .cevirici import cevir


class _Oturum:
    def __init__(self, kapi):
        baglanti = socket.create_connection(("127.0.0.1", kapi))
        self.akis = baglanti.makefile("rw", encoding="utf-8")
        self.kesmeler = set()
        self.kip = "devam"          # devam | adim

    def gonder(self, **veri):
        self.akis.write(json.dumps(veri) + "\n")
        self.akis.flush()

    def al(self):
        satir = self.akis.readline()
        return json.loads(satir) if satir.strip() else {"komut": "dur"}


def _degiskenler(cerceve):
    """Kullanıcıya gösterilecek değişkenler: modül/fonksiyon/özel adlar hariç."""
    sonuc = {}
    for ad, deger in list(cerceve.f_locals.items()):
        if ad.startswith("_") or inspect.ismodule(deger) or callable(deger):
            continue
        try:
            sonuc[ad] = repr(deger)[:120]
        except Exception:
            sonuc[ad] = "?"
    return sonuc


def calistir(kaynak, dosya_adi, kapi):
    """Kaynağı kesme noktalarına uyarak çalıştırır."""
    oturum = _Oturum(kapi)
    oturum.gonder(olay="hazir")
    baslangic = oturum.al()
    oturum.kesmeler = set(baslangic.get("kesmeler", []))

    def izleyici(cerceve, olay, _arg):
        if cerceve.f_code.co_filename != dosya_adi:
            return None  # kullanıcı dosyası dışına girme
        if olay == "line":
            satir = cerceve.f_lineno
            if oturum.kip == "adim" or satir in oturum.kesmeler:
                oturum.gonder(olay="durdu", satir=satir,
                              degiskenler=_degiskenler(cerceve))
                komut = oturum.al().get("komut")
                if komut == "adim":
                    oturum.kip = "adim"
                elif komut == "devam":
                    oturum.kip = "devam"
                else:  # dur
                    sys.settrace(None)
                    raise SystemExit(0)
        return izleyici

    py_kaynak = cevir(kaynak)
    kod = compile(py_kaynak, dosya_adi, "exec")
    genel = {"__name__": "__main__", "random": __import__("random")}
    sys.settrace(izleyici)
    try:
        exec(kod, genel)
    finally:
        sys.settrace(None)
        try:
            oturum.gonder(olay="bitti")
        except Exception:
            pass
