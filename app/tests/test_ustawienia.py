import pytest

from app.services import ustawienia


@pytest.fixture(autouse=True)
def _izolacja(tmp_path, monkeypatch):
    monkeypatch.setattr(ustawienia, "DATA_PLIK", tmp_path / "ustawienia.json")


def test_wczytaj_bez_pliku_zwraca_domyslne():
    stan = ustawienia.wczytaj()
    assert stan == ustawienia.DOMYSLNE


def test_zapisz_i_wczytaj_zwraca_ta_sama_wartosc():
    ustawienia.zapisz(sciezka_numery_zlecen="C:/Numery_zlecen_2026.xlsx")
    assert ustawienia.wczytaj()["sciezka_numery_zlecen"] == "C:/Numery_zlecen_2026.xlsx"


def test_zapisz_czesciowo_nie_nadpisuje_reszty():
    ustawienia.zapisz(sciezka_numery_zlecen="a.xlsx")
    ustawienia.zapisz(domyslny_account_manager="Igor Samul")
    stan = ustawienia.wczytaj()
    assert stan["sciezka_numery_zlecen"] == "a.xlsx"
    assert stan["domyslny_account_manager"] == "Igor Samul"
