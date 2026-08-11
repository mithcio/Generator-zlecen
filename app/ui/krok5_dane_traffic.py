import flet as ft

from app.models.dane_traffic import DaneTraffic
from app.services import cennik, generator_wydawcy
from app.services.eksport_nazwy import folder_zlecenia, nazwa_pliku_dane_traffic
from app.services.generator_dane_traffic import generuj_dane_traffic
from app.services.kalkulacje import MIESIACE_PL, etykieta_liczby, liczba_dla_okresu
from app.ui.krok4_podglad import dane_pomocnicze, zbuduj_zlecenie
from app.ui.pola_pomocnicze import lista_bledow, naglowek_kroku, pole_dropdown_zamkniety, pole_tekstowe
from app.ui.stan import LICZBA_KROKOW, StanKreatora

# Na razie pojedynczy wybór - jeśli wybrany (inny niż "brak"), krok generuje
# dodatkowo IO/brief dla tego wydawcy razem z Dane Traffic, patrz
# app/services/generator_wydawcy.py. PolaWspolne.wydawcy_zewnetrzni w
# app/models/kampania.py jest już listą pod przyszły wielokrotny wybór.
WYDAWCY_ZEWNETRZNI = ["brak", "KIDOZ", "ODEEO", "ADVERTY", "CRAZYGAMES", "POKI"]


