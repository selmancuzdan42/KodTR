"""Python hedefi — çekirdek çeviricinin çıktısı.

Tek fark: dosya tek başına çalışabilsin diye, kullanılıyorsa
'import random' satırı başa eklenir (canlı panel ve dışa aktarma için;
IDE içi çalıştırma bu yolu kullanmaz, satır eşleşmesi bozulmaz).
"""

import re

from ..cevirici import cevir as _cekirdek_cevir


def cevir(kaynak):
    py = _cekirdek_cevir(kaynak)
    if re.search(r"\brandom\.", py):
        py = "import random\n\n" + py
    return py
