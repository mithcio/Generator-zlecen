from datetime import date

import flet as ft

from app.models.okres import Okres
from app.services.kalkulacje import auto_podziel_budzet, etykieta_liczby, liczba_dla_okresu
from app.services.walidacja import waliduj_okres
from app.ui.kalendarz import widok_kalendarza
from app.ui.pola_pomocnicze import (
    STYL_PODPOWIEDZI,
    naglowek_kroku,
    pole_dropdown_zamkniety,
    pole_z_etykieta_na_ramce,
)
from app.ui.stan import LICZBA_KROKOW

MODELE_SPRZEDAZY = ["CPM", "CPC", "CPV", "FF"]


def _fmt(d: date | None) -> str:
    return d.strftime("%d.%m.%Y") if d else "— wybierz datę —"


def buduj(kreator) -> ft.Control:
    stan = kreator.stan

    tabela = _tabela_okresow(kreator)
    formularz_dodawania = _formularz_dodawania(kreator)

    def dalej(e: ft.Event) -> None:
        # Liczone przy kliknięciu (nie raz na starcie renderu), z tych samych
        # powodów co w kroku 2: pola nie przebudowują całej strony przy każdej
        # zmianie, więc stan trzeba czytać na bieżąco.
        bledy = []
        if not stan.model_sprzedazy:
            bledy.append("Wybierz model sprzedaży.")
        elif stan.model_sprzedazy != "FF":
            try:
                if float(str(stan.koszt_jednostkowy).replace(",", ".")) <= 0:
                    raise ValueError
            except (ValueError, AttributeError):
                bledy.append(f"Uzupełnij poprawny koszt jednostkowy ({stan.model_sprzedazy}).")
        if not stan.okresy:
            bledy.append("Dodaj przynajmniej jeden okres (budżet + daty startu/końca).")
        if bledy:
            kreator.pokaz_blad(bledy)
            return
        stan.krok = 4
        kreator.odswiez()

    return ft.Column(
        [
            naglowek_kroku(3, LICZBA_KROKOW, "Okresy (budżet i daty)"),
            ft.Text(
                "Jeden okres = jednorazowa kampania. Więcej niż jeden okres = "
                "kampania przejściowa — budżet, liczba i zakres dat na zleceniu "
                "zsumują/rozciągną się automatycznie.",
                size=12,
                color=ft.Colors.GREY_700,
            ),
            tabela,
            ft.Divider(),
            formularz_dodawania,
            ft.Row(
                [
                    ft.TextButton("Wstecz", on_click=lambda e: kreator.wroc()),
                    ft.FilledButton("Dalej", on_click=dalej),
                ],
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            ),
        ],
        spacing=16,
    )


def _fmt_liczba(x: float) -> str:
    return f"{round(x):,}".replace(",", " ")


def _tabela_okresow(kreator) -> ft.Control:
    stan = kreator.stan
    if not stan.okresy:
        return ft.Text("Brak dodanych okresów.", italic=True, color=ft.Colors.GREY_600)

    try:
        koszt = float(str(stan.koszt_jednostkowy).replace(",", "."))
    except (ValueError, AttributeError):
        koszt = 0.0
    etykieta = etykieta_liczby(stan.model_sprzedazy)

    def usun(indeks: int):
        def _handler(e: ft.Event) -> None:
            stan.okresy.pop(indeks)
            kreator.odswiez()

        return _handler

    wiersze = [
        ft.Row(
            [
                ft.Text("Okres", width=220, size=11, color=ft.Colors.GREY_600),
                ft.Text("Budżet", width=140, size=11, color=ft.Colors.GREY_600),
                ft.Text(f"Szacunek: {etykieta}", width=160, size=11, color=ft.Colors.GREY_600),
            ]
        )
    ]
    for i, okres in enumerate(stan.okresy):
        bledy = waliduj_okres(okres)
        liczba = liczba_dla_okresu(stan.model_sprzedazy, koszt, okres.budzet)
        wiersze.append(
            ft.Row(
                [
                    ft.Text(f"{_fmt(okres.data_startu)} — {_fmt(okres.data_konca)}", width=220),
                    ft.Text(f"{okres.budzet:,.2f} PLN".replace(",", " ").replace(".", ","), width=140),
                    ft.Text(_fmt_liczba(liczba), width=160),
                    ft.Text(" / ".join(bledy), color=ft.Colors.RED_700, size=11, expand=True),
                    ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, on_click=usun(i)),
                ]
            )
        )

    liczba_total = sum(liczba_dla_okresu(stan.model_sprzedazy, koszt, o.budzet) for o in stan.okresy)
    wiersze.append(
        ft.Row(
            [
                ft.Text(
                    f"Razem: {sum(o.budzet for o in stan.okresy):,.2f} PLN".replace(",", " ").replace(".", ","),
                    weight=ft.FontWeight.BOLD,
                    width=360,
                ),
                ft.Text(f"{etykieta}: {_fmt_liczba(liczba_total)}", weight=ft.FontWeight.BOLD),
            ]
        )
    )
    if not koszt and stan.model_sprzedazy != "FF":
        wiersze.append(
            ft.Text(
                "Uzupełnij model sprzedaży i koszt jednostkowy poniżej, żeby zobaczyć szacunek.",
                size=11, italic=True, color=ft.Colors.ORANGE_800,
            )
        )
    return ft.Column(wiersze, spacing=6)


