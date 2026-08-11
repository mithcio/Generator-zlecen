import flet as ft

from app.services import lookup_podmiotu as lp
from app.services import numeracja
from app.services.parser_wiersza import (
    BladParsowaniaWiersza,
    parsuj_wiersze,
    rozdziel_pola_wspolne_i_okresy,
    wykryj_ostrzezenia,
)
from app.ui.pola_pomocnicze import (
    STYL_PODPOWIEDZI,
    lista_bledow,
    naglowek_kroku,
    pole_dropdown_zamkniety,
    pole_kombo,
    pole_tekstowe,
)
from app.ui.stan import LICZBA_KROKOW

OPCJE_CAPPING = ["brak"] + [str(n) for n in range(1, 11)]
LIMIT_WIERSZY_WKLEJANIA = 12  # tyle miesięcy ma rok - kampania dłuższa to skrajny wyjątek

POLA_WYMAGANE_TUTAJ = [
    ("nazwa_kampanii", "Nazwa kampanii"),
    ("dom_mediowy", "DOM Mediowy"),
    ("klient", "Klient"),
    ("zlecajacy", "Zlecający"),
    ("target", "Target"),
    ("format_reklamowy", "Format reklamowy"),
    ("nr_zlecenia", "Numer zlecenia"),
]


def buduj(kreator) -> ft.Control:
    stan = kreator.stan

    if not stan.account_manager or not stan.podmiot_realizujacy:
        return ft.Column(
            [
                naglowek_kroku(2, LICZBA_KROKOW, "Dane kampanii"),
                ft.Text(
                    "Najpierw wybierz accounta i podmiot realizujący w kroku 1.",
                    color=ft.Colors.ORANGE_800,
                ),
                ft.Row([ft.FilledButton("Wróć do kroku 1", on_click=lambda e: kreator.idz_do_kroku(1))]),
            ],
            spacing=16,
        )

    prefiks_oczekiwany = numeracja.PREFIKSY[stan.podmiot_realizujacy]
    # Rezerwujemy raz na sesję — ale jeśli użytkownik wrócił do kroku 1 i
    # zmienił podmiot realizujący, poprzedni numer ma zły prefiks (K/S), więc
    # trzeba zarezerwować nowy zamiast zostawić niepasujący.
    if not stan.nr_zlecenia or not stan.nr_zlecenia.startswith(f"{prefiks_oczekiwany}/"):
        try:
            stan.nr_zlecenia = numeracja.zarezerwuj_numer(stan.podmiot_realizujacy, stan.account_manager)
            stan.nr_zlecenia_automatyczny = stan.nr_zlecenia
            stan.numer_automatyczny_aktywny = True
        except numeracja.BladNumeracji as err:
            return ft.Column(
                [
                    naglowek_kroku(2, LICZBA_KROKOW, "Dane kampanii"),
                    ft.Text(str(err), color=ft.Colors.RED_800),
                    ft.Row(
                        [
                            ft.FilledButton("Ustawienia", on_click=lambda e: kreator.pokaz_ustawienia()),
                            ft.TextButton("Wstecz", on_click=lambda e: kreator.wroc()),
                        ]
                    ),
                ],
                spacing=16,
            )

    def przelacz(tryb: str):
        def _handler(e: ft.Event):
            stan.tryb_danych = tryb
            kreator.odswiez()

        return _handler

    przelacznik = ft.Row(
        [
            ft.FilledButton("Wklej wiersz(e)", on_click=przelacz("wklej"))
            if stan.tryb_danych == "wklej"
            else ft.OutlinedButton("Wklej wiersz(e)", on_click=przelacz("wklej")),
            ft.FilledButton("Wypełnij pola", on_click=przelacz("formularz"))
            if stan.tryb_danych == "formularz"
            else ft.OutlinedButton("Wypełnij pola", on_click=przelacz("formularz")),
        ]
    )

    tresc = _widok_wklej(kreator) if stan.tryb_danych == "wklej" else _widok_formularz(kreator)

    return ft.Column(
        [
            naglowek_kroku(2, LICZBA_KROKOW, "Dane kampanii"),
            przelacznik,
            tresc,
            ft.Row(
                [
                    ft.TextButton("Wstecz", on_click=lambda e: kreator.wroc()),
                ],
                alignment=ft.MainAxisAlignment.START,
            ),
        ],
        spacing=16,
    )


