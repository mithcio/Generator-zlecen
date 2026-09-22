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
    `flet build macos`/`flet build apk` (serious_python) NIE ustawia go wcale,
    więc appka myliła się z wersją deweloperską: czytała/zapisywała ustawienia
    i mediafarm.json/podmioty.json do app/data/, folderu który w spakowanej
    appce żyje wewnątrz samego bundla - stąd puste ustawienia i pusta lista
    accountów mimo poprawnie wgranych plików do trwałego folderu.

    macOS (potwierdzone diagnostyką z realnego Maca): __file__ = ".../
    Generator Zlecen.app/Contents/Resources/
    serious_python_darwin_serious_python_darwin.bundle/Contents/Resources/
    app/main.pyc" - "serious_python" w ścieżce łapie ten przypadek (oraz
    tymczasowy katalog kompilacji .py->.pyc przy pierwszym uruchomieniu,
    "serious_python_tempXXXXXXX").

    Android (potwierdzone diagnostyką z realnego telefonu): __file__ = "/data/
    data/<pakiet>/files/flet/app/services/lokalizacje.pyc" - BEZ
    "serious_python" w ścieżce, więc ten sam trik jak na macOS by tu nie
    zadziałał. sys.platform == "android" jest za to jednoznaczne - to wartość,
    jakiej CPython nigdy nie zwraca na maszynie deweloperskiej (Windows/macOS/
    Linux), tylko na realnym urządzeniu z appki zbudowanej `flet build apk`."""
    if getattr(sys, "frozen", False):
        return True
    if sys.platform == "android":
        return True
    return "serious_python" in str(Path(__file__).resolve())


def katalog_danych_uzytkownika() -> Path:
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / NAZWA_FOLDERU
    if sys.platform == "win32":
        return Path(os.environ["APPDATA"]) / NAZWA_FOLDERU
    # Android/iOS (i Linux desktop) - piaskownica appki nie ma odpowiednika
    # %APPDATA%/Application Support, a Path.home() na Androidzie bywa
    # nieprzewidywalna (i tak czy inaczej niedostępna z poziomu zwykłego
    # menedżera plików bez roota). FLET_APP_STORAGE_DATA to oficjalna,
    # udokumentowana przez Fleta zmienna środowiskowa wskazująca trwały,
    # zapisywalny katalog appki, ustawiana przez runtime na każdej platformie
    # (patrz flet.controls.services.storage_paths) - używamy jej, gdy appka
    # faktycznie działa pod Fletem, zamiast zgadywać ścieżkę samodzielnie.
    z_fleta = os.environ.get("FLET_APP_STORAGE_DATA")
    if z_fleta:
        return Path(z_fleta) / NAZWA_FOLDERU
    return Path.home() / f".{NAZWA_FOLDERU.lower()}"
