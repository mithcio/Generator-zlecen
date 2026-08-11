"""Odwrotność parser_wiersza.py: buduje wiersz(e) gotowe do wklejenia z
powrotem do pliku kampanii (jeden wiersz = jeden okres/miesiąc), w dokładnie
tym samym układzie 15+1 kolumn, jakiego oczekuje parser przy wklejaniu:
Nazwa Kampanii, DOM Mediowy, Klient, Zlecający, Target, Przejściowa, Format
reklamowy, Podmiot realizujący, Uwagi, Model sprzedaży, Koszt jednostkowy,
Nr_zlecenia, Budżet, Data startu, Data końca, Liczba.

Kolumna Liczba to formuła Excela, nie zamrożona wartość — ale wklejenie
tekstu (nie natywne kopiuj-wklej Excela) NIE przesuwa referencji względem
wiersza docelowego, więc zwykłe "=M2/K2*1000" zawsze wskazywałoby na wiersz 2,
bez względu na to, gdzie faktycznie wkleisz. Zamiast tego formuła czyta własny
wiersz przez ROW()+INDIRECT — poprawnie liczy niezależnie od miejsca wklejenia
(potwierdzone testem w Excelu: kopiowanie całego wiersza gdziekolwiek indziej
dalej liczy z właściwych, lokalnych komórek).
"""
from app.models.okres import Okres
from app.models.zlecenie import Zlecenie


def _fmt_liczba(x: float) -> str:
    if x == int(x):
        return str(int(x))
    return f"{x:.2f}"


def _formula_liczby(model_sprzedazy: str) -> str:
    if model_sprzedazy == "FF":
        return "1"
    mnoznik = "*1000" if model_sprzedazy == "CPM" else ""
    return f'=IF(INDIRECT("K"&ROW())=0,0,INDIRECT("M"&ROW())/INDIRECT("K"&ROW()){mnoznik})'


def _zbuduj_wiersz(zlecenie: Zlecenie, okres: Okres) -> str:
    pola = zlecenie.pola
    przejsciowa = "TAK" if len(zlecenie.okresy) > 1 else "NIE"
    # Dla klienta bezpośredniego (Sp. z o.o.) kolumna Klient w źródle jest
    # pusta - to Dom Mediowy niesie tę samą wartość (patrz krok2_dane_kampanii.py).
    klient = pola.klient if pola.podmiot_realizujacy == "Sp. k." else ""

    kolumny = [
        pola.nazwa_kampanii,
        pola.dom_mediowy,
        klient,
        pola.zlecajacy,
        pola.target,
        przejsciowa,
        pola.format_reklamowy,
        pola.podmiot_realizujacy,
        # Kolumna Uwagi w pliku kampanii to co innego niż Zlecenie.pola.uwagi
        # (uwaga na dokumencie dla klienta) - nie wpisujemy jej tutaj z
        # powrotem, patrz ustalenia z użytkownikiem.
        "",
        pola.model_sprzedazy,
        _fmt_liczba(pola.koszt_jednostkowy),
        pola.nr_zlecenia,
        _fmt_liczba(okres.budzet),
        okres.data_startu.strftime("%d.%m.%Y"),
        okres.data_konca.strftime("%d.%m.%Y"),
        _formula_liczby(pola.model_sprzedazy),
    ]
    return "\t".join(str(k) if k is not None else "" for k in kolumny)


def zbuduj_wiersze_do_wklejenia_per_okres(zlecenie: Zlecenie) -> list[tuple[Okres, str]]:
    """Jak zbuduj_wiersze_do_wklejenia, ale zwraca listę (okres, wiersz) -
    do pokazania jako osobne pole tekstowe per miesiąc, każde podpisane
    zakresem dat, którego dotyczy (każdy miesiąc trafia do innej zakładki
    pliku kampanii, więc jedno wspólne pole tekstowe myliło, do której
    zakładki wkleić który wiersz)."""
    posortowane = sorted(zlecenie.okresy, key=lambda o: o.data_startu)
    return [(okres, _zbuduj_wiersz(zlecenie, okres)) for okres in posortowane]


def zbuduj_wiersze_do_wklejenia(zlecenie: Zlecenie) -> str:
    """Jeden wiersz tekstu per okres (miesiąc), rozdzielone nowymi liniami -
    gotowe do wklejenia bezpośrednio do zakładek miesięcznych pliku kampanii."""
    return "\n".join(wiersz for _, wiersz in zbuduj_wiersze_do_wklejenia_per_okres(zlecenie))