def _widok_wklej(kreator) -> ft.Control:
    """Jedno pole = jeden skopiowany wiersz z pliku kampanii. Kampania
    przejściowa ma osobny wiersz per miesiąc (osobna zakładka w pliku), więc
    "+" dokłada kolejne pole zamiast zmuszać do ręcznego sklejania wielu
    wierszy w jednym dużym polu tekstowym przed wklejeniem."""
    stan = kreator.stan

    def ustaw_wiersz(indeks: int):
        def _handler(e: ft.Event) -> None:
            stan.wiersze_wklejane[indeks] = e.control.value or ""

        return _handler

    def usun_wiersz(indeks: int):
        def _handler(e: ft.Event) -> None:
            stan.wiersze_wklejane.pop(indeks)
            kreator.odswiez()

        return _handler

    def dodaj_wiersz(e: ft.Event) -> None:
        if len(stan.wiersze_wklejane) < LIMIT_WIERSZY_WKLEJANIA:
            stan.wiersze_wklejane.append("")
            kreator.odswiez()

    def wczytaj(e: ft.Event) -> None:
        tekst = "\n".join(w for w in stan.wiersze_wklejane if w.strip())
        try:
            wiersze = parsuj_wiersze(tekst)
        except BladParsowaniaWiersza as err:
            kreator.pokaz_blad([str(err)])
            return

        wspolne, okresy, konflikty = rozdziel_pola_wspolne_i_okresy(wiersze)
        if konflikty:
            _pokaz_dialog_konfliktow(kreator, wiersze, wspolne, okresy, konflikty)
        else:
            _sprawdz_i_zastosuj(kreator, wiersze, wspolne, okresy)

    hint_pierwszy = (
        "Wklej tu jeden wiersz skopiowany z pliku kampanii (kolumny rozdzielone "
        "tabulatorem: Nazwa Kampanii, DOM Mediowy, Klient, Zlecający, Target, "
        "Przejściowa, Format reklamowy, Podmiot realizujący, Uwagi, Model "
        "sprzedaży, Koszt jednostkowy, Nr_zlecenia, Budżet, Data startu, Data "
        "końca)."
    )
    hint_kolejny = "Kolejny miesiąc tej samej kampanii przejściowej (osobna zakładka w pliku)."

    wiele_wierszy = len(stan.wiersze_wklejane) > 1
    pola_wierszy = []
    for i, wartosc in enumerate(stan.wiersze_wklejane):
        pole = ft.TextField(
            label=f"Wiersz {i + 1}",
            value=wartosc,
            on_change=ustaw_wiersz(i),
            hint_text=hint_pierwszy if i == 0 else hint_kolejny,
            hint_style=ft.TextStyle(color=ft.Colors.GREY_400, italic=True, size=12),
            expand=True,
        )
        dzieci = [pole]
        if wiele_wierszy:
            dzieci.append(
                ft.IconButton(
                    icon=ft.Icons.DELETE_OUTLINE,
                    tooltip="Usuń ten wiersz",
                    on_click=usun_wiersz(i),
                )
            )
        pola_wierszy.append(ft.Row(dzieci, spacing=4))

    przyciski = [ft.FilledButton("Wczytaj wiersze", on_click=wczytaj)]
    if len(stan.wiersze_wklejane) < LIMIT_WIERSZY_WKLEJANIA:
        przyciski.insert(0, ft.OutlinedButton("+ Dodaj wiersz (kolejny miesiąc)", on_click=dodaj_wiersz))

    return ft.Column(
        [*pola_wierszy, ft.Row(przyciski, spacing=12, wrap=True)],
        spacing=12,
    )


def _pokaz_dialog_konfliktow(kreator, wiersze_zrodlowe, wspolne: dict, okresy, konflikty) -> None:
    etykiety = {k: v for k, v in POLA_WYMAGANE_TUTAJ}
    kontrolki: dict[str, ft.Dropdown] = {}
    tresc = [
        ft.Text(
            "Te pola różnią się między wklejonymi wierszami. Wybierz, która "
            "wartość jest poprawna dla całej kampanii:"
        )
    ]
    for k in konflikty:
        dd = ft.Dropdown(
            label=etykiety.get(k.pole, k.pole),
            value=k.wartosci[0],
            options=[ft.DropdownOption(key=w, text=w) for w in k.wartosci],
        )
        kontrolki[k.pole] = dd
        tresc.append(dd)

    def zatwierdz(e: ft.Event) -> None:
        for pole, dd in kontrolki.items():
            wspolne[pole] = dd.value
        kreator.page.pop_dialog()
        _sprawdz_i_zastosuj(kreator, wiersze_zrodlowe, wspolne, okresy)

    dlg = ft.AlertDialog(
        title=ft.Text("Wykryto różnice we wklejonych wierszach"),
        content=ft.Column(tresc, tight=True, spacing=10),
        actions=[
            ft.TextButton("Anuluj", on_click=lambda e: kreator.page.pop_dialog()),
            ft.FilledButton("Zatwierdź wybór", on_click=zatwierdz),
        ],
    )
    kreator.page.show_dialog(dlg)