def _formularz_dodawania(kreator) -> ft.Control:
    stan = kreator.stan

    def ustaw_model(wartosc: str) -> None:
        stan.model_sprzedazy = wartosc
        if wartosc == "FF":
            stan.koszt_jednostkowy = ""
        kreator.odswiez()  # etykieta/wyłączenie pola kosztu zależą od modelu — trzeba przebudować

    jest_ff = stan.model_sprzedazy == "FF"
    pole_koszt_input = ft.TextField(
        value=stan.koszt_jednostkowy,
        on_change=lambda e: setattr(stan, "koszt_jednostkowy", e.control.value or ""),
        disabled=jest_ff,
        hint_text="uzupełnij" if not jest_ff else "przy FF cały budżet = jedna opłata",
        hint_style=STYL_PODPOWIEDZI,
        width=220,
    )
    # Etykieta wcięta w górną krawędź obwódki (jak wbudowany label=
    # Dropdown-a obok) zamiast osobnego Text NAD polem - patrz
    # pole_z_etykieta_na_ramce (Fletowy label= na pustym TextField wjeżdża w
    # środek pola czarną czcionką, wyglądając jak już wpisana wartość).
    pole_koszt = pole_z_etykieta_na_ramce(
        stan.model_sprzedazy or "Koszt jednostkowy", pole_koszt_input, width=220
    )
    # Dropdown modelu ma stałą szerokość i wiersz BEZ wrap=True — Dropdown
    # wewnątrz Row(wrap=True) wywala się w tej wersji Fletu (pusty szary
    # prostokąt zamiast formularza; potwierdzone izolowanym testem), więc ten
    # wiersz ma tylko dwa pola o stałej szerokości i nigdy nie musi się zawijać.
    dropdown_modelu = pole_dropdown_zamkniety(
        "Model sprzedaży", MODELE_SPRZEDAZY, stan.model_sprzedazy, ustaw_model
    )
    dropdown_modelu.expand = False
    dropdown_modelu.width = 220
    wiersz_modelu = ft.Row(
        [dropdown_modelu, pole_koszt],
        spacing=12,
    )

    pole_budzet = ft.TextField(
        label="Budżet (PLN)",
        value=stan.nowy_okres_budzet,
        on_change=lambda e: setattr(stan, "nowy_okres_budzet", e.control.value or ""),
        width=180,
    )

    wiersz_dat = ft.Row(
        [
            ft.OutlinedButton(
                f"Data startu: {_fmt(stan.nowy_okres_start)}",
                on_click=lambda e: _otworz_kalendarz(kreator, "start"),
            ),
            ft.OutlinedButton(
                f"Data końca: {_fmt(stan.nowy_okres_koniec)}",
                on_click=lambda e: _otworz_kalendarz(kreator, "koniec"),
            ),
            pole_budzet,
        ],
        spacing=12,
        wrap=True,
    )

    kalendarz = _widok_otwartego_kalendarza(kreator)

    def dodaj_jeden(e: ft.Event) -> None:
        blad = _sprawdz_dane_nowego_okresu(stan)
        if blad:
            kreator.pokaz_blad([blad])
            return
        nowy_okres = Okres(
            data_startu=stan.nowy_okres_start,
            data_konca=stan.nowy_okres_koniec,
            budzet=float(stan.nowy_okres_budzet.replace(",", ".")),
        )
        # Jeden okres = jeden miesiąc (patrz waliduj_okres) - zakres na dwa
        # miesiące tu nie przechodzi; do tego służy "Rozbij automatycznie"
        # obok, który sam dzieli na miesięczne kawałki.
        bledy_okresu = waliduj_okres(nowy_okres)
        if bledy_okresu:
            kreator.pokaz_blad(bledy_okresu)
            return
        stan.okresy.append(nowy_okres)
        _wyczysc_nowy_okres(stan)
        kreator.odswiez()

    def rozbij_auto(e: ft.Event) -> None:
        blad = _sprawdz_dane_nowego_okresu(stan)
        if blad:
            kreator.pokaz_blad([blad])
            return
        try:
            nowe = auto_podziel_budzet(
                float(stan.nowy_okres_budzet.replace(",", ".")),
                stan.nowy_okres_start,
                stan.nowy_okres_koniec,
            )
        except ValueError as err:
            kreator.pokaz_blad([str(err)])
            return
        stan.okresy.extend(nowe)
        _wyczysc_nowy_okres(stan)
        kreator.odswiez()

    return ft.Column(
        [
            ft.Text("Dodaj okres", weight=ft.FontWeight.BOLD),
            wiersz_modelu,
            wiersz_dat,
            kalendarz if kalendarz else ft.Container(),
            ft.Row(
                [
                    ft.OutlinedButton("Dodaj jako jeden okres", on_click=dodaj_jeden),
                    ft.OutlinedButton(
                        "Rozbij automatycznie na miesiące (proporcjonalnie do dni)",
                        on_click=rozbij_auto,
                    ),
                ],
                spacing=12,
                wrap=True,
            ),
        ],
        spacing=12,
    )


