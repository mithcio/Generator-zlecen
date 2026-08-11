from datetime import date

from app.models.kampania import PolaWspolne
from app.models.okres import Okres
from app.models.zlecenie import Zlecenie
from app.services.walidacja import waliduj_zlecenie

POLA_OK = dict(
    account_manager="Igor Samul",
    podmiot_realizujacy="Sp. k.",
    nr_zlecenia="K/2026/078",
    nazwa_kampanii="Test",
    dom_mediowy="Initiative Media Warszawa sp. z o.o.",
    klient="Colian",
    brand="Hellena",
    zlecajacy="Paulina Kowalik",
    target="KIDS",
    capping=3,
    format_reklamowy="In-game audio KIDS",
    model_sprzedazy="CPM",
    koszt_jednostkowy=26,
)


def _zlecenie(**nadpisania):
    pola = PolaWspolne(**{**POLA_OK, **nadpisania})
    okresy = [Okres(date(2026, 7, 28), date(2026, 7, 31), 5714.29)]
    return Zlecenie(pola=pola, okresy=okresy)


def test_poprawne_zlecenie_bez_bledow():
    assert waliduj_zlecenie(_zlecenie()) == []


def test_brak_wymaganego_pola():
    bledy = waliduj_zlecenie(_zlecenie(klient=""))
    assert any("Klient" in b for b in bledy)


def test_koszt_zero_jest_bledem():
    bledy = waliduj_zlecenie(_zlecenie(koszt_jednostkowy=0))
    assert any("Koszt jednostkowy" in b for b in bledy)


def test_capping_ujemny_jest_bledem():
    bledy = waliduj_zlecenie(_zlecenie(capping=-1))
    assert any("Capping" in b for b in bledy)


def test_brak_okresow_jest_bledem():
    pola = PolaWspolne(**POLA_OK)
    z = Zlecenie(pola=pola, okresy=[])
    bledy = waliduj_zlecenie(z)
    assert any("okres" in b.lower() for b in bledy)


def test_data_konca_przed_startem_jest_bledem():
    pola = PolaWspolne(**POLA_OK)
    z = Zlecenie(pola=pola, okresy=[Okres(date(2026, 8, 1), date(2026, 7, 1), 1000)])
    bledy = waliduj_zlecenie(z)
    assert any("Data końca" in b for b in bledy)


def test_okres_rozciagniety_na_dwa_miesiace_jest_bledem():
    # Jeden okres = jeden wiersz w jednej zakładce miesięcznej pliku
    # kampanii - zakres sierpień-wrzesień w jednym okresie nie ma gdzie
    # trafić, powinien być rozbity na dwa okresy (po jednym na miesiąc).
    pola = PolaWspolne(**POLA_OK)
    z = Zlecenie(pola=pola, okresy=[Okres(date(2026, 8, 15), date(2026, 9, 15), 1000)])
    bledy = waliduj_zlecenie(z)
    assert any("jednym miesiącu" in b for b in bledy)


def test_okres_w_jednym_miesiacu_nie_jest_bledem():
    pola = PolaWspolne(**POLA_OK)
    z = Zlecenie(pola=pola, okresy=[Okres(date(2026, 8, 1), date(2026, 8, 31), 1000)])
    assert waliduj_zlecenie(z) == []