def _sprawdz_i_zastosuj(kreator, wiersze_zrodlowe, wspolne: dict, okresy) -> None:
    """Przed faktycznym zastosowaniem wklejonych danych: jeśli łączymy kilka
    wierszy w jedną kampanię albo wykryliśmy niespójność (flaga Przejściowa,
    przerwa między okresami), pokazujemy podsumowanie do potwierdzenia -
    zamiast po cichu przechodzić dalej, żeby złapać pomyłki (np. przypadkowo
    pasujące pola wspólne dla dwóch w rzeczywistości różnych kampanii)."""
    ostrzezenia = wykryj_ostrzezenia(wiersze_zrodlowe, okresy)
    if len(okresy) > 1 or ostrzezenia:
        _pokaz_podsumowanie_polaczenia(kreator, wspolne, okresy, ostrzezenia)
    else:
        _zastosuj_dane_wklejone(kreator, wspolne, okresy)


def _pokaz_podsumowanie_polaczenia(kreator, wspolne: dict, okresy, ostrzezenia: list[str]) -> None:
    posortowane = sorted(okresy, key=lambda o: o.data_startu)
    tresc = [
        ft.Text(
            f"{wspolne.get('nazwa_kampanii') or '(brak nazwy)'} — {wspolne.get('klient') or '(brak klienta)'}",
            weight=ft.FontWeight.BOLD,
        ),
    ]
    for o in posortowane:
        budzet_fmt = f"{o.budzet:,.2f} PLN".replace(",", " ").replace(".", ",")
        tresc.append(
            ft.Text(f"{o.data_startu.strftime('%d.%m.%Y')} – {o.data_konca.strftime('%d.%m.%Y')}: {budzet_fmt}")
        )
    if ostrzezenia:
        tresc.append(ft.Divider())
        for tekst in ostrzezenia:
            tresc.append(ft.Text(f"⚠ {tekst}", color=ft.Colors.ORANGE_900))

    def kontynuuj(e: ft.Event) -> None:
        kreator.page.pop_dialog()
        _zastosuj_dane_wklejone(kreator, wspolne, okresy)

    dlg = ft.AlertDialog(
        title=ft.Text("Sprawdź przed kontynuacją" if ostrzezenia else "Podsumowanie połączenia"),
        content=ft.Column(tresc, tight=True, spacing=8),
        actions=[
            ft.TextButton("Wróć i popraw", on_click=lambda e: kreator.page.pop_dialog()),
            ft.FilledButton("Potwierdź i kontynuuj", on_click=kontynuuj),
        ],
    )
    kreator.page.show_dialog(dlg)


def _zastosuj_dane_wklejone(kreator, wspolne: dict, okresy) -> None:
    stan = kreator.stan
    if wspolne.get("podmiot_realizujacy"):
        stan.podmiot_realizujacy = wspolne["podmiot_realizujacy"]

    stan.nazwa_kampanii = wspolne.get("nazwa_kampanii") or ""
    stan.dom_mediowy = wspolne.get("dom_mediowy") or ""
    if stan.podmiot_realizujacy == "Sp. z o.o.":
        # klient bezpośredni - kolumna "Klient" w źródle jest ignorowana
        # (bywa pusta/"-"/"brak"), dane biorą się z kolumny "Dom Mediowy".
        stan.klient = stan.dom_mediowy
    else:
        stan.klient = wspolne.get("klient") or ""
    stan.zlecajacy = wspolne.get("zlecajacy") or ""
    stan.target = wspolne.get("target") or ""
    stan.format_reklamowy = wspolne.get("format_reklamowy") or ""
    stan.model_sprzedazy = wspolne.get("model_sprzedazy") or "CPM"
    koszt = wspolne.get("koszt_jednostkowy")
    stan.koszt_jednostkowy = str(koszt) if koszt is not None else ""
    stan.nr_zlecenia = wspolne.get("nr_zlecenia") or stan.nr_zlecenia
    # Uwagi celowo NIE są ustawiane z wklejonego wiersza - kolumna Uwagi w
    # pliku kampanii to co innego niż Zlecenie.pola.uwagi (uwaga na
    # dokumencie dla klienta) - do wypełnienia ręcznie, patrz pole niżej.
    stan.okresy = okresy
    # Nie skaczemy od razu do okresów — "Brand", "Capping" i "Uwagi" nie są
    # częścią wklejanego wiersza, więc przełączamy na widok formularza (te
    # same pola stan.*, już wypełnione z wklejenia) żeby użytkownik mógł je
    # uzupełnić i przejrzeć sparsowane dane, zanim pójdzie dalej.
    stan.tryb_danych = "formularz"
    kreator.odswiez()


