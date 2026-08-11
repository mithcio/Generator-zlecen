from datetime import date

from app.models.kampania import PolaWspolne
from app.models.okres import Okres
from app.models.zlecenie import Zlecenie
from app.services.eksport_wiersza import zbuduj_wiersze_do_wklejenia
from app.services.parser_wiersza import parsuj_wiersz


def _zlecenie(model_sprzedazy="CPM", koszt_jednostkowy=26.0, podmiot_realizujacy="Sp. k.", okresy=None):
    pola = PolaWspolne(
        account_manager="Igor Samul",
        podmiot_realizujacy=podmiot_realizujacy,
        nr_zlecenia="K/2026/077",
        nazwa_kampanii="Colian_Hellena_Lody",
        dom_mediowy="Initiative Media Warszawa sp. z o.o.",
        klient="Colian",
        brand="Hellena",
        zlecajacy="Paulina Kowalik",
        target="KIDS",
        capping=3,
        format_reklamowy="In-game audio KIDS",
        model_sprzedazy=model_sprzedazy,
        koszt_jednostkowy=koszt_jednostkowy,
        uwagi="Dzieci",
    )
    if okresy is None:
        okresy = [Okres(date(2026, 8, 1), date(2026, 8, 31), 50000.0)]
    return Zlecenie(pola=pola, okresy=okresy)


def test_jeden_okres_daje_jeden_wiersz_nie_przejsciowy():
    zlecenie = _zlecenie()
    tekst = zbuduj_wiersze_do_wklejenia(zlecenie)
    wiersze = tekst.splitlines()
    assert len(wiersze) == 1
    kolumny = wiersze[0].split("\t")
    assert len(kolumny) == 16
    assert kolumny[5] == "NIE"  # Przejściowa


def test_dwa_okresy_daja_dwa_wiersze_przejsciowe_posortowane_chronologicznie():
    okresy = [
        Okres(date(2026, 8, 1), date(2026, 8, 31), 44285.71),
        Okres(date(2026, 7, 28), date(2026, 7, 31), 5714.29),  # celowo nie po kolei
    ]
    zlecenie = _zlecenie(okresy=okresy)
    wiersze = zbuduj_wiersze_do_wklejenia(zlecenie).splitlines()
    assert len(wiersze) == 2
    assert all(w.split("\t")[5] == "TAK" for w in wiersze)
    assert wiersze[0].split("\t")[13] == "28.07.2026"  # lipiec pierwszy mimo kolejnosci wejsciowej
    assert wiersze[1].split("\t")[13] == "01.08.2026"


def test_formula_liczby_cpm_ma_mnoznik_tysiac_i_jest_niezalezna_od_wiersza():
    zlecenie = _zlecenie(model_sprzedazy="CPM")
    kolumny = zbuduj_wiersze_do_wklejenia(zlecenie).split("\t")
    formula = kolumny[-1]
    assert formula.startswith("=")
    assert "*1000" in formula
    assert "ROW()" in formula
    assert "K2" not in formula and "M2" not in formula  # nie odwoluje sie do konkretnego wiersza


def test_formula_liczby_cpc_bez_mnoznika():
    zlecenie = _zlecenie(model_sprzedazy="CPC", koszt_jednostkowy=2.0)
    kolumny = zbuduj_wiersze_do_wklejenia(zlecenie).split("\t")
    assert "*1000" not in kolumny[-1]


def test_ff_liczba_to_literalna_jedynka_bez_formuly():
    zlecenie = _zlecenie(model_sprzedazy="FF", koszt_jednostkowy=0.0)
    kolumny = zbuduj_wiersze_do_wklejenia(zlecenie).split("\t")
    assert kolumny[-1] == "1"


def test_sp_zoo_ma_pusta_kolumne_klient():
    zlecenie = _zlecenie(podmiot_realizujacy="Sp. z o.o.")
    zlecenie.pola.dom_mediowy = "TM Toys sp. z o.o."
    zlecenie.pola.klient = "TM Toys sp. z o.o."
    kolumny = zbuduj_wiersze_do_wklejenia(zlecenie).split("\t")
    assert kolumny[1] == "TM Toys sp. z o.o."  # Dom Mediowy
    assert kolumny[2] == ""  # Klient - pusty dla bezposredniego


def test_kolumna_uwagi_zawsze_pusta_mimo_wypelnionego_pola():
    # Uwagi w pliku kampanii to co innego niż Zlecenie.pola.uwagi (uwaga na
    # dokumencie dla klienta) - nie ma prawa trafić z powrotem do kolumny
    # Uwagi pliku kampanii.
    zlecenie = _zlecenie()
    assert zlecenie.pola.uwagi == "Dzieci"
    kolumny = zbuduj_wiersze_do_wklejenia(zlecenie).split("\t")
    assert kolumny[8] == ""  # Uwagi


def test_wiersz_da_sie_z_powrotem_sparsowac_symetrycznie():
    """Wiersz wyeksportowany musi być poprawnie odczytywany przez ten sam
    parser, który obsługuje wklejanie w kroku 2 - to sprawdza symetrię."""
    zlecenie = _zlecenie()
    wiersz_tekst = zbuduj_wiersze_do_wklejenia(zlecenie)
    sparsowany = parsuj_wiersz(wiersz_tekst)
    assert sparsowany["nazwa_kampanii"] == "Colian_Hellena_Lody"
    assert sparsowany["dom_mediowy"] == "Initiative Media Warszawa sp. z o.o."
    assert sparsowany["klient"] == "Colian"
    assert sparsowany["model_sprzedazy"] == "CPM"
    assert sparsowany["koszt_jednostkowy"] == 26.0
    assert sparsowany["budzet"] == 50000.0
    assert sparsowany["data_startu"] == date(2026, 8, 1)
    assert sparsowany["data_konca"] == date(2026, 8, 31)
