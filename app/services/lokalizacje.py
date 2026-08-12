"""Wspólna lokalizacja trwałych danych appki w spakowanej wersji - inna niż
app/data/ (które w spakowanej appce żyje w folderze rozpakowywanym na nowo
przy każdym starcie, więc zapis tam nie przetrwałby do następnego
uruchomienia). Windows: %APPDATA%\\GeneratorZlecenMediafarm. macOS:
~/Library/Application Support/GeneratorZlecenMediafarm."""
import os
import sys
from pathlib import Path

NAZWA_FOLDERU = "GeneratorZlecenMediafarm"


def katalog_danych_uzytkownika() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / NAZWA_FOLDERU
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / NAZWA_FOLDERU
    return Path.home() / f".{NAZWA_FOLDERU.lower()}"
