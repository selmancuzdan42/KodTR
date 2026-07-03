"""KodTR IDE başlatıcı: python -m kodtr_ide [dosya.kodtr]"""

import sys

from PyQt6.QtWidgets import QApplication

from .ana_pencere import AnaPencere


def main():
    uygulama = QApplication(sys.argv)
    uygulama.setApplicationName("KodTR IDE")
    uygulama.setDesktopFileName("kodtr-ide")

    dosya = sys.argv[1] if len(sys.argv) > 1 else None
    pencere = AnaPencere(dosya)
    pencere.show()
    return uygulama.exec()


if __name__ == "__main__":
    sys.exit(main())
