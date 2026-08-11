import flet as ft

from app.models.kampania import PolaWspolne
from app.models.podmiot import DanePodmiotu
from app.models.zlecenie import Zlecenie
from app.services import lookup_podmiotu as lp
from app.services.eksport_nazwy import folder_zlecenia, nazwa_pliku_zlecenie
from app.services.eksport_wiersza import zbuduj_wiersze_do_wklejenia_per_okres
from app.services.generator_pdf import generuj_pdf
from app.services.generator_xlsx import generuj_xlsx
from app.services.walidacja import waliduj_zlecenie
from app.templates.zlecenie_layout import (
    LiniaPodpisu,
    Naglowek,
    NaglowekZIdentyfikatorem,
    Pozycja,
    Tekst,
    zbuduj_layout,
)
from app.ui.pola_pomocnicze import lista_bledow, naglowek_kroku
from app.ui.stan import LICZBA_KROKOW


def zbuduj_zlecenie(stan) -> tuple[Zlecenie | None, list[str]]:
    """Buduje Zlecenie ze stanu kreatora, zwraca (None, błędy) jeśli dane są
    niepoprawne — używane przez krok 4 (Zlecenie: podgląd + generowanie) i
    krok 5 (Dane Traffic), żeby nie zdublować reguł konwersji/walidacji."""
    bledy: list[str] = []

    # Capping pochodzi z zamkniętej listy rozwijanej ("brak" albo 1-10), więc
    # zawsze jest poprawny — nie trzeba walidować formatu.
    capping = None if stan.capping in (None, "", "brak") else int(stan.capping)

    try:
        koszt = float(str(stan.koszt_jednostkowy).replace(",", "."))
    except (ValueError, AttributeError):
        koszt = 0.0
        # FF (opłata stała) celowo nie ma kosztu jednostkowego - pole jest
        # wyłączone w kroku 3, więc puste/niepoprawne tu nie jest błędem.
        if stan.model_sprzedazy != "FF":
            bledy.append("Koszt jednostkowy musi być liczbą.")

    pola = PolaWspolne(
        account_manager=stan.account_manager,
        podmiot_realizujacy=stan.podmiot_realizujacy,
        nr_zlecenia=stan.nr_zlecenia,
        nazwa_kampanii=stan.nazwa_kampanii,
        dom_mediowy=stan.dom_mediowy,
        klient=stan.klient,
        brand=stan.brand,
        zlecajacy=stan.zlecajacy,
        target=stan.target,
        capping=capping,
        format_reklamowy=stan.format_reklamowy,
        model_sprzedazy=stan.model_sprzedazy,
        koszt_jednostkowy=koszt,
        uwagi=stan.uwagi,
        wydawcy_zewnetrzni=(
            [] if stan.wydawca_zewnetrzny in (None, "", "brak") else [stan.wydawca_zewnetrzny]
        ),
    )
    zlecenie = Zlecenie(pola=pola, okresy=stan.okresy)
    bledy.extend(waliduj_zlecenie(zlecenie))
    if bledy:
        return None, bledy
    return zlecenie, []


def dane_pomocnicze(stan) -> tuple[DanePodmiotu, object, dict, str | None]:
    """Zwraca (podmiot, spółka Mediafarm, kontakt accounta, ostrzeżenie).
    Nie wybucha, gdy dom_mediowy nie ma jeszcze wpisu w bazie podmiotów —
    zwraca puste dane fakturowe + ostrzeżenie do pokazania w UI zamiast
    zepsutego dokumentu bez wyjaśnienia."""
    podmiot = lp.znajdz_podmiot(stan.account_manager, stan.dom_mediowy, stan.klient)
    ostrzezenie = None
    if podmiot is None:
        ostrzezenie = (
            f"Nie znaleziono „{stan.dom_mediowy}” w bazie podmiotów dla accounta "
            f"{stan.account_manager}. Dane fakturowe w dokumencie będą puste — "
            "uzupełnij je ręcznie przed wysłaniem zlecenia."
        )
        podmiot = DanePodmiotu(
            nazwa=stan.dom_mediowy, adres_fakturowy=None, numery_rejestrowe=None, termin_platnosci=None
        )
    spolka = lp.spolka_mediafarm(stan.podmiot_realizujacy)
    kontakt = lp.kontakt_accounta(stan.account_manager)
    return podmiot, spolka, kontakt, ostrzezenie


