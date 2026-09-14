"""Punkt wejścia kreatora Zlecenia.

Desktop:  python app/main.py
Web:      python app/main.py --web [--port 8550]
"""
import sys

if "app" not in sys.modules:
    try:
        import app  # noqa: F401 - tylko sondowanie, patrz komentarz niżej
    except ModuleNotFoundError:
        # `flet build macos` (patrz pyproject.toml [tool.flet.app].path="app"
        # i build-and-release.yml) pakuje WYŁĄCZNIE zawartość app/ jako korzeń
        # Pythona w bundlu - ten plik ląduje tam jako "<korzeń>/main.py", a
        # services/ui/models/... jako podfoldery TEGO korzenia, bez
        # opakowującego folderu "app" w środku. Import "app.xxx" (używany w
        # całym kodzie, łącznie z resztą tego pliku) wywala się wtedy z
        # "ModuleNotFoundError: No module named 'app'" (potwierdzony crash na
        # macOS) - `flet run`/pytest/Windows (`flet pack`, PyInstaller) NIE
        # mają tego problemu (u nich prawdziwy pakiet "app" jest już
        # importowalny, więc `import app` powyżej się udaje i ten blok jest
        # no-opem). Naprawa: aliasujemy "app" na katalog TEGO pliku, żeby
        # "app.services"/"app.ui"/... trafiały tam, gdzie faktycznie leżą.
        import os
        import types

        _app_alias = types.ModuleType("app")
        _app_alias.__path__ = [os.path.dirname(os.path.abspath(__file__))]
        sys.modules["app"] = _app_alias

from app.services.lokalizacje import czy_spakowana_appka, katalog_danych_uzytkownika

# TYMCZASOWA diagnostyka (do usunięcia po znalezieniu przyczyny pustej listy
# accountów na macOS) - zapisuje na Pulpit fakty o środowisku uruchomieniowym,
# niezależnie od tego, czy czy_spakowana_appka() zgadła poprawnie, czy nie.
# Owinięte w try/except - błąd tutaj nie ma prawa zablokować startu appki.
try:
    from pathlib import Path as _Path

    _diag = [
        f"sys.platform = {sys.platform!r}",
        f"getattr(sys, 'frozen', False) = {getattr(sys, 'frozen', False)!r}",
        f"sys.executable = {sys.executable!r}",
        f"__file__ = {__file__!r}",
        f"Path(__file__).resolve() = {_Path(__file__).resolve()!r}",
        f"czy_spakowana_appka() = {czy_spakowana_appka()!r}",
        f"katalog_danych_uzytkownika() = {katalog_danych_uzytkownika()!r}",
        f"  .exists() = {katalog_danych_uzytkownika().exists()!r}",
        f"  mediafarm.json .exists() = {(katalog_danych_uzytkownika() / 'mediafarm.json').exists()!r}",
    ]
    _data_dir = _Path(__file__).resolve().parent / "data"
    _diag.append(f"app/data (DATA_DIR) = {_data_dir!r}")
    _diag.append(f"  mediafarm.json .exists() = {(_data_dir / 'mediafarm.json').exists()!r}")
    _Path.home().joinpath("Desktop", "GeneratorZlecen_diagnostyka.txt").write_text(
        "\n".join(_diag), encoding="utf-8"
    )
except Exception as _diag_err:  # noqa: BLE001 - diagnostyka nie moze wywalic startu
    try:
        _Path.home().joinpath("Desktop", "GeneratorZlecen_diagnostyka.txt").write_text(
            f"Diagnostyka sama wywalila blad: {_diag_err!r}", encoding="utf-8"
        )
    except Exception:
        pass

# Folder na dane wgrywane ręcznie po instalacji (mediafarm.json, podmioty.json
# - patrz lokalizacje.py) ma istnieć od razu po pierwszym uruchomieniu, nie
# dopiero gdy coś do niego zapisze appka (np. Ustawienia dopiero po kliknięciu
# "Zapisz") - inaczej nie ma go gdzie wkleić plikami z Findera/Eksploratora.
if czy_spakowana_appka():
    katalog_danych_uzytkownika().mkdir(parents=True, exist_ok=True)

