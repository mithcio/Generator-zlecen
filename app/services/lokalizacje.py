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
    mediafarm.json/podmioty.json do app/data/, folderu, który serious_python
    rozpakowuje NA NOWO przy KAŻDYM starcie appki (potwierdzone: dwa różne
    crashe na tej samej maszynie pokazały dwa różne katalogi tymczasowe,
    "serious_python_tempTxDgS8" i "serious_python_temp4fYV7W", jako bieżący
    katalog roboczy) - stąd puste ustawienia i pusta lista accountów mimo
    poprawnie wgranych plików do trwałego folderu. Sprawdzenie ścieżki tego
    pliku po sys.frozen łapie też ten przypadek."""
    if getattr(sys, "frozen", False):
        return True
    return "serious_python_temp" in str(Path(__file__).resolve())


def katalog_danych_uzytkownika() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / NAZWA_FOLDERU
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / NAZWA_FOLDERU
    return Path.home() / f".{NAZWA_FOLDERU.lower()}"