def _pokaz_ostrzezenie_brak_brandu(kreator, stan) -> None:
    """Brand nie występuje w pliku z kampaniami (wklejone wiersze go nie
    ustawiają), więc łatwo o niego zapomnieć - a bywa wymagany na
    finalnym zleceniu. Ostrzeżenie, nie blokada: da się świadomie
    kontynuować bez niego."""

    def kontynuuj(e: ft.Event) -> None:
        kreator.page.pop_dialog()
        stan.krok = 3
        kreator.odswiez()

    dlg = ft.AlertDialog(
        title=ft.Text("Sprawdź przed kontynuacją"),
        content=ft.Text(
            "Pole „Brand” jest puste. Plik z kampaniami go nie zawiera, więc przy "
            "wklejaniu wierszy nigdy nie wypełnia się samo — a bywa wymagane na "
            "finalnym zleceniu.",
            color=ft.Colors.ORANGE_900,
        ),
        actions=[
            ft.TextButton("Wróć i popraw", on_click=lambda e: kreator.page.pop_dialog()),
            ft.FilledButton("Kontynuuj mimo to", on_click=kontynuuj),
        ],
    )
    kreator.page.show_dialog(dlg)


def _pokaz_ostrzezenie_numeru(kreator, stan) -> None:
    """Numer zlecenia w stanie różni się od tego faktycznie pobranego
    automatycznie z pliku (wklejony wiersz albo ręczna edycja go nadpisały).
    Użytkownik decyduje, który ma obowiązywać - jeśli zostaje przy wpisanym
    ręcznie, zwalniamy w pliku rezerwację tego pobranego automatycznie, żeby
    nie została "wisząca" (zajęta, ale nieużyta)."""
    numer_auto = stan.nr_zlecenia_automatyczny
    numer_wpisany = stan.nr_zlecenia

    def popraw_na_automatyczny(e: ft.Event) -> None:
        stan.nr_zlecenia = numer_auto
        kreator.page.pop_dialog()
        stan.krok = 3
        kreator.odswiez()

    def zachowaj_wpisany(e: ft.Event) -> None:
        try:
            numeracja.zwolnij_numer(numer_auto, stan.podmiot_realizujacy)
        except numeracja.BladNumeracji as err:
            kreator.page.pop_dialog()
            kreator.pokaz_blad([str(err)])
            return
        stan.numer_automatyczny_aktywny = False
        kreator.page.pop_dialog()
        stan.krok = 3
        kreator.odswiez()

    dlg = ft.AlertDialog(
        title=ft.Text("Numer zlecenia różni się od automatycznie pobranego"),
        content=ft.Text(
            f"Automatycznie pobrany numer to {numer_auto}, a w polu jest teraz "
            f"{numer_wpisany} (wklejony wiersz albo ręczna zmiana). Który ma zostać?",
            color=ft.Colors.ORANGE_900,
        ),
        actions=[
            ft.TextButton(f"Popraw na automatyczny ({numer_auto})", on_click=popraw_na_automatyczny),
            ft.FilledButton(f"Zachowaj wpisany ({numer_wpisany})", on_click=zachowaj_wpisany),
        ],
    )
    kreator.page.show_dialog(dlg)


