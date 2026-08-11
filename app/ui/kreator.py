"""Orkiestrator kreatora: trzyma stan, przełącza kroki, wspólne akcje UI
(błędy, nawigacja, ustawienia) wołane przez poszczególne kroki."""
from pathlib import Path

import flet as ft

from app.services import aktualizacje
from app.services import eksport_nazwy
from app.services import lookup_podmiotu as lp
from app.services import ustawienia
from app.ui import (
    krok1_podmiot,
    krok2_dane_kampanii,
    krok3_okresy,
    krok4_podglad,
    krok5_dane_traffic,
)
from app.ui.stan import LICZBA_KROKOW, StanKreatora

WIDOKI = {
    1: krok1_podmiot.buduj,
    2: krok2_dane_kampanii.buduj,
    3: krok3_okresy.buduj,
    4: krok4_podglad.buduj,
    5: krok5_dane_traffic.buduj,
}

ETYKIETY_KROKOW = ["Podmiot", "Dane kampanii", "Okresy", "Zlecenie", "Dane Traffic"]


class Kreator:
    def __init__(self, page: ft.Page):
        self.page = page
        self.stan = StanKreatora()
        self._file_picker = ft.FilePicker()
        self.page.services.append(self._file_picker)
        self.page.appbar = ft.AppBar(
            title=ft.Text("Generator Zleceń"),
            actions=[
                ft.IconButton(
                    icon=ft.Icons.SYSTEM_UPDATE_ALT,
                    tooltip="Sprawdź aktualizacje",
                    on_click=lambda e: self.sprawdz_aktualizacje(),
                ),
                ft.IconButton(
                    icon=ft.Icons.SETTINGS,
                    tooltip="Ustawienia",
                    on_click=lambda e: self.pokaz_ustawienia(),
                ),
            ],
        )

    def odswiez(self) -> None:
        self.page.clean()
        widok = WIDOKI[self.stan.krok](self)
        self.page.add(
            ft.Container(
                content=ft.Column(
                    [self._pasek_postepu(), ft.Divider(), widok],
                    spacing=20,
                    scroll=ft.ScrollMode.AUTO,
                ),
                padding=30,
                expand=True,
            )
        )

    def wroc(self) -> None:
        if self.stan.krok > 1:
            self.stan.krok -= 1
            self.odswiez()

    def idz_do_kroku(self, krok: int) -> None:
        self.stan.krok = krok
        self.odswiez()

    def _pasek_postepu(self) -> ft.Control:
        elementy = []
        for i, etykieta in enumerate(ETYKIETY_KROKOW, start=1):
            aktywny = i == self.stan.krok
            zrobiony = i < self.stan.krok
            kolor = ft.Colors.BLUE_700 if aktywny else (ft.Colors.GREEN_700 if zrobiony else ft.Colors.GREY_400)
            elementy.append(
                ft.Container(
                    content=ft.Text(
                        f"{i}. {etykieta}",
                        weight=ft.FontWeight.BOLD if aktywny else ft.FontWeight.NORMAL,
                        color=kolor,
                    ),
                    on_click=(lambda e, krok=i: self.idz_do_kroku(krok)),
                    ink=True,
                    border_radius=4,
                    padding=ft.Padding(4, 2, 4, 2),
                )
            )
        return ft.Row(elementy, spacing=8, wrap=True)

    def pokaz_blad(self, bledy: list[str] | str) -> None:
        if isinstance(bledy, list):
            tresc = ft.Column([ft.Text(f"• {b}") for b in bledy], tight=True)
        else:
            tresc = ft.Text(bledy)

        dlg = ft.AlertDialog(
            title=ft.Text("Popraw dane"),
            content=tresc,
            actions=[ft.TextButton("OK", on_click=lambda e: self.page.pop_dialog())],
        )
        self.page.show_dialog(dlg)

    def sprawdz_aktualizacje(self) -> None:
        wynik = aktualizacje.sprawdz()

        if wynik.blad:
            tresc = ft.Text(wynik.blad)
            akcje = [ft.TextButton("OK", on_click=lambda e: self.page.pop_dialog())]
        elif wynik.dostepna_nowsza:
            tresc = ft.Text(
                f"Dostępna nowa wersja {wynik.wersja_najnowsza} "
                f"(masz {aktualizacje.WERSJA_APP}). Otworzyć stronę pobierania?"
            )

            def otworz(e: ft.Event) -> None:
                aktualizacje.otworz_strone_pobierania(wynik.url_do_otwarcia)
                self.page.pop_dialog()

            akcje = [
                ft.TextButton("Anuluj", on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton("Pobierz", on_click=otworz),
            ]
        else:
            tresc = ft.Text(f"Masz najnowszą wersję ({aktualizacje.WERSJA_APP}).")
            akcje = [ft.TextButton("OK", on_click=lambda e: self.page.pop_dialog())]

        self.page.show_dialog(
            ft.AlertDialog(title=ft.Text("Aktualizacje"), content=tresc, actions=akcje)
        )

    def pokaz_ustawienia(self) -> None:
        biezace = ustawienia.wczytaj()

        pole_numery = ft.TextField(
            label="Plik Numery_zlecen_2026.xlsx",
            value=biezace.get("sciezka_numery_zlecen") or "",
            hint_text="wklej/wpisz pełną ścieżkę albo wybierz przyciskiem obok",
            expand=True,
        )
        blad_numery = ft.Text("", color=ft.Colors.RED_800, size=11)

        async def wybierz_plik_numery(e: ft.Event) -> None:
            wynik = await self._file_picker.pick_files(
                dialog_title="Wybierz plik Numery_zlecen_2026.xlsx",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["xlsx"],
            )
            if not wynik:
                return
            sciezka = wynik[0].path
            # Tryb web: przeglądarka nie udostępnia pełnej ścieżki pliku (tylko
            # samą nazwę, czasem wcale) - w tym trybie okienko wyboru nie da się
            # użyć do niczego poza podpowiedzią nazwy, więc zostawiamy pole do
            # ręcznego wpisania/wklejenia zamiast nadpisywać je bezużyteczną
            # wartością.
            if not sciezka or not Path(sciezka).is_absolute():
                blad_numery.value = (
                    "Przeglądarka nie udostępnia pełnej ścieżki do wybranego pliku "
                    "(ograniczenie trybu web) — wpisz albo wklej ją ręcznie w polu "
                    "wyżej, np. skopiowaną z paska adresu Eksploratora plików."
                )
                blad_numery.update()
                return
            blad_numery.value = ""
            pole_numery.value = sciezka
            pole_numery.update()
            blad_numery.update()

        opcje_account = [ft.DropdownOption(key="brak", text="Brak")] + [
            ft.DropdownOption(key=a, text=a) for a in lp.lista_accountow()
        ]
        dd_akant = ft.Dropdown(
            label="Domyślny account manager",
            value=biezace.get("domyslny_account_manager") or "brak",
            options=opcje_account,
            expand=True,
        )

        pole_folder = ft.TextField(
            label="Folder zapisu wygenerowanych zleceń (nadrzędny)",
            value=biezace.get("folder_eksportu") or str(eksport_nazwy.FOLDER_EKSPORTU_DOMYSLNY),
            hint_text="wklej/wpisz ścieżkę albo wybierz przyciskiem obok",
            expand=True,
        )
        blad_folder = ft.Text("", color=ft.Colors.RED_800, size=11)

        async def wybierz_folder(e: ft.Event) -> None:
            try:
                wynik = await self._file_picker.get_directory_path(
                    dialog_title="Wybierz folder zapisu zleceń",
                )
            except ft.FletUnsupportedPlatformException:
                # Natywny wybór folderu nie działa w trybie web (przeglądarka
                # nie ma dostępu do wyboru katalogów systemowych) - pole zostaje
                # edytowalne, żeby dało się ścieżkę wkleić/wpisać ręcznie.
                blad_folder.value = (
                    "Wybór folderu przez okno systemowe działa tylko w wersji "
                    "desktopowej aplikacji. Wpisz albo wklej ścieżkę ręcznie w polu wyżej."
                )
                blad_folder.update()
                return
            if wynik:
                blad_folder.value = ""
                pole_folder.value = wynik
                pole_folder.update()
                blad_folder.update()

        def zapisz(e: ft.Event) -> None:
            akant = dd_akant.value
            ustawienia.zapisz(
                sciezka_numery_zlecen=pole_numery.value or None,
                domyslny_account_manager=None if akant in (None, "brak") else akant,
                folder_eksportu=pole_folder.value or None,
            )
            self.page.pop_dialog()
            self.odswiez()

        dlg = ft.AlertDialog(
            title=ft.Text("Ustawienia"),
            content=ft.Column(
                [
                    ft.Text("Plik z numerami zleceń", weight=ft.FontWeight.BOLD, size=12),
                    ft.Row(
                        [
                            pole_numery,
                            ft.IconButton(icon=ft.Icons.FOLDER_OPEN, on_click=wybierz_plik_numery),
                        ]
                    ),
                    blad_numery,
                    ft.Divider(),
                    ft.Text("Domyślny account manager", weight=ft.FontWeight.BOLD, size=12),
                    ft.Text(
                        "Jeśli wybierzesz nazwisko, krok 1 ustawi je na stałe (bez możliwości "
                        "zmiany). Wybierz „Brak”, żeby zostawić wolny wybór w kroku 1.",
                        size=11,
                        color=ft.Colors.GREY_700,
                    ),
                    dd_akant,
                    ft.Divider(),
                    ft.Text("Folder zapisu zleceń", weight=ft.FontWeight.BOLD, size=12),
                    ft.Row(
                        [
                            pole_folder,
                            ft.IconButton(icon=ft.Icons.FOLDER_OPEN, on_click=wybierz_folder),
                        ]
                    ),
                    blad_folder,
                ],
                tight=True,
                spacing=8,
                width=480,
            ),
            actions=[
                ft.TextButton("Anuluj", on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton("Zapisz", on_click=zapisz),
            ],
        )
        self.page.show_dialog(dlg)