def buduj(kreator) -> ft.Control:
    stan = kreator.stan
    zlecenie, bledy = zbuduj_zlecenie(stan)

    tresc: list[ft.Control] = [naglowek_kroku(4, LICZBA_KROKOW, "Zlecenie")]

    if bledy:
        tresc.append(lista_bledow(bledy))
        tresc.append(
            ft.Row(
                [ft.TextButton("Wstecz", on_click=lambda e: kreator.wroc())],
                alignment=ft.MainAxisAlignment.START,
            )
        )
        return ft.Column(tresc, spacing=16)

    podmiot, spolka, kontakt, ostrzezenie = dane_pomocnicze(stan)
    if ostrzezenie:
        tresc.append(
            ft.Container(
                content=ft.Text(ostrzezenie, color=ft.Colors.ORANGE_900),
                bgcolor=ft.Colors.ORANGE_50,
                border_radius=8,
                padding=12,
            )
        )

    layout = zbuduj_layout(zlecenie, podmiot, spolka, kontakt)
    tresc.append(_render_layout(layout))

    def dalej(e: ft.Event) -> None:
        stan.krok = 5
        kreator.odswiez()

    def przelacz_wiersze(e: ft.Event) -> None:
        stan.pokaz_wiersze_kampanii = not stan.pokaz_wiersze_kampanii
        kreator.odswiez()

    def generuj(e: ft.Event) -> None:
        # Numer jest już zarezerwowany od kroku 2 (numeracja.zarezerwuj_numer) —
        # tu tylko generujemy pliki Zlecenie (xlsx+PDF). Dane Traffic to osobny
        # plik, generowany niezależnie w kroku 5.
        folder = folder_zlecenia(stan.nr_zlecenia)
        nazwa_pliku = nazwa_pliku_zlecenie(stan.nr_zlecenia, stan.nazwa_kampanii)
        try:
            sciezka_xlsx = generuj_xlsx(zlecenie, podmiot, spolka, kontakt, folder / f"{nazwa_pliku}.xlsx")
            sciezka_pdf = generuj_pdf(zlecenie, podmiot, spolka, kontakt, folder / f"{nazwa_pliku}.pdf")
        except OSError as err:
            kreator.pokaz_blad([f"Nie udało się zapisać plików: {err}"])
            return
        stan.zlecenie_wygenerowane = (str(folder), str(sciezka_xlsx), str(sciezka_pdf))
        kreator.odswiez()

    tresc.append(
        ft.Row(
            [
                ft.OutlinedButton(
                    "Ukryj wiersz(e) do pliku kampanii"
                    if stan.pokaz_wiersze_kampanii
                    else "Pokaż wiersz(e) do pliku kampanii",
                    on_click=przelacz_wiersze,
                ),
                ft.FilledButton("Generuj zlecenie", on_click=generuj),
            ],
            spacing=12,
        )
    )
    if stan.zlecenie_wygenerowane:
        folder, xlsx, pdf = stan.zlecenie_wygenerowane
        tresc.append(
            ft.Container(
                content=ft.Column(
                    [
                        ft.Text(f"Zapisano w: {folder}", color=ft.Colors.GREEN_800),
                        ft.Text(f"Plik xlsx: {xlsx}", selectable=True, color=ft.Colors.GREEN_800),
                        ft.Text(f"Plik PDF: {pdf}", selectable=True, color=ft.Colors.GREEN_800),
                    ],
                    spacing=4,
                ),
                bgcolor=ft.Colors.GREEN_50,
                border_radius=8,
                padding=12,
            )
        )
    if stan.pokaz_wiersze_kampanii:
        tresc.append(ft.Divider())
        tresc.append(widok_wierszy_do_wklejenia(zlecenie))

    tresc.append(
        ft.Row(
            [
                ft.TextButton("Wstecz", on_click=lambda e: kreator.wroc()),
                ft.FilledButton("Dalej", on_click=dalej),
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
        )
    )
    return ft.Column(tresc, spacing=16, scroll=ft.ScrollMode.AUTO)


def widok_wierszy_do_wklejenia(zlecenie: Zlecenie) -> ft.Control:
    """Jedno pole tekstowe per okres (miesiąc), podpisane zakresem dat,
    którego dotyczy — każdy miesiąc trafia do innej zakładki pliku kampanii,
    więc osobne pola zamiast jednego dużego z wszystkimi wierszami naraz.
    Dostępne w kroku 4 niezależnie od generowania zlecenia (przycisk
    "Pokaż wiersz(e) do pliku kampanii")."""
    wiersze = zbuduj_wiersze_do_wklejenia_per_okres(zlecenie)
    pola = [
        ft.Column(
            [
                ft.Text(
                    f"Okres: {okres.data_startu.strftime('%d.%m.%Y')} – {okres.data_konca.strftime('%d.%m.%Y')}",
                    size=12,
                    weight=ft.FontWeight.W_500,
                    color=ft.Colors.GREY_700,
                ),
                ft.TextField(value=wiersz_tekst, read_only=True),
            ],
            spacing=2,
        )
        for okres, wiersz_tekst in wiersze
    ]
    return ft.Column(
        [
            ft.Text("Wiersz(e) do wklejenia do pliku z kampaniami", weight=ft.FontWeight.BOLD),
            ft.Text(
                "Osobne pole na każdy miesiąc — wklej do właściwej zakładki miesięcznej "
                "pliku kampanii. Kolumna Liczba to formuła (nie zamrożona wartość) — policzy "
                "się poprawnie z budżetu i kosztu w miejscu, gdzie wkleisz. Kliknij w pole, "
                "zaznacz całość (Ctrl+A) i skopiuj (Ctrl+C).",
                size=12,
                color=ft.Colors.GREY_700,
            ),
            *pola,
        ],
        spacing=10,
    )


def _render_layout(layout) -> ft.Control:
    elementy = []
    for pozycja in layout:
        if isinstance(pozycja, NaglowekZIdentyfikatorem):
            elementy.append(ft.Divider())
            elementy.append(
                ft.Row(
                    [
                        ft.Text(pozycja.tekst, weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.BLUE_900),
                        ft.Text(pozycja.etykieta_id, weight=ft.FontWeight.W_500),
                        ft.Text(pozycja.wartosc_id),
                    ],
                    spacing=16,
                )
            )
        elif isinstance(pozycja, Naglowek):
            elementy.append(ft.Divider())
            elementy.append(ft.Text(pozycja.tekst, weight=ft.FontWeight.BOLD, size=14, color=ft.Colors.BLUE_900))
        elif isinstance(pozycja, Pozycja):
            elementy.append(
                ft.Row(
                    [
                        ft.Text(f"{pozycja.numer} {pozycja.etykieta}".strip(), width=280, weight=ft.FontWeight.W_500),
                        ft.Text(pozycja.wartosc, expand=True),
                    ]
                )
            )
        elif isinstance(pozycja, LiniaPodpisu):
            elementy.append(
                ft.Row(
                    [ft.Text(pozycja.lewa, italic=True, color=ft.Colors.GREY_700, expand=True),
                     ft.Text(pozycja.prawa, italic=True, color=ft.Colors.GREY_700, expand=True)]
                )
            )
        elif isinstance(pozycja, Tekst):
            elementy.append(ft.Text(pozycja.tresc, size=10, italic=True, color=ft.Colors.GREY_700))
    return ft.Container(
        content=ft.Column(elementy, spacing=6),
        bgcolor=ft.Colors.GREY_50,
        border_radius=8,
        padding=16,
    )