def _widok_formularz(kreator) -> ft.Control:
    """Sp. k. = agencja pośredniczy: "DOM Mediowy" (agencje accounta) + osobne
    "Klient" (marki obsługiwane przez WYBRANĄ agencję - lista zależna od
    wyboru powyżej, reset przy zmianie agencji). Sp. z o.o. = klient
    bezpośredni: jedno pole "Klient" (lista bezpośrednich klientów accounta),
    bez osobnego zdublowanego pola - zasila jednocześnie dom_mediowy i klient,
    bo to ta sama encja (patrz zlecenie_layout.py: 2.1 i 3.1 pokazują to samo)."""
    stan = kreator.stan
    slow = lp.slowniki()
    jest_bezposredni = stan.podmiot_realizujacy == "Sp. z o.o."

    def ustaw(pole: str):
        def _handler(wartosc: str) -> None:
            setattr(stan, pole, wartosc)

        return _handler

    if jest_bezposredni:
        klienci_bezposredni = list(
            lp.podmioty_dla_accounta_i_typu(stan.account_manager, "Sp. z o.o.").keys()
        )

        def ustaw_klienta_bezposredniego(wartosc: str) -> None:
            stan.dom_mediowy = wartosc
            stan.klient = wartosc

        pole_agencja_lub_klient = pole_kombo(
            "Klient", klienci_bezposredni, stan.dom_mediowy, ustaw_klienta_bezposredniego
        )
        pole_klient_agencyjny = None
    else:
        agencje = list(lp.podmioty_dla_accounta_i_typu(stan.account_manager, "Sp. k.").keys())

        def ustaw_agencje_wybor(e: ft.Event) -> None:
            stan.dom_mediowy = e.control.value or ""
            stan.klient = ""  # lista klientów zależy od agencji - reset przy zmianie
            kreator.odswiez()

        def ustaw_agencje_tekst(e: ft.Event) -> None:
            stan.dom_mediowy = e.control.text or ""
            # bez odswiez() przy każdym znaku - traciłoby fokus w trakcie pisania

        pole_agencja_lub_klient = ft.Dropdown(
            label="DOM Mediowy",
            value=stan.dom_mediowy if stan.dom_mediowy in agencje else None,
            text=stan.dom_mediowy,
            editable=True,
            enable_filter=True,
            options=[ft.DropdownOption(key=a, text=a) for a in agencje],
            on_select=ustaw_agencje_wybor,
            on_text_change=ustaw_agencje_tekst,
            hint_text="wybierz z listy albo wpisz",
            hint_style=STYL_PODPOWIEDZI,
            expand=True,
        )
        klienci_agencji = (
            lp.klienci_dla_agencji(stan.account_manager, stan.dom_mediowy) if stan.dom_mediowy else []
        )
        pole_klient_agencyjny = pole_kombo("Klient", klienci_agencji, stan.klient, ustaw("klient"))

    pola_lista = [
        pole_tekstowe(
            "Nazwa kampanii", stan.nazwa_kampanii, ustaw("nazwa_kampanii"),
            podpowiedz="np. LEGO City Sierpień",
        ),
        pole_agencja_lub_klient,
    ]
    if pole_klient_agencyjny is not None:
        pola_lista.append(pole_klient_agencyjny)
    pola_lista += [
        pole_tekstowe("Brand", stan.brand, ustaw("brand"), podpowiedz="np. Hellena"),
        pole_tekstowe(
            "Zlecający (osoba kontaktowa)", stan.zlecajacy, ustaw("zlecajacy"),
            podpowiedz="np. Jan Kowalski",
        ),
        pole_kombo("Target", slow.get("target", []), stan.target, ustaw("target")),
        pole_dropdown_zamkniety("Capping", OPCJE_CAPPING, stan.capping, ustaw("capping")),
        pole_kombo(
            "Format reklamowy", slow.get("format_reklamowy", []), stan.format_reklamowy,
            ustaw("format_reklamowy"),
        ),
        pole_tekstowe("Numer zlecenia", stan.nr_zlecenia, ustaw("nr_zlecenia")),
        pole_tekstowe(
            "Uwagi", stan.uwagi, ustaw("uwagi"), wieloliniowe=True,
            podpowiedz="np. dodatkowe ustalenia z klientem",
        ),
    ]
    pola = ft.Column(pola_lista, spacing=12)

    def dalej(e: ft.Event) -> None:
        # Liczone dopiero tu (nie raz na starcie renderu) - pola tekstowe/kombo
        # celowo nie odświeżają całej strony przy każdej zmianie (żeby nie
        # tracić fokusu), więc stan.* trzeba czytać na bieżąco przy kliknięciu.
        bledy = [etykieta for pole, etykieta in POLA_WYMAGANE_TUTAJ if not getattr(stan, pole)]
        if bledy:
            kreator.pokaz_blad([f"To pole jest wymagane: {b}." for b in bledy])
            return
        if not stan.brand:
            _pokaz_ostrzezenie_brak_brandu(kreator, stan)
            return
        if stan.nr_zlecenia_automatyczny and stan.nr_zlecenia != stan.nr_zlecenia_automatyczny:
            _pokaz_ostrzezenie_numeru(kreator, stan)
            return
        stan.krok = 3
        kreator.odswiez()

    return ft.Column(
        [pola, ft.Row([ft.FilledButton("Dalej", on_click=dalej)], alignment=ft.MainAxisAlignment.END)],
        spacing=16,
    )
