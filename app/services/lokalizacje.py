"""Wspólna lokalizacja trwałych danych appki w spakowanej wersji - inna niż
app/data/ (które w spakowanej appce żyje w folderze rozpakowywanym na nowo
przy każdym starcie, więc zapis tam nie przetrwałby do następnego
uruchomienia). Windows: %APPDATA%\\GeneratorZlecenMediafarm. macOS:
~/Library/Application Support/GeneratorZlecenMediafarm."""
import os
import sys
from pathlib import Path

NAZWA_FOLDERU = "GeneratorZlecenMediafarm"


def czy_spakowana_appka() -> bool:
    """PyInstaller (Windows, `flet pack`) ustawia sys.frozen=True - ale
    `flet build macos` (serious_python) NIE ustawia go wcale, więc appka na
    macOS myliła się z wersją deweloperską: czytała/zapisywała ustawienia i
    mediafarm.json/podmioty.json do app/data/, folderu który w spakowanej
    appce żyje wewnątrz samego .app bundla (potwierdzone diagnostyką z
    realnego Maca: __file__ = ".../Generator Zlecen.app/Contents/Resources/
    serious_python_darwin_serious_python_darwin.bundle/Contents/Resources/
    app/main.pyc") - stąd puste ustawienia i pusta lista accountów mimo
    poprawnie wgranych plików do trwałego folderu. "serious_python" w
    ścieżce tego pliku łapie ten przypadek (oraz - potwierdzone wcześniejszymi
    crashami tej samej appki - tymczasowy katalog kompilacji .py->.pyc przy
    pierwszym uruchomieniu, "serious_python_tempXXXXXXX")."""
    if getattr(sys, "frozen", False):
        return True
    return "serious_python" in str(Path(__file__).resolve())


def katalog_danych_uzytkownika() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / NAZWA_FOLDERU
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / NAZWA_FOLDERU
    return Path.home() / f".{NAZWA_FOLDERU.lower()}"