def buduj(kreator) -> ft.Control:
    stan = kreator.stan
    zlecenie, bledy = zbuduj_zlecenie(stan)

    tresc: list[ft.Control] = [naglowek_kroku(5, LICZBA_KROKOW, "Dane Traffic")]

    if bledy:
        tresc.append(lista_bledow(bledy))
        tresc.append(
            ft.Row(
                [ft.TextButton("Wstecz", on_click=lambda e: kreator.wroc())],
                alignment=ft.MainAxisAlignment.START,
            )
        )
        return ft.Column(tresc, spacing=16)

    tresc.append(_podsumowanie(zlecenie))
    tresc.append(ft.Divider())
    tresc.append(_tabela_miesiecy(zlecenie))
    tresc.append(ft.Divider())
    tresc.append(_pola_edytowalne(kreator, stan))

    def nowe_zlecenie(e: ft.Event) -> None:
        kreator.stan = StanKreatora()
        kreator.odswiez()

    ma_wydawce = stan.wydawca_zewnetrzny != "brak"

    def _wykonaj_generowanie(e: ft.Event | None) -> None:
        dane_traffic = DaneTraffic(
            uwagi_traffic=stan.uwagi_traffic, link_spot=stan.link_spot, link_kody=stan.link_kody,
        )
        folder = folder_zlecenia(stan.nr_zlecenia)
        nazwa_pliku = nazwa_pliku_dane_traffic(stan.klient, stan.brand, stan.nr_zlecenia)
        try:
            sciezka = generuj_dane_traffic(zlecenie, dane_traffic, folder / f"{nazwa_pliku}.xlsx")
        except OSError as err:
            kreator.pokaz_blad([f"Nie udało się zapisać pliku: {err}"])
            return
        stan.ostatnia_sciezka_dane_traffic = str(sciezka)

        if ma_wydawce:
            if stan.wydawca_zewnetrzny == "POKI" and not stan.poki_placement:
                kreator.pokaz_blad(["Wybierz placement POKI."])
                kreator.odswiez()
                return
            _, spolka, kontakt, _ = dane_pomocnicze(stan)
            try:
                if stan.wydawca_zewnetrzny == "POKI":
                    sciezka_wydawcy = generator_wydawcy.generuj_poki(
                        zlecenie, spolka, kontakt, folder, stan.poki_placement
                    )
                else:
                    sciezka_wydawcy = generator_wydawcy.GENERATORY[stan.wydawca_zewnetrzny](
                        zlecenie, spolka, kontakt, folder
                    )
            except (OSError, generator_wydawcy.BladSzablonuWydawcy, cennik.BladCennika) as err:
                kreator.pokaz_blad([f"Dane Traffic zapisane, ale nie udało się zapisać pliku dla {stan.wydawca_zewnetrzny}: {err}"])
                kreator.odswiez()
                return
            stan.ostatnia_sciezka_wydawcy = str(sciezka_wydawcy)
        else:
            stan.ostatnia_sciezka_wydawcy = None

        kreator.odswiez()

    def generuj_sam_plik(e: ft.Event) -> None:
        if ma_wydawce and not generator_wydawcy.czy_format_pasuje(
            stan.wydawca_zewnetrzny, stan.format_reklamowy
        ):
            _pokaz_ostrzezenie_niezgodnego_formatu(kreator, stan, _wykonaj_generowanie)
            return
        _wykonaj_generowanie(e)

    tresc.append(
        ft.Row(
            [
                ft.OutlinedButton(
                    f"Generuj Dane Traffic + plik {stan.wydawca_zewnetrzny}" if ma_wydawce else "Generuj plik Dane Traffic",
                    on_click=generuj_sam_plik,
                ),
            ],
        )
    )
    if stan.ostatnia_sciezka_dane_traffic:
        tresc.append(
            ft.Container(
                content=ft.Text(
                    f"Zapisano: {stan.ostatnia_sciezka_dane_traffic}", selectable=True, color=ft.Colors.GREEN_800,
                ),
                bgcolor=ft.Colors.GREEN_50,
                border_radius=8,
                padding=12,
            )
        )
    if stan.ostatnia_sciezka_wydawcy:
        tresc.append(
            ft.Container(
                content=ft.Text(
                    f"Zapisano: {stan.ostatnia_sciezka_wydawcy}", selectable=True, color=ft.Colors.GREEN_800,
                ),
                bgcolor=ft.Colors.GREEN_50,
                border_radius=8,
                padding=12,
            )
        )

    tresc.append(
        ft.Row(
            [
                ft.TextButton("Wstecz", on_click=lambda e: kreator.wroc()),
                ft.FilledButton("Nowe zlecenie", on_click=nowe_zlecenie),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
    )
    return ft.Column(tresc, spacing=16, scroll=ft.ScrollMode.AUTO)


def _fmt_data(d) -> str:
    return d.strftime("%d.%m.%Y")


def _fmt_liczba(x: float) -> str:
    return f"{round(x):,}".replace(",", " ")


def _wiersz(etykieta: str, wartosc: str) -> ft.Row:
    return ft.Row([ft.Text(etykieta, width=180, weight=ft.FontWeight.W_500), ft.Text(wartosc, expand=True)])


def _podsumowanie(zlecenie) -> ft.Control:
    """Skrót danych, które traffic potrzebuje z już wypełnionego zlecenia -
    te pola nie są tu edytowalne (edycja w krokach 2/3), tylko pokazane dla
    kontekstu, żeby nie trzeba było przełączać się między krokami."""
    pola = zlecenie.pola
    capping_tekst = str(pola.capping) if pola.capping is not None else "brak"
    wiersze = [
        _wiersz("Numer zlecenia", pola.nr_zlecenia),
        _wiersz("Nazwa kampanii", pola.nazwa_kampanii),
        _wiersz("Osoba kontaktowa", pola.zlecajacy),
        _wiersz("Model sprzedaży", pola.model_sprzedazy),
        _wiersz("Termin startu", _fmt_data(zlecenie.data_startu)),
        _wiersz("Termin końca", _fmt_data(zlecenie.data_konca)),
        _wiersz("Capp", capping_tekst),
        _wiersz("Formaty", pola.format_reklamowy),
        _wiersz("Target", pola.target),
        _wiersz("Spółka", pola.podmiot_realizujacy),
    ]
    return ft.Container(
        content=ft.Column(wiersze, spacing=6),
        bgcolor=ft.Colors.GREY_50,
        border_radius=8,
        padding=16,
    )


def _tabela_miesiecy(zlecenie) -> ft.Control:
    """Rozbicie liczby wyświetleń/klików na miesiące - ten sam układ
    (Okres/Miesiąc | Budżet | Liczba) co tabela okresów w kroku 3, żeby
    traffic widział dokładnie te same liczby, tylko podpisane nazwą
    miesiąca zamiast zakresu dat (każdy okres = jeden miesiąc, patrz
    waliduj_okres w app/services/walidacja.py)."""
    pola = zlecenie.pola
    etykieta_kolumny = etykieta_liczby(pola.model_sprzedazy)
    posortowane = sorted(zlecenie.okresy, key=lambda o: o.data_startu)

    wiersze = [
        ft.Row(
            [
                ft.Text("Miesiąc", width=180, size=11, color=ft.Colors.GREY_600),
                ft.Text("Budżet", width=140, size=11, color=ft.Colors.GREY_600),
                ft.Text(etykieta_kolumny, width=160, size=11, color=ft.Colors.GREY_600),
            ]
        )
    ]
    for okres in posortowane:
        liczba = liczba_dla_okresu(pola.model_sprzedazy, pola.koszt_jednostkowy, okres.budzet)
        etykieta_miesiaca = f"{MIESIACE_PL[okres.data_startu.month - 1].capitalize()} {okres.data_startu.year}"
        wiersze.append(
            ft.Row(
                [
                    ft.Text(etykieta_miesiaca, width=180),
                    ft.Text(f"{okres.budzet:,.2f} PLN".replace(",", " ").replace(".", ","), width=140),
                    ft.Text(_fmt_liczba(liczba), width=160),
                ]
            )
        )
    wiersze.append(
        ft.Row(
            [
                ft.Text("Razem", weight=ft.FontWeight.BOLD, width=180),
                ft.Text(
                    f"{zlecenie.budzet_total:,.2f} PLN".replace(",", " ").replace(".", ","),
                    weight=ft.FontWeight.BOLD,
                    width=140,
                ),
                ft.Text(_fmt_liczba(zlecenie.liczba_total), weight=ft.FontWeight.BOLD, width=160),
            ]
        )
    )
    return ft.Column([ft.Text("Rozbicie na miesiące", weight=ft.FontWeight.BOLD), *wiersze], spacing=6)


def _pokaz_ostrzezenie_niezgodnego_formatu(kreator, stan, kontynuuj) -> None:
    """Format reklamowy z kroku 2 zwyczajowo nie pasuje do wybranego
    wydawcy zewnętrznego (patrz generator_wydawcy.czy_format_pasuje) - to
    na razie tylko ostrzeżenie, nie blokada, więc generowanie da się
    świadomie przepchnąć dalej."""

    def _kontynuuj(e: ft.Event) -> None:
        kreator.page.pop_dialog()
        kontynuuj(e)

    dlg = ft.AlertDialog(
        title=ft.Text("Sprawdź przed kontynuacją"),
        content=ft.Text(
            f"Format „{stan.format_reklamowy}” zwykle nie pasuje do wydawcy {stan.wydawca_zewnetrzny}. "
            "Wygenerować pliki mimo to?",
            color=ft.Colors.ORANGE_900,
        ),
        actions=[
            ft.TextButton("Wróć i popraw", on_click=lambda e: kreator.page.pop_dialog()),
            ft.FilledButton("Kontynuuj mimo to", on_click=_kontynuuj),
        ],
    )
    kreator.page.show_dialog(dlg)


def _pola_edytowalne(kreator, stan) -> ft.Control:
    def ustaw(pole: str):
        def _handler(wartosc: str) -> None:
            setattr(stan, pole, wartosc)

        return _handler

    def ustaw_wydawce(wartosc: str) -> None:
        stan.wydawca_zewnetrzny = wartosc
        kreator.odswiez()

    pola = [
        ft.Text("Dane dla traffic", weight=ft.FontWeight.BOLD),
        pole_tekstowe(
            "Uwagi dla traffic", stan.uwagi_traffic, ustaw("uwagi_traffic"),
            wieloliniowe=True, podpowiedz="np. ustalenia z traffic/wydawcą",
        ),
        pole_tekstowe(
            "Link do Spotu", stan.link_spot, ustaw("link_spot"), podpowiedz="link do kreacji/spotu",
        ),
        pole_tekstowe(
            "Link do Kodów", stan.link_kody, ustaw("link_kody"), podpowiedz="link do kodów trackingowych",
        ),
        pole_dropdown_zamkniety(
            "Wydawcy zewnętrzni", WYDAWCY_ZEWNETRZNI, stan.wydawca_zewnetrzny, ustaw_wydawce,
        ),
    ]
    if stan.wydawca_zewnetrzny == "POKI":
        # POKI ma własny słownik placementów (nie ten sam co "Format
        # reklamowy" gdzie indziej w kreatorze) - decyduje, jaka stawka z
        # cennika trafi na brief (patrz generator_wydawcy.PLACEMENTY_POKI).
        pola.append(
            pole_dropdown_zamkniety(
                "Placement POKI", generator_wydawcy.PLACEMENTY_POKI, stan.poki_placement, ustaw("poki_placement"),
            )
        )
    return ft.Column(pola, spacing=12)