def _widok_otwartego_kalendarza(kreator) -> ft.Control | None:
    stan = kreator.stan
    if stan.kalendarz_pole is None:
        return None

    if stan.kalendarz_pole == "start":
        data_wybrana = stan.nowy_okres_start
        data_min = None  # data startu nie ma dolnego ograniczenia
    else:
        data_wybrana = stan.nowy_okres_koniec
        data_min = stan.nowy_okres_start  # blokuje dni wcześniejsze niż data startu

    return widok_kalendarza(
        rok=stan.kalendarz_rok,
        miesiac=stan.kalendarz_miesiac,
        data_wybrana=data_wybrana,
        data_min=data_min,
        on_wybierz_dzien=lambda d: _wybierz_dzien(kreator, stan.kalendarz_pole, d),
        on_zmien_miesiac=lambda delta: _zmien_miesiac(kreator, delta),
        on_anuluj=lambda: _zamknij_kalendarz(kreator),
    )


def _otworz_kalendarz(kreator, ktora: str) -> None:
    stan = kreator.stan
    stan.kalendarz_pole = ktora
    if ktora == "start":
        baza = stan.nowy_okres_start or date.today()
    else:
        # Domyślnie miesiąc daty startu (jeśli już wybrana) — od razu widać,
        # że wcześniejsze dni są zablokowane, zamiast trzeba było się cofać.
        baza = stan.nowy_okres_koniec or stan.nowy_okres_start or date.today()
    stan.kalendarz_rok = baza.year
    stan.kalendarz_miesiac = baza.month
    kreator.odswiez()


def _zmien_miesiac(kreator, delta: int) -> None:
    stan = kreator.stan
    nowy_miesiac = stan.kalendarz_miesiac + delta
    if nowy_miesiac < 1:
        stan.kalendarz_miesiac = 12
        stan.kalendarz_rok -= 1
    elif nowy_miesiac > 12:
        stan.kalendarz_miesiac = 1
        stan.kalendarz_rok += 1
    else:
        stan.kalendarz_miesiac = nowy_miesiac
    kreator.odswiez()


def _wybierz_dzien(kreator, ktora: str, wybrana_data: date) -> None:
    stan = kreator.stan
    if ktora == "start":
        stan.nowy_okres_start = wybrana_data
    else:
        stan.nowy_okres_koniec = wybrana_data
    stan.kalendarz_pole = None
    kreator.odswiez()


def _zamknij_kalendarz(kreator) -> None:
    kreator.stan.kalendarz_pole = None
    kreator.odswiez()


def _sprawdz_dane_nowego_okresu(stan) -> str | None:
    if not stan.nowy_okres_start or not stan.nowy_okres_koniec:
        return "Wybierz datę startu i końca."
    if stan.nowy_okres_koniec < stan.nowy_okres_start:
        return "Data końca nie może być wcześniejsza niż data startu."
    try:
        wartosc = float(stan.nowy_okres_budzet.replace(",", "."))
    except (ValueError, AttributeError):
        return "Budżet musi być liczbą (np. 1234.56)."
    if wartosc <= 0:
        return "Budżet musi być liczbą większą od zera."
    return None


def _wyczysc_nowy_okres(stan) -> None:
    stan.nowy_okres_start = None
    stan.nowy_okres_koniec = None
    stan.nowy_okres_budzet = ""
