#!/bin/sh
# KodTR .deb paketi oluşturur (Pardus / Debian tabanlı sistemler için).
#
# Kullanım:
#   ./paketle.sh            # dpkg-deb varsa doğrudan, yoksa Docker ile
#
# Çıktı: dist/kodtr_<sürüm>_all.deb
set -eu

SURUM="0.1.0"
KOK="$(cd "$(dirname "$0")" && pwd)"
DIST="$KOK/dist"
KURULUM="$DIST/kodtr_${SURUM}_all"

rm -rf "$KURULUM"
mkdir -p "$DIST"

# ---------------------------------------------------------------- dosyalar
mkdir -p "$KURULUM/DEBIAN" \
         "$KURULUM/usr/share/kodtr" \
         "$KURULUM/usr/bin" \
         "$KURULUM/usr/share/applications" \
         "$KURULUM/usr/share/icons/hicolor/scalable/apps" \
         "$KURULUM/usr/share/doc/kodtr/ornekler"

cp -r "$KOK/kodtr" "$KOK/kodtr_ide" "$KURULUM/usr/share/kodtr/"
find "$KURULUM/usr/share/kodtr" -name "__pycache__" -type d -exec rm -rf {} +

cp "$KOK/veri/kodtr-ide.desktop" "$KURULUM/usr/share/applications/"
cp "$KOK/kodtr_ide/kodtr.svg" "$KURULUM/usr/share/icons/hicolor/scalable/apps/"
cp "$KOK/ornekler/"*.kodtr "$KURULUM/usr/share/doc/kodtr/ornekler/"
cp "$KOK/README.md" "$KURULUM/usr/share/doc/kodtr/" 2>/dev/null || true

# başlatıcılar
cat > "$KURULUM/usr/bin/kodtr" << 'EOF'
#!/bin/sh
export PYTHONPATH="/usr/share/kodtr${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m kodtr "$@"
EOF
cat > "$KURULUM/usr/bin/kodtr-ide" << 'EOF'
#!/bin/sh
export PYTHONPATH="/usr/share/kodtr${PYTHONPATH:+:$PYTHONPATH}"
exec python3 -m kodtr_ide "$@"
EOF
chmod 755 "$KURULUM/usr/bin/kodtr" "$KURULUM/usr/bin/kodtr-ide"

# ------------------------------------------------------------------ control
cat > "$KURULUM/DEBIAN/control" << EOF
Package: kodtr
Version: $SURUM
Section: devel
Priority: optional
Architecture: all
Depends: python3 (>= 3.9), python3-pyqt6
Maintainer: Selman <selmancuzdan42@users.noreply.github.com>
Homepage: https://github.com/selmancuzdan42
Description: Turkce yazilan, Python'a cevrilen programlama dili
 KodTR, programlamaya yeni baslayanlar icin Turkce anahtar
 kelimelerle kod yazmayi saglar; kod otomatik olarak Python'a
 cevrilip calistirilir. Paket, komut satiri araci (kodtr) ve
 gelistirme ortamini (kodtr-ide) icerir.
EOF

# -------------------------------------------------------------------- build
DEB="$DIST/kodtr_${SURUM}_all.deb"
if command -v dpkg-deb > /dev/null 2>&1; then
    dpkg-deb --root-owner-group --build "$KURULUM" "$DEB"
elif command -v docker > /dev/null 2>&1; then
    echo "dpkg-deb yok, Docker (debian:12) ile paketleniyor..."
    docker run --rm -v "$DIST:/dist" debian:12 \
        dpkg-deb --root-owner-group --build \
        "/dist/kodtr_${SURUM}_all" "/dist/kodtr_${SURUM}_all.deb"
else
    echo "HATA: ne dpkg-deb ne docker bulundu." >&2
    echo "CachyOS'ta: sudo pacman -S dpkg" >&2
    exit 1
fi

echo ""
echo "Paket hazır: $DEB"
echo "Pardus'ta kurulum: sudo apt install ./$(basename "$DEB")"
