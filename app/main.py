"""Punkt wejścia kreatora Zlecenia.

Desktop:  python app/main.py
Web:      python app/main.py --web [--port 8550]
"""
import os
import sys

# W spakowanej appce (flet pack, --noconsole) sys.stdout/sys.stderr to None -
# nie brakujący plik, tylko dosłownie None, bo nie ma konsoli, do której pisać.
# Każdy print() albo odwołanie do .encoding (np. w scripts/export_seed_data.py,
# importowanym niżej) wywaliłoby AttributeError na starcie, zanim cokolwiek się
# pokaże. W trybie z konsolą (dev, `python app/main.py`) sys.stdout/stderr są
# normalnym plikiem i ten blok nic nie zmienia.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")

import flet as ft

from app.services import ustawienia
from app.ui.kreator import Kreator
from scripts.export_seed_data import (
    export_cennik_wydawcow,
    export_klienci_agencyjni,
    export_podmioty,
    export_terminy_platnosci_klientow,
)


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
