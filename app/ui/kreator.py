"""Orkiestrator kreatora: trzyma stan, przełącza kroki, wspólne akcje UI
(błędy, nawigacja, ustawienia) wołane przez poszczególne kroki."""
from datetime import datetime
from pathlib import Path

import flet as ft
import openpyxl

from app.services import aktualizacje
from app.services import eksport_nazwy
from app.services import lookup_podmiotu as lp
from app.services import numeracja
from app.services import ustawienia
from app.services.lokalizacje import czy_spakowana_appka, katalog_danych_uzytkownika
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
            title=ft.Row(
                [
                    ft.Text("Generator Zleceń"),
                    # Widoczny numer wersji - żeby zgłaszający problem od razu
                    # wiedział/mógł podać, jaki build ma zainstalowany (patrz
                    # WERSJA_APP w aktualizacje.py), bez szukania w Ustawieniach.
                    ft.Text(f"v{aktualizacje.WERSJA_APP}", size=12, color=ft.Colors.GREY_500),
                ],
                spacing=8,
                vertical_alignment=ft.CrossAxisAlignment.END,
            ),
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

        # Przy "x" na oknie: jeśli krok 2 zdążył zarezerwować numer, a
        # zlecenie nie zostało jeszcze wygenerowane (krok 4), ten numer
        # zostałby "wiszący" - zajęty w pliku, ale nieużyty przez nikogo -
        # patrz obsluz_zamkniecie_okna.
        self.page.window.prevent_close = True
        self.page.window.on_event = self.obsluz_zamkniecie_okna

    async def obsluz_zamkniecie_okna(self, e: ft.WindowEvent) -> None:
        if e.type != ft.WindowEventType.CLOSE:
            return

        if not self.stan.numer_automatyczny_aktywny or not self.stan.nr_zlecenia_automatyczny:
            await self.page.window.destroy()
            return

        numer = self.stan.nr_zlecenia_automatyczny
        podmiot = self.stan.podmiot_realizujacy

        async def zwolnij_i_zamknij(ev: ft.Event) -> None:
            try:
                numeracja.zwolnij_numer(numer, podmiot)
            except Exception:
                # Plik akurat niedostępny (otwarty w Excelu/sync) albo inny
                # nieoczekiwany błąd - nie blokujemy zamykania programu z
                # tego powodu, numer po prostu zostaje zajęty do ręcznego
                # zwolnienia później. Zamknięcie okna nie może nigdy utknąć
                # przez błąd w tle.
                pass
            await self.page.window.destroy()

        async def zamknij_bez_zwalniania(ev: ft.Event) -> None:
            await self.page.window.destroy()

        def anuluj(ev: ft.Event) -> None:
            self.page.pop_dialog()

        self.page.show_dialog(
            ft.AlertDialog(
                title=ft.Text("Masz zarezerwowany numer zlecenia"),
                content=ft.Text(
                    f"Numer {numer} jest zarezerwowany, ale zlecenie nie zostało jeszcze "
                    "wygenerowane. Zwolnić go, żeby ktoś inny mógł go użyć?"
                ),
                actions=[
                    ft.TextButton("Anuluj (nie zamykaj)", on_click=anuluj),
                    ft.TextButton(f"Zostaw zarezerwowany ({numer})", on_click=zamknij_bez_zwalniania),
                    ft.FilledButton("Zwolnij i zamknij", on_click=zwolnij_i_zamknij),
                ],
            )
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

    def pokaz_ustawienia(self, komunikat: str | None = None) -> None:
        biezace = ustawienia.wczytaj()
        # Na Androidzie/iOS nie ma pliku Numery_zlecen_2026.xlsx (OneDrive nie
        # jest tam lokalnie zamontowany) - użytkownik świadomie wpisuje numer
        # ręcznie (patrz krok 2), więc to pole na telefonie jest tylko
        # niepotrzebnym, mylącym polem w Ustawieniach.
        mobilna = bool(self.page.platform and self.page.platform.is_mobile())

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

        checkbox_uwagi_wspolne = ft.Checkbox(
            label="Wspólne pole Uwagi (wiersz do pliku kampanii ↔ 4.7 Uwagi na zleceniu)",
            value=bool(biezace.get("uwagi_wspolne")),
        )

        dd_klient_bezposredni_pole = ft.Dropdown(
            label="Klient bezpośredni w polu Agencja/Klient",
            value=biezace.get("klient_bezposredni_pole") or "agencja",
            options=[
                ft.DropdownOption(key="agencja", text="Agencja (Dom Mediowy)"),
                ft.DropdownOption(key="klient", text="Klient"),
            ],
            expand=True,
        )

        dd_jezyk_excel = ft.Dropdown(
            label="Język Excela na tym komputerze",
            value=biezace.get("jezyk_excel") or "EN",
            options=[
                ft.DropdownOption(key="PL", text="Polski"),
                ft.DropdownOption(key="EN", text="English"),
            ],
            expand=True,
        )

        pole_folder = ft.TextField(
            label="Folder zapisu wygenerowanych zleceń (nadrzędny)",
            value=biezace.get("folder_eksportu") or str(eksport_nazwy.FOLDER_EKSPORTU_DOMYSLNY),
            hint_text="wklej/wpisz ścieżkę albo wybierz przyciskiem obok",
            expand=True,
        )
        blad_folder = ft.Text("", color=ft.Colors.RED_800, size=11)

        status_import = ft.Text("", size=11)

        async def importuj_plik_danych(nazwa_docelowa: str, e: ft.Event) -> None:
            wynik = await self._file_picker.pick_files(
                dialog_title=f"Wybierz plik {nazwa_docelowa}",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["json"],
            )
            if not wynik:
                return
            sciezka_zrodlowa = wynik[0].path
            # Tryb web: jak przy wybierz_plik_numery, brak pełnej ścieżki -
            # tu nie ma pola do ręcznego wpisania (plik trzeba faktycznie
            # skopiować), więc to twardy błąd, nie tylko podpowiedź.
            if not sciezka_zrodlowa or not Path(sciezka_zrodlowa).is_absolute():
                status_import.value = (
                    "Przeglądarka nie udostępnia pełnej ścieżki do wybranego pliku "
                    "- import działa tylko w wersji desktopowej/mobilnej aplikacji."
                )
                status_import.color = ft.Colors.RED_800
                status_import.update()
                return
            try:
                docelowy_katalog = katalog_danych_uzytkownika()
                docelowy_katalog.mkdir(parents=True, exist_ok=True)
                (docelowy_katalog / nazwa_docelowa).write_bytes(Path(sciezka_zrodlowa).read_bytes())
            except OSError as err:
                status_import.value = f"Nie udało się zapisać {nazwa_docelowa}: {err}"
                status_import.color = ft.Colors.RED_800
                status_import.update()
                return
            # Zamknij i odtwórz dialog od nowa zamiast tylko pokazać status w
            # miejscu - lista accountów (dd_akant) jest budowana raz, przy
            # otwarciu dialogu, z lp.lista_accountow() - bez ponownego
            # zbudowania dialogu użytkownik importuje mediafarm.json, a lista
            # nadal pokazuje "Brak", co wygląda jak import się nie udał.
            self.page.pop_dialog()
            self.pokaz_ustawienia(komunikat=f"Zaimportowano {nazwa_docelowa}.")

        # on_click musi dostać funkcję async BEZPOŚREDNIO (tak jak
        # wybierz_plik_numery/wybierz_folder niżej) - Flet rozpoznaje i
        # awaituje handler tylko wtedy, gdy sam jest coroutine function.
        # `on_click=lambda e: importuj_plik_danych("x", e)` wygląda poprawnie,
        # ale lambda jest zwykłą funkcją synchroniczną - jej wywołanie tworzy
        # coroutine i od razu ją porzuca (nigdy nie jest odpalona), więc klik
        # nic nie robi. Stąd dwa małe opakowania zamiast jednej lambdy.
        async def importuj_mediafarm(e: ft.Event) -> None:
            await importuj_plik_danych("mediafarm.json", e)

        async def importuj_podmioty(e: ft.Event) -> None:
            await importuj_plik_danych("podmioty.json", e)

        # TYMCZASOWE - do usunięcia po teście. Sprawdza empirycznie (zamiast
        # zgadywać), czy zapis openpyxl pod ścieżką zwróconą przez FilePicker
        # na Androidzie faktycznie trafia z powrotem na OneDrive, czy tylko do
        # lokalnej/odłączonej kopii - to jest dokładnie to, co
        # numeracja.zarezerwuj_numer robi na Numery_zlecen_2026.xlsx.
        status_test_zapisu = ft.Text("", size=11)

        async def testuj_zapis_onedrive(e: ft.Event) -> None:
            wynik = await self._file_picker.pick_files(
                dialog_title="Wybierz plik xlsx (np. test.xlsx) do testu zapisu",
                file_type=ft.FilePickerFileType.CUSTOM,
                allowed_extensions=["xlsx"],
            )
            if not wynik:
                return
            sciezka = wynik[0].path
            if not sciezka or not Path(sciezka).is_absolute():
                status_test_zapisu.value = "Brak pełnej ścieżki do wybranego pliku."
                status_test_zapisu.color = ft.Colors.RED_800
                status_test_zapisu.update()
                return
            znacznik = f"TEST-ZAPIS {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            try:
                wb = openpyxl.load_workbook(sciezka)
                wb.active["A1"] = znacznik
                wb.save(sciezka)
            except Exception as err:  # diagnostyka - celowo szerokie, do usunięcia
                status_test_zapisu.value = f"Błąd zapisu: {err}"
                status_test_zapisu.color = ft.Colors.RED_800
                status_test_zapisu.update()
                return
            status_test_zapisu.value = (
                f"Zapisano do A1: {znacznik}. Sprawdź na innym urządzeniu/w przeglądarce, "
                "czy ta zmiana dotarła na OneDrive."
            )
            status_test_zapisu.color = ft.Colors.GREEN_800
            status_test_zapisu.update()

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
                jezyk_excel=dd_jezyk_excel.value or "EN",
                uwagi_wspolne=checkbox_uwagi_wspolne.value or False,
                klient_bezposredni_pole=dd_klient_bezposredni_pole.value or "agencja",
            )
            self.page.pop_dialog()
            self.odswiez()

        sekcje: list[list[ft.Control]] = []

        if komunikat:
            sekcje.append([ft.Text(komunikat, color=ft.Colors.GREEN_800, size=12)])

        if czy_spakowana_appka():
            # Pierwsza sekcja, nie ostatnia - bez mediafarm.json appka nie ma
            # ŻADNEGO accounta do wyboru (patrz "Domyślny account manager"
            # niżej), więc na świeżej instalacji (zwłaszcza na Androidzie,
            # gdzie nie da się tych plików wgrać inaczej niż tym przyciskiem)
            # to jest pierwsza rzecz, którą trzeba zrobić - nie coś do
            # przewinięcia na sam dół.
            sekcje.append(
                [
                    ft.Text("Dane klienta i spółek", weight=ft.FontWeight.BOLD, size=12),
                    ft.Text(
                        "mediafarm.json i podmioty.json (nie trafiają do instalki - dane "
                        "wrażliwe) - przyciskiem niżej (działa też na telefonie, gdzie nie "
                        "da się ich po prostu wgrać przez menedżer plików) albo ręcznie, "
                        "raz na maszynę, do:",
                        size=11,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.Text(
                        str(katalog_danych_uzytkownika()),
                        size=11,
                        selectable=True,
                        weight=ft.FontWeight.BOLD,
                    ),
                    ft.Row(
                        [
                            ft.OutlinedButton(
                                "Importuj mediafarm.json",
                                on_click=importuj_mediafarm,
                            ),
                            ft.OutlinedButton(
                                "Importuj podmioty.json",
                                on_click=importuj_podmioty,
                            ),
                        ],
                        spacing=8,
                    ),
                    status_import,
                ]
            )
            sekcje.append(
                [
                    ft.Text(
                        "Test zapisu do OneDrive (tymczasowe)", weight=ft.FontWeight.BOLD, size=12
                    ),
                    ft.Text(
                        "Wybierz plik xlsx z tego samego folderu OneDrive co "
                        "Numery_zlecen_2026.xlsx (oznaczony jako dostępny offline) - appka "
                        "wpisze znacznik czasowy do komórki A1 i zapisze. Sprawdź na innym "
                        "urządzeniu/w przeglądarce OneDrive, czy zmiana faktycznie dotarła.",
                        size=11,
                        color=ft.Colors.GREY_700,
                    ),
                    ft.OutlinedButton("Testuj zapis", on_click=testuj_zapis_onedrive),
                    status_test_zapisu,
                ]
            )

        sekcje.append(
            [
                ft.Text("Domyślny account manager", weight=ft.FontWeight.BOLD, size=12),
                ft.Text(
                    "Jeśli wybierzesz nazwisko, krok 1 ustawi je na stałe (bez możliwości "
                    "zmiany). Wybierz „Brak”, żeby zostawić wolny wybór w kroku 1.",
                    size=11,
                    color=ft.Colors.GREY_700,
                ),
                dd_akant,
            ]
        )

        if not mobilna:
            sekcje.append(
                [
                    ft.Text("Plik z numerami zleceń", weight=ft.FontWeight.BOLD, size=12),
                    ft.Row(
                        [
                            pole_numery,
                            ft.IconButton(icon=ft.Icons.FOLDER_OPEN, on_click=wybierz_plik_numery),
                        ]
                    ),
                    blad_numery,
                ]
            )

        sekcje.append(
            [
                ft.Text("Język Excela", weight=ft.FontWeight.BOLD, size=12),
                ft.Text(
                    "Decyduje o nazwach funkcji w formule wklejanej do pliku kampanii "
                    "(krok „Pokaż wiersz(e) do pliku kampanii”) - musi zgadzać się z "
                    "wersją językową Excela na TYM komputerze, nie z wersją Windows.",
                    size=11,
                    color=ft.Colors.GREY_700,
                ),
                dd_jezyk_excel,
            ]
        )

        sekcje.append(
            [
                ft.Text("Pole Uwagi", weight=ft.FontWeight.BOLD, size=12),
                ft.Text(
                    "Zaznacz, żeby pole 4.7 Uwagi (zlecenie dla klienta) i kolumna Uwagi "
                    "wiersza do pliku kampanii były tą samą treścią - w obie strony "
                    "(wklejenie wiersza uzupełni 4.7, a wygenerowany wiersz przeniesie "
                    "4.7 z powrotem do kolumny Uwagi). Odznaczone = jak dotychczas, dwa "
                    "niezależne pola.",
                    size=11,
                    color=ft.Colors.GREY_700,
                ),
                checkbox_uwagi_wspolne,
            ]
        )

        sekcje.append(
            [
                ft.Text("Klient bezpośredni w polu Agencja/Klient", weight=ft.FontWeight.BOLD, size=12),
                ft.Text(
                    "Dla zlecenia na Sp. z o.o. (klient bezpośredni) wiersz do pliku "
                    "kampanii zapisuje nazwę klienta w JEDNEJ z tych dwóch kolumn "
                    "(druga zostaje pusta) - wybierz, w której. Wklejenie wiersza z "
                    "powrotem działa poprawnie niezależnie od wyboru.",
                    size=11,
                    color=ft.Colors.GREY_700,
                ),
                dd_klient_bezposredni_pole,
            ]
        )

        sekcje.append(
            [
                ft.Text("Folder zapisu zleceń", weight=ft.FontWeight.BOLD, size=12),
                ft.Row(
                    [
                        pole_folder,
                        ft.IconButton(icon=ft.Icons.FOLDER_OPEN, on_click=wybierz_folder),
                    ]
                ),
                blad_folder,
            ]
        )

        zawartosc: list[ft.Control] = []
        for i, sekcja in enumerate(sekcje):
            if i > 0:
                zawartosc.append(ft.Divider())
            zawartosc.extend(sekcja)

        dlg = ft.AlertDialog(
            title=ft.Text("Ustawienia"),
            content=ft.Column(
                zawartosc,
                tight=True,
                spacing=8,
                width=480,
                # Przybyło sekcji (język Excela, pole Uwagi...) - bez scroll ta
                # kolumna potrafi być wyższa niż okno, dialog ją wtedy po
                # prostu przycina (potwierdzone realnym zrzutem ekranu, tekst
                # ucięty w połowie zdania) - a rozwijane listy (Domyślny
                # account manager, Język Excela) w takiej sytuacji w ogóle się
                # nie otwierają, bo nie mają się gdzie zmieścić (potwierdzone
                # w przeglądarce: te same dropdowny działają przy wyższym
                # oknie, nie działają przy niższym).
                scroll=ft.ScrollMode.AUTO,
                height=520,
            ),
            actions=[
                ft.TextButton("Anuluj", on_click=lambda e: self.page.pop_dialog()),
                ft.FilledButton("Zapisz", on_click=zapisz),
            ],
        )
        self.page.show_dialog(dlg)