# W spakowanej appce (flet pack, --noconsole/.app bez terminala) sys.stdout/
# sys.stderr to None - nie brakujący plik, tylko dosłownie None, bo nie ma
# konsoli, do której pisać. Każdy print() albo odwołanie do .encoding (np. w
# app/services/export_seed_data.py, importowanym niżej) wywaliłoby AttributeError
# na starcie, zanim cokolwiek się pokaże. W trybie z konsolą (dev,
# `python app/main.py`) sys.stdout/stderr są normalnym plikiem i ten blok nic
# nie zmienia. Przekierowane do pliku (nie /dev/null) - inaczej print()/
# wyjątki są nie do zdiagnozowania zdalnie, bez konsoli i bez debuggera
# podpiętego do czyjegoś komputera. Ten sam folder co ustawienia.json/
# mediafarm.json (patrz lokalizacje.py) - jedno miejsce do sprawdzenia.
if sys.stdout is None or sys.stderr is None:
    _log_dir = katalog_danych_uzytkownika()
    _log_dir.mkdir(parents=True, exist_ok=True)
    _log = open(_log_dir / "app.log", "a", encoding="utf-8", buffering=1)
    if sys.stdout is None:
        sys.stdout = _log
    if sys.stderr is None:
        sys.stderr = _log

import flet as ft

from app.services import ustawienia
from app.services.export_seed_data import (
    export_cennik_wydawcow,
    export_klienci_agencyjni,
    export_podmioty,
    export_terminy_platnosci_klientow,
)
from app.ui.kreator import Kreator


def odswiez_baze_klientow() -> None:
    """Etap testowy: baza klientów (Numery_zlecen_2026.xlsx) zmienia się
    często, a akanci nie mają się uczyć żadnej komendy odświeżania - więc
    przy każdym starcie aplikacji po cichu przeliczamy ją na nowo ze
    źródłowego pliku zamiast czekać na ręczne uruchomienie
    export_seed_data.py. Błąd (plik zajęty w Excelu, brak pliku, zła
    struktura zakładki) nie blokuje startu - aplikacja po prostu działa na
    ostatnio zapisanym app/data/*.json. Ścieżka do pliku - jeśli ustawiona w
    Ustawieniach (ikona koła zębatego) - bierze pierwszeństwo nad domyślną
    kopią w źródła/."""
    try:
        sciezka = ustawienia.wczytaj().get("sciezka_numery_zlecen")
        export_podmioty(sciezka)
        export_klienci_agencyjni(sciezka)
        export_terminy_platnosci_klientow(sciezka)
        export_cennik_wydawcow(sciezka)
    except Exception as err:
        print(f"Nie udało się odświeżyć bazy klientów z Numery_zlecen_2026.xlsx: {err}")


def main(page: ft.Page) -> None:
    page.title = "Generator Zleceń — Mediafarm"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.padding = 0
    page.window.width = 900
    page.window.height = 900
    # Bez tego natywne kontrolki Fluttera (np. DatePicker) mówią po angielsku
    # ("July 2026"), mimo że reszta interfejsu jest po polsku.
    page.locale_configuration = ft.LocaleConfiguration(
        supported_locales=[ft.Locale("pl", "PL")],
        current_locale=ft.Locale("pl", "PL"),
    )

    kreator = Kreator(page)
    kreator.odswiez()


if __name__ == "__main__":
    odswiez_baze_klientow()
    if "--web" in sys.argv:
        port = 8550
        if "--port" in sys.argv:
            port = int(sys.argv[sys.argv.index("--port") + 1])
        ft.run(main, view=ft.AppView.WEB_BROWSER, port=port)
    else:
        ft.run(main)
